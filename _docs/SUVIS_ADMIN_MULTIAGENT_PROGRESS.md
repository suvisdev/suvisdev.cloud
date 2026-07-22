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

---

## 2026-07-21 (집) 추가 완료

### 4. 사용자 화면 (`/admin/users`)

**백엔드** — `GET /viewer/admin/users` (require_admin 가드, 실 DB 연동)
- `viewer/adapter/inbound/api/schemas/admin_users_schema.py` — Pydantic response
- `viewer/app/dtos/admin_users_dto.py` — `UserAdminDto` + `to_schema()`
- `viewer/app/ports/input/admin_users_use_case.py` / `output/admin_users_repository.py` — Port ABCs
- `viewer/app/use_cases/admin_users_interactor.py`
- `viewer/adapter/outbound/pg/admin_users_pg_repository.py` — `users` 전체 조회 + `user_identities` LEFT JOIN(2-query), `ADMIN_EMAILS` env로 role 산출
- `viewer/dependencies/admin_users_provider.py`
- `viewer/adapter/inbound/api/v1/admin_users_router.py`
- `viewer/adapter/inbound/api/__init__.py` — `admin_users_router` include 추가

**프론트엔드**
- `suvis/lib/admin-users-api.ts` — `listAdminUsers()` API 클라이언트
- `suvis/app/admin/users/page.tsx` — 이메일/닉네임 검색 + 역할 필터(전체/관리자/사용자) + 테이블

**학원에서 확인할 것**
1. 백엔드 서버 재시작 후 `GET /viewer/admin/users` — admin 토큰으로 200, 비admin으로 403 확인
2. `/admin/users` 페이지 접속 — 사용자 테이블 렌더링 확인 (현재 DB에 4명)
3. 검색창에 이메일 일부 입력 → 필터 동작 확인
4. 역할 필터 버튼(관리자/사용자) 클릭 → `ssuvisdev@gmail.com`이 관리자 뱃지로 표시되는지 확인
5. OAuth provider 칸 — Google/Kakao/Naver 뱃지 노출 확인

---

---

## 2026-07-21 (집, 노트북) 추가 진행 — 02~08 에이전트 H0 + Echo H1 착수

### 5. 02~08 비전/ML 에이전트 H0 스캐폴딩 (전체 완료)

`00_COMMON_conventions.md` 규약대로 `app/dtos/`, `app/ports/{input,output}/`, `app/use_cases/` 4파일씩 × 7개 태스크 생성. **파일명은 doc 파일명 스템과 일치**시킴(`02_object_detection_agent.md` → `object_detection_*.py` 등, `argus`/`loom` 같은 별칭은 안 씀). docs의 `파일명:` 표기도 동일하게 수정 완료. `PYTHONPATH=apps` 기준 전체 import 검증 통과.

| doc | 파일 prefix |
|---|---|
| 02_object_detection | `object_detection_` |
| 03_semantic_segmentation | `semantic_segmentation_` |
| 04_pose_estimation | `pose_estimation_` |
| 05_image_generation | `image_generation_` |
| 06_anomaly_detection | `anomaly_detection_` |
| 07_sentiment_analysis | `sentiment_analysis_` |
| 08_video_classification | `video_classification_` |

**아직 안 한 것(전부)**: H1(VRAM 실측)~H6(에이전트 통합) — 지금은 포트/인터페이스 껍데기만 있고 실제 추론 어댑터(구현체)는 하나도 없음.

### 6. 환경 확인 — 노트북(RTX 4060 8GB)에서 로컬 개발 가능 확정

- 이 노트북 GPU: **RTX 4060 Laptop 8GB VRAM** — 서버(ssu, RTX 3050 8GB)와 VRAM 용량 동일, 세대는 더 신형. 노트북에서 H1~H4 먼저 개발 후 서버(3050)에서 재검증하는 흐름으로 진행 (`memory/project_dev_environments.md` 참고).
- conda `pytorch_env` 환경에 이미 `torch 2.12.0+cu126`(CUDA 사용 가능) 설치돼 있었음.
- Echo(07, 감정 분석) 진행을 위해 `transformers`, `peft`, `bitsandbytes`, `trl`, `accelerate`를 `pytorch_env`에 추가 설치. `bitsandbytes` 4bit 연산 Windows에서 정상 동작 확인(4bit Linear forward 성공).
- **학원 작업환경 = 별도 PC가 아니라 우분투 SSH 서버(ssu)에 직접 접속해서 그 서버 안에서 개발+git 전부 처리하는 구조.** 2026-10 이후 학원에서 이 서버 접근이 끊길 예정 → 그 이후엔 노트북+데스크탑 기준으로 전환.

