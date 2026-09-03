# Arda(seuk) AWS 배포 가이드 — 개인 계정, 서울 리전

작성 2026-09-04. 전날 밤 세션에서 확정한 절차를 **체크리스트로** 옮긴 것.
배경·결정 경위는 `SUBDOMAIN_MIGRATION_PLAN.md`, Arda 쪽 원본 문서는
`Seuk-Team/Arda` 저장소의 `docs/00_overview/07-deploy.md`·`infra/README.md`.

## 현재 상태 (출발점)

| 항목 | 상태 |
|------|------|
| 프론트 | Vercel 프로젝트 `arda` → https://seuk.suvisdev.cloud (완료). `VITE_API_BASE`는 아직 옛 백엔드 `api.arda.seuk.cloud` |
| 백엔드 | 아직 없음. 옛 팀 EC2가 서빙 중이나 새 프론트 origin을 CORS로 거부 |
| 개인 EC2 | 인스턴스 `i-09685fab629f1f57e`, m7i-flex.large, **중지 상태**. 개인 백엔드는 노트북으로 이전 완료라 이 EC2는 Arda 전용으로 씀 |
| GitHub | `Seuk-Team/Arda` (main 보호, PR #1 대기) |

목표 배선: `seuk.suvisdev.cloud`(Vercel) → `api.seuk.suvisdev.cloud`(EC2, Caddy 직결) → S3·SQS·SES(개인 계정).

---

## 1단계. AWS 리소스 4개 (콘솔, EC2 안 켜도 됨) — 30분

리전 선택기가 **아시아 태평양(서울) ap-northeast-2**인지 매 화면에서 확인.

### 1-1. S3 버킷
- [ ] S3 → Create bucket → 이름 `arda-resumes-seuk`(중복이면 뒤에 숫자), 리전 서울
- [ ] **Block all public access는 켜진 채로** 둔다 (업로드는 presigned URL이라 공개 불필요)
- [ ] 생성 후 버킷 → Permissions → CORS → Edit → 아래 붙여넣기 → Save

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT"],
    "AllowedOrigins": [
      "https://seuk.suvisdev.cloud",
      "https://arda-teal.vercel.app",
      "http://localhost:5173"
    ],
    "ExposeHeaders": []
  }
]
```

> 프론트 주소가 늘면 여기에도 추가. 빠지면 **API는 정상인데 브라우저 업로드만**
> 실패하고 서버 로그에 안 남는다(CORS는 브라우저만 검사).

### 1-2. SQS 큐
- [ ] SQS → Create queue → **Standard**, 이름 `arda-mail`, 나머지 기본값 → Create
- [ ] 상세 화면의 **URL** 복사 → 메모 (형식 `https://sqs.ap-northeast-2.amazonaws.com/<계정번호>/arda-mail`)

### 1-3. SES (메일)
- [ ] SES → Identities → Create identity → **Domain** → `seuk.suvisdev.cloud` → Easy DKIM 체크 → Create
- [ ] 화면에 나온 **CNAME 3개**를 Cloudflare DNS(suvisdev.cloud 존)에 그대로 추가. 프록시 **끄기(DNS only)**
- [ ] 10~30분 뒤 Identity 상태 **Verified** 확인 → 발신 주소는 `no-reply@seuk.suvisdev.cloud`
- [ ] SES → Account dashboard → **Request production access** (개인 계정은 샌드박스 = 검증된 수신자에게만 발송됨)

신청서에 쓸 내용(팀 계정이 2026-09-01 이 취지로 승인됨):

```
Use case: Transactional email for a recruiting management web app (Arda).
Recipients: Only job applicants who entered their own email address in our
application form; no marketing, no purchased lists.
Content: Application received confirmation, interview schedule notices,
result notices. ~50-100 emails/day expected.
Bounce/complaint handling: SES notifications are routed to an SNS topic;
addresses that bounce or complain are excluded from further sending.
Unsubscribe: Applicants can withdraw their application, which stops all mail.
```

- [ ] 승인 전 테스트는 `success@simulator.amazonses.com`으로. 승인 후 `.env`의 `MAIL_DRY_RUN`을 0으로

