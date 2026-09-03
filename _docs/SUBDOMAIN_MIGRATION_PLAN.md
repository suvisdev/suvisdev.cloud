# 서브도메인 이사 계획 — seuk(팀 프로젝트)만 (2026-09-03 결정 변경)

**2026-09-03 저녁 결정 변경(사용자)**: 개인 앱(mova·gildle)은 서브도메인으로
옮기지 않고 기존 경로(`suvisdev.cloud/mova`·`/gildle`)를 그대로 쓴다.
서브도메인 이사는 **팀 프로젝트 seuk만** 진행한다.
**AWS는 개인 계정 하나를 같이 쓴다**(같은 명의·결제수단이라 새 계정에
프리티어가 안 나옴 — 09-03 확인). 대신 계정 안에서 리소스를 분리한다:
Arda 전용 S3 버킷·SQS 큐·IAM 유저(`arda-server`, Arda 리소스만 권한).
**최종 결정(같은 날 밤)**: 개인 백엔드는 노트북으로 내리고 기존 EC2를
Arda 전용으로 전환(크레딧을 팀에만) — 아래 "개인 백엔드 EC2 → 노트북 이전".

## 개인 앱을 되돌린 이유

개인 포트폴리오 용도에 별도 앱·별도 배포 계획이 없어 서브도메인 서빙의
실익은 "주소가 제품처럼 보인다" 하나뿐인데, 비용은 실재했다.
- JWT가 localStorage라 **로그인 세션이 도메인별로 분리**된다.
- 백엔드 OAuth 복귀 주소가 `FRONTEND_URL` 하나로 고정
  (`apps/viewer/.../oauth_router.py`, `apps/auth/router.py`) — 서브도메인에서
  소셜 로그인하면 apex로 돌아와 세션이 엉뚱한 origin에 저장된다. 고치려면
  origin 화이트리스트 + state 저장 코드 변경 필요.
- 같은 페이지가 두 URL로 열려 대표 주소·검색엔진 중복 관리가 생긴다.

→ 리라이트 커밋 `0bef4f3`(`suvis/next.config.mjs`)은 되돌림. 짧은 주소가
필요해지면 서빙 대신 Cloudflare 리다이렉트 규칙(301 → `/mova`)으로 해결한다.

## 목표 배선도

```
suvisdev.cloud/mova      → 개인 Vercel(suvis) — 기존 유지 (변경 없음)
suvisdev.cloud/gildle    → 〃
api.suvisdev.cloud       → 노트북(teagy) 터널 replica (2026-09-03 밤 이전 완료)

seuk.suvisdev.cloud      → Vercel 프로젝트 arda (suvisdev 계정) — 완료
api.seuk.suvisdev.cloud  → 같은 AWS 계정의 **Arda 전용 새 EC2** (이전 대상)
```

- 팀 이전의 시의성: Arda 리스크 표의 "AWS 루트 계정이 이탈자 명의 —
  과정 종료 후 서버 소멸 가능". 본인 계정으로 옮기면 해소.

## GitHub 이전 — 완료 (2026-09-03 저녁)

- 구 조직 `Team-Seuk`은 owner가 woojeongalex 1명, 사용자는 member(Arda
  push 권한만) → Transfer 불가. 새 조직 **`Seuk-Team`** 신설(사용자 owner,
  `Team_Seuk`은 밑줄 불가·`Team-Seuk`은 중복이라 이 이름).
- 팀원 3명(cloverky·minahdev·woojeongalex) 초대 발송, 조직 기본 저장소
  권한 **write**로 설정(`gh api PATCH`).
- **`Seuk-Team/Arda`**(public, 사용자가 화면에서 빈 저장소 생성 — `gh repo
  create`는 분류기 차단) ← `git clone --mirror` + `git push --mirror`.
  검증: 브랜치 13/13 SHA 일치, 기본 main, main 366 커밋. `refs/pull/*`
  거부는 GitHub 숨김 ref 정상 동작. 이슈 9·PR 155 이력은 구 저장소에만
  남음(나중에 Transfer 받으면 그때 대체).