### 7. Echo(07_sentiment_analysis) H1 완료 ✅ (2026-07-22, ssu 서버) — EXAONE-3.5-2.4B-Instruct

**사용자 결정**: Qwen 대신 **EXAONE-3.5-2.4B-Instruct**로 진행(온프레미스에 이미 EXAONE 생태계가 있어 시너지). 기존 코드베이스의 EXAONE 활용(`core/lol/awq_exaone_orchestrator.py`)은 7.8B를 AWQ로 **서빙만** 하는 별도 프로세스(`~/.venv-exaone`, `awq_server`)라 QLoRA 학습에는 못 씀 — 2.4B를 HuggingFace(`LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct`)에서 새로 받아 학습용으로 세팅해야 함.
**추가 결정(2026-07-22)**: 앞으로 이 프로젝트의 생성형 QLoRA 작업은 **Qwen을 기본 후보에서 제외하고 EXAONE-2.4B로 고정**. `01`·`00_COMMON_conventions.md`의 "Qwen 에이전트가 GPU 점유 중" 문구는 다른 프로세스 존재를 설명하는 환경 서술이라 그대로 둠, `07_sentiment_analysis_agent.md`는 모델 선택 섹션 전체를 EXAONE-2.4B 기준으로 수정 완료.

**어제(2026-07-21) 막혔던 지점**: 4bit 로드·LoRA 부착까지는 성공, forward pass에서 `create_causal_mask() got an unexpected keyword argument 'input_embeds'`로 실패.

**오늘 이어서 진행, 해결**:
1. 처음엔 어제 기록대로 "`transformers~=4.43` 다운그레이드가 정석"이라 보고 전용 venv(`uv venv`)에 `transformers==4.43.3`+구버전 peft/bitsandbytes/accelerate로 시도 → **다른 에러로 실패**: `ImportError: cannot import name 'RopeParameters' from transformers.modeling_rope_utils`. 원인: EXAONE HF repo의 remote code(`configuration_exaone.py`, `modeling_exaone.py`)가 어제 이후 **repo 쪽에서 업데이트됨**(다운로드 로그에 "새 버전 발견" 표시) — 이제 최신 transformers API를 요구하도록 바뀌어 있어서, 오히려 구버전 transformers로 내리면 더 일찍 깨짐.
2. `transformers`/`peft`/`bitsandbytes`/`accelerate`를 전부 최신으로 올려서 재시도(`transformers==5.14.1` — 어제와 동일 버전) → config 로드는 통과했지만 **어제와 같은 `create_causal_mask` 에러 재현**. 즉 이건 버전 문제가 아니라 **EXAONE repo의 remote code 자체가 실제 transformers 5.14.1의 `create_causal_mask()` 시그니처(`inputs_embeds`, `cache_position` 파라미터 없음)와 안 맞는 버그**.
3. `_tmp_h1_exaone_vram_check.py` 최상단에 `transformers.masking_utils.create_causal_mask`를 감싸는 **얇은 compat 몽키패치**(`input_embeds`→`inputs_embeds` 이름 교정 + `cache_position` 등 신호 안 받는 인자 드롭) 추가 → **forward pass 성공**.

**실측(최종)**: 4bit(nf4) 로드 델타 2158MB, LoRA(r=8, q/v_proj) 델타 8MB, forward pass 후 총 할당 2180.1MB, free 4.25GB(8GB 중). **H1 판정: 여유 충분, 통과.**

**재현 환경 주의사항**:
- torch는 `--index-url https://download.pytorch.org/whl/cu126`로 `torch==2.13.0+cu126` **명시 고정** 필요 — 안 그러면 기본이 cu130 빌드로 잡혀서 이 서버 드라이버(12.6)와 안 맞아 `torch.cuda.is_available()`이 `False`가 됨.
- 이 서버(ssu, RTX 3050 8GB)는 `lora-server`(systemd `--user` 서비스, mova 채팅 RAG 상시 서빙)가 VRAM을 거의 다 씀 → H1 실행 전 `systemctl --user stop lora-server`로 내렸다가 완료 후 `systemctl --user start lora-server`로 반드시 복구. **H2(학습) 이후에도 같은 절차 필요.**
- 상세 재현 기록은 `suvisdev/apps/ontology/_docs/07_sentiment_analysis_agent.md` "5. H1 완료 기록" 참고.

**H2(데이터셋 준비) 완료 ✅ (2026-07-22, 이어서 같은 세션에서 진행)**: NSMC(네이버 영화 리뷰) 기반, output은 라벨만("긍정"/"부정", 사용자 결정 — 이유 설명은 스킵). `scripts/prepare_echo_sentiment_dataset.py`로 라벨당 균형 샘플링(train 2000/val 400), `apps/ontology/resources/echo_sentiment_train/`에 저장. 토크나이저 검증 결과 max_seq_length=256로 전체 수용(p95=93, max=135). 상세: `07_sentiment_analysis_agent.md` "6. H2 완료 기록".

