"""booking 트랙 — "호프 예매하고 싶어" 류 질의에 상영 여부·근처 영화관을 안내한다.

Phase 1(설계서 §5): 상영 중 판정은 KOFIC 주간 박스오피스 등재 여부로 근사하고,
상영시간표는 직접 보여주지 않는다 — 모르는 것은 체인 검색 딥링크로 위임(정직성
규칙). 지역은 사용자 발화의 지역명으로 받고, 없으면 되묻는다(슬롯 필링).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from mova.adapter.outbound.http.kofic_adapter import KoficAdapterError
from mova.app.dtos.market_chat_dto import (
    ChatBookingDto,
    ChatBookingLinkDto,
    ChatRecommendationDto,
    ChatTheaterDto,
    CinemaShowtimeDto,
)
from mova.app.dtos.studio_movies_dto import MovieDetailDto
from mova.app.ports.output.box_office_port import BoxOfficePort
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.ports.output.showtime_port import ShowtimePort
from mova.app.ports.output.theater_search_port import TheaterSearchPort
from mova.app.use_cases.market_chat_title_resolver import resolve_movie_title

logger = logging.getLogger(__name__)

# 지역 되묻기 응답의 결정론 마커 — 다음 턴을 지역 입력으로 이어 받는 근거.
# 제목은 『』로 감싸 넣어 다음 턴에서 그대로 복원한다(비로그인도 history만으로 동작).
REGION_ASK_MARKER = "어느 지역에서 보실 계획인가요"

# 체인 공식 검색 딥링크 — 시간표를 아는 척하지 않고 검색 페이지로 위임한다.
_BOOKING_LINK_TEMPLATES = (
    ("CGV", "http://www.cgv.co.kr/search/?query={q}"),
    ("롯데시네마", "https://www.lottecinema.co.kr/NLCHS/Search?searchText={q}"),
    ("메가박스", "https://www.megabox.co.kr/search?searchText={q}"),
)


@dataclass(frozen=True)
class BookingResult:
    status: str  # "ok" | "not_found" | "ambiguous"
    reply: str
    card: ChatRecommendationDto | None
    booking: ChatBookingDto | None
    resolved_movie_id: int | None = None  # 예매 의지 신호(booking_intent) 기록용


def pending_title_from_history(history: list[dict[str, str]]) -> str | None:
    """직전 assistant 응답이 지역 되묻기였으면 『』 안의 제목을 복원한다."""
    for msg in reversed(history):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content") or ""
        if REGION_ASK_MARKER in content and "『" in content and "』" in content:
            return content.split("『", 1)[1].split("』", 1)[0].strip() or None
        return None
    return None


# 이동수단 슬롯(2026-08-28 사용자 결정: 순위에 영향 주는 상황 변수는 되묻거나
# 함께 받는다) — 지역 답변에 이동수단이 섞여 오면 파싱해 검색 반경을 조정한다.
# 예: "강남 차로 갈게" → region="강남", 반경 20km.
_TRANSPORT_CAR_WORDS = ("차로", "자차", "운전", "자가용", "드라이브")
_TRANSPORT_WALK_WORDS = ("걸어", "도보")
_TRANSPORT_FILLER_WORDS = ("갈게", "갈래", "갈거야", "갈", "타고", "이동", "예정", "가요", "감")
_RADIUS_DEFAULT_M = 10_000
_RADIUS_CAR_M = 20_000
_RADIUS_WALK_M = 3_000


def _parse_region_transport(text: str) -> tuple[str, int, str | None]:
    """지역 발화 → (지역명, 검색 반경 m, 이동수단 라벨|None)."""
    radius, label = _RADIUS_DEFAULT_M, None
    region_tokens: list[str] = []
    for token in text.split():
        if any(w in token for w in _TRANSPORT_CAR_WORDS):
            radius, label = _RADIUS_CAR_M, "차량"
            continue
        if any(w in token for w in _TRANSPORT_WALK_WORDS):
            radius, label = _RADIUS_WALK_M, "도보"
            continue
        if token in _TRANSPORT_FILLER_WORDS:
            continue
        region_tokens.append(token)
    region = " ".join(region_tokens).strip() or text.strip()
    return region, radius, label


def _booking_links(title: str) -> list[ChatBookingLinkDto]:
    q = quote(title)
    return [
        ChatBookingLinkDto(chain=chain, url=url.format(q=q))
        for chain, url in _BOOKING_LINK_TEMPLATES
    ]


def _normalize(title: str) -> str:
    return "".join(title.split()).lower()


_MAX_SHOWTIME_CINEMAS = 2


class BookingAssistService:
    def __init__(
        self,
        *,
        repository: ChatRepositoryPort,
        movies: MoviesRepositoryPort,
        box_office: BoxOfficePort,
        theaters: TheaterSearchPort,
        showtimes: ShowtimePort | None = None,
    ) -> None:
        self._repository = repository
        self._movies = movies
        self._box_office = box_office
        self._theaters = theaters
        self._showtimes = showtimes

    async def assist(
        self,
        *,
        message: str,
        entities: list[str],
        trace_id: str,
        pending_title: str | None = None,
    ) -> BookingResult:
        if pending_title:
            return await self._assist_with_region(
                title_term=pending_title, region=message.strip(), trace_id=trace_id
            )

        resolution = await resolve_movie_title(self._repository, message=message, entities=entities)
        if resolution.status == "not_found":
            return BookingResult(
                status="not_found",
                reply=(
                    "예매하실 작품을 카탈로그에서 찾지 못했어요. "
                    "정확한 제목으로 다시 알려주시겠어요?"
                ),
                card=None,
                booking=None,
            )
        if resolution.status == "ambiguous":
            names = " / ".join(
                f"{c.title}({c.year})" if c.year else c.title for c in resolution.candidates
            )
            return BookingResult(
                status="ambiguous",
                reply=f"비슷한 제목이 여러 편이에요: {names}. 어떤 작품을 예매하시려나요?",
                card=None,
                booking=None,
            )

        assert resolution.item is not None
        movie_id = int(resolution.item.id)
        detail = await self._movies.find_by_id(movie_id)
        if detail is None:
            return BookingResult(
                status="not_found",
                reply="작품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
                card=None,
                booking=None,
            )
        card = self._card(detail, movie_id)

        if not await self._is_showing(detail.title):
            platforms = ", ".join(p.provider for p in detail.platforms if p.provider)
            ott_line = (
                f" 대신 {platforms}에서 감상하실 수 있어요."
                if platforms
                else " OTT 공개 정보도 아직 없어요."
            )
            return BookingResult(
                status="ok",
                reply=(
                    f"『{detail.title}』은(는) 최근 주간 박스오피스 기준으로 현재 상영작에서 "
                    f"확인되지 않아요(소규모 상영은 놓칠 수 있어요).{ott_line}"
                ),
                card=card,
                booking=ChatBookingDto(
                    status="not_showing", region=None, theaters=[], booking_links=[]
                ),
                resolved_movie_id=movie_id,
            )

        return BookingResult(
            status="ok",
            reply=(
                f"『{detail.title}』 상영관을 찾아드릴게요. "
                f"{REGION_ASK_MARKER}? 이동수단까지 알려주시면 더 정확해요 "
                f"(예: 강남 / 홍대입구역 차로 / 수원 도보)"
            ),
            card=card,
            booking=ChatBookingDto(
                status="need_region", region=None, theaters=[], booking_links=[]
            ),
            resolved_movie_id=movie_id,
        )

    async def _assist_with_region(
        self, *, title_term: str, region: str, trace_id: str
    ) -> BookingResult:
        region, radius_m, transport = _parse_region_transport(region)
        resolution = await resolve_movie_title(
            self._repository, message=title_term, entities=[title_term]
        )
        if resolution.status != "ok" or resolution.item is None:
            return BookingResult(
                status="not_found",
                reply="이어서 처리할 작품을 찾지 못했어요. 처음부터 다시 요청해 주시겠어요?",
                card=None,
                booking=None,
            )
        movie_id = int(resolution.item.id)
        detail = await self._movies.find_by_id(movie_id)
        if detail is None:
            return BookingResult(
                status="not_found",
                reply="작품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
                card=None,
                booking=None,
            )
        card = self._card(detail, movie_id)

        theaters = await self._theaters.search_theaters(region, radius_m=radius_m)
        if theaters is None:
            return BookingResult(
                status="ok",
                reply=(
                    f"'{region}' 지역을 찾지 못했어요. 동·역 이름이나 구 단위로 "
                    f"다시 알려주시겠어요? (『{detail.title}』 {REGION_ASK_MARKER}?)"
                ),
                card=card,
                booking=ChatBookingDto(
                    status="need_region", region=region, theaters=[], booking_links=[]
                ),
            )

        links = _booking_links(detail.title)
        cinema_showtimes = await self._fetch_lotte_showtimes(theaters, detail.title)
        basis = f"{transport} 기준 반경 {radius_m // 1000}km" if transport else "반경 10km"
        if not theaters:
            reply = (
                f"'{region}' 근처 {basis} 안에서 영화관을 찾지 못했어요. "
                + (
                    "차로 이동하신다면 '강남 차로'처럼 알려주시면 반경을 넓혀 다시 찾아드려요. "
                    if not transport
                    else ""
                )
                + "아래 체인 검색 링크에서 직접 확인해 보실 수도 있어요."
            )
        else:
            top = theaters[0]
            distance = f"약 {top.distance_m}m" if top.distance_m is not None else "가장 가까움"
            reply = (
                f"'{region}' 근처({basis}) 영화관 {len(theaters)}곳을 가까운 순으로 찾았어요. "
                f"가장 가까운 곳은 {top.name}({distance})이에요."
            )
            if cinema_showtimes:
                total_slots = sum(len(cs.slots) for cs in cinema_showtimes)
                reply += (
                    f" 롯데시네마 기준 오늘 상영 시간표 {total_slots}회차를 찾았어요."
                    " 다른 체인은 아래 예매 링크에서 확인해 주세요."
                )
            else:
                reply += (
                    " 상영 시간표와 예매는 각 체인 링크에서 확인해 주세요"
                    "(시간표는 극장 사정에 따라 달라져요)."
                )
        logger.info(
            "[BookingAssistService] trace=%s movie_id=%d region=%s theaters=%d showtimes=%d",
            trace_id,
            movie_id,
            region,
            len(theaters),
            len(cinema_showtimes),
        )
        return BookingResult(
            status="ok",
            reply=reply,
            card=card,
            booking=ChatBookingDto(
                status="showing",
                region=region,
                theaters=theaters,
                booking_links=links,
                showtimes=cinema_showtimes,
            ),
        )

    @staticmethod
    def _last_completed_week_date() -> str:
        """KOFIC 주간 박스오피스는 완결된 주만 데이터가 있다 — 주 중간 날짜로
        조회하면 빈 목록이 온다(2026-08-28 EC2 실측: 목요일 어제 날짜 → 0건).
        KST 기준 직전 일요일(항상 오늘보다 과거)을 쓴다."""
        today_kst = (datetime.now(UTC) + timedelta(hours=9)).date()
        last_sunday = today_kst - timedelta(days=today_kst.isoweekday())
        return last_sunday.strftime("%Y%m%d")

    async def _is_showing(self, title: str) -> bool:
        """KOFIC 주간 박스오피스 등재 여부로 근사 — 실패 시 상영 중으로 간주하지 않는다."""
        try:
            entries = await self._box_office.fetch_box_office(self._last_completed_week_date(), "0")
        except KoficAdapterError as e:
            logger.warning("[BookingAssistService] 박스오피스 조회 실패 — %s", e)
            return False
        wanted = _normalize(title)
        return any(
            wanted in _normalize(entry.title) or _normalize(entry.title) in wanted
            for entry in entries
            if entry.title
        )

    async def _fetch_lotte_showtimes(
        self, theaters: list[ChatTheaterDto], movie_title: str
    ) -> list[CinemaShowtimeDto]:
        """근처 영화관 중 롯데시네마에 대해 시간표를 조회한다(최대 2곳).

        카카오 결과에 롯데시네마가 없으면 첫 극장의 좌표로 최근접 롯데시네마를
        찾아 시간표를 조회한다(좌표 기반 폴백).
        """
        if self._showtimes is None:
            return []
        results: list[CinemaShowtimeDto] = []
        for theater in theaters:
            if "롯데" not in theater.name:
                continue
            try:
                cs = await self._showtimes.fetch_showtimes(theater.name, movie_title)
            except Exception:
                logger.warning(
                    "[BookingAssistService] 시간표 조회 예외 theater=%s",
                    theater.name,
                    exc_info=True,
                )
                continue
            if cs is not None and cs.slots:
                results.append(cs)
            if len(results) >= _MAX_SHOWTIME_CINEMAS:
                break

        if not results and theaters:
            anchor = next((t for t in theaters if t.lat and t.lng), None)
            if anchor is not None:
                try:
                    cs = await self._showtimes.fetch_nearest_showtimes(
                        anchor.lat,
                        anchor.lng,
                        movie_title,  # type: ignore[arg-type]
                    )
                except Exception:
                    logger.warning(
                        "[BookingAssistService] 최근접 시간표 조회 예외",
                        exc_info=True,
                    )
                    cs = None
                if cs is not None and cs.slots:
                    results.append(cs)

        return results

    @staticmethod
    def _card(detail: MovieDetailDto, movie_id: int) -> ChatRecommendationDto:
        platform = detail.platforms[0].provider if detail.platforms else None
        return ChatRecommendationDto(
            id=detail.slug,
            movie_id=movie_id,
            title=detail.title,
            year=str(detail.release_year or ""),
            poster=detail.poster_url or "",
            synopsis=detail.synopsis or "",
            platform=platform,
            hook="예매 도우미",
        )
