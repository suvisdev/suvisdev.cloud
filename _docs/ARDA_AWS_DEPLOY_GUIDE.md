# Arda(seuk) AWS 배포 가이드 — 개인 계정, 서울 리전

작성 2026-09-04. 전날 밤 세션에서 확정한 절차를 **체크리스트로** 옮긴 것.
같은 날 저녁 갱신: 기간(~10/27)·예산($400)·GPU 인스턴스 분리·깃 권한 이관
반영, 로컬 클론(`C:\Users\a\Arda`) 실측으로 기능·설정 확정.
배경·결정 경위는 `SUBDOMAIN_MIGRATION_PLAN.md`, Arda 쪽 원본 문서는
`Team-Seuk/Arda` 저장소의 `docs/00_overview/07-deploy.md`·`infra/README.md`.

## 현재 상태 (출발점)

| 항목 | 상태 |
|------|------|
| 기간·예산 | **~2026-10-27 (약 53일), 총 $400** 지원. 백엔드 상시분 ~$50 + GPU ~$350 배분 |
| 프론트 | Vercel 프로젝트 `arda` → https://seuk.suvisdev.cloud (완료). `VITE_API_BASE`는 아직 옛 백엔드 `api.arda.seuk.cloud` |
| 백엔드 | 아직 없음. 옛 팀 EC2가 서빙 중이나 새 프론트 origin을 CORS로 거부. **옛 운영은 t3.micro(1GiB)에서 돌았음** — t3.small이면 여유 |
| 개인 EC2 | 인스턴스 `i-09685fab629f1f57e`, m7i-flex.large, **중지 상태로 유지**. ~~Arda 전용으로 재활용~~ → **09-04 결정 변경: Arda는 새 인스턴스 `arda-api`(t3.small)를 신규 생성** — 팀원 열람 인프라라 개인 잔재와 분리. 개인 EC2는 중지 보관(EBS 월 ~$3), 필요 없다고 확정되면 종료 |
| GPU | **없음 → 신규.** g4dn.xlarge(T4 16GB)를 별도 인스턴스로, 쓸 때만 기동 (5단계) |
| GitHub | `Team-Seuk/Arda` — **퍼블릭**, 관리 권한 이관받음(09-04). 배포 전 PR #1 머지 여부 결정 |

기능 실측 (2026-09-04, 로컬 클론 기준):

| 기능 | 코드 상태 | 어디서 도나 |
|------|-----------|-------------|
| 이력서 분석·요약 | 구현됨 (`agent/`, Anthropic API) | 백엔드 EC2 |
| 메일 발송 | 구현됨 (SES + SQS `worker.py`) | 백엔드 EC2 |
| 인적성 검사 분석 | 구현됨 (`api/aptitude.py` 등) | 백엔드 EC2 |
| 면접 일정 조율 | 구현됨 (`api/schedules.py`·`availability.py`) | 백엔드 EC2 |
| STT 인터뷰 전사·요약 | 구현됨 (`agent/stt.py`) — `STT_BACKEND=openai`(기본) 또는 `faster_whisper`(로컬, in-process) | 기본: 백엔드에서 OpenAI API 호출. 로컬 전환은 GPU 박스로 옮길 때 |
| LLM 로컬 서빙 | 스위치 구현됨 (`AGENT_*_BACKEND=ollama`, `OLLAMA_HOST`) | GPU 박스 Ollama (선택) |
| **얼굴분석(영상)** | **코드 없음 — 신규 개발** | GPU 박스에 별도 서비스로 |
| **블록체인** | **코드 없음 — 신규 개발** | 테스트넷 + RPC 권장, AWS 인프라 불필요 |

목표 배선: `seuk.suvisdev.cloud`(Vercel) → `api.seuk.suvisdev.cloud`(EC2, Caddy 직결) → S3·SQS·SES(개인 계정). 백엔드 EC2는 같은 VPC의 GPU EC2(사설 IP)를 필요할 때만 호출.

## 0단계. 오늘 바로 걸어둘 것 (대기 시간 있는 신청 2건)

- [ ] **G 인스턴스 vCPU 쿼터 신청** — 개인 계정은 GPU 쿼터가 기본 0. Service Quotas → Amazon EC2 → "Running On-Demand G and VT instances" → **4** (g5 여지 두려면 8) 신청. 리전 서울 확인. 승인까지 며칠 걸릴 수 있음
- [ ] **AWS Budgets** — Cost budget, Monthly **$200**(두 달 합쳐 $400 프레임), 알림 50/80/100% → ssuvisdev@gmail.com. Budgets는 하루 몇 번 집계라 실시간 아님 — 실질 안전장치는 5단계의 자동 중지 알람

