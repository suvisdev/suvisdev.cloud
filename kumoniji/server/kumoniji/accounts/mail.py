"""계정 메일(가입 인증·재설정·알림). Gmail SMTP, 표준 라이브러리만(SECURITY.md 5절, 검증 32).

- API는 큐에 넣고 바로 응답한다(계정 존재 여부가 응답 시간으로 새지 않게 — 검증 4).
- 본문은 텍스트만, 사용자 입력(닉네임 등)을 넣지 않는다. 링크는 고정 공개 원점(KUMONIJI_PUBLIC_ORIGIN)만.
- 로그에 받는 주소·링크·토큰을 남기지 않는다.
"""

import logging
import os
import queue
import smtplib
import ssl
import threading
from email.message import EmailMessage

log = logging.getLogger("kumoniji.mail")
_q: queue.Queue = queue.Queue(maxsize=1000)
_worker: threading.Thread | None = None

WARN = {
    "ko": "비밀번호·인증번호·복구 코드는 이메일 회신이나 상담으로 요구하지 않습니다. 의심되면 앱이나 공식 주소로 직접 접속하세요.",
    "en": "We never ask for your password, verification code, or recovery codes by email reply or support chat. If in doubt, open the app or our official address directly.",
    "ja": "パスワード・認証コード・リカバリーコードをメールの返信やサポートで求めることはありません。不審な場合はアプリまたは公式アドレスに直接アクセスしてください。",
}
# kind → (언어별 제목, 본문). {link}만 채운다.
TEXT = {
    "verify": {
        "ko": ("쿠모니지 가입 인증", "아래 링크를 열어 이메일 인증을 마쳐 주세요(24시간 유효).\n{link}"),
        "en": (
            "Verify your Kumoniji account",
            "Open the link below to verify your email (valid for 24 hours).\n{link}",
        ),
        "ja": ("クモニジ登録の認証", "下のリンクを開いてメール認証を完了してください（24時間有効）。\n{link}"),
    },
    "already": {
        "ko": (
            "쿠모니지 가입 시도",
            "이 주소로 이미 가입된 계정이 있습니다. 비밀번호가 기억나지 않으면 재설정하세요.\n{link}",
        ),
        "en": (
            "Kumoniji sign-up attempt",
            "An account already exists for this address. Forgot your password? Reset it here.\n{link}",
        ),
        "ja": (
            "クモニジ登録の試み",
            "このアドレスのアカウントはすでにあります。パスワードを忘れた場合は再設定してください。\n{link}",
        ),
    },
    "reset": {
        "ko": (
            "쿠모니지 비밀번호 재설정",
            "아래 링크에서 새 비밀번호를 정하세요(30분 유효). 요청하지 않았다면 무시하세요.\n{link}",
        ),
        "en": (
            "Reset your Kumoniji password",
            "Set a new password at the link below (valid for 30 minutes). Ignore this if you didn't ask.\n{link}",
        ),
        "ja": (
            "クモニジのパスワード再設定",
            "下のリンクで新しいパスワードを設定してください（30分有効）。心当たりがなければ無視してください。\n{link}",
        ),
    },
    "password_changed": {
        "ko": (
            "쿠모니지 비밀번호가 바뀌었습니다",
            "모든 기기에서 로그아웃했습니다. 본인이 아니면 계정 보호를 요청하세요.\n{link}",
        ),
        "en": (
            "Your Kumoniji password changed",
            "You've been signed out everywhere. If this wasn't you, protect your account.\n{link}",
        ),
        "ja": (
            "クモニジのパスワードが変更されました",
            "すべての端末からログアウトしました。心当たりがなければアカウント保護を依頼してください。\n{link}",
        ),
    },
    "email_confirm": {
        "ko": (
            "쿠모니지 새 이메일 확인",
            "이 주소를 쿠모니지 계정 이메일로 쓰려면 링크를 여세요(24시간 유효).\n{link}",
        ),
        "en": (
            "Confirm your new Kumoniji email",
            "Open the link to use this address for your Kumoniji account (valid for 24 hours).\n{link}",
        ),
        "ja": (
            "クモニジの新しいメールの確認",
            "このアドレスをアカウントのメールにするにはリンクを開いてください（24時間有効）。\n{link}",
        ),
    },
    "email_changed": {
        "ko": (
            "쿠모니지 이메일이 바뀌었습니다",
            "계정 이메일이 다른 주소로 바뀌었습니다. 본인이 아니면 7일 안에 계정 보호를 요청하세요.\n{link}",
        ),
        "en": (
            "Your Kumoniji email changed",
            "Your account email was changed. If this wasn't you, protect your account within 7 days.\n{link}",
        ),
        "ja": (
            "クモニジのメールが変更されました",
            "アカウントのメールが変更されました。心当たりがなければ7日以内に保護を依頼してください。\n{link}",
        ),
    },
    "new_device": {
        "ko": ("쿠모니지 새 기기 로그인", "새 기기에서 로그인했습니다. 본인이 아니면 계정 보호를 요청하세요.\n{link}"),
        "en": (
            "New Kumoniji sign-in",
            "Your account signed in on a new device. If this wasn't you, protect your account.\n{link}",
        ),
        "ja": (
            "クモニジ新しい端末でのログイン",
            "新しい端末でログインしました。心当たりがなければアカウント保護を依頼してください。\n{link}",
        ),
    },
    "security": {
        "ko": (
            "쿠모니지 보안 알림",
            "계정 보안 설정이 바뀌었거나 의심스러운 로그인이 있어 모든 기기에서 로그아웃했을 수 있습니다. 본인이 아니면 계정 보호를 요청하세요.\n{link}",
        ),
        "en": (
            "Kumoniji security notice",
            "Your security settings changed or a suspicious sign-in was stopped. If this wasn't you, protect your account.\n{link}",
        ),
        "ja": (
            "クモニジのセキュリティ通知",
            "セキュリティ設定が変更されたか、不審なログインを止めました。心当たりがなければアカウント保護を依頼してください。\n{link}",
        ),
    },
}