### 1-4. IAM 유저 (서버 전용 키)
- [ ] IAM → Users → Create user → 이름 `arda-server`, **콘솔 접근 없음** → Next
- [ ] Permissions → Attach policies directly → **Create policy** → JSON 탭에 아래 붙여넣기 → 이름 `arda-server-policy` → Create → 돌아와서 새로고침 후 체크 → Create user

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::arda-resumes-seuk", "arn:aws:s3:::arda-resumes-seuk/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
      "Resource": "arn:aws:sqs:ap-northeast-2:*:arda-mail"
    },
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "*"
    }
  ]
}
```

- [ ] 유저 → Security credentials → **Create access key** → "Application running on an AWS compute service" → Create → **Access key ID·Secret 둘 다 복사** (Secret은 이 화면에서만 보임)

> 이 키는 Arda 서버 `.env`에만 넣는다. 개인 프로젝트 버킷·EC2엔 권한이 없어
> 새어도 피해가 Arda 리소스로 한정된다.

---

## 2단계. EC2 준비 — 20분

- [ ] EC2 → Elastic IPs → **Allocate Elastic IP address** → Allocate → Actions → **Associate** → 인스턴스 `i-09685fab629f1f57e` 선택 → Associate
  (먼저 해야 이후 중지·시작에도 IP가 고정. Arda는 터널이 아니라 Caddy 직결이라 고정 IP 필수)
- [ ] 인스턴스가 **중지** 상태인지 확인 → Actions → Instance settings → **Change instance type** → `t3.small` → Apply
- [ ] Instance state → **Start**
- [ ] Security → Security groups → Inbound rules에 **80, 443 : 0.0.0.0/0** 있는지 확인(개인 nginx가 쓰던 규칙이라 있을 것). 22는 본인 IP만
- [ ] Elastic IP 값을 Claude 세션에 알려 준다 → `~/.ssh/config`의 `Host aws` HostName 갱신 → 아래 서버 작업은 Claude가 대신 가능

### 서버 작업 (SSH, `ssh aws`)

```bash
# 개인 스택 정리 (볼륨은 남김 — 일주일 뒤 확인 후 -v로 삭제)
cd ~/suvisdev.cloud && docker compose down
docker system prune -af          # 개인 이미지 13GB 회수

# Arda 받기
git clone https://github.com/Seuk-Team/Arda.git ~/arda && cd ~/arda
cp backend/.env.example backend/.env
nano backend/.env                # 아래 표대로 채운다

# Caddy 호스트 교체 + compose 파일 위치 맞추기 (compose가 ./backend, ./Caddyfile 기준)
sed -i 's/api.arda.seuk.cloud/api.seuk.suvisdev.cloud/' infra/Caddyfile
cp infra/docker-compose.prod.yml infra/Caddyfile .

# DB 먼저 → 스키마 → 전체 기동
docker compose -f docker-compose.prod.yml up -d db
docker compose -f docker-compose.prod.yml run --rm api /app/.venv/bin/alembic upgrade head
docker compose -f docker-compose.prod.yml up -d --build

# 첫 admin (production은 공개 가입이 잠겨 있어 스크립트로만 만든다)
docker compose -f docker-compose.prod.yml exec -e ADMIN_PASSWORD='<비밀번호>' api \
  /app/.venv/bin/python scripts/create_admin.py ssuvisdev@gmail.com 관리자

