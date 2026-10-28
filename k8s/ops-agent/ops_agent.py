"""운영 제어 에이전트 — 관리자 페이지 버튼이 이 PC 에서 할 수 있는 일을 정해 둔 목록만큼만 한다.

호출하는 쪽은 suvisdev 백엔드(/admin/ops/*, 관리자 로그인 필수)뿐이다. 브라우저가 직접 부르지 않는다.
할 수 있는 일(이 밖의 요청은 전부 404):

  GET  /status          Arda 컨테이너 상태 · GPU(VRAM) · Ollama 에 올라간 모델과 설치된 모델
  POST /arda/start      docker compose up -d   (infra/onprem — 노트북 온프레미스 Arda)
  POST /arda/stop       docker compose stop    (unless-stopped 라 다음 부팅에도 꺼진 채 남는다)
  POST /arda/ai-mode    {"mode": "gpu"|"cpu"}  거짓말 탐지(음성 인식·표정)를 GPU 또는 CPU 로 다시 띄운다.
                        고른 모드는 파일에 남아, 다음 /arda/start 도 그 모드로 켠다
  POST /ollama/load     {"model": "..."}  모델을 GPU 에 올려 둔다(keep_alive -1)
  POST /ollama/unload   {"model": "..."}  모델을 내린다(keep_alive 0)

지키는 것:
- 토큰: 헤더 X-Ops-Token 이 OPS_AGENT_TOKEN 과 같아야 한다(상수 시간 비교).
- 출발지: 자기 자신 · k3s 파드망(10.42.0.0/16) · Tailscale(100.64.0.0/10) 만. 집컴이 서빙할 때
  집컴 백엔드가 Tailscale 로 부른다. 그 밖(공유기 LAN 등)은 토큰이 맞아도 거절한다.
- 셸을 쓰지 않는다. 명령은 인자 목록으로 고정이고, 모델 이름은 Ollama 에 실제 설치된 이름만 받는다.
- 동작(켜기·끄기·올리기·내리기)은 한 번에 하나만 — 버튼을 연달아 눌러도 겹치지 않는다(409).
- 동작은 202 로 접수하고 뒤에서 돈다(Cloudflare 100초 제한). 진행·결과는 /status 의 job.

의존성 없이 표준 라이브러리만 쓴다(WSL 의 python3 로 바로 돈다). 설치는 같은 폴더 README.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# systemd 유저 서비스의 PATH 에는 WSL GPU 도구 폴더(/usr/lib/wsl/lib)가 없다(2026-10-28 실측 — GPU 칸이 비었다)
NVIDIA_SMI = shutil.which("nvidia-smi") or "/usr/lib/wsl/lib/nvidia-smi"
TOKEN = os.environ.get("OPS_AGENT_TOKEN", "")
BIND = os.environ.get("OPS_AGENT_BIND", "0.0.0.0")
PORT = int(os.environ.get("OPS_AGENT_PORT", "8210"))
ARDA_COMPOSE = os.environ.get(
    "ARDA_COMPOSE", "/mnt/c/Team Seuk/Arda/infra/onprem/docker-compose.yml"
)
ARDA_COMPOSE_GPU = os.environ.get(
    "ARDA_COMPOSE_GPU",
    os.path.join(os.path.dirname(ARDA_COMPOSE), "docker-compose.gpu.yml"),
)
AI_MODE_FILE = os.environ.get(
    "ARDA_AI_MODE_FILE", os.path.expanduser("~/.config/ops-agent/arda_ai_mode")
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


def read_ai_mode() -> str:
    try:
        with open(AI_MODE_FILE, encoding="utf-8") as f:
            mode = f.read().strip()
    except OSError:
        return "cpu"
    return mode if mode in ("gpu", "cpu") else "cpu"


def write_ai_mode(mode: str) -> None:
    os.makedirs(os.path.dirname(AI_MODE_FILE), exist_ok=True)
    with open(AI_MODE_FILE, "w", encoding="utf-8") as f:
        f.write(mode)


def compose_files(mode: str) -> list[str]:
    files = ["-f", ARDA_COMPOSE]
    if mode == "gpu":
        files += ["-f", ARDA_COMPOSE_GPU]
    return files


def _compose(*cmd: str, timeout: int, mode: str | None = None) -> str:
    files = compose_files(mode if mode is not None else read_ai_mode())
    return _run(["docker", "compose", *files, *cmd], timeout)


def lie_detection_device() -> str | None:
    """지금 떠 있는 거짓말 탐지 컨테이너의 STT_DEVICE — 파일에 적힌 모드와 실제가 다를 때 보이려고."""
    try:
        cid = _compose("ps", "-q", "lie-detection", timeout=20).strip()
        if not cid:
            return None
        env = _run(["docker", "inspect", "-f", "{{json .Config.Env}}", cid], timeout=10)
    except OpsError:
        return None
    for item in json.loads(env or "[]"):
        if item.startswith("STT_DEVICE="):
            return item.split("=", 1)[1]
    return "cpu"


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
            "ai_mode": read_ai_mode(),
            "ai_device": lie_detection_device(),
        }
    except OpsError as e:
        return {"available": False, "error": str(e)}


def gpu_status() -> list[dict]:
    try:
        out = _run(
            [
                NVIDIA_SMI,
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
    return {
        "arda": arda_status(),
        "gpu": gpu_status(),
        "ollama": ollama_status(),
        "job": job_snapshot(),
    }


def _installed_model(model: object) -> str:
    if not isinstance(model, str) or not model:
        raise OpsError(400, "model 이 필요하다")
    names = ollama_status().get("installed", [])
    if model not in names:
        raise OpsError(404, f"설치되지 않은 모델: {model}")
    return model


# 오래 걸리는 동작(Arda 켜기·GPU 전환·모델 로드)은 1~3분 — Cloudflare 가 100초 넘는 요청을 524 로 끊으므로
# 받자마자 202 로 접수하고 뒤에서 돌린다. 진행·결과는 /status 의 job 으로 본다(2026-10-28).
RUN_IN_BACKGROUND = True
_job: dict = {
    "action": None,
    "target": "",
    "state": "idle",
    "error": None,
    "started_at": None,
    "finished_at": None,
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def job_snapshot() -> dict:
    return dict(_job)


def _plan(path: str, body: dict):
    """입력 검사는 여기서 바로 한다(잘못된 요청은 접수 전에 400·404). 실제 일은 돌려주는 함수가 한다."""
    if path == "/arda/start":
        return (lambda: _compose("up", "-d", timeout=300)), ""
    if path == "/arda/stop":
        return (lambda: _compose("stop", timeout=180)), ""
    if path == "/arda/ai-mode":
        mode = body.get("mode")
        if mode not in ("gpu", "cpu"):
            raise OpsError(400, 'mode 는 "gpu" 또는 "cpu"')

        def switch() -> None:
            # 거짓말 탐지만 다시 만든다 — api·db 는 그대로라 로그인·화면은 끊기지 않는다
            _compose("up", "-d", "lie-detection", timeout=300, mode=mode)
            write_ai_mode(mode)

        return switch, mode
    if path in ("/ollama/load", "/ollama/unload"):
        model = _installed_model(body.get("model"))
        # 빈 프롬프트 + keep_alive -1: 생성 없이 GPU 에 올려 두기만 한다(Ollama 공식 방법), 0 이면 내린다
        keep = -1 if path == "/ollama/load" else 0
        return (lambda: _keep_alive(model, keep)), model
    raise OpsError(404, "없는 동작")


def _finish(fn) -> None:
    try:
        fn()
        _job.update(state="ok", error=None, finished_at=_now())
    except OpsError as e:
        _job.update(state="failed", error=str(e), finished_at=_now())
        log.warning("실패 %s: %s", _job["action"], e)
    except Exception as e:  # 뒤에서 도는 동작이 죽어도 잠금은 풀어야 한다
        _job.update(
            state="failed", error=f"{type(e).__name__}: {e}", finished_at=_now()
        )
        log.exception("예외 %s", _job["action"])
    finally:
        _action_lock.release()


def act(path: str, body: dict) -> dict:
    if not _action_lock.acquire(blocking=False):
        raise OpsError(409, "다른 동작이 진행 중이다 — 끝난 뒤 다시 누른다")
    try:
        fn, target = _plan(path, body)
    except Exception:
        _action_lock.release()
        raise
    _job.update(
        action=path,
        target=target,
        state="running",
        error=None,
        started_at=_now(),
        finished_at=None,
    )
    if RUN_IN_BACKGROUND:
        threading.Thread(target=_finish, args=(fn,), daemon=True).start()
    else:
        _finish(fn)
        if _job["state"] == "failed":
            raise OpsError(502, _job["error"] or "실패")
    return {"accepted": True, "job": job_snapshot()}


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
            self._send(202, act(self.path, body))
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