---

## 계정 체계 (09-04 세션 정리) — 루트는 금고, 작업은 IAM

| 주체 | 로그인 | 권한 | 용도 |
|------|--------|------|------|
| 루트 | 안 씀 (MFA 등록 완료) | 전부 | 비상 복구·결제 설정만 |
| 본인 | **mova 시절 admin IAM 유저 재사용** (AdministratorAccess + MFA 확인됨) | 관리 전부 | 이 가이드의 모든 콘솔 작업 |
| 팀원 | 각자 IAM 유저 | `arda-viewers` 그룹 = **ViewOnlyAccess** | 상태 열람만. S3 이력서(개인정보) 다운로드 불가 |
| 서버 | 없음 (키만) | `arda-server-policy` | EC2 `.env`의 S3·SQS·SES 호출 |

- [ ] 계정 별칭 생성: IAM → 대시보드 → 계정 별칭 → `suvisdev` → 팀 로그인 주소 `https://suvisdev.signin.aws.amazon.com/console`
- [ ] 그룹 `arda-viewers` 생성 + `ViewOnlyAccess` 연결
- [ ] 팀원 수만큼 유저 생성(콘솔 액세스 켬, 자동 생성 암호 + 첫 로그인 시 변경 강제, 그룹 추가) → **.csv를 각자에게 개별 DM** (전체 채널 금지) + "리전 서울로 변경" 안내
- 결제(Billing) 화면은 구형 계정이면 루트로 한 번 "결제 정보에 대한 IAM 사용자 및 역할 액세스"를 켜야 IAM 유저에게 보인다. 예산 생성이 액세스 거부되면 이것부터.

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

## 2단계. EC2 준비 — 20분 (09-04 변경: 재활용 대신 신규 생성)

- [ ] EC2 → 인스턴스 → **인스턴스 시작(Launch)** → 이름 `arda-api`
  - AMI **Ubuntu Server 24.04 LTS**, 유형 **t3.small**, 키 페어는 기존 것
  - 네트워크: 기본 VPC, 퍼블릭 IP 자동 할당 **활성화**, SG 신규 `arda-api-sg`
    (22←내 IP, 80·443←0.0.0.0/0)
  - 스토리지 **gp3 30GiB** (기본 8은 도커 이미지에 부족)
- [ ] 탄력적 IP → **할당** → **연결** → `arda-api` (옛 인스턴스에 연결했었으면 "재연결 허용" 체크로 이전)
- [ ] 옛 개인 EC2(`i-09685...`)는 **중지 상태로 그대로 둠** — 데이터 확정 전 종료 금지
- [ ] Elastic IP로 `~/.ssh/config`의 `Host aws` HostName 갱신 (유저명 `ubuntu`)

### 서버 작업 (SSH, `ssh aws`)

```bash
# 도커 설치 (신규 서버 최초 1회) — 설치 후 exit 하고 재접속해야 docker 그룹이 먹는다
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu

# 스왑 2G (옛 팀 서버도 t3.micro+스왑 2G로 임베딩 프리페치 OOM을 피했다 — 07-deploy 실측)
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile \
  && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Arda 받기 (org 이름 주의: Team-Seuk이다. Seuk-Team 아님 — 09-04 실측)
git clone https://github.com/Team-Seuk/Arda.git ~/arda && cd ~/arda
cp backend/.env.example backend/.env
nano backend/.env                # 아래 표대로 채운다

# compose 변수 치환용 링크 — docker-compose.prod.yml의 ${DB_PASSWORD:?}는
# env_file이 아니라 "프로젝트 루트의 .env"에서 치환된다. 링크 없이 up 하면
# "DB_PASSWORD: set in .env"로 실패한다 (mova의 --env-file 누락 사고와 같은 계열,
# 단 Arda는 :? 가드 덕에 빈 값 대신 시끄럽게 죽는다)
ln -s backend/.env .env

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
| `DB_PASSWORD` | 긴 랜덤 — `openssl rand -hex 24` (hex만: `$` 등 특수문자는 compose 치환이 오해함) |
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
| `AGENT_CHAT_BACKEND` / `AGENT_SUMMARY_BACKEND` | **비움(=anthropic).** GPU 박스는 상시가 아니라 ollama를 운영 기본으로 두면 안 됨 |
| `OPENAI_API_KEY` | **필수** — STT 인터뷰 전사가 핵심 기능이고 기본 백엔드가 openai. whisper-1 $0.006/분(3,000분 써도 ~$18) |
| `STT_BACKEND` | 비움(=openai). 로컬 전사(faster_whisper)는 in-process라 t3.small에선 불가 — GPU 박스로 STT를 옮기려면 원격 STT 서비스 코드가 필요(백로그) |

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
6. 팀원에게 remote 교체 공지: `git remote set-url origin https://github.com/Team-Seuk/Arda.git`
   — 관리 권한이 있으니 **옛 저장소는 Settings → Archive**로 읽기 전용화(잘못 푸시 방지, 언제든 해제 가능)

