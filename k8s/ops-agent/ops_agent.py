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
  POST /server/stop     이 노트북의 서버 전체를 끈다(k3s·Arda·Ollama·도커·배포 러너). 재부팅해도 꺼진 채 남는다.
                        집컴이 이어받은 걸 확인한 뒤에 내리므로 사이트는 끊기지 않는다. 집컴이 준비 안 됐으면 409
  POST /server/start    다시 켠다. 노트북이 서빙을 시작할 때까지 기다린다

지키는 것:
- 토큰: 헤더 X-Ops-Token 이 OPS_AGENT_TOKEN 과 같아야 한다(상수 시간 비교).
- 출발지: 자기 자신 · k3s 파드망(10.42.0.0/16) · Tailscale(100.64.0.0/10) 만. 집컴이 서빙할 때
  집컴 백엔드가 Tailscale 로 부른다. 그 밖(공유기 LAN 등)은 토큰이 맞아도 거절한다.
- 셸을 쓰지 않는다. 명령은 인자 목록으로 고정이고, 모델 이름은 Ollama 에 실제 설치된 이름만 받는다.
  루트 권한은 laptop-server-switch(루트 소유, on·off 만 허용)로만 쓴다.
- 동작(켜기·끄기·올리기·내리기)은 한 번에 하나만 — 버튼을 연달아 눌러도 겹치지 않는다(409).
- 동작은 202 로 접수하고 뒤에서 돈다(Cloudflare 100초 제한). 진행·결과는 /status 의 job.

