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

- **비밀값·설정을 바꾸면 두 기기의 `.env` 를 같이.** 차이는 집컴의 `ENABLE_MOVA_STARTUP=false` 하나뿐이어야 한다.
- 노트북 앱은 와이파이 너머 집컴 DB를 쓴다 — 요청당 쿼리 수만큼 지연이 붙는다(10-05 실측 검색 0.12초).
- 집컴 IP `172.30.1.21` 이 바뀌면 `desktop-link.service`·`serve_agent.sh`·`../ollama-proxy/ollama-tunnel.service`·`sync-standby.sh` 기본값을 고친다.
- 노트북이 응답 없이 멈추면(잠듦) 집컴 전환까지 약 30초 사이트가 530.
- 노트북 재부팅 후에는 윈도우 로그인이 있어야 WSL 이 켜진다. 그 전까지는 집컴이 받는다.
- 집컴 파드는 `imagePullPolicy: Always`라 **레지스트리 컨테이너(`standby-registry`)가 꺼져 있으면 새 파드가 뜨지 못한다**
  (이미 떠 있는 파드는 계속 돈다). `--restart unless-stopped`라 집컴 재부팅에도 다시 뜬다.
- 레지스트리에는 배포마다 옛 레이어가 쌓인다(디스크 여유 큼). 정리: `docker exec standby-registry registry garbage-collect -m /etc/docker/registry/config.yml`.
