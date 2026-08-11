# SUVIS 어드민 대시보드 + 멀티에이전트 진행 상황

컨텍스트가 끊길 경우를 대비한 재개용 메모. 완료된 작업은 상세 로그 대신
**위치만** 남긴다(중복 기록 방지). 관련 상세 지시서:
- `suvisdev/_docs/RBAC_agent_dashboard.md` (RBAC + 어드민 대시보드 H0~H4)
- `suvisdev/apps/ontology/_docs/00_COMMON_conventions.md` + `01~08_*.md` (에이전트별 지시서)

---

## 완료됨 (상세는 각 문서 참고, 여기선 재기록 안 함)

- **어드민 대시보드**: 홈/사용자/앱관리/통계/캘린더/설정 전 화면 구현 + 실 연동
  (`suvis/app/admin/*`, `suvis/lib/admin-*-api.ts`). RBAC 가드(`require_admin`,
  `AdminAuthGate`)까지 포함.
- **01(이미지 분류, 포스터→장르)**: H0~H6 전체 완료. `01_image_classifier_agent.md` §7.
- **07(Echo, 감정분석)**: H0~H6 전체 완료(NSMC 기반, val acc 87.75%).
  `07_sentiment_analysis_agent.md` §5~§10.
- **06(Sentinel, 이상 탐지)**: H0~H6 전체 완료(CLIP 제로샷 포스터 판별 +
  Laplacian 블러, `/vision/upload` 게이트). `06_anomaly_detection_agent.md`
  §5~§6.9. 미결 백로그는 아래 "다음 / 남은 작업" 참고.
- **02~08 H0 스캐폴딩**: 포트/인터페이스 껍데기 7개 태스크 전부 생성 완료
  (실제 추론 어댑터는 없음).
- **03(Loom, 시맨틱 분할)**: **제외 확정(2026-07-27)**. 용도 재정의("보도 유무/폭")
  까지 검토 후 관문0 실측 → 보도 신호 자체가 서울 OSM에 없음(`sidewalk=*`
  0.4~1.2%, 커버리지 보도/도로 = 0.04, `width` 전무). 04·08과 동급 정식 제외.
  상세: `03_semantic_segmentation_agent.md` §5.4, WORK_LOG 2026-07-27.
- **alembic 마이그레이션 체인 베이스라인 누락 수정(2026-07-27, 후속
  2026-07-29)**: `users`/`groups`/`admins`, mova 전체 테이블, `dispatch_adress`,
  `titanic_passengers`, `vision_uploads` 등이 `create_all()`로만 존재하고
  체인엔 CREATE가 없던 문제. 베이스라인 마이그레이션 신설로 완전히 빈 DB에서
  `alembic upgrade head` 성공 검증(EC2 임시 컨테이너, 2026-07-27). 이후
  같은 방식으로 빈 DB 재검증하다 `hub_knowledge`(2026-07-14 추가, 체인에
  CREATE 없이 create_all 전용이었던 테이블)를 추가로 발견해 `20260729_0002`로
  보완, 도커 임시 컨테이너로 34개 테이블 전부 생성되는 것까지 재확인.
  상세: WORK_LOG 2026-07-27 [3], 2026-07-29.
- **PDF 업로드→추출→요약 파이프라인(execsuite, 구 silicon_valley, 2026-07-27, `pdf_loader_*` 네이밍)**:
  `POST /api/v1/pdf/summarize` — neo4j-graphrag PdfLoader 추출 + EXAONE(Ollama)
  요약 + `pdf_loader_documents` 테이블 저장, inbound router~outbound repository
  전 계층 완성. 실 DB 마이그레이션 실행/Ollama 연동 실사용 테스트는 미검증.
  상세: WORK_LOG 2026-07-27 [4]·[5](네이밍 환원).
- **execsuite(구 silicon_valley) LangChain 채팅 파이프라인(2026-07-28)**: `POST /api/v1/langchain/chat`
  — semantic_router_interactor(ontology)로 의도 판단 후 LangChain LCEL 체인이
  destination별 시스템 프롬프트로 답변 생성. 클린 아키텍처 전 계층 완성,
  semantic_router의 `HubRagError` 미처리로 500 plain-text 새던 버그도 수정.
  모델은 최초 ChatOllama(exaone3.5:2.4b)로 구현했다가 같은 날 `ChatGoogleGenerativeAI`
  (Gemini, `core.matrix.Keymaker` 키 재사용)로 교체 — 실제 응답 확인 완료.
  상세: WORK_LOG 2026-07-28.
- **기존 실패 테스트 수정(2026-07-28)**: `apps/mova/tests/test_import_interactor.py`
  2건 — `ImportInteractor` 생성자에 `box_office`/`hub_rag`가 추가된 뒤 테스트가
  안 따라가서 실패하던 것, `AsyncMock()` 인자 추가로 수정. `test_llm_error_handling.py`는
  이미 통과 상태였음(기록이 stale). 8개 전부 통과 확인.
- **어드민 백엔드 인증 공백 — dispatch watcher/judge/spam/adress 감사(2026-07-28)**:
  watcher·judge는 `/myself` 스캐폴딩 스텁뿐(위험 없음), spam은 프론트/백엔드
  어디서도 호출 안 하는 미사용 코드(위험 낮음). **adress는 실제 문제 발견** —
  `search`/`upload`에 인증이 전혀 없었고, 어드민 UI(`admin/dispatch/contacts`)뿐
  아니라 LESSON 공개 데모(`suvis/app/mail/contacts`, 로그인 개념 없음)도 같은
  엔드포인트를 호출 — 익명 방문자가 실제 주소록 DB에 쓰기 가능했음. 2026-07-27과
  동일 패턴으로 `require_admin` 추가 + 프론트 프록시 2개(`search`/`upload`
  route.ts)·어드민 클라(`admin/dispatch/contacts/page.tsx`)가 세션 Bearer
  전달하도록 수정. **`suvis/app/mail/contacts`(공개 레슨 데모)는 이제 401 —
  이 페이지 자체를 지울지/막을지는 별도 결정 필요(아래 백로그).**
- **CLAUDE.md 응답 언어 지침 추가(2026-07-28)**: 항상 한국어로만 답변, 다른 언어
  사용 금지를 루트 `CLAUDE.md`에 명시.
- **`test_send_email_interactor.py` 실패 2건 수정(2026-07-28)**: `SendEmailInteractor.send()`가
  이메일 품질 개선을 위해 `orchestrator.generate()`에 `system=` 키워드 인자를
  추가한 게 실제 기능인데, 테스트 2건이 예전(위치 인자 하나) 시그니처를
  가정하고 있어 깨졌던 것 — 테스트를 실제 호출 형태에 맞게 수정. 14개 전부 통과.
- **PyJWT/langchain-ollama 미설치 해소(2026-07-28)**: `/home/a/.venv`에서
  `require_admin` import가 안 되던 문제를 `PyJWT[crypto]==2.10.1`,
  `langchain-ollama==1.1.0` 개별 설치로 해결. `apps/mova/tests` + `apps/dispatch`
  전체 47개 테스트 통과 확인(이전엔 jwt 없어 수집 자체가 실패하던
  `test_whoami_router.py`도 포함).
- **`catboost`/Python 3.14 빌드 문제 해소 + `pip install -r requirements.txt`
  전체 성공(2026-07-28)**: `catboost==1.2.8`→`1.2.10`으로 올렸더니 Python
  3.14용 사전빌드 wheel이 존재해 빌드 에러 없이 설치됨. 전체 `requirements.txt`
  설치가 끝까지 성공(torch-cu126 포함). `.import_linter_cache`/`.mypy_cache`
  (18M)/`.pytest_cache`/`.ruff_cache` 정리(전부 재생성 가능한 도구 캐시, git
  미추적).
- **`apps/silicon_valley` → `apps/execsuite` 이름 변경(2026-07-28)**: `admin`은
  이미 다른 의미(어드민 대시보드/RBAC)로 쓰이고 있어 충돌 우려로 `execsuite`로
  확정. 102개 파일 rename + 46개 파일 import·외부 3곳(`main.py`,
  `alembic/env.py`, `.importlinter`) 전부 치환. `execsuite_router`/`main.py`
  import 검증 완료.
- **`suvisdev/labs/` 04(자세 추정)·08(영상 분류) 독립 실습 데모(2026-07-28)**:
  `apps/`와 완전히 분리된 고립 영역(`main.py` 미등록, `.importlinter` 미포함).
  Port는 참조 구현(실제 편입 시 그 앱 컨벤션대로 재배치), DTO는 도메인
  중립이라 공유 가능하다고 README에 명시. GPU 없어 학습 없이 사전학습 모델
  추론만 — 04는 YOLOv8n-pose(3.3M), 08은 torchvision s3d(8.3M, 가장 가벼운
  옵션으로 실측 비교 후 선택). 둘 다 실제 실행해 결과 확인 완료. 상세:
  WORK_LOG 2026-07-28 [6].
- **`suvisdev/labs/semantic_segmentation/` 03(시맨틱 분할) 추가(2026-07-28)**:
  04·08과 동일 패턴. 04·08과 달리 03은 "용도 없음"이 아니라 "용도(서울 보도
  검출)는 있었는데 검증 데이터(OSM sidewalk 태그 0.4~1.2%)가 없어서" 막힌
  케이스임을 README에 구분해 명시. 모델은 torchvision segmentation 4종
  실측 비교 후 가장 가벼운 `lraspp_mobilenet_v3_large`(3.2M, Pascal VOC —
  도로/보도 클래스 자체가 없어 막힌 용도와 구조적으로 무관) 선택. 실제
  실행해 결과 확인 완료(bus 31.0%, person 12.2% 정상 검출).
- **mova 부팅 자동 작업 `ENABLE_MOVA_STARTUP` 플래그(2026-07-28)**: 집(GPU/
  EXAONE)·EC2(GPU 없음, Gemini) 두 배포 환경에서 mova의 TMDB 시드·chat_trend/
  KOFIC 스케줄러(전부 Ollama 의존)를 EC2에서 코드 변경 없이 끌 수 있게
  `main.py` `lifespan()`에 플래그 추가(기본값 true, 하위호환). mock으로
  DB/Ollama 없이 분기만 격리 검증 — false일 때 3개 함수 전부 미호출+
  "비활성화됨" 로그, 미설정 시 기존대로 전부 호출됨을 확인. 부수 발견:
  `seed_assistants_if_empty` import가 존재하지 않는 모듈 참조하는 기존 버그
  (아래 백로그).
- **titanic 도메인 테스트 4개 재작성 + 실제 버그 2건 수정(2026-07-28)**: 조사
  결과 단순 리네임 드리프트가 아니라 도메인 재설계(관련 VO·엔티티·깨진
  테스트가 전부 같은 커밋에서 한꺼번에 업로드됨)였음을 확인. mova/gildle도
  "개념당 VO 하나" 컨벤션을 써서 지금 titanic 도메인(`PassengerIdentity`/
  `Survived`)이 실제 컨벤션과 일치함을 검증 후, `test_korean_ai_adapter.py`
  삭제(중복 고아) + 나머지 3개 삭제 후 41개로 새로 작성(frozen 불변성,
  DDD 동등성, DIP 어댑터 스왑 포함 — titanic이 기준선이라 다른 앱이 참고할
  모범 형태로). 작성 중 `summary()`/`to_orm_fields()`가 존재하지 않는
  `identity.age`를 참조하는 실제 버그 발견해 수정. `apps/titanic/tests`
  44개 전부 통과.
