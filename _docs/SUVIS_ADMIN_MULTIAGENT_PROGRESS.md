# SUVIS 어드민 대시보드 + 멀티에이전트 진행 상황

컨텍스트가 끊길 경우를 대비한 재개용 메모. 관련 상세 지시서:
- `suvisdev/_docs/RBAC_agent_dashboard.md` (RBAC + 어드민 대시보드 H0~H4)
- `suvisdev/apps/ontology/_docs/00_COMMON_conventions.md` + `01~08_*.md` (에이전트별 지시서)

---

## 오늘(2026-07-21) 완료한 것

### 1. 이미지 분류 에이전트 (포스터 → 장르, `01_image_classifier_agent.md`)
- H0~H6 헤르메스 단계 전부 게이트 검증 완료, 실 서버 배포 확인
- `apps/ontology`에 ConvNeXt-Nano 기반 6클래스(액션/드라마·로맨스/공포·스릴러/애니·가족/코미디/SF·판타지) 포스터 장르 분류기
- 요청 시 로드→추론→언로드 GPU 전략(H1 VRAM 실측 근거)
- `/api/vision/genre/{classify,classes}` API, MCP 서버(`image_classifier_mcp_server.py`), 에이전트 통합(`vision_genre_agent.py`, qwen2.5 tool_calls 신뢰 불가 확인 → 결정적 트리거+LLM 요약 방식 채택)
- 데이터셋: TMDB API로 232장 확보(`scripts/prepare_genre_classifier_dataset.py`), 학습 스크립트(`scripts/train_genre_classifier.py`), val_acc 53.3%

### 2. RBAC + 멀티에이전트 관리 대시보드 (`RBAC_agent_dashboard.md`)
- H0: `ADMIN_EMAILS`(env, 지금 `ssuvisdev@gmail.com`) 기준 OAuth 로그인 시 role 산출 → JWT claim 포함
- H1: `viewer/dependencies/require_admin.py` 가드(401/403/200 실측)
- H2: `/viewer/admin/agents/*` mock API(목록·상세·토글·invoke·로그·모델정보), 8개 에이전트(이미지분류기 실제 완성 + Argus/Loom/Atlas/Prisma/Sentinel/Echo/Chronos mock)
- H3: 기존 `/admin` 사이드바에 "에이전트" 탭 추가, `/admin/agents`(목록)·`/admin/agents/[id]`(상세) 페이지
- 추가 수정:
  - 헤더 "Admin" 버튼이 무조건 노출되던 것 → `role==="admin"`일 때만 노출
  - 로그인해도 Header가 리마운트 안 돼 role 반영 안 되던 문제 → `suvis-session.ts`에 커스텀 이벤트(`suvis-session-changed`) 추가, Header가 구독
  - `/admin` 전체(홈/앱관리/사용자/캘린더/통계/설정/디스패치/수집기)에 프론트 가드가 전혀 없어 비로그인도 URL로 그냥 들어가지던 문제 → `AdminAuthGate`를 `admin/layout.tsx`에 적용해 일괄 차단
  - `/api-login` 쿠키가 7일 유지돼 로그인이 안 풀리던 것 → 세션 쿠키로 변경(브라우저 완전히 닫으면 만료)

### 3. 어드민 홈 화면 구현 (사용자 지시: 홈→사용자→앱관리→통계→캘린더→설정 순)
- 기존 정적 목업(titanic/mova 카드 등) → 에이전트 현황 중심으로 교체
- 요약 카드 4개(전체 에이전트/실행중·대기/오늘 크롤링/활성 사용자), 최근 활동 피드, 에이전트 상태 그리드 8개
- 에이전트 수·상태는 `/viewer/admin/agents` 실제 연동, 나머지(크롤링 수·사용자 수·최근 활동)는 `suvis/lib/admin-dashboard-api.ts`에 분리된 mock 함수 — 나중에 실제 API로 교체만 하면 됨

**✅ 확인 완료**: 로그아웃 후 재로그인 + Admin 버튼 노출/레이아웃 가드까지 사용자가 직접 확인, 정상 동작 확인됨.

