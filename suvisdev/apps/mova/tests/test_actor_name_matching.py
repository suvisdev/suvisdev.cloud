"""발화 속 DB 배우 실명 매칭 테스트 (2026-09-22).

의도 추출의 `_guess_actors`는 "{이름} 배우|출연|이랑" 패턴만 잡아
"톰 크루즈 영화 추천"에서 배우를 놓치고(actors=[]), "톰 크루즈 배우 영화"는
공백 앞 한 토큰만 캡처해 `['크루즈']`로 줄어든다(프로덕션 실측). 배우를 놓치면
태그도 0건이라 RAG의 제목 유사 히트("정글 크루즈"·"크루즈 패밀리")만 후보에
남는 것이 무관 픽의 경로였다. keywords에 원문 전체가 들어오는 것을 이용해
DB 배우 실명을 찾아 쓴다.
"""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository


def _movie(mid: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=mid,
        title=f"영화{mid}",
        release_year=2020,
        rating=4.0,
        poster_url="",
        synopsis="",
        vote_count=100,
    )


def _repo() -> ChatPgRepository:
    return ChatPgRepository(session=MagicMock())


class ActorNamesInTextTests(IsolatedAsyncioTestCase):
    """_actor_names_in_text — 발화에 든 배우 실명 조회."""

    async def test_empty_keywords_skips_query(self) -> None:
        repo = _repo()
        repo._session.execute = AsyncMock()
        self.assertEqual(await repo._actor_names_in_text([]), [])
        repo._session.execute.assert_not_awaited()

    async def test_returns_matched_names(self) -> None:
        repo = _repo()
        repo._session.execute = AsyncMock(return_value=[("톰 크루즈",)])
        names = await repo._actor_names_in_text(["크루즈", "톰 크루즈 영화 추천"])
        self.assertEqual(names, ["톰 크루즈"])

    async def test_no_match_returns_empty(self) -> None:
        """배우가 없는 질의는 빈 리스트 — 오탐이 나면 엉뚱한 배우 영화가 후보에 든다."""
        repo = _repo()
        repo._session.execute = AsyncMock(return_value=[])
        self.assertEqual(await repo._actor_names_in_text(["비 오는 날 보기 좋은 영화"]), [])


class SearchTagCatalogActorPriorityTests(IsolatedAsyncioTestCase):
    """search_tag_catalog — DB 실명이 정규식 추측보다 우선한다."""

    async def test_db_name_preferred_over_guessed_surname(self) -> None:
        """정규식이 성만 잡아 넘긴 "크루즈"보다 DB의 "톰 크루즈"를 쓴다 —
        `%크루즈%`로 검색하면 테리·레이먼드 크루즈까지 섞인다."""
        repo = _repo()
        repo._movie_ids_by_tags = AsyncMock(return_value=(set(), set()))
        repo._actor_names_in_text = AsyncMock(return_value=["톰 크루즈"])
        repo._movie_ids_by_actors = AsyncMock(return_value={7})
        repo._movies_by_ids = AsyncMock(return_value=[_movie(7)])
        repo._genres_for = AsyncMock(return_value={})

        await repo.search_tag_catalog(["크루즈", "톰 크루즈 영화 추천"], 16, actor_names=["크루즈"])
        repo._movie_ids_by_actors.assert_awaited_once_with(["톰 크루즈"])

    async def test_falls_back_to_given_actor_names(self) -> None:
        """DB 실명이 안 잡히면 기존 동작(호출부가 준 actor_names) 그대로."""
        repo = _repo()
        repo._movie_ids_by_tags = AsyncMock(return_value=(set(), set()))
        repo._actor_names_in_text = AsyncMock(return_value=[])
        repo._movie_ids_by_actors = AsyncMock(return_value={3})
        repo._movies_by_ids = AsyncMock(return_value=[_movie(3)])
        repo._genres_for = AsyncMock(return_value={})

        await repo.search_tag_catalog(["액션"], 16, actor_names=["마동석"])
        repo._movie_ids_by_actors.assert_awaited_once_with(["마동석"])

    async def test_db_actor_wins_over_tag_union(self) -> None:
        """태그가 대량 매칭돼도 DB 실명이 잡히면 배우 조건을 유지한다.

        "송강호 나오는 영화"의 keywords는 `['송강호','나오는','영화',...]`이고
        "영화"가 tags.label에 광범위하게 걸린다. 교집합이 비었다고 합집합으로
        완화하면 무관 영화가 후보를 채워 LLM이 0편을 냈다(2026-09-22 실측 6/6).
        """
        repo = _repo()
        repo._movie_ids_by_tags = AsyncMock(return_value=({101, 102, 103}, set()))
        repo._actor_names_in_text = AsyncMock(return_value=["송강호"])
        repo._movie_ids_by_actors = AsyncMock(return_value={7, 8})
        repo._movies_by_ids = AsyncMock(return_value=[_movie(7), _movie(8)])
        repo._genres_for = AsyncMock(return_value={})

        items = await repo.search_tag_catalog(["송강호", "나오는", "영화"], 16)

        self.assertTrue(all(i.match_type == "actor" for i in items))
        # 합집합이 아니라 배우 집합만 조회해야 한다
        self.assertEqual(repo._movies_by_ids.await_args.args[0], {7, 8})
