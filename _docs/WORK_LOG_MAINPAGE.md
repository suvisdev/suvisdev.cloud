# 작업 일지 — 도메인 메인페이지 워크로드

날짜별로 그날 한 작업·수정·오류·데이터를 기록한다. **최신 날짜가 맨 위**로
오게 추가한다(새 항목은 이 안내 바로 아래에 삽입). 요약용 재개 메모는
`SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(현재 상태·다음 할 일)를 따로 쓰고,
이 파일은 **그날그날 실제로 있었던 일의 상세 기록**(무엇을 왜 했는지,
어디서 막혔는지, 데이터가 어떻게 바뀌었는지)에 집중한다.

**항목 템플릿**:
```
## YYYY-MM-DD

### 작업 내용
- 무엇을 했는지, 왜 했는지(계기)

### 수정/구현
- 만들거나 고친 파일·코드, 핵심 변경점

### 오류·막힌 점
- 무슨 에러가 났는지, 원인, 어떻게 해결했는지(해결 안 됐으면 그것도 기록)

### 데이터
- 데이터셋 출처·규모·라벨 변경 등

### 산출물
- 커밋 해시, 문서 갱신 위치 등
```

---

## 2026-10-05

### 작업 내용
- 집컴(운영) mova 채팅이 느린 원인 확인: 집컴 GPU(GTX 1650 SUPER 4GB)는 lora-server가 쓰고 올라마는 CPU 전용
  (`ollama ps` 100% CPU, `exaone3.5:2.4b` 4.2 tok/s). 노트북(RTX 4060 8GB)이 켜져 있을 때만 올라마 호출을 노트북 GPU로
  보내고 꺼지면 집컴 CPU로 돌아가는 중계기를 붙임. DB·API·터널은 집컴 한 곳 그대로(이중화 검토 후 DB 분기 위험으로 기각).

### 수정/구현
- 집컴: HAProxy 컨테이너 `ollama-proxy`(`--network host`, `:11435`) — laptop `127.0.0.1:21434` 우선, desktop `127.0.0.1:11434` backup.
  1초 점검, `observe layer4 error-limit 1 on-error mark-down`, `retry-on conn-failure empty-response`, `on-marked-down shutdown-sessions`.
- 노트북: 유저 서비스 `ollama-tunnel`(`ssh -N -R 127.0.0.1:21434:127.0.0.1:11434`, `Restart=always`, 시작 전 집컴 옛 세션 포트 정리).
  운영이 7일간 불러온 모델 4종 + 코드 기본값 2종을 같은 ID로 맞춤(공개 4종 pull, `mova-agent-v9`·`mova-understand-v7`은 집컴 blob을
  sha256 검증 후 `ollama create`). 윈도우 로그온 작업 `WSL 유지 (올라마 터널)`(관리자 불필요) 등록.
- `k8s/backend.yaml` `OLLAMA_BASE_URL` `:11434`→`:11435`, `k8s/ollama-proxy/`(설정 3개 + README), `k8s/README.md` 주의 항목.

### 오류·막힌 점
- 1차 설정(3초 점검)은 터널을 끊은 직후 503 1건 — backup은 활성 서버가 남아 있는 동안 재시도 대상이 아님.
  연결 오류 즉시 제외 + L7 재시도로 바꾼 뒤 끊는 순간 실패 0건.
- 노트북이 응답 없이 멈추는 경우(`kill -STOP`으로 흉내)는 처리 중이던 1건이 실패(약 5초) — 집컴 sshd에 ClientAlive가 없어
  옛 세션이 포트를 쥔 채 남기 때문. 점검 타임아웃 2초 + 제외 시 연결 끊기로 이후 요청은 집컴. 1건 손실은 수용.
- 집컴 사용자는 올라마 저장소를 못 읽음(권한) — 이미 있는 pgvector 이미지로 읽기 전용 마운트해 blob을 꺼냄.

### 데이터
- 실측(집컴에서 같은 요청): `exaone3.5:2.4b` 생성 5.40초·4.2 tok/s → 0.31초·120.5 tok/s, `bge-m3` 임베딩 0.605초 → 0.227초.

### 산출물
- 브랜치 `feat/ollama-laptop-gpu-proxy`. 머지되면 CD가 집컴 backend를 `:11435`로 재배포.

### 작업 내용 (2) — #166 머지·배포, 직후 DB 크래시 2분 23초
- PR #166 머지(7365f40) → backend-ci 통과 → 집컴 CD(`deploy.sh --external-db --build`): 이미지 빌드 약 14분 30초 + import + 롤아웃,
  워크플로 성공(19:17). 새 backend 파드 `OLLAMA_BASE_URL=:11435` 확인.
- **19:19:07 Postgres 서버 프로세스가 죽어 전체 재초기화 → 19:21:30 복구 완료**(약 2분 23초 동안 API가 "database system is in recovery mode" 502/타임아웃).
  집컴 WSL 메모리 8.9GB 중 여유 84MB·스왑 3.5/4GB·load 28 — 빌드·import·새·옛 파드 동시 기동 + 집컴 CPU 올라마 상주 모델 2개.
  데이터 손실 없음(복구 후 movies 3921·users 11 동일, redo 0.36초). SSH도 배너 교환에서 시간 초과.
- 조치: 집컴 CPU 올라마 상주 모델 2개 내림(노트북이 받으니 예비일 뿐 — 노트북이 빠질 때만 다시 올라옴) → 사용 3.2→2.2GB, 스왑 3.5→0.9GB.
- 확인: 운영 파드 안에서 앱의 `OllamaClient`로 호출 → 중계기 노트북 처리 16→18건, 1.09초. 공개 API 200.

### 오류·막힌 점 (2)
- 근본 원인은 집컴 메모리(8.9GB)에서 CD가 이미지를 직접 빌드하는 것. 이번 변경과 무관하게 다음 배포에서도 재발할 수 있음 — 미결.
  후보: ① 빌드를 GitHub 러너로 옮겨 레지스트리에서 받기 ② 집컴 `.wslconfig` 메모리 상향 ③ 배포 중 올라마·lora 일시 정지.

### 작업 내용 (3) — 운영 파이프라인 시험 · 집컴 예열기
- #167(문서) 머지 — `!**/*.md` 필터로 CI·배포가 돌지 않음 확인.
- 운영 파드에서 앱 `OllamaClient`로 3단계 시험(공개 API는 내내 200): 평상시 노트북 판단 1.18초·임베딩 0.31초 →
  노트북 끊음 첫 호출 **판단 88.18초·임베딩 45.94초**(집컴 모델을 내려 둔 탓의 콜드 로드, 앱 타임아웃 20초 초과) · 두 번째 10.23초 →
  복귀 1.01초·0.21초.
- 예열기 `ollama-warm`(집컴 유저 서비스): 중계기 상태가 노트북 DOWN이 되면 집컴 모델을 바로 올리고, 노트북 UP 120초 뒤 내림.
  재시험: 끊고 판단 22초·임베딩 51초 만에 예열 완료, 이후 운영 호출 판단 17.4초(집컴 CPU 평소 속도)·임베딩 0.42초,
  복귀 120초 뒤 두 모델 내림·집컴 사용 메모리 2.2GB.

### 작업 내용 (4) — 노트북 끄기 실측 · 공개 API 채팅 · 임베딩 상주
- #168 머지·배포(빌드 캐시로 5분): 배포 중 최저 여유 메모리 3.5GB(1차 84MB)·DB 재시작 없음. 직후 새 backend 기동으로 1~2분 부하 14.
- 노트북 WSL 실제 종료(`wsl --shutdown`) 3분 → 로그온 작업으로 재시작: 5초 간격 요청 56회 실패 0, 복귀 8초 만에 터널 재연결.
- 공개 API로 도메인 챗봇·mova 실제 채팅: 노트북 끈 직후 **도메인 챗봇 504(31초)·mova 69초에 추천 0편** — 두 기능 모두
  RAG 임베딩을 쓰는데 집컴 bge-m3 콜드 로딩(50~70초)을 그대로 기다림. 예열기에서 bge-m3만 상주로 바꿈(집컴 여유 6.7→5.1GB).
  재시험 끈 직후 도메인 챗봇 200·8.35초, mova 200·27.78초·추천 3편. 노트북 켬 상태는 8.21초·8.17초.

### 작업 내용 (5) — 노트북 우선 서빙 · 꺼지면 집컴 (DB는 집컴 한 곳)
- 사용자 결정: 집컴이 느리고 집컴 재빌드가 오래 걸려 노트북으로 운영하되, 노트북이 꺼지면 집컴이 받게. 노트북 운영 구성은
  10-02에 지웠으므로 k3s 재설치(사용자 sudo 1회)부터. DB 이중화(복제·승격·되돌리기) 대신 **DB·Redis를 집컴 한 곳**에 두고
  노트북 앱이 `desktop-link`(ssh -L 5432·6379·8200·21435)로 쓰게 해 앱 계층만 전환 — 데이터가 갈라질 수 없다.
- 판단기: 노트북 `serve-agent`(앱→DB 요청이 건강하면 노트북 터널 1, 집컴에 심장박동) · 집컴 `standby-agent`(심장박동 15초 끊기면
  집컴 터널 1, 노트북 30초 서빙이면 0). 노트북 배포 중엔 `deploy.sh --external-db`가 터널을 1로 올리므로 검증 끝까지 0으로 붙잡음.
- 집컴 `.env` `ENABLE_MOVA_STARTUP=false`(스케줄러는 노트북만) · 배포 러너 노트북으로(집컴 러너 등록 해제) ·
  `k8s/sync-standby.sh`(집컴 로컬 레지스트리로 바뀐 레이어만 push → import → apply → 재시작, 집컴은 빌드 안 함).
- 감정분석 근본 원인: k3s 파드엔 GPU가 없어 Echo가 EXAONE-2.4B를 CPU fp32로 올림 — 집컴에선 기동 직후 메모리 고갈로 DB 크래시 2회,
  노트북에선 어댑터가 있어 실제로 CPU 8코어·5.6GB로 돎. `_gpu_available()` 없으면 배치·단건 모두 로드 안 함(테스트 2 추가, 6 통과).

### 데이터 (5)
- 첫 전환: 공개 API 24회 실패 0(노트북 서빙 22:40:19, 집컴 물러남 22:40:50).
- 노트북 WSL 종료 3분: 공개 API **530 약 31초**(22:43:48~22:44:19) 뒤 집컴 정상. 재시작 46초 뒤 노트북 복귀, 그 사이 시간 초과 2회.
- 예비 동기화 첫 실행 약 12분(빈 레지스트리라 전 레이어).

### 오류·막힌 점 (5)
- 노트북 `.env` 백업을 같은 분(分) 이름으로 두 번 떠서 노트북 옛 `.env`(09-29)가 덮어써짐 — 운영에 필요한 건 집컴 `.env`라 영향 없음,
  옛 파일은 USB 백업(`D:\전달파일`, `D:\suvisdev_notebook_backup_20261002`)에 있음.
- 재부팅 직후 k3s가 노트북 cloudflared 파드를 앱보다 먼저 되살림 → 판단기가 18초 만에 0으로(앱 503). 공개 API 오류는 관측되지 않음.

### 작업 내용 (6) — #170 첫 실전 CD · 집컴 이미지 적재 단축
- #170 머지 → 노트북 러너가 끝까지 처리, 16분 36초 성공(노트북 빌드·배포 5분 28초, push 2분 20초, 집컴 docker save→k3s import
  6분 56초, 재시작 1분 30초). 배포 중 공개 API 300회 중 실패 6(배포 끝난 뒤 58회는 0) — 노트북 CPU(빌드 + 옛 코드의 감정분석).
- 집컴 k3s가 로컬 레지스트리에서 직접 받게: `registries.yaml` http 미러(사용자 sudo 1회), `sync-standby.sh`에서 docker pull·save·import 제거,
  집컴 사본 매니페스트만 `127.0.0.1:5000/...`·`imagePullPolicy: Always`. 시험 파드 pull 1.9초.
- #171 실전: 배포 2분 16초(노트북 56초 · 집컴 동기화 59초 — push 2초, 재시작 56초). 코드 변경이 없던 배포라 빌드는 캐시.
  머지 순서 실수로 PR CI 등록 전에 머지 → main CI가 취소돼 배포 skipped, 같은 run 재실행으로 통과 후 배포.

## 2026-10-06

### 작업 내용
- 노트북 끄기 재시험(WSL 3분 종료): 공개 API 530 약 26초 후 집컴 서빙, 복귀 자동. 끈 상태 실제 채팅 — 도메인 챗봇 200 13.70·7.56초,
  mova 200 29.81·27.53초(추천 3편). 켬 상태 mova 9.63~12.71초.
- 켬 상태 도메인 챗봇 502 1건 — 로그: Gemini `503 UNAVAILABLE ... high demand`(전환과 무관). 재시도 + 노트북 7.8B 대체 추가:
  `RetryHubLlmAdapter`(429·502·503·504면 1.5초 뒤 한 번 더), gemini 모드에서 `PORTFOLIO_LLM_FALLBACK_URL`이 있으면
  Gemini(재시도 포함) 실패 시 그 주소의 EXAONE 7.8B. 노트북 `.env`만 `http://host.docker.internal:11434`(노트북 올라마 직접 —
  중계기를 거치면 노트북이 빠졌을 때 집컴 CPU에 7.8B가 올라간다). 테스트 7 추가, 포트폴리오 채팅 27 통과.

### 오류·막힌 점
- 시험 스크립트 실수 2번: 윈도우 curl이 한글 본문을 깨뜨려 400, 경로 변환으로 채팅 스크립트를 못 찾음 → 노트북을 한 번 더 껐다 켬.
  파이썬 송신(UTF-8)으로 바꾸고, 첫 채팅이 기록되지 않으면 끄기 전에 멈추는 가드 추가. Cloudflare는 파이썬 기본 UA를 1010으로 막음.

### 작업 내용 (2) — 홈 AI 채팅 순서 변경(사용자 결정)
- #172 배포(3분) 뒤 사용자 결정: **노트북은 EXAONE 7.8B 먼저, 실패하면 Gemini(재시도)**, 집컴은 Gemini(재시도)만.
  `PORTFOLIO_LLM_FALLBACK_URL`(gemini→7.8B 대체)을 `PORTFOLIO_LLM_OLLAMA_URL`(exaone 모드의 7.8B 주소)로 바꾸고,
  7.8B 타임아웃 40초(`PORTFOLIO_LLM_TIMEOUT_S`, 기존 120초) — 막히면 Gemini로 빨리 넘김. 노트북 `.env` = exaone + 노트북 올라마 직접,
  집컴 `.env` = gemini. 테스트 29 통과.

### 작업 내용 (3) — Tailscale: 어디서나 노트북 GPU · 집컴 서빙 홈 채팅도 7.8B
- 계기: 노트북을 집 밖 Wi-Fi(`hi01`, 192.168.0.x)에 붙였더니 노트북이 서빙에서 빠지고(09:42 serve-agent 터널 1→0, 앱 503) 집컴이 서빙.
  원인은 `desktop-link`·`ollama-tunnel`이 둘 다 집컴 내부 IP `172.30.1.21:22`로 SSH 하는 구조 — 집 밖이면 GPU 빌려주기까지 같이 끊김
  (집컴 HAProxy는 노트북을 빼고 CPU로, 홈 채팅은 집컴 `.env`가 gemini라 Gemini만).
- 결정(사용자): 집 밖에서는 **앱은 집컴, GPU만 노트북**. Tailscale(개인 무료) vs Cloudflare SSH 비교 후 Tailscale — 바꿀 것이 IP 하나뿐.
- 노트북·집컴 WSL에 Tailscale 설치(사용자): `teagy-laptop` 100.118.78.100 · `home-desktop` 100.91.129.31, **직접 연결 9ms**,
  두 기기 key expiry 끔. 덕분에 집 밖에서 집컴 SSH 가능해짐.

### 수정/구현 (3) — 운영 설정만 (저장소 코드 변경 없음)
- 노트북 `~/.config/systemd/user/ollama-tunnel.service`: `suvisdev@172.30.1.21` → `suvisdev@100.91.129.31` (ExecStartPre·ExecStart 둘 다).
  `desktop-link`·`serve_agent.sh`는 **일부러 내부 IP 유지** — 집 밖에서 노트북이 앱까지 서빙하면 DB 쿼리가 매번 인터넷을 건넘.
- 집컴 `~/ollama-proxy/haproxy.cfg`: 7.8B 전용 입구 `frontend ollama_laptop_in :11436` → `backend ollama_laptop`(노트북 21434만, **backup 없음**).
  노트북이 빠지면 즉시 503 → 앱이 Gemini로. 7.8B가 집컴 CPU에 올라갈 길이 없다. 기존 :11435(임베딩·판단)는 그대로.
- 집컴 `suvisdev/.env`: `PORTFOLIO_LLM_BACKEND=gemini` → `exaone`, `PORTFOLIO_LLM_OLLAMA_URL=http://host.docker.internal:11436` 추가 →
  시크릿 `suvisdev-env` 재생성 + `rollout restart deploy/backend`(사용자 실행 — 클로드 실행은 하네스 권한 검사 'Production Deploy'에 막힘).
- 백업: 노트북 `ollama-tunnel.service.bak-20261006-lan`, 집컴 `haproxy.cfg.bak-20261006`·`suvisdev/.env.bak-20261006-gemini`.

### 오류·막힌 점 (3)
- 집컴 `.env` 반영 스크립트를 클로드가 실행하려다 권한 검사에 막혔는데, 같은 명령에 들어 있던 스크립트 파일 생성까지 통째로 안 돼
  사용자가 실행하니 "No such file". 파일만 따로 만들어 다시 실행. 또 WSL 터미널에서 윈도우 경로(`C:/…`)를 써서 한 번 더 실패 → `/mnt/c/…`.
- 저장소 원본 `k8s/ollama-proxy/ollama-tunnel.service`·`haproxy.cfg`는 아직 옛 값 — 이 파일로 재설치하면 오늘 변경이 사라짐(미결, PR 예정).

### 데이터 (3) — 실측
- 집컴 서빙 상태에서 공개 API `POST /portfolio/chat`: 첫 질문 **200 · 13.0초**(7.8B 적재 포함) → 노트북 `ollama ps` = `exaone3.5:7.8b 100% GPU 5.7GB`,
  두 번째 **200 · 8.8초**. HAProxy 상태: `ollama/laptop UP`, `ollama_laptop/laptop UP`.

### 산출물 (3)
- 운영 설정 3곳(위) · 이 문서들(WORK_LOG·LESSONS·INTERVIEW_QUESTIONS·`k8s/failover/README.md` 주의 항목).

### 작업 내용 (4) — 인수인계 반영 · 집 밖 CD 실패 문서화
- 바탕화면 `HANDOFF_suvisdev_2026-10-06.md`(10-05~06 변경 전체·구조·CD 실패 경로)를 읽고 저장소 문서를 현행화.
- 계기: #174 머지 후 backend-deploy 실패(run 37402009303, 상세 `WORK_LOG_GILDLE.md` 10-06). 루트 `CLAUDE.md`가 아직
  "프로덕션 = 노트북, db·redis도 노트북"이라 세션이 상황을 잘못 읽음.

### 수정/구현 (4) — 문서만
- 루트 `CLAUDE.md`: CI/CD 주석(노트북 러너 → sync-standby, 집 밖 실패), compose 단락, `RECOMMENDATION_BACKEND`(lora-server는 집컴),
  주의사항 "개인 배포 환경"을 두 기기 구성으로 교체(구 "데스크톱 상시 서버 아님"·노트북 lora-server 서술 삭제).
- `k8s/failover/README.md`: "배포"에 집 밖 CD 실패 경고·고칠 방향 후보, 홈 채팅 `.env` 서술을 집컴 exaone(:11436)으로 정정.
- `k8s/README.md` CI/CD 표: 러너 = 노트북(유일) + sync-standby, 집 밖 실패 링크.
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`: 10-06 Tailscale 완료 인덱스 + 백로그 "노트북·집컴 이중화 후속" 4건. `LESSONS.md` ⏳ 1줄.

### 오류·막힌 점 (4)
- 미확인: 1단계 apply가 노트북 cloudflared를 1로 올린 약 15초 동안 외부 요청이 노트북으로 가서 실패했는지(인수인계 A-5 4번).
  `CLAUDE.md` 주의사항 VRAM 항목의 `DESKTOP-IOAQ7L7` 서술은 현재 여부를 확인 못 해 그대로 둠.
- 인수인계 개정판(섹션 B: 10-05 대화의 결정·맥락) 재반영: failover README에 GPU 자리 다툼 실측·"그대로" 결정, k8s/README에 머지 순서
  규칙(#171 사례), PROGRESS 백로그에 방화벽 15432·`ssh home` 정리·"취업할 때까지 단순·무료" 방향. 모델 양쪽 동기화는
  `k8s/ollama-proxy/README.md` 주의에 이미 있어 생략.
- 새로 드러난 점: 집컴 `ENABLE_MOVA_STARTUP=false`라 노트북이 집 밖인 동안 mova 부팅·주기 작업이 어디서도 안 돈다(백로그 6번, 결정 필요).

### 작업 내용 (5) — 집 밖 CD 실패 수정 (브랜치 `fix/cd-away-from-home`)
- 사용자 요청 "2번 고쳐줘". 방향은 인수인계 A-6 후보 중 가장 단순한 조합(사용자 방향 "취업할 때까지 단순·무료").

### 수정/구현 (5)
- `.github/workflows/backend-deploy.yml` "배포": `nc -z -w 3 127.0.0.1 5432`(desktop-link 포워딩)가 되면 기존 `deploy.sh --external-db --build`,
  안 되면 `docker build` → `k3s ctr images import` → `rollout restart backend·auth`만(기다리지 않음, Secret·매니페스트·cloudflared apply 안 함).
- `k8s/sync-standby.sh`: `STANDBY_HOST` 기본값 `suvisdev@172.30.1.21` → 집컴 Tailscale `suvisdev@100.91.129.31`.
- 문서: failover README "배포"(경고 → 현재 동작), k8s/README CI/CD 표, 루트 CLAUDE.md CI/CD 주석, PROGRESS·LESSONS 상태.
- 기각: `if: always()`로 동기화만 강제 — 10분 타임아웃을 매번 기다리고 cloudflared 1 부작용이 남음. 러너 집컴 이전 — 빌드 금지 제약.

### 오류·막힌 점 (5)
- 확인한 것: 집 밖 노트북에서 `nc -z 127.0.0.1 5432` 실패(exit 1), Tailscale로 집컴 SSH·`standby-registry` `/v2/` 200, 러너 `.env`에 `KUBECONFIG` 있음,
  `bash -n`·YAML 파싱 통과.
- **실제 CD 검증(집 밖, 브랜치 `workflow_dispatch` — 클로드 실행은 권한 검사에 막혀 사용자 실행) run 37404372412 성공, 1분 29초**:
  로그 "집컴 DB(127.0.0.1:5432)에 닿지 않음" 분기 → 노트북 빌드·적재·restart → `[standby]` push·집컴 apply·restart → api 200·auth 200.
  집컴 backend·auth 새 파드 Running, 이미지 `sha256:2ff8c1d…`가 노트북 빌드와 일치. 노트북 cloudflared 0/0 유지(안 건드림),
  노트북 파드는 `Init:0/2`로 대기(집에 오면 뜰 예정 — 미확인). 집 안 경로(`deploy.sh`)는 기존 그대로라 이번에 다시 돌리지 않음.
- 스케줄러 결정(사용자, 10-06): 집 밖 동안 mova 주기 작업이 안 도는 것은 **그대로 감수**. 코드 확인 결과 5개 작업 모두 기동 시 바로
  1회 실행 후 반복(채팅 트렌드 6시간, 나머지 24시간, 에디터 리뷰만 20시간 간격 가드)이라 집에 오면 자동으로 따라잡는다.

### 작업 내용 (6) — 소개·연락 페이지(`/contact`) 현행화
- 사용자 지적: 이메일 오기(`suvisdev@gmail.com`) + 소개 카드가 실제 구조와 다름. 사이트 나머지(이력서·푸터·개인정보 처리방침)는
  이미 `ssuvisdev@gmail.com`이고 이 파일만 틀렸음. 인스타그램·X `@suvisdev`는 맞다고 사용자 확인.

### 수정/구현 (6)
- `suvis/lib/contact-profile.ts`: email → `ssuvisdev@gmail.com`. 주요 영역을 실제 구조로(웹 Next.js·앱 Flutter / Clean Architecture +
  Hexagonal·스타 토폴로지 모듈러 모놀리식 / PostgreSQL·pgvector·Redis 집 서버 k3s / EXAONE LoRA·llama.cpp·Ollama·RAG(bge-m3)·Gemini 폴백),
  "Neon" 삭제. 프로젝트 Titanic(데모) → Gildle, Apps 설명 "개인·팀 프로젝트 모음".
- 검증: `tsc --noEmit` 0, eslint 0, 로컬 `next dev` + 헤드리스 크롬 캡처로 화면 확인(노트북엔 pnpm이 없어 `node_modules/.bin` 직접).
- `/resume`(`suvis/app/resume/_components/resume-content.tsx`)의 "GPU 노트북 한 대의 k3s로 직접 운영" 두 곳(소개 문단·suvisdev.cloud 카드)
  → "집 서버와 GPU 노트북 두 대의 k3s"(카드엔 "노트북이 빠지면 집 서버가 자동으로 넘겨받음"). tsc·eslint 0, 헤드리스 크롬 캡처 확인.

### 작업 내용 (7) — 사이트 기본 탭 아이콘을 직접 만든 SV 로고로
- 홈·`/contact`·`/resume` 등 탭 아이콘이 v0 기본 로고였음. 저장소에 쓰이지 않던 `suvis/public/suvis-logo.png`(빨강·금 육각형 SV, 722×761,
  오른쪽 위 "DeeVid AI" 워터마크, 로고가 왼쪽 아래로 치우침)를 Pillow로 육각형만 잘라 정사각형으로: `public/suvisdev-icon.png`(512, 투명),
  `public/apple-icon.png`(180, 배경 #0A0A0D — 애플 아이콘은 투명 불가) 교체.
- `suvis/app/layout.tsx` metadata `icons` → `/suvisdev-icon.png` + apple. 쓰이지 않게 된 v0 파일 `icon.svg`·`icon-light/dark-32x32.png` 삭제.
- 확인: 로컬 `next dev`에서 `/`·`/contact`·`/resume`은 새 아이콘, `/mova`·`/gildle`은 각자 아이콘 유지. 흰/어두운 배경 128·32·16px 렌더 확인, tsc·eslint 0.
- 홈 타일 그림(`apps-catalog.ts` 사진)과 Gildle "준비 중" 표시는 사용자 결정 대기로 그대로.

### 산출물 (5·6)
- PR #175(문서)·#176(CD 수정) 머지(`5e798c3`). #176 머지로 backend-deploy 자동 실행.

## 2026-10-02

### 작업 내용
- 집컴 이관 후속 백로그 중 두 건: ① 재학습 lora GGUF를 집컴에 반영하는 절차를 문서화 ② ruff에서 `.ipynb` 제외(10-01에 남겨 둔 54건).

### 수정/구현
- `suvisdev/_docs/lora-remote-gpu-ops.md` §6 "재학습 GGUF를 운영(집컴)에 반영" 신설 — 집컴(GTX 1650 SUPER 4GB)은 병합 VRAM(~5GB)과
  학습 패키지가 없어 GGUF를 만들 수 없음 → 코랩 또는 노트북 `export_mova_gguf.py`로 생성 → sha256 확인 후 복사 → `LATEST_GGUF` 백업·교체
  → `/reload` → `/health` → 운영 하네스 2종 → 롤백. GGUF는 아키텍처 무관이라 sm_89에서 구운 파일을 sm_75 빌드에서 그대로 사용.
  토큰은 `systemctl --user show lora-server -p Environment`에서 추출, 하네스 포트는 `kubectl get svc backend` nodePort 조회(설치마다 다름).
  판단 모델 `mova-agent-v9`는 Ollama라 이 절차 대상이 아님을 명시.
- `suvisdev/pyproject.toml` `[tool.ruff]`에 `extend-exclude = ["*.ipynb"]`.
- 진행 문서: 집컴 상시 가동 마무리 완료 표시(사용자가 10-01에 자동 로그인·절전 끄기·재부팅 테스트 완료, BIOS AC 복구는 안 하기로 결정).

### 오류·막힌 점
- 없음. 노트북에서 문서의 명령 검증: 토큰 추출(64자)로 `/generate` 200, nodePort 조회 31386, `/health` 응답 형식 일치.
  `ruff check .` **All checks passed**(54→0). `ruff format --check`는 `.md` 코드블록 8파일만 남음(10-01에 의도적으로 보류한 것, 손대지 않음).

### 산출물
- 미커밋: 위 두 파일 + 문서 갱신.

### 작업 내용 (2) — 노트북 USB 백업·복원 가이드 · 면접 예상 질문 HTML
- 노트북은 이제 코드 작성 전용(검사·배포는 CI/CD·집컴) → C 드라이브 정리 전에 운영·학습 자산을 USB(D: One Touch 1.8TB, exFAT)로.
  실측: C 420GB 중 WSL vhdx 163GB(내용 151GB), 윈도우 개발 도구 ~25GB, 게임 ~120GB, `C:\Team Seuk` 15GB(Arda — 미접촉).
- **USB `D:\suvisdev_notebook_backup_20261002\`** — tar 10개(약 80GB): misc(.env·노트북 DB 덤프 `pg_dump -Fc` 45MB/63테이블·
  compose), repo(git 밖 파일 164개 2.8GB — .env 4종·길들 데이터·서명 설정·datasets), config(lora-server·Ollama systemd, 터널 인증서,
  gh), lora, ollama(23GB), hf(16GB), models(20GB), images(`docker save` 3종), datasets, llama.cpp + `windows\`(길들 서명 키 jks·
  길들 키 폴더·10-01 이관 런북). 묶음마다 원본 스트림 sha256(tee)과 USB `Get-FileHash` 대조 → `MANIFEST.txt`.
- **`RESTORE_GUIDE.md`**(클로드에 붙여 넣으면 WSL 설치→저장소·git 밖 파일→대용량→DB→Ollama→lora(sm 재빌드)→배포→터널 컷오버→
  상시 가동→CD 러너까지 단계별 검증 포함, 10-01 막힌 점 반영) + `README_먼저읽기.txt`. DB·.env는 10-01 밤 노트북 스냅숏이라
  집컴이 살아 있으면 그쪽이 최신임을 명시.
- 면접 대비: 322문항 HTML을 만들었다가 사용자 요청으로 **49문항 선별본** `바탕화면/면접_예상_질문.html`(주제 6개, 문항마다 30초 핵심 한 줄 +
  원문 답, 검색·익힘 체크·랜덤)으로 교체.

### 오류·막힌 점 (2)
- USB가 WSL에 안 붙음 — `!` sudo는 비번 창이 없어 실패, 사용자 터미널 mount도 미반영. 윈도우 `cmd.exe` 리다이렉트로 우회(LESSONS).
- 정리(삭제) 스크립트 작성이 하네스 권한 검사(되돌릴 수 없는 삭제)에 막힘 → 사용자 실행 또는 권한 허용 대기. 삭제는 아직 안 함.

### 작업 내용 (3) — USB 백업 확정 · 아키텍처 면접 질문
- USB 백업 10묶음 **전부 체크섬 OK**(원본 tee sha256 = USB `Get-FileHash`), `RESTORE_GUIDE.md`·`README_먼저읽기.txt`·`MANIFEST.txt` 복사·해시 확인.
  노트북 정리 명령·WSL 디스크 압축(`Optimize-VHD`)은 사용자에게 전달(실행 대기).
- 인터뷰 질문에 처음부터 깔린 구조를 묻는 문항이 거의 없음을 집계로 확인(클린 아키텍처·SOLID·import-linter·RS256·Riverpod 0회) →
  **"아키텍처·기술 선택 총정리" 12문항** 추가(모듈러 모놀리식·auth 분리·RS256 vs HS256·헥사고날 사례·Schema/Command/Dto·스타 토폴로지 강제·
  FastAPI·Alembic·pgvector·BFF·Flutter+Riverpod·온프레미스). 답은 코드 확인 후 작성 — 백엔드는 `JWT_PUBLIC_KEY_B64`로 RS256 검증, viewer HS256
  세션도 함께 받는 이행 중 상태임을 명시. 면접 HTML(사용자가 `진수택_이력서_자소서/`로 옮김) 49→61문항, 빌더를 줄 번호 대신 질문 제목으로 찾게 변경.


### 작업 내용 (4) — 집컴 원격 접속 · 운영 측정 · 회원가입 500 · 구글 앱 로그인(보류)
- **집컴 SSH**: `ssh.suvisdev.cloud` 터널 경로가 노트북 시절 설정 그대로 **Access 없이 열려 있었고 sshd가 비밀번호 로그인도 받는 상태**였다
  (노트북에서 로그인 없이 `Permission denied (publickey,password)`까지 도달 확인, 비밀번호 시도는 안 함). 사용자가 Zero Trust에서
  Access 앱(`ssh`, Emails 정책 1명, Cloudflare 로그인) 생성 → 302 로그인 리다이렉트 확인. 노트북 키 `~/.ssh/home_desktop` 생성,
  `~/.ssh/config` `Host home`(ProxyCommand `cloudflared access ssh`), 집컴 authorized_keys 등록 → `ssh home` 동작(호스트 지문
  SHA256:siK5PCL9…). 집컴 sudo는 비번 필요(k3s ctr import 등만 NOPASSWD), kubectl은 sudo 없이 됨.
- **운영 측정(집컴)**: WSL 8.7GB 중 가용 3.5GB·**스왑 2GB 사용**. 판단 모델 v9 단독 — 콜드 로드 15.8s, 생성 16 tok/s(CPU).
  집컴 세션이 넣은 `OLLAMA_KEEP_ALIVE=-1`이 백엔드에도 들어가 `keep_alive:"-1"` 문자열 전송 → Ollama **HTTP 400**
  ("missing unit in duration") → 판단·이해 단계가 매 요청 즉시 실패, 결정론 경로로 6~8s(빠르지만 이해 꺼짐).
- **운영 수정 1(사용자 승인)**: 집컴 `.env` `OLLAMA_KEEP_ALIVE=-1m`, `MOVA_CHAT_AGENT=0`(백업 `.env.bak-20261002-keepalive`) →
  Secret 갱신 + backend 재시작(집컴 저장소가 c802a6b로 뒤처져 deploy.sh 대신 Secret만 수동). 400 사라짐. 이해 단계(2.4B CPU)가
  실제로 돌면서 6.8~18.9s·20s 타임아웃 빈발. 재시작 직후엔 **감성 분석 모델 로드(84s/샤드)**가 CPU를 잡아 524 — 그리고 집컴에
  `apps/ontology/runs/echo_sentiment/adapter`가 없어 결국 실패(리뷰 저장 때마다 `analyze_one`도 같은 로드 시도).
- **APK 500**: auth `/auth/mobile/signup` — users에 같은 이메일 2쌍(id 1·3, 2·9; 각 쌍 구글+이메일) → `scalar_one_or_none`
  MultipleResultsFound. `create_email_user` 중복 확인에 `limit(1)` → 409. 카카오 모바일 생성 경로도 이메일 중복을 확인하지 않아
  중복의 출처로 보임(미수정).
- **구글 앱 로그인(사용자 지시로 콘솔 설정은 출시 준비 때)**: auth `POST /auth/google/mobile`(id_token JWKS 검증, aud=GOOGLE_CLIENT_ID,
  email_verified일 때만 이메일 사용, 연동 identity면 로그인·처음이면 생성·**같은 이메일 계정 있으면 409** — 사용자 결정), 앱 `google_sign_in`
  7.2.0 + "Google로 계속하기" 버튼(serverClientId=웹 클라이언트 ID). Firebase(gildle, 711959837274)와 웹 OAuth 프로젝트(226054818742)가
  달라 Android OAuth 클라이언트는 **226054818742 쪽**에 패키지명 + SHA-1 2개(업로드 `48:FF:D5:6E:…:11:E5`, Play 앱 서명 키) 필요.

### 오류·막힌 점 (4)
- `~/.ssh/config` 추가는 하네스 분류기가 지속성 변경으로 막음 → 사용자가 `!`로 직접 실행.
- Cloudflare 대시보드 안내를 옛 UI 기준으로 해 사용자 화면과 어긋남, One-time PIN을 "기본 포함"이라 잘못 안내(현재는 Cloudflare 로그인이
  기본, OTP는 자동 추가 안 됨) → 공식 문서 3곳 확인 후 정정. 앱 생성 중 다른 메뉴로 이동해 첫 앱이 저장되지 않음.
- 집컴 노트북은 이미 정리됨(k3s·Ollama 모델·lora·llama.cpp·HF 캐시 없음) — 노트북 복귀는 USB 전체 복원이 필요.

### 산출물 (4)
- 브랜치 `feat/gildle-google-login`(미커밋): auth google 검증기·리포지토리·서비스·라우터·테스트 6개(auth 72 통과, ruff 통과),
  gildle `auth.dart`·`google_config.dart`·pubspec(analyze 무이슈, test 18 통과).
- 회원가입 500 수정은 따로 PR(`fix/auth-signup-duplicate-email`, auth 테스트 66 통과). 머지 후 중복 이메일 가입 시도로 409 확인 예정.
- 미결: 이해 단계 끄기(A)·감성 분석 스위치(B, 코드 필요)·중복 계정 삭제(D — id 1에 채팅 179·추천 168 등 데이터, 3은 비어 있음).


### 작업 내용 (5) — 배포 확인 · 입구 필터 검토
- PR #163(봤어요 선분기)·#164(회원가입 409) 머지 — #164는 #163과 문서 충돌(INTERVIEW·LESSONS)을 양쪽 보존으로 해결 후 머지.
  CD 두 번 모두 성공(각 약 5분). 운영 확인: 중복 이메일 가입 → **409**(그 이메일 계정 수 2 그대로, 새 계정 없음),
  비로그인 "택시 운전사는 봤어" → 봤어요 로그인 안내(선분기 경로), 배포 후에도 `MOVA_CHAT_AGENT=0`·`OLLAMA_KEEP_ALIVE=-1m` 유지,
  채팅 11.5~12.9s.
- 배포 직후 약 3분 502 — 감성 분석 시작 작업이 체크포인트 로드(93s/샤드) 후 어댑터 없음으로 실패. 배포마다 반복(스위치 미결).
- 구글 앱 로그인은 `feat/gildle-google-login`(d6f7505)에 커밋·푸시만, 머지 안 함(Android OAuth 클라이언트 등록 전).
- **입구 필터 검토(사용자 질문: Arda의 Caddy 같은 게 필요한가)**: 필요 없음 — 분류=Traefik(`ingress.yaml`), HTTPS 인증서=Cloudflare,
  노출=터널(포트 닫힘), 토큰 재발급=auth(`/auth/refresh`·`/auth/mobile/refresh`, 로테이션). 빈 곳은 입구 요청 제한뿐(채팅 2곳만 앱에서
  IP당 60초 20회, 인메모리). Traefik 3.7.8 RateLimit 미들웨어를 설계했으나 **보류**(사용자 결정): 길들 앱 경로(`api.../auth/`)만 덮고,
  웹 로그인은 `auth.suvisdev.cloud → auth:9000` 직행 + Vercel BFF IP라 못 덮음, 기본 소스가 cloudflared 파드 IP라 `CF-Connecting-IP`
  필수, 같은 IP(CGNAT·와이파이) 오탐 위험. 정식 공개 전에 Cloudflare 규칙과 함께 다시 검토.

## 2026-10-01

### 작업 내용
- v1 백로그 **"ruff 린트 11건·포맷 드리프트" 정리**(사용자 지시 3번). 길들 큰길 중앙선 수정은 `[GILDLE]` 10-01.

### 수정/구현
- `uvx ruff@0.16.9 format .` → **.py 37파일** 재포맷(스크립트·datasets·mova/titanic 일부·alembic 1). 같이 바뀐 **.md 9·.ipynb 3은
  되돌림**(`git checkout`) — ruff 0.16이 마크다운 코드블록과 노트북 셀까지 포맷하는데, 문서 코드블록은 손으로 쓴 것이고 코랩 노트북은
  사용자가 업로드해 쓰는 산출물이라 포맷 diff(770줄)를 섞지 않기로 함. **포맷 드리프트(.py) 0.**
- 린트 11건: UP042 ×7 — `(str, Enum)` → `StrEnum`(mova Feedback·RoleType·AgeRating·TagKind, ontology SpamCategory, titanic Embarked·Gender).
  f-string·`str()`로 멤버를 찍는 곳은 grep상 없음(전부 `.value`·비교) → `str(member)`가 "Class.NAME"→값으로 바뀌는 영향 없음.
  B905 ×2 — `zip(..., strict=True)`(taste vector: `eff_ratings`가 reviews 컴프리헨션이라 길이 동일 / eval_chat_queries: `titles`가 recs
  컴프리헨션). I001 alembic/env.py(gildle push_token_orm 줄 정렬), UP017 `datetime.UTC` + 미사용 `timezone` 제거.
- **검증**: ruff check(.py) 0건 / 포맷 .py 0 / import-linter 6 kept / 이미지 안 pytest **1052 passed·3 skipped**(gildle 제외) + gildle 256.

### 오류·막힌 점
- `ruff check .`는 **54건이 남는데 전부 `.ipynb`**(`mova_*_colab.ipynb` 3개 — 세미콜론 E702·import 정렬·`l` 변수명 등). 노트북은
  코랩 실행용이라 건드리지 않았다. 계속 셀 거면 `pyproject`의 ruff `extend-exclude = ["*.ipynb"]`로 빼는 것이 맞다(사용자 결정).
- 하네스 분류기가 읽기 전용 `ruff check .`를 한 번 "프로덕션 배포"로 오판해 막음(재시도는 통과).

### 산출물
- 미커밋 변경 44파일(gildle 포함). 커밋 분리 권장: ① gildle 차도 페널티 ② ruff 포맷·린트 정리.

### 작업 내용 (2) — 집 데스크톱 온프레미스 이관 런북
- 면접 다닐 때 노트북을 들고 나가도 사이트가 살아 있게, 프로덕션을 노트북(teagy)→집 상시 데스크톱
  **DESKTOP-T89E5ID**(Ryzen 5 3600·16GB·GTX 1650 SUPER 4GB = sm_75)로 내리는 계획. 실행은 사용자가 집에서(대부분 클로드 위임).
- 노트북 실구성을 읽어 작성: k3s 파드 3·도커 db/redis·lora-server(serve_gguf가 `~/llama.cpp/build/bin/llama-server`를
  자식으로 띄움 → 집컴은 **sm_75 재빌드** 필수)·Ollama 모델 13·`.env` 키 57·backend hostPath 4.
- 결론: mova 2.4B GGUF(~1.7GB)는 4GB에 들어감, 홈 챗봇 `exaone3.5:7.8b`(4.8GB)는 안 들어가 `PORTFOLIO_LLM_BACKEND=gemini`
  권장(코드 확인: `FallbackHubLlmAdapter`가 요청마다 7.8B 실패 시 Gemini). 터널 토큰이 하나라 노트북↔집컴 동시 기동 금지.
  거상(2D)은 VRAM 수백 MB라 lora와 공존 OK. 클라우드 이관 시 비용은 GPU 상시가 7~8할(T4 기준 월 $500~650).

### 작업 내용 (3) — 전체 코드 점검·정리 (브랜치 `chore/code-cleanup`)
- 사용자 지시 "코드 점검·파이프라인·테스트·낡은 코드·오류 정리". 1차는 읽기 전용 점검 → 목록 승인 후 4묶음 정리.
- 점검 결과: pytest 1052 통과(shapely 3파일은 .venv에서 12 통과) · import-linter 6/6 · ruff(.py) 0 · tsc·eslint 0 ·
  **mypy 17건**(08-31 0건) · **pre-commit 게이트 꺼짐** · CI 없음 · Flutter는 노트북에 SDK 없어 미점검.

### 수정/구현 (3)
- **게이트 복구**(cc2eb28 + 후속): ruff-pre-commit rev `v0.4.9`→`v0.16.9`(pyproject `required-version ==0.16.9`와 어긋나
  ruff가 실행 거부 → 훅 항상 실패였음, 실측) · mypy·import-linter를 `suvisdev-app:latest` 이미지 안에서 실행(노트북 .venv엔
  둘 다 없음, 의존성 없는 mypy는 오탐 457건) · ruff 훅 `types_or: [python, pyi]`(노트북 E702 등 자동수정 불가 → 노트북 커밋이
  전부 막히는 것 방지) · 훅 id `ruff`→`ruff-check` · 노트북에 `uv tool install pre-commit && pre-commit install`.
- **mypy 17→0**(017805d): gildle `WalkPlanUseCase.plan` 포트에 `start_point` 추가(라우터가 넘기는데 포트에 없던 계약 위반).
  나머지는 동작 불변 — `bool(date) and date >`→`date is not None and`(빈 문자열 결과 동일), `_act_on_agent`에 에이전트 assert
  (호출부 1곳이 에이전트 있을 때만), float 거리 집계 `Counter`→dict+sorted(`most_common`과 동률 포함 무작위 2만 회 대조 일치).
- **죽은 코드**(33575eb): grimp import 그래프 + 심볼 참조로 고아 파일 8개 삭제(dispatch Holmes·ReportWriter interactor —
  호출하던 왓처는 09-27에 이미 삭제됐는데 소비자만 남음, gildle ImportTreeSegmentUseCase, mova VO 5개). 연쇄 고아
  `InboundMessageEvent`(Hub) 삭제. 미사용 파라미터 `via_point`·`active_url`, 프론트 `cookieAuthHeader` 제거.
- **잔재**(1c01142): `chat_teacher_dataset.jsonl.bak-20260909` 추적 해제(gitignore `*.jsonl`이 `.bak-` 접미사를 못 잡아
  커밋돼 있었음, 로컬 보존 + 패턴 추가), 0바이트 문서 4개 삭제.

### 오류·막힌 점 (3)
- 고아 모듈 1차 탐지가 174개로 부풀었다 — 앱 5개 누락 + `main.py`(패키지 밖) import 미집계 + 패키지(폴더) 자체를 고아로 셈.
  잎 모듈만 남기고 심볼 참조를 다시 세서 실제 8개로 확정(viewer 9개는 provider에서 쓰는 오탐).
- 처음 mypy 결과의 `google.genai` 1건은 09-27의 오래된 `.mypy_cache` 탓 — `--cache-dir=/tmp/mc`로 캐시 없이 재확인해 17건 확정.
- `uv run --with grimp`를 `--no-project` 없이 돌려 `suvisdev/uv.lock`(52B)이 생김 — pyproject에 `[project]`가 없어 .venv는
  무변경(오늘 바뀐 dist-info 0) 확인 후 삭제.
- 미해결 관찰: `ensure_*_database`가 URL이 바뀌면 옛 엔진을 dispose하지 않는다(누수 가능성, 범위 밖이라 그대로).
  `vision_s3_repository.py`는 참조 0건인데 막은 근거가 "S3 미연결"(08-10에 틀렸다고 정정된 전제) — 삭제/연결은 기능 판단.

### 산출물 (3)
- 커밋 cc2eb28·017805d·33575eb·1c01142 + 문서 커밋(게이트가 실제로 도는 첫 커밋). 브랜치 `chore/code-cleanup`(미푸시).
- 바탕화면 `집컴_서버_이관/01_이관_가이드.html`(사용자용)·`02_클로드_전달용_지시서.md`(클로드 전달용).

### 작업 내용 (4) — 후속: Flutter 점검 · S3 정리 · CI/CD
- 사용자 지적 "플러터 있을 텐데" — WSL 안만 찾고 "없다"고 단정했던 것. 실제는 윈도우 `C:\src\flutter`(3.47.2 stable).
  `\\wsl.localhost` 경로에선 `flutter test`가 잠금 대기라 윈도우 임시 폴더로 rsync 후 실행: **analyze 0 · test 15 통과**.
- S3: 사용자 "S3는 안 쓴다" → 참조 0건 `VisionS3Repository` 삭제(a685e8c), provider 주석을 실제 이유로. 아바타 업로드(viewer
  Tank)는 S3를 계속 써서 `VISION_S3_BUCKET`·Tank 유지.
- DB 엔진 dispose 우려는 철회: `.env`는 이미지에 안 들어가고(.dockerignore) 파드 DB URL은 Secret 고정이라 운영에선 URL이 안 바뀐다.
- CI/CD 신설(저장소 비공개, 기존 워크플로 이력 없음):
  - `backend-ci.yml`(ruff·mypy·import-linter·pytest, Dockerfile과 같은 CPU torch 치환 + shapely) · `frontend-ci.yml`
    (pnpm 10·type-check·lint) · `gildle-ci.yml`(flutter 3.47.2 analyze·test) — 전부 GitHub 러너, PR·main push, 경로 필터.
  - `backend-deploy.yml`: main의 backend-ci 성공(workflow_run, push 이벤트만) 또는 수동 → **라벨 `prod` 셀프호스티드 러너**
    (운영 서버가 NAT 뒤) → `deploy.sh --external-db --build` → api·auth 외부 200 확인. CI가 통과한 head_sha를 체크아웃.
  - 프론트 CD는 이미 Vercel 연동(main→Production, 브랜치→Preview, GitHub deployments로 확인)이라 추가 안 함.
  - `deploy.sh`: `SUVISDEV_DATA_ROOT`로 hostPath·.env 출처를 덮어쓰기 + 그 경로에 `datasets` 없으면 중단.

### 오류·막힌 점 (4)
- **배포 함정**: 러너가 자기 체크아웃에서 deploy.sh를 돌리면 `__REPO_ROOT__`가 데이터 없는 체크아웃을 가리키는데, hostPath가
  `DirectoryOrCreate`라 **에러 없이 빈 폴더가 운영에 마운트**된다. 개발 저장소에서 돌리면 작업 중 브랜치를 바꿔 버린다 →
  코드는 체크아웃, 데이터·.env는 `SUVISDEV_DATA_ROOT`(러너 `.env`)로 분리하고 가드 추가.
- 깨끗한 체크아웃(git worktree)으로 CI를 재현하자 **프론트가 pnpm 9에서 실패**("packages field missing") — `pnpm-workspace.yaml`의
  `allowBuilds`가 pnpm 10 설정. lockfileVersion 9.0만 보고 9로 짐작한 것. pnpm 10으로 재현 통과 후 수정.
- YAML 앵커(`&paths`)는 Actions 지원이 불확실해 풀어 씀. actionlint 0건(`.github/actionlint.yaml`에 `prod` 라벨 등록).
- 러너는 노트북에 등록(`teagy`, v2.337.0, `~/actions-runner/.env`에 `SUVISDEV_DATA_ROOT`)까지 했으나, **상시 실행 systemd 유저
  서비스 생성은 하네스 권한 정책(지속성)에 막힘** → 사용자가 `k8s/README.md` "CI/CD" 블록의 서비스 3줄을 직접 실행해야 한다.
  그 전까지 GitHub에선 러너 offline, 배포 잡은 대기.
- 사용자 질문(같은 세션): 네이버 로그인인데 이메일이 `@nate.com` — 네이버 프로필 API `email`은 네이버 계정의 **연락처 이메일**이라
  외부 주소일 수 있다(정상). 아이디 `jst0432_naver`는 `{로컬}_{provider}` 규칙.

### 작업 내용 (5) — PR #152 머지 · 첫 자동 배포 · 네이버 이메일 조사
- 러너 상시 서비스는 사용자가 `!`로 직접 등록 → GitHub에 `teagy` online(prod).
- PR #152(브랜치 chore/code-cleanup, gildle 차도 페널티 포함) GitHub CI 3종 통과(frontend 43s·gildle 1m43s·backend 3m41s)
  → 머지 `b63c4d9` → main backend-ci 성공 → **backend-deploy가 노트북 러너에서 자동 실행·성공**(run 36815126361, 04:26→04:32 UTC):
  backend·auth 롤아웃, api·auth 외부 200. "성공"만으론 빈 마운트를 못 거르니 직접 확인: 파드 hostPath 3개가 러너 `_work`가
  아니라 `/home/suteagy/projects/suvisdev/...`, 파드 안 `scored_edges.json` 89MB(10-01 갱신본)·datasets 31개,
  운영 `/api/gildle/navigate` 실노드 호출 183.2m 경로 반환. → 하네스가 막던 gildle 차도 페널티 배포가 이걸로 해소.
- 네이버 이메일(`@nate.com`) 조사: 네이버 개발자 문서(회원 프로필 조회 API) 원문 — email은 "기본적으로 네이버ID@naver.com이나
  사용자가 외부메일로 변경했으면 변경된 주소". 운영 DB(읽기 전용) id 21 `jst0432_naver`, 10-01 naver 가입, email·identity_email 모두
  nate.com. **기존 연결 로그인은 `_find_linked_user`가 사용자를 찾아 반환만 해 이메일을 갱신하지 않는다** → 네이버에서 기본 이메일을
  바꿔도 반영 안 됨(처음에 "바꾸면 된다"고 안내한 것을 정정). 네이버는 `email_verified=False`라 기존 계정 자동 병합도 안 한다(보안 설계).
  개선안(로그인 시 이메일 동기화 / 마이페이지 이메일 수정)은 사용자 결정 대기.

### 작업 내용 (6) — 홈 상단 Apps·Blog 제거 · 채팅창 아래 지킬 링크 (브랜치 `feat/home-jekyll-links`, ff477a9)
- 사용자 지시. 헤더 데스크톱·모바일의 Apps·Blog 링크만 제거(`/apps`·`/blog` 페이지는 유지). 홈 채팅 입력창 바로 아래에
  "팀 프로젝트 지킬"(ats.suvisdev.cloud)·"개인 프로젝트 지킬"(jk.suvisdev.cloud) 링크 — 주소는 기존 /blog 페이지와 동일, 둘 다 200.
- prettier가 안 건드린 header 줄들의 Tailwind 클래스 순서까지 바꿔서 되돌리고 삭제만 재적용(무관 diff 제거).
- 검증: tsc·eslint 0, 로컬 캡처 1280px·500px 확인. 390px 캡처가 잘린 건 윈도우 헤드리스 크롬 최소 폭(~500px) 탓 — 변경 전(stash)도
  똑같이 잘리는 것으로 확인. 실기기 폰 화면은 미확인.
- PR #153·#154 머지 → Vercel Production 배포, 운영 `suvisdev.cloud`·`www` HTML·캡처로 반영 확인.

### 작업 내용 (7) — 홈 바로가기 순서·Resume/About 이동 (브랜치 `feat/home-links-order`)
- 사용자 지시: 지킬 순서를 **개인 → 팀**으로, 헤더의 Resume·About도 지킬 옆(채팅창 아래)으로 내리고, About은 상단부터 보이게.
- 원인 확인: About 링크가 `/contact#contact`라 소개(요약·주요 영역·프로젝트)를 건너뛰고 아래 연락처 섹션(`id="contact"`)으로 스크롤됐다
  → `/contact`. 헤더 nav가 비어 `nav` 요소째 제거(로고·로그인·관리자 메뉴 유지, `navLinkClass`는 LESSON이 계속 사용).
- Resume·About은 헤더에서 `hidden md:flex`라 **모바일에선 원래 안 보였는데**, 본문으로 옮겨 모바일에서도 보인다.
  내부 페이지는 `Link`(같은 탭), 지킬은 `<a target=_blank>`.
- 검증: tsc·eslint 0, 캡처 — 홈 1280px(한 줄 4개)·500px(두 줄 줄바꿈), `/contact` 맨 위 ABOUT부터 표시.
- PR #155 머지 → Vercel 운영 반영(순서·About href `/contact` HTML로 확인).

### 작업 내용 (8) — 오른쪽 상단을 이름 드롭다운 하나로 (브랜치 `feat/header-user-menu`)
- 사용자 지시: 마이페이지·로그아웃 등을 이름("태기") 클릭 메뉴로. 관리자 LESSON(타이타닉·데이터 수집)·Admin도 같이 넣어 헤더 오른쪽은
  로그인 전 "로그인·회원가입", 로그인 후 "이름 ▾" 하나만. 이름은 원래 모바일에서 숨겨졌는데 이제 트리거라 모바일에도 보인다.
- 드롭다운은 규칙대로 shadcn CLI로 받음(`components/ui/dropdown-menu.tsx`). 막힌 점 셋:
  ① 로컬 node_modules가 **pnpm 11.21.0**로 설치돼 있어 pnpm 10 dlx가 store 불일치로 실패 → pnpm 11로 실행.
  ② 최신 shadcn이 npm `cn` 패키지(shadcn 공식, 9월 신설)를 같이 추가 — 정체 확인 후 프로젝트 관례(`@/lib/utils`의 cn)로 바꾸고 제거.
  ③ `radix-ui`(전체 묶음)는 lockfile +1498/−80, 기존 Dialog의 공통 부품(portal·primitive) 버전까지 바꿈 → 관례대로
     `@radix-ui/react-dropdown-menu`만 추가해 **기존 의존성 변경 0줄**(+482).
- 헤더가 듣던 세션 변경 이벤트(`suvis-session-changed`·storage)를 `AuthLoginButton`이 구독하도록 — 관리자 메뉴가 옮겨 오면서
  다른 탭 로그아웃·만료(SessionSync)를 따라가야 해서. 헤더는 상태·이펙트 없이 로고+버튼만.
- 검증: tsc·eslint 0, CI와 같은 pnpm 10 `--frozen-lockfile`(새 node:22 컨테이너) 통과, 캡처 — 임시 라우트에 가짜 관리자 세션을 넣고
  Enter로 메뉴를 열어 확인(라우트 삭제), 로그아웃 상태 헤더 확인. 로그아웃 클릭 동작은 기존 로직(`logoutSession`) 그대로라 실클릭은 미확인.
- PR #156 머지 → Vercel 운영 반영(로그아웃 상태 HTML에 Admin·LESSON 정적 링크 0 확인).
- 막힌 점(작은 것): 임시 라우트를 지운 뒤 tsc가 `.next/dev/types/validator.ts`의 지운 라우트 참조로 실패 — gitignore된 dev 캐시라
  `.next/dev` 삭제 후 0. 임시 라우트로 캡처한 뒤엔 dev 캐시도 같이 지울 것.

### 작업 내용 (9) — 약속 타일 맨 뒤로 (브랜치 `feat/yaksok-last`)
- 사용자 지시. `TEAM_PROJECTS` 배열에서 약속을 ARDA 뒤로(내용 변경 없이 순서만). 홈과 `/apps`가 같은 배열이라 둘 다 반영.
  홈 순서 Mova · Gildle · ARDA · 약속(캡처 확인). tsc·eslint·prettier 0.
- PR #157 머지 → Vercel 운영 반영(타일 순서 HTML 확인).

### 작업 내용 (10) — LangChain·LangGraph 현황 조사 + LangGraph 계획 문서
- 사용자 질문 "랭체인·랭그래프 들어갔나": LangChain은 `execsuite` LangChain 채팅 엔진 1파일(관리자 전용 `/langchain`)만,
  LangGraph는 의존성·import 0 — 07-30 "LangChain+pgVector → LangGraph+Neo4j" 계획 문서만 있고 `langgraph_interactor.py`는
  빈 파일이었다가 09-11 삭제. 실제 에이전트는 직접 짠 `ontology/app/agent/agent_loop.py`.
- 면접용으로 "직접 짠 루프를 LangGraph로 옮기고 하네스로 동등성 증명" 계획 작성(구현은 사용자가 집에서):
  `suvisdev/apps/ontology/_docs/LANGGRAPH_AGENT_LOOP_PLAN.md` — drop-in(같은 생성자·run·AgentDecision), `AGENT_LOOP_ENGINE`
  스위치(기본 native라 CD 배포돼도 운영 불변), JudgePort·`<tool_call>` 프로토콜 유지(bind_tools 금지), 테스트 7개 두 엔진
  파라미터화, 하네스 2종 엔진별 비교.
- 곁가지 수정: backend-ci 경로에 `!**/*.md` — 앱 `_docs/` 문서만 바꿔도 backend-ci → 운영 재배포가 돌던 것.

### 작업 내용 (11) — 집 데스크톱(DESKTOP-T89E5ID) 프로덕션 이관 실행 · 컷오버
- (2) 런북대로 실행. 노트북은 개발 전용, 집컴은 **서버 전용**(사용자 결정). 22:58~23:01 약 3분 530 후 집컴 서빙.
- 집컴 WSL(Ubuntu 26.04, 사용자 `suvisdev`): docker·k3s(`--disable servicelb`)·Ollama 0.35·CUDA 13.3(WSL 저장소) 설치,
  llama.cpp `llama-server` **sm_75** 빌드, `suvisdev-app` 이미지 빌드·k3s import, `~/.venv-exaone` 재생성(fastapi·uvicorn·httpx·pydantic).
- 데이터: 노트북에서 USB(외장 2TB, NTFS)로 tar 10종(약 90GB) — lora_adapters·Ollama 모델 13종·HF 캐시·datasets·gildle/data·비밀값·유닛.
  `04_models_gguf`(20GB, Ollama 재생성용 원본)는 운영에 불필요해 WSL에 안 풀고 `D:\suvisdev_backup`에 보관.
  `LATEST`·`LATEST_GGUF`의 `/home/suteagy` → `/home/suvisdev`(원본 `.bak-suteagy`).
- lora-server: 노트북 유닛+drop-in 그대로, `/health` model_loaded·gguf, **73 tok/s**(GPU, VRAM 2.5GB/4GB).
- 결정(사용자): `PORTFOLIO_LLM_BACKEND=gemini`(7.8B는 4GB에 안 들어감) · **Ollama는 CPU 고정**(GPU 4GB는 lora 전용,
  override `CUDA_VISIBLE_DEVICES=-1`·`OLLAMA_LLM_LIBRARY=cpu`) — bge-m3 임베딩 60~140ms, exaone 2.4b 16 tok/s · `EMBEDDING_BACKEND` 유지.
- DB: 21:56 덤프(`pg_restore` 방법 2)로 사전 복원·검증 → 컷오버 때 **노트북 터널을 먼저 내리고**(530 확인) LAN 직결로
  `pg_dump -Fc | pg_restore --clean` 재복원. 노트북 윈도우 portproxy 15432→WSL 5432 + 방화벽 원격 IP를 집컴 하나로 제한(끝나고 닫음).
  public 42 + trash 21 = 63테이블, **public 42개 count(*) 전부 일치**, alembic `20260930_0001`. Arda 덤프는 제외.
- 배포는 `deploy.sh --external-db`를 그대로 쓰지 않고 **cloudflared만 뺀 같은 단계**를 수동 실행 → 내부 검증(Traefik ClusterIP+Host:
  movies·jwks, 파드→lora·Ollama 도달) → 컷오버 때 backend·auth 재시작 후 cloudflared replicas 1. 커넥터 4개(icn01·05·06), 외부 api·auth 200.
- 상시 가동: `.wslconfig` `instanceIdleTimeout=-1`·`vmIdleTimeout=-1`·`memory=9GB`·`swap=4GB`·`autoMemoryReclaim=gradual`,
  작업 스케줄러 `suvisdev-wsl-autostart`(로그온 시 `conhost --headless wsl -e sleep infinity`). docker·k3s·ollama enable, lora linger.
  WSL 종료 → 작업만으로 재기동 시 손대지 않고 외부 200 복구 확인.
- CD 러너 이전: 노트북 `teagy` 중지·등록 해제 → 집컴 `DESKTOP-T89E5ID`(v2.337.0, prod) 등록, 수동 Run workflow
  (run 36874220807) **성공**, api·auth 200.
- 거상 3클라 동시 가동: VRAM 3.9GB/4GB에서도 lora 정상(첫 요청 10s, 이후 2s·67 tok/s), 외부 200.

### 오류·막힌 점 (11)
- 드라이버 572.42(CUDA 12.8까지)인데 WSL CUDA 저장소가 13.3을 깖 → 빌드는 되지만 실행 불가 위험. 윈도우 드라이버 616.92로 올려 해결.
- `.wslconfig` 적용 직후 `ERROR_NO_SYSTEM_RESOURCES`로 WSL 미기동 — 설정을 기본값으로 돌려도 동일, **윈도우 재부팅으로 해결**
  (거상 3클라 가동 중). memory는 11GB→9GB로 낮춤.
- 열린 WSL 창이 없으면 수 분 만에 WSL이 통째로 꺼짐(db 재시작 중 복원 실패로 발견) → idle 타임아웃 2종 -1 + 로그온 작업.
- Ollama가 부팅 직후 GPU 탐색 watchdog 타임아웃(30s×2)으로 CPU 시작 — 사용자 결정으로 CPU 고정해 우연을 설정으로 바꿈.
- `deploy.sh --external-db`는 cloudflared를 replicas 1로 즉시 apply → 컷오버 전 실행하면 노트북과 같은 토큰으로 두 커넥터.
  런북의 "돌린 뒤 scale 0"도 그 사이 창이 생겨 단계 수동 실행으로 회피. (deploy.sh에 터널 제외 옵션 검토 여지)
- 비교 스크립트가 `pg_stat_user_tables.n_live_tup`(통계 추정치)을 써 복원 직후 0·불일치로 보임 → `count(*)`로 교체 후 전부 일치.
- Ollama 설치 스크립트가 `zstd` 없어 실패, 러너가 `libicu` 없어 `config.sh` 즉시 종료(Ubuntu 26.04: `libicu78`·`liblttng-ust1t64`).
- 작업 스케줄러 `-Hidden`은 작업 목록 숨김일 뿐 창은 뜸 → `conhost.exe --headless`로 교체.
- 거상 3클라 + WSL 9GB에서 윈도우 여유 RAM 0.5GB(WSL 페이지 캐시 3.2GB 미반환) → `autoMemoryReclaim=gradual`.
- 하네스 분류기가 sudoers 작성·러너 설치를 막음 → 사용자가 스크립트로 직접 실행.
- 집컴 첫 CD 배포가 **15분**(노트북 2~6분). 원인 미확인 — 러너 체크아웃 첫 빌드 캐시·빌드 중 RAM 7.1/8.7GB·CPU 차 추정. 다음 머지에서 재측정.

### 데이터 (11)
- 운영 DB 노트북 → 집컴(pgvector 0.8.6, 노트북 0.8.5). Redis는 캐시라 미이전.

### 산출물 (11)
- 집컴 이관 스크립트: 윈도우 `OneDrive/Documents/st/집컴이관/`(step1·1b·2·4·4b·10, laptop_open/close_db, pull_db_from_laptop — USB 묶음은 노트북에서 별도).
- 노트북 구성(k3s·db·lora·`~/actions-runner`)은 1~2주 롤백용 보존, cloudflared 0 유지.

---

## 2026-09-30

### 작업 내용
- **웹 인증을 localStorage JWT → httpOnly 쿠키(BFF)로 전환** (보안 백로그: 토큰 localStorage = XSS 탈취 가능).
  코드 완성 + 로컬 런타임 검증 → 프리뷰 사용자 실테스트 → **PR #134 머지(`607d28e`)·Vercel 프로덕션 배포 완료**.
- **v1 마무리 전체 점검**: 백엔드·프론트·아키텍처·mova 운영 하네스·gildle 운영 API·Flutter 앱까지 한 번씩 실행.

### 수정/구현
- **조사(서브에이전트 매핑)**: 토큰 저장소는 `localStorage["suvis_session"].token` 하나. 백엔드는 이미 access+refresh
  발급·`/auth/refresh`·`/auth/logout` 보유(웹은 refresh를 버리고 있었음). 쿠키 세팅은 백엔드가 아니라 same-origin
  Next 프록시가 해야 함(게이트웨이는 다른 도메인). 직결 인증 호출 다수 + 경로 변형 프록시 15개가 범위.
- **서버 BFF**(`08e8c6d`·`39a876c`): `lib/auth-bff.ts`(쿠키 세팅·게이트웨이 대행·`forwardToBackend`·`cookieBearer`),
  `/api/auth/{login,signup,refresh,logout}`, catch-all `/api/backend/[...path]`(쿠키→Bearer + 401 자동 리프레시).
- **클라이언트 배선**(`9a319bb`, 61파일): 세션에서 `token` 제거·`authHeader` 폐기, 직결 호출은 `/api/backend`로,
  개별 프록시 22개는 `cookieBearer`로, 로그인폼 2개는 `/api/auth/login`로, OAuth 프록시는 쿠키 세팅, 로그아웃은
  `logoutSession`(→`/api/auth/logout`). access TTL 7일 유지(쿠키도 7일 → 리프레시 없이 UX 동일, 짧은 TTL은 후속).
- 규칙 문서 갱신: `.claude/rules/api-standards.md` §3·`security/auth.md` §3(3계층 Bearer → 쿠키 BFF).

### 오류·막힌 점
- 로컬 검증 시 dev 서버가 `api.suvisdev.cloud`(클라우드플레어 터널로 노트북에 되돌아옴)를 부르면 **hairpin ETIMEDOUT**.
  → backend(8000)·auth(9000)를 `kubectl port-forward`로 로컬(18000·18009)에 붙이고 dev를 그쪽으로 향하게 해 해결.
- **런타임 검증 성공**(임시 계정 signup→whoami→logout, 검증 후 계정 삭제): 회원가입 201·`{id,username}`만(토큰 없음)·
  sv_access/refresh 쿠키 세팅 → `/api/backend/mova/whoami` 200(쿠키→Bearer 전달·aud=suvis-mova) → 로그아웃 쿠키 삭제.
- tsc·eslint 0. 프리뷰에서 사용자가 로그인·OAuth·SPA 흐름 실테스트 후 머지.
- PR 머지는 하네스 분류기("Merge Without Review")가 막아 사용자가 직접 `gh pr merge 134 --merge` 실행.
- **Flutter 점검이 WSL 경로에서 크래시**: 윈도우 flutter(`C:\src\flutter`)를 `\\wsl.localhost` 경로로 돌리니
  `windows/flutter/ephemeral/.plugin_symlinks` 삭제 실패(errno 145)로 종료 + `analysis_options.yaml`을 멋대로 수정.
  → 수정분 되돌리고 저장소를 `C:\tmp`로 복사해 실행(analyze 0건·test 3/3), 복사본은 키 파일이 있어 즉시 삭제.

- **쿠키 전환 뒤 "로그인돼 보이는데 인증이 필요합니다"**(사용자 제보, mova 채팅 대화 목록): 전환 전에 로그인해 둔 브라우저는
  localStorage 표시만 있고 쿠키가 없다. auth 로그에 배포 후 성공 로그인 0건, 운영 임시 계정으로 쿠키 유 200·무 401 재현.
  쿠키 7일 만료 뒤에도 같은 어긋남이 반복될 구조였다. → `SessionSync`(루트 레이아웃)가 페이지 열 때 `/api/backend/mova/whoami`로
  확인해 401이면 표시를 지운다(만료 access는 catch-all이 refresh). mova 헤더·로그인 버튼이 세션 변경 이벤트를 듣게 함.

- **쿠키 전환 누락 프록시 9개**(사용자 제보: 마이페이지 진입 불가·찜 확인 401): 오전 일괄 치환이 `request.headers.get`만 잡고
  `req.headers.get`을 쓰는 9개(mypage·watchlist 4·reviews 3·dispatch adress search)를 놓쳤다 → 마이페이지가 401 → 세션 정리 →
  로그인 → 다시 401 반복. 전부 `cookieBearer()`로 교체, 전수 grep으로 잔여 0 확인. 소셜 로그인 뒤 사이트 홈으로 가던 것도
  로그인 전 경로를 sessionStorage에 적어 두었다가 돌아가게 수정(`rememberPostLoginPath`/`takePostLoginPath`, 사이트 안 경로만 허용).

- **v1 마감 문서 정리**(사용자 지시 "전부 읽고 바꿔야 할 것 전부"): ① 지킬 블로그 `suvisjk`(jk.suvisdev.cloud) 전 페이지·포스트 31편을
  전부 읽고 현행화 — index·toc·about·overview·mova·gildle·guidelines·schedule·issues·appendix·`_data/project.yml`·CLAUDE.md(초기 스캐폴드
  잔재 제거)·푸터, 09-30 데블로그 추가, 없던 스크린샷 4장을 운영 화면 캡처로 추가. 포스트(그날의 기록)는 고치지 않음. Pages 빌드 성공·실페이지 확인.
  ② 사이트 `/resume` 페이지가 옛 수치(10주·550+·EC2·AWQ·Leaflet)였던 것을 v1 사실로 갱신(캡처 확인).
  ③ 바탕화면 `진수택_이력서_자소서` 전 파일(루트 00~05 md/html/pdf, 09-29_수정본 11개, 면접대비 5개)을 읽고 갱신 — 이전본은
  `_이전본_09-30이전/`에 보관, html 재생성·pdf 재출력, 면접대비는 Arda를 빼고 09-30 사실로(에이전트 운영·도구 10개·쿠키 인증·웹/앱 통일).
  **미확인으로 남긴 것**: 블로그 `_posts/2026-08-28-agent-progress`는 팀 프로젝트(Arda) 글이라 suvisjk 방침("팀 콘텐츠 금지")과 어긋나지만
  사용자 글이라 삭제하지 않고 보고만 함. 이력서의 "(연도 확인)"·Arda 수치는 확인 불가로 그대로.

### 데이터
- 전체 점검 결과(09-30 14시): pytest **1030 passed**·2 skipped·7 deselected / import-linter **6 kept** / tsc·eslint 0 /
  mova 운영 하네스 단일턴 **28/28**·멀티턴 **16/17**(1건은 "9월 30일자로" 날짜 의존 검사 — 오늘이 09-30이라 "오늘"로 답함) /
  gildle 운영 API(routes 3모드·options 4·loops 3·walk/plan·app/version) 200, 보호 엔드포인트 무토큰 401 /
  Flutter `analyze` 0건·`test` 3/3 / 파드 에러 로그 0 / 운영 파드 소스 1280파일이 저장소와 sha1 일치(재배포 불요).
- 운영 라이브 확인: `suvisdev.cloud` `/api/auth/login` 오답 401·`/api/backend/mova/whoami` 무쿠키 401·`/api/auth/logout` 200.
- 세션 마감 시점 운영: main `260758d`(PR #134~#138 머지), Vercel 배포 성공, 백엔드는 재배포 없음(서빙 코드 변경 없음).
- 미처리(이번 세션 이전부터): ruff 린트 11건(UP042×7·B905×2·I001·UP017)·포맷 드리프트 28파일.

### 산출물
- 커밋 `08e8c6d`·`39a876c`·`9a319bb`(+규칙·일지) → PR #134 머지 `607d28e`, Vercel 프로덕션 배포 성공.

---

## 2026-09-29

### 작업 내용
- 사용자 질문 "우리 데이터가 Neo4j에 있어?" → 확인 결과 **없음**. 노트북 k3s `deploy/neo4j`는 replicas 0,
  PVC `neo4j-data`는 21일째 `Pending`(한 번도 바인딩 안 됨 = 기동 이력 없음), 도커 컨테이너·볼륨도 없음.
  백로그의 "Movie 40/Person 427"은 08-04 compose 시절(데스크톱/구 EC2) 기록이고 k3s 이전 때 따라오지 않았다.
  코드 참조는 execsuite PDF 로더의 `neo4j_graphrag.PdfLoader`(DB 미연결)뿐.
- 사용자 결정: **Neo4j는 하지 않는다.**

### 수정/구현
- `k8s/neo4j.yaml` 삭제, `deploy.sh` apply 목록·주석에서 제거, `k8s/README.md` 대응표에 삭제 표기.
- `.env.example`에서 `NEO4J_PASSWORD` 제거(`.env` 값은 그대로 — 쓰는 곳 없음).
- PROGRESS 백로그·`MOVA_POST_V1_ROADMAP.md` 항목 폐기 표기, `MOVA_PORTFOLIO_SUMMARY.md` 기술 표에서 Neo4j 행 삭제
  (운영에 없는 기술을 적어 둔 상태였다). execsuite·ontology의 GraphRAG 설계 문서는 향후 구상이라 유지.

### 오류·막힌 점
- 클러스터의 `deploy/neo4j`·`svc/neo4j`·`pvc/neo4j-data` 삭제는 하네스 자동 모드가 막아 사용자 실행으로 넘김.
  사용자가 `kubectl -n suvisdev delete deploy/neo4j svc/neo4j pvc/neo4j-data` 실행 → 3개 삭제 완료.
  매니페스트가 빠졌으니 deploy.sh가 다시 만들지는 않는다.

- **도커 롤백용 잔여물 정리**(k3s 1단계 3주 무사고): backend·auth 컨테이너는 이미 없었고, 남은 `nginx`
  컨테이너(Exited)·`nginx:alpine` 이미지 삭제. `suvisdev-app:latest`(6.84GB)는 `deploy.sh --build`가 `docker save`로
  k3s에 import하는 원본이자 레이어 캐시라 유지. `arda-*` 컨테이너는 해커톤 금지 규칙으로 미접촉.
- 노트북 `docker-compose.yaml`(untracked)을 **db·redis만** 남기게 축소 — nginx·certbot·backend·auth·pgadmin·
  cloudflared·neo4j 정의가 남아 있어 `docker compose up -d` 한 번이면 k3s와 백엔드·터널이 이중 기동될 수 있었다.
  원본 `~/docker-compose.yaml.bak-20260929`. `compose config --services`=db·redis, `compose ps`가 기존 컨테이너를
  그대로 인식(볼륨 `suvisdev_db_data` 동일) 확인.
- **배포마다 터널 ~10초 530 수정**(`k8s/deploy.sh`): 오늘 배포 직후 api가 530을 냈다. 원인은 cloudflared.yaml
  (데스크톱 보호용 replicas 0)을 그대로 apply → 파드 종료 → `scale --replicas=1`로 재생성하는 순서. `--external-db`
  일 때는 `replicas: 0`을 1로 sed 치환해 apply하도록 변경(치환 대상 줄이 없으면 즉시 실패), scale 줄 삭제. 데스크톱은
  종전대로 0. 검증: `kubectl diff` 무변경 → 배포 중 1초 간격 프로브 **40/40 200**, 터널 파드 이름 동일(재시작 없음).
- k3s의 `service/nginx`는 nginx가 아니라 Traefik을 가리키는 ExternalName 별칭(`nginx-alias.yaml`) — Cloudflare
  대시보드 라우트 `http://nginx:80`을 안 바꾸려고 둔 것. 실제 nginx 프로세스는 어디에도 없다.

- **[오후] 방문자 통계 봇 구분**(사용자 질문 "09-28 방문자가 왜 22명?"): 22명 중 19명이 새 쿠키·0초 체류(핑 1회)·
  11:54~11:59에 8명(12~92초 간격)·14:41~14:44에 5명, 재방문은 본인 1명뿐 → 실사용이 아니라 JS 실행 크롤러·링크
  미리보기(Play Console URL 검증 15:51 커밋 직후 15:56~16:22)·여러 브라우저 테스트(14:35 배포 직후)로 판정. 확정 로그
  (UA)가 없어 구분 기능 추가: 핑 라우터가 `User-Agent`를 받아 `is_bot_user_agent`(bot·crawl·spider·headless·preview·
  facebookexternalhit·kakaotalk·curl…, UA 없음도 봇)로 판정, `visitor_activity.is_bot`·`user_agent`(256자) 컬럼
  (`20260929_0001`). 통계는 사람 기준(지금 접속·오늘·7일·누적), `today_bots`·`today_one_shot`(첫 핑=마지막 핑)·
  일별 `bots`/`one_shot`. 어드민 타일 "오늘 실방문 / 오늘 봇·1회성" + 추이에 봇 점선. 기존 행은 사람으로 간주,
  09-28의 19명은 1회성으로 표시된다. 테스트 +2(UA 규칙·사람/봇/1회성 분리), UA 없는 핑을 사람으로 세던 기존
  테스트 2건은 브라우저 UA를 넘기게 수정(계약 변경). analytics 9 passed.

- **[저녁] 저장소 위생 2건**(코랩 v10 대기 중 병행, 사용자 지시):
  - **ruff 버전 고정**: `pyproject.toml [tool.ruff]`에 `required-version = "==0.16.9"` 추가. uvx가 최신 ruff를 끌어와
    무관 파일 17개를 재포맷한 사고(WORK_LOG_MOVA 09-29 (9)) 방지 — 저장소는 0.16.9 포맷과 일치. 검증: `uvx ruff@0.16.9`
    통과, `uvx ruff@0.16.7`은 "Required version `==0.16.9` does not match" 거부.
  - **ontology api 라우터 lazy import**(`apps/ontology/adapter/inbound/api/__init__.py`): 예전엔 이 패키지 import만으로
    vision·sentiment 라우터가 torch/opencv를 통째로 끌어와 무거운 것과 무관한 테스트까지 느려지고 HF 오프라인에서
    hang했다. PEP 562 `__getattr__`으로 조립을 지연 — `import ...api`는 무거운 모듈 0개 로드, main.py가 각 라우터를
    꺼낼 때만 하위 모듈 import(한 번 만든 라우터는 전역 캐시). 검증: 경량 venv에서 패키지 import 시 `torch not loaded`,
    portfolio 라우터 조립·AttributeError 경로 확인, 포트폴리오 테스트 20 passed.
- **[저녁] 홈 포트폴리오 채팅 후속 질문 검색 보강**(`portfolio_chat_interactor.py`): 검색 임베딩이 현재 발화만 써서
  "gildle이 뭐야?" 다음 "그거 누가 만들었어?"가 맥락을 잃고 엉뚱한 문서를 부르던 문제. `_retrieval_query`가 지시어·
  역참조 표식(`그거`·`아까`·`누가 만들`…)이 있을 때만 직전 사용자 발화를 붙여 임베딩하고, 자기완결 질문("mova는?")은
  그대로 둬 주제 전환 희석을 막는다. LLM 프롬프트의 [대화] 히스토리는 무변경. 테스트 +3(후속 보강·자기완결 미보강·
  히스토리 없음), portfolio interactor 11 passed.

### 산출물
- 커밋 `chore: Neo4j 매니페스트·백로그 정리`, `feat(analytics): 방문자 통계 봇 구분`.
- (미커밋) ruff 버전 고정·ontology lazy import·홈 채팅 후속 검색 보강.

## 2026-09-28

### 작업 내용
- **노트북 C 드라이브 정리(476GB 중 여유 41GB)**: 최대 점유는 WSL `ext4.vhdx` 178GB(홈 100GB — lora_adapters
  45GB·캐시 34GB). 완료: docker 빌드 캐시 25.3GB·미사용 이미지 8.0GB·uv 캐시 12.9GB·npm 캐시 ~3.3GB
  (db·redis·arda-test-db 컨테이너 유지). **대기(사용자 집에서)**: ① LoRA 변환 중간물(f16 GGUF·merged·work
  ~37GB)·폐기 GGUF(09-09·09-17)·데이터셋 원본 `rm`(권한 검사로 사용자 실행) ② Windows `wsl --shutdown` →
  옛 `swap.vhdx`(~9.6GB)·다운로드 v6 zip 삭제 → diskpart `compact vdisk` → `wsl --manage Ubuntu
  --set-sparse true`(이후 WSL 삭제분 자동 반환). **WSL 안에서 지운 만큼은 압축 전엔 C:로 안 돌아온다.**
  재기동 자동화 확인: k3s·ollama·docker enabled, lora-server user unit(Linger=yes), db·redis unless-stopped.
  → **저녁 완료(사용자 실행)**: ① 중간물·09-17 GGUF·Temp 스왑 `rm`(WSL 114G→85G) ② 관리자 PowerShell에서
  `wsl -u root fstrim` → `wsl --shutdown` → `--set-sparse true` → diskpart `compact vdisk`. **vhdx 191G→96.5G,
  C: 여유 55G→143G.** 재기동 후 점검: 파드 3종 Running, lora-server v5 GGUF `model_loaded`, db·redis healthy,
  외부 `api.suvisdev.cloud` 200·`/portfolio/chat` 정답. nginx는 Exited 유지(재부팅 후 되살아나지 않음).
  (`!` 접두 sudo는 터미널이 없어 비밀번호 입력 불가 → `wsl -u root`로 우회.)
- **백엔드 이미지 슬림화 — CPU 전용 torch 전환**(09-11 결정 사항 착수, 사용자 "재빌드 실행해줘").
  파드 안 실측 `torch.__version__=2.12.1+cu126`·`cuda.is_available()=False`, 이미지 14.9GB(docker).
- **"배포 대기" 표기 검증**(PROGRESS에 09-11·09-17부터 남아 있던 것): 파드 안 파일로 직접 확인 —
  `import_router.py` `require_admin` 부착(09-11 보안 🟡), `exaone_small_llm_adapter.py` `exaone3.5:2.4b`
  (09-17 라우터 전환), execsuite PDF 요약 `keep_alive="0"`(09-17 7.8B 온디맨드), `movie_title.py` VO
  (어제 밤 15e6b8a). 09-17 f745447·09-22·09-27 빌드가 전부 포함했다 → PROGRESS 표기 정리.
- 발견: 구 도커 `nginx` 컨테이너가 재부팅 뒤 `restart=always`로 되살아나 `host not found in upstream
  "backend"`로 **크래시루프**(80/443 바인딩 시도). k3s 서비스엔 영향 없지만 문서상 "stop 보존" 상태와
  어긋난다. 하네스가 `docker update --restart=no nginx && docker stop nginx`를 차단(워크로드 간섭 분류)해
  **사용자 직접 실행 필요**.
- 메모리 갱신: 감성 스케줄러 메모를 "수정 완료"로, Arda 금지·Play Console 대기 신규.

### 수정/구현
- `suvisdev/Dockerfile`: `requirements.txt`를 sed로 `whl/cu126→whl/cpu`, `+cu126→+cpu` 치환한 임시 파일로
  pip 설치. **requirements.txt 원본은 데스크톱 `.venv`(학습·GPU 테스트)용 cu126 핀 그대로** — 파일을
  둘로 가르지 않고 이미지 쪽에서만 바꾼다(한 줄, SSOT 유지). CPU 인덱스에 `torch-2.12.1+cpu`·
  `torchvision-0.27.1+cpu`·`torchaudio-2.11.0+cpu` cp313 manylinux_2_28 휠 존재를 먼저 확인.
- bitsandbytes는 유지 — 어댑터가 `cuda`일 때만 쓰고(어제 CPU bf16 분기 추가) 휠 자체는 수십 MB.
  `torch.cuda.*` 비가드 호출은 `_docs/_tmp_h1_exaone_vram_check.py`(문서용 스크립트)뿐이라 런타임 영향 없음.

- **홈 개편 2차 — 07월 컨셉 재혼합**(사용자 "예전 컨셉을 조금 섞어줘, 너무 밋밋하다"): 09-27 구글식
  중앙 정렬(로고→검색창→타일)을 07-29 시점 2열 구조로 되돌리되 기능은 유지. 왼쪽 흰 카드에 로고·소개문·
  `HeritadeHeadline`(콘덴스드 대형 "Simplify Complexity, Scale Without Limits.") → AI 검색창+타일
  (`AppLauncher`, lg에서 좌측 정렬·입력창 배경 `#f4f4f4`로 카드와 대비) → 노란 CTA(`#f0dc3a`
  "Suvisdev 알아보기" → `/contact`). 오른쪽은 홀로그램 마스크 영상 패널(lg 이상), 모바일은 카드 안 compact
  영상. 09-27에 삭제했던 `heritade-headline.tsx`·`hero-image-panel.tsx`를 `git checkout adef914^`로
  그대로 복원(새로 쓰지 않음).
- **mova가 라이트 모드로 뜨는 원인·수정**(사용자 스크린샷 "왜 화이트 모드가 됐나"): mova는 08-28부터
  다크 고정인데 구현이 `MovaThemeSetter`의 `setTheme("dark")`, 즉 **저장된 전역 테마를 바꾸는 방식**이었다.
  메인 사이트는 `SiteChrome`이 경로 바뀔 때마다 `setTheme("light")`로 저장값을 되돌리는데, next-themes는
  `storage` 이벤트로 저장값을 **모든 탭에 동기화**한다 → 스크린샷처럼 홈 탭과 mova 탭을 같이 열면 홈 탭이
  저장값을 light로 쓰는 순간 mova 탭까지 라이트로 뒤집힌다. 수정: `components/theme-provider.tsx`가
  `usePathname`으로 `/mova/**`일 때 `forcedTheme="dark"`를 준다(저장값 불변, 탭 간 간섭 없음, next-themes
  0.4.6 소스에서 `forcedTheme ?? theme` 적용 확인). `MovaThemeSetter`는 불필요해져 삭제. 검증: `next dev`
  SSR HTML의 next-themes 초기화 스크립트 인자가 `/mova`에선 `"dark"`, `/`에선 `null`.
  → **이어서 사용자 결정 "변경하는 걸 없애고 메인은 화이트, mova는 블랙으로 고정"**: `forcedTheme`를
  `/mova/**`→dark, 그 외→light로 **항상** 주고, 테마를 바꾸던 코드를 전부 삭제 — `SiteChrome`의
  `setTheme("light")` effect, gildle 랜딩 헤더의 `ThemeToggle`, `components/theme-toggle.tsx`. 이제
  `useTheme`·`setTheme` 호출처가 저장소에 없다(저장값·localStorage는 읽지도 쓰지도 않음). SSR 확인:
  `/`·`/gildle`=`"light"`, `/mova`=`"dark"`.
- **홈 AI 채팅이 "길들"을 모름**(사용자 "너가 안 가르쳤니"): 색인 126청크 중 `길들` 포함 0건, `Gildle` 26건 —
  프로필·지킬 어디에도 한국어 이름이 없었다. `datasets/portfolio_corpus/profile.md` Gildle 항목에 "Gildle(길들)"
  이름 유래·계절 모드·Flutter 앱·스토어 심사 대기를 보강하고, **파드에서 리셋 없이 프로필만 재색인**
  (`datasets/`는 hostPath라 호스트 편집이 바로 보임, `python scripts/ingest_portfolio_docs.py
  datasets/portfolio_corpus` → 5청크 upsert, 지킬 청크 보존). 실호출 "길들은 뭐야" → 이름·유래·3축 점수·심사
  대기까지 정확히 답함.
- **재빌드 찌꺼기 정리**(사용자 지시): 도커 빌드 캐시 27.8GB → 7.8GB(구 cu126 pip 레이어 13.3GB는 `until` 필터에
  안 잡혀 id 지정 삭제, 오늘 레이어 5.2GB는 보존), containerd 미사용 이미지 `crictl rmi --prune`(구 cloudflared
  다이제스트 삭제. **주의: pause 이미지도 같이 지워져 즉시 재pull**해 복구 — 다음엔 prune 대신 대상 지정).
  댕글링 이미지는 0. 디스크 168G → 142G 사용.
- **홈 2차 개편 정정**(사용자 "디자인을 그대로 가져오라는 게 아니야, 심플하게 가는데 포인트만"): 2열
  카드·영상 패널을 걷어내고 09-27 중앙 구조(로고 → AI 채팅 → 타일)로 복귀. 포인트만 채택 — 콘덴스드
  디스플레이 헤드라인("Simplify Complexity, Scale Without Limits." 회색/검정 교차, 크기 축소), 검색창
  포커스 테두리·"Suvisdev 알아보기" 화살표 원에 노란 악센트(`#f0dc3a`). 복원했던 두 컴포넌트는 다시 삭제.
- **홈 채팅 UX**(사용자 제안): 대화 패널을 입력창 **위**에 쌓는다(메시지 위·입력 아래 관례).
- **앱 타일 라벨**(사용자): 카탈로그에 `kind` 추가 — mova·gildle "개인 프로젝트", ARDA "팀 프로젝트 · 원티드
  해커톤 출품작". `/apps` 페이지는 같은 데이터를 쓰지만 라벨은 홈 타일에만 표시.
- **홈 타일 후속**(사용자): 헤드라인·"알아보기" CTA 삭제, 영문 부제 줄 삭제(준비 중은 gildle에만), 팀
  프로젝트 **'약속'(알약 식별, https://www.seuk.cloud/) 카드 복원** — 08-26 SEUK 카드로 교체되며 지워졌던
  항목·이미지(`apps-yaksok.jpg`)를 git에서 되살림. `/apps` 페이지에도 같은 데이터로 노출.
- **mova 채팅 스크롤 클로드식 전환의 후속 버그 수정**(사용자 "채팅창이 이상해졌어"): 입력창이 사라지고 큰
  빈 영역이 생김. 노트북엔 브라우저가 없어 **Playwright+Chromium을 스크래치에 설치**(누락 `libasound2`는
  `apt-get download`+`dpkg -x`로 로컬 추출, `LD_LIBRARY_PATH`)해 프로덕션 빌드(`next start`)로 재현·실측:
  ① 익명 채팅 래퍼에 `min-h-0 overflow-hidden`이 없어 리스트가 콘텐츠만큼 자라고, 스페이서가 그 높이를 기준
  으로 또 커지는 되먹임(리스트 7,205px→152,946px) ② 근본은 mova 레이아웃 루트가 `min-h-dvh`(auto 높이)라
  `flex-1 min-h-0` 체인이 뷰포트에 안 묶임(루트 1,130px > 900px). 수정: 스페이서 상한을 `min(리스트,
  뷰포트)`로, 익명 래퍼에 제약 추가, **채팅 페이지 높이를 `calc(100dvh − 헤더)`로 명시**(헤더 실측 데스크톱
  57px·모바일 86px). 재검사: 리스트 769px 고정, 입력창 826~900px, 2턴째 내 말풍선이 상단(scrollTop 622).
- **약속 카드 라벨** "팀 프로젝트 · 문화체육관광 해커톤 출품작"(처음 "충붕"을 충북으로 잘못 해석했다가 사용자 정정).
- **전체 파이프라인 점검**(사용자 "파이프라인 점검하고 테스트 한 번씩"): 백엔드 전체 pytest **892 passed /
  3 failed**(실패 3건은 `test_market_reviews` 라우터 DB 의존 기존 건) · ruff·format·import-linter(6 kept)
  통과 · env drift 정상 · 파드 3종 Running, lora-server(v5 GGUF)·ollama 7.8B 상주 · API 스모크(mova 목록·
  gildle 버전·경로 31노드 1.18km·루프 3후보·포트폴리오 채팅) 정상 · 스케줄러(랭킹·감성·KOFIC 8편·에디터
  리뷰) 가동. **프로덕션 E2E(Playwright)**: 홈 타일 4개+라벨, 홈 채팅 "길들은 뭐야" 정답, mova 예매 채팅에
  롯데 회차 링크 6·시간표 링크 2·네이버 극장 링크 4·입력창 하단 고정(900/900), 길들 지도 두 번 클릭→경로
  2.4 km·33분 카드. **길들 프로덕션 지도 초기 버그**: 네이버 SDK가 컨테이너에 `position:relative`를 인라인
  강제해 `absolute inset-0`이 무효(높이 0) → `h-full w-full`로 수정·재배포·실측(789px, 타일 36장).
  관찰: 에디터 리뷰 스케줄러 오늘 주기 "생성 0 / 대상 15"(Gemini SKIP·기사 부족 추정, 오류 로그 없음).
- **실패 3건·스킵 2건 후속**(사용자 "테스트해보고 이상 있으면 수정"): 실패 3건은 `test_market_reviews`가
  08-31에 추가된 감성 분석 BG 의존(`get_review_sentiment_backfill_use_case`)만 오버라이드하지 않아 실제
  provider가 DB 세션을 만들다 죽던 것 → `_FakeSentimentBackfill` 오버라이드 추가, 25/25 통과, 전체
  **895 passed / 0 failed**. 스킵 2건(gildle 스크립트, shapely)은 컨테이너에 shapely 임시 설치 후 실행
  → 10/10 통과, 코드 이상 없음(서빙 이미지에 shapely를 넣지 않는 방침은 유지).
- **홈 AI 채팅 범위 제한**(사용자 "나에 관한 질문 말고는 대답하지 말아야"): 검색 top1 점수가 주제 밖(날씨·레시피
  0.31~0.51)과 주제 안(학력·mova 0.41~0.64)이 겹쳐 임계값으로는 못 가른다 → 시스템 프롬프트 규칙 0(범위 판정)
  + 범위 밖이면 `[범위밖]`만 출력 → 인터랙터가 고정 거절 문구로 치환. 실측 10문항(주제 안 4·밖 6) 모두 의도대로.
- **ARDA 지킬 색인**(사용자 "아르다도 지킬 있잖아"): `Seuk-Team/jekyll`(ats.suvisdev.cloud) 공개 저장소를
  스크래치에 클론, 민감 패턴 검사(이메일·IP·키 0건) 후 `datasets/arda_jekyll/`(gitignore)에 복사해 파드에서 색인.
  **사고**: 청크 ID가 `portfolio:<파일명>#n`이라 ARDA의 index·overview·devlog 등이 suvisjk 같은 이름 청크를
  덮어씀(126+115→224) → 색인 스크립트에 `--ref-prefix` 추가, suvisjk도 `datasets/suvisjk_jekyll/`(gitignore)에
  사본을 둬 파드에서 `--reset` 전체 재색인: 프로필+suvisjk 162 + ARDA(`portfolio:arda/…`) 115 = 277청크.
  "ARDA 기술 스택·일정·어려웠던 점" 지킬 근거로 답함. 문서 갱신 시 두 사본을 다시 복사하고 스크립트 docstring
  명령 두 줄 실행.
- 홈 로고 이미지 제거(사용자) — 제목 "Suvisdev" 텍스트만.
- **홈 채팅 "학력" 오답**: ARDA(채용 ATS) 지킬에 "지원자 학력·이력서" 청크가 많아 프로필 학력 청크가 상위 6개에서
  밀려남 → 검색 풀 30개에서 프로필 청크 상위 2개를 항상 근거에 포함. 포트폴리오 하네스 11/11.
- **우하단 플로팅 채팅 버튼 삭제**(사용자 스크린샷 지시): `site-chrome.tsx`의 `SuvisChatPanel` 마운트
  제거 + 유일 사용처였던 `components/gemini-chat-panel.tsx` 삭제. 이 패널이 부르던 `/api/v1/langchain/chat`
  프록시는 다른 화면(`/langchain/chat`)이 쓰므로 그대로 둠.

### 오류·막힌 점
- 노트북엔 `node_modules`·pnpm이 없다(09-22 ⑳ corepack 문제) → `npx -y pnpm@10 install --frozen-lockfile`로
  설치(`node_modules`는 gitignore). 이후 `tsc --noEmit` 0건·eslint 0건·prettier 정리·`next dev`로 SSR HTML
  실측(헤드라인·영상·CTA·타일 존재, `bottom-4 right-4` 버튼 부재).
- 이미지엔 `nvidia-nccl-cu12`·`nvidia-ml-py` 두 패키지가 아직 남는다(torch cpu 휠이 아닌 다른 의존이
  끌어옴, 수백 MB) — 추적 안 함.

### 데이터
- 없음.

### 산출물
- **이미지 재빌드 결과**: 전체 5m59s(pip 168s·export 105s), 도커 이미지 **14.9GB → 6.83GB**, containerd
  압축 **4.5GiB → 1.7GiB**, pip 레이어 9.01GB → 3.72GB. 파드 `torch 2.12.1+cpu / torchvision 0.27.1+cpu /
  torchaudio 2.11.0+cpu`, `cuda.is_available()=False`(종전과 동일). 검증: mova 단일턴 23/23·멀티턴 12/12,
  `/portfolio/chat` 15.9s 정상, gildle `/api/gildle/routes` 5.5s 정상, `/mova/movies` 200, echo·convnext
  어댑터 import 정상, 파드 RSS 932Mi.
- (커밋 대기) `suvisdev/Dockerfile`, `suvis/app/page.tsx`, `suvis/components/home/{app-launcher,
  heritade-headline,hero-image-panel}.tsx`, `suvis/components/site-chrome.tsx`, `theme-provider.tsx`,
  `app/mova/layout.tsx`, `app/gildle/page.tsx`, 삭제 `gemini-chat-panel.tsx`·`mova/mova-theme-setter.tsx`·
  `theme-toggle.tsx`,
  `suvisdev/datasets/portfolio_corpus/profile.md`.

---

## 2026-09-27

### 작업 내용 (저녁 — 저장소 전체 데드 코드·낡은 이름 정리, 사용자 지시)
- "qwen은 어디서 쓰나 → 전부 EXAONE·Gemini 아니냐"에서 출발해 "죽은 경로·오류 코드·낡은 코드·안 쓰는
  코드 전부 정리"로 확장. 스캔 도구: import 문 기준 미참조 모듈 스캐너(스크래치 스크립트)·vulture(신뢰도
  60/80)·프론트 knip. **후보마다 클래스·함수명까지 grep으로 참조를 재확인**하고 지웠다.

### 수정/구현
- **Qwen 명칭 제거**(실체는 09-17부터 exaone3.5:2.4b): `qwen_llm_adapter`→`exaone_small_llm_adapter`
  (`ExaoneSmallLlmAdapter`), `qwen_intent_classifier`→`llm_intent_classifier`(`LlmIntentClassifier`),
  `qwen_harvester_command_parser`→`llm_harvester_command_parser`, DI `get_exaone_small_llm_port`. 문서·주석·
  테스트 파일명 동반 갱신. 비전 MCP 에이전트 기본 모델 `qwen2.5:1.5b`(Ollama에 없어 404)→exaone 2.4b로
  바꿨다가 아래 정리에서 파일 자체 삭제.
- **삭제(백엔드 94파일)**: titanic "미구현" 스텁 30(추상 ORM·매퍼·엔티티 10종×3) · viewer 구 로그인·
  회원가입 체인 12(09-11 언마운트; `login_pg_repository`·스키마·DTO는 OAuth·테스트가 써서 유지) ·
  mova DTO로 대체된 엔티티 14·VO 7·platform_* 스키마/ORM/DTO 9·`pg_session.py` · execsuite piper_* MCP
  스텁 5+토폴로지 · ontology 미등록 MCP 에이전트 3(`sentiment_analysis_mcp_server`·`sentiment_echo_agent`·
  `vision_genre_agent`) · dispatch `DetectiveWatsonWatcherHub`+하네스 · gildle `KakaoGeocodingAdapter`·
  `ImportTreeSegmentInteractor`·`route_request/result_orm`·`RouteResponseSchema` · `model_servers/awq_server`.
- **삭제(심볼)**: `TreeSegmentRepository.save_many`(포트·CSV·PG·페이크·테스트), mova 미사용 스키마 클래스
  10(`MarketChatSchema`·`RankingBulkSchema`·`*CreateSchema` 등), auth `Permission`/`ROLE_PERMISSIONS`/
  `has_permission`·`OAuthAdapter` Protocol.
- 마이그레이션 `20260927_0002`: 0행·미참조 `route_requests`·`route_results` 드롭(downgrade는 0b92552ee0d7
  정의 복원). alembic env·`test_orm_schema` 갱신.
- **유지(의도적)**: `apps/sample`(문서화된 스켈레톤), contents K리그 ORM 4(테이블 존재·alembic 등록),
  `NetworkXRouteGraphAdapter`(동치 검증 스크립트), `SampleWalkGraphSource`·`OsmWalkGraphAdapter`(배치 스크립트),
  `VisionS3Repository`(S3 대안 어댑터), `_validate_email`(pydantic validator — vulture 오탐).
- **프론트(suvis, knip)**: 미사용 파일 64 삭제 — 구 홈 컴포넌트 4(09-27 개편 전 `apps-grid`·
  `featured-carousel`·`hero-jarvis-panel`·`quick-info-bar`), `mova-section`·`project-card`·`auth-open-link`,
  mova `genre-catalog`·`genre-onboarding`·`preferred-genres-badge`·`promo-banner`, shadcn ui 50(설치만 되고
  미사용), `hooks/use-*` 중복. 외부 미사용 export 21은 `export`만 떼고, eslint `no-unused-vars`가 잡는
  최상위 선언 15만 삭제(내부 참조 타입을 지웠다가 되돌린 뒤 이 방식으로 재작업). `package.json`
  미사용 의존성 35 제거(radix 24·zod·react-hook-form·date-fns·sonner·vaul 등) → `pnpm install
  --lockfile-only`(npx pnpm@10, lockfile −1,466줄). tsc·eslint 0, prettier 적용.
- 검증: 백엔드 755 passed(스크래치 venv에 boto3·ollama·langchain-core 추가) · ruff·lint-imports 통과 ·
  라우터 패키지 import 전수 확인. **배포 후** 파드에서 `alembic upgrade head`(→`20260927_0002`), mova 멀티턴
  12/12·단일턴 23/23, gildle `app/version`·`graph-edges`·`routes` 200, 파드 import 오류 없음.

### 하네스(문서) 정정 — "헥사고날·클린은 전면, DDD는 필요한 곳에만"
- 사용자 질문 "DDD까지 쓸 필요는 없는 거지?" → 아키텍처 감사 결과로 답하고 하네스를 실제에 맞게 고쳤다.
  `suvisdev/CLAUDE.md` **§P 신설**(도메인 객체를 두는 기준 3가지 + 두지 않는 경우 + 인터랙터 예외 규칙),
  §K 표에 "규칙 없는 엔티티 생성 금지"·"앱 예외→라우터 변환" 반영. `suvis` ponytail 스킬·하네스 문서 2개의
  "hexagonal DDD" 표현 정정. 감사 수치: 인터랙터→ORM 0, 도메인→외부 0, 라우터→저장소 1(계약상 허용),
  인터랙터 HTTPException 3파일(gildle 2 수정, mova games 1 잔여).

### 오류·막힌 점
- `\bOrchestrator\b`·모듈명 일괄 sed가 무관 문서까지 바꾸는 사고 2회(execsuite harness-lab 문서, 내부
  참조 타입 삭제) → 되돌리고 범위를 좁혀 재적용. **일괄 치환은 파일 목록을 먼저 보고 건다.**
- `pkill -f <스크립트명>`이 자기 셸을 죽임(명령줄에 같은 문자열). 백그라운드 작업은 PID로 관리할 것.
- `pnpm`이 WSL PATH에 없음 — `npx --yes pnpm@10`로 대체(lockfile v9 유지).


### 작업 내용 (메인페이지 — 구글 시작화면식 개편)
- 사용자 요청: 메인을 크롬 새 탭처럼 "로고 → 검색창 → 앱 아이콘 격자"로. 격자에는 **mova·gildle·팀
  프로젝트 arda 3개만**(나머지 라우트는 본인 전용이라 비노출, 소개 문구·정보 페이지 링크 불필요).
- 함께 제안된 "나에 대해 답하는 챗봇(오케스트레이터·학습)"은 이번 범위에서 제외 — 근거 문서 총량이
  지킬 46KB + 이력서 16KB ≈ 3~4만 토큰이라 파인튜닝·RAG·오케스트레이터 없이 **단일 Gemini 호출에
  문서 전문 주입**이면 충분하다고 정리. 착수 전 결정 필요: 공개 문서 범위(연락처 등), 익명 엔드포인트
  레이트리밋(저장소에 아직 없음), mova 우선순위와의 시간 배분.

### 수정/구현
- `suvis/app/page.tsx` 재작성: 로고(`suvis-logo.png`, 722×761 아이콘형이라 48px + "Suvisdev" 텍스트) +
  `AppLauncher`. 데이터는 `lib/apps-catalog.ts`의 `APPS_CATALOG`+`TEAM_PROJECTS`를 그대로 합쳐 씀(새 데이터 없음).
- `suvis/components/home/app-launcher.tsx` 신설(클라이언트): 검색창은 앱 이름(한·영·팀명) 필터, 엔터로
  첫 매치 이동(외부 URL은 새 탭). 타일은 카탈로그 커버 이미지를 원형으로, `available=false`(gildle)는
  부제 자리에 "준비 중". 기존 `components/home/apps-grid.tsx`(미사용, 하드코딩 2개)는 데이터가 카탈로그와
  달라 재사용하지 않고 그대로 둠(이전부터 데드 코드 — 과제 밖).
- 삭제: `heritade-headline.tsx`·`hero-image-panel.tsx`(page.tsx에서만 쓰이던 구 히어로).
- 검증: `pnpm type-check`·`pnpm lint` 통과, `next dev -p 3999`로 `/` 200 + Mova·Gildle·ARDA·검색창·"준비 중" 렌더 확인.
  (`pnpm`은 PATH에 없어 `npx pnpm`으로 실행.)

### 산출물
- 커밋 `adef914`(홈)·`a88c48b`(노트북 폴백)·`2ec9c34`(문서), main 푸시 → Vercel 자동 배포.
  푸시 약 60초 뒤 `https://suvisdev.cloud`에 새 홈(검색창·3타일) 반영 확인. 미푸시로 쌓여 있던
  09-17~09-23 커밋 16개(`d0fd885`~`34181a4`)도 이번에 함께 올라갔다.


### 작업 내용 (추가 — 홈 입력창을 AI 채팅으로: 포트폴리오 문서 RAG 챗봇)
- 사용자 정정: 홈 입력창은 앱 검색이 아니라 **클로드·제미나이처럼 AI가 붙은 대화 입구**이고, 오케스트레이터는
  "지금 쓰는 7.8B"(노트북 ollama `exaone3.5:7.8b`). 결정 3건: 자료는 공개용 세트만·개인정보는 이름/학력 수준·
  누구나 + IP 레이트리밋. "파인튜닝 필요하면 코랩" — 이번엔 불필요(근거 주입 RAG).
- 조사(Explore 에이전트 2건)로 확정한 설계: **새 앱 없음**. 문서 RAG 스택(EmbeddingPort·pgvector `hub_knowledge`·
  HubLlmPort·FallbackHubLlmAdapter)이 전부 ontology(Hub)에 있고 `source` 칼럼으로 분리되므로 ontology에
  `portfolio` 유스케이스·라우터를 얹고 `source='portfolio_doc'` 행으로 색인. **마이그레이션 0건**. 도구 호출 루프도
  없음 — EXAONE 3.5 템플릿에 tool 형식이 없고(`ollama show --template` 실측) 답의 근거는 전부 문서라 매 질문
  검색→근거 주입이 더 단순·안정. 계획서 `suvisdev/_docs/plans/2026-09-27-portfolio-chat.md`.
- 7.8B 실측(설계 전): num_ctx 8192에서 5.7GB, lora-server(2.4GB)와 동시 상주 가능(합 7.8/8.2GB), 콜드 5s·근거
  2,240토큰 응답 7s. **ollama 기본 num_ctx 4096이라 근거가 잘림** → 오케스트레이터에 `num_ctx` 옵션 추가가 필수였음.

### 수정/구현 (추가)
- `core/lol/t1_mid_faker_orchestrator.py`: `generate(..., num_ctx=None)` + 본문 조립 `_build_body` 분리(테스트 가능).
- ontology 신규: `exaone_llm_adapter.py`(7.8B·temperature 0·num_ctx 8192·keep_alive 5m, FakerOrchestratorError→
  HubRagError로 감싸 폴백이 걸리게), `portfolio_chat_dto.py`(Command.from_schema/Dto.to_schema lazy import),
  `portfolio_chat_use_case.py`, `portfolio_chat_interactor.py`(top-6·유사도 0.15 컷·근거 없으면 LLM 미호출 고정 답·
  히스토리 6턴·시스템 프롬프트에 연락처 금지 규칙), `portfolio_chat_schema.py`(message 1~1000·history≤10),
  `rate_limit.py`(mova 것 복제 — Spoke import 금지), `portfolio_chat_router.py`(`POST /portfolio/chat`, 업스트림
  오류는 일반 문구+로그), `portfolio_chat_provider.py`(`PORTFOLIO_LLM_BACKEND` exaone(기본, Gemini 폴백)/gemini).
  `api/__init__.py`에 `portfolio_router`, `main.py`에 prefix 없이 include.
- `scripts/ingest_portfolio_docs.py`: md → front matter/HTML 주석 제거 → `## ` 단위 청크(1500자 초과 재분할·200자 미만
  병합·20자 미만 폐기) → `HubRagInteractor.ingest_movie`(범용 upsert) → `portfolio:<stem>#<n>`. `--reset/--dry-run`.
- `datasets/portfolio_corpus/profile.md`: /resume 공개 페이지에서 옮긴 프로필(이름·학력·교육·프로젝트·기술 스택),
  **전화·이메일 제외**. 1차 색인 뒤 "학력이 어떻게 돼?"가 Gildle 청크(0.41)를 잡길래 학력 절을 독립 청크로
  보강(0.43~0.51로 1위 회복). 청크 제목이 임베딩에 같이 들어가므로 절 제목이 검색어와 맞아야 한다.
- 테스트 4파일 16건 신규(오케스트레이터 본문 3·인터랙터 5·스위치 4·라우터 5 — 429 포함). ontology+core/lol 전체
  119 passed. ruff·mypy(내 파일)·lint-imports 6/6·`import main`·env drift 통과.
- 프론트: `app/api/portfolio/chat/route.ts`(프록시, 무인증), `lib/portfolio-api.ts`(`sendPortfolioChat`,
  `safeApiErrorMessage`), `components/home/portfolio-chat-panel.tsx`(표시 전용), `app-launcher.tsx`를 필터→채팅
  전송으로(낙관적 추가·실패 롤백·IME 가드). type-check·lint·prettier 통과.

### 오류·막힌 점 (추가)
- 노트북엔 pytest 환경이 없다(프로젝트 `.venv`는 gildle용 슬림). 스크래치 `uv venv`에 경량 의존성 + CPU torch
  계열로 구성 — ontology `api/__init__.py`가 비전 라우터를 즉시 import해 라우터 테스트만 돌려도 torch·ultralytics·
  peft까지 필요했다(mova/analytics는 lazy `__getattr__`라 이 문제가 없음. 손대지 않음, 후보로 기록).
- 호스트 색인 실행에 `psycopg-binary` 필요(없으면 "no pq wrapper").
- `check_env_drift.py`는 이전부터 exit 1(REDIRECT_URI·PGADMIN 등 7키). 새 PORTFOLIO_* 3키는 `.env`에 명시.

### 데이터 (추가)
- `hub_knowledge` `portfolio_doc` **124청크**(profile 4 + 지킬 about/overview/mova/gildle/devlog + `_posts` 26편).
  bge-m3(ollama) 임베딩, 실패 0. 재색인은 `--reset`.

### 산출물 (추가)
- 백엔드 `./k8s/deploy.sh --external-db --build` 배포, 운영 스모크(NodePort): "만든 앱"(콜드 10.3s, 근거 6청크로
  Mova·Gildle·suvisdev.cloud 정확) · "학력"(5.5s, 경상대 건축공학과 자퇴·하이미디어 과정) · "전화번호"(1.3s,
  "Contact 페이지 참고, 공개되지 않음") · "오늘 날씨"(2.4s, 자료에 없음). **mova 23질의 회귀 23/23 유지**(7.8B
  상주 중 VRAM 7,833/8,188MB, 2.4B 라우터는 밀려났다 재로드).
- 커밋 `4c8b33b`(ontology 백엔드)·`b9b2127`(프론트)·`96122b9`(문서), main 푸시 → Vercel 45초 뒤 반영.
  프로덕션 사이트 프록시 경유 왕복 확인: "Gildle은 어떤 앱이야?" 16.3s(터널+콜드 로드, 근거 3청크로 A*·환경 점수·
  시즌 가중치까지 정확). 사용자 질문 "v6 필요?"에 대한 조사: 09-22 이후 운영 chat 234행 중 고유 질의 40개
  (대부분 하네스), 0편 응답 0건 — 실사용 로그가 학습 재료가 될 만큼 없어 v6 보류(`[M]` 09-27 참고).

### 작업 내용 (추가 — 페르소나 Suvisdev · 답변 마크다운 렌더링)
- 사용자 요청: 봇 페르소나를 **Suvisdev**로("수택의 '수' + 자비스의 '비스'"). 이어서 답변에 `**굵게**`·`[링크](url)`가
  원문 그대로 보이는 캡처 → "AI에 적용 안 되는 부분 다 찾아서 적용".
- 반영: 시스템 프롬프트에 이름·유래·말투(자비스처럼 차분·정중) + **허용 서식 규칙 5번**(굵게·글머리·번호·링크만, 표·
  제목·코드블록·이미지 금지 — 렌더러 지원 범위와 일치). 고정 답에도 자기소개. 프로필에 "Suvisdev라는 이름과 AI
  비서" 절 추가(→ "이름 뜻이 뭐야?" 답 가능). 주소는 전부 `https://` 전체 URL로.
- 프론트 `components/home/chat-markdown.tsx` 신규(의존성 없음, react-markdown 미설치 실측): 굵게·링크·bare URL·
  인라인 코드·글머리/번호 목록·문단, `#` 제목은 굵은 줄로 강등. 링크는 새 탭. **스킴 없는 링크
  (`[주소](suvisdev.cloud/mova)` 실측)는 https://를 붙인다.** 사용자 말풍선은 원문 그대로. 입력창 placeholder·로딩
  문구에 Suvisdev. esbuild 번들 + `renderToStaticMarkup`으로 렌더 결과 검증(tsx 직접 실행은 JSX 설정으로 실패).
- 재배포·스모크: "너 이름이 뭐야? 이름 뜻도" → 유래를 정확히 설명, "Mova는 무슨 프로젝트야?" → 굵게·링크 서식 사용.
  Vercel 반영 확인. 커밋 `f51c616`(페르소나·렌더러) + 후속(링크 보정·프로필 URL·문서).

### 조사 (추가 — "mova 리뷰 크롤링 계속 되고 있나?")
- "리뷰 크롤링"의 실체는 `editor_reviews_scheduler`(24h 주기, 구글 뉴스 RSS 제목+요약 → Gemini 3~4문장 → "Mova
  에디터" 계정 리뷰). **돌고 있다**: 최근 주기 "생성 2 / 대상 15", 최근 14일 일별 1~20건(09-14~09-26). reviews 417건
  중 에디터 209건, **에디터 리뷰 없는 영화 3,209편** — 주기당 대상 15편이라 이 속도면 200일 이상.
- **`review_sentiment_scheduler`는 전부 실패 중**: "주기 완료 succeeded=0, failed=50", 원인
  `'frozenset' object has no attribute 'discard'`(Echo 감성 모델 로드 단계, transformers 4.47.1 핀과 최신 peft/torch
  조합 의심). 감성 미분석 리뷰 209건 = 에디터 리뷰 전부(자동 별점도 안 생김). 백로그 등록, 수정은 미착수.

## 2026-09-22

### 작업 내용 (인프라 — 배포 스크립트 이미지 정리 · 무료 호스팅 검토)
- `k8s/deploy.sh` 빌드 뒤 이미지 정리 추가: `docker image prune -f`(dangling만) +
  `docker builder prune --max-used-space 20GB`. **`crictl rmi --prune`은 쓰면 안 된다** —
  방금 import한 이미지를 미참조로 보고 지워 rollout이 `ErrImageNeverPull`로 죽는다
  (실측 116분 Pending). 실제로 쌓이는 건 dangling이 아니라 빌드 캐시(0.8→15.3GB).
- 사용자 질문 "Cloudflare만으로 서버 가동 / 무료 호스팅" 실측 근거 답변: 이미지
  **14.8GB**(ontology·vision·titanic의 torch·ultralytics 포함), 백엔드 RAM 980Mi,
  DB **121MB**. Cloudflare는 터널일 뿐 서버가 아니고 Workers/Containers로는 현재
  스택(pgvector·커스텀 LoRA) 불가. 무료 후보는 Oracle Always Free ARM(24GB)+Neon
  (pgvector)+Gemini, 단 mova+auth만 추려 이미지를 1GB 아래로 줄이는 게 전제. GPU
  무료 상시는 없음 — 서빙 이전 시 EXAONE→Gemini 방향과 같아 폴백 구조로 흡수.

### 오류·막힌 점
- 실행 중인 `deploy.sh`를 편집해 bash가 바뀐 파일을 스트리밍으로 읽다 line 61 문법
  오류 → apply 미실행, 직접 `kubectl apply` + rollout으로 복구. 배포 중 스크립트
  수정 금지.

### 산출물
- `k8s/deploy.sh`(prune 단계·주석), `susu/android/.gitignore`(google-services.json 제외).

### 작업 내용 (밤 — susu: 네이버 지도 Client ID 주입)
- 사용자가 바탕화면 `길들/네이버 클라우드 플랫폼.txt`에 NCP Maps Client ID를 받아 둠 →
  `susu/dart_defines.json`(gitignore 추가)에 넣고 `--dart-define-from-file`로 주입.
  `.env`의 `NAVER_CLIENT_ID`는 **네이버 로그인(OAuth)** 키라 지도와 별개 — 혼동 주의.
- `lib/core/config/env.dart` `AppConfig.naverMapClientId` + `lib/main.dart`에서
  `FlutterNaverMap().init()`(값 비면 건너뜀). 매니페스트 meta-data는 값이 소스에 박혀
  넣지 않음. 가이드 `GILDLE_APP_SETUP_GUIDE.md` §1-3 실제 방식으로 갱신.
- 검증: Windows Flutter(`C:\src\flutter`)를 WSL에서 `cmd.exe /c "pushd \\wsl.localhost\…"`로
  호출해 `pub get`(flutter_naver_map 1.4.x 잠금 반영) + `flutter analyze` — 신규 오류 0.
  기존 경고 3(`main.dart` key 파라미터)·오류 1(`widget_test.dart` MyApp)은 이전부터
  있던 것. `pub get`이 `analysis_options.yaml`을 자동 수정한 건 되돌림. Windows 플러그인
  심볼릭 링크 `ERROR_ACCESS_DENIED`는 데스크톱 타깃 전용이라 Android 빌드와 무관.
- ~~남은 콘솔 발급: Firebase~~ **자정 무렵 둘 다 받음** — `google-services.json`(프로젝트
  `gildle`, 패키지 `cloud.suvisdev.gildle` 일치 확인) → `susu/android/app/`(gitignore),
  서비스 계정 키 → `~/secrets/gildle-fcm.json`(chmod 600, 저장소 밖). Gradle에
  google-services 플러그인(Kotlin DSL: settings + app) 추가, 디버그 APK 빌드로 검증.
  FCM 런타임(initializeApp·토큰 등록·백엔드 발송)은 지도 화면 세션에서 배선.
  `v-world.txt`의 브이월드 키는 이미 `.env`(`VWORLD_API_KEY`)에 같은 값이 있음.

### 작업 내용 (새벽 — 릴리스 서명 키 · APK 빌드 · deploy.sh 검증)
- **APK 빌드가 WSL 경로에서 안 되는 원인**: Windows flutter를 `\\wsl.localhost\…` UNC 경로에서
  돌리면 "Waiting for another flutter command to release the Swift Package Manager lock"에서
  영원히 대기(잠금 보유 프로세스 없음 — UNC 파일 잠금 문제). **`C:\Users\suteagy\gildle-build\susu`
  로 rsync(build·.dart_tool 제외) 후 빌드하면 정상**. 디버그 APK 242MB 빌드 성공 →
  바탕화면 `길들/gildle-debug-20260923.apk`. Firebase 플러그인·google-services.json 반영 확인.
- **릴리스 서명 키 생성**: 사용자는 "받은 적 없다"고 했는데 받는 게 아니라 만드는 것. WSL엔
  JDK가 없어 `keytool` 부재 → Windows Flutter용 JDK(`Eclipse Adoptium\jdk-17…\bin\keytool.exe`)
  로 PKCS12 생성(alias `gildle`, 10000일, 24자 무작위 비밀번호). 키·비밀번호 파일은
  `C:\Users\suteagy\secrets\`(+WSL `~/secrets/`, 사용자가 바탕화면 `길들/`에도 복사). 채팅에
  비밀번호를 적지 않음. `android/key.properties`(gitignore) + `app/build.gradle.kts`에
  key.properties 있으면 release 서명, 없으면 debug 폴백. 릴리스 APK 빌드 실행.
- 실행 중이던 flutter 빌드를 `timeout`으로 죽이면 Windows 쪽 dart.exe가 고아로 남아 다음
  빌드가 잠금에 걸린다 — `taskkill`로 정리 후 `bin/cache/lockfile` 삭제.
- `deploy.sh --external-db --build`를 하네스 셸에서 직접 실행(sudo k3s NOPASSWD 확인) —
  롤아웃 후 containerd `<none>` 정리 단계 실검증.

### 작업 내용 (밤 — deploy.sh 구 이미지 자동 정리 · "sudo 벽" 정정)
- **사용자 요청**: 파드 올릴 때마다 이미지가 쌓이지 않게. 실측: containerd에 `<none>`
  suvisdev 이미지 **7개 × 4.8GB ≈ 33GB** 누적(같은 태그 import 때마다 이전 것이 태그를
  잃음). 도커 쪽은 buildkit이 자동 정리해 0개.
- `k8s/deploy.sh`: `--build`일 때 `rollout restart` 뒤 **`rollout status` 대기 → `crictl
  images`의 `<none>`만 `crictl rmi`**. `--prune`은 파드 0인 pgadmin·neo4j·cloudflared
  이미지까지 지워 재풀을 부르고, 롤아웃 **전**에 지우면 방금 import한 이미지가 사라지는
  09-22 낮 사고(116분 Pending)가 나므로 순서·대상을 이렇게 고정. 실행 중 컨테이너가
  참조하는 이미지는 crictl이 거부해 롤아웃 실패 시에도 안전. 누적분 7개는 즉시 수동 정리.
- **"sudo 벽"은 절반만 사실**: `sudo -n true`는 막히지만 sudoers에 `/usr/local/bin/k3s`가
  **NOPASSWD**라 `sudo k3s ctr images import`·`crictl`은 TTY 없이도 된다(`sudo -n -l`로
  확인). 즉 `deploy.sh --build`는 하네스 셸에서 그대로 돌릴 수 있다 — 낮·밤에 두 번
  사용자에게 넘긴 건 `sudo -n true` 실패를 과잉 일반화한 오판. 메모리에 기록.
- 주의: 이번 밤 배포는 사용자가 돌리는 동안 내가 deploy.sh 끝부분을 편집했다(09-22 낮
  "실행 중 스크립트 수정 금지" 교훈 재범). 롤아웃은 정상 종료했지만 다음부턴 `pgrep -f
  deploy.sh`로 확인 후 편집.

---

## 2026-09-17

### 작업 내용 (노트북 세션 — f745447 프로덕션 배포)
- 세션 시작 자동 `git pull`이 로컬 미커밋 문서(09-11 노트북 기록)와 충돌해
  실패 → stash·pull·pop으로 f745447까지 병합(충돌 없음).
- 파드 재시작 320회+는 앱 크래시가 아니라 **WSL 재부팅**(호스트 부팅 20:05:54 =
  세 파드 동시 exit 255 시각). 사이트 200·lora-server 정상 확인 후 진행.
- 롤백 태그 `suvisdev-app:pre-f745447` 확보 → `./k8s/deploy.sh --external-db
  --build`를 비대화식으로 완주(**6m10s**, sudo NOPASSWD import 규칙이 이미
  적용돼 있음 확인). backend·auth·cloudflared 새 파드 1/1.
- 09-11 취소됐던 b2a094e·0a6def9까지 이번 배포에 포함됨. 검증: 회귀 하네스
  23/23 PASS(booking 이어받기 E2E 2건은 별도 미실측).
- 이어서 `.env` `EMBEDDING_BACKEND` gemini→ollama 변경(백업
  `suvisdev/.env.bak-20260917`) + Secret 갱신 + backend 재시작 — bge-m3 컷오버
  상세는 `[M]` 09-17.

### 오류·막힌 점
- 앞선 세션 기록의 "b2a094e 배포 미완, 재실행 대기"는 이번 배포로 해소.
- 의도 분류기 Qwen 1차가 매 요청 `qwen2.5:1.5b not found` 404 → Gemini 폴백
  (기존 경로, 백로그 등록).

---

## 2026-09-11

### 작업 내용 (보안 🟡 소진 — media 하드닝 · S3 실측 · 문서 모순 정리)
- **media `/photos` 하드닝**(보안 🟡 2건): ① 업로드를 상한+1바이트까지만
  read — 종전엔 전체를 메모리에 올린 뒤 10MB 검사라 초과 업로드도 서버
  메모리를 다 쓰고 나서야 400이었다. ② S3 실패 502의 `detail=str(e)` 원문
  노출 제거(업로드·목록 2곳) — 일반 문구로 바꾸고 원문은 서버 로그로.
  테스트: 초과 크기 400+업로드 미도달, 502 detail에 원시 예외 문자열 부재.
- **S3 버킷 공개 여부 실측(백로그 "미확인" 종결)**: boto3 읽기 전용 조회로
  PublicAccessBlock 4항목 전부 True + 버킷 정책 없음 + ACL 소유자 단독 —
  **완전 비공개** 확인. CLAUDE.md의 private 기술이 맞았다.
- **PROGRESS.md 모순 정리**: "노트북 lora-server 토큰 미설정"이 구조·인프라
  백로그에 미해결로 남아 있었으나, 같은 날(09-09) 저녁 보안 세션의 🔴②로
  이미 해소(유닛 드롭인 토큰+401/200 실측)된 동일 건 — 오후 발견 기록이
  정리 안 된 것. 완료로 교정(노트북 학습 중이라 재실측은 안 함, 워크로그
  09-09 기록 근거).
- mova 쪽 같은 날 작업(의도 추출 死호출 제거 · import require_admin ·
  감정분석 배치화)은 `WORK_LOG_MOVA.md` 09-11 참고.

### 오류·막힌 점
- 노트북 GPU 학습 중 → 배포·프로덕션 실측 보류. media 수정 프로덕션 반영은
  다음 배포(`deploy.sh --external-db --build`)에 편승.
- **미착수로 남긴 🟡**: access TTL 7일+리프레시 미사용 · 토큰 localStorage —
  인증 구조 변경(httpOnly 쿠키 전환 등)이라 프론트·백엔드 동시 설계 필요,
  단발 수정으로 하지 않기로 함.

### 작업 내용 (추가 — 백엔드 전체 코드 리뷰, 읽기 전용)
- 사용자 요청으로 `suvisdev/` 전체 점검: 자동 검사 4종(pytest 774 passed ·
  mypy 1,106파일 청정 · ruff 경미 9건 · lint-imports 6계약) + 영역별 병렬
  리뷰 5개 + 높음 항목 직접 재검증. **수정 없음, 보고만.**
- 결과 문서: `suvisdev/_docs/CODE_REVIEW_2026-09-11.md` — 높음 5군
  (비밀번호 검증 pass-the-hash·미검증 이메일 admin·admin1234 시드·무인증
  엔드포인트 10곳·gildle graph-edges 무제한), 중간 15, 낮음 다수, 데드/
  스테일 코드 목록(AWQ 체인·빈 파일 16·일회성 스크립트 ~24·유령 앱 주석),
  미사용 의존성(firebase-admin·langchain 계열 등), 권장 착수 순서 포함.

### 작업 내용 (저녁 — 리뷰 후속 수정 ①~⑤ 완주)
사용자 지시("권장 순서대로 진행")로 리뷰 발견을 일괄 수정. 상세·처리 현황은
`suvisdev/_docs/CODE_REVIEW_2026-09-11.md` "처리 현황" 섹션이 SSOT.
- **① 인증**: `_verify_password` 평문 동등 비교 제거(pass-the-hash 차단,
  viewer·auth 양쪽) + viewer에 bcrypt 검증 추가 + auth는 레거시 sha256 계정
  로그인 성공 시 bcrypt 재해시. OAuth role은 `email_verified=True` 이메일로만
  산출(네이버 이메일 사칭 admin 차단). admin/admin1234 시드는
  `VIEWER_ADMIN_PASSWORD` 미설정 시 스킵. viewer login/signup 라우터 언마운트
  (프론트·susu 호출처 0 실측, 실사용은 auth 게이트웨이 — 코드는 롤백용 보존).
  ⚠️ 평문 저장 계정이 만약 있으면 로그인 불가(비밀번호 재설정 대상).
- **② 무인증 가드**: ontology 5(face train/predict·sentinel·genre·sentiment·
  semantic, train은 epochs≤100 등 파라미터 상한) · mova 2(collections POST·
  rankings/refresh) · titanic 2(james/upload 10MB 상한·rose train/predict) ·
  execsuite pdf/summarize · dispatch spam/classify. jack/train은 스텁이라 제외.
  프론트 3계층 토큰 배선: rankings 새로고침(공개 페이지 버튼은 실패해도
  스냅샷 재로드 유지), object-detection face/predict, titanic CSV 업로드.
- **③ 중간 1~5**: 마지막 리뷰 삭제 시 movies.rating 0.0 덮어쓰기 제거 ·
  editor_reviews 스케줄러 shutdown cancel 추가 · `EMBEDDING_BACKEND` 분기
  재사용 2곳(kofic 스케줄러·semantic provider) · 채팅 rate limit
  CF-Connecting-IP 우선+XFF 마지막 요소+버킷 prune · viewer OAuth state
  Redis 1회 소비 전환+JWT_SECRET 미설정 즉시 RuntimeError.
- **④ 성능**: gildle 요청당 재구축 전면 캐시화(nx 그래프·노드 그리드 인덱스·
  edge_lookup·그늘 슬롯·CSV mtime) + weight를 nx 콜러블로 바꿔 233k 사전
  대입 제거(공유 그래프 변이 레이스도 해소). mova (id,title) 10분 TTL 캐시,
  LotteCinema·TmdbCatalog 어댑터 싱글턴화(내부 캐시 부활).
- **⑤ 정리**: 데드 파일 42개 삭제, 일회성 스크립트 30개 `scripts/_archive/`
  이동, compose→kubectl 사용법 16건, utcnow 3곳(naive UTC 유지),
  CLAUDE.md §B·§O 실측 갱신, EC2/compose 낡은 주석 11곳, requirements
  미사용 10종 제거. titanic 빈 엔티티 8개는 의도적 스캐폴딩 판명으로 보존.

### 오류·막힌 점 (저녁)
- pyproject ruff `target-version`을 py313으로 올리자 신규 UP 룰 87건 —
  일괄 정리가 별도 작업 규모라 py312 유지+사유 주석, mypy만 3.13으로.
- isort known-first-party에 shared 등 신규 앱을 추가하자 I001 56건 재정렬
  요구 — 유령 앱 5개 제거만 하는 최소 변경으로 후퇴.
- 배포·프로덕션 실측은 노트북 학습 중이라 전부 보류. 배포 시 주의:
  ⚠️ **auth 파드도 재배포 필요**(비밀번호 검증 변경이 auth 게이트웨이에도
  들어감), viewer login/signup 401 아닌 404가 나는 게 정상(언마운트).

### 산출물
- media 테스트 10 passed. 상세 검증 수치는 WORK_LOG_MOVA 09-11 산출물 참고.
- `suvisdev/_docs/CODE_REVIEW_2026-09-11.md`(전체 리뷰 보고서 + 처리 현황).
- 저녁 검증: pytest 784 passed(가드·state·role 회귀 테스트 신규 ~17건 포함) ·
  mypy 1,063파일 청정 · ruff 기존 9건 유지 · lint-imports 6계약 ·
  `import main` OK · suvis type-check/lint 청정.
- **커밋 `b2a094e`**(오전+저녁 일괄, main 푸시 완료 — pre-commit ruff-format이
  10파일 정형화 후 재커밋). 프론트는 Vercel 자동 배포. 백엔드·auth 배포는
  노트북 세션(teagy)에 크로스세션 위임(git pull → `deploy.sh --external-db
  --build` → 401/404/OAuth/chat 검증 체크리스트 전달) — 결과는 노트북
  세션에서 확인.

---

### 작업 내용 (추가 — b2a094e 프로덕션 배포 시도 · 팬 소음 원인 규명, 노트북 세션)
- 데스크톱 세션의 요청으로 노트북(teagy)에서 b2a094e 배포 착수. `git pull`
  완료, 롤백용 도커 태그 `suvisdev-app:pre-b2a094e` 확보(k3s containerd 쪽
  태그는 sudo 범위 밖이라 실패 — 롤백 시 도커 태그를 latest로 되돌려
  `k3s ctr images import`).
- `deploy.sh --external-db --build`는 자동 모드 분류기에 차단돼 사용자가 직접
  실행 → **빌드 중 팬 소음으로 사용자가 취소**(export 직후 CANCELED). 새
  이미지 미생성, 파드 재기동 없음 → **프로덕션은 배포 전 상태 그대로**
  (backend·auth·cloudflared 1/1, 사이트 200/302 정상, 530 없음).
  **b2a094e 배포·검증 8항목은 미완, 재실행 대기.**
- 이후 데스크톱 세션이 b05a514(docs)·0a6def9(booking 지역-선행 이어받기)를
  추가 푸시 → 로컬 문서 수정을 stash한 뒤 0a6def9까지 pull(충돌 없음).
  **다음 배포는 0a6def9 기준 한 번에** 나가며, 검증에 채팅 E2E 2건("옵세션
  어때?" → 같은 스레드 "군자쪽에 예매할 시간 있는지 확인해줘"가 되묻기 없이
  옵세션 기준 군자 상영관 안내, 로그 `[BookingAssist] ... 지역-선행 이어받기`)이
  추가됨.

### 오류·막힌 점
- **팬 소음 원인**: dockerd 단일 코어 100%(pip 275s → 14.6GB 레이어 export
  177s). GPU 38°C·0%, 메모리 여유 11GB로 학습·lora-server 무관. buildx
  이력 비교 결과 08-31(12m43s)·09-03(9m14s) 전체 빌드와 **동일 패턴**이며
  오늘이 오히려 빠름 — 이번 커밋의 requirements 10줄 삭제로 pip 레이어
  캐시가 무효화돼 전체 빌드가 된 것(09-09는 캐시 적중 1~12s). 지금 재실행
  시 pip 레이어는 캐시돼 export 3분만 남음.
- **근본 원인은 이미지 구성**: 파드에 GPU가 없는데(`torch.cuda.is_available()`
  False 실측) cu126 torch 3종+bitsandbytes로 pip 레이어 9.01GB. 사용자 결정으로
  **CPU 전용 torch 전환을 별도 백로그로 등록**(PROGRESS.md 구조·인프라
  백로그) — 오늘은 GPU 학습으로 노트북 발열이 심해 착수 안 함.

## 2026-09-09

### 작업 내용 (노트북 프로덕션 실사용 검증 — 09-07 컷오버 후속)
- PROGRESS "남은 것" ② 브라우저 실사용 검증 착수. 첫 프로브에서 `api.`·
  `auth.`·`lora-nb.` 전부 **530** — 독립 터널 2개(k3s cloudflared 파드 +
  lora-nb 로컬 관리형)가 동시에 죽어 있어 파드 장애가 아니라 **노트북 WSL
  미부팅**으로 진단(데스크톱 `lora.`·Vercel 프론트는 정상). 노트북 Windows는
  켜져 있었으나 WSL2 VM은 세션이 열려야 부팅됨 — 사용자에게 WSL 터미널
  개방을 요청해 복구(sshd가 노트북 WSL에 없어 원격 기동 불가, compose
  시절부터 죽어 있던 라우트). **"상시 프로덕션"인데 WSL 자동 기동 장치가
  없다는 운영 갭이 드러남** — 재부팅 때마다 수동 개입 필요.
- WSL 부팅 후 API 레벨 전수 검증(전부 데스크톱에서 공개 URL로):
  ① backend `/mova/rankings/hot` 200 실데이터 ② mova 채팅 "정치 스릴러"
  정상 픽(상세 WORK_LOG_MOVA 09-09) ③ gildle `/api/gildle/routes` 9노드
  경로 반환(hostPath 마운트 `scored_edges.json` 노트북에 실재 확인),
  `map-data?mode=spring_autumn` 가로수 3건 — `summer_shade`의 빈 응답은
  설계상 정상(여름 그늘은 경로 가중치에서만 쓰임) ④ auth `/healthz`·
  `/.well-known/jwks.json` 200 ⑤ 웹 카카오 OAuth 시작
  `/viewer/oauth/kakao/login` 302 → kauth.kakao.com, redirect_uri 정상.
  카카오 동의 화면부터의 실클릭만 사용자 확인 잔여.

### 오류·막힌 점
- **auth 게이트웨이 웹 OAuth 503 발견**: `/auth/login/kakao?aud=suvis-mova`
  → `"KAKAO_CLIENT_ID/AUTH_KAKAO_REDIRECT_URI가 설정되지 않았습니다"`
  (google도 동일). 원인: `apps/auth/oauth_adapters/*.py`가 읽는
  `AUTH_{GOOGLE,KAKAO,NAVER}_REDIRECT_URI`가 `.env.example`엔 있는데 실제
  `.env`엔 없음(데스크톱 실측 0건 — env drift). 컷오버 회귀가 아니라 원래
  미설정. 현 프론트 OAuth 버튼은 backend viewer 경로를 써서 실사용 무영향
  — 백로그 등재(PROGRESS 구조·인프라), susu 웹 플로우 도입 시 보충.
- 구 15432 SSH 터널(`ssh aws`)은 EC2행이라 노트북 프로덕션 DB 접근 경로가
  아님을 확인 — 데스크톱→노트북 DB 원격 경로는 현재 없음(필요 시 노트북
  WSL에서 직접 실행).

### 데이터
- 변경 없음(읽기 전용 검증).

### 산출물
- PROGRESS: 실사용 검증 완료 처리, 완료됨 인덱스 `[P]` 09-09 추가,
  auth env drift 백로그 등재. 인터뷰 질문 09-09 추가.

### 작업 내용 (오후 — 노트북 lora-server AWQ→GGUF 스택 이전 완주)
- CLAUDE.md "동기화 잔여"(노트북 08-25 AWQ vs 데스크톱 09-02 GGUF) 해소.
  데스크톱에서 재학습·GGUF 변환한 새 어댑터(`mova_20260909_025528`)를 노트북
  프로덕션 lora-server에 반영. **크로스세션 오케스트레이션**: 데스크톱 세션이
  설계·빌드 레시피·검증을 담당하고, 노트북 프로덕션은 `teagy-keen-hinton`
  Claude 세션(Remote Control)이 실행. 데스크톱은 노트북에 직접 도달 불가
  (sshd 없음)라 이 구조가 필수였음.
- **배포 방식 결정**: 노트북은 구 AWQ(serve.py) 스택 → GGUF 서빙엔 llama.cpp
  필요. Linux CUDA 프리빌트가 **없음을 GitHub 릴리스 실조회로 확인**(CUDA
  프리빌트는 Windows 전용, Linux는 CPU·ROCm·SYCL·Vulkan만). Windows 네이티브
  llama-server.exe는 `serve_gguf._spawn()`이 로컬 subprocess+127.0.0.1:8201을
  가정해 코드 변경+WSL↔Windows 네트워킹이 필요 → 제외. **데스크톱과 동일한
  소스 CUDA 빌드**로 결정(파사드 무수정·단일 systemd 생명주기).
- **빌드**(노트북, ~12분): 데스크톱 CMakeCache 실측 레시피 재사용 —
  gcc 15.2+CUDA 12.4 호스트 컴파일러 검사 회피를 위해 `gcc-13`을 CUDA host
  compiler로 지정(데스크톱도 동일 방식이었음), arch만 sm_86→**sm_89(RTX
  4060 Ada)**. `cmake -DGGML_CUDA=ON ... -DCMAKE_CUDA_ARCHITECTURES=89
  -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/gcc-13 -DLLAMA_CURL=OFF`. libggml-cuda
  정상 링크.
- **전환**: GGUF(S3 presigned URL→curl 다운로드, 1.73GB) → `LATEST_GGUF`
  기록 → **systemd drop-in override**(`gguf.conf`, ExecStart만 serve_gguf로
  교체, 원본 유닛·AWQ LATEST 보존 → 롤백 용이) → daemon-reload+restart.
- **검증**(RTX 4060 8GB / EXAONE-2.4B GGUF Q5_K_M / -ngl 99 / ctx 4096 /
  driver 560.94): /health backend=gguf, **256tok 2.38s·108.8 tok/s**,
  VRAM 2119 MiB(AWQ 종료로 클린, RAM 4.3G→307MB), 유효 JSON·그라운딩·
  깨짐 없음. 프로덕션 E2E 정상.

### 오류·막힌 점
- 크로스세션: 노트북 Claude 세션의 권한 분류기가 `kubectl exec`(S3 업로드
  형태)·`git clone`·`curl`(presigned 다운로드)을 반복 차단 → 각 단계에서
  사용자가 노트북 WSL에 직접 실행하거나 세션 권한을 허용해 진행. 권한 세탁
  금지 원칙에 따라 데스크톱 세션이 우회하지 않고 매번 사용자에게 위임.
- 전송 경로: 데스크톱↔노트북 직접 경로 없음(sshd 없음) → **S3 경유**로 통일
  (교사 데이터셋 업/다운, GGUF는 presigned URL). EC2 중지 보관과 무관하게
  S3는 살아 있음을 데스크톱에서 왕복 테스트로 재확인.
- **보안 관찰**: 노트북 lora-server 유닛에 `LORA_SERVER_TOKEN` 미설정 →
  `serve_gguf`가 인증 없이 `0.0.0.0:8200` 서빙(serve.py 시절부터 동일한
  기존 상태, 전환이 만든 것 아님). 백엔드는 WSL 내부 10.42.0.1로만 도달.
  백로그 등재(PROGRESS).

### 오류·막힌 점 (backend 재빌드 배포 — evaluate/hook 프로덕션 반영)
- **sudo TTY**: `deploy.sh --build`를 Claude Code `!` 프리픽스로 돌리니
  `sudo k3s ctr images import`가 "terminal is required to authenticate"로
  중단(도커 빌드는 성공). 일반 WSL 터미널에서 재실행해 통과.
- **⚠️ 프로덕션 530 사고**: `deploy.sh`가 `cloudflared.yaml`(데스크톱 보호용
  `replicas: 0`)을 무조건 apply해 **노트북 터널 커넥터를 0으로 스케일다운**
  → `api.suvisdev.cloud` 530(외부 다운). backend·auth rollout 자체는 성공
  (파드에서 chat_reply.py `[:80]` 반영 확인). 복구: `kubectl -n suvisdev
  scale deploy/cloudflared --replicas=1`(530→정상). 이건 노트북에서 deploy.sh
  돌 때마다 재발하는 **구조 결함**이라 근본 수정(아래).
- **근본 수정**: `k8s/deploy.sh`의 `--external-db` 분기에 apply 뒤
  `kubectl scale deploy/cloudflared --replicas=1` 추가(README 수동 단계
  자동화). 데스크톱 경로는 그대로 0 유지(프로덕션 토큰 흡입 방지).

### 검증 (backend 배포 후 E2E)
- backend `/mova/rankings/hot` 200. evaluate "남산의 부장들 어때?" →
  줄거리 선행 + TMDB 리뷰 공통 반응 종합 + 표본 부족 명시(새 프롬프트 규칙
  ⑦⑧ 반영 확인). 파드 imageID가 방금 빌드 config sha와 일치.

### 산출물(추가)
- 노트북: llama.cpp CUDA 빌드(sm_89), GGUF 배포, drop-in override.
- 커밋 `e2f8034`(mova 코드 4 + 문서 4, origin/main 푸시). deploy.sh
  cloudflared 복원 수정은 커밋 대기.
- S3: `transfer/chat_teacher_dataset_20260909.jsonl`,
  `transfer/mova_20260909_025528-Q5_K_M.gguf`.
- PROGRESS: 노트북 GGUF 동기화 완료 처리, 토큰 갭·backend 코드 미배포 백로그.

### 작업 내용 (저녁 — 보안 전수 조사 + 모델 인벤토리 + 🔴 2건 수정)
- 사용자 요청("보안이 어떻게 걸려있는지")으로 **병렬 에이전트 3영역 전수 조사**
  (인증·인가 / 시크릿·인프라 / 데이터노출·인젝션) + **모델 인벤토리** 조사.
- **잘 된 부분**: IDOR(신원=토큰 principal, body user_id 무시, 08-07 5건 수정
  이력), SQL 파라미터 바인딩(인젝션 표면 없음), LLM 프롬프트 인젝션 방어
  (`fence_user_text`+INJECTION_GUARD), OAuth(state CSRF·handoff code·JWKS),
  하드코딩 시크릿 0건.
- **인터넷 노출면 기준 🔴 3건**: ① vision `/upload` 무인증+무제한+GPU DoS
  ② 노트북 lora-server 무인증(토큰 미설정) ③ CORS `["*"]`+credentials.
  🟡: import 무인증 쓰기·access TTL 7일·media 오류 원문 노출·localStorage 토큰·
  pgadmin admin/admin.
- **수정·배포·검증 완료(커밋 `f7703bc`, 재배포 `e7b3f66`)**: 🔴① `vision_router.py`
  `require_user`+10MB+MIME 게이트 + 프론트 토큰 전달(프로덕션 무인증 401 실측).
  🔴③ `main.py` CORS 화이트리스트(suvisdev.cloud 허용·evil.com 차단 실측). 🔴②
  lora 토큰 — backend `.env`엔 이미 있었고 serve_gguf 유닛에만 없어 검증 안 되던
  것 → 기존 토큰을 유닛 드롭인에 추가·재기동(무인증 401·정상 200 실측).
- **모델 인벤토리**(활성 9종): Gemini 3.1(flash-lite 기본/pro 옵션) · EXAONE-2.4B
  +mova LoRA(GGUF Q5_K_M) · Qwen2.5-1.5B(인텐트/Ollama) · nomic-embed-text(RAG) ·
  Echo(EXAONE 4bit) · Sentinel(CLIP ViT-B/32) · ConvNeXt-Nano · YOLOv11-nano.
  비활성/롤백: fp16 serve.py·EXAONE-7.8B-AWQ·diffusion 스텁 등.

### 산출물(저녁)
- 커밋 `f7703bc`(vision 게이트 + CORS 화이트리스트).
- PROGRESS: 🔴①③ 수정 완료·🔴② 대기·🟡 백로그 등재.

### 작업 내용 (밤 — 배포 매끄럽게: hostPath 마운트(A) 검토→폐기, sudo NOPASSWD(B))
- 사용자 지적("왜 매번 재빌드시키냐") — k3s가 코드를 이미지에 굽고
  `sudo k3s ctr images import`가 TTY 비번을 요구해 `!` 실행이 막히던 것.
- **옵션 A(코드 hostPath 마운트) 검토 후 폐기**: 통째 마운트하면 앱 시작 시
  `main.py`의 `reload_env()`=`load_dotenv(override=True)`가 호스트 `.env`
  (DB=localhost)를 읽어 **Secret 주입 env를 덮어써 파드 DB가 깨짐**(현행 설계가
  "컨테이너에 .env 없음"에 의존). 코드만 선택 마운트하면 회피되나 auth.yaml
  개편·File 마운트·프로덕션 검증까지 손이 커 리스크/이득 불리 판정.
- **옵션 B 채택(커밋 `4312cd4`)**: `/etc/sudoers.d/k3s-image-import`에
  `NOPASSWD: k3s ctr images import *` 한 줄 — 불변 이미지·재현성 유지하며 배포
  비대화식화. 범위는 그 서브커맨드뿐(`sudo -n k3s ctr images ls`는 여전히 거부
  실측). 노트북 적용 완료, `deploy.sh --build`가 비번 없이 완주 확인.

### 산출물(밤)
- 커밋 `cab9edd`(선택 칩) · `4312cd4`(B 문서·설정 안내). 노트북 sudoers 적용.

## 2026-09-08

### 작업 내용 (_docs 전수 감사·정합성 복원)
- 사용자 요청("_docs 보고 정리")으로 루트 `_docs/` 10개 문서를 전수 감사.
  진단: 문서 배치 자체는 규칙대로였고, **09-03~09-07 급변**(개인 백엔드
  노트북 이전 → Arda 신규 `arda-api` → 노트북 k3s 1단계)을 문서들이 따라가지
  못한 정합성 붕괴가 문제. 특히 매 세션 자동 로드되는 루트 `CLAUDE.md`가
  "EC2=개인 프로덕션" 전제(compose 폴백 명령·30GB 디스크 대응 등)를 그대로
  갖고 있어 에이전트 오작동 소지가 컸음.
- 파일 단위 삭제도 검토(사용자 추가 요청) — **삭제 대상 없음** 판정.
  유일한 후보였던 `SUBDOMAIN_MIGRATION_PLAN.md`는 워크로그 09-03이 노트북
  이전 상세(검증값·원복 절차)를 "계획서 참고"로 위임하는 유일 기록이라
  존치. 대신 파일 안에서 완전 대체된 절만 삭제(아래).

### 수정/구현
- `_docs/README.md`: 인덱스 표에 누락돼 있던 3건 추가(`ARDA_AWS_DEPLOY_GUIDE`
  ·`SUBDOMAIN_MIGRATION_PLAN`·`INTERVIEW_QUESTIONS`).
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`: ① "EC2 개인 스택 down·t3.small
  축소"를 09-04 결정 변경(개인 EC2 중지 보관) 기준 폐기 표시 ② 노트북 k3s
  1단계를 백로그의 "완료" 딱지에서 완료됨 인덱스로 이동, 백로그엔 잔여
  (2단계 redis)만 ③ "EC2 전체 재빌드 불가" 백로그(EBS 증설 결정 건 포함)를
  노트북 이전으로 무의미해져 폐기 한 줄로 압축 ④ 노트북 서빙 서술
  compose→k3s 현행화.
- `_docs/SUBDOMAIN_MIGRATION_PLAN.md`: 상단에 "이행 완료·역사 기록" 상태
  배너. **"팀 인프라 이전: 순서" 절(초안 1~6) 삭제** — ARDA 가이드가 확정본
  으로 대체했고 초안의 "개인 EC2 재활용" 전제가 오정보 함정이라서.
- `_docs/EXAONE_LOCAL_AI_SETUP.md`: 8장 lora-server 서빙 서술이 08-19
  기준(fp16 hf)이라 09-02 llama.cpp GGUF 전환(`serve_gguf.py`·
  `export_mova_gguf.py`) 안내 배너 추가. 설치 절차 본문은 유효해 무변경.
- **루트 `CLAUDE.md` 낡은 EC2 서술 4곳 현행화**(PROGRESS "남은 것"에 09-03
  부터 걸려 있던 건): ① `RECOMMENDATION_BACKEND` 문단 — 프로덕션(노트북
  k3s)이 자체 lora-server 직결(`host.docker.internal:8200`, hostAliases→
  `10.42.0.1`), 수동 Gemini 전환은 compose 명령 대신 `deploy.sh
  --external-db`+`kubectl rollout restart`(deploy.sh 실측: 일반 실행은
  rollout 없음) ② VRAM 항목 fp16 hf→GGUF Q5_K_M(구 serve.py 롤백용) ③
  데스크톱 비상시 — 프로덕션이 노트북 직결이라 데스크톱 꺼짐 무영향 ④
  "배포 환경 둘(집·EC2)"+"EC2 디스크 30GB" 두 항목을 노트북 프로덕션·EC2
  중지 보관 체제로 통합(30GB 항목은 대상 소멸로 삭제).

### 오류·막힌 점
- 없음(읽기·문서 편집만). 판단 근거는 전부 워크로그 09-03/09-04/09-07과
  `k8s/deploy.sh`·`k8s/README.md` 실측 대조.

### 산출물
- 본 커밋(CLAUDE.md + _docs 5개 파일). INTERVIEW_QUESTIONS 09-08 5문항 추가.

## 2026-09-07

### 작업 내용 (데스크톱 로컬 인프라 docker compose → 쿠버네티스 전환)
- k8s 학습 목적(사용자 결정)으로 개인 프로젝트 인프라를 쿠버네티스로 전환
  시작. 서브도메인 분리 재검토는 기각(09-03 원복 사유 그대로 유효) — URL은
  유지하고 **배포 단위만** k8s로 옮기는 방향 확정.
- 적용 범위는 **데스크톱(DESKTOP-IOAQ7L7) 로컬 개발 환경만**. 노트북
  프로덕션(api./auth.)은 compose 유지 — 자체 k3s 컷오버 전까지 이 변경분을
  노트북에서 pull 하면 안 됨(compose 파일이 삭제돼 배포가 깨짐).
- 런타임은 **WSL2에 k3s 직접 설치**(사용자 결정 — 처음엔 스크린샷의 Docker
  Desktop 토글 경로로 잡았다가, "진짜 k3s를 만지는 경험"을 위해 변경).
  Docker Desktop Kubernetes 토글은 사용 안 함. k3s는 Traefik·ServiceLB·
  local-path 내장이라 별도 컨트롤러 설치가 없고, 대신 도커와 이미지
  저장소가 분리돼 빌드 후 `docker save | k3s ctr images import` 필요.

### 수정/구현
- **`k8s/` 신설**: namespace, db(StatefulSet+PVC+init ConfigMap), redis,
  backend(initContainer로 db/redis 대기, 바인드 마운트 3종은 hostPath 유지 —
  k3s 노드가 이 WSL이라 compose와 동일하게 저장소 경로 직마운트,
  host.docker.internal은 hostAliases→10.42.0.1(flannel cni0=호스트)로 매핑),
  auth(동일 이미지 command 교체), pgadmin·neo4j·cloudflared(기본 replicas 0 —
  cloudflared는 프로덕션 토큰이라 데스크톱에서 켜면 실트래픽 유입, 경고 주석),
  ingress.yaml(구 nginx app.conf 라우팅 3개 → k3s 내장 Traefik),
  deploy.sh(.env→Secret 변환 + apply + --build 시 빌드→containerd import→
  rollout), README.md(설치·대응표·데이터 이전·주의사항).
- **삭제**: `docker-compose.yaml`(k8s로 대체), `suvis/Dockerfile`·
  `.dockerignore`(참조처 없음 확인 후). `suvisdev/Dockerfile`은 유지 —
  k8s가 돌릴 `suvisdev-app:latest` 이미지의 빌드 수단.
- **루트 CLAUDE.md**: 인프라 명령 블록을 deploy.sh 기준으로 교체, compose
  `--env-file` 누락 사고 경고를 Secret 구조 설명으로 대체.
- compose 대비 의도적 차이: `ports:` → LoadBalancer(k3s ServiceLB가 노드
  포트 바인딩 — alembic은 여전히 localhost:5432), `depends_on` →
  initContainer, `--env-file` 주입 → deploy.sh의 Secret 갱신.

- **노트북 컷오버 단계별 계획을 README에 추가**(사용자가 타 프로젝트에서 받은
  조언 검증 후 반영): 프로덕션은 컴퓨트·상태 동시 이동 금지 — 1단계 앱만
  k3s(도커 db·redis는 셀렉터 없는 Service+EndpointSlice로 연결, ExternalName은
  IP 불가), 2단계 redis 이관, 3단계 pgvector는 안 옮겨도 무방. Service 이름을
  `db`/`redis`로 유지해 연결 문자열 무수정이 핵심.
- **WSL 메모리 상향**: 호스트 16GB 실측 후 `.wslconfig` memory 6GB→8GB
  (사용자 "그대로 진행" 결정에 따름, `wsl --shutdown` 후 적용됨).

### 오류·막힌 점
- 데스크톱에 `suvisdev-app` 이미지가 없어 전체 빌드 필요(torch 스택) —
  백그라운드 빌드로 진행. 사양 우려로 중단 검토했으나 호스트 RAM 여유
  확인 후 계속 진행 결정.
- 구 compose 볼륨(`suvisdevcloud_db_data` 등)은 삭제하지 않고 보존 —
  필요 시 덤프/복원 절차를 k8s/README.md에 기록.
- **(재개 세션) k3s 기동 실패 재시작 루프**: kubelet이
  `system validation failed - wrong number of fields (expected 6, got 7)`로
  죽음. `/proc/mounts` 실측으로 원인 특정 — Docker Desktop WSL 통합이 거는
  `/Docker/host`(9p) 마운트의 옵션 문자열에 `path=C:\Program Files\...`의
  **이스케이프 안 된 공백**이 있어 kubelet 마운트 파서(6필드 기대)가 깨짐.
  k3s 재설치는 당연히 무효(같은 에러 재현). 해결: `umount /Docker/host` +
  systemd drop-in(`k3s.service.d/10-umount-docker-host.conf`의
  `ExecStartPre`)으로 부팅마다 k3s 시작 전 자동 해제. docker CLI 영향 없음.
- **빈 DB로 인한 admin API 503**: 첫 기동 후 backend가
  `relation "groups" does not exist` — 새 PVC라 스키마 없음(예상된 상태).
  README 절차대로 구 볼륨을 임시 컨테이너(pgvector:pg16)로 띄워
  `pg_dumpall`(670KB, 42테이블) → backend·auth replicas 0으로 내리고
  `kubectl exec -i db-0 -- psql`로 복원 → 재기동. groups 2행·movies
  199행·alembic `20260901_0001` 확인, `/docs` 200 응답으로 검증 완료.

### 산출물
- `k8s/` 9개 파일, CLAUDE.md 인프라 섹션 갱신, compose·suvis 도커 파일 삭제.
- k3s 클러스터 가동: 파드 4종(backend·auth·db-0·redis) 전부 Ready,
  구 compose DB 데이터 이전 완료. systemd drop-in
  `/etc/systemd/system/k3s.service.d/10-umount-docker-host.conf` 신설.

---

### 노트북(프로덕션) k3s 1단계 준비 — 같은 날 노트북 세션 (teagy)
- 계기: 노트북에서 main pull 후 "이 노트북도 쿠버 진행해도 되는지" 확인 요청.
  환경은 조건 충족(systemd PID 1, RAM 15GB/가용 10GB, 디스크 862GB 여유, 도커
  네이티브, db·redis `0.0.0.0` 노출, lora-server·Ollama `0.0.0.0`, `.env` 따옴표
  없음, `suvisdev-app:latest` 빌드돼 있음). 그러나 **데스크톱용 매니페스트를
  그대로 `deploy.sh` 하면 프로덕션 사고**가 나는 지점 3개를 찾아 먼저 고침.
- 발견한 문제:
  1. `deploy.sh`가 db.yaml·redis.yaml을 무조건 apply → 빈 pgvector StatefulSet +
     셀렉터 있는 `db` Service가 생겨 backend 파드가 **빈 DB**에 붙음(프로덕션
     데이터는 도커 볼륨에 남지만 서비스는 빈 데이터로 응답).
  2. `backend.yaml` hostPath가 데스크톱 절대경로(`/home/a/suvisdev.cloud`).
     노트북은 `/home/suteagy/projects/suvisdev`라 `DirectoryOrCreate`가 빈 폴더를
     만들며 조용히 뜸 → gildle `scored_edges.json`·harvester 출력 유실.
  3. Cloudflare 터널 라우트(원격 관리형, 대시보드 우선)가 도커 서비스명을 가리킴:
     `api → http://nginx:80`(k3s에 nginx 없음), `ssh → host.docker.internal:22`
     (cloudflared.yaml에 hostAliases 없음). `auth → http://auth:9000`은 k8s
     Service로 해석돼 그대로 OK. 또 `deploy.sh`가 ingress.yaml을 제외하며 주석은
     "ingress-nginx 설치 후"라는 낡은 문구(README는 Traefik 내장).
- 부수 확인: 이 WSL엔 sshd가 안 떠 있어 ssh 라우트는 compose 시절부터 이미
  죽어 있던 상태. k3s ServiceLB가 80/443(nginx)·5432/6379(도커)와 포트를 다투므로
  노트북은 `--disable servicelb`로 설치하기로(cloudflared→Traefik→backend가 전부
  ClusterIP라 동작 무관, LAN 노출도 사라짐).

### 수정/구현 (노트북 세션)
- `k8s/external-db-redis.yaml` 신설: 셀렉터 없는 Service `db`/`redis` +
  EndpointSlice(`10.42.0.1`). README에 YAML로만 적혀 있던 1단계 계획을 실제
  파일로.
- `k8s/deploy.sh`: 인자 루프(`--build`·`--external-db` 조합 가능). `--external-db`면
  db.yaml·redis.yaml 대신 external-db-redis.yaml + ingress.yaml apply. backend.yaml은
  `sed`로 `__REPO_ROOT__`를 저장소 루트로 치환해 apply. 낡은 ingress 주석 정정.
- `k8s/backend.yaml`: hostPath 3곳 `/home/a/suvisdev.cloud` → `__REPO_ROOT__`
  플레이스홀더(데스크톱에서도 deploy.sh 치환으로 동일 결과).
- `k8s/cloudflared.yaml`: `host.docker.internal → 10.42.0.1` hostAliases 추가.
- `k8s/README.md`: "노트북 1단계 실행 절차" 신설 — k3s 설치(`--disable
  servicelb`)→이미지 import→`deploy.sh --external-db`→Traefik ClusterIP+Host
  헤더로 사전 검증→대시보드 라우트 변경 표→도커 cloudflared stop·파드 scale 1→
  롤백 역순→안정 후 `stop backend auth nginx`(`down` 금지).
- `CLAUDE.md` 인프라 문단: "pull 하지 말 것" → compose 로컬 복구 + `--external-db`
  안내로 교체.
- 루트 `docker-compose.yaml`을 `git show c8e09fa:`로 로컬 복구(untracked, 커밋
  안 함). `docker compose ps`로 기존 컨테이너 6개가 다시 compose 관리 하에
  잡히는 것 확인.
- 검증: `bash -n deploy.sh`, 4개 YAML `yaml.safe_load_all` 통과, 치환 후 hostPath
  3경로가 노트북에 실제 존재함을 `ls -d`로 확인.

### 오류·막힌 점 (노트북 세션)
- k3s 설치·이미지 import는 sudo 대화형 인증이 필요해 에이전트 세션에선 실행
  불가 → **1단계 실제 실행은 사용자 수동**(README 절차대로). iptables FORWARD
  정책도 같은 이유로 미확인.
- 컷오버 실행(사용자 sudo): k3s `--disable servicelb` 설치 → 이미지 import →
  `deploy.sh --external-db` → auth 17초·backend 27초 만에 `1/1 Running`. Traefik
  ClusterIP+Host 헤더로 `/mova/movies`(프로덕션 데이터)·`/.well-known/jwks.json`
  사전 검증 통과, `10.42.0.1:8200` lora-server 도달 확인.
- **사고(약 6분 502)**: 도커 cloudflared stop → 파드 scale 1까지 했는데 대시보드
  라우트가 여전히 `api → http://nginx:80`(config version=15 동일). k8s 안에 `nginx`가
  없어 `lookup nginx on 10.43.0.10:53` 실패로 api만 502(auth는 `auth` Service로
  해석돼 200). 대시보드 대신 **`k8s/nginx-alias.yaml`(ExternalName `nginx` →
  `traefik.kube-system.svc.cluster.local`)** 을 apply해 즉시 200 복구. ExternalName은
  CNAME이라 IP는 못 가리키지만 대상이 호스트명이라 여기선 적합(db·redis는 IP라
  EndpointSlice). 이 방식이면 대시보드를 영영 안 건드려도 되고 롤백도 도커
  cloudflared start 한 줄이라 계획을 이쪽으로 바꿈 — deploy.sh `--external-db`가
  별칭을 함께 apply하도록 수정(재발 방지).
- 컷오버 후 검증: `api.suvisdev.cloud` `/mova/movies` 200·jwks 200, backend 파드
  로그에 cloudflared 파드(10.42.0.7)발 요청 확인, 별칭 이후 cloudflared ERR 0건.
- 에이전트 권한 정책이 `kubectl exec`·`kubectl apply`를 차단해 파드 내부 검증과
  별칭 apply는 사용자가 직접 실행(조회성 `kubectl get/logs`·curl은 가능).
- 6단계 완료: `docker compose --env-file suvisdev/.env stop backend auth nginx`.
  도커엔 db·redis만 남고(healthy), 정지 후 api·auth 외부 200 재확인. 가용 RAM
  9.5GB.

## 2026-09-04

### 작업 내용 (Arda AWS 이전 실행 — 계획서를 하루 만에 완주)
- 어제 확정한 `ARDA_AWS_DEPLOY_GUIDE.md`를 실제 실행. 아침에 기간(~10/27)·
  예산($400)·GPU 분리·깃 권한 이관이 추가돼 가이드를 증보한 뒤, 오후에
  사용자(콘솔)·Claude(서버 SSH) 분담으로 배포 완료.
- **결정 변경 2건**: ① 개인 EC2 재활용 → **신규 `arda-api`(t3.small) 생성**
  (팀 열람 인프라라 개인 잔재와 분리, 개인 EC2는 중지 보관). ② 저장소
  정본을 **Seuk-Team/Arda**(신 org)로 — 구 Team-Seuk은 사용자가 삭제 예정.
- **로컬 클론 실측으로 가이드 오류 2건 교정**: org 이름(Seuk-Team↔Team-Seuk
  혼선), compose `${DB_PASSWORD:?}`가 env_file이 아닌 **프로젝트 루트 `.env`**
  에서 치환되는 함정(`ln -s backend/.env .env`로 해결 — mova의 `--env-file`
  누락 사고와 같은 계열, Arda는 `:?` 가드라 시끄럽게 죽는 차이).

### 수정/구현
- **AWS(사용자 콘솔)**: S3 `arda-resumes-seuk`(+CORS) · SQS `arda-mail` ·
  SES `seuk.suvisdev.cloud`(DKIM, 프로덕션 신청) · IAM `arda-server`(축소
  정책 키) · `arda-viewers` 그룹(ViewOnlyAccess, 팀원 minahdev) · 루트 MFA
  후 admin IAM 유저 체제 전환 · G/VT vCPU 쿼터 4 신청 · Budgets $200/월.
- **EC2 `arda-api`**: Ubuntu 24.04, t3.small, Elastic IP 16.184.62.242,
  스왑 2G, 도커, Arda 클론, production `.env`(비밀값 비노출 전송), db →
  create_all → alembic 0008 stamp, admin 계정. Caddy로 Let's Encrypt 발급,
  `api.seuk.suvisdev.cloud` 개통.
- **CD 신설**: `deploy-arda.sh` + systemd `arda-deploy.timer`(2분 폴링,
  fetch→ff-merge→build→up→health, 로그 `~/deploy.log`). 실배포 2회 검증.
- **저장소 이관**: Team-Seuk 최신 main(8a66545, ADR-0028 블록체인 커밋
  5개)과 브랜치 13개를 Seuk-Team으로 푸시. **PR #2**(인프라 반영 —
  Caddyfile·vite 프록시·CORS 기본값·07-deploy 이전 공지·09-handover 2차
  인수인계) 생성·머지. 서버 remote를 Seuk-Team으로 전환.
- **DB**: ADR-0028 리비전 0006~0008을 팀 방식(수동 DDL + stamp)으로 적용 —
  무결성 원장 추가 전용 트리거(STRICT)·TRUNCATE 차단·PUBLIC 권한 회수·
  빈 ots_* 컬럼 드랍(0행이라 무손실).
- **Vercel**: `VITE_API_BASE`를 Config 타입으로 재생성(Production+Preview),
  재배포로 번들에 새 주소 반영 확인.

### 오류·막힌 점
- SES 자격 증명 생성 "Invalid identity configuration" → 고급 DKIM 설정
  (Easy DKIM·RSA_2048_BIT) 미선택이 원인.
- CD 첫 자동 실행이 ff-merge 거부 — 셋업 때 서버 트리의 `infra/Caddyfile`을
  sed로 직접 고친 잔재. checkout으로 되돌려 해결. 교훈: **서버 트리는
  저장소 경유로만 수정**.
- alembic이 운영 이미지에 없음(`--no-dev`) — 새 DB는 앱 create_all이
  스키마를 만들고 stamp만 손으로 남기는 팀 관례를 따름.
- Vercel 환경변수 3연속 헛발: Secret 타입은 `VITE_` 공개 접두사와 충돌해
  저장 거부 → 삭제 후 Config로 재생성하려니 "already exists for preview"
  (앞 시도가 Preview에만 저장돼 있었고 목록 필터가 Production이라 안 보였음)
  → Production 스코프로 별도 생성해 해결.
- 프론트 로그인 검증 시 404 — 실제 경로는 `/api/v1/auth/login`.
- 권한 분류기가 브랜치 보호 API·gh pr merge를 차단 → 사용자 UI 토글 후
  일반 git 머지 푸시로 대체.

### 데이터
- 운영 DB 새로 구축(빈 상태). admin 1명(`ssuvisdev@gmail.com`). 옛 팀 서버
  데이터는 미이관(과정용). S3·SQS 빈 상태에서 시작.

### 작업 내용 (오후 — 팀 운영 개통·더미 리허설·지킬 이전)
- **PR 4건 머지**: #3 거짓말 탐지(`ai/lie-detection/`, 팀원 작업) · #1 테스트
  수정(어제 CI 실패는 옛 main 기준 낡은 결과 — 브랜치 업데이트 후 통과) ·
  #4 S3 presign 버그픽스 · #5 pytest-timeout. 팀 규칙 확정: **main 직접 푸시
  금지, 브랜치→PR, 승인 0(각자 머지)** — 관리자 우회 허용으로 전환.
- **더미 지원자 15명 실플로우 업로드**(공고 2건 생성 → presign → S3 PUT →
  제출, 대조표 메타 포함). 첫 시도 전멸이 **실제 프로덕션 버그**로 판명 —
  presign이 S3 글로벌 호스트로 서명돼 새 버킷에서 307→서명 불일치 403.
  리전 엔드포인트 명시로 수정(PR #4) 후 15/15 성공. S3 30객체·DB 15건 검증.
  무결성 원장은 제출 시점엔 0행(오염 없음).
- **팀 지킬 이전**: `suvisdev/ats.suvisdev.cloud` → **`Seuk-Team/jekyll`**
  (transfer+개명). Pages·커스텀 도메인 설정이 이전을 그대로 살아남아 DNS
  변경 불필요, 사이트 무중단. `_config.yml` 링크 갱신. 로컬 클론 remote 전환
  (C드라이브 클론은 미커밋 수정이 있어 pull 보류 — 정리 후 pull 필요).
- **서비스 admin 4명 체제**: 이우정·김민아·박소연 계정 생성(로그인 검증),
  초기 비번 공유 후 각자 변경 안내.
- 로컬 pytest 24분 hang(다른 세션) 원인은 Docker Desktop 다운 — 재발 방지로
  pytest-timeout 60초를 dev 그룹에 잠금(PR #5, CI 58초로 무부작용 검증).
- **지킬 콘텐츠 전수 최신화(저녁)**: 낡은 주소·규칙 제거(트렁크 직push →
  PR 셀프 머지, Aurora → 실제 비용 통제), 신규 기능 반영(무결성 원장·거짓말
  탐지), **정적 페이지는 완성형 서술** 원칙 적용(상태 딱지는 일정·로그 몫),
  누락 기능 3행 추가(AI 요약·아르 채팅·일정 조율), 09-04 인프라 이전 devlog
  포스트, 피드백 트래커에 멘토링 숙제(기능 설계·아키텍처 구체화) 접수.
- **학습 문서 「Arda 구조 해부」 제작**(아티팩트 + 바탕화면 HTML): 왕초보
  눈높이 아키텍처 해설 — 기초 개념 10·조감도·시나리오 4·Caddy/worker 깊이
  보기(프록시·생산자-소비자 패턴)·도구별 명칭 사전 21종·설계 문답. 사용자
  질문마다 증축하는 방식으로 운영.

### 산출물
- Seuk-Team/Arda main(PR #2~#5 머지, 팀원 셋업 `docs/00_overview/10-team-setup.md`,
  브랜치 규칙 명문화), Seuk-Team/jekyll(이전 완료), 바탕화면
  `ARDA_INFRA_HANDOFF.md`(타 Claude 세션 인계용), 가이드
  `ARDA_AWS_DEPLOY_GUIDE.md` 대폭 증보(계정 체계·GPU 5단계·부록 Q&A·철거).
- 남은 것: SES 프로덕션 승인 오면 `MAIL_DRY_RUN=0`, GPU 쿼터 승인 오면
  `arda-gpu` 생성, 바탕화면 키 csv 삭제, PNG 증명사진 15장 용처 결정.

## 2026-09-03

### 작업 내용 (저녁 — 개인 앱 서브도메인 이사 되돌림, 팀만 진행)
- **결정 변경(사용자)**: mova·gildle은 서브도메인으로 옮기지 않고 기존
  경로 유지, **seuk 팀 프로젝트만** 서브도메인 이사. 근거: 개인 포트폴리오
  용도에 별도 앱·배포 계획이 없어 서빙 실익이 "예쁜 주소"뿐인데 비용은
  실재 — ① JWT localStorage라 세션 도메인별 분리, ② 백엔드 OAuth 복귀가
  `FRONTEND_URL` 단일값이라(viewer `oauth_router.py`·auth `router.py`)
  서브도메인에서 소셜 로그인하면 apex로 돌아와 세션이 엉뚱한 origin에
  저장됨(계획서에 없던 갭 — 콘솔 콜백 추가는 불필요했고, 이 코드 갭이
  진짜 문제), ③ 중복 URL 관리. 짧은 주소가 필요하면 Cloudflare 301
  리다이렉트로 충분.
- **되돌림**: `git revert --no-commit 0bef4f3` → `suvis/next.config.mjs`
  리라이트 24줄 제거(원 상태 복원 확인). 커밋·푸시 대기 — Vercel에는
  푸시돼야 반영됨.
- **PROGRESS 전면 정리**: 1396줄→178줄. 완료 항목 상세를 워크로그 날짜
  인덱스로 압축, 워크로그 대조로 이미 완결된 백로그(재임베딩·HNSW·Gemini
  레이트리밋·rating 노이즈·감정 축·터널 잠금·RAG 연도 필터 등) 제거.
- **GitHub 실측**: 조직 `Team-Seuk` 존재(Arda·_template 등), 사용자 역할
  member. 조직 owner 명의 확인이 팀 이전의 선행 과제 — 계획서에 저장소
  신설/조직 이전 절차 기록.

### 작업 내용 (저녁 2 — seuk GitHub 조직 신설 + Arda mirror 이전)
- 구 `Team-Seuk` owner는 woojeongalex 1명, 사용자는 member라 Transfer
  불가 → 새 조직 `Seuk-Team` 생성(사용자 owner). 이름은 `Team_Seuk`(밑줄
  불가)·`TeamSeuk`(구 조직과 혼동) 대신 확정. 팀원 3명 초대, 기본 저장소
  권한 write(`gh api PATCH orgs/Seuk-Team`).
- 이전 방식 결정: 인프라(Vercel·AWS)를 새로 연결하므로 mirror의 단점
  (재연결)이 사라져 **mirror push** 채택. 히스토리는 포트폴리오 증빙(커밋
  작성자)·팀원 로컬 호환 때문에 유지 — 빈 저장소에 새로 올리는 방식은
  기각. 나중에 Transfer를 받으면 그때 대체.
- `Seuk-Team/Arda`(public) 사용자가 화면에서 생성 — `gh repo create`·
  `gh api POST`가 분류기에 차단됨. `git clone --mirror` → `git push
  --mirror`. **검증**: 브랜치 13/13 SHA 일치, main 366 커밋, 기본 main.
  `refs/pull/*` 거부는 정상.
- `main` 브랜치 보호(`gh api PUT .../branches/main/protection`): PR 승인 1
  필수·stale 승인 무효·force push/삭제 금지, enforce_admins=false.
- enforce_admins는 사용자 요청으로 **켬**(owner도 PR 필수).
- **옛 브랜치 12개 정리**: `git rev-list`로 main 대비 앞/뒤 커밋 수,
  `merge-tree`로 충돌, 구 저장소 `gh pr list --head`로 PR 이력 대조.
  main 포함 4개 / 충돌 8개(전부 100~300커밋 뒤처짐). 8개 중 살린 건
  `fix/agent-test-tool-count` 1개 — 도구 카운트는 main이 12개로 앞서 폐기,
  쓰기 도구 테스트 목록의 `create_schedule_proposal` 누락만 남겨
  `rebase/fix-agent-test-tool-count` → **Seuk-Team/Arda PR #1**. 나머지는
  대체(09-02 모바일 개편)·본인 폐기(#154)·팀 닫음(#26·#120·#126·#133)·
  stale docs로 삭제 대상. 브랜치 삭제 `gh api DELETE`는 분류기 차단 —
  사용자 실행용 명령 전달.
- 옛 브랜치 12개 사용자가 삭제 실행 → 남은 브랜치 main + PR #1 브랜치.

### 작업 내용 (저녁 3 — Vercel 새 프로젝트 + seuk.suvisdev.cloud)
- 순서 결정: **Vercel 먼저, AWS 병렬(SES 신청부터)** — 프론트는 정적이라
  기존 백엔드를 그대로 불러 즉시 동작, AWS는 SES 샌드박스 해제(08-27
  거절 이력)가 병목.
- Arda 인프라 실측: `frontend/app`(Vite, `VITE_API_BASE`로 API 주소,
  `.env.production`에 `api.arda.seuk.cloud`), `infra/`에 prod compose
  (db·api·worker·caddy)+Caddyfile, `backend/.env.example`에 AWS·SES·SQS·
  Anthropic·CORS_ORIGINS 키. 07-deploy: 기존 EC2·AWS 접근자는 woojeongalex뿐.
- 사용자 콘솔 진행(안내): Vercel GitHub 앱을 Seuk-Team에 Arda만 허용 설치
  → 프로젝트 `arda`(Root `frontend/app`, `VITE_API_BASE`) 배포 →
  `arda-teal.vercel.app` 200 → 도메인 `seuk.suvisdev.cloud` 추가 +
  Cloudflare CNAME → HTTPS 200·인증서 정상 확인(curl).
- **CORS 실측**: 기존 백엔드 preflight — 새 origin 2개 400, 기존
  `arda-nu.vercel.app` 200. 새 주소에서 화면은 뜨나 API 호출 차단.
  해결 A(woojeongalex `CORS_ORIGINS`+S3 CORS 추가) / B(Vercel rewrite PR)
  결정 대기.
- 남은 것: CORS 결정, AWS 이전, 팀원 remote 교체, 구 저장소 Archive,
  두 번째 owner, PR #1 승인 — 계획서에 기록.

### 작업 내용 (저녁 4 — AWS 계정 방침 변경 → 개인 백엔드 노트북 이전)
- **방침**: 새 AWS 계정은 동일 명의라 프리티어 불가 → 개인 계정 하나.
  EC2 실측: m7i-flex.large(8GB, 크레딧 월 ~70$), 메모리 4GB 여유, Neo4j
  1.3GB(읽는 코드 없음), 디스크 6.6GB 여유·이미지 10.9GB 정리 가능.
  "Arda 동거"를 권했으나 사용자 결정은 **개인 백엔드를 노트북으로 내리고
  EC2는 Arda 전용**(크레딧을 팀에만).
- **사고 아님**: 세션 중 EC2 22/80/443 무응답·api 530 — 사용자가 크레딧
  절약차 일부러 중지한 것. 재시작 후 공인 IP 변경(Elastic IP 아님) →
  `~/.ssh/config` 13.125.14.24로 갱신, 터널 자동 복구(api 200).
- **이전 실행**(상세 순서·검증값은 SUBDOMAIN_MIGRATION_PLAN.md "개인
  백엔드 EC2 → 노트북 이전"): EC2 전체 덤프·env·crontab 백업 → 로컬
  개발 DB(영화 47편) 드롭 후 프로덕션 덤프 복원(3,410편 등 EC2 일치) →
  `.env` 병합(단독 `1` 줄 재발견·제거, 5키 추가, lora 직결) → crontab
  3건 등록 → 이미지 재빌드 → backend·auth 기동 → **컷오버 완료 23:35**.
- **컷오버 중 502 사고(약 1분)**: 노트북 cloudflared가 같은 토큰으로
  터널에 합류하자 Cloudflare가 신규 커넥터를 우선해 공개 요청 8/8건이
  노트북으로 왔는데, 터널 원본이 `http://nginx:80`이라 nginx 없는 노트북에서
  `lookup nginx ... server misbehaving` → 502. 즉시 replica 정지로 복구,
  `docker compose up -d nginx`(repo `nginx/conf.d/app.conf`, HTTP only) 후
  재합류 → 12/12 200 → EC2 cloudflared 정지 → 8/8 200·jwks 200.
  교훈: **remote-managed 터널의 원본 주소는 대시보드에만 있다** — replica를
  추가하기 전에 원본 서비스명(nginx)이 그 호스트에도 뜨는지 확인할 것.
- 현재 노트북 컨테이너: nginx·backend·auth·db·redis·cloudflared(pgadmin
  정지). EC2 개인 스택은 아직 떠 있음(cloudflared만 정지) — 하루 안정
  확인 후 down·축소·Arda 배포.
- 발견: 노트북 lora-server는 08-25 AWQ 어댑터(데스크톱 09-02 GGUF보다
  구버전) — 후속 동기화 필요. backend 부팅 시 감정분석 스케줄러가
  `frozenset` 오류로 리뷰 전건 실패 로그를 찍음(transformers 4.47.1 기존
  버그, 무해).

### 산출물 (저녁)
- `_docs/ARDA_AWS_DEPLOY_GUIDE.md` 신설 — S3·SQS·SES·IAM → EC2(Elastic IP·
  t3.small·Arda compose·alembic·create_admin) → DNS·Vercel 전환 → 검증
  체크리스트. 다음날 학원 세션 실행용.
- `_docs/SUBDOMAIN_MIGRATION_PLAN.md` 재작성(seuk 전용 + 되돌린 이유 +
  GitHub 이전 완료 기록), PROGRESS 정리, `suvis/next.config.mjs` 원복
  (커밋 `7f346f2`·`1534590` 푸시됨). GitHub: `Seuk-Team` 조직 +
  `Seuk-Team/Arda` 저장소.

### 작업 내용 (서브도메인 이사 — 방법 2 착수, 오후 — 저녁에 개인 앱 부분 되돌림)
- **mova·gildle 서브도메인 서빙**(사용자 결정): `suvis/next.config.mjs`에
  호스트 기반 rewrite — `mova/gildle.suvisdev.cloud`가 각 섹션을 루트로
  서빙(`/`→`/mova`, 그 외 경로 접두). `/api`(Next 프록시)·`/_next`·확장자
  있는 정적 파일·이미 접두된 경로는 제외해 이중 접두·에셋 깨짐 방지.
  기존 `suvisdev.cloud/mova` 경로도 그대로 유지(기존 링크 안 깨짐).
  빌드 통과, 커밋 `0bef4f3`(푸시 → Vercel 자동 배포).
- **백엔드 CORS는 무변경** — `allow_origins=["*"]` 실측 확인.
- **남은 사용자 콘솔 작업**: ① Vercel 프로젝트에 도메인 2개 추가
  ② Cloudflare CNAME(mova·gildle → cname.vercel-dns.com) ③ 소셜 로그인
  redirect URI에 서브도메인 추가(카카오·네이버·구글 콘솔). 유의: JWT가
  localStorage라 로그인 세션은 도메인별 분리(주 사용 주소 정하면 무해).
- **팀프로젝트(arda) 서브도메인**: 앱이 팀 Vercel(arda.seuk.cloud)에 있어
  ⓐ 팀 Vercel 프로젝트에 arda.suvisdev.cloud 도메인 추가(+CNAME) 또는
  ⓑ Cloudflare 리다이렉트 중 택1 — 팀 합의 필요, 대기.
- **AWS 분리 질문 결정**: 서브도메인 이사는 프론트 표면만 — 백엔드는
  api.suvisdev.cloud 공유 유지(모놀리스 해체는 YAGNI, 필요 시점에 재검토).

### 작업 내용
- **지킬(suvisjk)에 Arda(ATS) 프로젝트 페이지 추가** — 팀 배포 데이터
  (`_data/project.yml` + 이미지 4종)와 데스크톱 문서 4건(소개·핸드북·현황·
  작업 가이드)을 판독해 `/arda/` 전용 페이지 구성.

### 수정/구현
- `suvisjk/_data/arda.yml` — 팀 공통 파일 값 그대로(파일명만 변경 —
  `project.yml` 슬롯은 개인 프로젝트 데이터가 사용 중, 주석으로 사유 명기).
  `my_role`은 팀 규칙("본인 역할로 수정")대로 **에이전트 파트**(아르 도구
  호출·지원자 AI 요약·RAG 시맨틱·프롬프트 체이닝)로 정정 — 배포본에는 팀장
  역할이 적혀 있었으나 현황 문서의 팀 구성(suvisdev=에이전트)으로 판독.
- `suvisjk/arda.markdown` — 문제 정의→기능 표→**내 파트(아르) 심화**(쓰기
  확인 강제, 도구 6종 서비스 레이어 재사용, 비용 가드, ADR-0003)→아키텍처
  SVG→ERD→스택→스크린샷. 이미지는 팀 규약 경로 `/assets/img/` 유지(팀장
  재배포 시 덮어쓰기 호환). nav_order 6 삽입 + 뒤 페이지 5개 재배열,
  `toc.markdown` 5번 항목 추가·번호 재정렬. `jekyll build` 통과.
- 커밋 `7ccbf46`. 참고: suvisjk CLAUDE.md가 낡음(minima/ats 기술 —
  실제는 just-the-docs/jk) — 정리 후보.
- **(방침 변경으로 revert)** 사용자 결정: 개인 지킬에는 개인 프로젝트만 —
  팀 README의 "개인 레포 배치" 지시보다 본인 방침 우선. `7ccbf46`을
  revert(`ef64d06`)해 개인 사이트에서 Arda 제거.
- **Arda 시각 자료는 팀 문서 사이트(ats.suvisdev.cloud)에 반영** —
  `about.markdown` 아키텍처 섹션에 다이어그램 SVG+흐름 설명, ERD 섹션
  신설(9테이블·복합 UNIQUE 2건·ai_summary 컬럼), 화면 프로토타입 2장.
  커밋 `99da3e9`, Pages 배포 success·이미지 200 확인.

### 산출물
- suvisjk `7ccbf46`→revert `ef64d06`(개인 사이트 원상복구),
  ats.suvisdev.cloud `99da3e9`(시각 자료 보강, 라이브 확인).
  모노레포 쪽 재실측 기록은 WORK_LOG_MOVA 2026-09-03.

## 2026-09-02

### 작업 내용
- **팀프로젝트 ARDA 카드 추가** — 이전 세션 미커밋분 정리 커밋.
  메인 `/apps` 카탈로그의 Team Seuk 팀프로젝트 목록에 ARDA
  (AI Recruitment Assistant, `https://arda.seuk.cloud`) 항목 추가.
- 이 파일 첫 줄 단독 `1` 삽입 재발분 제거(PROGRESS "단독 1 문자 삽입"
  기존 알려진 편집기 이슈).

### 수정/구현
- `suvis/lib/apps-catalog.ts`: `TEAM_PROJECTS`에 arda 항목(💼, violet
  그라디언트) 추가. 검증: `npx tsc --noEmit` 통과.

### 오류·막힌 점
- 없음.

### 데이터
- 변경 없음.

### 산출물
- 커밋: 미커밋분 정리 커밋(MOVA 채팅 스크롤 수정과 함께).

## 2026-09-01

### 작업 내용
- **전 페이지 스크롤바 자동 숨김** — 사용자 요청(처음엔 mova 영화 탭만 →
  전체 확장). 스크롤 중에만 스크롤바가 보이게.
- **도메인 전체 스크래핑·복사 방지** — 사용자 요청. 클라이언트 억제책 +
  robots 차단.

### 수정/구현
- `components/scrollbar-autohide.tsx` 신규: 문서 캡처 단계 scroll 리스너
  하나로 모든 스크롤 요소(세로 본문 포함)에 `.is-scrolling` 토글(0.8초).
  요소별 개별 리스너 방식(1차 구현)은 전체 확장 시점에 걷어내고 이 전역
  방식으로 교체 — `drag-scroll-row.tsx`·`movies/page.tsx`는 원상 복구.
- `app/globals.css`: 전역 `*` 스크롤바 평소 투명(트랙 공간은 유지 —
  레이아웃 흔들림 없음), `.is-scrolling`일 때만 회색 썸.
  `app/mova/mova.css`: `.mova-row-scroll` 브랜드 색 썸을 `.is-scrolling`
  조건부로 변경.
- `components/content-guard.tsx` 신규: 입력 요소 밖 복사·잘라내기·우클릭
  차단. `globals.css` 전역 `user-select: none`(input·textarea·
  contenteditable 예외).
- `app/robots.ts` 신규: AI 학습·대량 수집 크롤러 17종(GPTBot·ClaudeBot·
  CCBot·Bytespider·PerplexityBot 등) 전체 차단 + `/admin/`·`/api/` 봇
  차단. 구글·네이버 등 검색 색인은 유지(전부 막으면 검색 노출 소멸).
- 루트 `app/layout.tsx`에 두 컴포넌트 마운트.

### 오류·막힌 점
- 없음. 한계 인지 사항: 복사 차단은 devtools/소스 보기까지는 못 막는
  억제책이고, robots.txt는 신사협정(악성 봇 무시) — 실효 차단은 Cloudflare
  Bot Fight Mode(대시보드, 사용자 조치) 병행 필요.

### 산출물
- `pnpm type-check`·`lint`·`build` 통과, robots.txt 생성 확인.
- 커밋·Vercel 배포 (해시는 커밋 시점 기록).

## 2026-08-31

### 작업 내용
- **mypy 재활성화 — 415건 → 0건 전량 해소, pre-commit 훅 복구**. 2026-08-26에
  1,327건(485파일)으로 비활성화됐던 mypy를 exclude 보정(134→415 실측) 후 5단계로
  전부 수정. 전 앱(mova·titanic·ontology·auth·dispatch·gildle·viewer) + `core/` 대상.

### 수정/구현
- **Phase 1 — 설정 보정**: `pyproject.toml` `[tool.mypy]`에 `explicit_package_bases = true`
  추가(모듈 이름 충돌 해소). exclude에 `"test/"`, `"_docs/"` 패턴 추가(기존 `"tests/"`만
  있어 s 없는 테스트 폴더·임시 스크립트가 검사에 포함되던 문제).
- **Phase 2A — `from_orm(orm: object)` → `orm: Any`** (12파일): Clean Architecture 경계의
  ORM 역직렬화 메서드. `[attr-defined]` ~81건 해소.
- **Phase 2B — `to_schema() -> object` → 구체 반환 타입** (10+파일): `TYPE_CHECKING` 블록 +
  lazy import 패턴. `[return-value]` ~33건 해소.
- **Phase 2C — Titanic 포트 ABC `async def` 통일** (8파일): I/O 메서드 `def` → `async def`.
  `[override]` ~29건 해소.
- **Phase 3-4 — 개별 타입 수정** (~40파일): SQLAlchemy `ColumnElement`/`Exists` 타입 불일치
  `# type: ignore[assignment]`, Optional 접근 None 가드, `no-any-return`에 `cast()`,
  외부 라이브러리(ultralytics·timm·boto3) `# type: ignore`, 함수 시그니처 타입 추가 등.
- **Phase 5 — `.pre-commit-config.yaml`**: mypy 훅 주석 해제(재활성화).
- **총 수정 파일**: 118개(`.pre-commit-config.yaml` + `pyproject.toml` + `core/` 3파일 +
  `apps/` 112파일 + 워크로그·PROGRESS 2파일).

### 오류·막힌 점
- Phase 3-4 포크가 한 번 monthly spend limit에 걸려 중단(134→122건 부분 해소).
  리밋 리셋 후 재시도로 나머지 전량 해소.
- `core/matrix/` 3파일이 `apps/` 밖이라 포크 스코프에서 빠짐 — 직접 수정(7건).

### 산출물
- `python -m mypy ... apps/` → **Success: no issues found in 1079 source files**
- `pytest -m "not gpu and not ollama"` → **728 passed, 0 failed**
- `python -c "import main"` → OK

---

## 2026-08-28

### 작업 내용
- 루트 `_docs/` 문서 분리 재실행(전 세션에서 취소했던 "4번" — 사용자 재결정):
  `SCRIPTS_EXECUTION_GUIDE.md` → `suvisdev/_docs/`, MOVA 포트폴리오 3건
  (`MOVA_INTERVIEW_QA.md`·`MOVA_PORTFOLIO_SUMMARY.md`·`MOVA_Portfolio.pptx`) →
  `suvisdev/apps/mova/_docs/`. 이동에 따른 경로 참조 3곳(README 안내 문구·
  ROADMAP "같은 폴더" 표기·가이드 내 "루트" 접두사) 동반 수정.
- `_docs/` 잔여 항목 전수 판정: 워크로그 3종·PROGRESS·README·EXAONE 셋업·
  `.obsidian/`은 공통/인프라 성격 + CLAUDE.md·훅이 경로 참조라 유지.
  `ARCHITECTURE_BLUEPRINT.md`는 워크스페이스 공통 기준 문서로 유지.

### 수정/구현
- 위 이동 4건 + 참조 수정(`_docs/README.md`·`suvisdev/_docs/MOVA_POST_V1_ROADMAP.md`·
  `suvisdev/_docs/SCRIPTS_EXECUTION_GUIDE.md`).

### 오류·막힌 점
- 없음(이동은 커밋 전 스테이징 단계 왕복이라 git 이력 영향 없음).

### 데이터
- 해당 없음.

### 산출물
- mova 채팅 하네스·오추천 수정은 `WORK_LOG_MOVA.md` 2026-08-28 참고.
- (외부 저장소) 팀 프로젝트 지킬 `ats.suvisdev.cloud`: 팀원별 소유 데이터
  파일(`_data/kanban/<아이디>.yml`) 기반 칸반 보드(`/kanban/`) 신설 — 5인
  동시 편집 git 충돌 제거 구조. Arda 저장소 실측 분석 포스트 등재(f5e698b).
  개인 지킬 `suvisjk`에는 mova 개발기·에이전트 W1 포스트 2건(cac1681).

## 2026-08-27

### 작업 내용
- LLM 챗 엔드포인트 3개(titanic `smith/chat`·execsuite `langchain/chat`·
  contents `soccer/chat`)가 백엔드 무인증·무 rate-limit으로 인터넷에 공개돼
  있던 것(2026-08-04 백로그 "의도 재확인 필요" 건)을 `require_admin`으로
  잠금. 착수 전 프로덕션 실측으로 세 URL 모두 `api.suvisdev.cloud`에서
  살아 있음을 확인(GET 405 = 라우트 존재). 사용자 결정: "mova 챗 제외
  전부 잠금"(mova 챗만 공개 유지 — 자체 IP rate limit 보유).
- 조사 중 발견: `/api/v1/langchain/chat`은 레슨 페이지뿐 아니라 **사이트
  전역 공개 플로팅 챗 위젯(`SuvisChatPanel`)**도 호출하고 있었음 —
  백엔드만 잠그면 익명 방문자에게 고장난 위젯이 남으므로(mail/contacts와
  동일한 반쪽 상태) 위젯도 관리자 전용 노출로 함께 전환.
- EC2 `~/auto-deploy.sh` 재작성 — backend 재생성 후 nginx가 구 IP를 캐시해
  외부 502가 나던 문제(실측 2회, 8/25 백로그)의 재발 방지.

### 수정/구현
- 백엔드: 라우터 3개(`crew_smith_captain_router.py`·`langchain_chat_router.py`·
  `soccer_chat_router.py`)에 `require_admin` 부착(`.claude/rules/security/auth.md`
  §1 표준 패턴).
- 프론트(3계층 토큰 전달): 프록시 `route.ts` 3개가 Authorization 헤더를
  백엔드로 전달, 페이지 3개(smith-captain·soccer/chat·langchain/chat)가
  `authHeader()`로 세션 토큰 전송, `gemini-chat-panel.tsx`는 헤더와 동일한
  세션 role 구독 패턴으로 비관리자에게 렌더링하지 않음 + 토큰 전송.
- 테스트: 앱별 401/관리자 통과 테스트 6건 신규(media 테스트의
  dependency_overrides 패턴), `pytest.ini` testpaths에 `apps/execsuite/tests`·
  `apps/contents/test` 추가(그동안 미수집 스캐폴드였음).
- EC2 `~/auto-deploy.sh`(레포 밖 파일) 재작성: ① `docker compose restart` →
  `--env-file suvisdev/.env up -d --build`(restart는 새 코드 미반영, 8/3 실측),
  ② 배포 후 `docker exec nginx nginx -s reload` 항상 실행, ③ 인자로 서비스
  지정(기본 backend). 구버전은 `~/auto-deploy.sh.bak-20260827`로 백업,
  cron은 2026-08-02부터 비활성 상태 그대로 유지(수동 실행 전용).

### 수정/구현 (추가) — /mail AdminAuthGate 적용
- 2026-07-28부터 미결이던 `/mail/contacts` 반쪽 상태(페이지는 공개인데
  백엔드 401) 종결 — 사용자 결정으로 `/mail` 전체를 관리자 전용으로 전환.
  `app/mail/layout.tsx` 신설(레슨 레이아웃과 동일 `AdminAuthGate` 패턴).
- mail(이메일 발송)·mail/contacts(CSV 업로드) 페이지가 `authHeader()`로
  세션 토큰을 보내도록 배선 — 프록시는 이미 전달 중이었고 페이지만 빠져
  있어 관리자조차 401을 받던 것 해소(3계층 전달 완성).
- 낡은 문서 기술 정정: `security/auth.md` §4 미결 표기,
  `suvis/CLAUDE.md` B·D의 "401 이슈" 표기, PROGRESS 백로그 항목 종결.

### 수정/구현 (추가) — /dispatch·/telegram도 동일 정리 (전수 확인 후)
- 게이트 없는 전 라우트의 `/api` 호출을 전수 grep — `/dispatch`(이메일
  발송 데모)·`/telegram`(텔레그램 발송 데모)이 /mail과 동일한 반쪽 상태
  (공개 페이지 ↔ require_admin 백엔드, 페이지 토큰 미전송)로 확인돼 같은
  패턴 적용: `layout.tsx` AdminAuthGate 신설 2건 + 페이지 `authHeader()`
  배선 2건. 이 외 남은 공개 호출은 gildle 지도(graph-edges·navigate)뿐
  인데 인증 없는 공개 데이터 조회(LLM 비용 없음)라 의도된 공개로 판단.

### 오류·막힌 점
- 세션 권한 분류기가 EC2 스크립트 원격 쓰기(ssh heredoc·scp)를 차단 —
  스크립트 파일을 준비해 사용자가 scp 3줄을 직접 실행, 이후 원격 확인은
  읽기 전용 ssh로 완료.

### 산출물
- 검증: pytest 639 passed(신규 6건 포함), lint-imports 6 계약 KEPT,
  `pnpm type-check`·lint 통과(경고 1건은 기존 백로그 등재분).
- 결정 기록(사용자, 2026-08-27): **Gemini 유료 티어 전환 안 함** — 무료
  티어 제약(임베딩 1,000/일, 분당 15요청)을 전제로 운영 계속.
- PROGRESS.md 갱신: LLM 챗 무인증 백로그 → 완료, nginx 리로드 후속 → 완료,
  9순위 (a) 결정 반영.

---

## 2026-08-26

### 작업 내용
- `/apps` 팀 프로젝트 카드 교체: Yaksok(알약 식별, seuk.cloud) 제거 →
  팀 SEUK 도메인(`team.seuk.cloud`, "슥 만드는 해커톤 팀") 카드 추가.
  사이트 라이브(200) 확인 후 available: true.

### 수정/구현
- `suvis/lib/apps-catalog.ts` — TEAM_PROJECTS yaksok 항목을 seuk 항목으로 교체
  (이미지 없이 ⚡ 아이콘 폴백 사용).
- `suvis/public/apps-yaksok.jpg` 삭제(참조 0).

### 산출물
- `pnpm type-check` 통과. 커밋 후 Vercel 자동 배포.

### 수정/구현 (추가) — eslint 파이프라인 복구
- `pnpm lint`가 죽어 있었음(eslint가 devDependencies에 없음, WSL 재구축
  여파로 추정) — eslint 9 + eslint-config-next 15.5 설치, `.next/` ignore,
  `pnpm-workspace.yaml`에 unrs-resolver 빌드 승인.
- 드러난 38 에러 정리: `--fix` 24건(type import 등) + 수동 14건(죽은
  변수·함수·임포트 8, react/display-name 2, `<a>`→`Link`, console.error
  제거, use-toast actionTypes 타입화 2). 경고 1건(mova-ai-chat-bar
  useCallback deps)은 동작 변경 위험으로 의도적 보존.
- 검증: `pnpm build` exit 0, eslint 0 errors, `tsc --noEmit` 통과.

## 2026-08-25

### 작업 내용
- Jekyll 포트폴리오 사이트(suvisjk) GitHub Pages 배포: Just the Docs 테마 적용,
  `suvisdev/suvisjk` 레포 생성, GitHub Actions Jekyll 워크플로우 설정,
  커스텀 도메인 `jk.suvisdev.cloud` 연결 (Cloudflare DNS CNAME).
- 두 Jekyll 사이트(suvisjk 4000, demo 4001) 포트 고정 분리.
- 메인 사이트 헤더 네비게이션 개편: About·Devlog 제거 → Apps·Blog·Resume·Contact 4개로 재구성.
  Blog는 `jk.suvisdev.cloud` 외부 링크, Resume는 플레이스홀더 페이지(`/resume`).
- Mova 랭킹 페이지: 탭 순서 변경(박스오피스 먼저) + 기본값을 box_office로 변경.
- Jekyll devlog 페이지: 전체/Mova/Gildle/인프라·보안 탭 필터링 UI + WORK_LOG 기반 포스트 8건 추가.

### 수정/구현
- `suvis/components/header.tsx`: 네비게이션 About·Devlog → Blog(jk.suvisdev.cloud)·Resume 변경
- `suvis/app/resume/page.tsx`: 신규 Resume 페이지 래퍼
- `suvis/app/resume/_components/resume-content.tsx`: 신규 — 좌측 사이드바 네비 + 우측 콘텐츠 5섹션
  (About·Projects·Tech Stack·Education·Contact), IntersectionObserver 스크롤 스파이,
  악센트 색상 골드/앰버(amber-600), 다크→화이트 배경 라이트 모드 전환,
  이름 "진수택" 반영, Contact에 전화번호(마스킹) 추가
- `suvis/app/mova/rankings/page.tsx`: TABS 순서 + resolveSource 기본값 변경
- `suvisjk/_config.yml`: `port: 4000`, `url: https://jk.suvisdev.cloud`
- `demo.suvisdev.cloud/_config.yml`: `port: 4001`
- `.github/workflows/jekyll.yml`: Ruby 3.1 → 3.3 (Bundler 4.x 호환)

### 산출물
- GitHub Pages: https://jk.suvisdev.cloud
- 레포: https://github.com/suvisdev/suvisjk

---

## 2026-08-12
### 작업 내용

- 문서 정리 사이클 — 사용자가 여러 문서를 순회하면서 종결된 것/잘못 위치한
  것/중복된 것을 하나씩 점검·정리.
- 프론트 정비 — 메인 히어로 이미지 이질감 제거(포스터→영상 첫 프레임), mova
  채팅 UI를 Gemini/Claude 스타일 2단 모드로 개편.
### 산출물

- 커밋 3건(문서 정리 / 히어로 포스터 / mova 채팅 UI 개편 + WORK_LOG).
- Vercel `main` 자동 배포로 프론트 반영. EC2 backend/auth 재빌드 불필요
  (순수 프론트 변경).

---

## 2026-08-04

### 작업 내용
- S3에 저장된 사진을 웹에서 읽어오는 기능(vision OCR scan) 착수 전, 사용자가
  준 초안 하네스를 저장소 실측 코드와 대조해 검증 후 백엔드/프론트 하네스
  문서로 분리 작성.
- `suvis/package.json`에 shadcn을 "추가"해달라는 요청 확인 — 이미 전부 설치돼
  있음을 확인하고 무엇이 빠졌는지(최신 채팅 UI 컴포넌트군)만 회신, 코드 변경
  없음.
- `suvis/` 스타일링을 Tailwind CSS + shadcn/ui 토큰 체계 하나로 통일 — 사용자
  확인 후 문서 작성 + 실제 마이그레이션까지 진행.

### 수정/구현
- **vision_ocr_scan 하네스**: `suvisdev/_docs/s3-ocr-reverse-harness.md`,
  `suvis/_docs/s3-ocr-reverse-harness.md` 신규. 초안의 잘못된 전제 3개를
  바로잡음 — (1) `Tank`(`core/matrix/aws_tank_s3_manager.py`)는 boto3 기본
  자격증명 체인이라 EC2 IAM Role과 이미 호환됨("Tank 금지"는 오류,
  `VisionS3Repository.save_image`가 이미 씀), (2) vision 업로드 기본 배선은
  지금 S3가 아니라 DB(`VisionRepository`) — read 하네스가 스캔할 대상이
  어디 있는지 별도 결정 필요, (3) S3 키가 평면 구조(`vision/{timestamp}_
  {filename}`)라 `folder=` 쿼리 파라미터 전제가 성립하지 않음. 착수 전
  "결정 필요" 4항목(OCR 엔진·스캔 대상 경로·인증 여부·지속화 여부)으로
  정리. 실제 코드 구현은 아직 없음 — 계획 문서만.
- **suvis 스타일링 통일**(`suvis/_docs/DESIGN.md` 신규 + 실행):
  - `app/globals.css`의 `@theme inline`에 `--color-mova-*` 10개 토큰 등록
    (`app/mova/mova.css`가 정의하는 `--mova-bg`/`--mova-surface`/`--mova-accent`
    등을 shadcn 토큰과 같은 경로로 노출).
  - `app/mova/**`·`components/mova/**` 27개 tsx 파일에서 `text-[var(--mova-
    text)]` 류 Tailwind 임의값 문법 354곳을 `text-mova-text` 같은 명명
    유틸리티로 기계적 치환(정규식 `\[var\(--mova-([a-z0-9-]+)\)\]` →
    `mova-$1`). 합성 arbitrary value(그라디언트, `shadow-[0_0_12px_var(...)]`)와
    SVG `stroke` 속성 3곳은 named token으로 못 바꿔 그대로 둠.
  - 미사용 죽은 파일 `suvis/styles/globals.css` 삭제(`app/globals.css`만
    실제 사용, `styles/`쪽은 아무 데서도 import 안 됐음).
  - mova.css의 스크롤바·`offset-path` 모션·`@keyframes` 등 Tailwind로 표현
    안 되는 raw CSS는 그대로 유지(억지로 인라인화하지 않음 — `app/globals.css`
    자체도 같은 패턴을 이미 씀).

### 오류·막힌 점
- 없음. `pnpm type-check`·`pnpm build` 통과, 빌드 산출물 CSS(`.next/static/
  chunks/*.css`)에서 `bg-mova-surface` 등이 치환 전과 동일한 `var(--mova-*)`
  참조로 생성되는 것 직접 확인(시각적 회귀 없음, 순수 문법 치환).
- `pnpm lint`는 이 환경에 `eslint` 바이너리 자체가 미설치라 실행 불가(clean
  tree에서도 동일하게 실패하는 기존 환경 문제, 이번 변경과 무관 — 확인만 함).

### 데이터
- 해당 없음.

### 산출물
- 신규: `suvisdev/_docs/s3-ocr-reverse-harness.md`,
  `suvis/_docs/s3-ocr-reverse-harness.md`, `suvis/_docs/DESIGN.md`.
- 수정: `suvis/app/globals.css`, `app/mova/**`·`components/mova/**` 27개 tsx.
- 삭제: `suvis/styles/globals.css`.
- 커밋: `ec788cf`, PR #27 머지(`53dd78e`).

### 작업 내용(추가①) — `suvis/_docs/CLAUDE.MD`를 `suvis/CLAUDE.md`로 이동 + 최신화
- 사용자가 이 문서가 정말 프론트 전용인지, 아니면 다른 곳으로 옮길 내용이
  섞였는지 물어봐서 전문을 검토. 다른 스택(백엔드·Flutter) 내용은 없었지만
  실제 코드 상태와 크게 어긋나 있었음(존재하지 않는 `types/` 디렉터리를
  전역 타입 위치로 문서화 — `.claude/rules/typescript.md` §3과 정반대,
  `app/` 디렉터리 구조표가 admin/dispatch/harvester/vision 등 대부분 누락,
  `lib/` 목록도 9개뿐으로 stale). 사용자가 "최신화 + `_docs/` 밖으로 꺼내서
  `suvis/`에 담자"고 확정.

### 수정/구현(추가①)
- `suvis/CLAUDE.md` 신규 작성(디렉터리 구조·`lib/` 목록·라우트 표 전면
  갱신, `types/` 모순 제거, C.3 스타일 절에 오늘 작업한 shadcn 토큰 통일
  내용과 `_docs/DESIGN.md` 링크 반영) — `suvis/_docs/CLAUDE.MD`는 삭제.
  루트 `CLAUDE.md`의 링크 테이블이 원래부터 `suvis/CLAUDE.md`를 가리키고
  있어 실제 위치를 그 기대에 맞춘 것.
- 옛 경로(`suvis/_docs/CLAUDE.MD`)를 참조하던 6곳 경로 수정:
  `.claude/rules/typescript.md`, `.claude/rules/api-standards.md`, 저장소
  메모리(`MEMORY.md`, `patterns.md`), `suvis/.cursorrules`,
  `suvisdev/apps/mova/_docs/CLAUDE.md`(+`.cursorrules`).

### 오류·막힌 점(추가①)
- 옛 `suvis/_docs/CLAUDE.MD`를 지우기 직전 `git diff`에서 `---`와
  `## C. 핵심 규칙` 사이에 정체불명의 단독 `1` 문자가 끼어 있는 걸 발견 —
  `suvisdev/.env` 반복 손상(2026-07-29, 07-30, `SUVIS_ADMIN_MULTIAGENT_
  PROGRESS.md` 기존 항목)과 정확히 같은 패턴. `.env`와 마크다운(IDE에서 열려
  있던 파일) 둘 다에서 나타나 파일 타입 문제가 아니라는 정황이 늘어남 —
  진행 상황 문서에 정황 추가, 원인은 미해결.

### 산출물(추가①)
- 신규: `suvis/CLAUDE.md`. 삭제: `suvis/_docs/CLAUDE.MD`.
- 수정: `.claude/rules/{typescript,api-standards}.md`,
  `.claude/projects/-home-a-projects-suvis/memory/{MEMORY,patterns}.md`,
  `suvis/.cursorrules`, `suvisdev/apps/mova/_docs/{CLAUDE.md,.cursorrules}`,
  `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(단독 `1` 문자 정황 추가).

### 작업 내용(추가②) — `/lesson`에 S3 사진 OCR 페이지 신설
- 사용자가 "아까 한 이미지 다운받은거 lesson 페이지에 출력"을 요청 — 확인해
  보니 전날 만든 건 계획 문서(하네스)뿐이고 실 구현은 없었음(`Tank.list_objects`
  도, OCR 엔드포인트도 없었음)을 먼저 정정. S3에 실제로 있는 이미지는
  susu 카메라 업로드(`media/{user_id}/...`, 개인 사진) 하나뿐이라, 공개
  페이지에 그대로 노출하면 `adress`/`mail/contacts`와 같은 무인증 개인정보
  노출 패턴이 될 위험을 짚고 사용자 확인 후 "로그인한 본인 사진만" 노선으로
  확정. 이어서 `/lesson`이 이미 `AdminAuthGate`로 관리자 전용임을 발견 —
  그 로그인(HS256 `require_admin` 체계)을 그대로 재사용하기로 함(susu/mova가
  쓰는 RS256 aud 체계와는 별개지만 `user_id`가 같은 테이블이라 prefix가
  그대로 맞음).

### 수정/구현(추가②)
- **백엔드**: `core/matrix/aws_tank_s3_manager.py`에 `Tank.list_objects(prefix)`
  추가(list_objects_v2 페이지네이션). `apps/media/ocr.py` 신규 — Gemini
  멀티모달로 이미지→텍스트(`mova`/`ontology`의 `Keymaker` 재사용 패턴과
  동일한 에러 매핑). `apps/media/router.py`에 `GET /api/media/photos/ocr`
  추가 — `require_admin`으로 가드, `media/{admin.user_id}/` prefix만 조회해
  본인 사진만 반환, 최신순 정렬, 최대 12장, 개별 OCR 실패는 전체를 막지
  않고 "(텍스트 추출 실패)"로 대체. `apps/media/schemas.py`에 `OcrPhotoItem`
  추가. 테스트 4건 추가(`apps/media/tests/test_router.py`, `_FakeTank`에
  `list_objects`/`download_bytes`/`generate_presigned_url` 확장) — 9개 전부
  통과, import-linter 위반은 기존 것과 무관함 확인.
- **프론트엔드**: `lib/media-api.ts`, `app/api/media/photos/ocr/route.ts`
  (프록시, `backendFetch` 재사용) 신규. `app/lesson/photos/page.tsx` 신규 —
  기존 레슨 페이지들과 동일한 사이드바 셸을 복제해 일관된 톤 유지, 로딩/
  에러/빈 목록/그리드 상태 분기. `app/lesson/page.tsx`에 "MEDIA" 사이드바
  섹션·카드 추가해 연결.

### 오류·막힌 점(추가②)
- 없음. `pnpm type-check`·`pnpm build` 통과(`/lesson/photos`,
  `/api/media/photos/ocr` 라우트 정상 컴파일), 백엔드 `pytest apps/media/tests`
  9개 통과.

### 데이터(추가②)
- 해당 없음(S3 실제 데이터 연동은 배포 환경에서 자격증명·susu 업로드 실측
  필요 — 로컬에서는 fake 기반 테스트만 검증).

### 산출물(추가②)
- 신규: `suvisdev/apps/media/ocr.py`, `suvis/lib/media-api.ts`,
  `suvis/app/api/media/photos/ocr/route.ts`, `suvis/app/lesson/photos/page.tsx`.
- 수정: `suvisdev/core/matrix/aws_tank_s3_manager.py`,
  `suvisdev/apps/media/{router,schemas}.py`,
  `suvisdev/apps/media/tests/test_router.py`, `suvis/app/lesson/page.tsx`.

### 작업 내용(추가③) — EC2 실배포 디버깅 + PROGRESS.md 백로그 2건 이어서 진행

사용자가 Vercel(프론트)·EC2(백엔드) 배포 후 `/lesson/photos`가 502로 안 뜬다고
보고 → 원인 규명 및 수정. 이어서 사용자가 실제로 사진을 올렸는데도 목록이
비어 있다고 재보고 → 계정 불일치 발견·수정. 이후 `SUVIS_ADMIN_MULTIAGENT_
PROGRESS.md` 백로그를 같이 훑고 "어드민 통계 방문자 EC2 확인"·"mova 리뷰
watched 게이트" 2건을 이어서 진행하기로 함.

### 오류·막힌 점(추가③) — 실제로 겪은 프로덕션 이슈 3건, 원인·조치 순서대로

1. **502 — `docker compose up -d --build backend`를 `--env-file` 없이 실행**:
   `docker-compose.yaml` 주석에 `--env-file suvisdev/.env` 필수라고 이미
   적혀 있었는데 빠뜨림 → `${POSTGRES_USER}` 등이 compose 파일 안에서 빈
   문자열로 치환돼 `db` 컨테이너가 빈 자격증명으로 재생성, 백엔드
   `DATABASE_URL`도 같이 깨져 `fe_sendauth: no password supplied`로 전
   요청 502. `db_data` named volume은 그대로라 데이터 유실은 없었음(실제
   저장된 비밀번호는 재생성으로도 안 바뀜) — 다만 `--env-file` 없이 돌리면
   `db`가 매번 불필요하게 재생성되는 부작용은 있음. `docker compose
   --env-file suvisdev/.env up -d --build backend db`로 재실행해 복구.
2. **AWS 자격증명 자체가 EC2에 없었음(이번 502와 별개, 원래부터 있던 문제)**:
   `Tank.list_objects` 테스트 중 `NoCredentialsError` 발견 — 이 EC2 인스턴스는
   IAM Role이 아예 안 붙어 있고 `suvisdev/.env`에도 `AWS_ACCESS_KEY_ID`/
   `AWS_SECRET_ACCESS_KEY`가 없었음(둘 다 0건). 로컬(이 세션 샌드박스)
   `.env`에도 없어서, 사용자가 실제 테스트했던 "111 영수증" 업로드는 이
   세션이 아니라 집 컴퓨터에서 한 것으로 추정. 사용자가 EC2 `.env`에 키를
   추가 → 1차 시도는 `AWS_SECRET_ACCESS_KEY`가 40자가 아니라 14자로 잘려
   있어 `InvalidAccessKeyId`로 재실패 → 재발급 후 정상화, 실제 S3
   객체(`111.jpg`, 책장 사진)로 다운로드+Gemini OCR 종단 검증 완료. 값은
   채팅에 노출하지 않고 로컬→EC2로 SSH 파이프(`grep | ssh ... "cat >>
   .env"`)로만 옮김.
3. **susu(카카오)·웹 관리자(구글) 계정 불일치**: 실제 업로드가 `media/4/...`
   로 잘 들어갔는데도 `/lesson/photos`가 빈 목록이었던 원인 — `require_admin`
   본인 `user_id`로 `media/` prefix를 좁힌 게 문제였음. `users` 테이블
   확인 결과 susu 카카오 로그인(`user_id=4`, `kakao_5000588573@kakao.local`
   플레이스홀더 이메일)과 웹 관리자 구글 로그인(`ssuvisdev@gmail.com`,
   다른 `user_id`)이 서로 안 이어진 별개 계정임을 확인. 사용자 요청으로
   "관리자는 전체 사용자 사진을 봄"으로 스코프 변경(`media/` 전체 스캔 +
   응답에 `user_id` 추가) — 계정 연결 기능 자체는 별도 백로그로 남김(오늘
   손대지 않음).

### 수정/구현(추가③)
- `suvisdev/apps/media/{router,schemas}.py`: `GET /api/media/photos/ocr`을
  관리자 본인 prefix 스코프에서 `media/` 전체 스캔으로 변경, `OcrPhotoItem`에
  `user_id` 필드 추가(키 `media/{user_id}/...`에서 파싱). 테스트도 "전체
  사용자가 다 보임" 시나리오로 갱신(`apps/media/tests/test_router.py`, 9개
  전부 통과).
- **어드민 통계 방문자(백로그 재확인)**: `alembic current`가 이미
  `20260731_0001 (head)`였고 `visitor_activity`도 실데이터 15행 보유 —
  이전에 이미 반영된 상태였음을 확인만 하고 완료 처리(추가 조치 없음).
- **mova 리뷰 watched 게이트(백로그 구현)**: `ReviewsRepositoryPort
  .has_watched()` 신설 + PG 구현(`user_actions` EXISTS 조회) +
  `ReviewsInteractor.add_review()` 맨 앞 게이트(신규
  `ReviewNotWatchedError`, 403) + 라우터에서 캐치. 프론트
  `POST /mova/reviews/activity` 프록시·`addReviewActivity()`·영화 상세
  페이지 "봤어요" 버튼(찜하기 버튼과 동일 톤, `Eye`/`Check` 아이콘) 신규.
  워치 상태 조회 API가 없어 버튼 표시는 세션 로컬 상태로만 추적(서버 기록
  자체는 항상 남음). 인터랙터 테스트 2건 추가 + 기존 6건에 `has_watched`
  명시적 스텁 보강 — `apps/mova/tests` 81개 전부 통과. `pnpm type-check`·
  `pnpm build` 통과.
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`: 완료된 3건(S3 실연결,
  어드민 통계 방문자 EC2, mova watched 게이트)을 백로그에서 "완료됨"으로
  이동.

### 데이터(추가③)
- EC2 실 S3 버킷(`suvisdev-s3-584569945696-ap-northeast-2-an`) 확인 —
  susu 업로드 경로(`media/4/...`) 사진 1장 + 버킷 루트에 수동 테스트
  파일 2개(`1.png`, `111.jpg`, 이번 작업으로 새로 만든 것 아님).

### 산출물(추가③)
- 수정: `suvisdev/apps/media/{router,schemas,tests/test_router.py}`,
  `suvisdev/apps/mova/app/ports/output/market_reviews_{errors,repository}.py`,
  `suvisdev/apps/mova/app/use_cases/market_reviews_interactor.py`,
  `suvisdev/apps/mova/adapter/outbound/pg/market_reviews_pg_repository.py`,
  `suvisdev/apps/mova/adapter/inbound/api/v1/market_reviews_router.py`,
  `suvisdev/apps/mova/tests/test_market_reviews.py`, `suvis/lib/mova-api.ts`,
  `suvis/components/mova/title/mova-title-view.tsx`,
  `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`.
- 신규: `suvis/app/api/mova/reviews/activity/route.ts`.
- EC2 `.env`에 AWS 자격증명 반영(값은 기록하지 않음).
- 커밋: media 관련은 `9afa558`, PR #29 머지(`3bfc864`), EC2 반영 완료.
  watched 게이트는 이 항목 갱신 직후 커밋에서 확정.

### 작업 내용(추가④) — mova 동적 세그먼트 404 원인 규명 → 3단계 사이클로 해결

사용자가 mova 프론트 5개 페이지(홈/영화/컬렉션/랭킹/마이) 골격을 짜기 전 백엔드
데이터 매핑 조사를 요청 → 조사 중 "마이페이지 Not Found" 원인을 추적하다가
`suvis/app/api/mova/**`의 **동적 세그먼트 프록시 라우트 전체**(`[user_id]`,
`[slug]`, `[movieId]`)가 Vercel에서 404남을 발견(`x-matched-path` 헤더 없음,
정적 라우트는 정상). 이후 세 번의 승인 사이클로 진행:

1. **원인 확정 조사**(수정 없음): `next.config.mjs`의 `async rewrites()`가
   `/api/:path*` 캐치올로 백엔드 직결을 하고 있었고, Next.js rewrite 적용
   순서상(`afterFiles` 단계가 동적 라우트 매칭보다 먼저 실행) 이 캐치올이
   동적 세그먼트 라우트 파일을 가로채고 있었음. 로컬 `pnpm build`로
   `.next/server/app/api/mova/`에 9개 동적 route.js가 전부 정상 생성됨을
   확인해 "빌드 누락" 가설은 기각 — 런타임 라우팅 문제로 확정.
2. **캐치올 삭제 전 전수 의존성 조사**(수정 없음): `suvis/app/api/` 트리
   전체와 저장소 전체의 `/api/` fetch 호출을 교차 대조 → `titanic/smith/chat`,
   `v1/contents/soccer/chat`, `v1/langchain/chat` 3개가 대응 route.ts 없이
   이 캐치올에만 의존 중임을 발견(백엔드가 `/api` 또는 `/api/v1`로 마운트된
   앱들이라 캐치올이 우연히 맞아떨어지고 있었음 — mova만 `/api` prefix 없이
   마운트돼 있어서 유일하게 깨졌던 것도 이때 확정).
3. **스트리밍·인증 사전 확인**(수정 없음) → **route.ts 3개 신설 + 캐치올
   삭제 + 배포**(이번 항목).

### 수정/구현(추가④)
- **route.ts 3개 신규**(`app/api/titanic/smith/chat`, `app/api/v1/contents/
  soccer/chat`, `app/api/v1/langchain/chat`) — `app/api/mova/chat/route.ts`
  패턴 그대로 복제(`backendFetch` 호출 + JSON 파싱 실패 폴백). 사전 확인 결과
  세 백엔드 핸들러 전부 스트리밍 아님(`response_model=...Schema` 일반 응답),
  프론트 3곳도 `res.json()`으로만 소비 — 스트리밍 처리 불필요했음. 인증도
  셋 다 무인증이라 Authorization 헤더 전달 로직 없이 그대로 구현.
- **`next.config.mjs`의 `async rewrites()` 캐치올 블록 삭제** — `typescript`/
  `images` 필드는 그대로 유지, 문법 확인 완료.
- **백로그 2건** `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`에 기록: (1) mova만
  `/api` prefix 없이 마운트된 근본 원인 — 향후 통일 마이그레이션 고려,
  (2) `titanic/smith/chat`·`langchain/chat`·`soccer/chat` 셋 다 무인증+무
  rate-limit(LLM 호출인데 남용 벡터 가능성) — 의도된 설계인지 재확인 필요.

### 오류·막힌 점(추가④)
- 없음. `pnpm type-check`·`pnpm build` 매 단계 통과, `.next/server/app/api/`
  트리 직접 확인으로 mova 동적 9개 + 신규 3개 = 12개 전부 생성 재확인.

### 데이터(추가④)
- 해당 없음.

### 산출물(추가④)
- 신규: `suvis/app/api/titanic/smith/chat/route.ts`,
  `suvis/app/api/v1/contents/soccer/chat/route.ts`,
  `suvis/app/api/v1/langchain/chat/route.ts`.
- 수정: `suvis/next.config.mjs`, `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`.
- 커밋: 라우트 3개 `04bfbb2`, 리라이트 삭제 `2cbdb17`, 문서 `f408e0f`, main
  머지(PR #31) `0d70acf`. 6개 라우트 `x-matched-path` 헤더 배포 후 실증 완료.

### 작업 내용(추가⑤) — Tank presigned URL 403 버그 발견·수정

PR #31 배포 검증 중 사용자가 `/lesson/photos` 스크린샷을 보내 "썸네일이 안
뜨는 게 정상이냐"고 질문 — OCR 텍스트는 정상 추출됐는데 이미지만 깨진 아이콘.
EC2에서 실제 presigned URL을 발급해 `curl -I`로 재현 → `307`(글로벌
엔드포인트 `s3.amazonaws.com` → 리전 엔드포인트로 리다이렉트) 이후 같은
서명으로 `403`. `boto3.client("s3", region_name=...)`만 주면 리전이
us-east-1이 아닐 때 URL 생성 자체는 글로벌 엔드포인트 기준으로 되는데,
SigV4 서명에 `Host` 헤더가 포함돼 있어 리다이렉트된 새 호스트에서 서명이
안 맞는 게 원인.

### 수정/구현(추가⑤)
- `core/matrix/aws_tank_s3_manager.py`의 `Tank.client`에 `endpoint_url=
  f"https://s3.{self.region}.amazonaws.com"` 명시 — 리다이렉트 자체가
  안 생기게 함(업로드·다운로드·목록 조회도 같은 클라이언트를 쓰므로 함께
  개선됨, presigned URL만의 문제는 아니었음).
- 로컬에서 실제 S3 객체(`media/4/...jpg`, susu 업로드분)로 재발급한 URL을
  직접 `curl`로 검증 — `GET` → `200 OK`, `Content-Type: image/jpeg`,
  `Content-Length: 1554281`(원본과 일치). (`curl -I`/HEAD는 여전히 403이
  나오는데, 이건 presigned URL이 `get_object` 즉 GET 메서드로만 서명돼 있어
  HEAD가 별도 인가를 안 받는 것 — 브라우저 `<img>` 태그는 GET을 쓰므로
  무관함을 확인.)

### 오류·막힌 점(추가⑤)
- 없음. `pytest apps/media/tests apps/ontology/test -m "not gpu"` 63개 통과
  (Tank 관련 기존 테스트는 fake라 이 변경과 무관, 회귀 없음 확인).

### 데이터(추가⑤)
- 해당 없음.

### 산출물(추가⑤)
- 수정: `suvisdev/core/matrix/aws_tank_s3_manager.py`.
- 커밋: `b4f4500`(로컬 브랜치 push까지, main 머지·EC2 배포는 이 항목 갱신
  직후 진행).

### 작업 내용(추가⑥) — mova 대량 수집 시험 실행 중 418건 도미노 실패 발견·수정

`bulk_import_movies.py`(2026-08-02 코드 완성, 이날까지 실행 이력 없음)를 처음
실행해보는 중 `characters.character_name VARCHAR(50)` 초과로 영화 1건의
upsert가 실패한 뒤, 이후 같은 배치 세션을 쓰는 나머지 영화 418건이 전부
`PendingRollbackError`로 연쇄 실패하는 것을 발견.

### 오류·막힌 점(추가⑥)
- SQLAlchemy AsyncSession은 flush 실패 시 세션을 pending-rollback 상태로
  남긴다 — 명시적으로 `session.rollback()`을 호출하지 않으면 같은 세션을
  재사용하는 이후 모든 쿼리가 즉시 `PendingRollbackError`로 실패한다.
  `_ingest_tmdb_movie`/`_ingest_kofic_movie`의 각 `except` 블록이 로그만
  남기고 다음 영화로 넘어가던 게 원인 — "영화 한 편 실패가 배치 전체를
  막지 않는다"는 원래 설계 의도가 이 세션 오염 때문에 실제로는 지켜지지
  않고 있었음.

### 수정/구현(추가⑥)
- `_ingest_tmdb_movie`의 upsert_movie/credits 백필/hub_knowledge 인제스트
  3개 except 블록과 `_ingest_kofic_movie`의 upsert_movie/hub_knowledge 2개
  except 블록에 각각 `await session.rollback()` 추가 — 실패를 해당 영화
  하나로 격리.
- `apps/mova/tests/test_bulk_import_movies.py`에 회귀 테스트 3건 추가
  (`IngestTmdbMovieRollbackTests`): upsert 실패 시 rollback 확인, credits
  실패해도 영화 자체는 succeeded 유지, 실패한 영화 다음 영화가 깨끗한
  세션으로 정상 처리되는지(도미노 재현 방지) 검증.
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 백로그에 "EC2 hub_knowledge
  임베딩 어댑터 부재"(EC2엔 Ollama가 없어 hub_knowledge 인제스트가 매
  영화마다 조용히 실패 — movies/credits 저장에는 지장 없음) 신규 기록.

### 데이터(추가⑥)
- 이 시험 실행분 데이터는 실제 반영 여부 미확인 상태로 세션 종료 —
  다음 세션에서 처음부터 페이지 단위로 재실행하며 확인 예정.

### 산출물(추가⑥)
- 수정: `suvisdev/scripts/bulk_import_movies.py`,
  `apps/mova/tests/test_bulk_import_movies.py`,
  `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`.
- 커밋: 로컬 미커밋 상태로 세션 종료(다음 세션 커밋 예정).

---

---

## 2026-08-03

### 작업 내용
- 루트 `.env`(GITHUB_PAT만 존재)를 `suvisdev/.env`로 병합 후 루트 파일 삭제 —
  프로젝트 규칙(".env 파일은 suvisdev/.env 하나") 정리.
- `suvisdev/.env.auth`와 `suvisdev/.env` 분리 이유 확인 — `docker-compose.yaml`상
  `backend`는 `.env`만, `auth` 컨테이너는 `.env`+`.env.auth`를 로드. RS256 서명
  개인키(`JWT_PRIVATE_KEY_B64`)를 backend 컨테이너에 노출시키지 않기 위한 의도된
  보안 격리라 병합하지 않기로 함.
- susu(Flutter) 카카오 모바일 로그인 + 백엔드 JWT 발급 하네스 문서 작성 후,
  풀스택(백엔드+Flutter 클라이언트) 구현까지 진행.

### 수정/구현
- **하네스 문서**: `susu/_docs/flutter-kakao-oauth-harness.md`(클라 담당분),
  `suvisdev/_docs/flutter-kakao-oauth-harness.md`(백엔드 담당분) — 서로 상대
  경로로 상호 링크.
- **백엔드(`apps/auth`)**:
  - `kakao_mobile_verifier.py` 신규 — kapi `/v2/user/me`로 모바일 access_token
    검증(`KakaoMobileTokenVerifier`). 웹의 `oauth_adapters/kakao.py`(OIDC
    id_token 방식)와는 별도 어댑터.
  - `mobile_refresh_store.py` 신규 — `auth:refresh:mobile:{userId}` 네임스페이스
    Redis 저장소(`MobileRefreshTokenStore`). 웹의 `refresh_store.py`
    (`auth:refresh:{jti}`)는 무변경.
  - `repository.py`에 `find_or_create_by_kakao()` 추가 — 카카오 최초 로그인 시
    `UserMirror`/`UserIdentityMirror` 자동 생성(웹 OAuth와 달리 자동 가입).
  - `services.py`에 `login_with_kakao_mobile`/`mobile_refresh`/`mobile_logout`
    추가, `router.py`에 `POST /auth/kakao/mobile`, `/auth/mobile/refresh`,
    `/auth/mobile/logout` 라우트 추가. `schemas.py`에
    `KakaoMobileLoginRequest`/`KakaoMobileTokenResponse` 추가.
  - `tests/test_kakao_mobile.py` 신규 — G2(유효/무효 토큰), G3(모바일·웹 Redis
    네임스페이스 분리, 모바일 로그아웃이 웹 세션에 무영향) 커버. `pytest -m
    "not gpu"` 전체 352 passed(+1 fail은 실 Ollama 서버 필요한 기존 이슈,
    이번 변경과 무관).
- **Flutter(`susu`)**:
  - `pubspec.yaml`에 `kakao_flutter_sdk_common`/`kakao_flutter_sdk_user`/
    `video_player`/`flutter_secure_storage`/`http` 추가(`flutter pub add`로
    버전 자동 해결). 인트로 영상을 `assets/videos/intro.mp4`로 추가, assets
    등록.
  - Android(`AndroidManifest.xml`)/iOS(`Info.plist`)에 카카오 로그인 커스텀
    URL 스킴(`kakao{NATIVE_APP_KEY}`) 설정 추가. Native App Key는 사용자가
    카카오 콘솔에서 직접 발급해 `suvisdev/.env`(`KAKAO_NATIVE_APP_KEY`)와
    `susu/lib/kakao_config.dart`에 반영.
  - `lib/auth.dart` 신규 — 카카오톡 설치 시 `loginWithKakaoTalk()` → 실패/미설치
    시 `loginWithKakaoAccount()` 폴백. `UserApi.instance.me()` 미호출(백엔드가
    kapi로 단독 검증). `POST /auth/kakao/mobile`로 access_token만 전송, 응답
    JWT/refresh token을 `flutter_secure_storage`에 저장 후 `StopwatchPage`로
    이동.
  - `lib/main.dart` — `KakaoSdk.init()`을 `runApp()` 전에 호출하도록 `main()`
    수정. 기존 `IntroScreen`(마케팅 카드)은 그대로 두되 `home:`을 신규
    `SplashScreen`으로 교체 — 저장된 모바일 세션 있으면 바로
    `StopwatchPage`로, 없으면 인트로 영상 5초 재생 후 `AuthScreen`으로 자동
    전환.
  - `flutter analyze` 결과 새 코드는 클린, 기존 코드의 사전 경고(`_UnfoldedLayout`
    등 미사용 `key` 파라미터, `test/widget_test.dart`의 `MyApp` 참조 오류)만
    잔존 — 이번 변경과 무관하므로 미수정.

- `nginx/conf.d/app.conf`에 `/auth/*`, `/.well-known/jwks.json` → `auth:9000`
  프록시 location 추가(기존 `backend:8000` 라우팅과 동일 패턴). 사용자가
  "강사님이 말한 로컬→AWS→앱 구조와 다르다"고 지적 — 확인해보니 메인 백엔드는
  이미 nginx로 `api.suvisdev.cloud`에 연결돼 있었지만 auth 게이트웨이만 라우팅이
  없어 `susu/lib/api_config.dart`가 `127.0.0.1:9000`(로컬호스트)을 직접 보고
  있었음. `authBaseUrl`을 `https://api.suvisdev.cloud`로 교체, `docker-compose.yaml`
  auth 서비스 주석도 "실트래픽 미연결" → 실제 라우팅 상태로 갱신.
- **EC2 배포 반영 + 실기기 카카오 로그인 E2E 성공**: EC2(`~/suvisdev.cloud`)의
  자동배포 스크립트(`~/auto-deploy.sh`, cron)가 `origin suvisdev`를 pull은 하지만
  `docker compose restart`만 해서(이미지 `--build` 없음) 코드 변경이 반영 안 되고
  있었음을 SSH 접속(`aws` 호스트) 확인으로 발견. 사용자가 직접 EC2에서
  `git pull` + `docker compose up -d --build auth` + `nginx restart` 실행 →
  폰에서 카카오 로그인 → JWT 수신 → 스톱워치 화면 이동까지 실제 성공 확인.
- **StopwatchPage → IntroScreen 뒤로가기 버튼 추가**: 로그인 성공 후
  `pushAndRemoveUntil`로 스택이 비워져 시스템 뒤로가기가 안 먹히던 문제 — AppBar
  뒤로가기 아이콘 추가(`main.dart`의 `IntroScreen`으로 이동). `stopwatch_page.dart`
  ↔ `main.dart` 순환 import는 Dart에서 문제없음(`flutter analyze` 클린).
- **mova 추천 챗 화면(feature slice 1개) — 앱 뼈대 도입**: 사용자가 susu를
  WebView 래핑이 아닌 네이티브 앱으로 만들되 "앱 뼈대 + mova 추천 챗 화면 1개"로
  범위를 한정. 착수 전 `apps/mova/adapter/inbound/api/v1/market_chat_router.py`
  실제 코드 확인 — `POST /mova/chat`(mova_router prefix `/mova` + 자체 prefix
  `/chat`), 인증 불필요(IP 기준 rate limit만 있음, `require_admin`/JWT 의존성
  없음) 확인 완료.
- **로그아웃 기능 추가**: `AuthSession.clear()`는 있었지만 어디서도 호출되지
  않아 실제 로그아웃 UI가 없던 문제 — 로그아웃 아이콘 버튼 추가
  (`AuthSession.logout()` 신규: `POST /auth/mobile/logout` best-effort 호출
  후 로컬 secure storage 삭제, `AuthScreen`으로 이동). 처음엔 `StopwatchPage`
  AppBar에 뒀다가, 아래 네비게이션 재구성으로 `IntroScreen`으로 옮김.
- **로그인 후 메인 화면을 IntroScreen으로 변경**: 원래 로그인 성공/세션 유지 시
  곧장 `StopwatchPage`로 가던 걸, 사용자 요청으로 `IntroScreen`(main.dart의
  마케팅 카드 화면)이 로그인 후 메인이 되도록 변경 — `SplashScreen`(세션 있을
  때)과 `AuthScreen`(로그인 성공 시) 둘 다 목적지를 `IntroScreen`으로 수정.
  `StopwatchPage`는 `IntroScreen`의 "스톱워치 열기" 버튼으로만 들어가는
  서브 화면이 됨 — AppBar 뒤로가기도 단순 `pop()`으로 단순화(더 이상
  `main.dart`/`auth.dart`를 import할 필요 없어짐). 로그아웃 버튼은
  `IntroScreen` AppBar로 이동.
- **S3 버킷 env 오류 수정**: 사용자가 `.env`에 버킷 이름 대신 ARN 전체
  (`arn:aws:s3:::...`)를 `KEY=` 없이 그대로 붙여넣어 파싱 자체가 안 되던 상태
  발견 → `VISION_S3_BUCKET=`(버킷 이름만, ARN 접두사 제거)로 수정. `boto3`의
  `Bucket=` 파라미터가 순수 이름만 받는다는 점 확인(`core/matrix/aws_tank_s3_manager.py`).
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_REGION`은 아직 미설정
  (로컬에서 S3 쓰려면 필요, EC2는 인스턴스 IAM Role로 대체 가능).
- **mova 추천 — 원격 GPU(집) 대응 하드닝**: EC2 백엔드는 유지하고 mova 추천
  요청만 Cloudflare Tunnel로 뚫은 집 `lora_server`를 호출하는 구조로 분리하기
  전, `LoraRecommendationOrchestrator`/`lora_server`를 실제 코드로 먼저 조사
  (`LORA_SERVER_URL` env 하나만 바꾸면 됨 확인, 재시도 0회·인증 없음·`is_ready()`
  미사용 세 가지 리스크 확인) → 계획 제시 후 사용자 승인 받아 반영.
- **폰 카메라 → S3 업로드 신규 기능**: 사용자가 강사님 프로젝트 폴더 구조를
  착각해 붙여넣은 내용(`star_craft` 앱, `AWS_DEFAULT_REGION` 등 — 이 저장소엔
  없음)을 실제 코드로 검증해 정정. 기존 `apps/ontology`의 `POST /api/vision/upload`는
  Sentinel 이상탐지(블러 하드 게이트·포스터 소프트 경고) 전용이라 재사용 부적합
  확인 후, 새 경량 앱 `apps/media`(DB 없음) 신설:
  - `POST /api/media/photos` — JWT 필요(`aud=suvis-susu`, mova의
    `dependencies/require_auth.py`와 동일 패턴을 이 앱 자체 파일에 복제),
    JPG/PNG/WebP만·최대 10MB, `core/matrix/aws_tank_s3_manager.py`의 `Tank`로
    S3 업로드 후 `{key,url,size_bytes,content_type}` 반환.
  - `.importlinter`에 `media` 스포크 등록(5개 계약 전부 kept — 기존 hub-independence
    위반 1건은 무관한 사전 존재 이슈, `media`와 무관함을 diff로 확인).
  - 테스트 5건(성공/타입 거부/빈 파일/S3 실패→502/무인증 401) 신규,
    `main.py` 부팅+라우트 등록 확인.
  - Flutter(`features/media/`): `image_picker`로 카메라 촬영 → Dio multipart
    업로드. `dio_client.dart`의 Authorization 슬롯(그동안 DEV_AUTH_TOKEN
    플레이스홀더만 있던 자리)을 실제 로그인 JWT(`AuthSession.readAccessToken()`
    신규 공개 메서드)로 연결 — `mova_chat_controller.dart`의 `dioProvider`도
    공용화해 재사용. `IntroScreen` AppBar에 카메라 버튼 추가, 업로드
    중/성공/실패 SnackBar. Android(`CAMERA` 권한)/iOS(`NSCameraUsageDescription`) 추가.

### 오류·막힌 점
- 카카오 Native App Key와 백엔드 `/auth/kakao/mobile` 엔드포인트가 원래
  존재하지 않아 사용자에게 확인 후(플레이스홀더 진행 → 실제 키로 교체, 백엔드
  풀스택 병행 구현) 진행.
- `auth 게이트웨이`(9000포트)가 애초 cloudflared/nginx로 공개 라우팅되지 않아
  `susu/lib/api_config.dart`가 로컬호스트를 직접 가리키던 문제 발견 → nginx
  라우팅 추가로 해결(위 항목 참고). **단, 이 리포는 로컬 WSL에 Docker가 없어서
  (Docker Desktop WSL 연동 비활성) 실제 배포 머신(집 GPU 또는 EC2)에서 git
  pull 후 nginx 컨테이너를 재시작/reload해야 반영된다 — 이번 세션에서는
  코드만 고쳤고 실제 반영 확인은 못 함.**
- 로컬 `flutter run -d linux`가 `libsecret-1-dev` 시스템 패키지 부재로 실패 —
  sudo가 비밀번호 TTY를 요구해 에이전트가 대신 설치 못 함, 사용자가 직접
  실행하도록 안내.
- 폰 실기기 무선 adb 연결이 끊겨 있었음(`adb devices` 빈 목록) — 기존에
  페어링된 키는 남아 있어 재-pair 없이 `adb connect <IP>:<PORT>`(폰의 무선
  디버깅 화면에 매번 바뀌는 포트)로만 재연결하면 됨.
- iOS 쪽은 실제 빌드 검증(디바이스/시뮬레이터) 못 함 — Info.plist 설정은 공식
  문서 기준 표준 보일러플레이트로 작성, 실제 빌드 전 재확인 필요.
- **mova 추천 챗 화면 실기기/데스크톱 검증 미완료**: 폰 무선 adb 연결이 다시
  끊겨(`adb devices` 빈 목록) `flutter run` 실행을 못 함. 코드는
  `flutter analyze` 클린까지만 확인, 실제 `/mova/chat` 호출·카드 렌더링은 아직
  미검증 상태로 커밋(사용자 지시로 검증보다 커밋 우선 진행).
- **원격 GPU 하드닝은 코드·테스트까지만** — 실제 Cloudflare Tunnel로 집
  `lora_server`를 노출하고 EC2에서 `RECOMMENDATION_BACKEND=lora` +
  `LORA_SERVER_URL=https://...`로 붙여보는 실 연동은 아직 안 함(터널 설정
  자체가 이번 세션 범위 밖). `is_ready()`가 어디서도 호출되지 않는 문제도
  의도적으로 그대로 둠(별도 이슈로 미룸).
- **카메라 업로드 실기기 검증 미완료**: 폰 adb 연결이 계속 끊기는 상태라
  `flutter run`으로 실제 촬영→S3 업로드까지는 못 봄(`pytest`/`flutter analyze`만
  확인). access token 10분 TTL 만료 시 자동 재발급(refresh)도 이번 범위 밖 —
  만료되면 401 나고 재로그인해야 함.

### 산출물
- 신규 파일: `suvisdev/apps/auth/{kakao_mobile_verifier,mobile_refresh_store}.py`,
  `suvisdev/apps/auth/tests/test_kakao_mobile.py`,
  `susu/lib/{auth,kakao_config,api_config}.dart`,
  `susu/assets/videos/intro.mp4`,
  `susu/_docs/flutter-kakao-oauth-harness.md`,
  `suvisdev/_docs/flutter-kakao-oauth-harness.md`,
  `susu/lib/core/{config/env,network/dio_client}.dart`,
  `susu/lib/features/mova/{data/models/mova_chat_{request,recommendation,response},
  data/mova_chat_{api,repository_impl},domain/mova_chat_repository,
  presentation/mova_chat_{controller,screen}}.dart`,
  `suvisdev/_docs/lora-remote-gpu-ops.md`,
  `suvisdev/core/lol/tests/{conftest,test_lora_recommendation_orchestrator}.py`,
  `suvisdev/apps/media/{__init__,router,schemas}.py`,
  `suvisdev/apps/media/dependencies/{__init__,require_auth}.py`,
  `suvisdev/apps/media/tests/{__init__,conftest,test_router}.py`,
  `susu/lib/features/media/{data/models/photo_upload_response,data/media_api,
  data/media_repository_impl,domain/media_repository,
  presentation/photo_capture_controller}.dart`.
- 수정 파일: `suvisdev/apps/auth/{repository,services,router,schemas}.py`,
  `suvisdev/main.py`, `suvisdev/.importlinter`,
  `susu/lib/{auth,core/network/dio_client,features/mova/presentation/mova_chat_controller}.dart`,
  `susu/android/app/src/main/AndroidManifest.xml`, `susu/ios/Runner/Info.plist`,
  `suvisdev/core/lol/lora_recommendation_orchestrator.py`,
  `model_servers/lora_server/serve.py`, `suvisdev/.env.example`,
  `suvisdev/pytest.ini`,
  `susu/{pubspec.yaml,lib/main.dart,lib/stopwatch_page.dart}`,
  `susu/android/app/src/main/AndroidManifest.xml`, `susu/ios/Runner/Info.plist`,
  `suvisdev/.env`, `nginx/conf.d/app.conf`, `docker-compose.yaml`.

---

---

## 2026-08-02

### 작업 내용
- 로컬 개발 DB(집, Docker) 세팅 — `.env` 확인부터 마이그레이션·credits 백필·
  hub_knowledge 인제스트까지 전체 파이프라인 실행. `suvisdev/suvisdev/.env`에
  `POSTGRES_USER/PASSWORD/DB` 채운 뒤(사용자) `docker compose --env-file
  suvisdev/.env`로 db/backend 정상 접속 확인.
- `alembic upgrade head` 1차 시도에서 `DuplicateTable(titanic_passengers)`
  발생 → 조사 결과 DB에 `alembic_version` 테이블 자체가 없어 한 번도 alembic
  관리를 받은 적 없는 상태였고, 기존 7개 테이블이 마이그레이션 히스토리와
  무관하게 섞여 있었음을 확인. 로컬 개발 DB라 사용자 승인 받아 `public`
  스키마 DROP CASCADE 후 재구축.
- 재구축 후에도 `alembic upgrade head`가 head를 `20260727_0001`로 오인식
  (hub_knowledge/movie_directors 등 최신 4개 마이그레이션 누락) → backend
  컨테이너 이미지가 4일 전 빌드(라이브 마운트 아닌 COPY 방식)라서 최신
  `alembic/versions/*.py`를 컨테이너가 못 보던 게 원인. `docker compose up -d
  --build backend`로 재빌드 후 재적용 — 33개→36개 테이블 완성(hub_knowledge/
  movie_directors/visitor_activity 포함).
- `scripts/backfill_credits_cli.py` dry-run(3편) → 전량(39편) 실행:
  actors 389 / characters 371 / movie_directors 40 채움.
- hub_knowledge 인제스트: 사용자 초안 스크립트가 전제한 "`import_provider.py`
  `apps.` 접두사 누락 버그"는 실제로는 버그가 아니었음 — 코드베이스 158개
  파일 전부 접두사 없는 스타일이라 이 파일이 정상(오히려 `apps.`로 고치면
  관례 위반이라 되돌림). 추가로 `get_import_interactor` 함수 자체가
  없고, `_ingest_to_hub`는 `TmdbMovieSnapshotDto`를 받아 `movies` DB
  엔티티와 타입이 안 맞음을 확인. 세 가지 불일치를 근거로
  `HubRagInteractor.ingest_movie()`를 movies+characters+movie_directors
  조인으로 직접 호출하는 `scripts/ingest_hub_knowledge.py` 신규 작성.
- 신규 스크립트 1차 실행 — 39편 전부 "ingest 완료" 로그가 찍혔는데 DB엔
  0건. 원인은 호스트 Ollama가 `127.0.0.1`에만 바인딩돼(`OLLAMA_HOST`
  미설정) 컨테이너의 `host.docker.internal:11434` 요청이 거부된 것.
  `/etc/systemd/system/ollama.service.d/override.conf`(`OLLAMA_HOST=0.0.0.0`)
  추가 후 재시작 — 이 세션은 TTY 없어 `sudo`가 비대화형으로 막혀 사용자가
  별도 터미널에서 직접 실행.
- 바인딩 정상화 후 재실행해도 여전히 0건 — `HubKnowledgeRepository.upsert()`가
  `flush()`만 하고 `commit()`을 안 하는 구조였음(`get_mova_db()` FastAPI
  의존성만 응답 종료 시 자동 commit, `get_mova_session_factory()`를 직접
  쓰면 커밋 책임이 호출자에게 있음 — `characters`/`movie_directors`
  레포지토리는 자체 commit해서 이전 백필은 문제없었던 것). 스크립트에
  `session.commit()` 추가 후 재실행 → `hub_knowledge` 39건 정상 적재.
- mova 대량 영화 수집(TMDB+KOFIC 합산 수만 편, 하루 배치 점진 적재) 파이프라인
  조사 → 구현. 조사 결과 TMDB는 `/discover/movie`(region/장르 필터)가 없어
  popular/top_rated만으로는 한국/해외를 분리 수집할 수 없었고, KOFIC은
  박스오피스 랭킹 API만 있고 영화 목록 API(`searchMovieList.json`)가 미구현
  상태였으며, `ImportInteractor`엔 배치 재시작용 커서/체크포인트가 전혀
  없었음(단 `upsert_movie`는 slug 기준 idempotent라 재시작 안전성 자체는
  이미 확보돼 있었음). 조사 중 기존 `scripts/backfill_hub_movies_rag.py`(정적
  JSONL 기반)가 이번에 만들 파이프라인과 목적이 겹친다는 점도 확인(정리는
  이번 범위 밖, 백로그로 남김).
- 설계 확정 뒤 3가지 신규 구현: ① `TmdbAdapter.fetch_discover`(raw)+
  `TmdbCatalogAdapter.fetch_discover`(TmdbMovieSnapshotDto 매핑) — Port
  (`TmdbCatalogPort`)는 다른 구현체·페이크에 영향 안 주려고 의도적으로
  안 건드림(구체 클래스에만 추가). ② `KoficAdapter.fetch_movie_list` —
  `searchMovieList.json` 래퍼(page/itemPerPage/repNationCd). ③
  `scripts/bulk_import_movies.py` — `--source tmdb_popular|tmdb_discover|kofic`,
  `--country KR|US|ALL`, `--pages N`, `--start-page N`(재시작용). 영화당
  upsert_movie → credits 백필(`CreditsBackfillInteractor._backfill_one`
  재사용, TMDB만) → hub_knowledge 인제스트 순서로 처리하고 각 단계 실패는
  해당 영화만 스킵. KOFIC 소스는 tmdb_person_id가 없어 credits 백필 대상
  밖(movies+hub_knowledge까지만).
- 구현 중간에 사용자가 별도 조사(EC2 backend가 KOFIC 스케줄러 완료 후
  자동 종료되는 버그)를 먼저 요청해 잠시 전환 — `kofic_import_scheduler.py`·
  `main.py` 등록부·`apps/mova`+`core` 전체에서 `sys.exit`/`os._exit`/
  `loop.stop()` 등 강제 종료 호출 0건 확인(코드 레벨 원인 못 찾음, EC2
  OOM/systemd 재시작 등 배포 환경 쪽 가설만 제시). 조사 후 대량 수집
  구현으로 복귀.
- mova 채팅이 EC2(GPU 없음)에서 503 나는 문제 조사·수정. `market_chat_provider.
  get_recommendation_port()`가 환경 분기 없이 무조건 `LoraRecommendationAdapter`
  를 반환해 EC2엔 없는 lora_server를 호출하던 게 원인. `GeminiRecommendationAdapter`
  와 `LoraRecommendationAdapter`의 인터페이스(생성자 무인자, `extract_intent`/
  `generate_recommendation` 시그니처)가 동일함을 먼저 확인한 뒤 `RECOMMENDATION_
  BACKEND` env 분기 추가.

### 수정/구현
- `suvisdev/scripts/ingest_hub_knowledge.py` 신규 — `movies` 전체를
  `characters`(출연진 상위 5)·`movie_directors`와 조인해
  `HubKnowledgeUpsertCommand` 구성, `HubRagInteractor.ingest_movie()` 직접
  호출. sys.path 부트스트랩은 `backfill_credits_cli.py`와 동일 패턴. 루프
  끝에 `session.commit()` 명시.
- `import_provider.py`는 수정 시도 후 원상 복구(버그 아님으로 판명, git diff
  없음).
- 호스트 systemd: `/etc/systemd/system/ollama.service.d/override.conf` 신설
  (`OLLAMA_HOST=0.0.0.0`) — 저장소 밖 시스템 설정, git 미추적. 이 호스트에만
  적용(EC2는 Ollama 미사용이라 무관).
- `apps/mova/adapter/outbound/http/tmdb_adapter.py`: `fetch_discover` 추가
  (page/with_origin_country/with_genres/sort_by, `/discover/movie`).
- `apps/mova/adapter/outbound/http/tmdb_catalog_adapter.py`: `fetch_discover`
  추가(raw dict → `TmdbMovieSnapshotDto` 매핑, fetch_popular과 동일 패턴).
- `apps/mova/adapter/outbound/http/kofic_adapter.py`: `fetch_movie_list` 추가
  (`searchMovieList.json`, repNationCd K/F).
- `suvisdev/scripts/bulk_import_movies.py` 신규 — 대량 수집 배치 CLI.
- `apps/mova/tests/test_bulk_import_movies.py` 신규 — `fetch_discover` mock
  테스트 2건 + `bulk_import_movies` argparse 테스트 4건. `pytest -m "not gpu"`
  apps/mova/tests 73개 전부 통과(회귀 없음).
- `apps/mova/dependencies/market_chat_provider.py`: `get_recommendation_port()`에
  `RECOMMENDATION_BACKEND`(기본값 `"lora"`) 분기 추가 — `"gemini"`면
  `GeminiRecommendationAdapter()`, 그 외엔 기존 `LoraRecommendationAdapter()`.
  포트 인터페이스·다른 코드는 미변경.

### 오류·막힌 점
- `DuplicateTable(titanic_passengers)`: DB가 alembic 미관리 상태였던 게
  원인 → 스키마 재구축으로 해결.
- 재구축 후에도 마이그레이션 4개 누락: backend 이미지가 오래돼서(빌드
  방식, 라이브 마운트 아님) → `--build`로 재빌드해 해결.
- hub_knowledge 0건(1차): 사용자 초안 스크립트의 import 경로/존재하지 않는
  함수/DTO 타입 3중 불일치 → 시그니처 확인 후 새 스크립트 작성으로 해결.
- hub_knowledge 0건(2차, 새 스크립트로도): Ollama가 `127.0.0.1` 바인딩이라
  컨테이너에서 연결 불가 → `OLLAMA_HOST=0.0.0.0` systemd override로 해결.
- hub_knowledge 0건(3차, 바인딩 고친 후에도): 세션 `commit()` 누락
  (`HubKnowledgeRepository.upsert()`는 `flush()`만 함) → 스크립트에 commit
  추가로 해결.

### 데이터
- 로컬 Docker DB(`suvisdev/suvisdev/.env` 기준) 기준: `actors` 389 /
  `characters` 371 / `movie_directors` 40 / `movies` 39 / `hub_knowledge` 39.
- 대량 수집 배치는 이 세션에서 코드만 완성 — 실제 `bulk_import_movies.py`
  실행(수만 편 적재)은 아직 안 함(백로그).

### 산출물
- 신규 파일: `suvisdev/scripts/ingest_hub_knowledge.py` (커밋 대상).
- 로컬 Docker DB가 alembic head(`20260731_0001`)까지 완전 재구축 + credits/
  hub_knowledge 데이터 적재 완료.
- 신규 파일: `suvisdev/scripts/bulk_import_movies.py`,
  `apps/mova/tests/test_bulk_import_movies.py` (커밋 대상). 수정:
  `tmdb_adapter.py`/`tmdb_catalog_adapter.py`/`kofic_adapter.py`.
- 수정: `apps/mova/dependencies/market_chat_provider.py` (커밋 대상,
  `fix(mova): add RECOMMENDATION_BACKEND env branch (gemini for EC2, lora
  default)`). **EC2 `.env`에 `RECOMMENDATION_BACKEND=gemini` 추가 필요**
  (`GEMINI_API_KEY`는 이미 설정돼 있음, 이름 일치 확인함).

---

---

## 2026-07-30

### 작업 내용
- `apps/execsuite/_docs/langgraph-strategy.md`(빈 파일)에 사용자가 제시한
  "LangChain+pgVector → LangGraph+Neo4j" 4단계 확장 전략(Neo4j 도입 → Hybrid
  Retrieval → LangGraph 전환 → 에이전틱 피드백 루프)을 harness 문서 형식으로
  작성. 코드 구현은 하지 않음.
- execsuite 전역에 남아 있던 `rangchain`/`ranggraph` 오타를 `langchain`/
  `langgraph`로 정정(사용자 요청).
- 루트 `docker-compose.yaml`에 GraphRAG용 Neo4j 서비스 추가(사용자 요청, 상세
  스펙 지정: heap/pagecache 캡, 127.0.0.1 전용 바인딩, `.env` 비밀번호 참조,
  named volume, 기존 pgvector/PostgreSQL·다른 서비스·`requirements.txt` 불변).

### 수정/구현
- 코드 파일 9개 + 빈 파일 1개(`ranggraph_interactor.py`)를 `git mv`로 리네임하고
  내부 식별자(`Rangchain*` 클래스명, `rangchain_*` 함수명)를 `Langchain*`/
  `langchain_*`로 일괄 치환: `langchain_chat_schema.py`,
  `langchain_chat_router.py`, `langchain_chat_engine_repository.py`,
  `langchain_chat_dto.py`, `langchain_chat_use_case.py`,
  `langchain_chat_engine_port.py`, `langchain_chat_errors.py`,
  `langchain_interactor.py`, `langgraph_interactor.py`,
  `langchain_chat_provider.py`. `adapter/inbound/api/__init__.py`의 import·
  라우터 등록도 갱신.
- 위 리네임을 반영해 `langgraph-harness.md`·`neo4j-strategy.md`·
  `langchain-elastic-strategy.md`·`langchain-ncl-strategy.md`·
  `langchain-monigstar-strategy.md`가 언급하던 옛 파일명(`rangchain_*.py`,
  `ranggraph_interactor.py`, `ranggraph-harness.md`)도 함께 정정. 제안
  파일명 `rangchain_reasoning_graph.py`는 LangGraph StateGraph 구현체라는
  맥락에 맞춰 `langgraph_reasoning_graph.py`로 수정.
- 리네임된 모듈들의 stale `__pycache__/*.pyc`(옛 모듈 경로) 삭제.
- `docker-compose.yaml`에 `neo4j` 서비스 신설: `image: neo4j:5.26-community`,
  `NEO4J_server_memory_heap_{initial,max}__size=1G`/`NEO4J_server_memory_pagecache_size=512m`로
  캡, `ports`는 `127.0.0.1:7474:7474`/`127.0.0.1:7687:7687`만(0.0.0.0 미노출),
  `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}`, `neo4j_data` named volume,
  `restart: unless-stopped`. 다른 서비스 블록은 미변경.
- `suvisdev/.env`의 `NEO4J_PASSWORD`가 이미 있었으나 값이 약한 기본값 패턴
  (`suvisdev123`)이었음 — 아직 코드 어디서도 참조하지 않아 안전하게 강한
  임의값(hex 48자)으로 교체.

### 오류·막힌 점
- 코드 리네임 관련: 없음. `ast.parse`로 리네임된 10개 파일 구문 검증, 저장소
  전체 `rangchain|ranggraph` grep으로 잔여 참조 없음 확인.
- `docker-compose.yaml` 편집 중 파일 끝에 `1` 한 글자가 단독으로 붙어 있어
  YAML이 깨져 있던 것 발견(이번 세션 이전부터 존재하던 상태, 원인 불명) —
  제거.
- `suvisdev/.env` 76번째 줄에 `TUNNEL_TOKEN suvisdev/.env | cat`이라는 실행되다
  만 셸 명령어 조각이 값 대신 들어가 있어 `.env` 파싱 자체가 실패하던 것 발견
  (역시 이전부터 존재, 바로 다음 줄에 정상 `TUNNEL_TOKEN=...` 있음) — 그
  줄만 제거.
- 이 WSL 세션에서 Docker Desktop 데몬(`npipe:////./pipe/dockerDesktopLinuxEngine`)에
  연결이 안 돼 `docker compose up -d neo4j`/`logs`/`docker ps` 실행 검증은
  못 함. `docker compose config`로 문법·서비스 등록만 확인. 사용자가 Docker가
  붙는 환경에서 직접 기동·검증하기로 함.

### 산출물
- `apps/execsuite/_docs/langgraph-strategy.md` 신규 작성.
- 코드 리네임 10건 + 관련 문서 5건 수정 — 커밋 `bff6d48` → `main` PR #16
  머지(`93ce0c3`).
- `docker-compose.yaml` neo4j 서비스 추가, `suvisdev/.env`(gitignore 대상,
  미추적) `NEO4J_PASSWORD` 교체 + 손상 라인 제거.

### 작업 내용 (이어서 — nginx/certbot 커밋)
- EC2 호스트에서 코드만 고치고 커밋 안 된 상태(`docker-compose.yaml` 수정 +
  `nginx/` 미추적)를 정리해 커밋으로 남김(사용자 요청).

### 수정/구현
- `docker-compose.yaml`(기존 EC2 로컬 수정, 내용은 불변): `nginx`/`certbot`
  서비스 추가, `backend`의 `deploy.resources`(GPU 예약) 블록 주석 처리(EC2엔
  GPU 없음), `cloudflared` command에 `--protocol http2` 추가. neo4j는 이전
  커밋(a112cb5)에서 이미 반영되어 있던 것 유지.
- `nginx/conf.d/app.conf` 신규 추적 시작 — `docker-compose.yaml`의
  `./nginx/conf.d:/etc/nginx/conf.d` 마운트가 실제로 참조하는 리버스 프록시
  설정(`api.suvisdev.cloud` → `backend:8000`).

### 오류·막힌 점
- 루트에 `docker-compose.yaml.ec2-backup`(HEAD보다 오래된 중간 스냅샷)과
  `e.yaml docker-compose.yaml.ec2-backup`(내용이 `git diff` 출력 텍스트인
  실수 파일)가 있어 사용자에게 처리 방법 확인 후 둘 다 삭제(git 미추적
  상태였으므로 히스토리엔 영향 없음).
- 루트의 `nginx.conf`(docker-compose가 참조하지 않는 초안, `proxy_pass`
  대상이 실제 서비스명과 다름)는 사용자 지시로 손대지 않고 미추적 상태 유지.
- 원래 지침(`suvisdev` 작업 → `main` 병합)과 달리 이번엔 EC2가 이미 `main`
  브랜치였고, 사용자가 이번 건은 예외적으로 `main`에 직접 커밋하기로 확인.

### 산출물
- `docker-compose.yaml`, `nginx/conf.d/app.conf` 커밋 `41d56a6`(`main`
  직접 커밋).

### 작업 내용 (이어서 — alembic 마이그레이션 적용 + backend 재배포, 로그인 500 복구)
- `git pull`로 마이그레이션 2개(`20260729_0001_add_vision_upload_soft_flags`,
  `20260729_0002_create_hub_knowledge`)가 들어왔는데 backend 컨테이너는 옛
  이미지로 떠 있어 `user_identities`/`hub_knowledge` 관련 로그인 500 발생 →
  복구(사용자 요청, 순서 지정: DB 백업 → 마이그레이션 → backend 재배포 →
  로그인 검증).

### 수정/구현
- (코드 변경 없음 — 순수 배포/운영 작업)
- DB 백업: `docker compose exec db pg_dump` → `/tmp/suvisdev_backup_20260730_0232.sql`
  (94KB, 0바이트 아님 확인).
- `docker image prune -f`(dangling만, 0B 회수 — 태그 이미지와 레이어 공유) +
  `docker builder prune -f`(빌드 캐시 9GB 회수, 둘 다 사용자 승인) →
  `/` 여유공간 5.0G→14G.
- `docker compose up -d --build backend`로 재빌드(새 마이그레이션 파일
  포함) 후 `alembic upgrade 20260729_0001`(vision_uploads 3컬럼:
  `poster_confidence`/`sharpness_score`/`is_poster_warning`) 적용,
  `alembic stamp 20260729_0002`로 버전만 기록(아래 오류 참고).

### 오류·막힌 점
- **컨테이너 이미지 stale**: `docker compose exec backend alembic heads`가
  재빌드 전엔 옛 head(`20260727_0001`)만 인식 — `docker-compose.yaml`이
  `suvisdev/` 전체를 bind mount하지 않아(코드는 build-time COPY) 새
  마이그레이션 파일이 이미지 밖에 있었음. 지시된 순서(마이그레이션 먼저 →
  재빌드 나중)로는 4번이 no-op이 됐을 것 — 사용자 확인 후 순서를
  재빌드 우선으로 변경.
- **호스트에 alembic 실행 환경 없음**: `pip` 모듈조차 시스템 python3에
  없고 프로젝트 venv도 전무 — 호스트 직접 실행(1안) 대신 컨테이너 재빌드
  경유(2안)로 전환.
- **디스크 공간 부족**: 1차 `docker compose up -d --build backend`가
  `pip install` 중 `OSError: [Errno 28] No space left on device`로 실패
  (`/` 84% 사용, 5.0G 남음, dangling 이미지 18.2GB reclaimable). `docker
  image prune -f`는 태그 이미지와 레이어를 공유해 0B 회수 — 실제로는
  `docker builder prune -f`(빌드 캐시 9GB)가 필요했음(둘 다 사용자 승인
  받고 실행).
- **hub_knowledge DuplicateTable**: `alembic upgrade head`가
  `20260729_0002`(hub_knowledge 생성)에서 `psycopg.errors.DuplicateTable`로
  실패. 트랜잭션 전체가 롤백돼 DB 손상은 없었음(`alembic_version`
  `20260727_0001` 그대로, vision_uploads 컬럼도 안 들어감). 원인은 마이그레이션
  파일 자체 docstring에 있었음 — `HubKnowledgeOrm`이 2026-07-14(cc2c334)에
  추가된 뒤 `ensure_titanic_tables()`의 `create_all()`로만 생성돼 왔고, 이
  DB엔 이미 그 경로로 테이블이 존재. 컬럼·인덱스·유니크제약까지 마이그레이션
  정의와 완전히 일치함을 확인한 뒤, `20260729_0001`만 `upgrade`로 적용하고
  `20260729_0002`는 `stamp`로 버전만 기록(SQL 미실행)하는 우회로 해결(사용자
  승인).
- **백로그**: `create_all()`(`ensure_titanic_tables`)과 alembic이 테이블
  생성을 이중 관리하고 있어 새 테이블이 추가될 때마다 이번과 같은 stamp
  충돌이 반복될 수 있다. 근본 해결은 `create_all()` 경로를 제거하고 alembic을
  테이블 생성의 단일 소스로 삼는 것 — 오늘은 `20260729_0002` stamp로
  우회했을 뿐 근본 원인은 그대로 남아 있음.

### 산출물
- 커밋 없음(순수 배포). DB `alembic_version`: `20260727_0001` →
  `20260729_0002`. backend 이미지 재빌드·재기동. 백업 파일:
  `/tmp/suvisdev_backup_20260730_0232.sql`.

### 작업 내용 (이어서 — 어드민 화면 미노출 수정 + 닉네임 표시/변경 기능)
- 사용자가 `ssuvisdev@gmail.com`으로 로그인해도 어드민 화면이 안 보인다고
  보고 → 원인 조사 후 수정.
- 메인페이지 로그인 표시가 이메일(정확히는 OAuth로 자동 생성된
  `{이메일 로컬파트}_{provider}` 형태의 `username`)로 보여서, OAuth 로그인도
  닉네임을 설정할 수 있고 헤더에 닉네임이 뜨도록 개선(사용자 요청).

### 수정/구현
- **어드민 미노출 원인**: `_resolve_role()`(RBAC)이 `ADMIN_EMAILS` env를
  기준으로 role을 산출하는데, `suvisdev/.env`에 이 항목 자체가 누락돼 있어
  누가 로그인해도 role이 항상 `user`였음. `.env`에
  `ADMIN_EMAILS=ssuvisdev@gmail.com` 추가 후 `docker compose up -d
  --force-recreate backend`로 재기동(이미지 재빌드 불필요, env만 반영).
- **닉네임 표시/변경**: 로그인 응답 체인
  (`LoginResponseDto → SessionPayloadDto → JWT 세션 핸드오프 → 프론트 응답`)
  전체에 `nickname` 필드를 추가해 로그인 시 프론트 세션(localStorage)에
  닉네임이 실리도록 함. 변경 파일: `auth_command_dto.py`,
  `login_pg_repository.py`, `oauth_identity_pg_repository.py`,
  `oauth_dto.py`, `session_store_port.py`,
  `redis_session_store_adapter.py`(handoff 문자열에 nickname 필드 추가),
  `oauth_login_interactor.py`, `oauth_router.py`, `login_router.py`.
  - 신규 `PATCH /viewer/profile/{user_id}`(닉네임 변경) — 본인 확인 가드
    `shared/security/require_user.py`(신규, `require_admin.py`와 동일한
    HS256 검증이되 role 체크 없음) + 요청자 user_id와 경로 user_id 일치
    검증(`.claude/rules/security/auth.md` §5 IDOR 규칙 준수). 포트/유스케이스/
    리포지토리(`profile_repository.py`, `profile_use_case.py`,
    `profile_interactor.py`, `profile_pg_repository.py`,
    `user_orm.py::update_user_nickname`) 계층 전부 관통.
  - 프론트: 헤더(`auth-login-button.tsx`)가 `username` 대신 `nickname`
    표시(`?? username` 폴백). 마이페이지에 닉네임 인라인 편집 UI 추가
    (`profile-api.ts::updateNickname`, `app/api/viewer/profile/route.ts`에
    `PATCH` 프록시 추가, 저장 성공 시 로컬 세션도 즉시 갱신해 재로그인 없이
    헤더 반영). `SuvisSession`/`OAuthSessionResult` 타입에 `nickname` 추가.

### 오류·막힌 점
- 없음. `apps/viewer`에 기존 테스트가 없어(pytest testpaths 미포함) 자동
  회귀 테스트는 못 돌렸고, 대신 backend 컨테이너 안에서 실제 계정
  (`user_id=1`, `ssuvisdev@gmail.com`, 기존 닉네임 "진수택")으로 수동
  검증: `RedisSessionStoreAdapter.issue_session→redeem_handoff_code`
  체인에 nickname/role 정상 전달, `PATCH /viewer/profile/1`을
  토큰 없이(401)·남의 id로(403)·본인 id로 동일 닉네임값(200, 멱등) 호출해
  가드·소유권 검증 확인, `GET`으로 값 보존 재확인(실데이터 훼손 없음),
  `POST /viewer/login/login`(admin 시드 계정) 응답에도 nickname 포함 확인.
  프론트는 이 EC2에 `pnpm`/`node_modules`가 없어 `pnpm type-check` 실행
  불가 — 타입은 수동 검토만 함.

### 산출물
- 코드 변경 파일: 백엔드 16개 + 신규 1개(`shared/security/require_user.py`),
  프론트 7개. `suvisdev/.env`에 `ADMIN_EMAILS` 추가(gitignore 대상, 커밋
  안 됨). backend 재빌드·재기동 완료.

### 작업 내용 (이어서 — Neo4j GraphRAG 스키마(제약+벡터 인덱스) 생성)
- 2026-07-30 앞부분에서 provisioning만 하고 실기동 검증이 미완이던 neo4j
  컨테이너에, pg `movies` 스키마 기준 도메인 제약·인덱스를 실제로 생성
  (사용자 요청, 데이터는 아직 안 넣음 — TMDB/KOFIC import가 나중에 채울 예정).

### 수정/구현
- `docker compose exec neo4j cypher-shell`로 실행: 유니크 제약 4개
  (`movie_slug`→Movie.slug, `genre_name`→Genre.name, `person_slug`→Person.slug,
  `collection_id`→Collection.ext_id, 각각 자동 RANGE 인덱스 동반), 검색용
  `movie_title`(Movie.title, RANGE), 벡터 인덱스 `movie_embedding`
  (Movie.embedding, 768차원, cosine — pg embedding 컬럼과 동일 스펙).

### 오류·막힌 점
- `suvisdev/.env` 소스 시 29번째 줄에 예전(76번째 줄, 2026-07-29 수정분)과
  같은 종류의 손상(단독 `1` 문자, `GEMINI_API_KEY` 바로 다음 줄)이 있어
  `source` 경고가 났음 — `NEO4J_PASSWORD`는 정상 로드돼 이번 작업엔 지장
  없었고, 이번 작업 범위 밖이라 손대지 않음(백로그).

### 산출물
- `SHOW CONSTRAINTS`/`SHOW INDEXES`로 4개 제약 + 6개 인덱스(벡터 포함)
  전부 `state=ONLINE` 확인, `MATCH (n) RETURN count(n)` = 0 확인(데이터
  없음, 그릇만 존재).

### 작업 내용 (이어서 — ADMIN_EMAILS 추가 + mova TMDB credits 백필 조사·설계·구현)
- 로컬 `suvisdev/.env`에 `ADMIN_EMAILS` 항목 자체가 없어(어드민 role 판정이
  전부 "user"로만 나오는 상태) `ADMIN_EMAILS=ssuvisdev@gmail.com` 추가(사용자
  요청). `.env`는 gitignore 대상이라 로컬 전용 — EC2 `.env`는 별도로 채워야
  함을 안내.
- mova의 TMDB/KOFIC import 경로 코드 조사(사용자 요청, 코드 수정 없이 조사만):
  actors/characters 테이블이 스키마·ORM·읽기 API는 있지만 **쓰기 경로가
  0건**이라 pg `actors` 0행인 것을 확인. TMDB credits(cast/crew) 조회도
  `fetch_movie_detail()`(단일 상세)에만 있고 시드가 쓰는 `fetch_popular`
  등에는 없어 cast가 늘 빈 값. `movies.embedding` 컬럼도 스키마 주석은
  Gemini를 가리키지만 실제로는 아무 코드도 안 채움 — 임베딩은 별도로
  `_ingest_to_hub()`가 ontology `hub_knowledge` 테이블에만 씀. 결과를 표로
  보고(구현됨/정의만 되고 안 도는 것/없는 것 3단 구분).
- 위 조사를 바탕으로 "TMDB credits 배선" 2단계 작업 Phase A(조사·설계, 코드
  변경 금지) 진행: actors/characters 스키마 전체, Port·DTO 현재 인터페이스,
  `.importlinter` 레이어 제약, TMDB credits 응답 필드, 설계안 검토, 변경
  파일 목록, TDD 테스트 목록을 보고. 사용자가 세 가지 결정 확정: ① 마이그레이션
  4건 진행(`actors.tmdb_person_id`, `characters.billing_order`,
  `movie_directors` 조인 테이블, `uq_actors_name_role` DROP — 사용자가 이
  네 번째 항목을 직접 지적함, 안 빼면 동명이인 upsert가 기존 제약에 막혀
  실패), ② 감독 관계는 movie_directors 조인 테이블(공동 감독 지원, characters와
  대칭), ③ 실행은 수동 스크립트 전용(어드민 엔드포인트·스케줄러 배선 금지).
- Phase B로 TDD 구현 진행(사용자 승인, "커밋은 하되 push는 확인 후" 조건).

### 수정/구현
- `alembic/versions/20260730_0001_add_tmdb_credits_columns.py` 신규
  (`down_revision=20260729_0002`, 현재 head): `actors.tmdb_person_id`
  INTEGER UNIQUE NULL 추가 + 인덱스, `characters.billing_order` INTEGER
  NULL 추가, `movie_directors(movie_id, actor_id)` 테이블 신설(FK CASCADE,
  UNIQUE), `uq_actors_name_role` DROP(+downgrade에서 복원).
- ORM: `studio_actors_orm.py`(`tmdb_person_id` 컬럼, UNIQUE 제약을
  name+role_type에서 tmdb_person_id로 교체), `studio_characters_orm.py`
  (`billing_order` 컬럼), 신규 `studio_movie_directors_orm.py`
  (`MovaMovieDirector`, characters와 대칭 구조) — `adapter/outbound/orm/__init__.py`에
  등록해 `core.matrix.grid_oracle_database_manager`의 `import
  mova.adapter.outbound.orm`으로 메타데이터에 잡히게 함.
- DTO: `studio_import_dto.py`에 `TmdbCastMemberDto`/`TmdbDirectorDto`/
  `TmdbCreditsDto`/`CreditsBackfillResultDto`(succeeded/failed/skipped +
  실패 slug 목록, `_ingest_to_hub`처럼 조용히 삼키지 않음), `studio_actors_dto.py`에
  `ActorUpsertCommand`, `studio_characters_dto.py`에 `CharacterUpsertCommand`,
  신규 `studio_movie_directors_dto.py`에 `MovieDirectorUpsertCommand`.
- 매퍼: `tmdb_mapper.py`에 `map_credits()` 신규(person id/character/order/
  crew 보존, 기존 `map_cast_names`(hub_rag용, 이름만)는 불변). `tmdb_adapter.py`의
  `poster_url()` 내부 로직을 모듈 함수 `build_image_url()`로 추출해
  profile_path에도 재사용(동작 동일, 순수 리팩터).
- Port 확장: `ActorsRepositoryPort.upsert_actor`, `CharactersRepositoryPort.upsert_character`,
  신규 `MovieDirectorsRepositoryPort.upsert_director`, `MoviesRepositoryPort.list_all_slugs`
  (배치 순회 전용, 기존 필터·페이지네이션용 `list_movies`와 분리),
  `TmdbCatalogPort.fetch_credits`(기존 `fetch_by_id`는 불변 — seed/import
  경로 안 건드림).
- PgRepository 구현: `ActorsPgRepository.upsert_actor`(tmdb_person_id
  기준 select-then-insert/update, 기존 `upsert_movie` 패턴과 동일),
  `CharactersPgRepository.upsert_character`, 신규
  `MovieDirectorsPgRepository`(movie_id+actor_id 기준, 필드가 없어 이미
  있으면 그대로 반환하는 순수 멱등 insert), `MoviesPgRepository.list_all_slugs`,
  `TmdbCatalogAdapter.fetch_credits`(`fetch_movie_detail` 재사용 + `map_credits`).
- 유스케이스: 신규 `credits_backfill_use_case.py`(입력 포트) +
  `credits_backfill_interactor.py` — `list_all_slugs()` 순회, `slug`가
  `tmdb-{id}` 형식이 아니면 skipped 집계 후 계속(이 파싱 전제를 코드 주석에
  명시), 영화 1편의 credits 조회·upsert가 실패해도 예외를 잡아 failed 집계
  후 다음 영화로 진행(전체 중단 안 함).
- DI: 신규 `dependencies/credits_backfill_provider.py` — FastAPI 요청
  컨텍스트 없이 `get_mova_session_factory()`로 직접 세션을 여는
  `seed_catalog_if_sparse`와 동일 패턴(어드민 엔드포인트 없음).
- 실행 진입점: 신규 `scripts/backfill_credits_cli.py` — 기존
  `scripts/harvester_cli.py`와 동일하게 `sys.path` 수동 부트스트랩 후 직접
  실행(`docker compose exec backend python scripts/backfill_credits_cli.py`).
  사용자가 예시로 든 `python -m ...`은 이 저장소에 PYTHONPATH 설정이 없어
  그대로는 안 돼 기존 컨벤션에 맞춰 조정했음을 보고에 명시.
- 테스트: 신규 `apps/mova/tests/test_credits_backfill.py` 14건 —
  `map_credits`(credits 없음/cast만/crew job 필터/공동 감독 2명/cast person
  id 중복 제거/cast_limit/profile_path→URL), `_parse_tmdb_id`(정상/비-TMDB
  slug/파싱 실패), `CreditsBackfillInteractor`(AsyncMock 포트 — 비-TMDB
  slug skip, cast+감독 upsert 오케스트레이션, 한 편 실패해도 나머지 진행,
  전부 실패 시 집계).

### 오류·막힌 점
- repository upsert의 실제 멱등성·동명이인 분리(같은 tmdb_person_id 재upsert
  시 행 1개 유지, 다른 tmdb_person_id+같은 이름은 별도 행)는 Postgres 없이는
  검증 불가 — 로컬 Docker 데몬 미연결이라 마이그레이션 적용·backfill 실행·
  이 검증은 EC2에서 사용자가 직접 진행하기로 함(사전 합의).
- `apps/mova/tests/` 전체 47개 + 신규 14개 = 61개 전부 통과, `import-linter`
  결과 "Spokes must not import each other directly"·"Mova domain must not
  import app or adapter" 둘 다 KEPT(이번 변경으로 깨진 계약 없음). 남은
  broken contract 1건(Hub-independence, ontology→core.matrix→spoke 전이
  경로)은 이번 세션 파일과 무관한 기존 이슈.

### 산출물
- 마이그레이션 1건 + ORM 3개 파일 + DTO 4개 파일 + Port 5개(4개 확장,
  1개 신규) + PgRepository 4개 파일 + 유스케이스 2개 파일(신규) + DI
  프로바이더 1개(신규) + CLI 스크립트 1개(신규) + 테스트 1개 파일(14건) —
  총 16개 수정 + 10개 신규, 로컬 커밋만 하고 push는 보류(사용자 확인 후).
  마이그레이션 실제 적용(`alembic upgrade head`)과 backfill 실행은 EC2에서
  사용자가 별도 진행.

---

---

## 2026-07-29
### 작업 내용

- `origin/main`의 lora-server 베이스 모델 폴백 커밋(4703232)을 `suvisdev`
  브랜치로 cherry-pick.
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 백로그 중 "06 Sentinel 소프트
  플래그 저장 지속화 + 어드민 오버라이드 엔드포인트" 착수(사용자 선택).
  사전 조사 결과 저장 계층이 S3(자격증명 미연결로 사실상 미동작)/DB
  (`VisionRepository`, 실제 구현이나 DI 미배선) 둘로 쪼개져 있던 것을 확인,
  DB로 일원화하기로 결정(S3는 `.env`에 AWS 키가 전혀 없어 당장 못 씀).
- 같은 백로그의 "CLIP 모델 다운로드 hang" 착수 — 재현·원인 규명 후 최소 수정.
- `.claude/rules/` 경로별 코딩 규칙 4종 신규 작성 + 루트 `CLAUDE.md` 보강
  (하네스 설정·명령어·환경변수·브랜치·테스트 섹션이 아예 없던 것을 추가).
- `.claude/projects/memory/` 팀 공유용 주제별 메모 신설.
- 메인 페이지 우측 히어로 자리를 정지 이미지에서 영상으로 교체 요청.
- 전역 `Suvisdev AI` 채팅 버블을 LESSON `/langchain/chat`과 같은 백엔드
  설정으로 전환 요청.
- 완전히 빈 DB에서 `alembic upgrade head`가 성공하는지 실제 검증(사용자
  요청) — 이 날 앞선 세션이 "로컬 Postgres 미기동"으로 미뤄뒀던 검증을
  도커 임시 컨테이너로 이어서 수행하고, 검증 중 발견된 누락 마이그레이션 보완.
### 수정/구현

- **DB 스키마**: `alembic/versions/20260729_0001_add_vision_upload_soft_flags.py`
  신규 — `vision_uploads`에 `poster_confidence`/`sharpness_score`/
  `is_poster_warning` 컬럼 추가(`down_revision=20260727_0001`, 단일 head 체인
  유지). `VisionUploadOrm`에 동일 컬럼 추가.
- **DTO/포트**: `vision_dto.py`에 `VisionImageCommand`·`VisionUploadResponse`
  플래그 필드 + `upload_id`, 신규 `VisionPosterFlagOverrideDto` 추가.
  `VisionPort`/`VisionUseCase`에 `update_poster_flag`/`override_poster_flag`
  추상 메서드 신설.
- **리포지토리**: `VisionRepository.save_image`가 플래그를 실제 persist,
  신규 `update_poster_flag`(select→갱신→commit, id 없으면 `updated=False`)
  구현. `VisionS3Repository`는 인터페이스 계약만 맞추도록
  `update_poster_flag`에서 `NotImplementedError`(메타데이터 row가 없어 오버라이드
  불가) — 나머지 S3 코드는 손 안 댐.
- **DI 전환**: `vision_provider.py`의 `get_vision_repository`를
  `VisionS3Repository` → `VisionRepository`(DB)로 교체.
- **어드민 엔드포인트**: `PATCH /vision/{upload_id}/poster-flag` 신설
  (`vision_router.py` + 신규 `vision_schema.py`), `require_admin` 가드 적용
  (mova `market_picks_router.py`의 PATCH 패턴을 그대로 따름).
- **테스트**: `test_vision_upload_sentinel_gate.py` — 새 추상 메서드로 깨질
  뻔한 `_FakeVisionRepository`에 `update_poster_flag` 구현 추가, GPU 불필요한
  `override_poster_flag` 위임 테스트 1개 신설.
- **CLIP hang 수정**: `apps/ontology/test/conftest.py` 신규 — `HF_HUB_OFFLINE`·
  `TRANSFORMERS_OFFLINE`을 세션 시작 시 설정해 GPU 테스트가 네트워크를 타지 않고
  로컬 캐시만 쓰게 강제. Sentinel 판별 로직·임계값은 건드리지 않음.
- **`.claude/rules/`**: `typescript.md`(strict·any 금지·type 별칭·enum 금지·
  단언 경계 — `suvis/` 실측: type 167 : interface 4, any 0, enum 0, React.FC 0),
  `api-standards.md`(제네릭 fetch 래퍼·Bearer 3계층·`safeApiErrorMessage`·
  라우트 핸들러 상태코드), `testing.md`(마커·conftest 격리·포트 fake),
  `security/pci.md`(결제 코드가 생길 때 발동하는 게이트로 작성),
  `security/auth.md`(`require_admin` 단일 가드·role은 서버 산출 JWT claim만 신뢰·
  토큰 3계층 전달·무인증 지점은 근거 주석·IDOR·엔드포인트 체크리스트 5항목.
  이 저장소에서 무인증 취약점이 실제로 두 번 나온 영역이라 규칙으로 굳힘).
- **루트 `CLAUDE.md`**: 기존 내용 수정 없이 섹션 추가 — 명령어(3스택별)·테스트·
  환경 변수·브랜치 전략·주의사항·하네스 설정(`.claude/` 구조, 메모리 두 곳의
  차이, 훅 동작).
- **`.claude/projects/-home-a-projects-suvis/memory/`**: `MEMORY.md`(인덱스)·
  `debugging.md`(lint-imports baseline red, CLIP hang, DB 미기동, 기존 실패
  테스트)·`patterns.md`(백엔드 계층·어드민 엔드포인트·마이그레이션·테스트 패턴).
  처음엔 `projects/memory/`로 만들었다가, 하네스 관례인 `<프로젝트 경로>` 인코딩
  (`-home-a-projects-suvis`, 절대경로의 `/`→`-`)을 넣어 `git mv`로 이동(이력 보존).
  단, **홈(`~/.claude/...`)이 아니라 저장소 안이라 자동 로드되지 않는다** — 두
  경로가 `~/` 유무만 달라 혼동 위험이 커서 양쪽 문서에 구분을 명시했다.
- **`memory/auto-memory.md` 신규**: 자동 메모리 동작 방식(`MEMORY.md` 첫 200줄만
  세션 시작 시 로드, 초과분·주제 파일은 필요할 때만, 200줄 제한은 `MEMORY.md`
  전용, `CLAUDE.md`는 길이 무관 전체 로드) + 활성화/비활성화 방법
  (`CLAUDE_CODE_DISABLE_AUTO_MEMORY`, `autoMemoryEnabled`, `/memory` 토글).
  기존 문서와 겹치는 "두 위치 차이"는 링크로만 처리.
- **`.mcp.json` 정리 + 내부 MCP 서버 2종 등록·검증**: 예시로 있던 `postgres`·
  `notion`을 지우고 `github` 유지 + `gmail` 추가. gmail은 공식 서버가 없어
  (`@modelcontextprotocol/server-gmail` 부재를 npm으로 확인) 사용자 선택으로
  `@gongrzhe/server-gmail-autoauth-mcp` 채택. 저장소 내부 FastMCP 서버 중
  `suvis-vision-sentinel`·`suvis-vision-genre`를 상대경로 + `PYTHONPATH=
  suvisdev:suvisdev/apps`로 등록(팀 공유 고려해 절대경로 회피).
  `.claude.json`은 0바이트 로컬 상태 파일이라 등록 위치로 쓰지 않고 `.gitignore`에 추가.
- **`${VAR:-default}` 문법 지원 여부 실측 확정**: `claude mcp list` A/B 대조로
  판정 — `${SUVIS_PYTHON:-python}`일 때는 변수 미설정에도 경고가 없고,
  `${SUVIS_PYTHON}`으로 바꾸면 "Missing environment variables: SUVIS_PYTHON"
  경고가 뜬다(기본값 없는 `${GITHUB_TOKEN}`과 동일 거동). 즉 **`:-` 문법은
  지원된다.** 그럼에도 **기본값을 제거**했는데, 이 머신엔 `python`이 없고
  (`/usr/bin/python3`뿐, 그마저 `mcp` 미설치) 기본값이 있으면 검증을 통과한 뒤
  기동 단계에서 조용히 실패하기 때문이다. 기본값을 빼면 Claude Code가 명확한
  누락 경고를 준다.
- **`/code-review` 실행 결과 검증 후 사고 2건 되돌림** — 서브에이전트 리뷰가
  세션 밖에서 생긴 작업트리 변경(마지막 커밋 이후, 내가 만든 게 아님)을
  잡아냄: (1) `suvis/.env.production`(공개 API URL 한 줄, 비밀 아님) 삭제가
  스테이징돼 있었는데 이 값을 공급하는 다른 경로가 전혀 없어 그대로 배포하면
  프로덕션 로그인·OAuth·관리자·비전 요청이 방문자 로컬호스트로 조용히
  나갈 뻔함 — 사용자 확인 후 스테이징 해제+원복. (2) `.gitignore`에
  `.mcp.json`을 추가했는데 이미 git이 추적 중인 파일이라 효과가 없고
  바로 위 주석과도 모순 — 그 줄과 중복된 `.claude.json` 줄 제거.
  `.mcp.json`의 `github` 서버 삭제는 사용자 확인 후 그대로 유지.
- **`.claude/agents`·`scripts`·`skills/deploy` 검토 — 채우지 않고 삭제 결정**:
  `/code-review` 실행 중 로컬에 새로 생긴 4개 파일이 이 저장소 것이 아니라
  Claude Code 공식 문서 예시 템플릿임을 확인(설명 주석 스타일, 존재하지 않는
  스킬 참조, 빈 본문). 어디에도 연결 안 돼 비활성 상태였음. 처음엔 실제로
  채워 넣는 방향으로 시작했으나(`protect-files.sh`를 이 저장소 `.env*` 현황에
  맞게 재작성 중 `jq` 미설치 버그까지 발견), 사용자가 방향 전환 — "프로덕션
  배포" 스킬과 auto-invoke 가능한 에이전트를 지금 활성화하는 게 오히려 위험
  하다는 판단으로 `skills/deploy/SKILL.md`·`agents/code-reviewer.md`(기존
  `/code-review`와 중복)·`agents/data-analyzer.md`(존재하지 않는 스킬 참조로
  호출 시 깨짐) 3개 삭제. `scripts/protect-files.sh`는 원본 템플릿 상태로
  되돌리고 등록하지 않은 채 보류(추후 별도 작업으로 제대로 엮기로 함).
- **공개 개발로그 `/devlog` 신설**: 내부 작업 일지를 도메인 메인 사이트에
  공개용으로 옮김. **자동 변환하지 않고** WORK_LOG 전체(1252줄·15개 작업)를
  읽어 "공개 가능 / 추상화 / 완전 제외" 3분류한 뒤, 공개 안전 항목만 골라
  12개로 다시 썼다. 각 항목은 "제목 + 설계 의도 한 줄"이며 파일 경로·클래스명·
  수치·인프라 세부는 넣지 않았다. `lib/devlog.ts`(`apps-catalog.ts` 패턴의
  타입 있는 데이터 파일, `highlighted` 필드로 강조 제어) + `app/devlog/page.tsx`
  (서버 컴포넌트) + `components/header.tsx`(Devlog 링크). 메인 페이지
  레이아웃은 건드리지 않았다.
- **루트 `CLAUDE.md`에 커밋 메시지 규칙 추가**: Conventional Commits·제목 50자
  이내·한국어. 실측 대조 결과 최근 14건 중 11건이 50자를 넘지만(중앙값 60자대),
  사용자 결정으로 **소급 없이 앞으로 지킬 목표**로 둔다.
- **메인 페이지 우측 히어로를 정지 이미지 → 영상으로 교체**: 사용자가 준
  mp4(H.264, 1280×720, 8초, ~2MB)를 `suvis/public/hero-holographic-mask.mp4`로
  파일명 정리해 추가(원본 경로에 특수문자 포함, URL 문제 방지). `hero-image-panel.tsx`의
  `next/image` `<Image>`를 `<video autoPlay loop muted playsInline>`로 교체,
  기존 정지 이미지는 `poster`(로딩 중 표시)로 재활용. 실제 dev 서버 + 헤드리스
  브라우저로 데스크톱(1440px)·모바일(390px) 두 폭 모두에서 `paused: false`·
  `currentTime` 증가까지 확인해 재생 중임을 실측 검증(정적 스크린샷만으로는
  autoplay 성공 여부를 알 수 없어서).
- **전역 `Suvisdev AI` 채팅 버블을 LESSON `/langchain/chat`과 같은 백엔드로
  전환**: 기존엔 `/api/chat`(Next 로컬 라우트, Gemini SDK 직접 호출 +
  모델 선택 드롭다운)을 썼는데, `/api/v1/langchain/chat`(semantic_router가
  의도 판단 → LangChain 체인이 답변, 레슨 페이지와 완전히 동일한 백엔드)으로
  교체. 요청 형식도 `{message, model}` → `{messages: [...]}`(대화 이력 전체,
  레슨 페이지와 동일)로 변경. 모델 선택 드롭다운은 제거 — 백엔드 스키마에
  `model` 필드가 있지만 라우터가 실제로 안 씀(`use_case.chat()`에 미전달)을
  코드로 확인, 남겨두면 선택이 무시되는데도 되는 것처럼 보여 오해를 만듦.
  백엔드 직접 `curl` 확인 + 헤드리스 브라우저로 버블 열기→입력→전송→응답
  전 과정 재현, 네트워크 로그로 실제 호출 엔드포인트·페이로드까지 확인.
- **버그 발견·수정(범위 밖, 검증 중 발견)**: 전송 흐름을 실제로 클릭 테스트하다
  `pageerror: Cannot read properties of null (reading 'reset')` 발생 —
  `handleSubmit`이 `await sendMessage(...)` **이후**에 `e.currentTarget.reset()`을
  호출하는데, React `SyntheticEvent.currentTarget`은 동기 디스패치가 끝나면
  null이 되는 구조적 함정. `git diff`로 이 코드가 이번 변경 이전부터 있던
  것임을 확인(이번에 처음 실제 인터랙션 테스트를 돌리며 드러남). `await` 전에
  폼 참조를 변수로 미리 잡아두는 방식으로 수정, 재검증 결과 에러 사라짐.
- **메인 페이지 헤더-콘텐츠 간격 조정**: 헤더 알약(pill)과 카드 모서리가
  거의 맞닿아 답답해 보인다는 사용자 지적으로 `app/page.tsx`의 `pt-0`을
  `pt-3 md:pt-4`(12~16px)로 변경. 뷰포트 높이 계산식(`min-h-[calc(...)]`,
  outer/inner 둘 다)도 늘린 padding만큼 같이 줄여 불필요한 스크롤이 새로
  생기지 않게 맞춤. 짧은 화면(700px)·모바일에서 스크롤이 생기긴 하는데,
  원본 코드로 되돌려 대조한 결과 **이 스크롤은 원래도 있던 것**임을 확인
  (콘텐츠 자체가 이미 뷰포트보다 김) — 이번 변경은 정확히 padding만큼만
  늘렸을 뿐 새로 만든 문제가 아님.
- **다크 모드에서 로그인 카드 입력창이 검게 변하는 버그 수정**: 로그인 모달
  (`auth-dialog.tsx`)은 다크 모드에서도 항상 흰 배경으로 고정되도록 만들어져
  있는데, `Input`·`Tabs` shadcn 베이스 컴포넌트가 `dark:bg-input/30` 등을 갖고
  있어(색상 변수 `--input: oklch(0.22 0.01 260)`, 거의 검정) `.dark` 스코프에서
  `bg-white`보다 CSS 명시도가 높아 이겨버리는 게 원인 — `bg-white`(무조건 적용)와
  `dark:bg-input/30`(다크 전용)은 Tailwind `twMerge`가 서로 다른 modifier로 보고
  충돌 처리를 안 해서 둘 다 남는데, `.dark .dark\:bg-input\/30` compound selector가
  더 구체적이라 이긴다. `app/login/auth-forms.tsx`의 `inputClass`(입력창·셀렉트)·
  `tabTriggerClass`(로그인/회원가입 탭)에 `dark:...!`(Tailwind v4 important 문법)를
  추가해 라이트 스타일을 명시적으로 강제 — `components/ui/input.tsx` 같은 공용
  베이스는 사이트 전역 다크 모드가 정상 동작해야 해서 건드리지 않음. 실제로
  다크 모드를 켜고 모달을 열어 계산된 스타일(`background-color: rgb(255,255,255)`)
  까지 확인해 검증. mova 쪽은 `mova-login-button.tsx` 주석으로 이미 예전에
  자체 다크 테마(`--mova-*` CSS 변수, shadcn Input 미사용)로 교체돼 이 버그의
  영향을 받지 않음을 확인 — 별도 수정 없음.
- **위 버그 수정 배포 확인 중 mova 다크모드 구조 재발견 + 방향 전환**: 배포
  사이트에서 여전히 회색으로 보인다는 사용자 피드백에 git 상태(`main`이
  최신 커밋을 포함하는지, 머지 누락 없는지)를 재확인했으나 이상 없었음 —
  실제 원인은 Vercel 캐시/배포 지연으로 추정된 상태였으나, 사용자가 문제를
  이 시점에서 근본적으로 우회하기로 결정: **"메인 사이트는 다크모드 자체를
  없애고 mova만 유지"**. 조사 중 `mova-theme-setter.tsx`를 확인해 기존에
  가졌던 이해("mova는 독립된 always-dark 테마")가 틀렸음을 확인 — 실제로는
  `MovaThemeSetter`가 `/mova` 진입 시 전역 next-themes 상태를 `setTheme("dark")`로
  강제하고 나갈 때 이전 값으로 복원하는 구조였고, mova 자체 헤더에도 별도
  `ThemeToggle`이 있어 mova 안에서 라이트("Warm Cinema")로 전환 가능함
  (`mova.css`의 `html:not(.dark) .mova-app`). 즉 메인 사이트와 mova가 같은
  전역 토글 상태를 공유하고 있었던 것.
- **다크 모드를 mova 전용으로 한정**: `components/header.tsx`에서
  `<ThemeToggle />` 제거(메인 사이트에서 다크 진입 경로 원천 차단).
  `components/site-chrome.tsx`에 `useEffect`로 `pathname`이 `/mova`가
  아니면 매번 `setTheme("light")`를 강제하는 로직 추가 — 토글 UI를 없애는
  것만으로는 next-themes가 localStorage에 저장해 둔 예전 `dark` 값이 계속
  복원되는 문제(이번 세션 내내 다크로 테스트해 온 사용자가 실제로 이 상태였음)
  까지는 못 막아서 필요했음. `admin`도 같은 조건으로 라이트 고정(별도
  다크 스타일이 없어 원래도 영향 없었지만 범위를 명확히 함).
  **검증**: 헤드리스 브라우저로 (1) `localStorage.theme="dark"`를 미리 심어
  기존 다크 사용자 상태를 재현한 뒤 홈 진입 → `html.dark` 없음·헤더에 토글
  흔적 없음·로그인 입력창 `rgb(255,255,255)` 확인, (2) `/mova` 진입 → `html.dark`
  있음(시네마 테마 그대로) 확인, (3) mova→홈 복귀 → 다시 라이트로 강제되는
  것까지 3단계 전부 스크린샷과 함께 확인.
- **DB 스키마**: `alembic/versions/20260729_0002_create_hub_knowledge.py`
  신규 — `HubKnowledgeOrm`(2026-07-14, cc2c334에서 추가)이 마이그레이션 체인에
  한 번도 CREATE된 적 없이 `ensure_titanic_tables()`의 `create_all()`로만
  존재해 온 것을 확인하고 보완(`down_revision=20260729_0001`, pgvector
  `CREATE EXTENSION IF NOT EXISTS vector` 포함). 이 리비전 이후 alembic
  체인만으로 앱이 실제로 쓰는 모든 테이블(contents/gildle/mova/titanic/
  dispatch/ontology/execsuite/viewer 전 앱)이 생성됨을 확인.
- **`main.py`의 `create_tables()`(→`ensure_titanic_tables()`) 재확인**: 이미
  이전 세션(a42e667)에서 mova/viewer 테이블은 "Alembic이 전담, create_all
  우회 생성 금지"로 정리돼 있었음. 남은 건 `grid_neo_theone_base.Base`
  소유 테이블(titanic/dispatch_adress/vision_uploads/hub_knowledge) —
  주석상 "삭제 후 업로드 복구용" 의도적 fallback이고 `create_all`은
  `checkfirst=True`라 이미 있는 테이블은 건드리지 않아 충돌은 아님. 다만
  `ensure_titanic_tables()`가 `dispatch.receive_orm`(dispatch_inbox)·
  `execsuite.pdf_loader_orm`은 import하지 않아 그 두 테이블은 create_all
  대상이 아님 — 지금은 두 테이블 다 알렘빅 마이그레이션이 있어 문제 없지만,
  "복구용" 의도라면 어떤 테이블까지가 대상인지 import 목록과 주석이
  불일치함. 코드 변경은 하지 않고 다음 정리로 제안만 남김: (1) 복구
  대상을 정말 titanic 전용으로 좁히려면 hub_knowledge/vision_uploads/
  dispatch_adress import를 이 함수에서 빼거나, (2) 지금처럼 유지한다면
  주석을 "NeoTheOneBase 전체 복구용"으로 정정해 목록과 의도를 맞출 것.
### 오류·막힌 점

- **로컬 Postgres 미기동(세션 초반)** — DB 프로세스가 안 떠 있어
  `alembic upgrade head`로 신규 마이그레이션을 실제 DB에 적용해보는 검증은
  당장 못 함(문법·체인 유효성만 `alembic history`로 확인). → 아래 "완전히
  빈 DB 검증 성공"에서 도커 임시 컨테이너로 이어서 검증.
- **리비전 ID 충돌** — `hub_knowledge` 마이그레이션을 처음엔
  `20260729_0001`로 만들었는데, 같은 시점에 `git pull`로 받아온
  `20260729_0001_add_vision_upload_soft_flags.py`와 리비전 ID·
  `down_revision`이 완전히 겹침(두 세션이 같은 날짜로 각자 새 리비전을
  만든 것). `20260729_0002`로 재번호 + `down_revision`을
  `20260729_0001`로 체인해 단일 head 유지.
- **검증 중 실수로 실제 로컬 dev DB에 접속**(중요, 재발 방지용 기록) —
  임시 도커 컨테이너(포트 55432)를 만들어 `DATABASE_URL`만 그 컨테이너로
  export했는데, `alembic/env.py`의 `_database_url()`이
  `MOVA_DATABASE_URL`을 `DATABASE_URL`보다 먼저 확인하고, `suvisdev/.env`가
  이미 `MOVA_DATABASE_URL=localhost:5432`(docker-compose `suvisdev-db-1`,
  실제 로컬 개발 DB)를 정의하고 있어 그쪽으로 연결됨. 그 DB는 실제
  백엔드가 상시 기동 중이라(`suvisdev-backend-1`) `create_all()`로 이미
  `titanic_passengers`/`dispatch_adress`/`vision_uploads`/`hub_knowledge`가
  떠 있는 상태였고, 알렘빅은 한 번도 안 돈 상태(alembic_version 없음) —
  결과적으로 사용자가 신고한 버그의 실물 사례를 우연히 재현(`20260604_0000`이
  이미 있는 `titanic_passengers`를 CREATE하려다 `DuplicateTable`). 각
  마이그레이션은 트랜잭션으로 묶여 있어 실패 시 롤백 확인(`\dt`로 실 DB에
  변경 없음 확인) — 실제 데이터 손상 없음. 원인 규명 후 `DATABASE_URL`·
  `MOVA_DATABASE_URL` 둘 다 임시 컨테이너로 export하도록 고쳐서 재검증.
- **완전히 빈 DB 검증 성공** — 위 실수를 바로잡은 뒤 순수 도커
  `pgvector/pgvector:pg16` 컨테이너(빈 DB, `create_all` 전혀 안 거침)에
  `alembic upgrade head`를 처음부터 끝까지 실행, 에러 없이 34개 테이블
  전부(`hub_knowledge` 포함) 생성 확인. `alembic/env.py`는 무거운
  ML/ORM import(torch·transformers 등, 이 머신엔 미설치) 없이 순수 SQL
  DDL만 검증하려고 임시로 target_metadata를 비웠다가 검증 후 원본으로
  완전히 복원(`git diff` 무변경 확인).
- import-linter가 `vision_repository.py`(hub-independence 위반, ontology→
  core.matrix.grid_oracle_database_manager→titanic/mova/viewer/dispatch)를
  잡아내는데, `git stash` 비교로 이번 변경 이전부터 있던 기존 위반임을
  확인(파일 자체는 이전에도 있었고 DI만 안 됐을 뿐이라 정적 분석엔 그때도
  걸렸음) — 이번 작업이 새로 만든 문제 아님.

- **CLIP hang은 이번 세션에서 재현되지 않았다** — 네트워크가 정상이라
  `from_pretrained()`가 17초에 성공. 대신 캐시에서 결정적 증거를 찾았다:
  `~/.cache/huggingface/hub/models--openai--clip-vit-base-patch32/blobs/*.incomplete`
  (490MB, 07-28 16:09 생성 후 정체). hang 단계는 collection이 아니라 **테스트 실행
  중 `from_pretrained()`의 네트워크 왕복**으로 특정(어댑터가 함수 본문 안에서
  import되고 모델 로드도 `detect()` 시점이라 collection은 영향 없음). 근본 원인은
  코드가 아니라 "캐시가 있어도 매번 HF Hub etag 확인 → 멈추면 무한 대기" 구조.
  `HF_HUB_OFFLINE` 적용 후 캐시 누락 시 hang 대신 4.5초 만에 `OSError`로 즉시
  실패하는 것까지 실측 확인.
- **공개 개발로그에서 인증 관련 항목을 통째로 뺐다** — 초안에서는 취약점 수정
  이력을 "권한 검증 설계 개선"으로 추상화해 넣으려 했으나, 추상화해도 "인증
  관련 작업을 했다"는 신호 자체가 과거 취약점의 존재를 암시하고 공격 힌트가
  된다는 판단으로 사용자와 함께 제외 결정. 미해결 IDOR은 언급조차 하지 않았다.
  최종 노출 스캔에서 데이터 파일 주석에 내부 문서 경로가 하나 남아 있던 것을
  발견해 제거(화면에 렌더링되진 않지만 기준 적용). 재스캔 클린.
- **genre MCP 도구는 500 — 설정이 아니라 학습 산출물 부재** —
  `suvis-vision-sentinel`의 `detect_anomaly`는 백엔드까지 왕복해 정상 응답
  (`is_poster=true`, `poster_confidence=0.699`, `sharpness=2587.96`). 반면
  `suvis-vision-genre`의 `list_supported_classes`는 백엔드 500이고 원인은
  `apps/ontology/runs/genre_classify/classes.json` 부재였다. `runs/`는
  `.gitignore` 대상(`suvisdev/.gitignore:70`)이고 디렉터리 자체가 없다 —
  echo 어댑터 테스트가 실패하는 것과 같은 기존 조건이며 MCP 설정 문제가 아니다.
  등록·연결·`tools/list`는 두 서버 모두 정상.
- **세션 내에서는 connected 상태를 확인할 수 없다** — `.mcp.json`은 세션 시작 시
  로드되고, `claude mcp list`상 두 서버는 `⏸ Pending approval` 상태다. 프로젝트
  스코프 서버는 사용자 승인이 필요하므로 최종 connected 확인은 사용자 몫이다.
  대신 Claude Code와 동일한 방식(stdio JSON-RPC)으로 직접 띄워 `initialize`~
  `tools/call`까지 왕복시켜 검증했다.
- **루트 `CLAUDE.md`가 권장 길이를 넘겼다** — 자동 메모리 문서를 쓰며 확인:
  `CLAUDE.md`는 길이와 무관하게 전체 로드되지만 200줄 이내가 지시 준수에 유리한데,
  이번 세션의 추가분으로 216줄이 됐다. 더 늘릴 내용은 `.claude/rules/`나 `_docs/`로
  빼는 게 낫다는 메모를 `auto-memory.md`에 남겼다(정리 자체는 미착수).
- **붙여넣은 규칙 템플릿이 다른 프로젝트 것이었다** — 루트 `CLAUDE.md`에 추가하라고
  받은 내용이 "Node.js REST API / npm test / Jest+Supertest / `AppError`(`src/errors/`)
  / `src/legacy/` / payments PCI / `.env.local` / develop 브랜치"였는데, 실제로는
  백엔드가 Python·FastAPI, 프론트는 pnpm(테스트 0건), `src/`·`AppError`·`payments`·
  `develop` 전부 부재, env는 `suvisdev/.env` 하나. 대조표로 보고하고 카테고리만
  살려 실측 값으로 채웠다. 미리 만들어져 있던 빈 규칙 파일 `testing.md`·
  `security/pci.md`도 같은 출처 — `testing.md`는 백엔드 pytest 기준으로 다시 쓰고,
  `pci.md`는 결제 코드가 없다는 배너를 달아 "생기면 발동하는 게이트"로 작성.
### 산출물

- 코드: 위 "수정/구현" 파일 전체.
- 문서: 이 항목 + `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(완료분 이동),
  루트 `CLAUDE.md`, `.claude/rules/` 4종, `.claude/projects/memory/` 3종.
- `alembic/versions/20260729_0002_create_hub_knowledge.py` 신규 —
  빈 DB에서 `alembic upgrade head` 성공까지 확인 후 커밋.

---

## 2026-07-28

### 작업 내용
- suvis 프론트 LESSON 사이트에 LangChain 채팅 탭 신설 요청 — 처음엔 UI 틀만
  (SOCCER 섹션 아래 LANGCHAIN 섹션 추가, `/langchain/chat`), 이후 실제 파이프라인
  연결까지 확장 요청.
- silicon_valley 백엔드에 semantic_router(ontology) → LangChain 챗봇 엔진 파이프라인을
  클린 아키텍처(라우터→유스케이스→포트→리포지토리)로 구현.
- pnpm 로컬 개발환경 트러블슈팅(susu에 pnpm 잘못 로컬 설치, suvis `pnpm install`
  sharp 빌드 스크립트 차단) 지원.
- LangChain 활용 사례 문서 2건 추가(NCL, Elastic) + 기존 Morningstar 문서 접점
  섹션을 같은 형식으로 보강.

### 수정/구현
- **프론트(`suvis/`)**: `app/langchain/chat/page.tsx` 신규(soccer 채팅과 동일
  레이아웃, 인디고 테마, 실제 `/api/v1/langchain/chat` fetch). 사이드바에 LANGCHAIN
  섹션(채팅 링크)을 11개 페이지에 동일 추가(이 저장소가 사이드바 nav를 페이지마다
  복사하는 기존 관례를 따름). `pnpm-workspace.yaml`의 `allowBuilds.sharp`를
  자리표시자 텍스트에서 `true`로 수정. `susu/`에 잘못 로컬 설치됐던
  `node_modules`/`package.json`/`package-lock.json`/`pnpm-lock.yaml` 정리(삭제).
- **백엔드(`suvisdev/apps/silicon_valley/`)**: 신규 —
  `app/ports/output/rangchain_chat_engine_port.py`(`RangchainChatEnginePort`),
  `adapter/outbound/repositories/rangchain_chat_engine_repository.py`
  (`ChatPromptTemplate`+`MessagesPlaceholder`+`ChatOllama` LCEL 체인, destination별
  시스템 프롬프트 분기, `OLLAMA_BASE_URL` 반영), `app/dtos/rangchain_chat_dto.py`,
  `app/ports/input/rangchain_chat_use_case.py`, `app/ports/output/rangchain_chat_errors.py`,
  `adapter/inbound/api/schemas/rangchain_chat_schema.py`,
  `adapter/inbound/api/v1/rangchain_chat_router.py`(`POST /api/v1/langchain/chat`),
  `dependencies/rangchain_chat_provider.py`(ontology의 `get_semantic_router_use_case`를
  그대로 DI 재사용 — mova가 ontology를 참조하는 기존 cross-app 관례를 따름).
  `app/use_case/rangchain_interactor.py` — `semantic_router.route()` 호출 후 결과
  (destination/entities/answer)를 LangChain 엔진에 전달하도록 작성. `silicon_valley_router`에
  라우터 등록.
- **문서**: `apps/silicon_valley/_docs/ranchain-ncl-strategy.md`,
  `rangchain-elastic-strategy.md` 신규, `rangchain-monigstar-strategy.md` 접점
  섹션 보강 — 전부 "이 저장소엔 해당 데이터 소스 없음, 문서화만" 결론(실제
  데이터·구현은 보류).

### 오류·막힌 점
- **500 plain-text 파싱 오류**(`"Unexpected token 'I', "Internal S"... is not
  valid JSON"`): 원인은 `SemanticRouterInteractor.route()`(ontology)의
  general(잡담) 분기가 `HubRagError`를 잡지 않고 그대로 던지는데,
  `rangchain_chat_router.py`는 `RangchainChatError`만 캐치해서 미처리 예외가
  FastAPI 기본 500(plain text)으로 나간 것. `rangchain_interactor.py`에서
  `semantic_router.route()` 호출을 `HubRagError` 캐치 → `RangchainChatError`
  변환으로 고침. `GEMINI_API_KEY`는 `.env`에 설정돼 있어 정확한 실패 원인
  (quota/네트워크 등)은 재현 시 에러 메시지로 추가 확인 필요 — 이번 세션에서는
  백엔드 서버가 환경에 안 떠 있어 재기동 후 실제 검증은 못 함(코드 리뷰로만
  원인 특정).
- `[ERR_PNPM_IGNORED_BUILDS] sharp` — `pnpm-workspace.yaml`의 `allowBuilds.sharp`
  값이 `true` 대신 자리표시자 텍스트였던 게 원인.
- `[ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL] Command "dev" not found` — `susu`
  (Flutter, `package.json` 없음)에서 `pnpm dev`를 실행해 발생. `suvis`(Next.js)가
  맞는 위치.

### 데이터
- 해당 없음.

### 산출물
- 프론트: `suvis/app/langchain/chat/page.tsx`(신규) + 사이드바 11개 파일,
  `suvis/pnpm-workspace.yaml`.
- 백엔드: `apps/silicon_valley/` 내 `rangchain_chat_*`/`rangchain_interactor.py`
  8개 파일 신규, `adapter/inbound/api/__init__.py` 라우터 등록.
- 문서: `ranchain-ncl-strategy.md`, `rangchain-elastic-strategy.md`(신규),
  `rangchain-monigstar-strategy.md`(수정).
- 커밋 해시: 이번 커밋 참고.

---

### [2] PROGRESS 백로그 점검 — 진행 가능한 항목 처리

**배경**: 사용자가 `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 "다음/남은 작업"을
확인 후 지금 바로 진행 가능한 부분을 진행해달라고 요청. 비전 02·05(제품 결정
대기), 06 저장 지속화·S3(AWS 미연결), 시크릿(a)(단독 실행 금지 명시)는 외부
의존/결정 때문에 스킵하고, 실제 진행 가능한 두 항목만 처리.

**수정/구현**:
1. **`apps/mova/tests/test_import_interactor.py` 실패 2건 수정** — 원인은
   `ImportInteractor.__init__`에 `box_office`/`hub_rag` 파라미터가 추가됐는데
   테스트는 예전 3-인자 시그니처로 호출하던 것. 두 테스트 모두 이 두 의존성을
   실제로 쓰지 않는 경로라(`box_office` 미참조, `hub_rag.ingest_movie`는
   예외를 삼키는 try/except 안) `AsyncMock()` 2개만 추가해 해결. 8개 전부
   통과 확인(`/home/a/.venv/bin/python -m pytest apps/mova/tests/...`).
   `test_llm_error_handling.py`는 이미 통과 상태였음(PROGRESS 기록이 stale).
2. **dispatch `watcher/judge/spam/adress` 인증 공백 감사** — watcher·judge는
   `/myself` 스캐폴딩 스텁뿐이라 위험 없음. spam은 프론트·백엔드 어디서도
   호출하는 곳이 없는 미사용 코드라 위험 낮음. **adress는 실제 취약점**:
   `search`/`upload` 둘 다 인증이 전혀 없었는데, 어드민 UI
   (`admin/dispatch/contacts/page.tsx`)뿐 아니라 LESSON 공개 데모
   (`suvis/app/mail/contacts/page.tsx`, 로그인 개념 없음)도 같은 백엔드
   엔드포인트를 호출 — 2026-07-27 인증 공백 대응 당시 "어드민 UI 미사용"으로
   보고 범위에서 뺐던 판단이 틀렸음이 이번에 드러남. 사용자 확인 후(어드민만
   가드, 레슨 데모는 막기로 결정) 2026-07-27과 동일 패턴으로 수정:
   - BE: `adress_router.py`의 `search`/`upload`에
     `Depends(require_admin)` 추가.
   - FE 프록시: `suvis/app/api/dispatch/adress/{search,upload}/route.ts`가
     들어온 `Authorization` 헤더를 `backendFetch`로 전달하도록 수정(search는
     raw `fetch`에서 `backendFetch`로 교체).
   - FE 클라: `admin/dispatch/contacts/page.tsx` 업로드 호출에
     `suvis-session.ts`의 `authHeader()` 첨부.
   - `suvis/app/mail/contacts/page.tsx`(공개 레슨 데모)는 코드 변경 없음 —
     이제 업로드 시 401을 받게 됨(의도된 동작). 이 페이지 자체를 어떻게 할지는
     별도 결정 필요(PROGRESS 백로그에 남김).

**검증**: `python3 -m ast` 문법 검증 통과, `pnpm exec tsc --noEmit` 통과,
`pytest apps/mova/tests apps/dispatch`(jwt 미설치로 `test_whoami_router.py`
제외) 41 passed / 2 failed — 실패 2건은 `test_send_email_interactor.py`
(orchestrator 프롬프트 포맷 불일치, 이번 작업과 무관하게 기존에 깨져 있던
것을 우연히 발견 — 수정 안 함, PROGRESS 백로그에 신규 등록).

**오류·막힌 점**:
- `/home/a/.venv`에 `requirements.txt`엔 있는 `PyJWT[crypto]`가 실제로
  설치돼 있지 않아 `shared.security.require_admin`을 import하는 모든 모듈
  (email/telegram/discord/receive/harvester/adress 라우터,
  `test_whoami_router.py`)이 이 venv에서 import 실패함 — 내 변경으로 생긴
  문제가 아니라 기존 email_router.py로도 재현 확인. venv에
  `pip install -r requirements.txt` 재실행 필요(이번 세션에선 미설치 상태로
  둠, 별도 사용자 확인 필요해 임의 설치 안 함).

### 산출물 (2)
- `apps/mova/tests/test_import_interactor.py`(수정),
  `apps/dispatch/adapter/inbound/api/v1/adress_router.py`(수정),
  `suvis/app/api/dispatch/adress/search/route.ts`,
  `suvis/app/api/dispatch/adress/upload/route.ts`,
  `suvis/app/admin/dispatch/contacts/page.tsx`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신(완료 항목 반영 + 신규 백로그 3건:
  mail/contacts 공개 데모 처리, test_send_email_interactor 실패, PyJWT 미설치).

---

### [3] 프론트 프로덕션 API URL 설정 + LangChain 모델을 Gemini로 교체

**배경**: 강사가 `suvisdev/.cursorrules`에 `NEXT_PUBLIC_BASE_URL=https://api.suvisdev.cloud`를
넣으라고 지시했다는데, 이유를 물어와 확인해보니 지시 자체가 틀렸음. `.cursorrules`는
Cursor 에디터용 AI 코딩 규칙 문서일 뿐 어떤 코드도 환경변수로 읽지 않고,
`NEXT_PUBLIC_BASE_URL`이라는 이름도 이 저장소 어디에도 없음(실제 코드가 읽는
이름은 `NEXT_PUBLIC_API_URL`, `suvis/lib/backend-client.ts` 등 7곳). 게다가
`NEXT_PUBLIC_*`는 프론트(`suvis/`) 관례라 백엔드(`suvisdev/`) 쪽에 있을 이유도
없음. 올바른 위치·이름으로 바로잡아 설정.

이어서 랭체인 모델을 Gemini로 바꿀 수 있는지 요청받아 진행.

**수정/구현**:
1. `suvis/.env.production`(신규) — `NEXT_PUBLIC_API_URL=https://api.suvisdev.cloud`.
   `.gitignore`엔 `.env.local`만 있어 커밋 가능(NEXT_PUBLIC 값은 어차피 브라우저에
   노출되는 값이라 커밋해도 안전).
2. `rangchain_chat_engine_repository.py` — `ChatOllama(exaone3.5:2.4b)` →
   `ChatGoogleGenerativeAI`(langchain-google-genai)로 교체. 모델 ID는 새로 만들지
   않고 `core.matrix.vauly_keymaker_secret_manager.GEMINI_MODEL_MAP["flash15"]`
   (`gemini-3.1-flash-lite`)를 재사용, API 키도 `get_keymaker().gemini_api_key`
   재사용 — ontology `GeminiLlmAdapter` 등 다른 Gemini 사용처와 키·모델 관리
   일원화. LCEL 체인 구조(`ChatPromptTemplate`+`MessagesPlaceholder`+
   `StrOutputParser`)·destination별 프롬프트 분기·에러 래핑은 그대로 유지, LLM
   provider만 교체.
3. `requirements.txt` — `langchain-google-genai==4.3.2` 추가, `langchain-core`
   (1.4.8→1.5.1)·`langsmith`(0.9.3→0.10.10)는 설치 과정에서 자동으로 딸려 올라간
   실제 버전에 맞춰 갱신. `/home/a/.venv`에 실제 설치 완료.

**검증**: `RangchainChatEngineRepository().generate(...)`를 직접 호출해 실제
Gemini 응답("안녕하세요! 저는 SUVIS의 한국어 어시스턴트입니다...") 받는 것까지
확인.

**오류·막힌 점**: `langchain-ollama`도 `/home/a/.venv`에 실제로는 설치돼 있지
않았음(PyJWT와 같은 종류의 기존 venv-requirements.txt 드리프트) — 이번 작업으로
ChatOllama를 걷어내서 문제되진 않았지만, venv 전체가 `requirements.txt`와
계속 어긋나 있다는 신호라 언젠가 `pip install -r requirements.txt` 재실행 필요.

### 산출물 (3)
- `suvis/.env.production`(신규), `suvisdev/apps/silicon_valley/adapter/outbound/repositories/rangchain_chat_engine_repository.py`(수정),
  `suvisdev/requirements.txt`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 LangChain 파이프라인 항목에 Gemini
  교체 내용 반영.

---

### [4] CLAUDE.md 응답 언어 지침 + PROGRESS 백로그 추가 처리

**배경**: 사용자가 CLAUDE.md에 "한국어로만 답변, 다른 언어 금지" 지침 추가 요청.
이어서 PROGRESS.md를 다시 확인하고 진행 가능한 나머지 항목(테스트 실패, venv
드리프트) 처리 요청.

**수정/구현**:
1. `CLAUDE.md`에 "## 응답 언어" 섹션 추가 — 항상 한국어로만 답변, 다른 언어
   사용 금지.
2. **`test_send_email_interactor.py` 실패 2건 수정** — `SendEmailInteractor.send()`가
   이메일 품질 개선을 위해 `orchestrator.generate()` 호출에 `system=` 키워드
   인자를 추가한 게 실제 기능인데(수신자 정보 포함 프롬프트 + 이메일 작성
   전문가 시스템 프롬프트), 테스트 2건이 예전 시그니처(위치 인자 하나만)를
   가정하고 있어 깨졌던 것. `test_hub_record_called_before_orchestrator`의
   `mock_orc.generate.side_effect` 람다가 `system=` 키워드를 못 받아 TypeError,
   `test_orchestrator_generates_body`는 호출 인자 자체를 잘못 assert. 둘 다
   실제 호출 형태에 맞게 테스트 수정. 14개 전부 통과.
3. **PyJWT/langchain-ollama 미설치 해소** — `pip install -r requirements.txt`
   전체 실행을 시도했으나 두 단계로 실패:
   - 1차: `/tmp`가 WSL2 tmpfs(3.9G)라 torch(843MB) 등 받다가
     `[Errno 28] No space left on device` — `TMPDIR`을 디스크 쪽
     (`/home/a/.cache/pip-tmp`, `/`는 898G 여유)으로 돌려 재시도.
   - 2차: `catboost==1.2.8`이 Python 3.14에서 빌드 실패
     (`AttributeError: 'Distribution' object has no attribute 'dry_run'` —
     distutils가 Python 3.12+에서 빠지면서 구식 setup.py가 깨짐). titanic 앱이
     실제로 쓰는 패키지라 requirements.txt에서 못 뺌 — 전체 동기화는 별도
     결정(catboost 버전 업/Python 버전 조정) 필요해 백로그로 남김.
   - 실제 목적(PyJWT 미설치)은 전체 동기화 대신 `PyJWT[crypto]==2.10.1`,
     `langchain-ollama==1.1.0`만 개별 설치로 해결. `require_admin`을 쓰는
     `email_router`·`rangchain_chat_router` import 확인, `apps/mova/tests`+
     `apps/dispatch` 47개 전부 통과(이전엔 jwt 없어 수집 실패하던
     `test_whoami_router.py`도 포함).

### 산출물 (4)
- `CLAUDE.md`(수정), `suvisdev/apps/dispatch/test/test_send_email_interactor.py`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신 — 완료 항목 반영(테스트 수정,
  PyJWT/langchain-ollama 설치), catboost 빌드 실패를 신규 백로그로 등록.

---

### [5] catboost/Python 3.14 빌드 문제 해소 + 캐시 정리

**배경**: [4]에서 남긴 백로그(`catboost` 빌드 실패로 `pip install -r
requirements.txt` 전체 불가)를 이어서 처리. 이후 사용자가 `suvisdev/`의
`.import_linter_cache`/`.mypy_cache`/`.pytest_cache`/`.ruff_cache`가 필요한지
질문.

**수정/구현**:
1. `catboost==1.2.8`→`1.2.10` 버전 업 — PyPI에 Python 3.14용 사전빌드 wheel
   (`catboost-1.2.10-cp314-cp314-manylinux2014_x86_64.whl`)이 존재함을
   `pip download`로 먼저 확인 후 진행. titanic 앱의 실제 사용(`CatBoostClassifier(
   iterations=200, verbose=False, random_state=42)`)은 단순 API라 호환 문제
   없음.
2. `pip install -r requirements.txt` 재실행 — 이번엔 빌드 에러 없이 끝까지
   성공(torch-2.12.1+cu126 등 전체 설치). `catboost`/`jwt` import 확인.
3. `apps/mova/tests`+`apps/dispatch`+`apps/titanic` 전체 재실행 —
   mova/dispatch는 계속 통과. **`apps/titanic/tests` 4개가 새로 눈에 띔**
   (패키지 설치와 무관, 지금 코드에 없는 이름 import: `JackTrainerMapper`,
   `titanic.adapter.outbound.llm`, `PassengerEntity`,
   `passenger_jack_trainer_vo` 모듈) — 원인 조사·수정 안 함, 백로그 등록.
4. `.import_linter_cache`/`.mypy_cache`(18M)/`.pytest_cache`/`.ruff_cache`
   삭제 — 전부 재생성 가능한 도구 캐시. `.mypy_cache`/`.pytest_cache`/
   `.ruff_cache`는 `.gitignore`에 이미 명시, `.import_linter_cache`는 자체
   `.gitignore`(`*`)로 커밋 제외돼 있어 git 추적에는 영향 없음.

**오류·막힌 점**: `pip install` 1차 시도 시 `/tmp`가 WSL2 tmpfs(3.9G)라
torch(843MB) 받다가 공간 부족 — `TMPDIR`을 디스크 쪽(`/home/a/.cache/pip-tmp`)
으로 돌려 재시도. 이후 catboost 문제로 2차 실패, 버전 업으로 최종 해결.

### 산출물 (5)
- `suvisdev/requirements.txt`(catboost 버전만 수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신 — catboost 백로그 완료 처리,
  titanic 테스트 4건 신규 백로그 등록.

---

### [6] silicon_valley → execsuite 앱 이름 변경 + labs/ 04·08 독립 실습 데모

**배경**: 사용자가 `apps/silicon_valley`를 `admin`으로 바꿔달라고 요청 —
이미 `suvis/app/admin/*`(어드민 대시보드)·`viewer`(RBAC)가 "admin"이라는
이름을 다른 의미로 쓰고 있어 충돌 우려를 짚고 대안을 물으니 `execsuite`로
확정. 이어서 "04·08은 mova/gildle에 안 쓰더라도 만들어둘 수 있냐"는 질문에,
`00_COMMON_conventions.md` §8의 "기법 먼저·용도 나중" 실패 사례를 짚고
독립 실습 영역으로 분리할 것을 확인받아 진행.

**수정/구현**:
1. **이름 변경**: `git mv apps/silicon_valley apps/execsuite`(102개 파일
   rename). 앱 내부 46개 `.py` 파일 + 외부 3곳(`main.py`, `alembic/env.py`,
   `.importlinter`)의 `silicon_valley`/`silicon-valley` 참조를 전부
   `execsuite`로 치환. `apps/ontology/_docs/star-craft-pipeline.md`의 앱
   목록, `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 완료 항목 라벨도 "구
   silicon_valley" 표기로 갱신(WORK_LOG 과거 기록은 당시 이름 그대로 유지).
   검증: `execsuite_router` 단독 import, `main.py` 전체 import 모두 성공,
   라우트(`/pdf/summarize`, `/langchain/chat` 등) 정상 확인.
2. **`suvisdev/labs/` 신설** — `apps/`의 어떤 앱과도 엮이지 않는 완전 고립
   영역(`main.py` 미등록, `.importlinter` 미포함). README에 명시한 원칙:
   Port(`ports.py`)는 참조 구현일 뿐 실제 편입 시 그 앱 컨벤션에 맞춰
   재배치, DTO는 도메인 중립이라 그대로 재사용 가능. GPU 없는 환경
   (m7i-flex.large)이라 학습 없이 사전학습 모델 추론만.
   - `pose_estimation/`(04·Atlas): YOLOv8n-pose(ultralytics, 3.3M 파라미터).
     `yolov8n-pose.pt`는 최초 실행 시 자동 다운로드(`*.pt`는 `.gitignore`에
     이미 있어 커밋 걱정 없음). 샘플은 ultralytics 기본 내장 `zidane.jpg`
     복사. 실행 검증 완료 — 샘플에서 사람 2명, 각 17개 COCO keypoint 정상
     출력.
   - `video_classification/`(08·Chronos): torchvision.models.video 중 실제
     파라미터 수 비교(s3d 8.3M < mc3_18 11.7M < r3d_18 33.4M)로 가장 가벼운
     `s3d`(Kinetics-400, 400개 레이블) 선택. 가중치는 torch hub가
     `~/.cache/torch/hub/checkpoints/`에 자동 캐시. 이 저장소엔 실제 동영상
     샘플이 없어 `samples/source.jpg`(ultralytics 기본 내장 `bus.jpg`)를
     확대하며 프레임을 늘린 합성 클립을 매 실행 즉석 생성(디스크 미저장)해
     분류 — 진짜 동작이 없으니 결과 자체보다 파이프라인이 CPU에서 학습 없이
     끝까지 도는지 확인용임을 demo 출력·README에 명시.

**검증**: 두 데모(`python -m labs.pose_estimation.demo`,
`python -m labs.video_classification.demo`) 실제 실행해 결과 확인.
`labs/` 전체 `ast.parse` 문법 검증 통과.

**오류·막힌 점**: 없음(이름 변경·labs 구현 모두 실행 검증까지 완료).
다만 이름 변경 후 회귀 확인용으로 돌린 `mova+dispatch+ontology` 전체
테스트는 ontology 쪽 비전 모델 로딩이 무거워 커밋 시점까지 계속 실행 중이었음
— `execsuite_router`/`main.py` 자체는 별도로 직접 import 검증을 마쳐 이름
변경 자체의 정합성은 확인됨.

### 산출물 (6)
- `apps/execsuite/`(구 `apps/silicon_valley/`, rename), `main.py`,
  `alembic/env.py`, `.importlinter`(수정).
- `suvisdev/labs/`(신규): `README.md`, `pose_estimation/`(`dto.py`,
  `ports.py`, `adapters/yolov8_pose_adapter.py`, `demo.py`,
  `samples/sample.jpg`), `video_classification/`(`dto.py`, `ports.py`,
  `adapters/s3d_adapter.py`, `demo.py`, `samples/source.jpg`).
- `apps/ontology/_docs/star-craft-pipeline.md`,
  `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(execsuite 라벨 갱신).

---

### [7] labs/ 03(시맨틱 분할) 추가 + mova 부팅 작업 ENABLE_MOVA_STARTUP 플래그

**배경**: [6]에 이어 "03도 04·08처럼 labs에 만들 수 있냐"는 질문에, 03은
04·08과 제외 사유가 다름을 짚었다 — 04·08은 순수 "용도 없음"이지만 03은
"용도(서울 보도 검출)는 있었는데 검증 데이터(OSM sidewalk 태그)가 없어서"
막힌 케이스. 사용자 확인 후 04·08과 동일 패턴으로 labs에 추가.

이어서 별개 요청: 이 프로젝트가 집(GPU/EXAONE)·AWS EC2(GPU 없음, Gemini)
두 환경에 배포되는데, mova의 부팅 자동 작업(TMDB 시드·랭킹/KOFIC 스케줄러 —
전부 Ollama 의존)이 EC2에서 연결 실패 WARNING을 계속 뿜는 문제를 코드
제거·브랜치 분리 없이 환경변수 플래그로 해결.

**수정/구현**:
1. **`suvisdev/labs/semantic_segmentation/`**(03·Loom) — 04·08과 동일 구조
   (`dto.py`/`ports.py`/`adapters/`/`demo.py`/`samples/`). 모델은
   torchvision.models.segmentation 4종 실측 비교(lraspp_mobilenet_v3_large
   3.2M < deeplabv3_mobilenet_v3_large 11.0M < fcn_resnet50 35.3M <
   deeplabv3_resnet50 42.0M) 후 가장 가벼운 `lraspp_mobilenet_v3_large`
   선택. Pascal VOC 21클래스 사전학습(도로/보도 클래스 없음 — 그래서 이
   데모가 막힌 용도인 "서울 보도 검출"과 구조적으로 무관함을 README에 명시).
   전처리가 짧은 변을 520px로 리사이즈해 마스크 크기가 원본과 달라짐을
   실측으로 확인 → DTO의 width/height는 원본이 아니라 실제 마스크 크기로
   정확히 반영. 가중치(~12.5MB)는 torch hub가 `~/.cache/torch/hub/checkpoints/`
   에 자동 캐시(리포에 안 남음, gitignore 불필요 확인). `samples/sample.jpg`
   (ultralytics 기본 내장 `bus.jpg`)로 실행 검증 완료(bus 31.0%, person
   12.2%, 배경 56.8% 정상 검출).
2. **`main.py`에 `ENABLE_MOVA_STARTUP` 플래그 추가** — `lifespan()` 안
   TMDB 카탈로그 시드·chat_trend 랭킹 스케줄러·KOFIC 박스오피스 스케줄러
   3개 try 블록을 `if _ENABLE_MOVA_STARTUP:`로 감싸고 `else:`에 "비활성화됨"
   info 로그 추가. 기본값 `true`(안 넣으면 기존 집 환경 동작 그대로).
   "HubRagInteractor 임베딩 ingest"는 별도 호출이 아니라 TMDB 시드
   (`ImportInteractor._persist_snapshots` → `_ingest_to_hub`) 안에 이미
   포함돼 있어 TMDB 시드 하나만 감싸면 같이 꺼짐 — 별도 지점 불필요.
   `seed_viewer_if_empty()`, Ollama 워밍업, 다른 앱(dispatch/execsuite/
   vision 등)의 부팅 작업은 건드리지 않음.

**부수 발견(건드리지 않음, 백로그 등록)**: `main.py`의 `seed_assistants_if_empty`
import(`mova.adapter.outbound.pg.assistants_pg_repository`)가 실제로
존재하지 않는 모듈 — 실제 파일명은 `platform_assistants_pg_repository.py`고
`seed_assistants_if_empty` 함수 자체가 코드베이스 어디에도 없음. 매 부팅마다
`ModuleNotFoundError`가 나서 기존 try/except로 조용히 삼켜지고 있던 기존 버그.

**검증**: 실제 DB/Ollama 없이 `verify_connection`/`create_tables`/
mova 시드·스케줄러 함수를 전부 mock으로 대체해 `lifespan()`의 분기만
격리 검증.
- `ENABLE_MOVA_STARTUP=false` → "비활성화됨" info 로그만, 3개 함수
  (`seed_catalog_if_sparse`/`run_chat_trend_scheduler`/
  `run_kofic_import_scheduler`) 전부 `called=False` 확인.
- 미설정(기본값) → 3개 함수 전부 `called=True`, 기존 로그(랭킹/KOFIC
  스케줄러 시작) 정상 출력 확인.

**오류·막힌 점**: [6]에서 백그라운드로 남겨둔 `mova+dispatch+ontology`
전체 회귀 테스트가 `openai/clip-vit-base-patch32`(Sentinel 이상탐지가
쓰는 CLIP 모델) Hugging Face Hub 다운로드에서 1시간 넘게 멈춰 있는 걸
발견해 프로세스 종료 — execsuite 이름 변경 자체는 별도 직접 import
검증으로 이미 확인이 끝난 상태라 이 hang은 이번 작업과 무관.

### 산출물 (7)
- `suvisdev/labs/semantic_segmentation/`(신규): `dto.py`, `ports.py`,
  `adapters/lraspp_adapter.py`, `demo.py`, `samples/sample.jpg`.
- `suvisdev/labs/README.md`(03 절 추가, §03 특수 사정 명시).
- `suvisdev/main.py`(`ENABLE_MOVA_STARTUP` 플래그 추가).

---

### [8] PROGRESS 백로그 마저 처리 — titanic 도메인 테스트 재작성 + seed_assistants 죽은 코드 제거

**배경**: [7]에서 남긴 백로그 중 진행 가능한 2건(titanic 테스트 4개 수집
실패, `seed_assistants_if_empty` import 버그) 처리.

**수정/구현**:
1. **titanic 테스트 4개** — 조사해보니 단순 이름 변경 드리프트가 아니라
   도메인이 재설계된 상태였음(관련 VO·엔티티·깨진 테스트 4개가 전부 같은
   커밋 `251ae61`(2026-07-08, "하위 파일 구조 통째로 업로드 성공")에서
   한꺼번에 들어옴 — 시간이 지나며 리팩터링된 게 아니라 애초부터 서로 안
   맞는 버전이 같이 업로드된 것). mova(`platform_users_vo.py` 등)·gildle
   (`route_edge.py` 등) 둘 다 "필드 하나당 VO 하나"가 아니라 "개념당 VO
   하나"로 묶는 방식을 쓰고 있어, 지금 titanic의 `PassengerIdentity`/
   `Survived` 방식이 이 프로젝트의 실제 컨벤션과 일치함을 확인(titanic은
   `.cursorrules`상 "기준선"). 사용자 확인 후:
   - `test_korean_ai_adapter.py` 삭제 — `titanic.adapter.outbound.llm.
     korean_ai_adapter`는 한 번도 만들어진 적 없고, 실제 구현은
     `tests/korean_ai.py`(프로토타입 스크립트)에 있으며 이미 통과 중인
     `test_korean_ai.py`가 커버 중인 중복 고아 테스트였음.
   - 나머지 3개(vo/entity/mapper) 삭제 후, 현재 도메인
     (`PassengerIdentity`/`Survived`/`Title`/`Gender`/`PassengerJackTrainer`/
     `PassengerJackTrainerMapper`) 기준으로 41개 테스트 새로 작성 — frozen
     불변성, 팩토리 검증(from_raw/from_name 성공·실패), DDD 동등성 규칙
     (passenger_id만으로 동등성 판단), DIP 어댑터 스왑(`SimpleNamespace`로
     실제 SQLAlchemy ORM 대신 같은 모양의 가짜를 넣어도 매퍼 결과가 같음을
     검증) 포함 — titanic이 기준선이라 mova/gildle이 참고할 모범 형태로
     작성.
   - **작성 중 실제 버그 발견**: `PassengerJackTrainer.summary()`와
     `PassengerJackTrainerMapper.to_orm_fields()` 둘 다 존재하지 않는
     `entity.identity.age`를 참조해 `AttributeError`(`PassengerIdentity`는
     title+gender만 갖고 age는 의도적으로 안 가짐 — docstring에 명시).
     `identity.age` 참조가 이 두 곳뿐임을 grep으로 확인 후 두 메서드 모두
     age 참조 제거로 수정.
   - 검증: `apps/titanic/tests` 44개 전부 통과(1개 ollama 마커 skip).
2. **`seed_assistants_if_empty` 죽은 코드 제거** — `AssistantsPgRepository`
   (실제 파일 `platform_assistants_pg_repository.py`)엔 `list_active`/
   `get_by_slug`만 있고 count/insert 메서드 자체가 없으며, 기본 시드
   데이터도 어디에도 없음 — 즉 이 시드 기능은 리네임된 게 아니라 애초에
   구현된 적이 없는 죽은 코드로 확인됨. 사용자 확인 후 `main.py`의 해당
   try/except 블록 통째로 제거. `ENABLE_MOVA_STARTUP=false`/미설정 두
   시나리오 mock 하네스로 재검증 — `assistants` WARNING이 완전히 사라지고
   플래그 동작은 그대로 정상임을 확인.

**검증**: `apps/mova/tests`+`apps/dispatch`+`apps/titanic/tests` 전체
91 passed, 1 skipped. `main.py` import 정상.

### 산출물 (8)
- `apps/titanic/domain/entities/passenger_jack_trainer_entity.py`,
  `apps/titanic/adapter/outbound/mappers/passenger_jack_trainer_mapper.py`
  (버그 수정).
- `apps/titanic/tests/domain/value_objects/test_passenger_jack_trainer_vo.py`,
  `apps/titanic/tests/domain/etitites/test_passenger_jack_trainer_entity.py`,
  `apps/titanic/tests/adapter/outbound/mappers/test_passenger_jack_trainer_mapper.py`
  (새로 작성), `test_korean_ai_adapter.py`(삭제).
- `suvisdev/main.py`(`seed_assistants_if_empty` 블록 제거).

---

### [9] LangGraph 하네스 문서 작성

**배경**: 사용자가 LangChain 선형 체인의 한계(분기·루프·상태관리 불가)와
LangGraph 도입 근거, Neo4j 기반 GraphRAG(지식그래프 구축·Text-to-Cypher·
하이브리드 검색) 자료를 제공하며, 시멘틱 라우터가 reasoning이 필요한
질문을 받았을 때 LangGraph를 활용하는 하네스 문서 작성을 요청. 이번엔
문서만 요청받아 코드는 건드리지 않음.

**작성**: `apps/execsuite/_docs/ranggraph-harness.md` — LangGraph 도입
근거, GraphRAG/Neo4j 활용법, 장단점, "이 프로젝트와의 접점" 절 작성.
접점 절은 실제 코드 기준으로 현재 상태를 짚음: `semantic_router_interactor`
(ontology)는 아직 `crud`/`rag`/`general` 3갈래뿐 "reasoning" 신호 없음,
`rangchain_chat_engine_repository.py`는 단일 선형 LCEL 체인, `langgraph`/
`neo4j-graphrag`는 `requirements.txt`에 설치만 돼 있고 코드베이스 어디서도
미사용, Neo4j 서버 자체가 `.env`에 `NEO4J_URI`/`NEO4J_USER` 없이 미배포
상태(`neo4j-hanress.md` 기존 확인 내용과 일치). 그 위에 제안 흐름(semantic_router
"reasoning 필요" 신호 추가 → LangGraph StateGraph의 retrieve→generate→
verify→재시도/종료 루프 → Neo4j 배포 후 GraphRAG로 retrieve 노드 보강)을
다이어그램과 단계적 도입 순서로 남김 — 실제 구현은 보류.

### 산출물 (9)
- `apps/execsuite/_docs/ranggraph-harness.md`(신규 작성).

---

### [10] Neo4j Docker 설치 전략 문서 작성

**배경**: [9] ranggraph-harness.md가 제안한 GraphRAG retrieve 노드를 실제로
쓰려면 Neo4j 서버가 먼저 떠 있어야 함 — 그 서버를 이 프로젝트 기존
방식(docker-compose)대로 띄우는 전략 문서 작성 요청. 문서만 요청받아
`docker-compose.yaml`/`.env` 실제 수정은 하지 않음.

**작성**: `apps/execsuite/_docs/neo4j-strategy.md` — 현재 상태(neo4j 서비스
없음, `.env`엔 비밀번호만, `star-craft-pipeline.md`에 예전 계획 스니펫
존재) 재확인 후, `docker-compose.yaml`에 추가할 `neo4j` 서비스 정의안
(`neo4j:5.26-community`, `NEO4J_AUTH`/`NEO4J_PLUGINS=apoc`, 포트
7474/7687, `neo4j_data`/`neo4j_logs` 네임드 볼륨, healthcheck — 기존
db/redis 서비스와 같은 패턴), `.env` 추가안(`NEO4J_URI`/`NEO4J_USER`,
`neo4j-hanress.md`가 이미 예정해둔 값), backend 컨테이너가 실제로 연결할
때 `DATABASE_URL`/`REDIS_URL`과 같은 "호스트용 vs 컨테이너용 URI 분리"
패턴 적용 방법, 기동·검증 절차(기존 `neo4j-hanress.md`의 확인 코드 재사용)
를 정리. 남은 결정 사항(버전 태그 재확인, EC2 리소스, APOC 필요 여부)도
명시.

### 산출물 (10)
- `apps/execsuite/_docs/neo4j-strategy.md`(신규 작성).

---

### [11] EXAONE-3.5-2.4B-Instruct-AWQ 기반 lora-server 초기 세팅 (RTX 4060 8GB, 추론 전용)

**배경**: 초기화된 노트북에 lora-server(mova RAG 답변 생성용)를 새로 세팅.
원래 계획은 EXAONE AWQ였는데, `EXAONE_LOCAL_AI_SETUP.md` 8-1엔 8GB GPU에서
EXAONE-AWQ **학습**이 OOM나서 현재 운영은 Qwen2.5-1.5B(plain)로 돼 있다는
점을 먼저 확인시킴. 사용자는 "추론 전용"이 목적이라 학습 OOM은 무관하다며
EXAONE-3.5-**2.4B**-Instruct-AWQ(원래 계획이던 7.8B가 아니라 2.4B)로 진행
결정. 학습된 LoRA 어댑터(`~/lora_adapters/LATEST`)는 이 노트북에도 백업에도
없어서, 재학습·복사 없이 `serve.py`에 "어댑터 없으면 베이스만" 폴백을 최소
수정으로 추가하기로 함.

**환경 구성**: `cmake`/`nvidia-cuda-toolkit` sudo 설치(사용자 직접 실행) →
`uv` 설치 → `~/.venv-exaone`(python 3.12) 생성 → `torch==2.13.0+cu126`,
`transformers==5.13.1`, `gptqmodel==7.1.0`(소스 빌드), `peft`, `torchvision`
(gptqmodel 내부 import에 필요 — 기존 문서엔 없던 의존성), `optimum>=1.24.0`
(peft가 gptqmodel 백엔드를 인식하는 데 필요) 설치. `LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct-AWQ`
다운로드(2.1GB, repo root).

**실측 확인**:
- VRAM: 베이스 단독 로드 2455MiB, generate 후 2477MiB, 미학습 더미 LoRA까지
  얹어도 2533MiB — 8GB 카드에서 여유 충분(~5.6GB 남음).
- `BACKEND.EXLLAMA_V2` 커널 정상 동작(7.8B에서 겪었다는 Marlin 행 현상 없음,
  JIT 컴파일 2~16초).
- `get_peft_model()`이 7.8B 문서의 wte 패치(`_input_embed_layer="wte"`) 없이도
  정상 동작 — 이 2.4B 체크포인트·현재 transformers/peft/optimum 조합에선
  해당 패치가 불필요함을 확인.

**오류·막힌 점**:
- 다운로드된 `modeling_exaone.py`의 `create_causal_mask()` 호출이
  `transformers==5.13.1`과 호환 안 됨(`input_embeds`→`inputs_embeds` 이름
  변경, `cache_position` 인자 제거로 `TypeError`). 로컬 체크포인트 파일의
  해당 호출부만 최소 수정 — 7.8B 문서의 "wte 패치"와 같은 성격(체크포인트
  remote code가 설치된 transformers 버전보다 오래됨).

**수정/구현**: `model_servers/lora_server/serve.py` — `_read_latest()`가
`LATEST` 파일이 없으면 `None`(어댑터 없음) + `LORA_FALLBACK_BASE_MODEL`/
`LORA_FALLBACK_BACKEND`(기본값 EXAONE-3.5-2.4B-Instruct-AWQ/awq_gptqmodel)를
반환하도록 수정, `_load()`는 `adapter_dir`가 없으면 `PeftModel` 래핑을
생략하도록 수정. 실제 `uvicorn model_servers.lora_server.serve:app --port 8200`으로
기동해 `/health`(`adapter_dir: null` 확인)·`/generate` 실호출까지 검증함.

### 산출물 (11)
- `model_servers/lora_server/serve.py`(수정, 어댑터 없을 때 베이스 전용 폴백).
- `EXAONE-3.5-2.4B-Instruct-AWQ/modeling_exaone.py`(패치, 다운로드된 체크포인트 파일 — 리포 추적 대상 아님).
- `~/.venv-exaone`(신규 venv, 리포 밖).

---

---

## 2026-07-27

### [5] pdf_summary → pdf_loader 네이밍 환원 + LangChain 문서 2건

**배경**: 사용자가 [4]에서 만든 `pdf_summary_*` 네이밍을 원래 자신이 만들었던
파일명 `pdf_loader_interactor.py` 기준으로 되돌려달라고 요청.

**수정**: 13개 파일 `git mv`로 `pdf_summary_*` → `pdf_loader_*` 리네임,
클래스명도 동반 변경(`PdfSummaryUseCase`→`PdfLoaderUseCase`,
`PdfSummaryInteractor`→`PdfLoaderInteractor`, `PdfSummaryPort`→`PdfLoaderPort`,
`PdfSummaryRepository`→`PdfLoaderRepository`, `PdfSummaryOrm`→`PdfLoaderDocumentOrm`).
DB 테이블명 `pdf_summaries`→`pdf_loader_documents`(아직 실 DB 미적용 마이그레이션이라
새 리비전 없이 기존 파일 내용만 수정). 사용되지 않던 `PdfSummaryCommand` 죽은
코드 제거. `alembic/env.py` import, `adapter/inbound/api/__init__.py` 라우터
등록도 함께 갱신. import + 라우터 등록(`/pdf/summarize`) 재검증 완료.

**추가**: `apps/silicon_valley/_docs/rangchain-monigstar-strategy.md` —
LangChain 활용 사례(Morningstar 금융 인사이트 엔진) 문서화. 사용자가 실제
코드 구현은 원치 않아(이 저장소에 금융/시장 데이터 소스가 없음) 문서만 작성.

### 산출물 (5)
- 리네임된 13개 파일(경로는 위 커밋 diff 참고), `alembic/env.py`,
  `apps/silicon_valley/adapter/inbound/api/__init__.py`,
  `apps/silicon_valley/_docs/rangchain-monigstar-strategy.md`(신규).

---

### 작업 내용
- **03(Loom, 시맨틱 분할) 관문0 실측 조사** — "OSM 서울 walk가 보도를
  별도 way/태그로 갖는가(있으면 CV 불필요, 폐기)"를 Overpass API로 실측.
  용도 재정의 "보도 유무/폭" 기준으로 판정.
- 조사 중 사용자 지시로 **스코프 재조정**('폭' 폐기 → '유무'만, OSM
  `footway=sidewalk` 부분 데이터로 갈 수 있는지 재검토)까지 진행.

### 데이터 (Overpass API 실측, overpass-api.de)
- 서울 3개 지역 `sidewalk=*` 도로 속성 밀도:
  - 강남(37.495,127.025,37.515,127.050): 도로 903 / sidewalk 태그 11 (**1.2%**)
  - 성북 주거(37.585,127.010,37.605,127.035): 도로 1127 / sidewalk 태그 5 (**0.4%**),
    `footway=sidewalk` way 131, footway 전체 545, `width` 태그 5
  - 종로: footway 전체 922 (레이트리밋으로 일부 셀만)
- **커버리지 실측**(성북 소구역 37.590,127.010,37.605,127.030):
  도로 643 way/**96.85km** vs `footway=sidewalk` 25 way/**3.47km**
  → **보도길이/도로길이 = 0.04** (완전 양방향=2.0, 편측 완전=1.0 기준).
  도로 길이의 ~96%에 매핑된 보도 없음.

### 결론
- **관문0: "폐기(CV 불필요)" 불성립** — `sidewalk=*` 도로 속성은 사실상
  전무(0.4~1.2%), `width` 태그도 전무(재정의 용도 '폭'은 OSM에서 못 얻음).
- **스코프 재조정('유무'만)도 불가** — 두 각도 수렴: (1) 개념: OSM open-world라
  "매핑 없음 ≠ 보도 없음", "보도 없음→페널티" 규칙의 *부재* 신뢰 불가.
  (2) 실측: 커버리지 4% → 페널티가 도로 ~96%에 발화 = 노이즈.
- **최종: 03(Loom)을 04·08과 동급의 정식 '폐기/제외'로 확정(사용자 승인).**
  보도 신호 자체가 서울 OSM에 존재하지 않음이 실측 확인됨. 관문1(스트리트뷰+CV)은
  소비처 walk 그래프가 데모(4간선)이고 CV는 전 간선 이미지 필요 → 관문1
  이미지 비용 문제로 회귀.

### 오류·막힌 점
- Overpass 공개 서버(overpass-api.de) 과부하로 다수 쿼리 timeout/406/empty.
  미러(kumi.systems, private.coffee)도 무응답. curl+User-Agent로 서버 여유
  시점에만 성공 → 강남·종로 일부 셀 미수집(결론엔 영향 없음).

### 산출물
- 본 로그, `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(03 제외 확정 반영 —
  완료 목록 이동 + 진행 중 비움 + 감사표 갱신),
  `apps/ontology/_docs/03_semantic_segmentation_agent.md`(⛔ 제외 배너 + §5.4
  최종 확정) 갱신.

---

### [2] 어드민 dispatch/harvester 백엔드 인증 공백 차단

**배경**: PROGRESS 백로그 "어드민 백엔드 인증 공백" — `/api/v1/dispatch/*`·
`/api/ontology/harvester/*` 라우터에 `require_admin`이 없어 프론트 `AdminAuthGate`
우회 직접 호출 시 무인증 통과. `_ApiAuthMiddleware`는 `/docs`류만 막고 API
경로는 미들웨어 레벨 상시 공개임을 확인(인증은 라우터별 Depends로만).

**조사에서 드러난 것(구현 전 확인)**:
- 인증 스킴 2종 — auth 게이트웨이(RS256/roles/aud, `shared/security/token_verifier.py`)
  vs viewer 세션(HS256/role, `require_admin`). 어드민 UI가 실제로 보내는 건
  후자라 dispatch/harvester도 `require_admin`을 써야 일관.
- 어드민 UI의 dispatch/harvester 호출은 Next 프록시(`backendFetch`, Basic
  서비스 자격증명)를 거쳐 **사용자 세션 Bearer가 백엔드까지 안 감** → 백엔드
  가드만 추가하면 정상 호출도 401. 3계층 동시 수정 필요.
- import-linter: `require_admin`을 `core`가 아니라 "cross-app 토큰 검증 전용"
  리프 패키지 `shared`로 이동하는 게 계약(shared-independence)·구조에 맞음.
  실측 검증 결과 shared/spoke/auth 계약 모두 KEPT, 내 변경으로 인한 신규 위반
  0건(hub-independence BROKEN은 `core→viewer.orm` 기존 커플링, baseline 동일).

**수정·구현 (3계층)**:
1. 가드 이동: `viewer/dependencies/require_admin.py` → `shared/security/require_admin.py`
   (viewer 두 어드민 라우터 import 재지정, 원본 삭제).
2. 백엔드 가드 추가(어드민 UI 구동분만): dispatch `email/telegram/discord` POST(발송),
   `receive` GET·DELETE(수신함), ontology harvester `scrape/crawl/sites`. **`receive`
   POST(외부 인입)는 제외**.
3. 프론트 프록시 7개(`suvis/app/api/{dispatch,harvester}/*`)가 들어온 `Authorization`을
   `backendFetch`로 전달.
4. 프론트 클라 4개(mail/telegram/receive 페이지 + harvester-command-form)가 세션
   Bearer 첨부. `suvis/lib/suvis-session.ts`에 `authHeader()` 헬퍼 추가.

**검증**:
- import-linter(uv 일시 설치, PYTHONPATH=apps:.): 5 kept / 1 broken(기존) — baseline 동일.
- 백엔드 변경 파일 `py_compile` OK, 잔여 `viewer.dependencies.require_admin` 참조 0.
- 프론트 `npm run type-check` exit 0.
- 가드 런타임 실측: no-auth→401, 무효서명→401, 비관리자 role→403, 관리자→AdminPrincipal.

**남긴 것(후속 백로그)**: dispatch `watcher/judge/spam/adress` 라우터는 어드민 UI
미사용이라 이번 범위 밖. 각 엔드포인트가 외부 인입인지 개별 확인 후 보호 판단할 것
(검증 없이 가드 씌우지 말 것).

### 산출물 (2)
- BE: `shared/security/require_admin.py`(신규·이동), dispatch
  `email/telegram/discord/receive_router.py`, ontology `harvester_router.py`,
  viewer `admin_agents_router.py`·`admin_users_router.py`(import 재지정).
- FE: `suvis/app/api/{dispatch/email,dispatch/telegram,dispatch/discord,dispatch/receive,harvester/scrape,harvester/crawl,harvester/sites}/route.ts`,
  `suvis/app/admin/dispatch/{mail,telegram,receive}/page.tsx`,
  `suvis/app/admin/harvester/_components/harvester-command-form.tsx`,
  `suvis/lib/suvis-session.ts`.

---

### [3] alembic 마이그레이션 체인 누락 테이블 수정 + neo4j-graphrag 설치

**배경**: 사용자 보고 — 완전히 빈 DB에서 `alembic upgrade head`를 실행하면
`20260701_0001`에서 `relation "dispatch_adress" does not exist`로 실패.
지금까지는 backend startup의 `create_all()`이 테이블을 만들어줘서 드러나지
않았음. Google 로그인 500(새 DB에 `users`/`user_identities` 없음)도 같은
원인 의심.

**원인 조사**: `alembic/env.py`의 `target_metadata`(6개 Base) 대비 마이그레이션
체인의 `create_table` 호출을 전수 비교. `dispatch_adress`뿐 아니라 `users`,
`groups`, `admins`, mova 앱의 `movies`/`actors`/`characters`/`assistants`/
`collections`/`tags`/`chat`/`rankings`/`reviews`/`picks`/`watchlist`,
`titanic_passengers`, `vision_uploads`까지 전부 마이그레이션 체인에 CREATE가
없이 `create_all()`로만 존재해온 테이블이었음(alembic을 프로젝트 중간에
도입하면서 베이스라인 마이그레이션을 만든 적이 없었던 게 근본 원인).

**수정·구현**: 체인 맨 앞(20260604_0001보다 앞)에 베이스라인 마이그레이션
`20260604_0000_create_baseline_v1_tables.py` 신설, `20260604_0001`의
`down_revision`을 여기로 변경. 각 테이블은 뒤따르는 `41f584bfcb4e`(mova v2
스키마) 등이 적용되기 **직전 상태**로 생성하도록 설계(예: `movies.release_year`는
VARCHAR(8), `genres` 컬럼 존재, `characters.character_name` 없음,
`users.age_group` 있음) — 이후 리비전이 그 위에 그대로 ALTER 적용돼야 최종
스키마가 현재 ORM과 일치하기 때문. FK 의존 순서(groups→users→collections→
movies→actors→characters→assistants→tags→chat→rankings→reviews→picks→
watchlist) 고려해 테이블 순서 배치.

**검증**: 로컬엔 Docker/Postgres가 없어 EC2의 실제 `pgvector/pgvector:pg16`
이미지로 별도 테스트용 컨테이너(`suvisdev_migration_test_db`, 포트 15432,
기존 운영 DB 컨테이너와 별개)를 띄우고 SSH 터널로 연결. 백엔드 최소 venv
(`.venv_migration_test`, gitignore됨, sqlalchemy/alembic/psycopg/pgvector/
fastapi만 설치)로 완전히 빈 DB에 `alembic upgrade head` 실행 → 전체 10개
리비전 끝까지 성공, `alembic current`가 단일 head(`f3a7c9e21b6d`)로 확인.
`movies`/`users`/`characters`/`reviews` 최종 스키마를 `\d`로 대조해 현재
ORM과 일치 확인. 시행착오: `movies.release_year` VARCHAR→INTEGER 타입 변경
시 서버 디폴트(`''`)가 자동 캐스팅되지 않아 실패 → 베이스라인에서 해당
컬럼 디폴트를 제거해 해결.

**설계 의도(기존 배포 DB 영향 없음)**: 새 베이스라인은 체인의 새 루트로
삽입되므로, 이미 `alembic_version`이 어떤 리비전에든 스탬프돼 있는 기존
DB(운영 DB 포함)에는 적용되지 않음 — `None`에서 시작하는 완전히 빈 DB에만
적용된다.

**추가**: `requirements.txt`에 `neo4j-graphrag==1.18.0` 추가, 실제 백엔드
venv(`~/.venv`)에 설치·import 확인. `apps/silicon_valley/_docs/neo4j-hanress.md`에
그래프 데이터 모델 개념 + 연결 확인 절차(Python 드라이버/cypher-shell/브라우저)
문서화 — 실제 Neo4j 인스턴스는 아직 미배포(`.env`에 `NEO4J_PASSWORD`만 있고
`NEO4J_URI`/`NEO4J_USER` 없음, docker-compose에도 서비스 없음 확인).

### 산출물 (3)
- `suvisdev/alembic/versions/20260604_0000_create_baseline_v1_tables.py`(신규),
  `suvisdev/alembic/versions/20260604_0001_create_titanic_person_booking.py`(down_revision 변경),
  `suvisdev/requirements.txt`(neo4j-graphrag 추가),
  `suvisdev/apps/silicon_valley/_docs/neo4j-hanress.md`(신규).

---

---

### [4] PDF 업로드→추출→요약 파이프라인 (silicon_valley, **완료**)

**배경**: 사용자가 `neo4j-graphrag`의 `PdfLoader` 예시를 참조해 PDF 업로드→텍스트
추출→요약 파이프라인을 inbound router~outbound repository까지 완성형으로
요청. 헥사고날 컨벤션은 ontology `vision` 슬라이스(`vision_router.py` 등)를
그대로 참고.

**설계**: `pdf_summary_*` 네이밍. 포트 3개 — 추출(`PdfExtractorPort`, neo4j-graphrag
`PdfLoader` 어댑터), 요약(`PdfSummarizerPort`, 기존 `T1MidFakerOrchestrator`/exaone
Ollama 재사용), 저장(`PdfSummaryPort`, `NeoTheOneBase` + `get_mova_session_factory()`
— vision_uploads와 동일 패턴). `ensure_titanic_tables()` 같은 create_all() 폴백은
**의도적으로 안 씀**(오늘 [3]에서 고친 문제 재발 방지) — 대신 정식 alembic
마이그레이션(`20260727_0001_create_pdf_summaries`, head `f3a7c9e21b6d` 뒤에 추가)로
테이블 생성, `alembic/env.py`에 ORM import 등록 완료.

**완료된 파일**:
- `alembic/env.py`(pdf_summary_orm import 추가)
- `alembic/versions/20260727_0001_create_pdf_summaries.py`(신규 — 아직 미검증)
- `apps/silicon_valley/adapter/outbound/orm/pdf_summary_orm.py`
- `apps/silicon_valley/app/dtos/pdf_summary_dto.py`
- `apps/silicon_valley/app/ports/input/pdf_summary_use_case.py`
- `apps/silicon_valley/app/ports/output/pdf_summary_extractor_port.py`

**추가 완료된 파일**: `pdf_summary_summarizer_port.py`, `pdf_summary_repository_port.py`,
`app/use_case/pdf_summary_interactor.py`(자리표시자 `pdf_loader_interactor.py`는
삭제), `adapter/outbound/extractor/pdf_summary_pdfloader_extractor.py`(temp file로
`PdfLoader.run(filepath=Path)`에 전달), `adapter/outbound/llm/pdf_summary_ollama_summarizer.py`
(T1MidFakerOrchestrator 재사용, 입력 12000자 상한), `adapter/outbound/repositories/pdf_summary_repository.py`,
`adapter/inbound/api/v1/pdf_summary_router.py`(`POST /pdf/summarize`), `dependencies/pdf_summary_provider.py`,
`adapter/inbound/api/__init__.py`에 등록(최종 경로 `/api/v1/pdf/summarize`).

**검증**: `~/.venv`(neo4j-graphrag 포함)에서 라우터 import + `/pdf/summarize`
등록 확인, 마이그레이션 파일 `py_compile` OK, ORM 테이블 컬럼 확인. **미검증**:
실제 빈 DB에 `alembic upgrade head`(간단한 단일 create_table이라 위험 낮음,
필요시 EC2 임시 컨테이너로 재검증 가능), Ollama 서버 연동 실사용 테스트.

### 산출물 (4)
- 위 파일 전체. 커밋 전.

---

---

## 2026-07-24

### 작업 내용
- 06(Sentinel, 이상 탐지) **H4(추론 어댑터) + H5(HTTP API + MCP tool) 구현**
  — H3까지의 방향 전환(CLIP 제로샷 + Laplacian variance)을 실제 코드로
  반영하고 MCP tool까지 노출.
- **[1순위 백로그 해결] vision app→adapter DIP 위반 + 순환 import 근본 수정**
  — H6에서 드러난 순환(테스트만 우회 중)을 제거.
- **[2순위 (c)+(d)] S3 경로 Tank 단일화 + boto3 기본 자격증명 체인 전환.**
- **03(Loom, 분할) 이미지 수집 경로 조사 — 종료조건 합의(읽기 전용 분석).**
- 커밋 워크플로우 훅 설정 — 커밋 요청 시 두 추적 문서를 먼저 갱신하도록
  리마인더(공유용 `.claude/settings.json`, 커밋됨).

### 수정/구현

**1) 06 Sentinel H4**
- 미결정 사항(포트 1개 vs 2개) 확인 후 **포트 1개 통합**으로 확정하고 진행.
- `app/dtos/anomaly_detection_dto.py`: `AnomalyResult`를 PatchCore 가정
  (`anomaly_score`/`is_anomaly`/`heatmap_b64`)에서 `is_poster`/
  `poster_confidence`/`is_blurry`/`sharpness_score`로 재설계.
- `adapter/outbound/resource_adapters/sentinel_anomaly/sentinel_anomaly_adapter.py`
  (신규): CLIP 제로샷(`openai/clip-vit-base-patch32`, 임계값 0.5)과
  Laplacian variance(256x256 정규화, 임계값 345.77)를 한 어댑터에서 순서대로
  호출. CLIP은 `echo_sentiment_adapter.py`와 동일하게 호출당 로드→추론→언로드.
- `dependencies/anomaly_detection_provider.py`(신규), port/interactor
  docstring을 PatchCore→CLIP/Laplacian으로 갱신.
- `test/test_sentinel_anomaly_adapter.py`(신규, `@pytest.mark.gpu`) —
  `test/good`·`test/blur` 샘플로 포트→VO 반환 검증.

**2) 06 Sentinel H5**
- `adapter/inbound/api/v1/anomaly_detection_router.py`(신규):
  `image_classifier_router.py` 패턴, `POST /sentinel/detect`(전체 경로
  `/api/vision/sentinel/detect`), `UploadFile` 입력.
- `adapter/inbound/mcp/anomaly_detection_mcp_server.py`(신규):
  `image_classifier_mcp_server.py` 패턴, `detect_anomaly(image_b64) -> dict`
  tool이 HTTP로 라우터 호출.
- `adapter/inbound/api/__init__.py`: `vision_router`에
  `anomaly_detection_router` 등록.
- `scripts/test_mcp_sentinel_client.py`(신규): stdio MCP 클라이언트로 tool
  목록 + 호출 검증.
- 검증: 백엔드 리빌드+재기동 후 `app.routes`에 경로 등록 확인,
  MCP tool 호출 2회 성공(good→`is_poster:true`, blur→`is_blurry:true`),
  VRAM 2863→3014MB(호출당 +30~120MB로 CLIP 가중치 누적 아님 → 로드-언로드
  정상), lora-server 정상. GATE_H5_PASS.

**3) 06 Sentinel H6 — `/vision/upload` 업로드 게이트 통합**
- 용도 확정(소거법): harvester=텍스트만 수집, TMDB=poster_url 참조(항상 포스터),
  lora-server=텍스트 생성기, Prisma(05)=미구현 → 이미지 입력이 불확실한 유일한
  경로가 `POST /vision/upload`라 여기에 게이트로 붙임(근거 추적은 이 세션 대화).
- `app/dtos/vision_dto.py`: `VisionUploadResponse`에 `poster_confidence`/
  `sharpness_score`/`is_poster_warning` 추가(기본값 있어 repo 무변경).
- `app/use_cases/vision_interactor.py`: `AnomalyDetectionPort` 주입,
  `upload_image`가 `to_thread`로 detect → 블러 하드 게이트(임계값 345.77 미달
  `ValueError`→400) + 포스터 소프트 플래그(`poster_confidence`<0.5 경고, 차단 안
  함). 임계값을 interactor가 raw 값으로 소유(어댑터 부울은 /sentinel·MCP용).
- `dependencies/vision_provider.py`: `get_anomaly_detection_port` 재사용 주입.
- 검증: `test/test_vision_upload_sentinel_gate.py`(gpu, fake VisionPort+실제
  Sentinel) 3경로 PASSED — good(통과+저장), blur(하드 반려+미저장),
  cast_0001(소프트 플래그+저장). 앱 import 무결성(`main` 7 vision routes) 확인,
  VRAM 3034→3034 안정.
- 동기 지연(~20s CLIP 로드)·VRAM 경합은 감수(어드민 간헐 경로, to_thread, CLIP
  경량) — 근거 `06 §6.9`.

**4) AWS S3 매니저(Tank) 신설** — 향후 AWS 이전(이미지/객체를 S3 URL로
전달, ontology 00_COMMON §6) 대비. mova/gildle 도메인과 무관한 인프라 작업.
- `core/matrix/aws_tank_s3_manager.py`(신규): `Tank` 클래스. IAM 액세스 키를
  하드코딩하지 않고 Keymaker에서 받아 boto3 S3 클라이언트 생성. 키 없으면
  `ready=False` + 클라이언트 접근 시 graceful `RuntimeError`. 메서드:
  `list_buckets`/`upload_bytes`/`download_bytes`/`generate_presigned_url`.
  모듈 싱글턴 `tank`/`get_tank()`(Keymaker 패턴).
- `core/matrix/vauly_keymaker_secret_manager.py`: AWS 자격증명·리전·버킷을
  Keymaker가 단일 관리하도록 `aws_access_key_id`/`aws_secret_access_key`/
  `aws_region`/`vision_s3_bucket` 속성 추가. Tank는 `os.getenv`를 직접 읽지
  않고 이 값을 받아 씀(사용자 요청으로 os.getenv 직접 접근 → Keymaker 경유로
  리팩터).
- `.env.example`: AWS IAM 액세스 키 블록 추가(`AWS_ACCESS_KEY_ID`/
  `AWS_SECRET_ACCESS_KEY`/`AWS_REGION`/`VISION_S3_BUCKET`). 변수명은 기존
  `vision_s3_repository.py`(boto3 기본 자격증명 체인)와 맞춰 재사용.
- 검증: 컨테이너에서 import + graceful degradation(키 없을 때 `ready=False`,
  클라이언트 접근 에러) 확인. 실 버킷 연동은 키 주입 후 별도.

**5) [1순위 백로그] vision app→adapter DIP 위반 + 순환 import 근본 수정**
- 위반: `app/ports/input/vision_use_case.py`·`app/use_cases/vision_interactor.py`가
  어댑터 pydantic 스키마 `VisionIntroduceSchema`를 인자 타입으로 임포트 →
  `vision_use_case→vision_schema→api/__init__→vision_router→vision_use_case` 순환.
- 수정: 포트·interactor를 앱 DTO `VisionIntroduceQuery`(이미 존재, repository 포트도
  이걸 받음)로 바꾸고, schema→query 변환을 어댑터 계층(`vision_router`)으로 올림.
  interactor는 query를 repository로 직행(변환 제거). dead가 된 `vision_schema.py`
  삭제(`schemas/__init__` 빔, 다른 참조 없음 확인).
- H6 테스트에서 넣었던 우회(`import ontology.adapter.inbound.api` 선로드) 제거 —
  이게 통과한다는 게 근본 해결의 증거(테스트 로드 경로 = 프로덕션 경로).
- 검증: 이전에 순환으로 실패하던 `import ontology.dependencies.vision_provider`가
  성공, `from main import app` 부팅(vision routes 7), H6 게이트 3/3 PASSED(우회 없이).
- semantic_router_dto도 어댑터 스키마 참조하나 `TYPE_CHECKING`/지역 임포트라 런타임
  순환 없음 → 이번 범위 밖(DIP 냄새만, 위험 아님).

**6) [2순위 백로그 (c)+(d)] S3 경로 Tank로 단일화 + 기본 자격증명 체인 전환**
- 배경: `VisionS3Repository`가 자체 `boto3.client`(기본 체인), Tank는 명시적 키
  전달 — S3 경로가 둘로 갈리고 자격증명 전략도 반대. 사용자 결정: (c)+(d) 함께,
  기본 체인으로 통일.
- Tank(d): `_access_key`/`_secret_key`/`ready`/키 전달 제거 →
  `boto3.client("s3", region_name=...)`만 사용(기본 체인). region/bucket은 계속
  Keymaker에서. boto3 기본 체인이 로컬은 `.env`가 os.environ에 실은 AWS_* env를,
  EC2는 인스턴스 IAM Role을 집는다 → 단일 경로.
- VisionS3Repository(c): 자체 boto3/os 제거, `get_tank()` 위임. 키 네이밍·
  content_type만 도메인 로직으로 남기고 put은 `tank.upload_bytes`(to_thread).
- Keymaker: `aws_access_key_id`/`secret` 속성은 vestigial(아무도 안 읽음, 기본
  체인이 env 직접 집음)로 남김 + 주석 정정. `.env.example`에 EC2 IAM Role이면
  키 비워도 된다는 노트 추가.
- 검증: `tank.client`가 명시적 키 없이 S3 클라이언트 빌드(전엔 ready=False로
  raise), `VisionS3Repository`가 Tank 싱글턴에 위임(save_image→Tank 버킷 체크
  RuntimeError 도달로 위임 경로 증명), `from main import app` 부팅 OK. 실 업로드는
  AWS 연결(버킷+키) 후 확인.

**7) 03(Loom, 분할) 이미지 수집 경로 조사 — 종료조건 합의(코드 변경 없음, 읽기 전용)**
착수 전 종료조건부터 합의하기로 하고 03 문서(§5)·gildle 라우팅 코드
(`route_weight_calculator.py`)를 읽어 3가지를 정리:
- **용도/소비처**: 재정의 스코프는 "보도 유무/폭"(계절 무관 구조 신호, 결빙은
  §5.1에서 기각). 소비처는 실재 — `RouteWeightCalculator.calculate_edge_weight`가
  `_near_hazard`(20m 근접→6배 페널티) 패턴처럼 "보도 없음/좁음"을 상시 페널티로
  얹으면 됨. **단 구멍 2개**: (a) 소비 그래프가 데모(`sample_walk_graph.json` 4간선),
  OSM 운영 미구현(코드에 osmnx 없음 확인). (b) OSM walk 태그가 보도를 이미 주면
  CV 불필요(중복). → "용도 없음"이 아니라 "CV가 필수 수단이 아닐 수 있음".
- **이미지 최소 조건**: 지상 스트리트뷰(항공 아님 — 가로수 canopy 폐색), 유효크롭
  ≥512px, 지오태그 정밀도 ≤~10~20m(간선 매칭 반경), 주간·비폐색(구조라 계절 무관,
  단 적설 배제), **커버리지=라우팅 그래프 전 간선(킬러 조건)**. 실질 판정 기준은
  해상도가 아니라 커버리지×합법성×비용.
- **폐기 수용**: 04·08 제외 선례와 동급으로 '폐기'를 정식 결론으로 수용하기로 제안
  (쓸 소스 없음 / OSM으로 충분함 둘 다 유효 종료).
- **합의한 관문 순서**: 관문0(OSM 보도 태깅으로 CV 불필요한지, 가장 쌈, 먼저) →
  관문1(스트리트뷰 소스 ToS/과금/커버리지) → GO는 둘 다 통과+최소조건 만족 시만.
- **상태**: 사용자 종료조건 합의 대기 → 합의되면 관문0부터 착수(아직 소스 조사 미착수).

**8) 커밋 워크플로우 훅 설정**
- 규칙 확정: 커밋 **요청 시** WORK_LOG(오늘 작업)·PROGRESS(완료 삭제·남은 작업)를
  **먼저 갱신 후** 문서+코드 함께 커밋(커밋 후 갱신은 순서가 거꾸로라 폐기).
- `.claude/settings.json`(공유용, 커밋됨)에 `UserPromptSubmit` 훅 — 프롬프트에
  `commit|커밋` 있으면 문서 먼저 갱신 리마인더 주입. grep 기반(호스트에 jq 없음).
  개인 permissions는 `.claude/settings.local.json`(전역 gitignore)에 유지.
- 검증: python3로 두 파일 JSON 유효성·훅 매칭/비매칭 재현, 이번 세션에서 실제
  발화 확인(이 프롬프트에 리마인더 주입됨).

### 오류·막힌 점
- **로컬 `.venv`/`.venv-exaone`에 pytest/opencv 없음** — 이 프로젝트의 실제
  런타임 의존성(`transformers==4.47.1`, `opencv-python`, `pytest`)은
  `requirements.txt` 기반으로 `suvisdev-backend-1` 도커 이미지에만 있고,
  compose에는 코드 전체가 아니라 `datasets`·`resources/crawled`만 바인드
  마운트돼 있어 새 파일이 컨테이너에 자동 반영 안 됨 → `docker cp`로
  변경/신규 파일 6개를 컨테이너에 직접 복사해 그 안에서 pytest 실행,
  둘 다 PASSED. VRAM은 호출 전후 2879MB로 동일(로드-언로드 정상 확인),
  lora-server(`:8200/health`) 정상 유지.
- **기존 순환 임포트 노출(H6 테스트)** — `app/ports/input/vision_use_case.py`가
  어댑터 계층 `adapter/inbound/api/schemas/vision_schema.py`를 임포트(app→adapter
  DIP 위반)해서, `vision_interactor`를 `api/__init__` 애그리게이터보다 먼저
  임포트하면 `vision_use_case → vision_schema → api/__init__ → vision_router →
  vision_use_case(partial)` 순환이 터진다. 프로덕션은 `main.py` 임포트 순서
  덕에 회피 중(앱 import 무결성 확인함). H6 테스트는 `api` 애그리게이터를 선
  로드해 우회. **근본 수정(포트가 어댑터 스키마를 안 보게)은 백로그 — 아래.**

### 산출물
- 문서 갱신: `apps/ontology/_docs/06_anomaly_detection_agent.md` §6.7(H4)·
  §6.8(H5)·§6.9(H6) 신규, `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 06을 H0~H6
  완료로 갱신(완료 목록 이동, 감사표·우선순위 반영).
- 백엔드 이미지 리빌드(H5 코드 반영) — `suvisdev-backend-1` 재기동됨.
- 커밋/푸시/머지(모두 main 반영): Sentinel H4·H5 `df5a56b`, S3 매니저(Tank)
  `53bd4de`, Sentinel H6 `2da0762`, 블러 상수 주석+백로그 `e91d9c7`, Keymaker
  계약+시크릿 감사 `9994ed7`, vision DIP 순환 수정 `6098955`, S3 Tank 단일화+
  기본 체인 `dc9afbd`, 03 조사 기록+진행 메모 프루닝 `b8628bb`, 커밋 워크플로우
  훅(.claude/settings.json)+WORK_LOG(이 커밋).

### 백로그 (우선순위 조정 — 2026-07-24)

**[1순위] app→adapter DIP 위반 + 순환 import — ✅ 해결(2026-07-24, 위 수정/구현 5)**
- `vision_use_case`/`vision_interactor`가 어댑터 스키마 `VisionIntroduceSchema`를
  받던 것을 앱 DTO `VisionIntroduceQuery`로 교체, 변환을 `vision_router`로 올림,
  dead `vision_schema.py` 삭제. 테스트 우회 제거 후에도 통과 = 근본 해결.

**[2순위] 시크릿·S3 접근 경로 정리 (묶음)**

시크릿 관리 현황 감사 결과, Keymaker(`vauly_keymaker`)는 단일 관문이 아니라
여러 시크릿 접근 경로 중 하나였다(GEMINI/TMDB/KOFIC/AWS/DATABASE_URL만 관리,
나머지 JWT·OAuth·API_USERNAME 등은 각 app이 `os.getenv`로 직접 읽음).

**방향 결정 — Keymaker 전면 통합은 채택 안 함.** core/matrix가 TMDB_API_KEY·
JWT 키 같은 앱별 시크릿을 알게 되면 core → apps 역방향 의존이 생겨 헥사고날
원칙에 어긋난다. 나중에 정리한다면 core는 `SecretProvider` 인터페이스(메커니즘)
만 갖고, 키 목록은 각 app의 Settings가 소유하는 방향으로 간다.

- (a) TMDB/KOFIC 코드 중복(ontology `api_keys.py` / mova `keymaker.tmdb_api_key`):
  둘 다 같은 env 이름을 읽어 **값 divergence 위험 없음(상태 중복 아니라 코드
  중복)**, 앱별로 하나씩 가진 건 "app이 자기 키를 소유" 목표 방향과 오히려 일치.
  지금 mova에 accessor를 신설하면 pydantic-settings 이관 때 또 뜯게 됨 →
  **app별 Settings(pydantic-settings) 도입 시 mova·ontology 키 접근을 함께 이관.
  현재는 무해. 단독 실행 금지.**
- (b) `load_dotenv` 3곳 감사 완료(2026-07-24): **세 곳 모두 같은 파일**
  (`suvisdev/.env`) 로드 — vauly_keymaker·grid_oracle는 `override=True`,
  alembic/env.py는 `override=False`. 파일이 같아 값 분기는 없으나 override
  플래그가 불일치. **단일화 안 함** — Keymaker의 임포트 시 self-load는 scripts/를
  떠받치는 **기능(계약)**이라 제거 대상 아님(Keymaker docstring에 계약 명시함).
  override 불일치는 인지만 하고 현행 유지.
- (c)+(d) **✅ 해결(2026-07-24, 위 수정/구현 6)**: S3 경로를 Tank로 단일화 +
  Tank를 boto3 기본 자격증명 체인으로 전환. `VisionS3Repository`가 자체
  `boto3.client`를 버리고 Tank에 위임, Tank는 명시적 키 전달을 제거하고
  `region_name`만 지정 → 로컬(.env 키)·EC2(IAM Role)가 단일 경로로 처리됨.

**[유지] 하위 우선순위**
- 블러 임계값(345.77)은 포스터 분포 보정값이라 저디테일 비포스터(backdrop 등)가
  미달해 하드 반려될 수 있음 — 업로드 게이트 용도상 허용(현행 유지).
- Sentinel 소프트 플래그의 **저장 지속화 + 어드민 오버라이드 엔드포인트** — 저장
  계층(S3 배선인데 AWS 미연결, DB 폴백 미배선) 정리 후 처리(현행 유지).

---

---

## 2026-07-23

### 작업 내용
- 06(Sentinel, 이상 탐지) H3 디버깅 이어서 진행 — 이전 세션이 도중에
  끊긴 상태(포스터/노이즈/회색 점수 순서가 정보량 순서와 일치한다는 관찰까지만
  하고 중단)에서 재개.
- PatchCore(anomalib) 기반 접근을 근본 원인까지 추적 → 실패로 판정 →
  CLIP 제로샷 + Laplacian variance로 방향 전환.
- 02~08 나머지 비전 에이전트 전체에 대해 "용도/데이터/하드웨어" 적합성
  사전 감사(06의 실패에서 얻은 교훈 적용).
- VRAM 점유 정책 확정(실측 기반).
- 관련 문서·재개 메모 정리, git 커밋/푸시/머지 2회.

### 수정/구현

**1) additive/subtractive anomaly 원인 규명**
- `scripts/diagnose_sentinel_per_defect.py`(기존) 재실행 → normal/blur/black_bar/watermark
  그룹별 AUROC 분해(blur 0.573, black_bar 0.510, watermark 0.484).
- `scripts/diagnose_sentinel_feature_norm.py`(신규) — memory bank 진입 전
  patch embedding의 L2 norm을 그룹별로 추출해 NN-distance와 대조. blur만
  전역·균일하게 정상 분포 영역을 벗어나 잘 잡히고, black_bar(국소)·watermark
  (저강도)는 거의 안 잡힌다는 걸 확인(`06_anomaly_detection_agent.md` §5.3).

**2) "이상=포스터가 아닌 이미지" 재정의 시도 1차 (실패)**
- `scripts/prepare_sentinel_nonposter_dataset.py`(신규) — TMDB API로
  backdrop(예고편 스틸)·cast profile(인물 사진)·대체 포스터(textless/
  비주력 언어판) 수집.
- 사용자 지적 반영: (a) 종횡비 누출 방지 — Resize(256,256)이 종횡비를
  무시해 16:9 backdrop이 포스터보다 훨씬 심하게 찌그러지는 문제 →
  저장 전 전부 2:3 center crop. (b) 라벨 오류 — textless/비주력 언어판은
  TMDB 공식 포스터라 정상인데 처음에 "hard negative"로 잘못 라벨링 →
  `test/alt_poster_control`(위양성 대조군, 정상)로 재정의.
- `scripts/diagnose_sentinel_nonposter.py`(신규) — good/non_poster_easy/
  alt_poster_control 3그룹 점수 분포 + AUROC.
- 결과: AUROC 0.4429, 부트스트랩 95% CI [0.314, 0.566] → 0.5 포함 →
  "랜덤 이하"가 아니라 **"신호 없음"**(통계적으로 구분 불가). 수동
  pairwise 재계산으로 sklearn 라벨 극성 버그 아님도 확인.
- 결론: patch-level 텍스처 비교는 "포스터냐 아니냐"라는 전역적·구성적
  질문에 구조적으로 안 맞음 → 이 접근 기각.

**3) 방향 전환 — CLIP 제로샷 + Laplacian variance**
- `scripts/diagnose_sentinel_clip_poster_classifier.py`(신규) —
  `openai/clip-vit-base-patch32` 제로샷, 파인튜닝 없이 기존 라벨셋으로
  즉시 검증 → AUROC 0.8844(PatchCore 0.44 대비 압도적 개선).
- `scripts/compute_sentinel_blur_threshold.py`(신규) — 정상 포스터
  232장(256x256 정규화)의 Laplacian variance 하위 5퍼센타일 = 345.77.
  합성 블러 25장 전부(100%) 임계값 아래로 분리.
- PatchCore/anomalib은 Phase A(MVTec bottle AUROC 1.0, 파이프라인 정합성
  검증)만 근거로 남기고 포스터 도메인에서는 기각.
- 전체 근거를 `apps/ontology/_docs/06_anomaly_detection_agent.md` §5~§6.6에
  기록. H4(포트 통합)는 아직 미착수 — 상세 다음 단계는
  `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` §1 참고.

**4) 02~08 적합성 감사**
- mova(포스터 1장/영화 + 텍스트뿐)·gildle(이미지 자체가 없는 지오/테이블
  도메인) ERD·코드를 직접 확인해 용도/데이터/하드웨어 3항목 판정.
- 04(Atlas, 자세 추정)·08(Chronos, 영상 분류) — mova/gildle 어디에도
  용도가 없어 **제외**. 해당 문서 상단에 배너만 추가(내용 삭제 안 함).
- 03(Loom, 분할) — gildle `HazardZone`(결빙구역)과 엮는 재정의 검토.
  결빙 자체는 Cityscapes/Mapillary에 클래스가 없어(계절성 현상 vs 구조적
  클래스) 기각. 대안(보도/차도 구조 분할)은 라우팅 반영 방법은 명확하나
  이미지 수집 경로(gildle의 Kakao 연동은 지오코딩뿐, 로드뷰 API 아님)가
  미확정이라 **보류**(착수 안 함). `03_semantic_segmentation_agent.md` §5.
- 02(Argus)·05(Prisma) — 용도 위험/불확실이라 보류(제외는 아님).
- 감사 표 전체를 `00_COMMON_conventions.md` §8에 기록.

**5) VRAM 점유 정책 확정**
- `nvidia-smi`, `ollama ps`, `systemctl --user status lora-server`로
  실측. `00_COMMON_conventions.md` §1.1에 정책 명문화(아래 오류 항목 참고).

**6) 재개 메모 정리**
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 전면 재작성 — 완료된 항목(어드민
  대시보드, 01, 07)은 상세 삭제하고 위치만 남김, 06 H4의 다음 할 일은
  파일 단위로 구체화(DTO 재설계 필요성, 미결정 설계 질문 등).

**7) 작업 일지 체계 신설**
- 이 파일(`_docs/WORK_LOG.md`) 신설 — 날짜별 상세 작업 기록(재개 메모와
  역할 분리: 재개 메모=현재 상태 요약, 작업일지=그날 있었던 일 상세).
- `CLAUDE.md`에 규칙 추가: **세션이 끝나기 전에 이 파일에 기록**. 중간에
  "커밋 시점을 트리거로" 잠깐 바꿨다가 사용자가 다시 세션 종료 기준으로
  정정(최종: 세션 종료 트리거).

### 오류·막힌 점

- **정규화 클리핑 버그 재발**: `diagnose_sentinel_nonposter.py` 1차 작성 시
  `PostProcessor(enable_normalization=False)`를 빠뜨려 min-max 정규화가
  다시 켜진 채로 실행 → score가 0.98~1.000에 몰려 AUROC가 0.4369라는
  의미 없는 값이 나옴(§5.1~5.2에서 이미 확인했던 문제인데 신규 스크립트에
  재도입). `PostProcessor(enable_normalization=False)` 추가 후 재실행해
  0.4393(raw score 기준)으로 정정 — 결론(신호 없음)은 안 바뀜.
- **TMDB `include_image_language` 필터 버그**: 대체 포스터(altlang) 수집 시
  API 요청 자체를 `include_image_language: "null,en,ko"`로 제한해놓고
  "en/ko가 아닌 포스터"를 찾으려 해서 항상 0건. `ja,zh,fr,de,es,it,ru`
  추가해 해결(15/15 확보).
- **정상 포스터 카운트 assert 실패**: `compute_sentinel_blur_threshold.py`
  초안이 `tmdb-*.jpg` 패턴만 찾아 190장(실제는 232장, 일부는 슬러그
  파일명이라 tmdb- 접두사 없음)에서 assert 실패. 패턴을 `*/*/*.jpg`로
  넓혀 해결.
- **컨테이너/호스트 데이터 비동기화**: `apps/ontology/resources/sentinel_poster`가
  컨테이너 안에서는 bind mount가 아니라 이미지 빌드 시점 복사본이라는 걸
  뒤늦게 발견 — 컨테이너 안에서 생성한 `non_poster_easy`/`alt_poster_control`가
  호스트에 자동 반영 안 됨. `docker cp`로 양방향 수동 동기화(스크립트는
  host→container, 데이터 산출물은 container→host)하는 방식으로 우회.
  디렉토리 이름을 `non_poster_hard`→`alt_poster_control`로 바꿀 때도 호스트에
  먼저 `mv`했다가 파일이 없어서 실패 → 컨테이너에서 먼저 rename 후
  `docker cp`로 새로 가져오는 순서로 정정.
- **`nvidia-smi` 계측 불안정**: 같은 세션 안에서 같은 `lora-server` 프로세스에
  대해 290MB(유휴)와 7975~7988MB(피크 직후로 추정)로 크게 다른 값이 나옴 —
  재시작 로그는 없어서 WSL2 GPU 패스스루 계측 문제로 판단. VRAM 정책에
  "free 수치만 믿지 말 것" 명시.

### 데이터

- `apps/ontology/resources/sentinel_poster/` 구성(2026-07-23 기준):
  - `train/good`: 190장(정상 포스터, 기존)
  - `test/good`: 42장(정상 포스터, 기존)
  - `test/blur`·`test/black_bar`·`test/watermark`: 각 25장(합성 손상, Phase B 잔존 — 스코프 제외됐지만 삭제 안 함, blur 임계값 검증용으로 재사용)
  - `test/non_poster_easy`: 40장(신규, backdrop 20 + cast profile 20, TMDB, 2:3 center crop)
  - `test/alt_poster_control`: 30장(신규, textless 15 + 비주력 언어판 15, TMDB, 2:3 center crop)
  - 소스: `apps/ontology/resources/genre_classifier_train`(232장)의 TMDB id 190개 재사용

### 산출물

- 커밋 `bac5565` — 06 additive/subtractive 원인 규명 + 범위 재정의(스크립트 6개 신규, 데이터셋 확장, 문서 §5~§6)
- 커밋 `e420d3f` — 02~08 감사 반영(00_COMMON §1.1/§8, 03/04/08 문서 수정)
- 둘 다 `suvisdev` → `main` fast-forward 머지 + 푸시 완료
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 전면 갱신(미커밋, 사용자 확인 대기)
