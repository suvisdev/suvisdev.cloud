# 운영 제어 에이전트 (ops-agent)

관리자 페이지의 버튼(노트북 서버 전체·Arda 켜기·끄기, GPU 모델 올리기·내리기)이 실제로 일을 시키는 곳. PC 마다 하나씩
systemd 유저 서비스로 돈다. 1단계는 노트북(Arda 온프레미스 + 노트북 Ollama GPU)만.

```
관리자 페이지 → suvisdev 백엔드 /admin/ops/*(관리자만, 2단계) → ops-agent :8210 (이 폴더)
```

| 요청 | 하는 일 |
|---|---|
| `GET /status` | 노트북 서버 켜짐·꺼짐, Arda 컨테이너 상태, GPU(VRAM·사용률), Ollama 올라간 모델·설치된 모델 |
| `POST /server/stop` · `/server/start` | 노트북 서버 전체 끄기·켜기(아래 "서버 켜기·끄기") |
| `POST /arda/start` · `/arda/stop` | `docker compose -f infra/onprem/docker-compose.yml up -d` · `stop` (Arda 저장소) |
| `POST /arda/ai-mode` `{"mode": "gpu"|"cpu"}` | 거짓말 탐지만 GPU 덮어쓰기(infra/onprem/docker-compose.gpu.yml) 포함·제외로 다시 띄움. 모드는 `~/.config/ops-agent/arda_ai_mode` 에 남아 다음 켜기에도 씀 |
| `POST /ollama/load` · `/ollama/unload` `{"model": ...}` | keep_alive -1 / 0. 임베딩 모델은 `/api/embed` 로 |

## 서버 켜기·끄기 (2026-11-06)

어드민 "노트북 서버 전체" 버튼. 끄면 이 노트북에서 백엔드·로그인·터널(k3s), Arda, Ollama, 도커, 배포 러너, 집컴 연결이 모두 멈추고
**재부팅해도 꺼진 채 남는다**. 남는 건 이 에이전트(메모리 약 14MB)와 Tailscale 뿐이다.
DB·Redis 는 집컴에 있으므로 사이트와 어드민은 집컴이 계속 받고, 켜기 요청은 집컴 백엔드가 Tailscale 로 이 에이전트에 전달한다.

| 순서 | 끄기 | 켜기 |
|---|---|---|
| 1 | **거절 검사**(접수 전, 409): 배포 중 · 스크립트 미설치 · 집컴 판단기 꺼짐 · 집컴 backend·auth 미준비 | `laptop-server-switch on` — 도커·Ollama·k3s |
| 2 | 배포 러너 끄기(유닛이 `KillMode=process` 라 Listener 까지 직접 멈춤), `serve-agent` 끄기, 집컴 심장박동에 not-serving 기록(15초를 안 기다림) | 러너·터널·집컴 연결·`serve-agent` 켜기 |
| 3 | 집컴 터널이 뜰 때까지 대기(최대 15분). **못 뜨면 러너·`serve-agent` 를 되살리고 실패 처리** — 노트북이 계속 서빙 | Arda `compose up -d` |
| 4 | 상태 파일 off, 노트북 터널 닫기, Arda `compose stop` | 노트북 터널이 뜰 때까지 대기(최대 5분). 집컴은 그 뒤 30초 있다 물러남 |
| 5 | `laptop-server-switch off` — k3s(`k3s-killall.sh` 까지, 안 그러면 파드가 남는다)·Ollama·도커·파일 캐시 | |
| 6 | 올라마 터널·집컴 연결 끄기 | |

- 끄는 동안 뉴스 수집·요약이 멈춘다(스케줄러는 노트북만). 핫한 소식 칸은 12시간 지나면 비고, AI 채팅은 Gemini 로 넘어간다. 머지한 배포는 켤 때까지 큐에서 기다린다(GitHub 는 24시간 넘게 기다린 잡을 실패시킨다).
- 꺼진 동안 Arda·Ollama 버튼은 409.
- 4번부터는 일부가 실패해도 끝까지 간다. 멈추면 절반만 꺼진 채 남기 때문이다. 같은 버튼으로 다시 시도할 수 있다.
- 집컴을 쓸 수 없을 때는 끄기가 거절된다 — 그대로 끄면 사이트 전체가 멈추고, 켜기 버튼도 쓸 수 없게 된다.

### 실측 (2026-11-06, 첫 실제 전환)

| 항목 | 결과 |
|---|---|
| 끄기 | 91초. k3s·컨테이너·Ollama 프로세스 0, 자동 시작 disabled, 집컴 파드 → 에이전트 닿음 |
| 켜기 | 50초. 파드 3·컨테이너 9·Arda 7/7 복구, 러너 online, 집컴은 켜기 완료 38초 뒤 물러남 |
| 서버 오류(5xx·530) | 바깥 요청 637건 중 **0건** |
| 10초 초과 | 끄기 전 99건 중 0 · 끄는 앞부분 94건 중 1 · **도커·k3s 를 내리는 막바지 50초 39건 중 7** · 꺼진 동안 187건 중 5 · 켜는 중·뒤 218건 중 3 |
| 메모리 | 윈도 남은 RAM 10.5GB → 17.4GB, vmmemWSL 8.8GB → 2.9GB, CPU 1~5%. 켠 직후는 4.9GB / 15.5GB(파일 캐시·요약 모델 포함) |

한계: 측정기도 같은 노트북에서 돌았고 평소에도 Cloudflare LA 경유로 시간 초과가 난다. 막바지 시간 초과가 집컴 탓인지 노트북 쪽 영향인지는 가리지 못했다. 실제 재부팅은 해 보지 않았다(자동 시작 disabled 만 확인).

**처음 한 번 직접 설치**(루트 권한이라 사용자가 실행):

```bash
sudo bash k8s/ops-agent/install-server-switch.sh   # /usr/local/sbin/laptop-server-switch + sudo 규칙(on·off 만 허용)
bash k8s/ops-agent/install.sh                      # 에이전트 코드 갱신
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
