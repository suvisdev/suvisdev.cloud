"""메일(검증 32 일부): 피싱 방지 문구·고정 원점·큐."""

import smtplib

from kumoniji.accounts import mail


def test_32_warning_and_fixed_origin(monkeypatch):
    monkeypatch.setenv("KUMONIJI_PUBLIC_ORIGIN", "https://kumoniji.suvisdev.cloud")
    for lang in ("ko", "en", "ja", "zh"):
        m = mail.compose("u@x.com", "reset", "/reset?token=abc", lang)
        body = m.get_content()
        assert "https://kumoniji.suvisdev.cloud/reset?token=abc" in body
        assert mail.WARN[lang] in body
        assert m.get_content_type() == "text/plain"


def test_send_is_queued_and_smtp_failure_does_not_raise(monkeypatch, caplog):
    sent = []

    def boom(m):
        sent.append(m["Subject"])
        raise smtplib.SMTPServerDisconnected("x")

    monkeypatch.setattr(mail, "_deliver", boom)
    mail.send("u@x.com", "verify", "/verify?token=secret-token-value")
    mail.flush()
    assert len(sent) == 3  # 3번 재시도
    assert "secret-token-value" not in caplog.text and "u@x.com" not in caplog.text