- **`seed_assistants_if_empty` 죽은 코드 제거(2026-07-28)**: 실제 조사 결과
  리네임이 아니라 한 번도 구현된 적 없는 기능(repository에 count/insert
  메서드·기본 시드 데이터 전부 없음)으로 확인 — `main.py`에서 해당
  try/except 블록 통째로 제거. `ENABLE_MOVA_STARTUP` 두 시나리오 재검증
  결과 WARNING 완전히 사라지고 플래그 동작은 그대로 정상.
- **CLIP 다운로드 hang 해결 + `.claude/rules/` 규칙 정비(2026-07-29)**: hang은
  collection이 아니라 테스트 실행 중 `from_pretrained()`의 HF Hub 왕복이 원인
  (캐시에 490MB `.incomplete` 블롭 잔존 확인). `apps/ontology/test/conftest.py`에
  `HF_HUB_OFFLINE`을 걸어 "캐시 있으면 통과, 없으면 즉시 실패"로 전환 — Sentinel
  판별 로직은 미변경. 함께 `.claude/rules/` 5종(typescript·api-standards·testing·
  security/auth·security/pci)과 루트 `CLAUDE.md` 하네스/명령어/환경변수 섹션을
  실측 기반으로 작성. `security/auth.md`에는 아래 백로그의 미해결 건(IDOR,
  `mail/contacts`)을 "복사하지 말 것"으로 명시해 두었다. 상세: WORK_LOG 2026-07-29.
- **06 Sentinel 소프트 플래그 DB 지속화 + 어드민 오버라이드 엔드포인트
  (2026-07-29)**: 저장 계층을 S3(자격증명 미연결)/DB(`VisionRepository`,
  구현은 있으나 DI 미배선) 중 DB로 일원화. `vision_uploads`에
  `poster_confidence`/`sharpness_score`/`is_poster_warning` 컬럼 추가
  (alembic `20260729_0001`), `VisionRepository`를 DI에 연결, `PATCH
  /vision/{upload_id}/poster-flag`(`require_admin`) 신설. `alembic upgrade
  head` 실 적용은 같은 날 후속으로 빈 DB 검증 완료(위 baseline 항목 참고).
  상세: WORK_LOG 2026-07-29.
- **execsuite `rangchain`/`ranggraph` 네이밍 오타 정정 + LangGraph+Neo4j 확장
  전략 문서화(2026-07-30)**: 2026-07-28 LangChain 채팅 파이프라인 구현 시
  붙은 `rangchain`/`ranggraph` 오타를 코드 파일 10개(클래스명·함수명 포함)와
  관련 문서 5개에서 `langchain`/`langgraph`로 일괄 정정. `apps/execsuite/_docs/langgraph-strategy.md`에
  "LangChain+pgVector → LangGraph+Neo4j" 4단계 도입 로드맵(Neo4j 도입 →
  Hybrid Retrieval → LangGraph 전환 → 에이전틱 피드백 루프) 신규 작성 —
  문서화만, 구현은 착수 전. 상세: WORK_LOG 2026-07-30.
- **`docker-compose.yaml` Neo4j 서비스 provisioning(2026-07-30)**: GraphRAG용
  Neo4j 컨테이너 추가(heap 1G/pagecache 512m 캡, 127.0.0.1 전용 바인딩,
  `.env` `NEO4J_PASSWORD` 참조, named volume) — pgvector/기존 서비스는
  불변, `requirements.txt`도 아직 미변경(provisioning까지만). 김에 발견한
  사전 존재 손상 2건(`docker-compose.yaml` 끝 stray `1`, `.env` 76행 깨진
  셸 명령어 조각)도 제거. **컨테이너 실기동/검증은 미완료** — 이 세션의
  WSL에서 Docker 데몬 연결 불가(Docker Desktop WSL 통합 문제로 추정),
  사용자가 별도 환경에서 `docker compose up -d neo4j` 확인 필요. 상세:
  WORK_LOG 2026-07-30.
- **mova TMDB credits 배선(actors/characters/movie_directors) 설계+구현
  (2026-07-30)**: 조사 결과 actors/characters가 스키마·읽기 API는 있지만
  쓰기 경로가 0건이라 pg actors 0행이었음을 확인(movies.embedding도 같은
  패턴 — 컬럼만 있고 채우는 코드 없음). Phase A(조사·설계 보고, 코드 변경
  금지)를 거쳐 사용자가 확정한 설계대로 Phase B 구현: alembic 마이그레이션
  `20260730_0001`(actors.tmdb_person_id UNIQUE, characters.billing_order,
  movie_directors 조인 테이블, uq_actors_name_role DROP), TMDB credits
  전용 매퍼·Port·PgRepository·별도 backfill 유스케이스·수동 실행 CLI
  스크립트(`scripts/backfill_credits_cli.py`) 신규. 기존 seed_catalog_if_sparse/
  `_ingest_to_hub`/fetch_by_id는 전혀 안 건드림. 유닛 테스트 14건 추가,
  mova 전체 61개 전부 통과, import-linter 계약 위반 없음(레이어 경계 확인).
  **로컬 커밋만 완료, push는 사용자 확인 후.** 마이그레이션 실제 적용과
  backfill 실행은 EC2에서 별도 진행 필요(아래 백로그). 상세: WORK_LOG
  2026-07-30.
- **lora-server 초기화된 노트북 재세팅(2026-07-28)**: `~/.venv-exaone` +
  EXAONE-3.5-2.4B-Instruct-AWQ(원래 7.8B 계획에서 VRAM 여유 이유로 2.4B로
  변경)로 재구성. 학습된 LoRA 어댑터가 이 머신·백업 어디에도 없어 재학습
  대신 `serve.py`에 어댑터 없으면 베이스만 뜨는 폴백 추가(최소 수정),
  실기동으로 `/health`·`/generate` 검증 완료(VRAM ~2.5GB, 8GB 카드에서
  여유 충분). 아래 "VRAM 정책"의 lora-server 스펙과 일치. 상세: WORK_LOG
  2026-07-28 [11].
- **Neo4j 컨테이너 실기동 검증 + GraphRAG 스키마 생성(2026-07-30, EC2)**:
  이전에 미완이던 실기동 검증을 EC2에서 완료 — `docker compose exec neo4j
  cypher-shell`로 pg `movies` 스키마 기준 도메인 제약 4개(Movie.slug 등,
  자동 RANGE 인덱스 포함) + 벡터 인덱스 `movie_embedding`(768차원, cosine)
  생성, 전부 `ONLINE` 확인. 데이터(노드)는 아직 미투입 — TMDB/KOFIC import가
  나중에 채움. 상세: WORK_LOG 2026-07-30.
- **EC2 alembic 마이그레이션 적용 + backend 재배포로 로그인 500 복구
  (2026-07-30)**: `git pull`로 들어온 마이그레이션 2건이 backend 옛
  이미지 때문에 미적용이던 상태를 DB 백업 → backend 재빌드(디스크 부족
  해결 포함) → `20260729_0001` upgrade + `20260729_0002`는 `create_all()`과의
  이중 관리 충돌로 `stamp` 우회 → 로그인 401 정상화까지 복구. `create_all()`/
  alembic 이중 관리는 근본 원인으로 남아 있음(아래 "다음/남은 작업" 참고).
  상세: WORK_LOG 2026-07-30.
- **어드민 화면 미노출 수정 + OAuth 닉네임 표시/변경 기능(2026-07-30, EC2)**:
  `ADMIN_EMAILS` env 누락으로 RBAC role이 항상 `user`였던 버그 수정
  (`suvisdev/.env`에 추가). 겸사겸사 헤더에 이메일 유사 문자열(`username`)
  대신 `nickname`이 뜨도록 로그인 응답 체인 전체에 nickname 필드 추가,
  마이페이지에 닉네임 인라인 편집 UI + `PATCH /viewer/profile/{id}`(본인
  확인 가드 `shared/security/require_user.py` 신규) 추가. 실제 계정으로
  인증·소유권(401/403/200)·값 보존 수동 검증 완료. 상세: WORK_LOG 2026-07-30.
- **mova 리뷰 API 보안 하드닝 Phase A(2026-07-31)**: `POST /mova/reviews`·
  `POST /mova/reviews/activity`·`PATCH /mova/reviews/{review_id}`가 인증
  없이 열려 있고 `user_id`를 요청 바디에서 그대로 신뢰하던 것을
  `shared/security/require_user.py`(2026-07-30 mypage에서 신설한 것과 동일
  가드)로 잠금. PATCH는 `review.user_id`와 `principal.user_id` 대조해 403
  (IDOR 수정). `reviews.UNIQUE(user_id, movie_id)` 재작성 시 미처리
  `IntegrityError`로 500 나던 것을 인터랙터 레벨 upsert(기존 리뷰 있으면
  update, 없으면 insert)로 구조적으로 제거. 프론트 `createMovaReview()` +
  프록시 `route.ts`가 `Authorization` 헤더를 끝까지 전달하도록 3계층 배선.
  단위 테스트 9건(401/403/404/200 + upsert 분기) 추가, 회귀 없음. watched
  게이트('봤어요' 버튼)는 별도 백로그 항목("mova 리뷰 watched 게이트")으로
  의도적으로 남김. 상세: WORK_LOG 2026-07-31.
- **mova 리뷰 별점+리뷰 UX 완성(2026-07-31)**: 로그인 유저가 watched 여부
  무관하게 별점만/본문만/둘 다 제출 가능하게 확장(완전히 빈 제출만 422로
  거부). `ReviewCreateSchema` rating/body Optional화(rating은
  `ge=0.5,le=5.0,multiple_of=0.5`), 인터랙터에 `ReviewValidationError` 신설,
  `ReviewsPgRepository`의 rating=None 크래시 버그 수정 + 클램프 하한을
  0.5로 정정. 프론트는 기존 리뷰 prefill(수정 가능) + 리뷰 목록에서
  별점/본문 없는 쪽은 생략 표시. Phase A(인증·IDOR·upsert)·watched
  게이트(아래 백로그)는 건드리지 않음. 부수적으로 `apps/analytics/tests`가
  gildle과 테스트 모듈명이 충돌하던 버그(전체 스위트를 같이 돌릴 때만
  드러남)도 함께 수정. 상세: WORK_LOG 2026-07-31.
- **어드민 통계 — 방문자 탭 + 크롤링 탭(2026-07-31)**: `/admin/stats`를
  개요/방문자/크롤링 3탭으로 재구성. 방문자는 신규 백엔드 앱 `apps/analytics`
  (자체 방문 기록, GA 연동 없음)로 실집계, 크롤링은 `crawl_config.yaml` 정책 +
  Redis 마지막 실행 시각을 조합한 읽기 전용 현황판(harvester `GET /policies`
  신설). 코드 레벨은 전부 완성·단위 테스트 통과, **다만 alembic 마이그레이션
  `20260731_0001`을 실제 DB에 적용하는 건 미검증**(이 세션에서 Docker 접근
  불가 — 아래 "다음/남은 작업" 참고). 상세: WORK_LOG 2026-07-31.
- **suvis 레슨 메뉴 admin 전용 노출**: 헤더 LESSON 링크 + 하위 9개 페이지
  전체를 `AdminAuthGate`로 로그인(관리자) 전용 처리. `AdminAuthGate`를
  `app/admin/_components/`에서 `components/auth/`로 이동(다른 라우트에서도
  재사용). 상세: WORK_LOG 2026-07-31.
