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
  POST /server/stop     서버 전체를 끈다(앱·Arda·DB·Redis·lora·k3s·Ollama·도커·배포 러너). 재부팅해도 꺼진 채 남는다.
                        이 노트북이 유일한 서버라(2026-11-08~) 사이트가 내려가고 어드민도 쓸 수 없다
  POST /server/start    다시 켠다. 노트북이 서빙을 시작할 때까지 기다린다. 끈 뒤에는 바탕화면 '서버 켜기'(server_on.py)가 부른다

지키는 것:
- 토큰: 헤더 X-Ops-Token 이 OPS_AGENT_TOKEN 과 같아야 한다(상수 시간 비교).
- 출발지: 자기 자신 · k3s 파드망(10.42.0.0/16) · Tailscale(100.64.0.0/10) 만. 그 밖(공유기 LAN 등)은 토큰이 맞아도 거절한다.
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
RUNNER = "actions-runner"
# lora 는 GPU 를 쥐고 있어 같이 끄고 켠다
USER_SERVICES = ("lora-server",)
# 저장소 루트 docker-compose.yaml(프로젝트 suvisdev)의 DB·Redis. 도커 종료의 기본 15초에 맡기지 않고 DB 가 정상 종료할 시간을 준다
DATA_CONTAINERS = ("suvisdev-db-1", "suvisdev-redis-1")
APP_DEPLOYS = ("deploy/cloudflared", "deploy/backend", "deploy/auth")
# backend(DB 까지 확인하는 /healthz)와 auth(JWKS). ingress.yaml 이 둘 다 api.suvisdev.cloud 로 받는다
HEALTH_PATHS = ("/healthz", "/.well-known/jwks.json")
# 도우미를 먼저 멈춘다 — Listener 가 먼저 죽으면 도우미가 다시 띄울 수 있다
RUNNER_PROCESSES = (
    "actions-runner/run-helper.sh",
    "actions-runner/bin/Runner.Listener",
)
RUNNER_STOP_TIMEOUT = 20
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


def sudo_rule_ok(listing: str, switch: str) -> bool:
    """`sudo -n -l` 출력에 비밀번호 없는 on·off 규칙이 있는가.

    `sudo -n -l 명령 인자` 로 묻지 않는다 — 관리자 일반 권한((ALL : ALL) ALL)이 있으면 비밀번호가 필요한
    명령도 허용으로 답한다(11-06 실측: 규칙에 없는 status 도 통과).
    """
    for line in listing.splitlines():
        rule = line.partition("NOPASSWD:")[2]
        if f"{switch} on" in rule and f"{switch} off" in rule:
            return True
    return False


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


def _pkill(pattern: str) -> None:
    subprocess.run(["pkill", "-TERM", "-f", pattern], capture_output=True, check=False)


def _runner_alive() -> bool:
    done = subprocess.run(
        ["pgrep", "-f", RUNNER_PROCESSES[-1]], capture_output=True, check=False
    )
    return done.returncode == 0


def check_can_stop() -> None:
    if runner_busy():
        raise OpsError(409, "배포가 진행 중이다 — 끝난 뒤 다시 누른다")
    # 이게 없으면 터널과 Arda 만 끄고 멈춰 절반만 꺼진다 — 아무것도 건드리기 전에 확인한다
    try:
        listing = _run(["sudo", "-n", "-l"], 10)
    except OpsError:
        listing = ""
    if not sudo_rule_ok(listing, SERVER_SWITCH):
        raise OpsError(
            409,
            "켜기·끄기 스크립트가 설치되지 않았다(k8s/ops-agent/install-server-switch.sh)",
        )


def _wait(what: str, done, timeout: int) -> bool:
    deadline = time.monotonic() + timeout
    while True:  # 기한이 0 이어도 한 번은 확인한다
        try:
            if done():
                return True
        except OpsError as e:  # 전환 중에는 잠깐 안 닿을 수 있다
            log.info("%s 대기 중: %s", what, e)
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL_SECONDS)


