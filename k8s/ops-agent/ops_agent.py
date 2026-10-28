"""운영 제어 에이전트 — 관리자 페이지 버튼이 이 PC 에서 할 수 있는 일을 정해 둔 목록만큼만 한다.

호출하는 쪽은 suvisdev 백엔드(/admin/ops/*, 관리자 로그인 필수)뿐이다. 브라우저가 직접 부르지 않는다.
할 수 있는 일(이 밖의 요청은 전부 404):

  GET  /status          Arda 컨테이너 상태 · GPU(VRAM) · Ollama 에 올라간 모델과 설치된 모델
  POST /arda/start      docker compose up -d   (infra/onprem — 노트북 온프레미스 Arda)
  POST /arda/stop       docker compose stop    (unless-stopped 라 다음 부팅에도 꺼진 채 남는다)
  POST /ollama/load     {"model": "..."}  모델을 GPU 에 올려 둔다(keep_alive -1)
  POST /ollama/unload   {"model": "..."}  모델을 내린다(keep_alive 0)

지키는 것:
- 토큰: 헤더 X-Ops-Token 이 OPS_AGENT_TOKEN 과 같아야 한다(상수 시간 비교).
- 출발지: 자기 자신 · k3s 파드망(10.42.0.0/16) · Tailscale(100.64.0.0/10) 만. 집컴이 서빙할 때
  집컴 백엔드가 Tailscale 로 부른다. 그 밖(공유기 LAN 등)은 토큰이 맞아도 거절한다.
- 셸을 쓰지 않는다. 명령은 인자 목록으로 고정이고, 모델 이름은 Ollama 에 실제 설치된 이름만 받는다.
- 동작(켜기·끄기·올리기·내리기)은 한 번에 하나만 — 버튼을 연달아 눌러도 겹치지 않는다.

의존성 없이 표준 라이브러리만 쓴다(WSL 의 python3 로 바로 돈다). 설치는 같은 폴더 README.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import os
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("OPS_AGENT_TOKEN", "")
BIND = os.environ.get("OPS_AGENT_BIND", "0.0.0.0")
PORT = int(os.environ.get("OPS_AGENT_PORT", "8210"))
ARDA_COMPOSE = os.environ.get(
    "ARDA_COMPOSE", "/mnt/c/Team Seuk/Arda/infra/onprem/docker-compose.yml"
)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

ALLOWED_NETS = [
    ipaddress.ip_network(n) for n in ("127.0.0.0/8", "10.42.0.0/16", "100.64.0.0/10")
]
MAX_BODY = 4096

log = logging.getLogger("ops-agent")
_action_lock = threading.Lock()


class OpsError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# ── 순수 판정 (테스트 대상) ─────────────────────────────────────


def source_allowed(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return any(addr in net for net in ALLOWED_NETS)


def token_ok(given: str | None, expected: str = "") -> bool:
    expected = expected or TOKEN
    # 토큰이 설정되지 않은 에이전트는 아무것도 받지 않는다(빈 토큰끼리 같다고 통과시키지 않는다)
    return bool(expected) and given is not None and hmac.compare_digest(given, expected)


def parse_compose_ps(stdout: str) -> list[dict]:
    """`docker compose ps --format json` — 버전에 따라 한 줄에 하나 또는 배열 하나로 나온다."""
    text = stdout.strip()
    if not text:
        return []
    rows = (
        json.loads(text)
        if text.startswith("[")
        else [json.loads(line) for line in text.splitlines() if line.strip()]
    )
    return [
        {
            "service": r.get("Service"),
            "state": r.get("State"),
            "status": r.get("Status"),
        }
        for r in rows
    ]


def parse_nvidia_smi(stdout: str) -> list[dict]:
    gpus = []
    for line in stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            continue
        name, used, total, util = parts
        gpus.append(
            {
                "name": name,
                "memory_used_mib": int(used),
                "memory_total_mib": int(total),
                "utilization_pct": int(util),
            }
        )
    return gpus


# ── 바깥 세상 ────────────────────────────────────────────────


def _run(args: list[str], timeout: int) -> str:
    try:
        done = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as e:
        raise OpsError(504, f"{args[0]} 시간 초과({timeout}s)") from e
    except FileNotFoundError as e:
        raise OpsError(500, f"{args[0]} 을(를) 찾을 수 없다") from e
    if done.returncode != 0:
        raise OpsError(
            502,
            (done.stderr or done.stdout).strip()[-500:]
            or f"{args[0]} 실패({done.returncode})",
        )
    return done.stdout


def _compose(*cmd: str, timeout: int) -> str:
    return _run(["docker", "compose", "-f", ARDA_COMPOSE, *cmd], timeout)


def _ollama(path: str, body: dict | None = None, timeout: int = 10) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        OLLAMA_URL + path, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        err = OpsError(
            502, f"Ollama {e.code}: {e.read()[:200].decode(errors='replace')}"
        )
        err.ollama_code = e.code  # type: ignore[attr-defined]
        raise err from e
    except urllib.error.URLError as e:
        raise OpsError(502, f"Ollama 응답 없음: {e}") from e


def _keep_alive(model: str, keep_alive: int) -> None:
    """모델을 올리거나(-1) 내린다(0). 생성 모델은 /api/generate, 임베딩 모델(bge-m3 등)은
    generate 를 400 으로 거절하므로 /api/embed 로 같은 일을 한다(2026-10-28 실측)."""
    try:
        _ollama(
            "/api/generate",
            {"model": model, "prompt": "", "keep_alive": keep_alive, "stream": False},
            timeout=180,
        )
    except OpsError as e:
        if getattr(e, "ollama_code", None) != 400:
            raise
        _ollama(
            "/api/embed",
            {"model": model, "input": "warmup", "keep_alive": keep_alive},
            timeout=180,
        )


def arda_status() -> dict:
    try:
        return {
            "available": True,
            "services": parse_compose_ps(
                _compose("ps", "-a", "--format", "json", timeout=20)
            ),
        }
    except OpsError as e:
        return {"available": False, "error": str(e)}


def gpu_status() -> list[dict]:
    try:
        out = _run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            timeout=10,
        )
    except OpsError:
        return []
    return parse_nvidia_smi(out)


def ollama_status() -> dict:
    try:
        loaded = _ollama("/api/ps").get("models", [])
        installed = _ollama("/api/tags").get("models", [])
    except OpsError as e:
        return {"available": False, "error": str(e)}
    return {
        "available": True,
        "loaded": [
            {
                "name": m.get("name"),
                "size_vram": m.get("size_vram"),
                "expires_at": m.get("expires_at"),
            }
            for m in loaded
        ],
        "installed": sorted(m.get("name") for m in installed if m.get("name")),
    }


def status() -> dict:
    return {"arda": arda_status(), "gpu": gpu_status(), "ollama": ollama_status()}


def _installed_model(model: object) -> str:
    if not isinstance(model, str) or not model:
        raise OpsError(400, "model 이 필요하다")
    names = ollama_status().get("installed", [])
    if model not in names:
        raise OpsError(404, f"설치되지 않은 모델: {model}")
    return model


def act(path: str, body: dict) -> dict:
    if not _action_lock.acquire(blocking=False):
        raise OpsError(409, "다른 동작이 진행 중이다 — 끝난 뒤 다시 누른다")
    try:
        if path == "/arda/start":
            _compose("up", "-d", timeout=300)
            return {"ok": True, "arda": arda_status()}
        if path == "/arda/stop":
            _compose("stop", timeout=180)
            return {"ok": True, "arda": arda_status()}
        if path == "/ollama/load":
            # 빈 프롬프트 + keep_alive -1: 생성 없이 GPU 에 올려 두기만 한다(Ollama 공식 방법)
            _keep_alive(_installed_model(body.get("model")), -1)
            return {"ok": True, "ollama": ollama_status()}
        if path == "/ollama/unload":
            _keep_alive(_installed_model(body.get("model")), 0)
            return {"ok": True, "ollama": ollama_status()}
        raise OpsError(404, "없는 동작")
    finally:
        _action_lock.release()


# ── HTTP ─────────────────────────────────────────────────────


class Handler(BaseHTTPRequestHandler):
    server_version = "ops-agent"

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _guard(self) -> bool:
        ip = self.client_address[0]
        if not source_allowed(ip):
            log.warning("거절(출발지) %s %s", ip, self.path)
            self._send(403, {"error": "forbidden"})
            return False
        if not token_ok(self.headers.get("X-Ops-Token")):
            log.warning("거절(토큰) %s %s", ip, self.path)
            self._send(401, {"error": "unauthorized"})
            return False
        return True

    def do_GET(self) -> None:
        if not self._guard():
            return
        if self.path == "/status":
            self._send(200, status())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._guard():
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(413, {"error": "body too large"})
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            if not isinstance(body, dict):
                raise OpsError(400, "JSON 객체가 필요하다")
            log.info(
                "동작 %s %s %s",
                self.client_address[0],
                self.path,
                body.get("model", ""),
            )
            self._send(200, act(self.path, body))
        except json.JSONDecodeError:
            self._send(400, {"error": "JSON 이 아니다"})
        except OpsError as e:
            log.warning("실패 %s %s: %s", self.path, e.status, e)
            self._send(e.status, {"error": str(e)})

    def log_message(
        self, fmt: str, *args: object
    ) -> None:  # 기본 접근 로그 대신 위의 로그만
        return


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    if not TOKEN:
        raise SystemExit(
            "OPS_AGENT_TOKEN 이 비어 있다 — ~/.config/ops-agent/env 를 확인"
        )
    log.info(
        "ops-agent %s:%s (compose=%s, ollama=%s)", BIND, PORT, ARDA_COMPOSE, OLLAMA_URL
    )
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
