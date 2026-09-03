# 서브도메인 이사 계획 — mova·gildle·seuk (2026-09-03 확정)

사용자 결정(2026-09-03 오후, 데스크톱 세션): 개인 앱과 팀 프로젝트를
서브도메인으로 분리하고, **AWS는 개인/팀이 서로 다른 계정**을 쓴다.
저녁(집) 세션이 이 문서만 읽고 이어받을 수 있게 전 단계를 기록한다.

## 목표 배선도

```
suvisdev.cloud           → 개인 Vercel(suvis) — 기존 유지
mova.suvisdev.cloud      → 〃 (호스트 리라이트로 /mova 섹션을 루트 서빙)
gildle.suvisdev.cloud    → 〃 (〃 /gildle)
api.suvisdev.cloud       → 개인 EC2 (개인 AWS 계정 — 현행 유지)

seuk.suvisdev.cloud      → 팀 Vercel 프로젝트 (Arda 프론트)
api.seuk.suvisdev.cloud  → 팀 EC2 (별개 AWS 계정 — 이전 대상)
```

- 도메인과 AWS 계정은 독립 — Cloudflare(suvisdev.cloud 존) 레코드가
  가리키는 곳이 서로 다른 계정이어도 무방. TLS는 Vercel/Caddy가 호스트별 발급.
- 팀 이전의 시의성: Arda 리스크 표의 "AWS 루트 계정이 이탈자 명의 —
  과정 종료 후 서버 소멸 가능". seuk.suvisdev.cloud + 새 계정이 그 이전 계획.

## 이미 완료된 것 (2026-09-03 데스크톱)

- `suvis/next.config.mjs` 호스트 리라이트 — 커밋 `0bef4f3`, 푸시됨(Vercel
  자동 배포). mova/gildle.suvisdev.cloud가 각 섹션을 루트로 서빙,
  `/api`·`/_next`·확장자 파일·기존 접두 경로는 제외. 기존
  `suvisdev.cloud/mova` 경로도 그대로 유지.
- 백엔드 CORS 무변경 확인(`allow_origins=["*"]`).

## 1부 — 개인(mova·gildle) 남은 작업: 콘솔 3단계

1. **Vercel**: suvis 프로젝트 → Settings → Domains에
   `mova.suvisdev.cloud`·`gildle.suvisdev.cloud` 추가.
2. **Cloudflare DNS**: CNAME `mova`·`gildle` → `cname.vercel-dns.com`
   (**DNS only/회색 구름** 권장 — Vercel이 TLS 발급).
3. **(로그인 쓸 경우) 소셜 콘솔**: 카카오·네이버·구글 redirect URI에
   서브도메인 콜백 추가.

검증(에이전트에게 시킬 것): 두 서브도메인 루트 200 + Mova/Gildle 화면 서빙,
`/movies` 류 경로 서빙, 정적 에셋 로드, `/api/mova/*` 프록시 정상.

유의: JWT가 localStorage라 **로그인 세션은 도메인별 분리** — 주 사용 주소를
정하면 실사용 문제 없음. suvisdev.cloud/mova에서 로그인한 세션은
mova.suvisdev.cloud로 안 넘어간다.

## 2부 — 팀(seuk) 인프라 이전: 순서

1. **프론트(콘솔 2분)**: 팀 Vercel 프로젝트(Arda)에 `seuk.suvisdev.cloud`
   도메인 추가(팀장 권한) + Cloudflare CNAME `seuk` → `cname.vercel-dns.com`.
   — 백엔드 이전과 독립적으로 먼저 가능(기존 api.arda.seuk.cloud를 당분간
   그대로 호출).
2. **새 AWS 계정 준비물**: EC2(팀 compose·Caddyfile 재사용, infra/ 폴더에
   있음) · S3 버킷 신설 · SES(메일 도메인 인증 재신청 — 샌드박스 해제 시간
   걸림, 가장 먼저 신청) · SQS 큐 · IAM(팀원 유저).
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

- 워크로그: `_docs/WORK_LOG_MAINPAGE.md` 2026-09-03 (리라이트 구현 상세)
- Arda 리스크·현황: `c:/Users/a/Desktop/Arda-프로젝트-종합분석-2026-09-03.md` §11
- 팀 문서 사이트 규칙: `~/ats.suvisdev.cloud/CLAUDE.md`
