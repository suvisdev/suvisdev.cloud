# 노트북 우선 서빙 · 꺼지면 집컴 (2026-10-05)

노트북(teagy, RTX 4060 · 16코어 · 15GB)이 켜져 있으면 노트북이 api./auth.suvisdev.cloud 를 받고,
꺼지면 집컴(DESKTOP-T89E5ID, 8.9GB)이 받는다. **DB·Redis는 집컴 한 곳**이라 어느 쪽이 받든 데이터가 갈라지지 않는다.

```
                Cloudflare 터널 (같은 토큰, 커넥터 2개 중 판단기가 켠 쪽)
                  │                                   │
   노트북 cloudflared(1/0)                    집컴 cloudflared(0/1)
   노트북 backend·auth (k3s)                  집컴 backend·auth (k3s, 예비 · mova 부팅 작업 끔)
     │ desktop-link (ssh -L)                    │
     ├─ 5432 · 6379 ───────────────────────────▶ 집컴 DB(pgvector)·Redis (도커)  ← 유일한 데이터
     ├─ 8200 ──────────────────────────────────▶ 집컴 lora-server (GTX 1650)
     └─ 11435 노트북 올라마 중계기 → 노트북 GPU 올라마 (안 되면 21435 → 집컴 올라마)
```

## 판단기 두 개

| 어디 | 서비스 | 규칙 |
|---|---|---|
| 노트북 | `serve-agent` (`serve_agent.sh`) | 5초마다 Traefik → backend → 집컴 DB 를 타는 요청 1건. 2번 연속 200이면 노트북 터널 1, 3번 연속 실패면 0. 매 주기 집컴 `~/serve/laptop_heartbeat` 에 상태 기록 |
| 집컴 | `standby-agent` (`standby_agent.sh`) | 심장박동이 15초 넘게 끊기거나 serving 이 아니면 집컴 터널 1. 노트북이 30초 연속 serving 이면 0 |

두 터널이 잠깐 겹치는 동안(노트북 복귀 후 30초)은 Cloudflare 가 둘에 나눠 보낸다 — DB가 하나라 안전하다.
mova 부팅 작업(스케줄러)은 노트북만 돈다: 집컴 `.env` 에 `ENABLE_MOVA_STARTUP=false`.

## 실측 (2026-10-05)

