"""아침 메일 — 어제 범위, 고르는 순서, 실패 때 안 보내고 기록도 안 남기는지."""

import json
import ssl
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from news_fakes import FakeRepo

from news.adapter.outbound.kvstore.redis_digest_ledger import MAX_TRIES, RedisDigestLedger
from news.adapter.outbound.llm.ollama_article_classifier import OllamaArticleClassifier
from news.adapter.outbound.mail import smtp_digest_mailer
from news.adapter.outbound.mail.smtp_digest_mailer import SmtpDigestMailer
from news.app.dtos.news_dtos import ArticleDto
from news.app.ports.output.news_digest_ports import (
    ArticleClassifierPort,
    ArticleJudgement,
    ClassifierUnavailableError,
    DigestLedgerPort,
    DigestMailerPort,
)
from news.app.use_cases.news_digest_interactor import NewsDigestInteractor
from news.domain.digest import (
    MAX_ITEMS,
    DigestItem,
    digest_day,
    digest_window,
    is_due,
    render_digest,
    select_items,
)

NOW = datetime(2026, 11, 9, 0, 30, tzinfo=UTC)  # 한국 시각 09:30


def _article(n: int, title: str = "글", group: str = "lab") -> ArticleDto:
    return ArticleDto(
        id=n,
        title=title,
        url=f"https://a.example/{n}",
        summary="",
        source_domain="a.example",
        source_name="출처",
        published_at=None,
        badge="none",
        reasons_ko=[],
        group=group,
        sort_at=datetime(2026, 11, 8, 3, tzinfo=UTC) + timedelta(minutes=n),
    )


class _Classifier(ArticleClassifierPort):
    def __init__(self, labels: dict[int, str | None] | None = None, down: bool = False) -> None:
        self.labels, self.down = labels or {}, down

    async def classify(self, article: ArticleDto) -> ArticleJudgement | None:
        if self.down:
            raise ClassifierUnavailableError("꺼짐")
        label = self.labels.get(article.id, "tech")
        return None if label is None else ArticleJudgement(label, 3)


class _Mailer(DigestMailerPort):
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.fail = fail

    def send(self, *, subject: str, text: str, html: str) -> None:
        if self.fail:
            raise OSError("smtp")
        self.sent.append((subject, text, html))


class _Ledger(DigestLedgerPort):
    def __init__(self, allow: bool = True) -> None:
        self.allow = allow
        self.finished: list[date] = []
        self.failures = 0

    def begin(self, day: date) -> bool:
        return self.allow

    def record_failure(self, day: date) -> None:
        self.failures += 1

    def finish(self, day: date) -> None:
        self.finished.append(day)


def _interactor(articles, classifier=None, mailer=None, ledger=None):
    repo = FakeRepo()
    repo.digest_candidates = articles
    mailer, ledger = mailer or _Mailer(), ledger or _Ledger()
    use_case = NewsDigestInteractor(repo, classifier or _Classifier(), mailer, ledger)
    return use_case, mailer, ledger


def test_yesterday_uses_korean_midnight():
    # UTC 11-08 15:30 은 한국 11-09 00:30 — 어제는 11-08 이다
    assert digest_day(datetime(2026, 11, 8, 15, 30, tzinfo=UTC)) == date(2026, 11, 8)
    since, until = digest_window(date(2026, 11, 8))
    assert since == datetime(2026, 11, 7, 15, tzinfo=UTC)
    assert until == datetime(2026, 11, 8, 15, tzinfo=UTC)


def test_due_from_seven_korean_time():
    assert not is_due(datetime(2026, 11, 8, 21, 59, tzinfo=UTC))
    assert is_due(datetime(2026, 11, 8, 22, 0, tzinfo=UTC))


def _item(n: int, group: str, hot: str | None = None, value: int = 1) -> DigestItem:
    return DigestItem(
        title=f"글{n}", url=f"https://a/{n}", group=group, source="s", hot_label=hot, value=value
    )


def test_select_prefers_study_value_over_source_and_hot():
    picked = select_items([_item(1, "lab", hot="1,000점", value=2), _item(2, "community", value=5)])
    assert [i.title for i in picked] == ["글2", "글1"]


def test_select_caps_total_and_group_then_fills_remaining():
    community = [_item(n, "community") for n in range(20)]
    labs = [_item(100 + n, "lab") for n in range(2)]
    picked = select_items(community + labs)
    assert len(picked) == MAX_ITEMS
    assert [i.group for i in picked[:2]] == ["lab", "lab"]
    # 다른 묶음이 없으면 상한 4를 넘어 채운다
    assert sum(i.group == "community" for i in picked) == MAX_ITEMS - 2


def test_select_puts_hot_first_and_limits_group_when_others_exist():
    groups = [_item(n, "community") for n in range(6)] + [_item(10 + n, "lab") for n in range(6)]
    groups.append(_item(99, "community", hot="1,000점"))
    picked = select_items(groups)
    assert picked[0].hot_label == "1,000점"
    assert sum(i.group == "lab" for i in picked) >= 4


def test_render_escapes_feed_text_and_drops_unsafe_link():
    bad = DigestItem(
        title="<script>x</script>",
        url="javascript:alert(1)",
        group="lab",
        source="<b>출처</b>",
        summary="a&b",
    )
    subject, text, html = render_digest(date(2026, 11, 8), [bad])
    assert subject == "[AI 소식] 11월 8일 AI 기술 소식 1건"
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "href=" not in html and "<b>출처" not in html and "a&amp;b" in html
    assert "<script>x</script>" in text


