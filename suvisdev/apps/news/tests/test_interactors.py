"""수집·읽기·운영자 유스케이스 (가짜 포트)."""

import pytest
from news_fakes import FakeFeeds, FakeRepo, FakeSearch, art

from news.app.dtos.news_dtos import FeedSource, TopicCreateCommand, TopicDto, TopicUpdateCommand
from news.app.errors import DuplicateTopicError, TopicNotFoundError, TopicValidationError
from news.app.use_cases.news_collect_interactor import NewsCollectInteractor
from news.app.use_cases.news_read_interactor import NewsReadInteractor
from news.app.use_cases.news_topic_admin_interactor import NewsTopicAdminInteractor

_AI_BODY = (
    "도서관 야간 이용에 대해 궁금하신 분들이 많습니다. 이 글에서는 장점을 알아보겠습니다.\n\n"
    "## 장점\n\n**조용한 환경**은 집중력에 중요한 역할을 합니다. 야간에는 이용자가 적습니다. "
    "퇴근 후에도 이용할 수 있습니다. 좌석 경쟁도 덜합니다. 결론적으로 다양한 측면에서 좋습니다. "
    "여러분도 오늘부터 도서관을 적극적으로 활용해 보시는 것이 중요합니다. 앞으로도 생활 정보를 전해 드리겠습니다."
)


def _collector(repo, search, feeds_result, feeds=("가나일보",)):
    return NewsCollectInteractor(
        repository=repo,
        search=search,
        feed_reader=FakeFeeds(feeds_result),
        feeds=[FeedSource(name=n, url=f"https://{n}.example/rss") for n in feeds],
    )


@pytest.mark.asyncio
async def test_collect_filters_irrelevant_dedupes_and_judges():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "도서관", "도서관", True, True)
    same = "https://www.ganadaily.example/news/1"
    search = FakeSearch(
        {
            "도서관": [
                art(same + "?utm_source=naver", "시립도서관 야간 운영", "평일 밤 10시까지"),
                art("https://other.example/2", "증시 마감", "코스피 상승"),  # 무관
            ]
        }
    )
    feeds = {
        "가나일보": [
            art(same, "시립도서관 야간 운영", "평일 밤 10시까지", origin="feed"),  # 같은 기사
            art("https://farm.example/3", "도서관 꿀팁", "요약", origin="feed", body=_AI_BODY),
        ]
    }
    report = await _collector(repo, search, feeds).collect_once()

    assert report.topics == 1 and report.feeds == 1 and report.irrelevant == 1
    assert report.new_articles == 2  # 같은 주소는 한 번만
    assert repo.links == {1: {1: 1.0}}
    assert report.judged == 2 and report.verdicts["ai"] == 1
    farm = repo.verdicts[(2, "rules")]
    assert farm.badge == "ai_suspected" and "기자 이름이 없음" in farm.reasons_ko


@pytest.mark.asyncio
async def test_collect_skips_search_without_keys_but_reads_feeds():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "도서관", "도서관", True, True)
    search = FakeSearch({}, enabled=False)
    report = await _collector(
        repo, search, {"가나일보": [art("https://a.example/1", "제목", origin="feed")]}
    ).collect_once()
    assert search.calls == [] and report.new_articles == 1
    assert any("키 없음" in e for e in report.errors)


@pytest.mark.asyncio
async def test_collect_survives_one_failing_query_and_feed():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "터짐", "터짐", True, True)
    repo.topics[2] = TopicDto(2, "도서관", "도서관", True, True)
    search = FakeSearch({"도서관": [art("https://a.example/1", "도서관 소식")]})
    report = await _collector(repo, search, {}, feeds=("없는피드",)).collect_once()
    assert report.new_articles == 1 and len(report.errors) == 2


@pytest.mark.asyncio
async def test_collect_does_not_rejudge_same_harness_version():
    repo = FakeRepo()
    feeds = {"가나일보": [art("https://a.example/1", "제목", origin="feed")]}
    first = await _collector(repo, FakeSearch({}), feeds).collect_once()
    second = await _collector(repo, FakeSearch({}), feeds).collect_once()
    assert first.judged == 1 and second.judged == 0 and second.new_articles == 0


@pytest.mark.asyncio
async def test_read_hides_private_or_inactive_topics():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "a", "a", True, True)
    repo.topics[2] = TopicDto(2, "b", "b", False, True)
    repo.topics[3] = TopicDto(3, "c", "c", True, False)
    uc = NewsReadInteractor(repo)
    assert [t.id for t in await uc.list_public_topics()] == [1]
    for tid in (2, 3, 99):
        with pytest.raises(TopicNotFoundError):
            await uc.list_topic_articles(tid, limit=10, before=None)


@pytest.mark.asyncio
async def test_admin_topic_rules():
    repo = FakeRepo()
    uc = NewsTopicAdminInteractor(repo)
    t = await uc.create_topic(TopicCreateCommand(query="  반도체   수출 ", label=""))
    assert t.query == "반도체 수출" and t.label == "반도체 수출"
    with pytest.raises(DuplicateTopicError):
        await uc.create_topic(TopicCreateCommand(query="반도체 수출", label="x"))
    with pytest.raises(TopicValidationError):
        await uc.create_topic(TopicCreateCommand(query="   ", label=""))
    off = await uc.update_topic(TopicUpdateCommand(topic_id=t.id, active=False))
    assert off.active is False
    with pytest.raises(TopicNotFoundError):
        await uc.update_topic(TopicUpdateCommand(topic_id=99, label="x"))
    await uc.delete_topic(t.id)
    with pytest.raises(TopicNotFoundError):
        await uc.delete_topic(t.id)
