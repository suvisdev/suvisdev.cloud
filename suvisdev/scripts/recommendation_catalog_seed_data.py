"""Mova 추천 카탈로그 시드 상수 — `seed_mova_recommendation_catalog.py` 전용."""

from __future__ import annotations

from typing import TypedDict


class MoodTagDef(TypedDict):
    slug: str
    label: str
    description: str


class MovieSeedDef(TypedDict):
    slug: str
    title: str
    release_year: str
    genres: list[str]
    rating: float
    platform: str | None
    actors: list[str]
    directors: list[str]
    tag_slugs: list[str]


MOOD_TAG_DEFS: list[MoodTagDef] = [
    {
        "slug": "fun",
        "label": "재미있는",
        "description": "가볍게 보기 좋은, 웃음·속도감 있는 작품",
    },
    {
        "slug": "uplifting",
        "label": "신나는",
        "description": "에너지·텐션을 올려 주는 작품",
    },
    {
        "slug": "sad-comfort",
        "label": "우울할 때",
        "description": "우울한 기분에 맞춘 감상",
    },
    {
        "slug": "comfort",
        "label": "위로되는",
        "description": "마음이 편해지는, 잔잔한 위로",
    },
    {
        "slug": "romance-mood",
        "label": "로맨스",
        "description": "사랑·연애 분위기",
    },
    {
        "slug": "thriller-genre",
        "label": "스릴러",
        "description": "긴장·반전·스릴러 장르",
    },
    {
        "slug": "scary",
        "label": "무서운",
        "description": "공포·긴장감",
    },
    {
        "slug": "action-mood",
        "label": "액션",
        "description": "액션·스펙터클",
    },
    {
        "slug": "sf-mood",
        "label": "SF",
        "description": "공상과학·미래",
    },
    {
        "slug": "family",
        "label": "가족",
        "description": "가족과 함께 보기 좋은",
    },
    {
        "slug": "korean",
        "label": "한국",
        "description": "한국 영화·드라마 감성",
    },
    {
        "slug": "twist",
        "label": "반전",
        "description": "예측을 깨는 전개",
    },
]

MOOD_TAG_BY_SLUG: dict[str, MoodTagDef] = {t["slug"]: t for t in MOOD_TAG_DEFS}

MOVIE_SEEDS: list[MovieSeedDef] = [
    {
        "slug": "wonderfuls",
        "title": "원더풀스",
        "release_year": "2026",
        "genres": ["코미디", "액션", "드라마"],
        "rating": 3.0,
        "platform": "netflix",
        "actors": ["박은빈", "차은우", "김해숙", "이동휘"],
        "directors": [],
        "tag_slugs": ["fun", "uplifting", "korean", "family"],
    },
    {
        "slug": "interstellar",
        "title": "인터스텔라",
        "release_year": "2014",
        "genres": ["SF", "드라마", "모험"],
        "rating": 4.5,
        "platform": "netflix",
        "actors": ["매튜 맥커너히", "앤 해서웨이", "제시카 차스테인"],
        "directors": ["크리스토퍼 놀란"],
        "tag_slugs": ["sf-mood", "sad-comfort", "family", "uplifting"],
    },
    {
        "slug": "dune-2",
        "title": "듄: 파트2",
        "release_year": "2024",
        "genres": ["SF", "모험", "드라마"],
        "rating": 4.3,
        "platform": None,
        "actors": ["티모시 샬라메", "제니퍼 로렌스", "오스카 아이작"],
        "directors": ["드니 빌뇌브"],
        "tag_slugs": ["sf-mood", "action-mood", "uplifting"],
    },
    {
        "slug": "oppenheimer",
        "title": "오펜하이머",
        "release_year": "2023",
        "genres": ["드라마", "역사", "스릴러"],
        "rating": 4.4,
        "platform": None,
        "actors": ["킬리언 머피", "에밀리 블런트", "맷 데이먼"],
        "directors": ["크리스토퍼 놀란"],
        "tag_slugs": ["thriller-genre", "sad-comfort", "twist"],
    },
    {
        "slug": "parasite",
        "title": "기생충",
        "release_year": "2019",
        "genres": ["드라마", "스릴러", "코미디"],
        "rating": 4.6,
        "platform": "disney",
        "actors": ["송강호", "이선균", "조여정", "최우식"],
        "directors": ["봉준호"],
        "tag_slugs": ["thriller-genre", "fun", "twist", "korean"],
    },
    {
        "slug": "assassination",
        "title": "암살",
        "release_year": "2015",
        "genres": ["스릴러", "드라마", "역사", "액션"],
        "rating": 4.2,
        "platform": None,
        "actors": ["전지현", "이병헌", "하정우"],
        "directors": ["최동훈"],
        "tag_slugs": ["thriller-genre", "action-mood", "twist", "korean"],
    },
    {
        "slug": "blade-runner-2049",
        "title": "블레이드 러너 2049",
        "release_year": "2017",
        "genres": ["SF", "스릴러"],
        "rating": 4.1,
        "platform": None,
        "actors": ["라이언 고슬링", "해리슨 포드", "아나 드 아르마스"],
        "directors": ["드니 빌뇌브"],
        "tag_slugs": ["sf-mood", "thriller-genre", "scary"],
    },
    {
        "slug": "lalaland",
        "title": "라라랜드",
        "release_year": "2016",
        "genres": ["로맨스", "뮤지컬", "드라마"],
        "rating": 4.0,
        "platform": None,
        "actors": ["라이언 고슬링", "엠마 스톤"],
        "directors": ["데미언 셔젤"],
        "tag_slugs": ["romance-mood", "uplifting", "comfort"],
    },
    {
        "slug": "matrix",
        "title": "매트릭스",
        "release_year": "1999",
        "genres": ["SF", "액션"],
        "rating": 4.4,
        "platform": None,
        "actors": ["키아누 리브스", "로렌스 피시번", "캐리-앤 모스"],
        "directors": ["라나 워쇼스키", "릴리 워쇼스키"],
        "tag_slugs": ["sf-mood", "action-mood", "twist"],
    },
    {
        "slug": "inception",
        "title": "인셉션",
        "release_year": "2010",
        "genres": ["SF", "스릴러", "액션"],
        "rating": 4.5,
        "platform": "netflix",
        "actors": ["레오나르도 디카프리오", "조셉 고든-레빗", "엘리엇 페이지"],
        "directors": ["크리스토퍼 놀란"],
        "tag_slugs": ["sf-mood", "thriller-genre", "twist", "action-mood"],
    },
    {
        "slug": "dark-knight",
        "title": "다크 나이트",
        "release_year": "2008",
        "genres": ["액션", "드라마", "스릴러"],
        "rating": 4.7,
        "platform": "netflix",
        "actors": ["크리스찬 베일", "히스 레저", "아론 에크하트"],
        "directors": ["크리스토퍼 놀란"],
        "tag_slugs": ["thriller-genre", "action-mood", "twist"],
    },
    {
        "slug": "squid-game",
        "title": "오징어 게임",
        "release_year": "2021",
        "genres": ["스릴러", "드라마"],
        "rating": 4.2,
        "platform": "netflix",
        "actors": ["이정재", "박해수", "위하준"],
        "directors": ["황동혁"],
        "tag_slugs": ["thriller-genre", "scary", "twist", "korean"],
    },
]
