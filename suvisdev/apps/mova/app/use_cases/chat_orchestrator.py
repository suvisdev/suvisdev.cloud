"""mova 채팅 오케스트레이터(2026-09-27) — 발화를 한 번 이해하고, 사실은 데이터로 검증한다.

전에는 이 역할이 셋으로 쪼개져 있었다: Hub 분류기(의도만), ChatInteractor의 if 사슬(디스패치),
트랙별 정규식(작품명·지역 추출). 같은 발화를 트랙마다 다르게 읽어 "파과→파", "시간표 질의→잡담"
같은 사고가 났다(09-27). 여기서는:
  1) ChatUnderstandingPort(EXAONE 7.8B)가 {의도, 작품명, 지역, 시각, 체인, 이어받기}를 읽고
  2) 작품명은 카탈로그와 대조해 확정(없으면 미확정 텍스트로 넘겨 트랙이 되묻는다)
  3) 예매 어휘 결정론 가드는 마지막 안전망으로 남긴다(LLM이 booking을 놓쳐도 잡는다)
지역은 예매 트랙이 카카오 지오코딩으로 확인하므로 문자열만 넘긴다. 이해 실패(LLM 불가)는
None을 돌려 ChatInteractor의 기존 결정론 경로로 폴백한다 — 회귀 하네스가 양쪽을 다 본다.

섀도 비교(2026-09-28): `shadow` 이해 모델(예: 학습한 2.4B)을 주면 같은 발화를 백그라운드로 한 번
더 읽혀 주 모델과 필드별로 비교하고 `on_shadow`로 기록한다. 응답은 주 모델 결과로 이미 나가므로
사용자 지연·결과에 영향이 없다. 교체 전 실사용 불일치를 모으는 용도.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.app.dtos.chat_understanding_dto import ChatUnderstanding, VerifiedSlots
from mova.app.ports.output.chat_understanding_port import (
    ChatUnderstandingError,
    ChatUnderstandingPort,
)
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.domain.value_objects.movie_title import MovieTitle

logger = logging.getLogger(__name__)

_SHADOW_FIELDS = ("intent", "title", "region", "time", "chain", "followup")
# 백그라운드 태스크가 GC로 사라지지 않게 참조를 잡아 둔다(asyncio 문서 권고)
_shadow_tasks: set[asyncio.Task[None]] = set()


class ChatOrchestrator:
    def __init__(
        self,
        understanding: ChatUnderstandingPort,
        repository: ChatRepositoryPort,
        *,
        booking_lexicon: re.Pattern[str] | None = None,
        recommend_word: re.Pattern[str] | None = None,
        shadow: ChatUnderstandingPort | None = None,
        on_shadow: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._understanding = understanding
        self._repo = repository
        self._booking_lexicon = booking_lexicon
        self._recommend_word = recommend_word
        self._shadow = shadow
        self._on_shadow = on_shadow

    async def plan(
        self, message: str, history: list[dict[str, str]], *, trace_id: str
    ) -> VerifiedSlots | None:
        t0 = time.monotonic()
        try:
            u = await self._understanding.understand(message, history)
        except ChatUnderstandingError as e:
            logger.warning("[Orchestrator] trace=%s 이해 실패 → 결정론 경로 폴백 | %s", trace_id, e)
            self._start_shadow(message, history, None, 0.0, trace_id)
            return None
        self._start_shadow(message, history, u, time.monotonic() - t0, trace_id)
        intent = self._guard_intent(u, message)
        movie = await self._verify_title(u.title)
        slots = VerifiedSlots(
            intent=intent,
            title_text=u.title,
            movie=movie,
            region=u.region,
            time=u.time,
            chain=u.chain,
            followup=u.followup,
        )
        logger.info(
            "[Orchestrator] trace=%s intent=%s(llm=%s) title=%r movie=%s region=%r followup=%s",
            trace_id,
            intent,
            u.intent,
            u.title,
            f"{movie.title}({movie.year})" if movie else None,
            u.region,
            u.followup,
        )
        return slots

    def _start_shadow(
        self,
        message: str,
        history: list[dict[str, str]],
        primary: ChatUnderstanding | None,
        primary_s: float,
        trace_id: str,
    ) -> None:
        if self._shadow is None:
            return
        task = asyncio.create_task(self._run_shadow(message, history, primary, primary_s, trace_id))
        _shadow_tasks.add(task)
        task.add_done_callback(_shadow_tasks.discard)

    async def _run_shadow(
        self,
        message: str,
        history: list[dict[str, str]],
        primary: ChatUnderstanding | None,
        primary_s: float,
        trace_id: str,
    ) -> None:
        assert self._shadow is not None
        t0 = time.monotonic()
        shadow: ChatUnderstanding | None
        error = None
        try:
            shadow = await self._shadow.understand(message, history)
        except Exception as e:  # noqa: BLE001 — 섀도 실패는 기록만 하고 서비스엔 영향 없음
            shadow, error = None, str(e)[:200]
        p = asdict(primary) if primary else None
        sh = asdict(shadow) if shadow else None
        diff = [f for f in _SHADOW_FIELDS if (p or {}).get(f) != (sh or {}).get(f)]
        record = {
            "trace_id": trace_id,
            "message": message,
            "history": history[-4:],
            "primary": p,
            "shadow": sh,
            "match": not diff,
            "diff": diff,
            "primary_s": round(primary_s, 2),
            "shadow_s": round(time.monotonic() - t0, 2),
            "shadow_error": error,
        }
        logger.info(
            "[OrchestratorShadow] trace=%s match=%s diff=%s primary=%s shadow=%s",
            trace_id,
            record["match"],
            ",".join(diff) or "-",
            p,
            sh if sh else error,
        )
        if self._on_shadow is not None:
            try:
                await asyncio.to_thread(self._on_shadow, record)
            except Exception:  # noqa: BLE001
                logger.warning("[OrchestratorShadow] 기록 실패", exc_info=True)

    def _guard_intent(self, u: ChatUnderstanding, message: str) -> str:
        """예매 어휘가 있는데 LLM이 booking을 놓치면 booking으로(추천 발화는 제외)."""
        if (
            self._booking_lexicon is not None
            and u.intent != "booking"
            and self._booking_lexicon.search(message)
            and not (self._recommend_word and self._recommend_word.search(message))
        ):
            return "booking"
        return u.intent

    async def _verify_title(self, title: str | None) -> MovaSearchItemSchema | None:
        """카탈로그 정확 일치(공백·대소문자 무시)만 확정으로 본다. 부분일치·퍼지는 여기서 안 한다 —
        그건 트랙의 해석기가 되묻기와 함께 처리한다."""
        if not title:
            return None
        items = await self._repo.search_movies_by_title([title], 5)
        wanted = MovieTitle(title)
        exact = [i for i in items if wanted.equals(i.title)]
        return exact[0] if exact else None
