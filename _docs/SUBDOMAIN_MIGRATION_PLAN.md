# 서브도메인 이사 계획 — seuk(팀 프로젝트)만 (2026-09-03 결정 변경)

**2026-09-03 저녁 결정 변경(사용자)**: 개인 앱(mova·gildle)은 서브도메인으로
옮기지 않고 기존 경로(`suvisdev.cloud/mova`·`/gildle`)를 그대로 쓴다.
서브도메인 이사는 **팀 프로젝트 seuk만** 진행한다. AWS는 개인/팀이 서로
다른 계정을 쓴다.

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
api.suvisdev.cloud       → 개인 EC2 (개인 AWS 계정 — 현행 유지)

seuk.suvisdev.cloud      → 팀 Vercel 프로젝트 (Arda 프론트)
api.seuk.suvisdev.cloud  → 팀 EC2 (별개 AWS 계정 — 이전 대상)
```

- 도메인과 AWS 계정은 독립 — Cloudflare(suvisdev.cloud 존) 레코드가
  가리키는 곳이 다른 계정이어도 무방. TLS는 Vercel/Caddy가 호스트별 발급.
- 팀 이전의 시의성: Arda 리스크 표의 "AWS 루트 계정이 이탈자 명의 —
  과정 종료 후 서버 소멸 가능". seuk.suvisdev.cloud + 새 계정이 그 이전 계획.

## GitHub 현황 (2026-09-03 실측)

- 조직 `Team-Seuk` 존재. 저장소: `Arda`(팀 프로젝트, main), `_template`
  (Python/uv 템플릿), `Yaksok`, `seuk_homepage`, `Team-Seuk`(private).
- 사용자(suvisdev) 역할은 **member** — 조직 설정·저장소 이전·브랜치 보호는
  owner에게 요청해야 한다.
- 조직 owner가 이탈자 명의인지 확인이 선행 과제. 아니면 저장소만 새로
  만들면 되고, 맞으면 새 조직을 만들어 Transfer(협조 가능 시) 또는
  `git clone --mirror` + `git push --mirror`(협조 불가 시, 이슈·PR 미이전)로
  옮긴 뒤 Vercel Git 연결을 새 저장소로 다시 잇는다. 새 조직은 owner를
  2명 이상 두어 단일 계정 잠금을 막는다.

```bash
# 저장소만 새로 만들 때 (member 권한으로 실패하면 owner에게 설정 요청)
gh repo create Team-Seuk/<이름> --template Team-Seuk/_template --private --clone
```

저장소 세팅 체크리스트(owner 권한): `main` 보호(PR 필수·리뷰 1·force push
금지), 팀원 write 권한, Secrets에 새 AWS 키·Vercel 토큰.

## 팀(seuk) 인프라 이전: 순서

1. **프론트(콘솔 2분)**: 팀 Vercel 프로젝트(Arda)에 `seuk.suvisdev.cloud`
   도메인 추가(팀장 권한) + Cloudflare CNAME `seuk` → `cname.vercel-dns.com`
   (DNS only/회색 구름). 백엔드 이전과 독립적으로 먼저 가능(기존
   api.arda.seuk.cloud를 당분간 그대로 호출).
2. **새 AWS 계정 준비물**: **SES 샌드박스 해제를 가장 먼저 신청**(시간
   걸림) · EC2(팀 compose·Caddyfile 재사용, infra/ 폴더) · S3 버킷 신설 ·
   SQS 큐 · IAM(팀원 유저).
3. **백엔드 기동 후**: Cloudflare `api.seuk` A 레코드(또는 터널) → 팀 EC2.
4. **코드(Team-Seuk/Arda — 에이전트 가능)**: 프론트 API base URL →
   `api.seuk.suvisdev.cloud`, 백엔드 CORS에 `seuk.suvisdev.cloud` 추가,
   서버 `.env` 갱신(새 S3/SES/SQS/DB + `PUBLIC_APP_BASE_URL`,
   Anthropic 키는 워크스페이스 범위 키 — 09/03 데블로그 참조).
5. **데이터 이전**: 기존 팀 EC2 DB 덤프 → 새 DB 복원, `alembic upgrade
   head`(0004까지), S3 이력서 객체 sync.
6. **검증**: 공개 지원 폼 → DB → 담당자 화면 수직 슬라이스 + 실메일 수신
   (인적성 설문 실메일 테스트가 대기 중이었음 — 같이 처리).

유의: 기존 arda.seuk.cloud(도메인 소유 확인 필요 — 이탈자 소유면 병행 기간
후 폐기), 전환 기간엔 구/신 주소 둘 다 살려 두고 팀 공지 후 전환.

## 관련 기록

- 워크로그: `_docs/WORK_LOG_MAINPAGE.md` 2026-09-03 (착수·되돌림 경위)
- Arda 리스크·현황: `c:/Users/a/Desktop/Arda-프로젝트-종합분석-2026-09-03.md` §11
- 팀 문서 사이트 규칙: `~/ats.suvisdev.cloud/CLAUDE.md`
