"""ops_agent 판정 로직 — 출발지·토큰·출력 파싱·동작 허용 목록. 실행: python3 -m pytest k8s/ops-agent -q"""

import json
from unittest import mock

import ops_agent as oa
import pytest
import server_on


@pytest.fixture(autouse=True)
def _inline_jobs(monkeypatch, tmp_path):
    # 이 PC 의 실제 모드 파일(~/.config/ops-agent/arda_ai_mode)에 기대지 않는다
    monkeypatch.setattr(oa, "AI_MODE_FILE", str(tmp_path / "arda_ai_mode"))
    monkeypatch.setattr(oa, "SERVER_STATE_FILE", str(tmp_path / "server_state"))
    monkeypatch.setattr(oa, "POLL_SECONDS", 0)
    # 시험에서는 뒤에서 돌리지 않고 그 자리에서 끝낸다(결과를 바로 확인하려고)
    monkeypatch.setattr(oa, "RUN_IN_BACKGROUND", False)


@pytest.mark.parametrize(
    "ip,ok",
    [
        ("127.0.0.1", True),
        ("10.42.0.15", True),  # k3s 파드
        ("100.91.129.31", True),  # Tailscale
        ("::ffff:10.42.0.9", True),
        ("172.30.1.21", False),  # 공유기 LAN — 토큰이 맞아도 거절
        ("172.24.60.1", False),  # WSL NAT 게이트웨이(윈도우 쪽)
        ("8.8.8.8", False),
        ("garbage", False),
    ],
)
def test_source_allowed(ip, ok):
    assert oa.source_allowed(ip) is ok


def test_token_ok():
    assert oa.token_ok("secret", "secret")
    assert not oa.token_ok("wrong", "secret")
    assert not oa.token_ok(None, "secret")
    # 토큰을 안 넣은 에이전트는 빈 헤더와도 같다고 보지 않는다
    with mock.patch.object(oa, "TOKEN", ""):
        assert not oa.token_ok("", "")


def test_parse_compose_ps_both_formats():
    rows = [
        {"Service": "api", "State": "running", "Status": "Up 2 hours"},
        {"Service": "db", "State": "exited", "Status": "Exited (0)"},
    ]
    lines = "\n".join(json.dumps(r) for r in rows)
    expected = [
        {"service": "api", "state": "running", "status": "Up 2 hours"},
        {"service": "db", "state": "exited", "status": "Exited (0)"},
    ]
    assert oa.parse_compose_ps(lines) == expected
    assert oa.parse_compose_ps(json.dumps(rows)) == expected
    assert oa.parse_compose_ps("") == []


def test_parse_nvidia_smi():
    out = "NVIDIA GeForce RTX 4060 Laptop GPU, 2263, 8188, 25\n"
    assert oa.parse_nvidia_smi(out) == [
        {
            "name": "NVIDIA GeForce RTX 4060 Laptop GPU",
            "memory_used_mib": 2263,
            "memory_total_mib": 8188,
            "utilization_pct": 25,
        }
    ]


def test_unknown_action_and_uninstalled_model():
    with pytest.raises(oa.OpsError) as e:
        oa.act("/rm-rf", {})
    assert e.value.status == 404
    with mock.patch.object(
        oa, "ollama_status", return_value={"installed": ["exaone3.5:7.8b"]}
    ):
        with pytest.raises(oa.OpsError) as e:
            oa.act("/ollama/load", {"model": "evil; rm -rf /"})
        assert e.value.status == 404
        with pytest.raises(oa.OpsError) as e:
            oa.act("/ollama/load", {})
        assert e.value.status == 400


def test_load_sends_keep_alive_forever_and_unload_zero():
    calls = []
    with (
        mock.patch.object(
            oa, "ollama_status", return_value={"installed": ["exaone3.5:7.8b"]}
        ),
        mock.patch.object(
            oa,
            "_ollama",
            side_effect=lambda path, body=None, timeout=10: (
                calls.append((path, body)) or {}
            ),
        ),
    ):
        oa.act("/ollama/load", {"model": "exaone3.5:7.8b"})
        oa.act("/ollama/unload", {"model": "exaone3.5:7.8b"})
    assert calls[0] == (
        "/api/generate",
        {"model": "exaone3.5:7.8b", "prompt": "", "keep_alive": -1, "stream": False},
    )
    assert calls[1][1]["keep_alive"] == 0