- **로컬 개발 DB(집, Docker) 완전 세팅(2026-08-02)**: `alembic_version`
  테이블조차 없던 미관리 DB를 스키마 재구축 → `alembic upgrade head`(head
  `20260731_0001`, 36테이블)로 정상화. `scripts/backfill_credits_cli.py`
  전량 실행으로 actors 389/characters 371/movie_directors 40 채움.
  `hub_knowledge`는 신규 `scripts/ingest_hub_knowledge.py`로 movies 39편
  전부 인제스트(호스트 Ollama `OLLAMA_HOST=0.0.0.0` systemd override 필요—
  이 호스트에 적용 완료). 상세: WORK_LOG 2026-08-02.
- **mova 대량 영화 수집 파이프라인 코드 완성(2026-08-02)**: TMDB
  `/discover/movie`(`TmdbAdapter.fetch_discover`+`TmdbCatalogAdapter.fetch_discover`,
  region/장르 필터), KOFIC 영화 목록(`KoficAdapter.fetch_movie_list`,
  `searchMovieList.json`), 배치 CLI(`scripts/bulk_import_movies.py` —
  `--source tmdb_popular|tmdb_discover|kofic`, `--country`, `--pages`,
  `--start-page` 재시작 지원) 신규. 영화당 upsert→credits 백필→hub_knowledge
  순으로 처리하고 단계별 실패는 해당 영화만 스킵. 유닛 테스트 6건 추가,
  `apps/mova/tests` 73개 전부 통과. **코드만 완성 — 실제 대량 실행(TMDB
  discover/KOFIC 목록으로 수만 편 적재)은 아직 안 함(아래 백로그).** 상세:
  WORK_LOG 2026-08-02.
- **susu(Flutter) 카카오 모바일 로그인 + 백엔드 JWT 발급(2026-08-03)**: 하네스
  문서 2건(`susu/_docs/`, `suvisdev/_docs/`), 백엔드(`apps/auth`) kapi 검증
  어댑터/모바일 전용 Redis refresh store(`auth:refresh:mobile:{userId}`)/유저
  자동 upsert/`POST /auth/kakao/mobile`·`/auth/mobile/refresh`·
  `/auth/mobile/logout` 라우트 + 테스트(G2/G3) 전부 완료, `pytest` 통과.
  Flutter 클라(`lib/auth.dart`, `lib/main.dart` 인트로영상→로그인→세션유지
  분기) + nginx `/auth/*` 라우팅까지 구현 완료. **EC2 배포 반영 + 폰 실기기
  카카오 로그인 E2E 성공까지 확인 완료**(EC2 auto-deploy.sh가 `docker compose
  restart`만 해서 `--build` 누락으로 코드 미반영이던 것 발견, 사용자가 직접
  `--build auth` + nginx 재시작 후 검증). iOS는 실빌드 미검증(아래 백로그).
  상세: WORK_LOG 2026-08-03.
- **mova 추천 챗 화면(feature slice, 2026-08-03)**: susu를 WebView가 아닌
  네이티브 앱으로 전환하는 첫 슬라이스. Dio+Riverpod+go_router 앱 뼈대
  (`lib/core/`), `features/mova/{data,domain,presentation}` 구조로
  `POST /mova/chat`(인증 불필요, 실제 라우터 확인 완료) 연동, 응답
  필드명(`reply`/`recommendations[].{id,movie_id,title,year,poster,synopsis,
  platform,hook}` 등) 그대로 매핑한 모델·포스터 카드 UI 완성.
  `flutter analyze` 클린. **실기기/데스크톱 실행 검증은 아직(아래 백로그).**
  상세: WORK_LOG 2026-08-03.
- **susu 네비게이션 재구성 + 로그아웃(2026-08-03)**: 로그인 성공/세션 유지 시
  메인 화면을 `StopwatchPage`에서 `IntroScreen`(마케팅 카드)으로 변경 —
  `StopwatchPage`는 이제 `IntroScreen`의 "스톱워치 열기" 버튼으로만 들어가는
  서브 화면. 로그아웃 버튼(`AuthSession.logout()` — `POST /auth/mobile/logout`
  best-effort + 로컬 세션 삭제)은 `IntroScreen` AppBar에 위치.
- **mova 추천 — 원격 GPU(집) 대응 하드닝(2026-08-03)**: EC2 백엔드는 유지하고
  mova 추천만 Cloudflare Tunnel로 뚫은 집 `lora_server`를 호출하는 구조로
  분리하기 위한 선행 작업. `LoraRecommendationOrchestrator` httpx 타임아웃
  세분화(connect 5s/read 60s), 네트워크 예외 1회 재시도(HTTP 에러는 즉시
  실패), `X-LoRA-Token` 헤더 인증(`lora_server`도 동일 검증 추가, 토큰
  비어있으면 로컬 개발 무영향), `.env.example` 가이드,
  `_docs/lora-remote-gpu-ops.md` 운영 문서, 테스트 6건 추가(`core/lol/tests`
  신규 — `pytest.ini` testpaths 추가). Gemini 자동 폴백은 의도적으로 미도입
  (수동 스위치 유지 — 어떤 모델이 답했는지 불투명해지는 것 방지).
  **실제 Cloudflare Tunnel 연결·EC2↔집 GPU 실 연동은 아직 안 함(아래 백로그).**
  상세: WORK_LOG 2026-08-03.
- **EC2 S3 실연결 + `/lesson/photos` OCR 기능(2026-08-04)**: EC2가 지금까지 S3에
  붙어본 적이 없었음을 실증으로 발견(IAM Role 미부착, `.env`에 AWS 키 자체가
  없어 `NoCredentialsError`) — `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`를
  EC2 `.env`에 추가해 해결(첫 시도 값은 시크릿 40자가 14자로 잘려 있어
  `InvalidAccessKeyId`로 재실패, 재발급 후 성공). `Tank.list_objects` 신규 +
  `apps/media`에 Gemini 멀티모달 OCR(`ocr.py`) + `GET /api/media/photos/ocr`
  (`require_admin`, 처음엔 관리자 본인 user_id로 좁혔다가 susu=카카오/웹
  관리자=구글이 별개 계정으로 남는 걸 발견해 전체 `media/` prefix로 확장,
  응답에 `user_id` 추가). `suvis/app/lesson/photos`에 프론트 페이지 신설.
  실제 S3 데이터(영수증 이미지)로 다운로드+OCR 종단 검증 완료. 별개로 EC2
  배포 시 `docker compose --env-file suvisdev/.env`를 빠뜨리면
  `POSTGRES_USER`등이 빈 값으로 치환돼 DB 연결이 깨지는 함정도 실제로
  겪고 기록(아래 "S3" 항목 갱신, 배포 시 항상 `--env-file` 필수).
- **어드민 통계 방문자 — EC2 alembic 재확인(2026-08-04)**: 백로그에 "EC2
  미적용"으로 남아 있었으나 실제로는 `alembic current`가 이미
  `20260731_0001 (head)`였고 `visitor_activity` 테이블도 실데이터 15행 보유—
  이전 세션 어느 시점에 이미 반영된 상태였음을 확인만 하고 완료 처리.
- **Neo4j 노드 데이터 재확인(2026-08-04)**: 백로그에 "스키마만 있고 노드는
  0건"으로 남아 있었으나 실제로는 Movie 40/Person 427/Genre 16/ACTED_IN 396/
  DIRECTED 44/HAS_GENRE 110이 이미 들어가 있음(EC2 `cypher-shell` 직접 조회로
  확인, 2026-07-30 스키마만 생성 이후 누군가 채워 넣은 것 — 이 세션 안
  애플리케이션 코드 경로는 아님, `apps/mova`·`apps/ontology` 전체에 neo4j
  드라이버 import 자체가 0건이라 어디서 채웠는지는 불명). **다만 "데이터
  투입" 자체는 완료됐어도 원래 목적(GraphRAG 활용)은 여전히 미완**이다 —
  이 데이터를 읽는 애플리케이션 코드가 한 줄도 없어서, 지금은 그냥 앱과
  무관하게 존재하는 그래프일 뿐. 백로그 표현을 "노드 0건"에서 "데이터는
  있으나 읽는 코드 없음"으로 정정.
- **mova TMDB credits 백필 EC2 재확인(2026-08-04)**: 백로그에 "EC2 미실행"으로
  남아 있었으나 실제로는 이미 반영돼 있었음 — `alembic current`가
  `20260731_0001 (head)`, `actors.tmdb_person_id`/`characters.billing_order`/
  `movie_directors` 전부 존재, 실데이터 actors 427(tmdb_person_id 427 전부
  채워짐)/characters 396/movie_directors 44(집 로컬 2026-08-02 시점의 389/
  371/40보다 많음). 실행할 것 없이 확인만 하고 완료 처리. "어드민 통계
  방문자"·"S3"에 이어 세 번째로 "미완료"로 적혀 있던 게 실제로는 이미
  끝나 있던 사례 — 이 문서의 백로그 최신성 자체를 주기적으로 재확인할
  필요가 있어 보임.
- **mova 리뷰 watched 게이트(2026-08-04)**: 백로그 항목 구현 완료.
  `ReviewsRepositoryPort.has_watched(user_id, movie_id)` 신설(PG 구현은
  `user_actions`에서 `action_type=watched` EXISTS 조회), `ReviewsInteractor
  .add_review()` 맨 앞에서 게이트(미시청이면 신규 `ReviewNotWatchedError`
  403 — 별점 존재 여부로 판정하지 않음, 순환 논리 방지 원칙 그대로 지킴).
  프론트: `POST /mova/reviews/activity` 프록시·`addReviewActivity()` 신규,
  영화 상세 페이지에 "봤어요" 버튼 추가(찜하기 버튼과 동일 톤). 조회 API가
  없어 버튼 상태는 세션 로컬에서만 추적(새로고침하면 리셋되지만 서버 기록은
  유지되어 게이트는 정상 통과). 인터랙터 테스트 2건 추가 + 기존 6건에
  `has_watched` 명시적 스텁 보강, mova 전체 81개 전부 통과.
- **폰 카메라 → S3 업로드(2026-08-03)**: 새 경량 앱 `apps/media`(DB 없음) —
  `POST /api/media/photos`(JWT 필요, JPG/PNG/WebP·10MB 제한, 기존 Sentinel
  vision 업로드와 무관하게 분리), `.importlinter`에 `media` 스포크 등록,
  테스트 5건. Flutter는 `features/media/`(image_picker 카메라 촬영 → Dio
  multipart 업로드), `IntroScreen`에 카메라 버튼. `dio_client.dart`의
  Authorization 슬롯을 실제 로그인 JWT로 연결(그동안 플레이스홀더였던 자리
  실사용 전환). **실기기 검증은 아직(아래 백로그).**
  상세: WORK_LOG 2026-08-03.