@pytest.mark.asyncio
async def test_sends_only_tech_and_records():
    arts = [_article(1, "기술 글"), _article(2, "투자 글"), _article(3, "모름")]
    labels = {2: "industry", 3: None}
    use_case, mailer, ledger = _interactor(arts, _Classifier(labels))
    report = await use_case.send_if_due(NOW)
    assert (report.status, report.candidates, report.tech, report.sent) == ("sent", 3, 1, 1)
    assert "기술 글" in mailer.sent[0][1] and "투자 글" not in mailer.sent[0][1]
    assert ledger.finished == [date(2026, 11, 8)]


@pytest.mark.asyncio
async def test_not_due_or_already_sent_does_nothing():
    early = datetime(2026, 11, 8, 21, 0, tzinfo=UTC)
    use_case, mailer, _ = _interactor([_article(1)])
    assert (await use_case.send_if_due(early)).status == "not_due"
    use_case, mailer2, _ = _interactor([_article(1)], ledger=_Ledger(allow=False))
    assert (await use_case.send_if_due(NOW)).status == "skipped"
    assert mailer.sent == [] and mailer2.sent == []


@pytest.mark.asyncio
async def test_model_down_sends_nothing_and_stays_retryable():
    use_case, mailer, ledger = _interactor([_article(1)], _Classifier(down=True))
    assert (await use_case.send_if_due(NOW)).status == "model_unavailable"
    assert mailer.sent == [] and ledger.finished == [] and ledger.failures == 0


@pytest.mark.asyncio
async def test_mail_failure_stays_retryable():
    use_case, _, ledger = _interactor([_article(1)], mailer=_Mailer(fail=True))
    assert (await use_case.send_if_due(NOW)).status == "mail_failed"
    assert ledger.finished == [] and ledger.failures == 1


@pytest.mark.asyncio
async def test_no_tech_sends_no_empty_mail():
    use_case, mailer, ledger = _interactor([_article(1)], _Classifier({1: "other"}))
    assert (await use_case.send_if_due(NOW)).status == "no_items"
    assert mailer.sent == [] and len(ledger.finished) == 1


class _Redis:
    def __init__(self) -> None:
        self.data: dict[str, object] = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True

    def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    def expire(self, key, seconds):
        return True


def test_ledger_blocks_concurrent_and_after_send():
    day = date(2026, 11, 8)
    client = _Redis()
    ledger = RedisDigestLedger(client)
    assert ledger.begin(day) is True
    assert ledger.begin(day) is False  # 다른 파드가 진행 중
    del client.data[f"news:digest:{day}:lock"]
    ledger.finish(day)
    assert ledger.begin(day) is False  # 이미 보냄


def test_ledger_stops_only_after_mail_failures_not_model_outage():
    day = date(2026, 11, 8)
    client = _Redis()
    ledger = RedisDigestLedger(client)
    for _ in range(MAX_TRIES + 2):  # 모델 장애: 발송 실패를 기록하지 않고 주기만 지난다
        assert ledger.begin(day) is True
        del client.data[f"news:digest:{day}:lock"]
    for _ in range(MAX_TRIES):
        assert ledger.begin(day) is True
        del client.data[f"news:digest:{day}:lock"]
        ledger.record_failure(day)
    assert ledger.begin(day) is False


def _classifier(handler) -> OllamaArticleClassifier:
    return OllamaArticleClassifier(
        base_url="http://o", model="m", transport=httpx.MockTransport(handler)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"label":"tech","value":5}', ArticleJudgement("tech", 5)),
        ('{"label":"tech","value":9}', ArticleJudgement("tech", 5)),
        ('{"label":"tech"}', None),
        ('{"label":"뉴스","value":3}', None),
        ("깨진 출력", None),
    ],
)
async def test_classifier_accepts_only_known_labels(content, expected):
    def handler(_):
        return httpx.Response(200, json={"message": {"content": content}})

    assert await _classifier(handler).classify(_article(1)) == expected


@pytest.mark.asyncio
async def test_classifier_server_error_is_unavailable():
    with pytest.raises(ClassifierUnavailableError):
        await _classifier(lambda _: httpx.Response(500)).classify(_article(1))


def test_classifier_prompt_contains_article():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": '{"label":"other","value":1}'}})

    import asyncio

    asyncio.run(_classifier(handler).classify(_article(1, "제목X")))
    assert "제목X" in seen["messages"][1]["content"] and seen["options"]["temperature"] == 0


def test_smtp_mailer_logs_in_and_sends_html(monkeypatch):
    calls = {}

    class _Smtp:
        def __init__(self, host, port, timeout, context):
            calls["addr"] = (host, port)
            calls["context"] = context

        def __enter__(self):
            return self

        def ehlo(self):
            self.esmtp_features = {"auth": "LOGIN PLAIN XOAUTH2"}

        def __exit__(self, *_):
            return False

        def login(self, user, password):
            calls["login"] = (user, password)
            calls["auth"] = self.esmtp_features["auth"]

        def send_message(self, message):
            calls["message"] = message

    monkeypatch.setattr(smtp_digest_mailer.smtplib, "SMTP_SSL", _Smtp)
    SmtpDigestMailer(user="me@x", password="pw", to="you@x").send(
        subject="제목", text="본문", html="<p>본문</p>"
    )
    assert calls["addr"] == ("smtp.gmail.com", 465) and calls["login"] == ("me@x", "pw")
    assert calls["auth"] == "PLAIN"
    assert calls["context"].verify_mode == ssl.CERT_REQUIRED and calls["context"].check_hostname
    message = calls["message"]
    assert message["To"] == "you@x" and message["Subject"] == "제목"
    assert message.get_body(("html",)).get_content().strip() == "<p>본문</p>"