def origin() -> str:
    return os.environ.get("KUMONIJI_PUBLIC_ORIGIN", "https://kumoniji.suvisdev.cloud").rstrip("/")


def compose(to: str, kind: str, path: str, lang: str = "en") -> EmailMessage:
    lang = lang if lang in WARN else "en"
    subject, body = TEXT[kind][lang]
    m = EmailMessage()
    m["From"] = os.environ.get("KUMONIJI_MAIL_FROM") or os.environ.get("KUMONIJI_SMTP_USER", "")
    m["To"] = to
    m["Subject"] = subject
    m.set_content(body.format(link=origin() + path) + "\n\n" + WARN[lang] + "\n")
    return m


def _deliver(m: EmailMessage) -> None:
    user, pw = os.environ.get("KUMONIJI_SMTP_USER", ""), os.environ.get("KUMONIJI_SMTP_PASSWORD", "")
    if not user or not pw:
        log.warning("메일 설정 없음 — %s 메일을 보내지 못함", m["Subject"])
        return
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15, context=ssl.create_default_context()) as s:
        s.login(user, pw)
        s.send_message(m)


def _run() -> None:
    while True:
        m = _q.get()
        try:
            for attempt in range(3):
                try:
                    _deliver(m)
                    break
                except (smtplib.SMTPException, OSError) as e:
                    log.warning("메일 발송 실패(%d/3): %s", attempt + 1, type(e).__name__)
        finally:
            _q.task_done()


def send(to: str | None, kind: str, path: str, lang: str = "en") -> None:
    """큐에 넣고 바로 돌아온다. 큐가 가득 차면 버린다(응답은 같음)."""
    global _worker
    if not to:
        return
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_run, daemon=True, name="kumoniji-mail")
        _worker.start()
    try:
        _q.put_nowait(compose(to, kind, path, lang))
    except queue.Full:
        log.warning("메일 큐 가득 참 — 버림")


def flush() -> None:
    """테스트용: 큐가 빌 때까지 기다린다."""
    _q.join()