def test_embedding_model_falls_back_to_embed_api():
    calls = []

    def fake(path, body=None, timeout=10):
        calls.append(path)
        if path == "/api/generate":
            err = oa.OpsError(502, "Ollama 400: does not support generate")
            err.ollama_code = 400
            raise err
        return {}

    with (
        mock.patch.object(
            oa, "ollama_status", return_value={"installed": ["bge-m3:latest"]}
        ),
        mock.patch.object(oa, "_ollama", side_effect=fake),
    ):
        oa.act("/ollama/load", {"model": "bge-m3:latest"})
    assert calls == ["/api/generate", "/api/embed"]


def test_actions_do_not_overlap():
    assert oa._action_lock.acquire(blocking=False)
    try:
        with pytest.raises(oa.OpsError) as e:
            oa.act("/arda/start", {})
        assert e.value.status == 409
    finally:
        oa._action_lock.release()


def test_arda_commands_are_fixed_argument_lists():
    seen = []
    with mock.patch.object(
        oa, "_run", side_effect=lambda args, timeout: seen.append(args) or ""
    ):
        oa.act("/arda/stop", {})
    assert seen[0] == ["docker", "compose", "-f", oa.ARDA_COMPOSE, "stop"]


def test_ai_mode_rejects_unknown_value():
    with pytest.raises(oa.OpsError) as e:
        oa.act("/arda/ai-mode", {"mode": "tpu"})
    assert e.value.status == 400


def test_ai_mode_gpu_recreates_only_lie_detection_and_remembers(tmp_path):
    seen = []
    mode_file = tmp_path / "arda_ai_mode"
    with (
        mock.patch.object(oa, "AI_MODE_FILE", str(mode_file)),
        mock.patch.object(
            oa, "_run", side_effect=lambda args, timeout: seen.append(args) or ""
        ),
    ):
        oa.act("/arda/ai-mode", {"mode": "gpu"})
        assert mode_file.read_text() == "gpu"
        seen.clear()
        oa.act("/arda/start", {})  # 다음 켜기도 GPU 덮어쓰기를 같이 쓴다
    assert seen[0] == [
        "docker",
        "compose",
        "-f",
        oa.ARDA_COMPOSE,
        "-f",
        oa.ARDA_COMPOSE_GPU,
        "up",
        "-d",
    ]


def test_ai_mode_defaults_to_cpu_when_file_missing_or_garbage(tmp_path):
    f = tmp_path / "m"
    with mock.patch.object(oa, "AI_MODE_FILE", str(f)):
        assert oa.read_ai_mode() == "cpu"
        f.write_text("quantum")
        assert oa.read_ai_mode() == "cpu"
        assert oa.compose_files("cpu") == ["-f", oa.ARDA_COMPOSE]


def test_background_job_is_reported_in_status(monkeypatch):
    monkeypatch.setattr(oa, "RUN_IN_BACKGROUND", True)
    done = __import__("threading").Event()
    monkeypatch.setattr(oa, "_compose", lambda *a, **k: done.wait(2) or "")
    res = oa.act("/arda/stop", {})
    assert res["accepted"] and res["job"]["state"] == "running"
    with pytest.raises(oa.OpsError) as e:  # 도는 동안 다른 동작은 409
        oa.act("/arda/start", {})
    assert e.value.status == 409
    done.set()
    for _ in range(50):
        if oa.job_snapshot()["state"] != "running":
            break
        __import__("time").sleep(0.02)
    assert oa.job_snapshot()["state"] == "ok"
    assert oa._action_lock.acquire(blocking=False)
    oa._action_lock.release()


def test_failed_job_records_error_and_releases_lock(monkeypatch):
    def boom(*a, **k):
        raise oa.OpsError(502, "compose 실패")

    monkeypatch.setattr(oa, "_compose", boom)
    with pytest.raises(oa.OpsError):
        oa.act("/arda/start", {})
    assert (
        oa.job_snapshot()["state"] == "failed"
        and "compose 실패" in oa.job_snapshot()["error"]
    )
    assert oa._action_lock.acquire(blocking=False)
    oa._action_lock.release()


# ── 노트북 서버 켜기·끄기 ──────────────────────────────────────


SUDO_LISTING = """User suteagy may run the following commands on teagy:
    (ALL : ALL) ALL
    (ALL) NOPASSWD: /usr/local/bin/k3s
    (root) NOPASSWD: {switch} on, {switch} off
"""


