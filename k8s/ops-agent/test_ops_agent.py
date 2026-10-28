"""ops_agent 판정 로직 — 출발지·토큰·출력 파싱·동작 허용 목록. 실행: python3 -m pytest k8s/ops-agent -q"""

import json
from unittest import mock

import ops_agent as oa
import pytest


@pytest.fixture(autouse=True)
def _inline_jobs(monkeypatch, tmp_path):
    # 이 PC 의 실제 모드 파일(~/.config/ops-agent/arda_ai_mode)에 기대지 않는다
    monkeypatch.setattr(oa, "AI_MODE_FILE", str(tmp_path / "arda_ai_mode"))
    # 시험에서는 뒤에서 돌리지 않고 그 자리에서 끝낸다(결과를 바로 확인하려고)
    monkeypatch.setattr(oa, "RUN_IN_BACKGROUND", False)


@pytest.mark.parametrize(
    "ip,ok",
    [
        ("127.0.0.1", True),
        ("10.42.0.15", True),  # k3s 파드
        ("100.91.129.31", True),  # Tailscale(집컴)
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