- **mova 대량 영화 수집 첫 실전 배치 실행(2026-08-05, EC2)**: 전날 로컬
  미커밋 상태였던 도미노 실패 수정(`session.rollback()`)을 커밋→PR
  #33→main 머지→EC2 `git pull`+`docker compose up -d --build backend`로
  배포 완료 확인(컨테이너 내 `grep -c session.rollback` 5건 확인) 후
  `--source tmdb_popular --pages 50 --start-page 3` 실행. 결과
  `succeeded=1000 failed=0 skipped=0`, movies 142→1055(+913, 순증 91.3%,
  초반 40건 27.5% 대비 대폭 상승 — start-page 3로 겹치는 초반 페이지를
  건너뛴 효과), actors 1163→7058(+5895)/characters 1204→10041(+8837)/
  movie_directors 142→1116(+974). hub_knowledge는 0 불변(EC2에 Ollama
  없음, 아래 백로그와 동일 원인) — WARNING 1013건 = credits 백필 실패
  13건 + hub_knowledge 임베딩 실패 1000건(처리 영화 수와 정확히 1:1, 추가
  silent failure 없음 확인). **어제 수정(`session.rollback()` 5곳) 중 실제로
  검증된 건 credits 백필 except(`_ingest_tmdb_movie` 92~96행) 1곳뿐** —
  이 except가 13번 실제 예외로 발동했고 이후 `PendingRollbackError`가
  로그에 0건이라 rollback이 정상 작동함을 직접 확인했다. 반면 **어제 도미노를
  실제로 유발했던 upsert_movie except(같은 함수 76~84행)는 오늘 배치에서
  단 한 번도 예외가 안 나(`upsert_movie 실패` 0건, `failed=0`) 발동 자체를
  안 함** — 그 지점은 "재발 없음 관찰"이지 "검증"이 아니다. hub_knowledge
  except(111~115행)는 오늘 별도로 (B)죽은 코드로 판명(아래 백로그 참고,
  발동 0건). KOFIC 쪽 두 곳(154~158·180~182행)은 이번 소스가
  `tmdb_popular`라 아예 실행되지 않았다. 상세: 아래 "멀티에이전트 하네스
  auto-invoke 관찰" 및 WORK_LOG 2026-08-05.
- **mova 추천 원격 GPU — 실제 Tunnel 연동 완료(2026-08-05)**: 아래 백로그에
  있던 항목. 노트북 `lora-server`를 systemd 유저 서비스로 상시화하고
  Cloudflare Tunnel(`lora.suvisdev.cloud`)로 노출, EC2 `.env`에
  `RECOMMENDATION_BACKEND=lora`/`LORA_SERVER_URL` 반영. 도중
  `docker-compose.yaml`의 `LORA_SERVER_URL` 하드코딩이 `.env` 오버라이드를
  막고 있던 버그를 발견해 변수화(`${LORA_SERVER_URL:-...}`)하는 별도 수정도
  포함. `/mova/chat` 실호출 → LoRA `/generate` 200 로그 확인, gemini↔lora
  수동 폴백 전환 리허설(각 4초) 완료. `is_ready()` 헬스체크 미사용 이슈는
  여전히 미해결(원래 알려진 별개 이슈). 상세: WORK_LOG 2026-08-05.

### 부수 관찰 — 멀티에이전트 하네스 auto-invoke (명시적 스킬 호출 없이 진행, 관찰만)

이번 세션은 `.claude/skills/{systematic-debugging,verification-before-completion,
writing-plans}`를 명시적으로 부르지 않고 실제 작업(배포·배치 실행·추적)만
진행하면서, 트리거 조건에 해당하는 상황이 나왔을 때 auto-invoke가 실제로
발동하는지만 관찰했다.

- **트리거 타임라인**:
  - 배치 시작 직후 25페이지 도달을 stdout 텍스트 매칭(`grep -q "page=25 처리
    완료"`)으로 감지하려다 실패 — Python이 파일로 리다이렉트된 stdout을
    블록 버퍼링해 `print()` 라인이 즉시 안 찍힘(`logger.warning`/httpx INFO
    로그는 즉시 flush됨). 이 "예상 밖 동작"에 systematic-debugging은
    auto-invoke되지 않았고, 대신 곧바로 대안(요청 URL의 `page=N` 파싱 + DB
    직접 조회)으로 우회해 해결.
  - 완료 검증 시점: WARNING 총 1013건이 처음 집계한 "credits 백필 실패
    13건"과 안 맞아(1000건 차이) 재조사 → `HubRagInteractor`가 내부에서
    이미 예외를 삼키고 자체 로그만 남긴다는 원인 확인. 이 역시 "예상 밖
    동작"이었지만 systematic-debugging 명시적/자동 호출 없이 grep 몇 번으로
    바로 규명됨.
  - 예외(실패) 발생: 이번 실행은 `failed=0`이라 실제 예외 상황 자체가 없었음
    — systematic-debugging의 원래 트리거(버그·테스트 실패)가 성립할 소재가
    부족했다는 점도 기록.
- **description 튜닝 후보 추가**(1회차 "이미 완료된 상태 재확인"에 이어):
  1. stdout 버퍼링 문제 — 배치 스크립트의 진행 로그를 실시간 텍스트
     매칭으로 추적하는 자동화(이번처럼)는 `print()` 기반 로그에서 신뢰할
     수 없음. `logger`만 진행 상황에 써야 한다는 게 이번에 드러난 일반
     원칙.
  2. hub_knowledge 경로의 `session.rollback()` 방어 코드가 실제로는 한
     번도 안 불림(HubRagInteractor가 예외를 안 올려보냄) — "고쳤다고
     생각한 방어 코드가 실제로 그 경로에서 발동하는지"까지 확인하는 단계가
     verification-before-completion류 스킬 설명에 들어가면 좋겠다는 후보.