def _stop_runner() -> None:
    """러너 유닛은 KillMode=process 라 서비스만 멈추면 Listener 가 남는다. GitHub 에 online 으로 남아
    꺼진 노트북이 배포 잡을 받게 되므로(11-06 실제 끄기에서 발견) 프로세스까지 직접 멈춘다."""
    _user_services("disable", RUNNER)
    for pattern in RUNNER_PROCESSES:
        _pkill(pattern)
    if not _wait("러너 멈춤", lambda: not _runner_alive(), RUNNER_STOP_TIMEOUT):
        raise OpsError(504, "배포 러너가 멈추지 않아 끄지 않았다")


def _scale_apps(replicas: int) -> None:
    _run(
        [
            "kubectl",
            "--kubeconfig",
            KUBECONFIG,
            "-n",
            "suvisdev",
            "scale",
            *APP_DEPLOYS,
            f"--replicas={replicas}",
        ],
        20,
    )


def server_stop() -> None:
    """앱을 먼저 끄고 DB 를 맨 나중에 끈다. 러너가 멈춘 뒤로는 일부가 실패해도 끝까지 간다 —
    멈추면 절반만 꺼진 채 남는다. 같은 버튼(또는 다시 켜기)으로 다시 시도할 수 있다."""
    try:
        # 1. 러너를 먼저 멈춰 새 배포를 받지 않게 한다
        _stop_runner()
    except OpsError:
        _user_services("enable", RUNNER)
        raise
    write_server_state("off")
    # 2. 터널을 먼저 닫아 받던 요청을 끝내고 앱을 내린다
    with contextlib.suppress(OpsError):
        _scale_apps(0)
        _wait(
            "노트북 터널 닫기",
            lambda: _laptop_ready("cloudflared") == 0,
            TUNNEL_DRAIN_TIMEOUT,
        )
    with contextlib.suppress(OpsError):
        _compose("stop", timeout=180)
    # 3. DB 는 앱이 내려간 뒤에, 도커를 끄기 전에 정상 종료한다
    with contextlib.suppress(OpsError):
        _run(["docker", "stop", "-t", "60", *DATA_CONTAINERS], 120)
    _run(["sudo", "-n", SERVER_SWITCH, "off"], 300)
    _user_services("disable", RUNNER, *USER_SERVICES)


def _app_healthy() -> bool:
    """사이트가 실제로 답하는가. 파드 준비 확인은 포트만 봐서 DB 에 못 닿아도 Ready 가 된다(11-08 리뷰) —
    옛 serve-agent 처럼 Traefik 을 거쳐 backend(DB 포함)와 auth 를 끝까지 확인한다."""
    tip = _run(
        [
            "kubectl",
            "--kubeconfig",
            KUBECONFIG,
            "-n",
            "kube-system",
            "get",
            "svc",
            "traefik",
            "-o",
            "jsonpath={.spec.clusterIP}",
        ],
        20,
    ).strip()
    for path in HEALTH_PATHS:
        req = urllib.request.Request(
            f"http://{tip}{path}", headers={"Host": "api.suvisdev.cloud"}
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                if r.status != 200:
                    return False
        except (urllib.error.URLError, OSError):
            return False
    return True


def _apps_up() -> bool:
    _scale_apps(1)
    return True


def server_start() -> None:
    _run(["sudo", "-n", SERVER_SWITCH, "on"], 300)
    # docker stop 한 컨테이너는 unless-stopped 여도 저절로 뜨지 않는다. 앱 파드는 wait-db 로 DB 를 기다린다
    _run(["docker", "start", *DATA_CONTAINERS], 120)
    _user_services("enable", *USER_SERVICES, RUNNER)
    write_server_state("on")
    # k3s 가 막 켜지면 API 가 잠깐 안 받는다 — 받을 때까지 다시 시도한다
    if not _wait("앱 켜기", _apps_up, SERVE_TIMEOUT):
        raise OpsError(504, "k3s 가 응답하지 않아 앱을 켜지 못했다")
    arda_error = None
    try:
        _compose("up", "-d", timeout=300)
    except OpsError as e:  # Arda 가 안 떠도 서빙은 끝까지 확인한다
        arda_error = str(e)
    if not _wait(
        "노트북 서빙",
        lambda: _laptop_ready("cloudflared") >= 1 and _app_healthy(),
        SERVE_TIMEOUT,
    ):
        raise OpsError(504, "켰지만 사이트가 아직 정상 응답하지 않는다")
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
    if path.startswith(("/arda/", "/ollama/")) and read_server_state() != "on":
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