class _Laptop:
    """명령을 순서대로 기록하고, 노트북 상태(터널 Ready 수)를 흉내 낸다."""

    def __init__(self, monkeypatch):
        self.calls: list[list[str]] = []
        self.fail: str | None = None  # 이 문자열이 든 명령은 실패한다
        self.laptop_tunnel = "1"
        self.serves_after_scale = True  # 앱을 1로 올리면 터널이 Ready 가 되는가
        self.healthy = True  # 사이트(backend /healthz·auth JWKS)가 200 인가
        self.sudo_listing = SUDO_LISTING.format(switch=oa.SERVER_SWITCH)
        self.runner_alive = False
        monkeypatch.setattr(oa, "_run", self.run)
        monkeypatch.setattr(oa, "runner_busy", lambda: False)
        monkeypatch.setattr(oa, "_pkill", lambda p: self.calls.append(["pkill", p]))
        monkeypatch.setattr(oa, "_runner_alive", lambda: self.runner_alive)
        monkeypatch.setattr(oa, "_app_healthy", lambda: self.healthy)

    def run(self, args, timeout):
        joined = " ".join(args)
        self.calls.append(args)
        if self.fail and self.fail in joined:
            raise oa.OpsError(502, f"실패: {self.fail}")
        if args[:3] == ["sudo", "-n", "-l"]:
            return self.sudo_listing
        if "scale" in args:
            up = "--replicas=1" in args and self.serves_after_scale
            self.laptop_tunnel = "1" if up else ""
        if "get" in args and "cloudflared" in args:
            return self.laptop_tunnel
        return ""

    def switched(self, arg: str) -> bool:
        """사전 검사(sudo -n -l)가 아니라 실제로 켜기·끄기를 불렀는가."""
        return ["sudo", "-n", oa.SERVER_SWITCH, arg] in self.calls

    def has(self, *words: str) -> bool:
        return any(all(w in " ".join(c) for w in words) for c in self.calls)

    def index(self, *words: str) -> int:
        return next(
            i for i, c in enumerate(self.calls) if all(w in " ".join(c) for w in words)
        )


def test_server_state_defaults_to_on(tmp_path):
    assert oa.read_server_state() == "on"
    oa.write_server_state("off")
    assert oa.read_server_state() == "off"
    with open(oa.SERVER_STATE_FILE, "w", encoding="utf-8") as f:
        f.write("garbage")
    assert oa.read_server_state() == "on"


def test_status_reports_server_state(monkeypatch):
    monkeypatch.setattr(oa, "arda_status", dict)
    monkeypatch.setattr(oa, "gpu_status", list)
    monkeypatch.setattr(oa, "ollama_status", dict)
    oa.write_server_state("off")
    assert oa.status()["server"] == {"state": "off"}


def test_stop_shuts_apps_before_db_and_db_before_docker(monkeypatch):
    lap = _Laptop(monkeypatch)
    oa.act("/server/stop", {})
    assert oa.job_snapshot()["state"] == "ok"
    assert oa.read_server_state() == "off"
    order = [
        lap.index("disable", "actions-runner"),  # 새 배포를 받지 않게 러너부터
        lap.calls.index(["pkill", "actions-runner/bin/Runner.Listener"]),
        lap.index("scale", "deploy/cloudflared", "deploy/backend", "--replicas=0"),
        lap.index("compose", "stop"),  # Arda
        lap.index("docker", "stop", "-t", "60", "suvisdev-db-1", "suvisdev-redis-1"),
        lap.calls.index(["sudo", "-n", oa.SERVER_SWITCH, "off"]),  # k3s·Ollama·도커
        lap.index("disable", "lora-server"),
    ]
    assert order == sorted(order)


