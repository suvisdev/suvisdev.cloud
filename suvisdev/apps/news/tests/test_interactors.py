"""수집·읽기·운영자 유스케이스 (가짜 포트)."""

import pytest
from news_fakes import FakeFeeds, FakeRepo, FakeSearch, art

from news.app.dtos.news_dtos import FeedSource, TopicCreateCommand, TopicDto, TopicUpdateCommand
from news.app.errors import (
    DuplicateTopicError,
    NewsQueryError,
    TopicNotFoundError,
    TopicValidationError,
)
from news.app.use_cases.news_collect_interactor import NewsCollectInteractor
from news.app.use_cases.news_read_interactor import NewsReadInteractor
from news.app.use_cases.news_topic_admin_interactor import NewsTopicAdminInteractor

_AI_BODY = (
    "도서관 야간 이용에 대해 궁금하신 분들이 많습니다. 이 글에서는 장점을 알아보겠습니다.\n\n"
    "## 장점\n\n**조용한 환경**은 집중력에 중요한 역할을 합니다. 야간에는 이용자가 적습니다. "
    "퇴근 후에도 이용할 수 있습니다. 좌석 경쟁도 덜합니다. 결론적으로 다양한 측면에서 좋습니다. "
    "여러분도 오늘부터 도서관을 적극적으로 활용해 보시는 것이 중요합니다. 앞으로도 생활 정보를 전해 드리겠습니다."
)
# 영어 1차 출처 글 — 기사체 규칙을 돌리면 기자명·인용 표기가 없어 배지가 붙는다(판정 범위 밖이어야 함)
_EN_BODY = (
    "We are releasing a new mixture of experts model.\n\n## Highlights\n\n"
    "- 2x faster inference\n- 128k context\n- open weights\n- new tokenizer\n\n"
    "**Try it today.** Sure, here is a summary of the results. " * 3
)


def _collector(repo, search, feeds_result, feeds=(("가나일보", "outlet"),)):
    return NewsCollectInteractor(
        repository=repo,
        search=search,
        feed_reader=FakeFeeds(feeds_result),
        feeds=[FeedSource(name=n, url=f"https://{n}.example/rss", group=g) for n, g in feeds],
    )


@pytest.mark.asyncio
async def test_collect_filters_irrelevant_dedupes_and_judges():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "도서관", "도서관", True, True, "economy")
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
    assert repo.links == {1: {1: 1.0, 2: 1.0}}  # 검색 결과 + 같은 섹션(경제) RSS 글
    assert report.judged == 2 and report.verdicts["ai"] == 1
    farm = repo.verdicts[(2, "rules")]
    assert farm.badge == "ai_suspected" and "기자 이름이 없음" in farm.reasons_ko
    stored = repo.articles[same]
    assert stored.section == "economy" and stored.group == "outlet"  # RSS 쪽을 남긴다


@pytest.mark.asyncio
async def test_ai_sources_are_not_judged_and_keep_no_body():
    repo = FakeRepo()
    feeds = {
        "OpenAI": [
            art(
                "https://openai.example/moe",
                "New MoE model",
                origin="feed",
                group="lab",
                body=_EN_BODY,
            )
        ],
        "AI타임스": [
            art(
                "https://aitimes.example/1",
                "도서관 꿀팁",
                "요약",
                origin="feed",
                group="ko_media",
                body=_AI_BODY,
            )
        ],
    }
    report = await _collector(
        repo, FakeSearch({}), feeds, feeds=(("OpenAI", "lab"), ("AI타임스", "ko_media"))
    ).collect_once()

    lab = repo.articles["https://openai.example/moe"]
    assert lab.section == "ai" and lab.body == ""  # 판정 범위 밖은 본문을 저장하지 않는다
    assert (lab.id, "rules") not in repo.verdicts
    assert report.judged == 1 and report.not_judged == 1  # 국내 AI 매체만 판정
    assert repo.verdicts[(2, "rules")].badge == "ai_suspected"


@pytest.mark.asyncio
async def test_ai_topic_matches_feed_items_of_its_section_without_search_api():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "mixture of experts", "MoE", True, True, "ai")
    search = FakeSearch({}, enabled=False)
    feeds = {
        "arXiv": [
            art(
                "https://arxiv.example/1",
                "Sparse Mixture of Experts at Scale",
                origin="feed",
                group="paper",
            ),
            art("https://arxiv.example/2", "Diffusion for audio", origin="feed", group="paper"),
        ],
        "가나일보": [art("https://ganadaily.example/9", "mixture of experts 펀드", origin="feed")],
    }
    report = await _collector(
        repo, search, feeds, feeds=(("arXiv", "paper"), ("가나일보", "outlet"))
    ).collect_once()

    assert search.calls == [] and report.errors == []  # AI 탭은 검색 API 를 쓰지 않는다
    assert repo.links == {1: {1: 1.0}}  # 같은 섹션(ai) 글만, 경제 기사는 제외