**H3(파인튜닝) 완료 ✅**: `scripts/train_echo_sentiment.py`, val accuracy 87.75%(F1 0.8778), 어댑터 `apps/ontology/runs/echo_sentiment/adapter`.

**H4(추론 어댑터) 완료 ✅**: 여기서 중요한 걸 하나 발견함 — 프로덕션 `requirements.txt`는 `transformers==4.47.1`로 고정돼 있고 `apps/dispatch`의 다른 기능이 이미 그 버전에 의존 중이라 못 올림. H1/H3에서 쓴 "최신 transformers + 몽키패치" 방식 대신, **EXAONE HF 리포를 v5 마이그레이션 이전 커밋(`e949c91...`)으로 `revision=` 고정**하는 방식으로 전환 — `transformers==4.47.1` 그대로 몽키패치 없이 동작 확인. `EchoSentimentAdapter`(`TimmConvnextAdapter`와 동일하게 호출당 로드→추론→언로드), DI 프로바이더, `@pytest.mark.gpu` 통합 테스트(신규 마커) 추가, `requirements.txt`에 `peft`/`bitsandbytes` 추가. 상세: `07_sentiment_analysis_agent.md` "7~8. H3/H4 완료 기록".

**다음에 이어서 할 일**:
- [ ] H5(MCP tool 노출) → H6(에이전트 통합) — 사용자 확인 받고 진행
- [ ] `_tmp_h1_exaone_vram_check.py`, `_tmp_h2_echo_dataset_check.py`는 재현/검증 스크립트로 유지 중(아직 삭제 안 함)

---

## 다음에 할 일

### A. 어드민 대시보드 나머지 화면 (사용자 지시 순서: 사용자 → 앱 관리 → 통계 → 캘린더 → 설정)

기존 `/admin` 레이아웃·사이드바·디자인 토큰(다크 사이드바 + 라이트 콘텐츠, `rounded-2xl border border-slate-200 bg-white p-5` 카드, slate 본문 + emerald 포인트) 그대로 재사용. 각 화면 완성 시 실 배포 후 스크린샷으로 확인할 것.

1. ~~**사용자** (`/admin/users`)~~ ✅ 완료 (2026-07-21)
2. ~~**앱 관리** (`/admin/apps`)~~ ✅ 완료 (2026-07-22) — `lib/apps-catalog.ts`의 실제 카탈로그(mova/gildle) + doro/star_craft mock 카드.
3. ~~**통계** (`/admin/stats`)~~ ✅ 완료 (2026-07-22) — recharts는 이미 `package.json`에 설치돼 있었음(2.15.0, 확인 완료). 라인/바/도넛/영역 + 기간 필터(일/주/월). 도넛 카테고리 컬러는 dataviz 스킬 `validate_palette.js`로 검증(8슬롯, light/#ffffff surface, 전체 PASS).
4. ~~**캘린더** (`/admin/calendar`)~~ ✅ 완료 (2026-07-22) — 커스텀 월간 그리드(react-day-picker 미사용, 관리자 화면 톤에 맞춰 직접 구현), mock 이벤트, 날짜 클릭 시 우측 패널에 목록.
5. ~~**설정** (`/admin/settings`)~~ ✅ 완료 (2026-07-22) — 일반/에이전트 기본값/API 연동/보안 4섹션. `ADMIN_EMAILS` 실값은 클라이언트로 절대 내려보내지 않고 마스킹된 문자열만 하드코딩. 저장 버튼은 mock(실제 반영 없음).

각 화면 데이터 페칭은 `suvis/lib/admin-*-api.ts`(apps/stats/calendar/settings)로 분리해 mock→실연동 전환이 쉽게. `tsc --noEmit` 통과 확인, 브라우저 스크린샷은 이 세션에 도구가 없어 미실시 — 사용자 직접 확인 필요.

### B. 나머지 비전/ML 에이전트 (마스터 문서 우선순위: Echo → Sentinel → Argus/Loom/Atlas → Prisma/Chronos)

지시서: `apps/ontology/_docs/02~08_*.md` (각 태스크별 헤르메스 단계 정의됨)

| # | 이름 | 태스크 | 모델 | 파인튜닝 |
|---|------|--------|------|---------|
| 7 | **Echo** | 감성 분석 | EXAONE-2.4B/KLUE-RoBERTa | QLoRA ⭐ (최우선, H1 완료) |
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