- `main` 브랜치 보호 설정 완료: PR 필수(승인 1, 새 푸시 시 기존 승인
  무효), force push·삭제 금지. **owner 예외 없음**(enforce_admins=true,
  사용자 요청) — 본인도 PR 필수.
- **mirror로 딸려온 옛 브랜치 12개 정리(09-03 저녁)**: main에 전부 포함된
  4개 + 대체·폐기된 8개 중 1개만 살림 — `fix/agent-test-tool-count`를
  main 위에 rebase해 **PR #1**(쓰기 도구 테스트에 create_schedule_proposal
  추가, 1줄). 나머지는 삭제 대상: 프론트 반응형 브랜치는 main의 09-02
  모바일 개편이 대체, `feat/agent-prompt-restructure`는 본인이 09-01 #154
  닫음(main과 중복), 닫힌 PR 4건(#26·#120·#126·#133)은 팀 결정, docs
  브랜치는 08-25 이후 main이 312커밋 앞섬. 삭제는 분류기 차단으로 사용자
  실행(구 저장소에 원본 남아 있어 손실 없음).
- **남은 것**: ① 팀원 remote 교체 `git remote set-url origin
  https://github.com/Seuk-Team/Arda.git` ② 구 저장소 Archive 요청(이중 푸시
  방지) ③ ~~Vercel 연결~~(완료, 아래 1) ④ Secrets(새 AWS 키) ⑤ 두 번째
  owner 지정 ⑥ PR #1 팀원 승인·merge.

## 개인 백엔드 EC2 → 노트북 이전 (2026-09-03 밤, 사용자 결정)

**결정**: 개인 EC2(m7i-flex.large, 크레딧 소모 월 ~70$)는 Arda 전용으로
돌리고, 개인 백엔드(mova·gildle·auth)는 **노트북(teagy, RTX 4060, 1TB)**에서
서빙한다. AWS 크레딧을 팀 프로젝트에만 쓰기 위함. 트레이드오프: 노트북이
꺼지면 개인 사이트 API 전부 다운(프론트 Vercel만 생존).

**핵심 배선**: 로컬 `.env`에 EC2와 **같은 `TUNNEL_TOKEN`**이 있어, 노트북
compose의 `cloudflared`를 띄우면 터널 `suvisdev.cloud`(bb0dccfc)의 두 번째
replica가 된다 → 새 터널·DNS 변경 없이 EC2 replica를 끄는 것이 컷오버.
프론트가 쓰는 호스트는 `api.`·`auth.suvisdev.cloud`(둘 다 이 터널),
`oauth.`는 DNS 없음(미사용). OAuth 콜백·FRONTEND_URL은 호스트명 불변이라
그대로.

**실행 기록**
1. EC2 재시작(사용자가 크레딧 절약차 중지해 둠) → 공인 IP 3.38.102.241 →
   **13.125.14.24**로 변경(Elastic IP 아님). `~/.ssh/config` 갱신.
2. 백업 `~/backups/ec2-2026-09-03/`: `pg_dumpall`(92MB, 테이블 63) ·
   `ec2.env`·`ec2.env.auth` · `crontab.txt` · 로컬 개발 DB 사전 백업.
3. 로컬 DB 교체: backend·auth·pgadmin 정지 → `DROP DATABASE suvisdev`
   (분류기 차단으로 사용자 실행) → 덤프 복원. 검증: movies 3,410 · users 9 ·
   reviews 258 · chat 414 · picks 668 · hub_knowledge 2,963 · tags 12,100 =
   EC2와 일치, alembic `20260901_0001`, pgvector 0.8.5.
4. `.env` 병합: 단독 `1` 줄(28행) 또 발견·제거, EC2에만 있던 5키 추가
   (`EMBEDDING_BACKEND=gemini`, `GEMINI_BACKFILL_API_KEY`, `KAKAO_API_KEY`,
   `LORA_SERVER_TOKEN`), `RECOMMENDATION_BACKEND=lora` +
   `LORA_SERVER_URL=http://host.docker.internal:8200`(노트북 lora-server
   직결). `.env.auth`는 동일. 사전 백업 `local.env.before`.
5. crontab 3건(03:00/03:30/03:45 백필) 노트북에 등록(경로
   `/home/suteagy/projects/suvisdev`).
6. 이미지 재빌드 완료(pip 레이어 재설치, 14.6GB) → `up -d backend auth`,
   컨테이너 내부에서 `/mova/movies` 200·`host.docker.internal:8200` 200.
7. **컷오버 완료(2026-09-03 23:35)**: 첫 replica 합류 때 공개 API가 **502**
   — 터널 공개 호스트의 원본이 `http://nginx:80`(ingressRule 0·2)인데
   노트북엔 nginx가 안 떠 있었음. 즉시 replica 정지로 EC2 복구(200) →
   `up -d nginx`(`nginx/conf.d/app.conf`, HTTP 80만, certbot 불필요) →
   네트워크 내 검증 → replica 재합류 → 공개 12/12건 노트북 200 →
   **EC2 `suvisdevcloud-cloudflared-1` 정지** → 커넥터 노트북 단독,
   8/8건 200, auth jwks 200, mova·gildle 라우터 응답 확인.
   원복은 EC2에서 `docker start suvisdevcloud-cloudflared-1`.

**EC2 후속(개인 스택 정리)** — 하루 정도 노트북 안정 확인 후:
`cd ~/suvisdev.cloud && docker compose down`(볼륨 유지) → `docker system
prune -a` → Elastic IP 할당 → 인스턴스 중지 → `t3.small` 변경 → 시작 →
Arda 배포(아래 2부). 개인 DB 볼륨은 1주일 뒤 `-v`로 삭제.

**주의·잔여**
- 노트북 lora-server는 `mova_20260825_123937`(AWQ) 서빙 — 데스크톱의
  09-02 GGUF 어댑터보다 구버전. 데스크톱 켜지면 GGUF 동기화 or
  `LORA_SERVER_URL=https://lora.suvisdev.cloud`로 전환.
- Windows 절전·덮개 닫기·업데이트 재부팅 설정은 사용자 확인 필요(샌드박스
  에서 powershell 조회 불가). WSL은 systemd=true·docker enabled 확인됨.
- backend/auth는 호스트 포트 미노출 — 로컬 검증은 `docker compose exec`
  또는 터널 경유.

## 팀(seuk) 인프라 이전: 순서

> **실행용 체크리스트는 `_docs/ARDA_AWS_DEPLOY_GUIDE.md`** (2026-09-04, 학원에서 이 문서만 보고 진행).

1. ~~**프론트**~~ — **완료(2026-09-03 저녁)**: 새 Vercel 프로젝트 `arda`
   (suvisdev Hobby 계정, `Seuk-Team/Arda` 연결, Root `frontend/app`, Vite,
   `VITE_API_BASE=https://api.arda.seuk.cloud`). 기본 주소
   `arda-teal.vercel.app`, 커스텀 도메인 **`seuk.suvisdev.cloud`** 연결·
   HTTPS 200 확인. Vercel GitHub 앱은 Seuk-Team 조직에 Arda만 허용으로 설치.
   **막힌 것 — CORS**: 기존 백엔드 preflight가 새 origin 두 개
   (`seuk.suvisdev.cloud`, `arda-teal.vercel.app`)에 400(기존 `arda-nu.
   vercel.app`은 200). 해결 A(권장): woojeongalex가 EC2 `backend/.env`
   `CORS_ORIGINS` + S3 버킷 CORS AllowedOrigins에 두 주소 추가 후 api
   재시작. 해결 B: `vercel.json` API rewrite + `VITE_API_BASE` 비움(S3 직접
   업로드는 못 우회, 새 백엔드 뜨면 폐기). 결정 대기.
2. **AWS 리소스(개인 계정, 서울)** — 상세 절차는 2026-09-03 밤 세션 답변
   기준. ① S3 `arda-resumes-seuk`(퍼블릭 차단 유지, CORS: PUT / Origins
   `seuk.suvisdev.cloud`·`arda-teal.vercel.app`·`localhost:5173` / Headers *)
   ② SQS Standard `arda-mail`(URL 기록) ③ SES 도메인 identity
   `seuk.suvisdev.cloud` + Easy DKIM CNAME 3개 Cloudflare 등록 → 발신
   `no-reply@seuk.suvisdev.cloud`; **production access 신청**(개인 계정은
   샌드박스, 팀 계정은 09-01 승인 이력 — 트랜잭션 메일·지원자 본인 입력·
   SNS 바운스 처리·일 100통 미만으로 기술) ④ IAM 유저 `arda-server`
   (콘솔 없음) + `arda-server-policy`(그 버킷 s3:Put/Get/Delete/List, 그
   큐 sqs Send/Receive/Delete/GetQueueAttributes, ses:SendEmail/SendRawEmail)
   → 액세스 키 발급.
3. **EC2 준비**: Elastic IP 할당·연결(먼저!) → 중지 상태에서 `t3.small`로
   변경 → 시작 → SG 80/443 0.0.0.0/0 확인 → 새 IP로 `~/.ssh/config` 갱신.
   서버: `cd ~/suvisdev.cloud && docker compose down`(볼륨 유지) →
   `docker system prune -af` → `git clone Seuk-Team/Arda ~/arda` →
   `backend/.env` 작성 → `infra/Caddyfile` 호스트 `api.seuk.suvisdev.cloud`
   → `cp infra/docker-compose.prod.yml infra/Caddyfile .` → `up -d db` →
   `run --rm api /app/.venv/bin/alembic upgrade head` → `up -d --build` →
   `scripts/create_admin.py`로 첫 admin(production은 공개 가입 차단).
   `.env` 필수: APP_ENV=production, DATABASE_URL(postgres:<DB_PASSWORD>@db/
   arda), DB_PASSWORD, JWT_SECRET, AWS_REGION, arda-server 키, S3_BUCKET,
   SQS_QUEUE_URL, SES_FROM_EMAIL, MAIL_REPLY_TO(seukathon@gmail.com),
   COMPANY_NAME, PUBLIC_APP_BASE_URL=https://seuk.suvisdev.cloud,
   CORS_ORIGINS=seuk.suvisdev.cloud,arda-teal.vercel.app, ANTHROPIC_API_KEY.
   SES 승인 전 MAIL_DRY_RUN=1.
4. **DNS·프론트 전환**: Cloudflare A `api.seuk` → Elastic IP(**DNS only**,
   Caddy ACME) → `/docs` 200 확인 → Vercel `VITE_API_BASE`=
   `https://api.seuk.suvisdev.cloud` → Redeploy(CORS 문제 소멸).
5. **데이터 이전(선택)**: woojeongalex에게 옛 서버 `pg_dump` + S3 객체 →
   복원 후 `alembic upgrade head`. 과정용 데이터면 빈 DB로 시작 가능.
6. **검증**: admin 로그인 → 공고 생성 → 공개 지원 폼 이력서 첨부 제출(S3
   CORS) → 담당자 화면 → 단계 변경 메일(워커 `sent`, 승인 전엔
   `success@simulator.amazonses.com`).

참고: 옛 팀 계정은 학원(ETECH) Organization 통합 결제 멤버로 학원이 400$
크레딧을 넣어 뒀고 SES도 승인된 상태("과정 끝날 때까지 유지" 발언, 09-handover).
지금 옮기는 동기는 이탈자 명의 루트 리스크.

유의: 기존 arda.seuk.cloud(도메인 소유 확인 필요 — 이탈자 소유면 병행 기간
후 폐기), 전환 기간엔 구/신 주소 둘 다 살려 두고 팀 공지 후 전환.

## 관련 기록

- 워크로그: `_docs/WORK_LOG_MAINPAGE.md` 2026-09-03 (착수·되돌림 경위)
- Arda 리스크·현황: `c:/Users/a/Desktop/Arda-프로젝트-종합분석-2026-09-03.md` §11
- 팀 문서 사이트 규칙: `~/ats.suvisdev.cloud/CLAUDE.md`