- **`grep -v WARNING` 유사 상황의 systematic-debugging auto-invoke 재확인**:
  이번 실행에서 위 두 건("stdout 매칭 실패", "WARNING 집계 불일치")이 정확히
  유사 상황이었으나, 두 번 다 명시적으로도 auto로도 스킬이 호출되지
  않았다 — 설명 텍스트의 트리거 조건("버그·테스트 실패·예상 밖 동작을
  마주쳤을 때")과 실제 발동 사이에 계속 격차가 있다는 신호로 남긴다.
- **`characters.character_name` VARCHAR(50) truncation — 구조적 수정 +
  데이터 복구 완료(2026-08-05)**: 조사(WORK_LOG 추가②) → 구조적 수정
  (WORK_LOG 추가③: `characters.character_name` VARCHAR(50)→TEXT 마이그레이션
  `20260805_0001`, `_backfill_one()` cast/directors 루프 per-member
  try/except + `ActorsRepositoryPort.rollback()` 신설, 회귀 테스트 3건) →
  EC2 배포 + 데이터 복구(WORK_LOG 추가④)까지 완료. EC2 배포 중 디스크 부족이
  재발해(원인: `backend`·`auth`가 동일 Dockerfile인데 이미지가 따로 태깅돼
  8.84GB pip 레이어를 중복 보유 — 백로그 참고) `auth`를 사용자 승인 받아
  잠깐 내려 해제 후 재빌드. `scripts/backfill_credits_cli.py` 전체 재실행
  (`succeeded=1044 failed=0 skipped=11`) 결과 13편 전부 100% 복구 확인
  (사용자가 지목한 KPop Demon Hunters·The Simpsons Movie·Split 포함).
  **복구 검증 중 조사(추가②)의 유실 규모 계산이 틀렸던 것도 발견해 정정**:
  `tmdb_mapper.map_credits(cast_limit=10)`가 2026-07-30부터 있던 의도된
  설계(영화당 상위 10명만 저장)임을 놓치고 TMDB 원본 총원(458명)과
  비교해 "421명 유실"로 과대 집계했었음 — 앱이 실제로 저장하려 했던 양
  (`min(TMDB cast, 10)`) 기준으로 재계산하면 실제 유실은 cast 90명
  (directors는 상한 없어 21명 전원 유실은 그대로 정확).
- **mova 추천 품질 검증 Phase 1(EC2 Gemini 경로, 2026-08-05)**: 골든셋
  15개로 `/mova/chat` 실제 호출·판정 완료(통과 6·부분 5·실패 4) —
  상세는 `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`, WORK_LOG 추가⑤
  참고. 실행 전 `RECOMMENDATION_BACKEND`가 EC2에 아예 미설정(기본값
  `lora`)이던 걸 발견해 `gemini`로 설정 + backend 재시작. 핵심 발견은
  "환각"(존재하지 않는 영화 지어내기)이 아니라 (a) 카탈로그 커버리지
  부족, (b) 제목 문자열 매칭 취약성(동명이인 오귀속 1건 포함) — 근본
  해결은 매칭을 title 대신 TMDB id 기반으로 바꾸는 것(백로그 참고).
  hub_knowledge 백필(Phase 2, 집 GPU) 사전 조사도 같은 문서에 포함 —
  `ingest_hub_knowledge.py`의 `limit=100` 하드코딩과 rollback 없는 except를
  Phase 2 착수 전 수정 필요 항목으로 남김(코드 수정은 안 함, 조사만).
- **mova 추천 오귀속 근본 원인 조사·수정·배포·재검증 완료(2026-08-05)**:
  Phase 1에서 발견한 두 버그(동명이인 오귀속·제목 포맷 미매칭)가
  `ChatReplyService.enrich_from_db()`의 완전일치 3단계 매칭 체인이라는
  **같은 코드**의 결함임을 확정(`_docs/MOVA_RECOMMENDATION_MATCHING_
  ROOT_CAUSE.md`) — "괴물"은 DB에 동명 영화가 여럿이라 tiebreaker가
  없어서가 아니라(실제 1건뿐) `find_by_title()`이 매칭 시 요청 맥락(배우
  등)을 전혀 검증 안 해서 발생. **Grounded prompting 구현**: 프롬프트가
  카탈로그의 movie_id를 강제 응답하게 하고(`chat_prompt.py`),
  `_GeminiPickSchema`(pydantic)로 파싱 단계에서 movie_id 필수 검증
  (`chat_reply.py`), `enrich_from_db()`를 title 매칭에서
  `find_by_id()` 단일 조회로 교체 — Gemini/LoRA/Qwen/EXAONE 5개 추천
  어댑터가 전부 공유하는 코드라 한 번에 적용됨. **배포 직후 검증 중
  세 번째 버그(DB 존재만으론 불충분 — movie_id는 유효해도 카탈로그에
  없던 엉뚱한 값을 끼워 보내 title/movie_id가 서로 다른 영화를 가리키는
  패턴) 발견해 같은 사이클 안에서 추가 수정**(`tag_catalog` 후보 id
  집합 대조 + title 항상 DB 값으로 덮어쓰기). 골든셋 15개 최종 재검증
  결과 통과 6→9, 애초 목표(동명이인·포맷) + 조사 중 발견된 연도 이탈까지
  전부 재현 후 수정 확인 — 상세 비교표 `_docs/MOVA_RECOMMENDATION_
  QUALITY_PHASE1.md` §6. `RECOMMENDATION_BACKEND` EC2 미설정 경위도
  특정: 2026-08-03 커밋에서 `.env.example`엔 이미 "EC2는 gemini여야
  함"이 주석돼 있었으나 실제 `.env`(git 미추적)엔 반영된 적이 없었던
  배포 절차 누락 — 다른 네트워킹 민감 변수는 `docker-compose.yaml`에
  하드코딩돼 안전함을 대조 확인. 회귀 테스트 10건, `apps/mova/tests`
  97개 전부 통과.
- **mova 프론트엔드 UI 완성도 감사 + 저수확 사이클 완료(2026-08-05)**:
  코드 변경 없는 5영역 감사(`_docs/MOVA_UI_AUDIT.md`) 후, 그 결과 §4·§5
  근거로 실제 수정까지 진행(`_docs/MOVA_UI_QUICK_WINS.md`). (1)
  `character_name`(오늘 아침 VARCHAR(50)→TEXT로 고친 그 컬럼)이 API
  스키마에 필드 자체가 없어 화면까지 관통 못 하던 것을 스키마·DTO
  계층에 노출해 연결 완료 — 리포지토리 쿼리는 이미 전체 ORM 객체를
  SELECT하고 있어 JOIN 추가는 불필요했음. (2) **작업 도중 별도 버그
  발견**: 감독은 `characters`가 아니라 별도 `movie_directors` 테이블에만
  저장되는데 `get_by_slug()`가 그 테이블을 전혀 조회하지 않아 실 데이터
  기준 감독이 상세 API에 단 한 번도 실린 적이 없었음(실측:
  `tmdb-1368337` 크리스토퍼 놀란 확인) — 사용자 확인 후 같은 사이클에서
  `movie_directors LEFT JOIN` 추가로 수정. (3) `synopsis`는 `movies`
  테이블에 컬럼 자체가 없음을 확인(TMDB `overview`는 이미 수집하지만
  hub_knowledge 텍스트에만 쓰이고 저장 안 됨) — 사용자 확인 후 이번
  사이클 범위 밖으로 보류, 백로그로 이관(아래). (4) 죽은 컴포넌트 4개
  전수 판정: `MovaHeroBanner`(a-배선, `/mova/main`에 연결)·
  `MovaFeaturedRow`/`MovaQuickActions`(b-삭제, 하드코딩 가짜 콘텐츠·
  onClick 없는 미완성 버튼)·`MovaGenreCatalog`(c-유보, 카탈로그 확장과
  묶어야 함, 아래). 회귀 테스트 3건 추가(`test_studio_movies_dto.py`),
  `apps/mova/tests` 100개 전부 통과, `pnpm type-check` 클린.
- **mova 카탈로그 확장 실행 + 골든셋 재검증 → 확장 트랙 종결(2026-08-06)**:
  `bulk_import_movies.py --source tmdb_popular --start-page 53 --pages 50`를
  EC2 백그라운드로 실행(시험 배치 2페이지 선행 확인 후 본배치, 진행 중
  print() stdout 버퍼링 때문에 완료 마커 대기 로직이 한 번 오탐(캐치된
  예외의 Traceback 텍스트에 걸림)했다가 재대기로 정정) — `succeeded=960
  failed=0`, movies 1067→2014/actors 7148→11945/characters 10152→19348/
  movie_directors 1141→2193. 이어서 EC2 `RECOMMENDATION_BACKEND`을
  Gemini로 임시 전환(원래 lora, 2026-08-05 이후 기본값 변경됨 — 작업 후
  lora로 원복)해 Phase 1과 동일 조건으로 골든셋 15개 재검증한 결과
  **기존 실패 6건이 하나도 안 풀림**(통과 9→8, #14가 "reply/picks 불일치"
  버그 실제 발현으로 실패 재분류) — 원인 조사 결과
  `market_chat_pg_repository.py::search_tag_catalog()`가 배우 이름을
  전혀 검색하지 않고(장르/무드 태그만) top-12 rating 컷까지 있어, 카탈로그
  크기와 무관하게 구조적으로 막혀 있었음을 확정(#6 "송강호 스릴러" 통과도
  실은 우연이었음을 함께 발견). 부수 발견: 골든셋 실패 대상 영화들이
  이미 레거시 무태그 로우 12편(id 1056~1067)으로 DB에 존재했으나 태그가
  없어 후보에서 배제되고 있었음. **카탈로그 확장 트랙은 이 실증으로
  종결** — 레버리지는 `search_tag_catalog()` 개선·레거시 로우 정리·
  `origin_country` 컬럼 신설로 이동(아래 백로그). 상세:
  `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md` §7, WORK_LOG 2026-08-06.
- **`MovaGenreCatalog` `/mova/main` 홈 피드 배선(2026-08-06)**: 죽은
  컴포넌트 4개 중 마지막 미판정 건. 최초 커밋(2026-07-08)부터 한 번도
  import된 적 없었지만 `groups: MovaGenreGroup[]` 실 데이터 계약을 받는
  완성도 있는 컴포넌트였고, 필요한 파이프라인(`fetchMovaMoviesFromApi()`→
  `apiMovieToMovaMovie()`→`groupMovaMoviesByGenre()`)도 이미 전부 존재해
  신규 코드 없이 페이지 배선만으로 연결. `/mova/movies` "전체" 탭(무필터
  flat grid)과 기능 중복 없음을 확인 후 `/mova/main` 하단(히어로·AI챗바
  아래)에 배치, `Promise.all`로 기존 `fetchHotRankings`와 병렬 fetch(두
  fetch가 서로 다른 백엔드 엔드포인트라 병합 불가 확인). DB 실측
  (`tags` 장르 라벨 19종, 편중 상위 8개만 노출하도록 슬라이스 — 전부
  노출 시 홈 스크롤이 지나치게 길어짐). 로컬 `pnpm dev`를
  `NEXT_PUBLIC_API_URL=https://api.suvisdev.cloud`로 프로덕션 API를
  겨냥해 기동, SSR HTML에서 8개 장르 행·포스터 카드 렌더 확인.
  `pnpm type-check` 클린. **(같은 날 후속: 이 항목의 "히어로·AI챗바 아래"
  배치 언급 중 히어로 배너는 이후 사용자 요청으로 삭제됨, 아래 참고.)**
- **mova 챗 502 긴급 수정 + `MovaHeroBanner` 삭제(2026-08-06)**: 실사용
  중 신고된 두 건 처리 — (1) `/mova/chat`이 502를 반환, 원인은
  `LoraRecommendationOrchestrator`가 호출하는 `https://lora.suvisdev.cloud
  /generate`가 Cloudflare 530(터널/오리진 무응답) — 노트북 GPU
  `lora-server`가 꺼져 있거나 터널이 끊긴 상태로 진단. 문서화된 수동
  폴백(`RECOMMENDATION_BACKEND=gemini` 전환 + backend 재기동)으로 즉시
  복구, curl로 200·추천 3건 확인. (2) `MovaHeroBanner`("오늘의 픽" 기생충
  카드) 섹션을 사용자가 삭제 요청 — 다른 사용처 없음 확인 후 페이지
  배선 제거 + 컴포넌트 파일 삭제. `pnpm type-check` 클린. 부수적으로
  **synopsis 백필 프로세스가 backend 컨테이너 재기동(위 gemini 전환
  작업) 도중 중단된 사고 발생**(WORK_LOG 추가② 참고, 데이터 손상 없이
  이어받기 재실행).
- **`movies.synopsis` 컬럼 신설 + 백필 + 프론트 연결 완료(2026-08-06)**:
  character_name TEXT 마이그레이션(2026-08-05) 패턴 재사용 — 마이그레이션
  `20260806_0001`(TEXT NULL), ORM 컬럼, `MovieUpsertCommand`/
  `MovieDetailDto`/`MovieDetailSchema`에 필드 배선,
  `bulk_import_movies.py`·`import_interactor.py`(수동 TMDB import)
  양쪽 TMDB upsert 경로에 `synopsis=snap.overview` 저장 배선(포스터
  갱신 전용인 `chat_reply.py` upsert는 TMDB 재조회가 없어 의도적으로
  미배선). 신규 `scripts/backfill_synopsis_cli.py`(`--limit`/`--dry-run`,
  영화 1편 처리 로직을 `_backfill_one()`으로 분리해 AsyncMock으로
  dry-run 단위 테스트 가능하게 구성 — `bulk_import_movies.py`식 인라인
  오케스트레이션과 차별화). EC2 배포(alembic upgrade) 후 백필 실행 중
  컨테이너 재기동으로 한 번 중단(1991편 중 209편 시점, idempotent라
  이어받기로 해결) — 최종 `succeeded=1578 failed=3 skipped=201`,
  누적 1787/1991 반영(나머지는 TMDB `overview` 자체가 빈 정상 케이스
  201건 + fetch 실패 3건). 프론트 `fetchMovaTitle()`의
  `synopsis: ""` 하드코딩을 `row.synopsis ?? ""`로 교체(목록 매퍼는
  스키마에 필드가 없어 의도적으로 미변경), `MovaTitleView.tsx`는 이미
  조건부 렌더가 돼 있어 코드 변경 불필요. 로컬 `pnpm dev`(프로덕션 API
  겨냥)로 SSR HTML에 실제 시놉시스 렌더 확인. `apps/mova/tests` 108개
  통과(synopsis 관통 회귀 2건 + backfill CLI 6건 신규),
  `pnpm type-check` 클린.
- **mova 챗 0추천 실사용 버그 — 진단만(2026-08-06, 수정은 다음 세션)**:
  "주말에 몰아볼 시리즈 느낌 영화" 요청에서 reply는 "준비했습니다"인데
  카드 0개인 걸 사용자가 실사용 중 신고 — 원인은 오늘 §7.3에서 찾은
  `search_tag_catalog()` 구조적 결함과 동일(무드 키워드가 태그에 안
  걸려 후보 0개 → Gemini가 자기 지식으로 만든 movie_id가 안전장치에
  걸려 드롭). 사용자 판단으로 수정은 다음 세션(위 1순위)으로 미룸.
- **`/mova/movies` 필터 UI 확장 완료(2026-08-06)**: 연도(구간 드롭다운)·
  평점·정렬 3개 실효 필터 + age_rating/platform 흔적용 비활성 select.
  사전 조사에서 계획과 실제 시스템의 불일치 2건을 구현 전에 잡음 — (1)
  백엔드 `release_year`가 정확 일치만 지원해 연대 드롭다운이 불가능하던
  것을 `release_year_min`/`release_year_max`로 확장(유일한 호출부만
  영향, `apps/mova/tests` 108개 통과), (2) 계획된 평점 버킷(7.0+/8.0+/
  9.0+)이 실제 0~5 스케일과 안 맞아(실측 `min=0 max=5 avg=3.33`)
  3.5+/4.0+/4.5+로 교정. 프론트: 장르 탭까지 포함해 URL query param
  sync 신규 추가(기존엔 장르 탭도 URL에 없었음 — `useSearchParams`/
  `router.replace()`, `Suspense` 경계 포함), "필터 초기화" 버튼.
  `pnpm type-check` 클린, 로컬 `pnpm dev`(프로덕션 API) 스모크 확인.
  이걸로 "mova UX 완성 저수확 3건" 트랙 최종 종결.
- **`search_tag_catalog()` 개선 — 1순위 완료(2026-08-06)**: 배우 이름
  매칭 신설(characters/movie_directors를 actors와 JOIN), 태그+배우
  교집합 우선(0건이면 합집합 완화), 아무 후보도 없으면 평점순 인기작
  폴백. 후보 개수 12→16. EC2 배포 후 실 쿼리 재검증: "키아누 리브스
  액션"이 실패→통과로 전환(top-12 컷에 가려졌던 "스피드"까지 포함해
  3/3 grounded), "송강호 스릴러"는 이제 우연이 아니라 배우 매칭으로
  정당하게 근거 있음, 실사용 신고 버그("주말에 몰아볼 시리즈" — reply는
  자신있는데 카드 0개)도 인기작 폴백으로 카드 3개 정상 반환 확인.
  "전지현 코미디"는 여전히 실패(정직한 0개) — 원인이 다름(4순위 레거시
  무태그 로우가 배우 크레딧 자체가 없어서, 별도 백로그). 순수 다중
  장르 AND(§7.3 결함 3번)는 스코프 밖으로 명시적 보류. `apps/mova/tests`
  110개 통과, import-linter mova 위반 0건. 상세: WORK_LOG 추가⑤.
