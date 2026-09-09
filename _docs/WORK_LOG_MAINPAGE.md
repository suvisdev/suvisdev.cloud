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