---

## 5단계. GPU 인스턴스 (쿼터 승인 후) — 얼굴분석·로컬 STT·Ollama

예산 프레임(서울 온디맨드, 53일 ≈ 1,272h 기준 약산):

| 구성 | 비용 |
|------|------|
| 백엔드 t3.small 상시 + EBS + EIP | ~$50/기간 |
| g4dn.xlarge $0.65/h 온디맨드 | 잔여 $350 ÷ 0.65 ≈ **540h = 하루 평균 ~10h** |
| (참고) g4dn 상시 가동 | ~$820 ❌ 예산 2배 초과 — **쓸 때만 켜는 운영이 전제** |

**g4dn.xlarge(T4 16GB)로 확정** — VRAM 배치: faster-whisper large-v3
int8_float16 ~3.5GB + 얼굴분석 1~2GB + Ollama 7~8B Q4 ~6GB ≈ 11GB로 동시 탑재 가능.
13B+ fp16이 필요해지면 그때 g5.xlarge(24GB, $1.4/h → 하루 ~4.5h)로 재검토.

### 생성
- [ ] EC2 → Launch instance → 이름 `arda-gpu`
- [ ] AMI: **Deep Learning OSS Nvidia Driver AMI GPU PyTorch (Ubuntu 22.04)** — 드라이버·CUDA·nvidia 도커 런타임 내장
- [ ] Type `g4dn.xlarge`, 키페어는 백엔드와 동일
- [ ] Network: **백엔드와 같은 VPC·서브넷**, Auto-assign public IP Enable, **Elastic IP는 주지 않는다**(외부 인바운드 없음, 과금 절약)
- [ ] Storage: **gp3 100GB** (기본 45GB는 AMI가 거의 다 먹음. 100GB ~$9/월)
- [ ] SG 신규 `arda-gpu-sg`: 22 ← 본인 IP, 서비스 포트(예: 11434 Ollama·8300 얼굴분석) ← **백엔드 인스턴스의 SG ID**(`sg-` 자동완성. IP가 아니라 SG로 지정해야 0.0.0.0/0 실수 원천 차단)
- [ ] 생성 후 **Private IPv4 메모** — 중지·시작해도 안 바뀜. 백엔드 `.env`에 이 주소를 쓴다 (`OLLAMA_HOST=http://<사설IP>:11434` 등)
- [ ] AWS 자격증명이 필요하면(S3의 면접 영상 읽기) `arda-server` 키 재사용 — 정책이 이미 버킷 한정이라 그대로 안전

### 운영 규칙 (예산의 생명줄)
- [ ] **쓸 때 켜고 끝나면 끈다.** 중지 중엔 EBS(~$9/월)만 과금.
  `aws ec2 start-instances --instance-ids <gpu-id>` / `stop-instances`
- [ ] **CloudWatch 자동 중지 알람**: Alarms → Create → `CPUUtilization` 1시간 < 5% → EC2 action **Stop** — 끄는 걸 까먹는 게 최대 예산 리스크
- [ ] (선택) `arda-server-policy`에 `ec2:StartInstances`/`StopInstances`(해당 인스턴스 ARN 한정) 추가 → 스크립트·관리자 화면에서 원터치 기동