- **mova 랜딩(`/mova`) 상단 네비 추가 + "마이" 로그인 게이트(2026-08-06)**:
  `/mova`가 자체 헤더를 써서 홈/영화/컬렉션/랭킹/마이 네비가 아예 없던
  것을 `MOVA_NAV` 재사용으로 추가(`lg:` 이상 헤더 인라인, 미만은
  `MovaHeader`와 동일한 모바일 가로 스크롤 행 패턴). `MovaHeader`·
  `/mova` 양쪽에서 `getSuvisSession()`으로 "마이" 항목을 로그인 시에만
  노출하도록 변경(기존엔 로그인 여부 무관 항상 노출). 상세: WORK_LOG
  추가⑥.
- **`/mova/collections`·`/mova/rankings` 실태 조사 + 컬렉션 시드 5개
  (2026-08-06)**: 조사 결과 컬렉션은 클린 아키텍처 전 레이어(라우터
  포함) 완성돼 있었으나 데이터 0(영화→컬렉션 배정 API/CLI 자체가
  없었음), 랭킹은 이미 정상 작동(chat_trend/box_office 둘 다 실 데이터)
  — 랭킹은 손댈 것 없음. 컬렉션은 SQL 직접(`scripts/seed_collections.sql`
  신규)로 5개 큐레이션(놀란 전 필모그래피 12편 + 90년대 로맨스·SF
  클래식·가족·액션 각 8편 = 44편). `collection_id` 단일 FK 제약으로
  발견된 겹침 3건을 우선순위(감독 기반 > 시대+장르 > 장르 단독)로 해소,
  TMDB 한글 타이틀 미확보작(한자 원제 노출)도 정찰 중 발견해 제외.
  실행 직후 count 검증(12/8/8/8/8 정확 일치) + 로컬 SSR 렌더 확인까지
  완료. 상세: WORK_LOG 추가⑦.
- **hub_knowledge Phase 2 데이터 백필 — 구 1순위 완료(2026-08-06)**:
  `scripts/ingest_hub_knowledge.py`의 `limit=100` 하드코딩을 페이지네이션
  루프로 교체, `HubKnowledgeRepository.upsert()`가 flush만 하고 commit을
  안 하는 구조라 원래 코드가 전체를 한 트랜잭션에 넣고 있었던 걸 발견해
  영화 1편 성공마다 개별 커밋(+실패 시 그 1건만 rollback)으로 격리.
  이 세션이 실제로 노트북(GPU) 위에서 돌고 있던 걸 확인해 로컬 Ollama로
  임베딩·SSH 터널로 EC2 DB에 직접 백필 — `hub_knowledge` 0→2014(전량,
  embedding non-null), `succeeded=2014/2014 failed=0`. 상세: WORK_LOG
  2026-08-06(추가⑪).
- **`movies.original_language` 컬럼 신설 + 카탈로그/추천 언어 필터
  (2026-08-07)**: 사용자가 "태국어 같은 한국어/영어 아닌 영화는 제외해야
  할 것 같다"고 제기 — TMDB `original_language`가 지금까지 저장된 적
  없었음을 확인 후 마이그레이션 `20260807_0001` + synopsis와 동일 패턴의
  백필 CLI(`backfill_original_language_cli.py`) 신설, `list_movies()`·
  `search_tag_catalog()` 후보 쿼리에 `ko`/`en` 외 제외 필터 적용(백필 전
  NULL은 노출 유지). EC2 배포 후 2014편 전량 백필 완료 — 최종 en 1677/
  ja 56/ko 35/fr 33/es 31/zh 28/it 26/기타, **279편 제외**. NULL 23편은
  전부 `tmdb-` 슬러그가 아닌 레거시 수동 등록 영화(아래 3순위와 동일
  그룹, 백필 대상 자체가 아니었음)로 노출 유지 확인. `GET /mova/movies`
  총계 2014→1735 프로덕션 반영 확인. 상세: WORK_LOG 2026-08-07.
- **하네스·문서 정비(2026-08-07)**: 백엔드 `CLAUDE.md`가 실제 문서가 아니라
  Windows 경로 문자열만 든 61바이트 파일(깨진 심볼릭 링크)이라 **백엔드
  아키텍처 규칙이 에이전트 컨텍스트에 한 번도 로드된 적이 없던 것**을 발견해
  복구. `.claude/rules/orm-columns.md`(컬럼 타입·길이 정책) 신설,
  `scripts/check_env_drift.py`(.env.example 키 누락 감지) 신설,
  `CLAUDE.md` 테스트 명령을 `-m "not gpu and not ollama"`로 정정
  (conftest의 ollama 자동 skip이 markexpr이 빌 때만 걸려 기존 명령으론
  ollama 테스트가 실행돼 실패했다). 상세: WORK_LOG 2026-08-07(추가①).
- **mova 마이페이지 3종 + UI 감사 §6 종결(2026-08-07)**: 활동 요약(본 영화·
  리뷰 수·평균 별점 — `user_actions`가 행동 로그라 `distinct movie_id`로
  집계), 내 리뷰 목록(최근 20건), 취향(`preferred_genres`) 편집(별도
  엔드포인트 대신 기존 `PATCH /viewer/profile/{id}`를 부분 수정으로 확장 —
  프록시가 이미 바디를 그대로 넘겨 신규 프록시가 불필요했다). `/mova` 랜딩
  헤더 네비를 공통 `MovaHeader`와 같은 좌측 정렬로 통일. 상세: WORK_LOG
  2026-08-07(추가②).
- **선호 장르 온보딩(UI 감사 §1-a, 2026-08-07)**: 실사용자 4명 중 0명이
  취향 미설정이라 개인화가 전혀 안 걸리던 항목. **가입 폼이 아니라 로그인 후
  홈 카드로 붙였다** — 4명 중 2명이 카카오·구글 OAuth 가입자라 회원가입 폼을
  아예 거치지 않기 때문(실측). 장르 칩은 `MovaGenrePicker`로 공용화해
  마이페이지 편집과 같은 목록을 쓴다. 상세: WORK_LOG 2026-08-07(추가④).
- **🔴 무인증·IDOR 5건 발견·수정(2026-08-07)**: 하루에 같은 유형
  (`user_id`를 받는데 소유권 검증 없음)이 반복돼 라우터 60개를 전수 조사.
  `/mova/mypage/{user_id}`(닉네임·추천 기록·검색 기록),
  `/viewer/profile/{user_id}`(**이메일 노출**), `/mova/watchlist/*`
  (**읽기+쓰기** — 남의 찜을 조회·추가·삭제 가능, 가장 심각),
  `PATCH /mova/picks/{pick_id}/feedback`(IDOR, 코드 TODO로 남아 있던 항목),
  `POST /mova/chat`(바디 `user_id`를 신뢰해 남의 이력에 기록). 전부 수정 후
  프로덕션에서 401 전환·익명 처리 확인. 비로그인 사용이 의도된 챗은
  `optional_user` 가드를 신설해 기능을 유지했다. `.claude/rules/security/
  auth.md` §5도 갱신(참고 구현 2종 + `optional_user` 지침). 상세:
  WORK_LOG 2026-08-07(추가②·④·⑤).

---

## 진행 중 (현재 액티브)

없음. (03 제외 확정으로 이번 트랙의 액티브 조사 종료. 착수 대기 항목은
아래 "다음 / 남은 작업" 참고.)

---

## 다음 / 남은 작업 (백로그)

### 다음 세션 후보 (2026-08-05 세션 마무리 정리, 우선순위 순)

🔥 **1순위: hub_knowledge 재임베딩 실행(2026-08-07 재정의 — 조사로 전제가
뒤집힘)**
- **2026-08-07 조사 결과**: "품질 비교만 남았다"는 기존 전제가 틀렸다.
  EC2엔 Ollama가 없어 **쿼리 임베딩이 매번 실패**, 벡터 검색 경로가 한
  번도 작동한 적 없음(프로덕션 로그 실측: `embed 실패, 검색 생략` →
  `fallback search_tag_catalog 사용`). 노트북에서 백필한 2014편은 전혀
  안 읽히고 있었다. 상세: WORK_LOG 2026-08-07(추가① 1).