---

## 다음에 할 일

### A. 어드민 대시보드 나머지 화면 (사용자 지시 순서: 사용자 → 앱 관리 → 통계 → 캘린더 → 설정)

기존 `/admin` 레이아웃·사이드바·디자인 토큰(다크 사이드바 + 라이트 콘텐츠, `rounded-2xl border border-slate-200 bg-white p-5` 카드, slate 본문 + emerald 포인트) 그대로 재사용. 각 화면 완성 시 실 배포 후 스크린샷으로 확인할 것.

1. **사용자** (`/admin/users`) — 로그인 사용자 테이블(이메일/role 뱃지/OAuth provider/최근 접속/가입일), role 필터, 검색. `viewer.users` 테이블 실측: 컬럼 `group_id/username/password_hash/nickname/email/gender/birth_year/preferred_genres/bio/created_at/updated_at/id`, 현재 4명. 목록 API가 아직 없어서 **백엔드에 사용자 목록 조회 API 신규 필요**(require_admin 가드 필수). OAuth provider는 `user_identities` 테이블 조인 필요.
2. **앱 관리** (`/admin/apps`) — mova/gildle/titanic/doro/star_craft 카드, mock 상태값으로 시작.
3. **통계** (`/admin/stats`) — 에이전트 호출 수 추이(라인)/크롤링 실적(바)/에이전트별 사용 비율(도넛)/사용자 활동(영역), 기간 필터. 차트 라이브러리 미설치 확인됨 — recharts 설치 필요(`package.json`에 없음, 먼저 확인).
4. **캘린더** (`/admin/calendar`) — 월간 뷰, mock 이벤트(크롤링 스케줄/에이전트 실행 예약), 날짜 클릭 시 해당일 이벤트 목록.
5. **설정** (`/admin/settings`) — 일반/에이전트 기본값/API 연동/보안(`ADMIN_EMAILS`는 읽기전용, 값 노출 주의) 섹션. 폼 저장은 mock/TODO.

각 화면 데이터 페칭은 `suvis/lib/admin-*-api.ts`로 분리해 mock→실연동 전환이 쉽게.

### B. 나머지 비전/ML 에이전트 (마스터 문서 우선순위: Echo → Sentinel → Argus/Loom/Atlas → Prisma/Chronos)

지시서: `apps/ontology/_docs/02~08_*.md` (각 태스크별 헤르메스 단계 정의됨)

| # | 이름 | 태스크 | 모델 | 파인튜닝 |
|---|------|--------|------|---------|
| 7 | **Echo** | 감성 분석 | Qwen/KLUE-RoBERTa | QLoRA ⭐ (최우선) |
| 6 | **Sentinel** | 이상 탐지 | PatchCore/EfficientAD | 학습 최소, 가벼움 |
| 2 | **Argus** | 물체 감지 | RT-DETR/YOLOv8 | LoRA/full |
| 3 | **Loom** | 시맨틱 분할 | SegFormer-B0 | LoRA |
| 4 | **Atlas** | 자세 추정 | ViTPose/RTMPose | LoRA/full |
| 5 | **Prisma** | 이미지 생성 | Stable Diffusion 1.5 | LoRA (VRAM 최난도) |
| 8 | **Chronos** | 동영상 분류 | VideoMAE/X3D | LoRA/full (최난도) |

각 완성 시 `/viewer/admin/agents` mock 데이터를 해당 항목만 실제 interactor 호출로 교체.

### C. 알려진 기존 이슈 (이번 작업 범위 밖, 별도 처리 필요)

- **`/admin/dispatch`, `/admin/harvester` 백엔드 API 자체에 인증이 전혀 없음** — 이번에 만든 `AdminAuthGate`는 프론트 URL 접근만 막을 뿐, 백엔드 엔드포인트를 직접 호출하면 그대로 뚫림. 필요시 해당 라우터들에도 `require_admin` 추가해야 함.
- `apps/mova/tests/test_import_interactor.py` 2건, `test_llm_error_handling.py` — 이번 세션과 무관한 기존 실패(과거 세션에서 확인됨).
