"""다중 장르 AND 우선 검색 테스트 (2026-09-02).

"SF 드라마"처럼 태그 여러 개를 함께 말한 질의에서, 합집합(OR) 단독으로
평점순 limit을 자르면 두 태그를 다 가진 영화가 통째로 밀리는 결함의 수정:
교집합 영화를 먼저 조회해 앞에 두고 남는 자리만 합집합으로 보충한다.
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


class MovieIdsByTagsGroupingTests(IsolatedAsyncioTestCase):
    """_movie_ids_by_tags — (합집합, 교집합) 계산."""

    async def test_intersection_of_two_keywords(self) -> None:
        repo = _repo()
        repo._session.execute = AsyncMock(
            return_value=[(1, "SF"), (2, "SF"), (2, "드라마"), (3, "드라마")]
        )
        union, inter = await repo._movie_ids_by_tags(["SF", "드라마"])
        self.assertEqual(union, {1, 2, 3})
        self.assertEqual(inter, {2})

    async def test_zero_match_keyword_excluded_from_intersection(self) -> None:
        """ "영화" 같은 비태그 어휘는 교집합 판정에서 빠진다 — 매칭된 키워드가
        1개뿐이면 교집합은 빈 set(우선순위 신호 없음)."""
        repo = _repo()
        repo._session.execute = AsyncMock(return_value=[(1, "SF"), (2, "SF")])
        union, inter = await repo._movie_ids_by_tags(["SF", "영화"])
        self.assertEqual(union, {1, 2})
        self.assertEqual(inter, set())

    async def test_single_keyword_no_intersection(self) -> None:
        repo = _repo()
        repo._session.execute = AsyncMock(return_value=[(1, "좀비"), (2, "좀비물")])
        union, inter = await repo._movie_ids_by_tags(["좀비"])
        self.assertEqual(union, {1, 2})
        self.assertEqual(inter, set())

    async def test_empty_keywords(self) -> None:
        repo = _repo()
        union, inter = await repo._movie_ids_by_tags([])
        self.assertEqual((union, inter), (set(), set()))


class SearchTagCatalogAndPriorityTests(IsolatedAsyncioTestCase):
    """search_tag_catalog — 교집합 우선 + 합집합 보충 오케스트레이션."""

    def _wire(
        self,
        repo: ChatPgRepository,
        *,
        tags: tuple[set[int], set[int]],
        actors: set[int] = frozenset(),
        movies_side_effect: list[list[SimpleNamespace]],
    ) -> None:
        repo._movie_ids_by_titles = AsyncMock(return_value=set())  # type: ignore[method-assign]
        repo._movie_ids_by_tags = AsyncMock(return_value=tags)  # type: ignore[method-assign]
        # 발화 속 DB 배우 실명 조회(2026-09-22 추가) — 여기선 매칭 없음으로 두어
        # 기존 동작(호출부가 준 actor_names 사용)을 검증한다.
        repo._actor_names_in_text = AsyncMock(return_value=[])  # type: ignore[method-assign]
        # 카탈로그 장르 조회(2026-09-22 추가) — 오케스트레이션 검증이 목적이라 빈 결과로 둔다
        repo._genres_for = AsyncMock(return_value={})  # type: ignore[method-assign]
        repo._movie_ids_by_actors = AsyncMock(return_value=set(actors))  # type: ignore[method-assign]
        repo._movies_by_ids = AsyncMock(side_effect=movies_side_effect)  # type: ignore[method-assign]

    async def test_intersection_first_then_union_backfill(self) -> None:
        repo = _repo()
        self._wire(
            repo,
            tags=({1, 2, 3, 4}, {3}),
            movies_side_effect=[[_movie(3)], [_movie(1), _movie(2)]],
        )
        items = await repo.search_tag_catalog(["SF", "드라마"], 16)

        self.assertEqual([i.id for i in items], ["3", "1", "2"])
        self.assertTrue(all(i.match_type == "keyword" for i in items))
        calls = repo._movies_by_ids.await_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[0], {3})  # 교집합 먼저
        self.assertEqual(calls[0].args[1], 16)
        self.assertEqual(calls[1].args[0], {1, 2, 4})  # 나머지 합집합 보충
        self.assertEqual(calls[1].args[1], 15)  # 남은 자리만

    async def test_no_intersection_keeps_single_union_query(self) -> None:
        """교집합 신호가 없으면(순수 mood 확장 등) 현행 합집합 1회 조회 유지."""
        repo = _repo()
        self._wire(
            repo,
            tags=({1, 2}, set()),
            movies_side_effect=[[_movie(1), _movie(2)]],
        )
        items = await repo.search_tag_catalog(["오싹오싹한"], 16)

        self.assertEqual([i.id for i in items], ["1", "2"])
        self.assertEqual(len(repo._movies_by_ids.await_args_list), 1)

    async def test_intersection_equal_to_union_skips_priority(self) -> None:
        """모든 영화가 전 키워드 매칭이면 재정렬할 게 없다 — 1회 조회."""
        repo = _repo()
        self._wire(
            repo,
            tags=({1, 2}, {1, 2}),
            movies_side_effect=[[_movie(1), _movie(2)]],
        )
        await repo.search_tag_catalog(["SF", "드라마"], 16)
        self.assertEqual(len(repo._movies_by_ids.await_args_list), 1)

    async def test_actor_keyword_branch_unchanged(self) -> None:
        """배우+태그 교집합 경로(기존 동작)는 AND 우선을 타지 않는다."""
        repo = _repo()
        self._wire(
            repo,
            tags=({1, 2, 3}, {2}),
            actors={2, 3},
            movies_side_effect=[[_movie(2), _movie(3)]],
        )
        items = await repo.search_tag_catalog(["SF", "드라마"], 16, actor_names=["톰 행크스"])

        self.assertTrue(all(i.match_type == "actor+keyword" for i in items))
        calls = repo._movies_by_ids.await_args_list
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[0], {2, 3})