def test_stop_refused_when_switch_not_installed(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.fail = "sudo -n -l"
    with pytest.raises(oa.OpsError) as e:
        oa.act("/server/stop", {})
    assert e.value.status == 409 and "install-server-switch" in str(e.value)
    assert not lap.has("disable") and oa.read_server_state() == "on"


def test_sudo_rule_needs_passwordless_on_and_off():
    s = oa.SERVER_SWITCH
    assert oa.sudo_rule_ok(SUDO_LISTING.format(switch=s), s)
    # 관리자 일반 권한만 있으면 비밀번호가 필요하다 — 11-06 실측: 이때 sudo -n -l 명령 은 허용이라 답한다
    assert not oa.sudo_rule_ok("    (ALL : ALL) ALL\n", s)
    assert not oa.sudo_rule_ok(f"    (ALL : ALL) ALL {s} on, {s} off\n", s)
    assert not oa.sudo_rule_ok(f"    (root) NOPASSWD: {s} on\n", s)
    assert not oa.sudo_rule_ok("", s)


def test_stop_refused_with_only_general_sudo(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.sudo_listing = "    (ALL : ALL) ALL\n"
    with pytest.raises(oa.OpsError) as e:
        oa.act("/server/stop", {})
    assert e.value.status == 409 and "install-server-switch" in str(e.value)
    assert not lap.has("disable")


def test_stop_aborts_and_restores_when_runner_will_not_die(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.runner_alive = True
    monkeypatch.setattr(oa, "RUNNER_STOP_TIMEOUT", 0)
    with pytest.raises(oa.OpsError):
        oa.act("/server/stop", {})
    assert "러너" in oa.job_snapshot()["error"] and oa.read_server_state() == "on"
    assert lap.has("enable", "actions-runner")
    assert not lap.has("scale") and not lap.switched("off")


def test_stop_refused_during_deploy(monkeypatch):
    lap = _Laptop(monkeypatch)
    monkeypatch.setattr(oa, "runner_busy", lambda: True)
    with pytest.raises(oa.OpsError) as e:
        oa.act("/server/stop", {})
    assert e.value.status == 409 and "배포" in str(e.value) and lap.calls == []


def test_stop_continues_when_arda_fails_so_nothing_is_left_half_off(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.fail = "compose"
    oa.act("/server/stop", {})
    assert oa.job_snapshot()["state"] == "ok"
    assert lap.has("docker", "stop") and lap.switched("off")


def test_stop_still_switches_off_when_db_stop_fails(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.fail = "docker stop"
    oa.act("/server/stop", {})
    assert lap.switched("off") and oa.read_server_state() == "off"


def test_start_brings_db_up_before_apps(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.laptop_tunnel = ""
    oa.write_server_state("off")
    oa.act("/server/start", {})
    assert oa.job_snapshot()["state"] == "ok" and oa.read_server_state() == "on"
    order = [
        lap.calls.index(["sudo", "-n", oa.SERVER_SWITCH, "on"]),
        lap.index("docker", "start", "suvisdev-db-1", "suvisdev-redis-1"),
        lap.index("enable", "lora-server", "actions-runner"),
        lap.index("scale", "deploy/cloudflared", "--replicas=1"),
        lap.index("compose", "up"),
    ]
    assert order == sorted(order)


def test_start_retries_scale_until_k3s_answers(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.laptop_tunnel = ""
    real = lap.run
    tries = {"n": 0}

    def flaky(args, timeout):
        if "scale" in args and tries["n"] < 2:
            tries["n"] += 1
            lap.calls.append(args)
            raise oa.OpsError(502, "k3s 아직")
        return real(args, timeout)

    monkeypatch.setattr(oa, "_run", flaky)
    oa.act("/server/start", {})
    assert oa.job_snapshot()["state"] == "ok" and tries["n"] == 2


def test_start_reports_arda_failure_but_stays_on(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.fail = "compose"
    oa.write_server_state("off")
    with pytest.raises(oa.OpsError):
        oa.act("/server/start", {})
    assert "Arda" in oa.job_snapshot()["error"] and oa.read_server_state() == "on"


def test_start_times_out_when_laptop_never_serves(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.laptop_tunnel = ""
    lap.serves_after_scale = False
    monkeypatch.setattr(oa, "SERVE_TIMEOUT", 0)
    with pytest.raises(oa.OpsError):
        oa.act("/server/start", {})
    assert "정상 응답" in oa.job_snapshot()["error"]


def test_start_fails_while_site_is_unhealthy_even_if_tunnel_is_ready(monkeypatch):
    lap = _Laptop(monkeypatch)
    lap.healthy = False  # 예: DB 복구가 늦어 backend 가 503
    monkeypatch.setattr(oa, "SERVE_TIMEOUT", 0)
    with pytest.raises(oa.OpsError):
        oa.act("/server/start", {})
    assert "정상 응답" in oa.job_snapshot()["error"]


@pytest.mark.parametrize(
    "path,body",
    [
        ("/arda/start", {}),
        ("/arda/stop", {}),
        ("/arda/ai-mode", {"mode": "gpu"}),
        ("/ollama/load", {"model": "x"}),
    ],
)
def test_other_actions_refused_while_server_off(path, body):
    oa.write_server_state("off")
    with pytest.raises(oa.OpsError) as e:
        oa.act(path, body)
    assert e.value.status == 409


def test_unknown_action_is_still_404_while_off():
    oa.write_server_state("off")
    with pytest.raises(oa.OpsError) as e:
        oa.act("/rm-rf", {})
    assert e.value.status == 404


def test_stop_all_is_gone():
    with pytest.raises(oa.OpsError) as e:
        oa.act("/server/stop-all", {})
    assert e.value.status == 404


def test_shortcut_reads_token_from_env_file():
    assert server_on.read_token("A=1\nOPS_AGENT_TOKEN=abc\n") == "abc"
    assert server_on.read_token("A=1\n") == ""
