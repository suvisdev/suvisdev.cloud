# 운영 제어 에이전트 (ops-agent)

관리자 페이지의 버튼(켜기·끄기, GPU 모델 올리기·내리기)이 실제로 일을 시키는 곳. PC 마다 하나씩
systemd 유저 서비스로 돈다. 1단계는 노트북(Arda 온프레미스 + 노트북 Ollama GPU)만.

```
관리자 페이지 → suvisdev 백엔드 /admin/ops/*(관리자만, 2단계) → ops-agent :8210 (이 폴더)
```

| 요청 | 하는 일 |
|---|---|
| `GET /status` | Arda 컨테이너 상태, GPU(VRAM·사용률), Ollama 올라간 모델·설치된 모델 |
| `POST /arda/start` · `/arda/stop` | `docker compose -f infra/onprem/docker-compose.yml up -d` · `stop` (Arda 저장소) |
| `POST /arda/ai-mode` `{"mode": "gpu"|"cpu"}` | 거짓말 탐지만 GPU 덮어쓰기(infra/onprem/docker-compose.gpu.yml) 포함·제외로 다시 띄움. 모드는 `~/.config/ops-agent/arda_ai_mode` 에 남아 다음 켜기에도 씀 |
| `POST /ollama/load` · `/ollama/unload` `{"model": ...}` | keep_alive -1 / 0. 임베딩 모델은 `/api/embed` 로 |

## 지키는 것

- 헤더 `X-Ops-Token` = `~/.config/ops-agent/env` 의 `OPS_AGENT_TOKEN` (백엔드 .env 에 같은 값)
- 출발지 제한: 127.0.0.0/8 · k3s 파드망 10.42.0.0/16 · Tailscale 100.64.0.0/10. 공유기 LAN 은 거절
- 셸 없음, 명령은 고정 인자 목록, 모델은 설치된 이름만, 동작은 한 번에 하나(겹치면 409)

## 설치 · 갱신 (노트북 WSL)

```bash
bash k8s/ops-agent/install.sh        # 토큰 생성(처음만) · 서비스 등록 · 시작. 다시 돌리면 코드만 갱신
journalctl --user -u ops-agent -f   # 로그
```

실행 파일은 `~/.local/lib/ops-agent/ops_agent.py` 로 복사해 돌린다 — 운영 hostPath 저장소 사본과 떼어 둔다.

## 시험

```bash
python3 -m pytest k8s/ops-agent -q   # 출발지·토큰·파싱·허용 목록·AI 모드(19개)
```

2026-10-28 노트북 실측: `/status` 로 Arda 7개 컨테이너·RTX 4060 VRAM·설치 모델 6개를 읽음,
없는 모델 404, nomic-embed-text 올리기→올라감·내리기→내려감, 토큰 없으면 401.

2026-10-28 GPU 모드 실측: `/arda/ai-mode gpu` → 거짓말 탐지 STT_DEVICE=cuda, 5초 오디오 전사 0.62초, VRAM 약 1.3GB.