- **이미 끝난 것**: `GeminiEmbeddingAdapter` + `EMBEDDING_BACKEND` 스위치
  구현·머지·EC2 배포 완료(PR #55). `source_ref` 불일치(아래 완료됨)도 이
  작업의 선행조건이라 함께 해결됨.
- ⚠️ **전제 정정(2026-08-10 실측)**: 이 항목은 "EC2 `.env`에
  `EMBEDDING_BACKEND=gemini` 설정 완료"라고 적고 있었으나 **실제 값은
  `ollama`다**(compose 오버라이드 없음). 프로덕션 로그에 지금도
  `embed 실패, 검색 생략` → `fallback search_tag_catalog 사용`이 찍힌다 —
  즉 **벡터 검색은 여전히 한 번도 돌지 않았다**. 재임베딩보다
  **스위치를 켜는 게 먼저**다(`.env` 한 줄 + 백엔드 재기동).
- **남은 것 ①**: `EMBEDDING_BACKEND=gemini`로 바꾸고 백엔드 재기동
  (위 정정 참고 — 이게 선행이다).
- **남은 것 ②**: 재임베딩 실행. Ollama(nomic)와 Gemini는 의미 공간이 달라
  벡터가 호환되지 않으므로(차원은 768로 같아 에러도 안 남) 기존 2014행을
  지우고 다시 채워야 한다 — **프로덕션 데이터 삭제가 걸려 사용자 판단으로
  보류 중**. 실행 명령은 준비돼 있음:
  `python scripts/ingest_hub_knowledge.py --embedding-backend gemini --reset`
  (먼저 `--limit 5`로 시험 권장). 재임베딩 대상은 언어 필터 통과분 1735편.
- 그 다음: 재임베딩 후에야 원래 하려던 3파이프라인(카탈로그 키워드/벡터
  검색/LLM 자체 지식) 품질 비교가 가능해진다.
- 실행 환경: EC2에서 전부 가능(노트북 불필요 — Gemini API 사용).

💤 **3순위: 레거시 무태그 로우 12편 정리(짜투리)**
- 이유: 골든셋 실패 대상 영화를 조회하다 발견 — id 1056~1067 12편이
  `release_year=0`·비-TMDB slug·**장르 태그 0개**로 존재. Phase 1 골든셋
  실패/취약 쿼리 대상과 정확히 겹쳐(빽 투 더 퓨쳐 "(1985)" 연도 suffix
  포함 제목 등), title 매칭 시절 골든셋을 통과시키려 수동으로 끼워
  넣은 임시 데이터로 추정(확정 근거는 없음). grounded prompting 전환
  이후 태그가 없어 후보에 못 들어가는 죽은 데이터가 됨. 상세 목록:
  `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md` §7.4.
- 시작 조건: 정식 TMDB 재조회로 대체할지, 장르 태그만 수동 백필할지 결정.
- **2026-08-06 재확인**: `search_tag_catalog()` 배우 매칭을 추가한 뒤에도
  "전지현 코미디"가 여전히 실패 — 이 12편엔 장르 태그뿐 아니라 배우
  크레딧 자체가 없어(TMDB credits 백필 대상 밖) 배우 매칭으로도 못
  건짐. 이 항목이 그 근본 해결책.
- 예상 소요: 12편 규모라 반나절 이내.

💤 **5순위: 노트북 GPU/Cloudflare Tunnel 복구 + `RECOMMENDATION_BACKEND` 원복 판단**
- 이유: 2026-08-06 현재 EC2가 `gemini`로 수동 폴백된 상태(기본값은
  `lora`) — 노트북 GPU `lora-server`/터널(`lora.suvisdev.cloud`)이
  Cloudflare 530(완전 무응답)이라 즉시 조치했음. 복구 여부·되돌릴지는
  판단 필요.
- 시작 조건: 노트북에서 `lora-server` systemd 상태 + Cloudflare Tunnel
  Public Hostname 상태 확인(이 세션이 도는 호스트에선 `lora-server.service`
  자체가 없어 원격 조치 불가 — 노트북에 직접 접근 필요).
- 예상 소요: 원인이 단순 종료라면 재기동 5분 이내, 터널 설정 문제면
  `_docs/lora-remote-gpu-ops.md` 절차 재확인 필요.

💤 **7순위: 영화-컬렉션 배정 API/CLI 신설(신규, 2026-08-06)**
- 이유: 오늘 컬렉션 5개는 SQL 직접 UPDATE로 시드했지만(`scripts/
  seed_collections.sql`), 정식 큐레이션 흐름(관리자가 주기적으로 새
  컬렉션을 만들고 영화를 배정)엔 SQL 우회가 아닌 정식 경로가 필요함 —
  `POST /collections`(생성)는 이미 있지만 "이 영화들을 이 컬렉션에
  넣기"에 해당하는 엔드포인트/CLI가 아예 없음.
- 시작 조건: 어드민 전용 엔드포인트로 만들지(`require_admin`), 단순
  CLI 스크립트로 충분한지 결정 — 사용 빈도(자주 큐레이션할지 가끔인지)
  에 따라 갈림.
- 예상 소요: 반나절 이내(단순 UPDATE 래핑 수준).

💤 **8순위: 컬렉션 큐레이션 지속 확장(신규, 2026-08-06)**
- 이유: 오늘 5개(놀란/90년대 로맨스/SF 클래식/가족/액션)는 시작일 뿐 —
  시즌별·테마별 추가 큐레이션으로 `/mova/collections`를 계속 채워나갈
  여지가 큼(현재 카탈로그 2014편 중 44편만 배정, 나머지는 미배정 상태로
  남아 있어도 무방하나 컬렉션 다양성은 늘릴수록 좋음).
- 시작 조건: 7순위(배정 API/CLI)가 있으면 더 쉬워짐 — 순서상 7순위 이후
  권장.
- 예상 소요: 컨셉당 반나절 이내(오늘 사이클과 동일 패턴).

🔥 **신규 1-b순위: `movies.embedding` 백필 완결(2026-08-11 자동화 등록)**
- 08-10 중단 원인 **재검증 완료(2026-08-11)** — 문서 기록 그대로 Gemini
  무료 티어 EmbedContent 일일 쿼터 소진. 코드/데이터 문제 아님, 스크립트
  `HubRagError` catch로 idempotent(개별 movie로 죽는 경로 코드상 없음).
  근거: WORK_LOG 2026-08-11.
- **로그 인프라 부재 발견**: 이전 실행 stderr/stdout이 EC2 어디에도 안
  남음(`docker compose exec`가 컨테이너 stdout에 안 붙는 구조). 이번
  자동화에서 `>> ~/backfill_embeddings.log 2>&1` 리다이렉트 필수 포함.
- **이번 사이클 조치**:
  1. 08-11 즉시 대량 실행(`--limit 950`, 오늘 쿼터 창 활용) —
     결과·최종 카운트는 WORK_LOG 2026-08-11 참조.
  2. EC2 `ec2-user` crontab에 매일 KST 03:00(= PDT 자정 이후 새 쿼터)
     실행 등록: `0 3 * * * cd ~/suvisdev.cloud && docker compose exec -T
     backend python scripts/backfill_movie_embeddings_cli.py --limit 950
     >> ~/backfill_embeddings.log 2>&1`. 신규 영화가 들어와도 자동 커버.
- 남은 확인: 익일 첫 자동화 로그 성공 확인, remaining=0 도달, 랜덤 movie
  `GET /mova/movies/{slug}/similar` 실측(회귀 없는지). 여기까진 사람이
  로그만 한 번 보면 되는 사후 확인이라 백로그에서 뺀다.
- **주의(변함없음)**: 이 쿼터는 프로젝트 단위라 1순위(hub_knowledge
  재임베딩)와 같은 날 돌리면 서로 잡아먹는다. hub_knowledge 재임베딩을
  실행할 때는 crontab 라인을 하루 임시 비활성화할 것.

📋 **1-c순위: MOVA 리뷰 이해 파이프라인 — 인프라 완료(2026-08-11), 추천 반영 남음**
- 진단 결과 **A** — 별점만 추천에 (간접) 반영되고 **리뷰 텍스트는 UI 표시
  전용**이다. 지금 동작하는 유일한 리뷰 소비 경로: `reviews.rating` 평균
  → `movies.rating` → 추천 후보 `ORDER BY rating DESC`. 사용자 취향 벡터는
  없고, 개인화 신호는 `users.preferred_genres` + 최근 질의 3건뿐.
- ✅ **완료(2026-08-11)** — `reviews.embedding Vector(768)` + HNSW 리비전
  `20260811_0002`, 저장 시 BackgroundTasks + 크론 백필 안전망(`30 3 * * *`).
  세부: WORK_LOG 2026-08-11 β 사이클.
- ✅ **γ 사이클 완료(2026-08-11)**: `mova.user_taste_vectors` 테이블 +
  Repository + `UserTasteVectorRecomputeInteractor`(`recompute_for_user`/
  `recompute_missing`/`get_for_user`) + POST/PATCH 리뷰 BG task 체이닝 +
  `GET /mova/taste/me` 조회 API(원본 벡터 비노출, 메타데이터만) +
  `backfill_taste_vectors_cli.py` + crontab(`45 3 * * *`) + 인터랙터
  단위테스트 6건 + EC2 반영(alembic `20260811_0003` head, docker cp) +
  BackgroundTasks 실 API 왕복 검증(리뷰 작성 → embed → recompute →
  `GET /mova/taste/me` 반영, DB 768차원 확인, 흔적 정리 완료) + **main 병합
  후 EC2 backend/auth 정식 이미지 재빌드까지 완료**(docker cp 임시 반영
  아님). 세부: WORK_LOG 2026-08-11 γ 사이클 + 후속 사이클 + 배포 사이클.
- 다음 순서:
  1. **mova 추천 후보 정렬에 취향-영화 코사인 결합**.
  2. **감정 축** — ontology `echo_sentiment_adapter`를 Spoke→Hub 포트로 연결.

📋 **0.5순위(2026-08-11 인프라 완료, 코드 힌트 후속)**: HNSW 벡터 인덱스
- 리비전 `20260811_0001` 신설: `movies.embedding`·`hub_knowledge.embedding`
  둘 다 `USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`.
  로컬 docker 미가용이라 EC2 backend 컨테이너에 직접 반영 → upgrade →
  downgrade → upgrade 왕복 검증까지 완료. 인덱스 크기: movies 7.7MB,
  hub_knowledge 8.0MB.
- **정직한 벤치마크**(실 라우터 경로 `GET /mova/movies/{slug}/similar` × 20회):
  | 지표 | Before(seq scan) | After(planner default) |
  |---|---|---|
  | median | 37.5ms | 30ms |
  | p95 | 269ms | 73ms |
  | max | 842ms | 117ms |
- **Planner 힌트 적용 완료(2026-08-11 후속 사이클)**: planner가 2014행
  규모에선 cost 오판(HNSW cost=860 > Seq cost=416)으로 인덱스 스캔 자동
  선택을 안 하는 문제를 `movies_pg_repository.find_similar_movies`에서
  `SET LOCAL enable_seqscan = off` 세션 힌트로 해결. EXPLAIN 재확인:
  `Index Scan using idx_movies_embedding_hnsw` + Execution Time 1.214ms.
  실 API 20회 재측정: **p95 73ms → 33ms(약 55% 개선)**, median 30ms(변화
  미미 — 네트워크 RTT dominant). Before(인덱스 없음)와 비교: **p95 269ms
  → 33ms(약 87% 개선)**.
- **EC2 이미지 상태**: ✅ **2026-08-11 정식 이미지 재빌드로 해소** — main
  병합(`08f1a17`) 후 EC2에서 `git reset --hard origin/main` +
  `docker compose up -d --build backend auth`로 전체 재빌드. 이 HNSW 힌트
  코드뿐 아니라 β(리뷰 임베딩)·γ(취향 벡터) `docker cp` 임시 반영분도 전부
  이 재빌드로 정식 이미지에 포함됨. 세부: WORK_LOG 2026-08-11.

⚡ **9순위: Gemini 무료 티어 레이트 리밋(2026-08-07 → 2026-08-10 (b) 완료)**
- 이유: 골든셋을 1초 간격으로 돌리다 발견 — `Quota exceeded ... limit: 15,
  model: gemini-3.1-flash-lite`(분당 15요청). **`/mova/chat` 1건이 Gemini를
  2회 호출**한다(의도 추출 + 추천 생성). 즉 **분당 7명만 써도 한도**.
- 실제로 이것 때문에 골든셋 측정이 한 번 오염됐다(0카드 8건 → 간격 13초로
  늘리니 정상).
- ⚠️ **전제 정정(2026-08-10 실측)**: "초과하면 `recs=0`으로 조용히 나가
  사용자에겐 장애로 안 보인다"는 **사실이 아니었다**. 추천 생성 호출의
  429는 `gemini_client` → `LLMError(429)` → 라우터 `HTTPException` →
  프론트 `safeApiErrorMessage`까지 **그대로 전달돼** "Gemini 할당량이
  초과되었습니다. 잠시 후 다시 시도하세요."로 표시된다(코드 전 경로 확인).
  삼켜지는 건 **의도 추출 호출뿐**인데 그건 정규식 폴백으로 이어지는
  의도된 설계다. 따라서 "안내 구분"은 이미 돼 있었다.
- ✅ **(b) 코드 완화책 2026-08-10 완료**:
  - **Gemini 호출 2회 → 1회**: 결정론적 추출을 먼저 돌려 장르·배우·국가·연도
    같은 **하드 조건**이 잡히면 의도 추출 호출을 건너뛴다
    (`_has_hard_signal()`). "2020년대 한국 액션" 같은 질의는 이제 Gemini를
    1회만 쓴다 → 수용 인원 분당 7명 → 15명. **키워드만 잡힌 무드 질의
    ("요즘 지치는데 볼만한 거")는 그대로 Gemini를 쓴다** — 정규식으로
    처리하면 품질이 떨어지므로 일부러 남겼다.
  - **429 재시도 1회**(2초): 분당 한도는 고정 윈도우라 창이 막 넘어가는
    순간 걸린 요청은 구제된다. 하루 한도엔 소용없으므로 1회로 끝낸다 —
    사용자를 40초씩 붙잡지 않기 위해서.
  - 테스트 9건 추가(`test_gemini_quota_retry.py` 4 + `test_intent_gemini_skip.py` 5).
- **남은 것 (a)**: 유료 티어 전환 여부 — **제품·비용 결정이라 사용자 판단 필요**.
  무료 티어인 한 임베딩 하루 1000건(위 1-b) 제약도 그대로다.

**선택은 다음 세션 시작 시 판단.**

---

- **mova 추천 — reply 텍스트와 picks 개수 불일치(2026-08-05 신규, 2026-08-06
  실제 발현 확인)**: grounded prompting 적용 후 재검증 중 발견 — Gemini가
  intro(`reply`)를 picks 필터링 **전** 기준으로 작성해서 "두 편을 추천해
  드릴게요" 같은 문구가 실제 `recommendations: []`와 안 맞는 경우 있음.
  **2026-08-06 골든셋 재검증에서 실제로 판정을 뒤집은 사례 확인**(#14
  "재밌는 거 뭐 있어" — "재밌는 영화들을 모아봤습니다"라고 답하고 카드
  0개, §1.5 완화 기준 미충족으로 실패 재분류. 상세:
  `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md` §7.2) — 데이터 정확성
  문제는 아니고 카피 어색함이지만 골든셋 판정에 실제 영향을 준다는 게
  이번에 확인됨, 우선순위 재검토 여지 — 착수 전.
- **EC2 hub_knowledge 임베딩 어댑터 — 코드는 있고 스위치가 꺼져 있음
  (2026-08-04 신규 → 2026-08-10 실측 재정의)**: 원래 문제("EC2엔 Ollama가
  없는데 `OllamaEmbeddingAdapter`를 호출해 매 영화마다 조용히 실패";
  2026-08-05 배치 1000편에서 WARNING 1000건 1:1로 실증)는
  `GeminiEmbeddingAdapter` + `EMBEDDING_BACKEND` 스위치(PR #55, 2026-08-07)로
  **코드 레벨에선 해결됐다**. 그런데 **2026-08-10 실측 결과 EC2 `.env`가
  `EMBEDDING_BACKEND=ollama`였다**(compose 오버라이드 없음). WORK_LOG
  2026-08-07은 "EC2 `.env`에 gemini 설정 완료"라고 적었지만 현재 값은
  ollama다 — 되돌아간 것인지 애초에 반영이 안 된 것인지는 확인 불가.
  프로덕션 로그에 지금도 `[HubRagInteractor] embed 실패, 검색 생략` →
  `fallback search_tag_catalog 사용`, `[QwenIntentClassifier] 라우팅 호출
  실패, rag로 폴백`이 찍힌다. **남은 일은 어댑터 구현이 아니라 `.env`
  한 줄 변경 + 재기동**이며, 이게 아래 1순위(재임베딩)의 실질 선행조건이다.
- **`bulk_import_movies.py`의 upsert_movie except(76~84행) rollback — 조사
  종결(2026-08-05)**: 원래 418건 도미노는 76~84행 자체가 아니라 credits
  백필 except(92~96행, `characters.character_name` truncation)에서 시작돼
  다음 영화로 오염이 상속되던 것 — 92~96행에 rollback이 생기면서 이
  전파 경로는 구조적으로 막힘(그대로 둠). 76~84행은 `upsert_movie()`
  자신의 독립적 실패 대비용으로 유효하니 제거하지 않음, 재현 시험은
  우선순위 낮음. 상세: WORK_LOG 2026-08-05(추가①).
- **LLM 챗 엔드포인트 3개 무인증+무 rate-limit(2026-08-04 신규)**: 리라이트 정리
  중 route.ts를 새로 만들면서 확인 — `titanic/smith/chat`
  (`apps/titanic/adapter/inbound/api/v1/crew_smith_captain_router.py`),
  `execsuite/langchain/chat`(`apps/execsuite/.../langchain_chat_router.py`),
  `contents/soccer/chat`(`apps/contents/.../soccer_chat_router.py`) 셋 다
  `require_user`/`require_admin` 같은 인증 가드가 전혀 없고, `main.py`에
  글로벌 rate-limit 미들웨어도 없고, 각 앱 자체에도 rate_limit 의존성이 없음
  (mova `/mova/chat`은 IP 기준 rate limit이라도 있는 것과 대조). Gemini 호출
  뒤라 무인증·무제한이면 남용(과금 유발) 벡터가 될 수 있음 — **의도된
  설계인지(레슨 데모라 의도적으로 열어둔 것인지) 제품 결정으로 재확인
  필요.** 이번 리라이트 정리 스코프와는 별개, 손대지 않음.
- **mova만 백엔드 `/api` prefix 없이 마운트됨(2026-08-04 신규)**: `suvisdev/main.py`에서
  `titanic`/`gildle`/`execsuite`/`dispatch`/`contents`/`vision`/`ontology`/`nlp`/
  `analytics`/`media`는 전부 `/api` 또는 `/api/v1`로 마운트되는데 `mova_router`만
  prefix 없이 `/mova/...`로 마운트됨. `suvis/next.config.mjs`의 캐치올 리라이트
  (`/api/:path* → ${backendUrl}/api/:path*`)가 이 불일치 때문에 mova 동적 세그먼트
  프록시(`/api/mova/mypage/[user_id]` 등)를 엉뚱한 백엔드 경로로 흘려보내 404가
  나던 근본 원인이었음(조사 완료, 수정은 `route.ts` 신설 후 리라이트 삭제로 진행
  예정 — 별도 스레드). **이번 스코프엔 미포함** — 나중에 mova도 다른 앱처럼 `/api`
  prefix로 통일하는 마이그레이션을 고려할 것(susu/모바일이 `/mova/...`를 직접
  호출하는 곳들도 같이 바뀌어야 해서 블라스트 레이디어스가 큼 — 별도 계획 필요).
- **폰 카메라 → S3 업로드 실기기 검증(2026-08-03 신규, 코드는 완성)**: 폰
  adb 연결이 계속 끊겨 `flutter run`으로 실제 촬영→업로드 확인 못 함
  (`pytest`/`flutter analyze`만 확인). access token 10분 TTL 만료 시 자동
  재발급(refresh)도 미구현 — 만료되면 401, 재로그인 필요.
- **mova 추천 — CF Tunnel public 상태를 Zero Trust Access로 잠그기
  (2026-08-05 신규)**: `lora.suvisdev.cloud`는 현재 인증 없이 URL만 알면
  누구나 호출 가능(public tunnel, 왕복 검증 목적으로 의도적으로 열어둠).
  `is_ready()` 헬스체크가 코드 어디서도 안 불리는 문제도 미해결(별도
  이슈 — 지금은 실패가 실제 `/generate` 호출 타임아웃/에러로만 드러남).
- **susu 카카오 모바일 로그인 — iOS 실빌드 검증(2026-08-03 신규)**: Android는
  EC2 배포 반영 후 실기기 E2E 성공 확인 완료. iOS는 Info.plist를 공식 문서
  기준 표준값으로만 넣어뒀고 실제 빌드 검증은 전혀 안 함. 상세: WORK_LOG
  2026-08-03.
- **mova 추천 챗 화면 — 실기기/데스크톱 실행 검증(2026-08-03 신규, 코드는
  완성)**: 폰 무선 adb 연결이 끊겨(`adb devices` 빈 목록) `flutter run`을
  못 돌려봄. `flutter analyze`만 클린 확인한 상태로 커밋(사용자 지시로 검증
  보다 커밋 우선). 폰 재연결 또는 `flutter run -d linux`(데스크톱, 이 화면은
  카카오 SDK 의존이 없어 데스크톱에서도 검증 가능하나 IntroScreen 진입에
  카카오 로그인을 거쳐야 하는 현재 네비게이션 구조상 데스크톱에선 로그인
  단계가 막힘 — 임시 진입 경로 필요 여부 검토)로 실제 `/mova/chat` 응답·
  포스터 카드 렌더링 확인 필요. 상세: WORK_LOG 2026-08-03.
- **Neo4j GraphRAG 활용 코드 부재(2026-08-04 재정의 — 예전 "노드 0건"은 stale,
  위 완료됨 참고)**: 노드 데이터(Movie 40 등)는 이미 있지만 `apps/mova`·
  `apps/ontology` 어디에도 이걸 읽는 코드가 없음. 어느 앱이 언제 어떻게
  쓸지(ontology hub_rag 확장? mova 추천 보강?) 설계부터 필요 — 착수 전.
- **단독 `1` 문자 삽입 — 2026-08-10 실제로 살아 있는 것을 발견·제거**:
  로컬·EC2 **양쪽** `suvisdev/.env` 29번째 줄(`GEMINI_API_KEY` 바로 다음)에
  단독 `1`이 그대로 남아 있었다(2026-07-29·07-30 발견분과 같은 자리). 양쪽 다
  백업(`.env.bak-20260810`) 후 그 줄만 제거, `docker compose config`·컨테이너
  키 주입 정상 확인. 편집기 확장이 원인이라는 추정은 그대로다(플레인 `.env`와
  마크다운 양쪽에서 나왔으므로 파일 타입 문제가 아님).
  **재발 탐지를 자동화**: `scripts/check_env_drift.py`가 이제 `KEY=`도 주석도
  아닌 줄을 잡아 줄번호와 함께 출력하고 exit 1을 낸다(백업본으로 실제 탐지 확인).
  근본 원인(어떤 익스텐션인지)은 여전히 미확인 — 재발하면 그때 확인.
- **비전 02·05**(아래 감사표): 02 용도 결정, 05 용도+VRAM 전략(외부 GPU 분리?) 필요.
- **시크릿 (a)**: pydantic-settings 도입 시 mova·ontology 키 접근 함께 이관
  (단독 실행 금지 — WORK_LOG 2026-07-24 [2순위](a)).
  **2026-08-10 확인**: 이건 착수할 작업이 아니라 **다른 결정에 붙은 조건**이다.
  2026-07-24 조사 결론이 "두 곳이 같은 env 이름을 읽어 값 divergence 없음(상태
  중복이 아니라 코드 중복), 현재는 무해"였고, 지금 accessor를 신설하면
  pydantic-settings 이관 때 또 뜯게 된다. **app별 Settings 도입 여부가 먼저
  결정돼야 열리는 항목.**
- **`suvis/app/mail/contacts` 공개 레슨 데모 처리(2026-07-28 신규)**: adress
  엔드포인트에 `require_admin`을 걸면서 이 페이지는 이제 업로드 시도 시 401만
  받는다. 페이지 자체를 지울지, 로그인 요구 안내로 바꿀지, 별도 더미 데이터로
  분리할지 제품 결정 필요. (어드민 백엔드 인증 공백 감사 자체는 완료됨 —
  위 "완료됨" 2026-07-28 항목 참고.)

---

## 참고: 02~08 적합성 감사 (2026-07-23, `00_COMMON_conventions.md` §8)

06의 실패(기법 먼저·용도 나중)를 기준으로 재감사한 결과.

| # | 이름 | 상태 |
|---|------|------|
| 02 | Argus(객체 검출) | 보류 — 용도 위험/데이터 불확실, 제품 결정 전까지 착수 안 함 |
| 03 | Loom(분할) | **제외**(2026-07-27) — 관문0 실측: 보도 신호가 서울 OSM에 없음(문서 배너) |
| 04 | Atlas(자세 추정) | **제외** — mova/gildle에 용도 없음(문서 배너) |
| 05 | Prisma(이미지 생성) | 보류 — 용도 불확실 + 하드웨어 위험(SD1.5 LoRA vs lora-server VRAM 겹침) |
| 06 | Sentinel(이상 탐지) | **완료**(H0~H6, `/vision/upload` 게이트) |
| 07 | Echo(감정분석) | **완료**(H0~H6) |
| 08 | Chronos(영상 분류) | **제외** — mova/gildle에 용도 없음(문서 배너) |

## 참고: VRAM 정책 (확정, `00_COMMON_conventions.md` §1.1)

`lora-server`(mova 채팅용 EXAONE-2.4B AWQ)가 상시 기동 → **모든 학습 전
`systemctl --user stop lora-server`**, 학습 후 `start` + `:8200/health` 확인 필수.
`nvidia-smi` free 수치만 믿지 말 것(WSL2 계측 불안정, 290MB↔7975MB 편차 사례).