# 확인
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail 30 api
```

`backend/.env`에 채울 값:

| 키 | 값 |
|----|----|
| `APP_ENV` | `production` (정확히 이 값. 오타·미설정도 production으로 잠김) |
| `DATABASE_URL` | `postgresql+psycopg://postgres:<DB_PASSWORD>@db:5432/arda` |
| `DB_PASSWORD` | 긴 랜덤 (compose의 db 컨테이너가 같은 변수를 읽음) |
| `JWT_SECRET` | 긴 랜덤 (`openssl rand -hex 32`) |
| `AWS_REGION` | `ap-northeast-2` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | 1-4의 `arda-server` 키 |
| `S3_BUCKET` | `arda-resumes-seuk` |
| `S3_ENDPOINT_URL` | 비움 (실제 AWS) |
| `SQS_QUEUE_URL` | 1-2에서 복사한 URL |
| `SES_FROM_EMAIL` | `no-reply@seuk.suvisdev.cloud` |
| `MAIL_REPLY_TO` | `seukathon@gmail.com` (팀 공용. **비우면 지원자 회신이 증발**) |
| `MAIL_DRY_RUN` | SES 승인 전 `1`, 승인 후 `0` |
| `COMPANY_NAME` | 메일 문구의 회사명 |
| `PUBLIC_APP_BASE_URL` | `https://seuk.suvisdev.cloud` |
| `CORS_ORIGINS` | `https://seuk.suvisdev.cloud,https://arda-teal.vercel.app` |
| `ANTHROPIC_API_KEY` | 팀 워크스페이스 키 |
| `AGENT_CHAT_MODEL` 등 | `.env.example` 기본값 유지 |
| `OPENAI_API_KEY` | STT 쓸 때만. 없으면 비움 |

---

## 3단계. 연결·전환 — 10분

- [ ] Cloudflare DNS → **A 레코드** 이름 `api.seuk`, 대상 Elastic IP, 프록시 **끄기(DNS only)**
  (Caddy가 Let's Encrypt 인증서를 HTTP 챌린지로 직접 받으므로 프록시를 켜면 발급 실패)
- [ ] 1~2분 뒤 `https://api.seuk.suvisdev.cloud/docs` 열림 확인 (첫 접속은 인증서 발급으로 10초쯤 걸릴 수 있음)
- [ ] Vercel → 프로젝트 `arda` → Settings → Environment Variables → `VITE_API_BASE` = `https://api.seuk.suvisdev.cloud` → Save
- [ ] Deployments → 최신 배포 ⋯ → **Redeploy** (환경 변수는 빌드 시 박히므로 재배포 필수)

---

## 4단계. 검증 순서

1. https://seuk.suvisdev.cloud 에서 admin 로그인 (2단계에서 만든 계정)
2. 공고 생성
3. 공개 지원 링크(`/apply/<token>`)에서 **이력서 파일 첨부**해 제출 — 여기서 실패하면 S3 CORS(1-1) 확인
4. 담당자 화면에 지원자 표시
5. 단계 변경 → 메일 발송. 서버에서 `docker compose -f docker-compose.prod.yml logs worker | tail`에 `sent` 확인. SES 승인 전이면 시뮬레이터 주소로
6. 팀원에게 remote 교체 공지: `git remote set-url origin https://github.com/Seuk-Team/Arda.git`

---

## 선택: 옛 팀 서버 데이터 가져오기

woojeongalex(옛 계정 IAM `arda-ops`)에게 부탁할 것 두 가지. 과정용 데이터라 빈 DB로 시작해도 무방.

```bash
# 옛 서버에서
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres -d arda > arda-dump.sql
aws s3 sync s3://<옛버킷> ./resumes/
# 새 서버에서 (api 정지 후)
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d arda < arda-dump.sql
docker compose -f docker-compose.prod.yml run --rm api /app/.venv/bin/alembic upgrade head
aws s3 sync ./resumes/ s3://arda-resumes-seuk/
```

## 막히면

| 증상 | 볼 곳 |
|------|-------|
| `/docs` 안 열림 | SG 80/443, DNS가 프록시(주황)로 켜져 있지 않은지, `docker compose logs caddy` |
| 화면은 뜨는데 로그인 실패 | `CORS_ORIGINS`에 프론트 주소 있는지, api 로그 |
| 이력서 업로드만 실패 | S3 CORS AllowedOrigins |
| 메일 안 감 | `MAIL_DRY_RUN`, SES 샌드박스 여부, worker 로그 |
| 디스크 부족 | `docker builder prune -af`, `docker image prune -af`. `--volumes`는 절대 금지(DB 날아감) |

옛 팀 계정 참고: 학원(ETECH) Organization 통합 결제 멤버, 학원이 400$ 넣어 둠,
SES 승인 상태, "과정 끝날 때까지 유지" 발언. 지금 옮기는 이유는 이탈자 명의
루트 계정 리스크.
