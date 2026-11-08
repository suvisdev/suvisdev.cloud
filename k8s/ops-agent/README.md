# 운영 제어 에이전트 (ops-agent)

관리자 페이지의 버튼(노트북 서버 전체·Arda 켜기·끄기, GPU 모델 올리기·내리기)이 실제로 일을 시키는 곳. PC 마다 하나씩
systemd 유저 서비스로 돈다. 1단계는 노트북(Arda 온프레미스 + 노트북 Ollama GPU)만.

```
관리자 페이지 → suvisdev 백엔드 /admin/ops/*(관리자만, 2단계) → ops-agent :8210 (이 폴더)
```

| 요청 | 하는 일 |
|---|---|
| `GET /status` | 노트북 서버 켜짐·꺼짐, Arda 컨테이너 상태, GPU(VRAM·사용률), Ollama 올라간 모델·설치된 모델 |
| `POST /server/stop` · `/server/start` | 서버 전체 끄기·켜기(아래 "서버 켜기·끄기") |
| `POST /arda/start` · `/arda/stop` | `docker compose -f infra/onprem/docker-compose.yml up -d` · `stop` (Arda 저장소) |
| `POST /arda/ai-mode` `{"mode": "gpu"|"cpu"}` | 거짓말 탐지만 GPU 덮어쓰기(infra/onprem/docker-compose.gpu.yml) 포함·제외로 다시 띄움. 모드는 `~/.config/ops-agent/arda_ai_mode` 에 남아 다음 켜기에도 씀 |
| `POST /ollama/load` · `/ollama/unload` `{"model": ...}` | keep_alive -1 / 0. 임베딩 모델은 `/api/embed` 로 |

## 서버 켜기·끄기 (2026-11-08 노트북 단독으로 바꿈)

서버는 이 노트북 한 대뿐이다(ADR-0008). 어드민 "서버 끄기"를 누르면 사이트·앱·로그인·DB·Arda 가 모두 멈추고
**재부팅해도 꺼진 채 남는다**. 남는 건 이 에이전트와 Tailscale 뿐이다. 켜기는 노트북 바탕화면 `서버 켜기.cmd`(`server_on.py`)로 한다 —
어드민은 백엔드를 거치는데 백엔드가 꺼져 있다.

| 순서 | 끄기 | 켜기 |
|---|---|---|
| 1 | **거절 검사**(접수 전, 409): 배포 중 · 스크립트 미설치 | `laptop-server-switch on` — 도커·Ollama·k3s |
| 2 | 배포 러너 끄기(유닛이 `KillMode=process` 라 Listener 까지 직접 멈춤). 못 멈추면 러너를 되살리고 실패 처리 | DB·Redis `docker start` |
| 3 | 상태 파일 off, 터널·backend·auth 0 | lora-server·러너 켜기 |
| 4 | Arda `compose stop` | 터널·backend·auth 1(k3s 가 받을 때까지 다시 시도) → Arda `compose up -d` |
| 5 | DB·Redis `docker stop -t 60`(정상 종료) | 터널 Ready + 사이트 `/healthz`·JWKS 200 까지 대기(최대 5분) |
| 6 | `laptop-server-switch off` — k3s(`k3s-killall.sh` 까지)·Ollama·도커·파일 캐시, lora-server 끄기 | |

- 3번부터는 일부가 실패해도 끝까지 간다. 멈추면 절반만 꺼진 채 남기 때문이다. 같은 버튼이나 켜기로 다시 시도할 수 있다.
- DB 는 앱이 내려간 뒤, 도커를 끄기 전에 사용자 권한으로 멈춘다. 그래서 루트 스크립트(`laptop-server-switch.sh`)는 바꿀 필요가 없었다.
- 결과는 `journalctl --user -u ops-agent` 와 에이전트 `/status` 의 job 에 남는다. 꺼진 뒤에는 어드민에서 볼 수 없다.
- 예전 구성(노트북 우선·집컴 예비, 2026-11-06 실측 끄기 91초·켜기 50초·5xx 0건)의 집컴 이어받기·전체 끄기는 삭제했다(git 기록에 남음).

**처음 한 번 직접 설치**(루트 권한이라 사용자가 실행):

```bash
sudo bash k8s/ops-agent/install-server-switch.sh   # /usr/local/sbin/laptop-server-switch + sudo 규칙(on·off 만 허용)
bash k8s/ops-agent/install.sh                      # 에이전트 코드 갱신 + 바탕화면 `서버 켜기.cmd`
```

## 지키는 것

- 헤더 `X-Ops-Token` = `~/.config/ops-agent/env` 의 `OPS_AGENT_TOKEN` (백엔드 .env 에 같은 값)
- 출발지 제한: 127.0.0.0/8 · k3s 파드망 10.42.0.0/16 · Tailscale 100.64.0.0/10. 공유기 LAN 은 거절
- 셸 없음, 명령은 고정 인자 목록, 모델은 설치된 이름만, 동작은 한 번에 하나(겹치면 409)
- 루트 권한은 `laptop-server-switch`(루트 소유, 에이전트가 고칠 수 없음)의 `on`·`off` 만

## 설치 · 갱신 (노트북 WSL)

```bash
bash k8s/ops-agent/install.sh        # 토큰 생성(처음만) · 서비스 등록 · 시작. 다시 돌리면 코드만 갱신
journalctl --user -u ops-agent -f   # 로그
```

실행 파일은 `~/.local/lib/ops-agent/ops_agent.py` 로 복사해 돌린다 — 운영 hostPath 저장소 사본과 떼어 둔다.

## 시험

```bash
python3 -m pytest k8s/ops-agent -q   # 출발지·토큰·파싱·허용 목록·AI 모드·서버 켜기·끄기(43개)
```

2026-10-28 노트북 실측: `/status` 로 Arda 7개 컨테이너·RTX 4060 VRAM·설치 모델 6개를 읽음,
없는 모델 404, nomic-embed-text 올리기→올라감·내리기→내려감, 토큰 없으면 401.

2026-10-28 GPU 모드 실측: `/arda/ai-mode gpu` → 거짓말 탐지 STT_DEVICE=cuda, 5초 오디오 전사 0.62초, VRAM 약 1.3GB.