### 신규 개발 배치 방침
- **얼굴분석(영상)**: 처음부터 GPU 박스의 **별도 서비스**(예: FastAPI :8300)로 설계. 영상은 S3에 있으니 GPU 서비스가 `arda-server` 키로 GetObject → 분석 → 결과를 백엔드 API로 회신. 영상 분석은 분 단위 작업이라 동기 HTTP보다 **잡 큐(제출→폴링)** 형태 권장. 백엔드는 GPU 꺼짐(타임아웃) 시 "분석 대기" 상태로 두는 폴백 필수 — GPU가 꺼져 있는 게 정상 상태다
- **로컬 STT 이전(백로그)**: 현 코드는 in-process라 백엔드에서만 동작. 옮기려면 얼굴분석 서비스에 전사 엔드포인트를 얹고 `STT_BACKEND=remote`류 추가 — OpenAI API 비용(~$18 수준)이 아까울 때만
- **블록체인**: **AWS 인프라 없이** 퍼블릭 테스트넷(Sepolia·Polygon Amoy 등) + 무료 RPC(Infura/Alchemy)로. 백엔드에 web3 클라이언트만 추가하면 되고 비용 0. **자체 노드를 t3.small에 올리지 말 것**(RAM 2GiB로 불가). 미검증 항목: 팀의 블록체인 용도 확정 필요(예: 전형 결과 위변조 방지 해시 앵커링)

---

## 10/27 철거 체크리스트 (프로젝트 종료 시 과금 0 만들기)

- [ ] GPU 인스턴스 **Terminate** (EBS 같이 삭제 확인)
- [ ] 백엔드 EC2 Terminate 또는 개인용 환원
- [ ] **Elastic IP Release** — 인스턴스 없이 잡아두면 계속 과금
- [ ] S3 이력서·영상(개인정보): 팀과 보관 여부 합의 후 삭제/이관
- [ ] SES Identity·SQS 큐·IAM 유저·`arda-server` 키 삭제
- [ ] Cost Explorer에서 잔여 과금 항목 0 확인

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

## 부록. 결정 근거·막힌 화면 Q&A (09-04 실작업 세션)

**GPU 쿼터 값 4의 의미** — 인스턴스 "개수"가 아니라 **동시에 켤 수 있는 G 계열
vCPU 총합**. g4dn.xlarge가 4 vCPU라 4 = 1대. G 계열 최소 단위가 4 vCPU라 5는
무의미, 다음 유효 단계는 8(2대 or 2xlarge 1대). 작게 신청해야 자동 승인이 잘 된다.
같은 화면의 "All G and VT **Spot** Instance Requests"는 스팟 전용이라 해당 없음.

**g4dn.xlarge가 뭔가** — g(GPU 계열)·4(세대)·dn(NVMe/네트워크 강화)·xlarge(크기).
NVIDIA T4 16GB + 4 vCPU + RAM 16GB, 서울 ~$0.65/h. T4 16GB면 얼굴분석(1~2GB)
+ Whisper(~3.5GB) + Qwen 7B Q4(~6GB) 동시 탑재 가능(~11GB)이 선택 이유.

**t3.small·Ubuntu 24.04 선택 이유** — 옛 팀 서버가 같은 스택을 t3.micro(1GB)
+스왑 2G로 돌린 실측이 있어 그 2배 사양이면 충분 + 상시 가동 53일에 ~$33.
t 계열은 버스트형이라 간헐 트래픽 API에 적합. AMI는 Arda 문서·명령이 전부
우분투(apt·ubuntu 유저) 기준이고 GPU 박스(Deep Learning AMI)도 우분투 기반이라 통일.

**키 페어** — 신규 생성 시 유형 ED25519 권장(RSA도 무방), 형식 .pem(WSL OpenSSH).
**.pem은 생성 순간 한 번만 다운로드된다.** `~/.ssh/`로 옮기고 `chmod 400`,
`~/.ssh/config`에 `Host arda / HostName <탄력적IP> / User ubuntu / IdentityFile ~/.ssh/arda.pem`.

**SES "Invalid identity configuration" 오류** — 도메인 자격 증명 생성 폼의
**고급 DKIM 설정**에서 ① Easy DKIM 라디오 ② 서명 키 길이 RSA_2048_BIT
③ DKIM 서명 활성화, 셋 중 하나라도 미선택이면 난다. 도메인 칸에
`https://`·공백·끝점이 들어가도 동일. 안 되면 새로고침 후 재입력.

**SES CNAME 값 다시 보기** — 생성 화면을 닫았으면 SES → 자격 증명 →
도메인 클릭 → **인증 탭**에 3쌍이 그대로 있다.

**예산 알림 설정 위치** — 예산 생성 마법사 **2페이지("경보 임계값 구성")**.
1페이지(금액)에서 "다음"을 눌러야 나온다. "경보 임계값 추가"로 50/80/100% 3개.

**루트로 이미 만든 리소스** — 리소스는 계정 귀속이라 IAM 유저로 갈아타도
재작업 불필요. 루트는 MFA만 걸고 보관, 이후 로그인할 일 없는 게 정상.

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