| 상황 | 결과 |
|---|---|
| 집컴 → 노트북 첫 전환 | 공개 API 요청 24회 실패 0. 노트북 서빙 22:40:19, 집컴 물러남 22:40:50 |
| 노트북 WSL 종료(꺼짐 흉내) | 공개 API **530 약 31초**(22:43:48~22:44:19), 이후 집컴이 정상 서빙 |
| 노트북 WSL 재시작(켜짐) | 46초 뒤 노트북 서빙(22:47:47), 32초 뒤 집컴 물러남. 그 사이 60여 회 중 8초 시간 초과 2회 |
| 예비 동기화 첫 실행 | 레지스트리가 비어 있어 전 레이어 전송 약 12분. 이후는 바뀐 레이어만 |
| 첫 실전 CD (#170) | 16분 36초 = 노트북 빌드·배포 5분 28초 · push 2분 20초 · **집컴 save→import 6분 56초** · 재시작 1분 30초 |
| 집컴 k3s 직접 pull 시험 (10-06) | 레지스트리에서 받기 1.9초(레이어가 이미 있을 때) |

## 배포 (CD)

`backend-deploy.yml` 의 러너는 **노트북**(라벨 `prod`, 집컴 러너는 10-05 등록 해제).
1. `deploy.sh --external-db --build` — 노트북에서 빌드(집컴 15분 빌드·메모리 고갈 없음)
2. `sync-standby.sh` — 집컴 로컬 레지스트리(`standby-registry`, 127.0.0.1:5000)로 바뀐 레이어만 push →
   같은 매니페스트를 집컴 사본만 `image: 127.0.0.1:5000/suvisdev-app:latest`·`imagePullPolicy: Always`로 바꿔 apply →
   backend·auth 재시작 — 집컴 k3s가 레지스트리에서 바뀐 레이어만 직접 받는다. **집컴은 빌드하지 않는다.**
   (10-06 전에는 집컴에서 docker pull → save → `k3s ctr import`로 5.8GB를 통째 옮겨 이 단계만 약 7분이었다.)

노트북이 꺼져 있는 동안 머지하면 배포 잡은 노트북이 켜질 때까지 대기한다(집컴은 그동안 직전 버전으로 서빙).

**노트북이 집 밖일 때(10-06 수정).** 예전엔 `desktop-link`(내부 IP)가 끊겨 노트북 새 파드가 init `wait-db`에서 멈추고
rollout 600초 타임아웃 → 집컴 동기화가 실행되지 않아 실제 서빙 중인 집컴에 반영되지 않았다(run 37402009303). 지금은:
- 1단계 앞에서 `nc -z 127.0.0.1 5432`(desktop-link 포워딩)로 집컴 DB에 닿는지 본다. 안 닿으면 `deploy.sh` 대신
  빌드 · k3s 적재 · `rollout restart`만 하고 기다리지 않는다(Secret·매니페스트·cloudflared apply 안 함). 노트북 파드는 집에
  돌아와 DB가 닿으면 새 이미지로 뜬다. cloudflared를 1로 올리지 않으므로 serve-agent가 내리기 전 15초 틈도 없다.
- `sync-standby.sh` 기본 `STANDBY_HOST`는 집컴 Tailscale(`suvisdev@100.91.129.31`) — 집 안팎 모두 닿는다.
- 집 밖 push는 인터넷 업로드라 바뀐 레이어가 크면(의존성 변경 등) 오래 걸릴 수 있다.
**집컴 빌드 부활은 금지**(10-05 메모리 부족으로 DB 크래시 2회).

## 설치 기록

**노트북** (`~/.config/systemd/user/`, linger):
- k3s: `curl -sfL https://get.k3s.io | sudo sh -s - --write-kubeconfig-mode 644 --disable servicelb` (사용자 sudo)
- `desktop-link.service`, `serve-agent.service`(+ `~/serve/serve_agent.sh`), `ollama-tunnel.service`(../ollama-proxy)
- 올라마 중계기 `~/ollama-proxy/haproxy.cfg` = `../ollama-proxy/haproxy.cfg` 에서 서버 두 줄만 바꾼 것
  (`laptop 127.0.0.1:11434`, `desktop 127.0.0.1:21435 backup`), 컨테이너 `ollama-proxy`
- 운영 `.env`·`.env.auth`·데이터(datasets·gildle/data·crawled·runs)는 집컴에서 복사
- 러너 `~/actions-runner`(라벨 prod, `.env` 에 `SUVISDEV_DATA_ROOT`·`KUBECONFIG`)
- 윈도우 로그온 작업 `WSL 유지 (올라마 터널)` — WSL 이 켜져야 전부 돈다

**집컴**:
- `standby-agent.service`(+ `~/serve/standby_agent.sh`), `.env` 에 `ENABLE_MOVA_STARTUP=false`
- 레지스트리 `docker run -d --name standby-registry --restart unless-stopped -p 127.0.0.1:5000:5000 -v ~/serve/registry:/var/lib/registry registry:2`
- sudoers: `k3s ctr images import *`, `k3s crictl images`, `k3s crictl rmi *` (기존)
- `/etc/rancher/k3s/registries.yaml` (10-06, 사용자 sudo 1회 + `systemctl restart k3s`):
  ```yaml
  mirrors:
    "127.0.0.1:5000":
      endpoint:
        - "http://127.0.0.1:5000"
  ```
  이게 없으면 집컴 파드가 `127.0.0.1:5000` 이미지를 https로 받으려다 실패한다(ErrImagePull) — 옛 파드는 그대로 남아 서비스는 유지.

## 확인 · 손으로 전환

```bash
# 노트북
journalctl --user -u serve-agent -n 5 --no-pager -o cat
kubectl -n suvisdev get deploy cloudflared
# 집컴
journalctl --user -u standby-agent -n 5 --no-pager -o cat; cat ~/serve/laptop_heartbeat
```

- 노트북만 빼기(점검 등): 노트북 `systemctl --user stop serve-agent && kubectl -n suvisdev scale deploy/cloudflared --replicas=0`
  → 15초 뒤 집컴이 받는다. 되돌리기는 `systemctl --user start serve-agent`.
- 집컴 판단기를 멈추면 자동 전환도 멈춘다 — 그 상태로 노트북을 끄면 사이트가 내려간다.

## 주의

- **비밀값·설정을 바꾸면 두 기기의 `.env` 를 같이.** 차이는 아래 줄들뿐이어야 한다(2026-10-06, 10-07 임베딩 추가):
  - 집컴 `ENABLE_MOVA_STARTUP=false` (스케줄러는 노트북만)
  - 임베딩(bge-m3)은 집컴 올라마 고정(10-07): 집컴 `OLLAMA_EMBED_URL=http://host.docker.internal:11434`,
    노트북 `OLLAMA_EMBED_URL=http://host.docker.internal:21435`(desktop-link → 집컴 올라마, 파드가 닿게 `0.0.0.0:21435`).
    질문 한 줄 임베딩이 집컴 CPU 직접 약 0.1초, 노트북 GPU를 중계기·Tailscale로 거치면 약 0.35초라 네트워크 왕복이 더 컸다.
  - 홈 AI 채팅: 노트북 `PORTFOLIO_LLM_BACKEND=exaone` + `PORTFOLIO_LLM_OLLAMA_URL=http://host.docker.internal:11434`
    (노트북 GPU의 EXAONE 7.8B 먼저, 실패하면 Gemini 재시도), 집컴도 `PORTFOLIO_LLM_BACKEND=exaone` +
    `PORTFOLIO_LLM_OLLAMA_URL=http://host.docker.internal:11436`(10-06 — 집컴 HAProxy의 노트북 전용 입구, 예비 없음).
    어느 쪽이든 7.8B는 노트북 GPU에서만 돌고, 노트북이 없으면 바로 Gemini로 넘어간다 — 집컴 CPU에 올라갈 일이 없다.
- 노트북 GPU(8GB)에서 7.8B(5.7GB)가 뜨면 mova 2.4B·임베딩이 잠깐 밀려나 다음 mova 요청이 몇 초 느릴 수 있다(7.8B는 5분 뒤 내려감).
  10-05 실측: 챗봇 질문 뒤 첫 mova 채팅 22.8초(평소 6.5초), mova 뒤 첫 챗봇 11.4초. 10-06부터 집컴이 서빙할 때도 챗봇이
  노트북 7.8B를 쓰므로 이 다툼은 서빙 위치와 무관하게 생긴다. 선택지(① 챗봇도 2.4B ② 7.8B 컨텍스트 8192→4096 ③ 그대로) 중
  10-05 사용자 결정은 **그대로**.
- 노트북 앱은 와이파이 너머 집컴 DB를 쓴다 — 요청당 쿼리 수만큼 지연이 붙는다(10-05 실측 검색 0.12초).
- 집컴 IP `172.30.1.21` 이 바뀌면 `desktop-link.service`·`serve_agent.sh` 기본값을 고친다(`sync-standby.sh`·`ollama-tunnel`은 Tailscale IP).
- **2026-10-06 Tailscale**: 노트북 `ollama-tunnel`은 집컴 Tailscale IP `100.91.129.31`로 붙는다(집 밖에서도 노트북 GPU). `desktop-link`·`serve_agent.sh`는 일부러 내부 IP 유지 — 집 밖에선 앱 서빙은 집컴. `sync-standby.sh`는 10-06부터 Tailscale IP(위 "배포"). 집컴 HAProxy에 7.8B 전용 `:11436`(노트북만, 예비 없음), 집컴 `.env` = `PORTFOLIO_LLM_BACKEND=exaone` · `PORTFOLIO_LLM_OLLAMA_URL=http://host.docker.internal:11436`. 저장소 `../ollama-proxy/` 원본 파일은 아직 옛 값(워크로그 10-06 (3)).
- 노트북이 응답 없이 멈추면(잠듦) 집컴 전환까지 약 30초 사이트가 530.
- 노트북 재부팅 후에는 윈도우 로그인이 있어야 WSL 이 켜진다. 그 전까지는 집컴이 받는다.
- 집컴 파드는 `imagePullPolicy: Always`라 **레지스트리 컨테이너(`standby-registry`)가 꺼져 있으면 새 파드가 뜨지 못한다**
  (이미 떠 있는 파드는 계속 돈다). `--restart unless-stopped`라 집컴 재부팅에도 다시 뜬다.
- 레지스트리에는 배포마다 옛 레이어가 쌓인다(디스크 여유 큼). 정리: `docker exec standby-registry registry garbage-collect -m /etc/docker/registry/config.yml`.
