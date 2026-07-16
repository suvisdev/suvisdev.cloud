"""KOBIS(영화진흥위원회) Open API 클라이언트 — kobis_scraper.py와
kobis_boxoffice_title_source.py가 공유한다 (HTTP 호출 로직 중복 금지).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from ontology.app.ports.output.page_fetcher_port import PageFetcherPort

_KST = timezone(timedelta(hours=9))

_BOXOFFICE_URL = (
    "http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/"
    "searchDailyBoxOfficeList.json?key={key}&targetDt={target_dt}"
)
_MOVIE_DETAIL_URL = (
    "http://kobis.or.kr/kobisopenapi/webservice/rest/movie/"
    "searchMovieInfo.json?key={key}&movieCd={movie_cd}"
)


def yesterday_kst(*, now: datetime | None = None) -> str:
    """KST 기준 어제 날짜를 YYYYMMDD로 돌려준다. 테스트에서는 now를 주입해 고정한다."""
    current = now.astimezone(_KST) if now else datetime.now(_KST)
    return (current - timedelta(days=1)).strftime("%Y%m%d")


def fetch_daily_boxoffice(fetcher: PageFetcherPort, *, api_key: str, target_dt: str) -> list[dict]:
    url = _BOXOFFICE_URL.format(key=api_key, target_dt=target_dt)
    payload = json.loads(fetcher.fetch(url))
    return list(payload.get("boxOfficeResult", {}).get("dailyBoxOfficeList") or [])


def fetch_movie_detail(fetcher: PageFetcherPort, *, api_key: str, movie_cd: str) -> dict:
    url = _MOVIE_DETAIL_URL.format(key=api_key, movie_cd=movie_cd)
    payload = json.loads(fetcher.fetch(url))
    return dict(payload.get("movieInfoResult", {}).get("movieInfo") or {})