의존성 없이 표준 라이브러리만 쓴다(WSL 의 python3 로 바로 돈다). 설치는 같은 폴더 README.
"""

from __future__ import annotations

import contextlib
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
SERVER_STATE_FILE = os.environ.get(
    "SERVER_STATE_FILE", os.path.expanduser("~/.config/ops-agent/server_state")
)
SERVER_SWITCH = os.environ.get("SERVER_SWITCH", "/usr/local/sbin/laptop-server-switch")
KUBECONFIG = os.environ.get("KUBECONFIG", "/etc/rancher/k3s/k3s.yaml")
# 집컴은 Tailscale 주소로 간다 — 노트북이 집 밖이어도 닿는다(sync-standby.sh 와 같다)
HOME_HOST = os.environ.get("HOME_SSH_HOST", "suvisdev@100.91.129.31")
HOME_KEY = os.path.expanduser("~/.ssh/home_desktop")
HOME_KNOWN_HOSTS = os.path.expanduser("~/.ssh/known_hosts_ollama_tunnel")
# 서빙 판단기는 맨 먼저 멈추고 맨 나중에 켜야 해서 따로 다룬다
SERVE_AGENT = "serve-agent"
USER_SERVICES = ("actions-runner", "ollama-tunnel", "desktop-link")
# 집컴 터널은 보통 30초 안에 뜨지만, 11-06 노트북 재부팅 때 집컴 부하가 높아 11분 걸린 적이 있다
HANDOVER_TIMEOUT = 900
HOME_SETTLE_SECONDS = 10  # 파드가 Ready 여도 Cloudflare 에 등록되기까지 잠깐 걸린다
TUNNEL_DRAIN_TIMEOUT = 45
SERVE_TIMEOUT = 300
POLL_SECONDS = 5

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


def parse_ready(stdout: str) -> dict[str, int]:
    """집컴 kubectl 출력 "backend=1" 줄들 → {이름: Ready 수}. Ready 가 없으면 값이 비어 나온다."""
    ready: dict[str, int] = {}
    for line in stdout.splitlines():
        name, sep, count = line.strip().partition("=")
        if sep and name:
            ready[name] = int(count) if count.isdigit() else 0
    return ready


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


def read_server_state() -> str:
    try:
        with open(SERVER_STATE_FILE, encoding="utf-8") as f:
            state = f.read().strip()
    except OSError:
        return "on"
    return "off" if state == "off" else "on"


def write_server_state(state: str) -> None:
    os.makedirs(os.path.dirname(SERVER_STATE_FILE), exist_ok=True)
    with open(SERVER_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(state)


def _home(command: str, timeout: int = 20) -> str:
    return _run(
        [
            "ssh",
            "-i",
            HOME_KEY,
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "-o",
            f"UserKnownHostsFile={HOME_KNOWN_HOSTS}",
            HOME_HOST,
            command,
        ],
        timeout,
    )


def _home_ready() -> dict[str, int]:
    return parse_ready(
        _home(
            "KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl -n suvisdev get deploy -o "
            "jsonpath='{range .items[*]}{.metadata.name}={.status.readyReplicas}{\"\\n\"}{end}'"
        )
    )


def _laptop_ready(deploy: str) -> int:
    out = _run(
        [
            "kubectl",
            "--kubeconfig",
            KUBECONFIG,
            "-n",
            "suvisdev",
            "get",
            "deploy",
            deploy,
            "-o",
            "jsonpath={.status.readyReplicas}",
        ],
        20,
    ).strip()
    return int(out) if out.isdigit() else 0


def _user_services(verb: str, *names: str) -> None:
    # --now 까지 해야 지금 멈추고(켜고) 재부팅 뒤에도 그대로다
    _run(["systemctl", "--user", verb, "--now", *names], 90)


def runner_busy() -> bool:
    """배포 잡이 돌고 있는가 — 러너가 잡을 받으면 Runner.Worker 가 뜬다."""
    done = subprocess.run(
        ["pgrep", "-f", "Runner.Worker"], capture_output=True, check=False
    )
    return done.returncode == 0


def check_can_stop() -> None:
    """끄면 집컴이 받아야 한다. 집컴이 못 받으면 사이트가 내려가므로 아예 시작하지 않는다."""
    if runner_busy():
        raise OpsError(409, "배포가 진행 중이다 — 끝난 뒤 다시 누른다")
    try:
        # 이게 없으면 터널과 Arda 만 끄고 멈춰 절반만 꺼진다 — 아무것도 건드리기 전에 확인한다
        _run(["sudo", "-n", "-l", SERVER_SWITCH, "off"], 10)
    except OpsError as e:
        raise OpsError(
            409,
            "켜기·끄기 스크립트가 설치되지 않았다(k8s/ops-agent/install-server-switch.sh)",
        ) from e
    try:
        active = _home("systemctl --user is-active standby-agent").strip()
        ready = _home_ready()
    except OpsError as e:
        raise OpsError(409, f"집컴에 닿지 않아 끄지 않았다: {e}") from e
    if active != "active":
        raise OpsError(409, f"집컴 예비 판단기가 멈춰 있어 끄지 않았다({active})")
    missing = [name for name in ("backend", "auth") if ready.get(name, 0) < 1]
    if missing:
        raise OpsError(409, f"집컴 {', '.join(missing)} 이 준비되지 않아 끄지 않았다")


def _wait(what: str, done, timeout: int) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if done():
                return True
        except OpsError as e:  # 전환 중에는 잠깐 안 닿을 수 있다
            log.info("%s 대기 중: %s", what, e)
        time.sleep(POLL_SECONDS)
    return False


def server_stop() -> None:
    # 1. 판단기를 멈추고 집컴에 바로 알린다(그냥 두면 심장박동이 끊긴 걸 15초 뒤에 안다)
    _user_services("disable", SERVE_AGENT)
    try:
        _home('echo "$(date +%s) not-serving off" > ~/serve/laptop_heartbeat')
        # 2. 집컴 터널이 뜰 때까지 노트북은 그대로 서빙한다. 둘이 겹쳐도 DB 가 하나라 안전하다
        if not _wait(
            "집컴 터널",
            lambda: _home_ready().get("cloudflared", 0) >= 1,
            HANDOVER_TIMEOUT,
        ):
            raise OpsError(504, "집컴이 이어받지 못해 끄지 않았다")
    except OpsError:
        _user_services("enable", SERVE_AGENT)  # 노트북이 계속 서빙한다
        raise
    time.sleep(HOME_SETTLE_SECONDS)
    write_server_state("off")
    # 3. 노트북 터널을 먼저 닫아 받던 요청을 끝내고, 그다음 나머지를 끈다.
    #    여기부터는 일부가 실패해도 계속 간다 — 멈추면 절반만 꺼진 채 남는다. 같은 버튼으로 다시 시도할 수 있다
    with contextlib.suppress(OpsError):
        _run(
            [
                "kubectl",
                "--kubeconfig",
                KUBECONFIG,
                "-n",
                "suvisdev",
                "scale",
                "deploy/cloudflared",
                "--replicas=0",
            ],
            20,
        )
        _wait(
            "노트북 터널 닫기",
            lambda: _laptop_ready("cloudflared") == 0,
            TUNNEL_DRAIN_TIMEOUT,
        )
    with contextlib.suppress(OpsError):
        _compose("stop", timeout=180)
    _run(["sudo", "-n", SERVER_SWITCH, "off"], 300)
    _user_services("disable", *USER_SERVICES)


def server_start() -> None:
    _run(["sudo", "-n", SERVER_SWITCH, "on"], 300)
    _user_services("enable", *USER_SERVICES, SERVE_AGENT)
    write_server_state("on")
    arda_error = None
    try:
        _compose("up", "-d", timeout=300)
    except OpsError as e:  # Arda 가 안 떠도 노트북 서빙은 끝까지 확인한다
        arda_error = str(e)
    # 판단기가 앱이 건강한 걸 보고 터널을 올린다. 집컴은 그 뒤 30초 있다가 물러난다
    if not _wait(
        "노트북 서빙", lambda: _laptop_ready("cloudflared") >= 1, SERVE_TIMEOUT
    ):
        raise OpsError(504, "켰지만 노트북이 아직 서빙을 시작하지 않았다")
    if arda_error:
        raise OpsError(502, f"서버는 켜졌지만 Arda 를 켜지 못했다: {arda_error}")


def status() -> dict:
    return {
        "server": {"state": read_server_state()},
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
    if path == "/server/stop":
        check_can_stop()
        return server_stop, ""
    if path == "/server/start":
        return server_start, ""
    if path.startswith(("/arda/", "/ollama/")) and read_server_state() == "off":
        raise OpsError(409, "노트북 서버가 꺼져 있다 — 먼저 켠다")
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
