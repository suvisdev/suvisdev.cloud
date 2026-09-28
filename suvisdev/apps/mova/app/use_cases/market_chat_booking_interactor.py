"""booking 트랙 — "호프 예매하고 싶어" 류 질의에 상영 여부·근처 영화관을 안내한다.

Phase 1(설계서 §5): 상영 중 판정은 KOFIC 주간 박스오피스 등재 여부로 근사하고,
상영시간표는 직접 보여주지 않는다 — 모르는 것은 체인 검색 딥링크로 위임(정직성
규칙). 지역은 사용자 발화의 지역명으로 받고, 없으면 되묻는다(슬롯 필링).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.adapter.outbound.http.kofic_adapter import KoficAdapterError
from mova.app.dtos.market_box_office_dto import BoxOfficeEntryDto
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
from mova.app.use_cases.market_chat_title_resolver import TitleResolution, resolve_movie_title
from mova.domain.services.showing_title_policy import prefer_showing_year
from mova.domain.value_objects.movie_title import MovieTitle

logger = logging.getLogger(__name__)

# 지역 되묻기 응답의 결정론 마커 — 다음 턴을 지역 입력으로 이어 받는 근거.
# 제목은 『』로 감싸 넣어 다음 턴에서 그대로 복원한다(비로그인도 history만으로 동작).
REGION_ASK_MARKER = "어느 지역에서 보실 계획인가요"

# 제목 없는 탐색형 예매 질의("지금 예매할 수 있는 영화 뭐있어") 감지 —
# 이걸 title resolver로 보내면 "영화" 같은 일반어가 제목 퍼지 매칭돼
# 무관 후보로 되묻는 오류가 났다(2026-09-02 실사용). 결정론 패턴으로
# 먼저 갈라 상영작 목록(박스오피스 근사)으로 답한다.
# "바로 예매할 수 있는 영화 찾아줘"(2026-09-22 실사용)는 '뭐있어'가 없어 이 패턴을
# 비껴가 '바로'가 제목 퍼지 매칭됐다(아바타·바튼 아카데미). '예매할 수 있는 영화/작품'
# 자체를 탐색 신호로 본다 — '영화관'은 제외해 "호프 예매할 수 있는 영화관"은 제목 경로.
_DISCOVERY_PATTERN = re.compile(
    r"뭐\s*(?:가\s*)?(?:있|볼|봐|나왔)|무슨\s*영화|어떤\s*(?:영화|작품)|상영작|상영\s*중인"
    r"|예매\s*(?:할\s*수\s*있는|가능한)\s*(?:영화|작품)(?!관)"
)
_DISCOVERY_LIST_LIMIT = 8

# 지역-선행 발화("군자쪽에 예매할 시간 있어?")의 지명 신호 — title resolver가
# 실패했을 때만 본다. 지명이 제목 후보로 흘러가 자모 퍼지 매칭되면
# "군자→군체/감자" 같은 무관 후보 되묻기가 났다(2026-09-11 실사용).
# 고정밀 접미(쪽/역/근처/주변/인근)만 신호로 삼는다 — 동·구 단독은 제목
# 오탐 여지가 있어 제외. 오탐해도 극장 검색이 0건으로 끝날 뿐이라 안전하다.
_REGION_SUFFIX_EXCLUDE = frozenset({"이", "그", "저", "양", "한", "어느", "오른", "왼", "반대"})
_REGION_JJOK = re.compile(r"([가-힣A-Za-z0-9]{1,12})\s*쪽")
_REGION_STATION = re.compile(r"([가-힣A-Za-z0-9]{2,12})역(?=[\s에으로은는이가,.!?~]|$)")
_REGION_NEAR = re.compile(r"([가-힣A-Za-z0-9]{2,12})\s*(?:근처|주변|인근)")

# 지역 되묻기 답변("군자역 근처")은 message를 그대로 슬롯에 넣기 때문에 꼬리말이
# 지오코딩까지 흘러간다 — 2026-09-22 실측: 카카오가 '군자역 근처'는 None,
# '군자역'은 정상 반환. 역·동 이름은 건드리지 않고 꼬리말만 떼어 낸다.
_REGION_TAIL = re.compile(r"\s*(?:근처|주변|인근)\s*$")


def _extract_region_signal(message: str) -> str | None:
    m = _REGION_JJOK.search(message)
    if m and m.group(1) not in _REGION_SUFFIX_EXCLUDE:
        return m.group(1)
    m = _REGION_STATION.search(message)
    if m:
        return m.group(1)
    m = _REGION_NEAR.search(message)
    if m:
        return m.group(1)
    return None


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


_DATE_MD = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_DATE_D = re.compile(r"(?<![\d월])(\d{1,2})\s*일(?:자|에|날)?(?!\s*[월간\d])")
_DATE_WORDS = {"오늘": 0, "내일": 1, "모레": 2}


def _kst_today() -> datetime:
    return datetime.now(UTC) + timedelta(hours=9)


def parse_showtime_date(message: str, *, today: datetime | None = None) -> str | None:
    """발화의 날짜 표현 → "YYYY-MM-DD"(KST). 오늘/내일/모레, "9월 30일", "30일(자)". 없으면 None.

    예매 트랙에 날짜 슬롯이 없어 "9월 30일자로 찾아줘"가 오늘 시간표를 다시 주거나 제목을
    되묻던 것(2026-09-28 실사용) 대응. 지난 날짜(같은 달 앞 날)는 다음 달로 본다.
    """
    base = today or _kst_today()
    for word, delta in _DATE_WORDS.items():
        if word in message:
            return (base + timedelta(days=delta)).strftime("%Y-%m-%d")
    m = _DATE_MD.search(message)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = base.year + (
            1 if (month, day) < (base.month, base.day) and month < base.month else 0
        )
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None
    m = _DATE_D.search(message)
    if m:
        day = int(m.group(1))
        month, year = base.month, base.year
        if day < base.day:
            month += 1
            if month > 12:
                month, year = 1, year + 1
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _date_label(date: str | None) -> str:
    if not date:
        return "오늘"
    base = _kst_today()
    if date == base.strftime("%Y-%m-%d"):
        return "오늘"
    if date == (base + timedelta(days=1)).strftime("%Y-%m-%d"):
        return "내일"
    d = datetime.strptime(date, "%Y-%m-%d")
    return f"{d.month}월 {d.day}일"


_REGION_IN_REPLY = re.compile(r"'([^']{1,20})' (?:근처|전역)")

# 광역(시·도) 요청 — "서울 전체로 찾아줘"는 좌표 하나 반경 검색이 아니라 그 광역의 상영관 전부를
# 봐야 한다(2026-09-28 사용자: 예전엔 "서울"이 시청 좌표 반경 10km 5곳으로 좁혀졌다).
_WIDE_AREAS = frozenset(
    {"서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "제주"}
    | {"충북", "충남", "전북", "전남", "경북", "경남", "충청", "전라", "경상"}
)
_WIDE_NOISE = re.compile(
    r"(특별자치시|특별자치도|특별시|광역시|전체|전역|어디서든|어디든|지역|권|쪽|\s)"
)
_MAX_WIDE_CINEMAS = 5


def wide_area(region: str | None) -> str | None:
    """ "서울", "서울 전체", "서울특별시", "경기도" → 광역 이름. 역·동·구 같은 지점이면 None."""
    if not region:
        return None
    name = _WIDE_NOISE.sub("", region)
    if name.endswith("도") and name[:-1] in _WIDE_AREAS:
        name = name[:-1]
    return name if name in _WIDE_AREAS else None


def _drop_past_slots(showing: list[CinemaShowtimeDto], date: str | None) -> list[CinemaShowtimeDto]:
    """오늘 조회면 이미 지난 회차를 빼고, 남은 회차가 없는 극장은 제외, 남은 첫 회차 순으로 정렬.
    (2026-09-28 실측: 12:30 지난 회차가 "이른 회차 순" 맨 앞에 왔다.)"""
    now = _kst_today()
    if date and date != now.strftime("%Y-%m-%d"):
        return showing
    cutoff = now.strftime("%H:%M")
    kept = []
    for cs in showing:
        slots = [sl for sl in cs.slots if sl.start_time >= cutoff]
        if slots:
            kept.append(replace(cs, slots=slots))
    kept.sort(key=lambda cs: cs.slots[0].start_time)
    return kept


def _upcoming_first(showing: list[CinemaShowtimeDto], date: str | None) -> tuple[str, str] | None:
    """(가장 이른 남은 회차 시각, 극장명). 오늘이면 이미 지난 회차는 뺀다."""
    now = _kst_today()
    cutoff = now.strftime("%H:%M") if (not date or date == now.strftime("%Y-%m-%d")) else ""
    cands = [
        (s.start_time, cs.cinema_name) for cs in showing for s in cs.slots if s.start_time >= cutoff
    ]
    return min(cands) if cands else None


def region_from_history(history: list[dict[str, str]] | None) -> str | None:
    """직전 assistant 예매 응답("'서울' 근처(…) 영화관 …")에서 지역을 복원한다."""
    for msg in reversed(history or []):
        if msg.get("role") != "assistant":
            continue
        m = _REGION_IN_REPLY.search(msg.get("content") or "")
        return m.group(1) if m else None
    return None


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
    region = _REGION_TAIL.sub("", region).strip() or region
    return region, radius, label


# OTT 검색 딥링크 — TMDB가 주는 제공자 URL은 전부 TMDB 시청처 페이지 하나라, 서비스별 검색으로 보낸다
# (2026-09-28 사용자: "상영 안 하면 어디서 볼 수 있는지 링크로"). 키는 movies.platforms[].provider.
_OTT_LINKS: dict[str, tuple[str, str]] = {
    "netflix": ("넷플릭스", "https://www.netflix.com/search?q={q}"),
    "netflixstandardwithads": ("넷플릭스", "https://www.netflix.com/search?q={q}"),
    "disneyplus": ("디즈니+", "https://www.disneyplus.com/ko-kr/search?q={q}"),
    "wavve": ("웨이브", "https://www.wavve.com/search?searchWord={q}"),
    "watcha": ("왓챠", "https://watcha.com/search?query={q}"),
    "tving": ("티빙", "https://www.tving.com/search?keyword={q}"),
    "googleplaymovies": ("구글 플레이", "https://play.google.com/store/search?q={q}&c=movies"),
    "appletv": ("Apple TV", "https://tv.apple.com/kr/search?term={q}"),
    "amazonprimevideo": ("프라임 비디오", "https://www.primevideo.com/search?phrase={q}"),
}


def _watch_links(detail: MovieDetailDto) -> list[ChatBookingLinkDto]:
    """상영작이 아닐 때 볼 수 있는 곳 — 알려진 OTT는 검색 링크, 끝에 TMDB 시청처 페이지."""
    q = quote(detail.title)
    links: list[ChatBookingLinkDto] = []
    seen: set[str] = set()
    tmdb_url = ""
    for p in detail.platforms:
        tmdb_url = tmdb_url or (p.url or "")
        known = _OTT_LINKS.get((p.provider or "").lower())
        if known and known[0] not in seen:
            seen.add(known[0])
            links.append(ChatBookingLinkDto(chain=known[0], url=known[1].format(q=q)))
    if tmdb_url:
        links.append(ChatBookingLinkDto(chain="전체 시청처(TMDB)", url=tmdb_url))
    return links


def _booking_links(title: str) -> list[ChatBookingLinkDto]:
    q = quote(title)
    return [
        ChatBookingLinkDto(chain=chain, url=url.format(q=q))
        for chain, url in _BOOKING_LINK_TEMPLATES
    ]


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

    async def assist_slots(
        self,
        *,
        message: str,
        title_text: str | None,
        verified_title: str | None,
        region: str | None,
        trace_id: str,
        history: list[dict[str, str]] | None = None,
    ) -> BookingResult:
        """오케스트레이터(2026-09-27)가 넘긴 슬롯으로 실행하는 얇은 경로.

        - 작품 확정 + 지역 → 곧장 지역 검색(되묻기 없이)
        - 작품(확정 또는 텍스트)만 → 기존 해석·상영 판정·지역 되묻기
        - 지역만 → 직전 대화의 작품이 있으면 그걸로, 없으면 제목을 묻는다
        - 아무것도 없음 → 탐색형이면 상영작 목록, 아니면 기존 경로
        """
        title = verified_title or title_text
        date = parse_showtime_date(message)
        if title and region:
            return await self._assist_with_region(
                title_term=title, region=region, trace_id=trace_id, date=date
            )
        if title:
            return await self.assist(
                message=title, entities=[title], trace_id=trace_id, history=history
            )
        if region:
            context = await self._context_movie_from_history(history)
            if context is not None:
                return await self._assist_with_region(
                    title_term=context.title, region=region, trace_id=trace_id, date=date
                )
            return BookingResult(
                status="not_found",
                reply=(
                    f"'{region}' 근처 상영관을 찾아드릴게요. "
                    "어떤 작품을 예매하실지 제목을 알려주시겠어요?"
                ),
                card=None,
                booking=None,
            )
        if date:
            followed = await self._follow_up_by_date(message, history, trace_id, date)
            if followed is not None:
                return followed
        if _DISCOVERY_PATTERN.search(message):
            return await self._discovery_reply(trace_id)
        return await self.assist(message=message, entities=[], trace_id=trace_id, history=history)

    async def _follow_up_by_date(
        self,
        message: str,
        history: list[dict[str, str]] | None,
        trace_id: str,
        date: str,
    ) -> BookingResult | None:
        """ "9월 30일자로 찾아줘"처럼 날짜만 바뀐 후속 — 직전 예매 응답의 작품·지역을 그대로 잇는다.
        작품이 없으면 None(기존 경로), 지역이 없으면 지역 되묻기."""
        context = await self._context_movie_from_history(history)
        if context is None:
            return None
        region = _extract_region_signal(message) or region_from_history(history)
        if region:
            logger.info(
                "[BookingAssist] trace=%s 날짜 후속 title=%s region=%s date=%s",
                trace_id,
                context.title,
                region,
                date,
            )
            return await self._assist_with_region(
                title_term=context.title, region=region, trace_id=trace_id, date=date
            )
        return BookingResult(
            status="ok",
            reply=f"『{context.title}』 {_date_label(date)} 상영관을 찾아드릴게요. {REGION_ASK_MARKER}?",
            card=None,
            booking=ChatBookingDto(
                status="need_region", region=None, theaters=[], booking_links=[]
            ),
        )

    async def assist(
        self,
        *,
        message: str,
        entities: list[str],
        trace_id: str,
        pending_title: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> BookingResult:
        if pending_title:
            return await self._assist_with_region(
                title_term=pending_title, region=message.strip(), trace_id=trace_id
            )

        if _DISCOVERY_PATTERN.search(message):
            return await self._discovery_reply(trace_id)

        resolution = await resolve_movie_title(self._repository, message=message, entities=entities)
        resolution = await self._prefer_showing_duplicate(resolution)

        # 지역-선행 이어받기(2026-09-11): 발화에서 제목이 확정되지 않았고 지명
        # 신호가 있으면, 직전 assistant 응답(평가·추천 문장)에서 방금 다루던
        # 영화를 역조회해 곧장 지역 검색으로 잇는다 — "옵세션 평가 →
        # 군자쪽에 예매" 흐름. 기존 pending_title 마커는 "제목 먼저 → 지역
        # 되묻기" 순서만 지원해 이 역순이 지명 퍼지 매칭 되묻기로 새고 있었다.
        if resolution.status != "ok":
            date = parse_showtime_date(message)
            region = _extract_region_signal(message)
            if region:
                context = await self._context_movie_from_history(history)
                if context is not None:
                    logger.info(
                        "[BookingAssist] trace=%s 지역-선행 이어받기 title=%s region=%s",
                        trace_id,
                        context.title,
                        region,
                    )
                    return await self._assist_with_region(
                        title_term=context.title, region=region, trace_id=trace_id, date=date
                    )
                # 맥락 영화도 없으면 지명을 제목 후보로 되묻지 않고 제목을 묻는다.
                return BookingResult(
                    status="not_found",
                    reply=(
                        f"'{region}' 근처 상영관을 찾아드릴게요. "
                        "어떤 작품을 예매하실지 제목을 알려주시겠어요?"
                    ),
                    card=None,
                    booking=None,
                )
            if date:
                followed = await self._follow_up_by_date(message, history, trace_id, date)
                if followed is not None:
                    return followed

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
            watch = _watch_links(detail)
            names = [link.chain for link in watch if link.chain != "전체 시청처(TMDB)"]
            ott_line = (
                f" 대신 {', '.join(names)}에서 감상하실 수 있어요. 아래 링크로 바로 찾아보세요."
                if names
                else (
                    " 아래 링크에서 시청처를 확인해 보세요."
                    if watch
                    else " OTT 공개 정보도 아직 없어요."
                )
            )
            return BookingResult(
                status="ok",
                reply=(
                    f"『{detail.title}』은(는) 최근 주간 박스오피스 기준으로 현재 상영작에서 "
                    f"확인되지 않아요(소규모 상영은 놓칠 수 있어요).{ott_line}"
                ),
                card=card,
                booking=ChatBookingDto(
                    status="not_showing",
                    region=None,
                    theaters=[],
                    booking_links=[],
                    watch_links=watch,
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

    async def _discovery_reply(self, trace_id: str) -> BookingResult:
        """제목 없는 탐색형 질의 — 주간 박스오피스 상영작을 나열하고 작품 선택을
        유도한다. 정직성 규칙: 출처(박스오피스 근사)를 명시한다."""
        try:
            entries = await self._box_office.fetch_box_office(self._last_completed_week_date(), "0")
        except KoficAdapterError as e:
            logger.warning(
                "[BookingAssistService] trace=%s 상영작 목록 조회 실패 — %s", trace_id, e
            )
            entries = []
        titles = [entry.title for entry in entries if entry.title][:_DISCOVERY_LIST_LIMIT]
        if not titles:
            reply = (
                "지금 상영작 목록을 불러오지 못했어요. 예매하실 작품 제목을 "
                "알려주시면 상영 여부부터 확인해 드릴게요."
            )
        else:
            reply = (
                f"최근 주간 박스오피스 기준 현재 상영작이에요: {' / '.join(titles)}. "
                "이 중 예매하실 작품을 알려주시면 근처 상영관을 찾아드릴게요."
            )
        logger.info(
            "[BookingAssistService] trace=%s 탐색형 예매 질의 → 상영작 %d편 안내",
            trace_id,
            len(titles),
        )
        return BookingResult(status="ok", reply=reply, card=None, booking=None)

    async def _context_movie_from_history(
        self, history: list[dict[str, str]] | None
    ) -> MovaSearchItemSchema | None:
        """직전 assistant 응답에서 방금 다루던 영화를 역조회한다.

        evaluate 후속 이어받기(`_is_bare_eval_followup`)와 같은 근거 —
        직전 응답 하나만 본다(더 거슬러 올라가면 엉뚱한 작품을 잇는다).
        """
        if not history:
            return None
        for idx in range(len(history) - 1, -1, -1):
            msg = history[idx]
            if msg.get("role") != "assistant":
                continue
            content = (msg.get("content") or "").strip()
            if not content:
                return None
            found = await self._repository.find_movie_titled_in_text(content)
            if found is not None:
                return found
            # 평가 응답은 줄거리만 담고 제목을 안 쓴다("음반점 직원 베어가…") — 그
            # 응답을 부른 user 발화("옵세션 어때")에 제목이 있다(2026-09-22 실사용).
            for prev in range(idx - 1, -1, -1):
                if history[prev].get("role") == "user":
                    user_text = (history[prev].get("content") or "").strip()
                    return (
                        await self._repository.find_movie_titled_in_text(user_text)
                        if user_text
                        else None
                    )
            return None
        return None

    async def _assist_with_region(
        self, *, title_term: str, region: str, trace_id: str, date: str | None = None
    ) -> BookingResult:
        region, radius_m, transport = _parse_region_transport(region)
        resolution = await resolve_movie_title(
            self._repository, message=title_term, entities=[title_term]
        )
        resolution = await self._prefer_showing_duplicate(resolution)
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

        area = wide_area(region)
        if area and self._showtimes is not None:
            return await self._wide_area_reply(
                detail=detail, card=card, area=area, date=date, trace_id=trace_id
            )

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
        cinema_showtimes = await self._fetch_lotte_showtimes(theaters, detail.title, date=date)
        basis = f"{transport} 기준 반경 {radius_m // 1000}km" if transport else "반경 10km"
        # 응답에 『제목』을 남겨 다음 턴("9월 30일자로", "강남으로")이 작품을 되찾게 한다
        # (2026-09-28 실사용: 제목 없는 응답 뒤 날짜 후속이 "제목을 알려주세요"로 새던 문제).
        if not theaters:
            reply = (
                f"『{detail.title}』 — '{region}' 근처 {basis} 안에서 영화관을 찾지 못했어요. "
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
                f"『{detail.title}』 — '{region}' 근처({basis}) 영화관 {len(theaters)}곳을 가까운 순으로 "
                f"찾았어요. 가장 가까운 곳은 {top.name}({distance})이에요."
            )
            if cinema_showtimes:
                total_slots = sum(len(cs.slots) for cs in cinema_showtimes)
                reply += (
                    f" 롯데시네마 기준 {_date_label(date)} 상영 시간표 {total_slots}회차를 찾았어요."
                    " 다른 체인은 아래 예매 링크에서 확인해 주세요."
                )
            else:
                # 롯데는 보통 이틀치 정도만 회차를 연다 — 먼 날짜는 "없다"가 아니라 "아직 안 열렸다"일
                # 수 있다(2026-09-28 실측: 9/30 조회가 전 작품 0건).
                far = bool(date) and date > (_kst_today() + timedelta(days=1)).strftime("%Y-%m-%d")
                reply += (
                    f" 롯데시네마 {_date_label(date)} 시간표엔 이 작품이 없었어요"
                    + ("(그날 예매 일정이 아직 안 열렸을 수 있어요). " if far else ". ")
                    + "상영 시간표와 예매는 각 체인 링크에서 확인해 주세요"
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

    async def _wide_area_reply(
        self,
        *,
        detail: MovieDetailDto,
        card: ChatRecommendationDto,
        area: str,
        date: str | None,
        trace_id: str,
    ) -> BookingResult:
        """광역 요청 — 그 광역의 롯데시네마 전부에서 이 작품 상영관만 모아 이른 회차 순으로 답한다.
        CGV·메가박스는 시간표를 가져올 수 없어 링크로 넘긴다."""
        assert self._showtimes is not None
        try:
            showing = await self._showtimes.find_showing_cinemas(area, detail.title, date=date)
        except Exception:
            logger.warning(
                "[BookingAssistService] 광역 시간표 조회 예외 area=%s", area, exc_info=True
            )
            showing = []
        showing = _drop_past_slots(showing, date)
        label = _date_label(date)
        links = _booking_links(detail.title)
        if showing:
            upcoming = _upcoming_first(showing, date)
            reply = (
                f"『{detail.title}』 — '{area}' 전역 롯데시네마 중 {label} 상영관 {len(showing)}곳을 "
                f"찾았어요."
                + (f" 가장 이른 회차는 {upcoming[1]} {upcoming[0]}이에요." if upcoming else "")
                + (
                    f" 이른 회차 순으로 {_MAX_WIDE_CINEMAS}곳만 보여드려요."
                    if len(showing) > _MAX_WIDE_CINEMAS
                    else ""
                )
                + " CGV·메가박스는 아래 예매 링크에서 확인해 주세요."
            )
        else:
            far = bool(date) and date > (_kst_today() + timedelta(days=1)).strftime("%Y-%m-%d")
            reply = (
                f"『{detail.title}』 — '{area}' 전역 롯데시네마 {label} 시간표엔 이 작품이 없었어요"
                + ("(그날 예매 일정이 아직 안 열렸을 수 있어요)." if far else ".")
                + " CGV·메가박스는 아래 예매 링크에서 확인해 주세요."
            )
        logger.info(
            "[BookingAssistService] trace=%s 광역 area=%s title=%s showing=%d date=%s",
            trace_id,
            area,
            detail.title,
            len(showing),
            date,
        )
        return BookingResult(
            status="ok",
            reply=reply,
            card=card,
            booking=ChatBookingDto(
                status="showing",
                region=area,
                theaters=[],
                booking_links=links,
                showtimes=showing[:_MAX_WIDE_CINEMAS],
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

    async def _box_office_entries(self) -> list[BoxOfficeEntryDto]:
        try:
            return await self._box_office.fetch_box_office(self._last_completed_week_date(), "0")
        except KoficAdapterError as e:
            logger.warning("[BookingAssistService] 박스오피스 조회 실패 — %s", e)
            return []

    async def _is_showing(self, title: str) -> bool:
        """KOFIC 주간 박스오피스 등재 여부로 근사 — 실패 시 상영 중으로 간주하지 않는다."""
        wanted = MovieTitle(title)
        return any(
            wanted.overlaps(entry.title)
            for entry in await self._box_office_entries()
            if entry.title
        )

    async def _prefer_showing_duplicate(self, resolution: TitleResolution) -> TitleResolution:
        """같은 제목이 여러 편이면(인턴 2015·2026) 지금 상영 중인 쪽을 고른다.

        제목 해석기는 평점·최신 정렬의 첫 항목을 주는데, 2026-09-27 실사용에서 예매 요청에
        2015년작 인턴 카드가 나갔다. 박스오피스 개봉 연도(openDt)와 맞는 후보가 있으면
        그쪽, 개봉 연도를 모르면 가장 최신작. 동명 후보가 하나뿐이면 그대로 둔다.
        """
        item = resolution.item
        if resolution.status != "ok" or item is None:
            return resolution
        wanted = MovieTitle(item.title)
        same = [c for c in resolution.candidates if wanted.equals(c.title)]
        if len(same) < 2:
            return resolution
        entries = [e for e in await self._box_office_entries() if wanted.equals(e.title)]
        if not entries:
            return resolution
        open_years = {e.open_year for e in entries if isinstance(e.open_year, int)}
        year = prefer_showing_year([c.year for c in same], open_years)
        pick = next((c for c in same if c.year == year), same[0])
        if pick.id == item.id:
            return resolution
        logger.info(
            "[BookingAssist] 동명 작품 중 상영작 선택 title=%s %s→%s",
            item.title,
            item.year,
            pick.year,
        )
        return TitleResolution(status="ok", item=pick, candidates=resolution.candidates)

    async def showing_titles(self) -> list[str]:
        """잡담 트랙 근거용 — 지금 상영 중인 작품 "제목(개봉연도)" 목록(주간 박스오피스)."""
        out: list[str] = []
        for e in await self._box_office_entries():
            if not e.title:
                continue
            out.append(f"{e.title}({e.open_year})" if isinstance(e.open_year, int) else e.title)
        return out

    async def _fetch_lotte_showtimes(
        self, theaters: list[ChatTheaterDto], movie_title: str, *, date: str | None = None
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
                cs = await self._showtimes.fetch_showtimes(theater.name, movie_title, date=date)
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
            if anchor is not None and anchor.lat is not None and anchor.lng is not None:
                try:
                    cs = await self._showtimes.fetch_nearest_showtimes(
                        anchor.lat,
                        anchor.lng,
                        movie_title,
                        date=date,
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
