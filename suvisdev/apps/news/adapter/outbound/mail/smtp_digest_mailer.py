"""Gmail SMTP 로 아침 메일 보내기 — 표준 라이브러리만 쓴다. 비용 0원.

비밀번호는 Google 계정의 16자리 앱 비밀번호다(NEWS_DIGEST_SMTP_PASSWORD).
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from news.app.ports.output.news_digest_ports import DigestMailerPort

_HOST = "smtp.gmail.com"
_PORT = 465


class SmtpDigestMailer(DigestMailerPort):
    def __init__(self, *, user: str, password: str, to: str, timeout: float = 30.0) -> None:
        self._user = user
        self._password = password
        self._to = to
        self._timeout = timeout

    def send(self, *, subject: str, text: str, html: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._user
        message["To"] = self._to
        message.set_content(text)
        message.add_alternative(html, subtype="html")
        # context 를 안 주면 인증서를 검증하지 않아 앱 비밀번호가 가짜 서버로 갈 수 있다.
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(_HOST, _PORT, timeout=self._timeout, context=context) as smtp:
            smtp.login(self._user, self._password)
            smtp.send_message(message)