@pytest.mark.asyncio
async def test_same_url_in_two_feeds_keeps_first_group():
    repo = FakeRepo()
    url = "https://openai.example/post"
    feeds = {
        "OpenAI": [art(url, "Post", origin="feed", group="lab")],
        "HN": [art(url, "Post", origin="feed", group="community")],
    }
    await _collector(
        repo, FakeSearch({}), feeds, feeds=(("OpenAI", "lab"), ("HN", "community"))
    ).collect_once()
    assert repo.articles[url].group == "lab"


@pytest.mark.asyncio
async def test_collect_skips_search_without_keys_but_reads_feeds():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "도서관", "도서관", True, True, "economy")
    search = FakeSearch({}, enabled=False)
    report = await _collector(
        repo, search, {"가나일보": [art("https://a.example/1", "제목", origin="feed")]}
    ).collect_once()
    assert search.calls == [] and report.new_articles == 1
    assert any("키 없음" in e for e in report.errors)


@pytest.mark.asyncio
async def test_collect_survives_one_failing_query_and_feed():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "터짐", "터짐", True, True, "economy")
    repo.topics[2] = TopicDto(2, "도서관", "도서관", True, True, "economy")
    search = FakeSearch({"도서관": [art("https://a.example/1", "도서관 소식")]})
    report = await _collector(repo, search, {}, feeds=(("없는피드", "outlet"),)).collect_once()
    assert report.new_articles == 1 and len(report.errors) == 2


@pytest.mark.asyncio
async def test_collect_does_not_rejudge_same_harness_version():
    repo = FakeRepo()
    feeds = {"가나일보": [art("https://a.example/1", "제목", origin="feed")]}
    first = await _collector(repo, FakeSearch({}), feeds).collect_once()
    second = await _collector(repo, FakeSearch({}), feeds).collect_once()
    assert first.judged == 1 and second.judged == 0 and second.new_articles == 0


@pytest.mark.asyncio
async def test_read_hides_private_or_inactive_topics_and_filters_section():
    repo = FakeRepo()
    repo.topics[1] = TopicDto(1, "a", "a", True, True, "ai")
    repo.topics[2] = TopicDto(2, "b", "b", False, True)
    repo.topics[3] = TopicDto(3, "c", "c", True, False)
    repo.topics[4] = TopicDto(4, "d", "d", True, True, "economy")
    uc = NewsReadInteractor(repo)
    assert [t.id for t in await uc.list_public_topics()] == [1, 4]
    assert [t.id for t in await uc.list_public_topics("economy")] == [4]
    for tid in (2, 3, 99):
        with pytest.raises(TopicNotFoundError):
            await uc.list_topic_articles(tid, limit=10, before=None)


@pytest.mark.asyncio
async def test_read_latest_and_search_validate_input():
    repo = FakeRepo()
    uc = NewsReadInteractor(repo)
    await uc.list_latest(section="ai", group="paper", limit=500, before=None)
    assert repo.last_query == ("latest", "ai", "paper", 100)
    with pytest.raises(NewsQueryError):
        await uc.list_latest(section="ai", group="outlet", limit=10, before=None)  # 경제 묶음
    with pytest.raises(NewsQueryError):
        await uc.list_latest(section="sports", group=None, limit=10, before=None)

    await uc.search("  금리   인하  금리 ", section="economy", limit=10, before=None)
    assert repo.last_query == ("search", "economy", ("금리", "인하"), 10)
    with pytest.raises(NewsQueryError):
        await uc.search("   ", section="ai", limit=10, before=None)


@pytest.mark.asyncio
async def test_sections_list_groups_and_feed_names():
    feeds = [
        FeedSource("OpenAI", "https://o.example/rss", "lab"),
        FeedSource("매일경제", "https://m.example/rss", "outlet"),
    ]
    sections = await NewsReadInteractor(FakeRepo(), feeds).list_sections()
    assert [s.code for s in sections] == ["ai", "economy"]  # 메인이 먼저
    lab = next(g for g in sections[0].groups if g.code == "lab")
    assert lab.feeds == ["OpenAI"]
    assert [g.code for g in sections[1].groups] == ["outlet", "search"]


@pytest.mark.asyncio
async def test_admin_topic_rules():
    repo = FakeRepo()
    uc = NewsTopicAdminInteractor(repo)
    t = await uc.create_topic(TopicCreateCommand(query="  반도체   수출 ", label=""))
    assert t.query == "반도체 수출" and t.label == "반도체 수출" and t.section == "ai"
    with pytest.raises(DuplicateTopicError):
        await uc.create_topic(TopicCreateCommand(query="반도체 수출", label="x"))
    with pytest.raises(TopicValidationError):
        await uc.create_topic(TopicCreateCommand(query="   ", label=""))
    with pytest.raises(TopicValidationError):
        await uc.create_topic(TopicCreateCommand(query="환율", label="", section="sports"))
    econ = await uc.create_topic(TopicCreateCommand(query="환율", label="", section="economy"))
    assert econ.section == "economy"
    off = await uc.update_topic(TopicUpdateCommand(topic_id=t.id, active=False))
    assert off.active is False
    with pytest.raises(TopicNotFoundError):
        await uc.update_topic(TopicUpdateCommand(topic_id=99, label="x"))
    await uc.delete_topic(t.id)
    with pytest.raises(TopicNotFoundError):
        await uc.delete_topic(t.id)
