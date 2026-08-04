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

---

## 진행 중 (현재 액티브)

없음. (03 제외 확정으로 이번 트랙의 액티브 조사 종료. 착수 대기 항목은
아래 "다음 / 남은 작업" 참고.)

---

## 다음 / 남은 작업 (백로그)

- **폰 카메라 → S3 업로드 실기기 검증(2026-08-03 신규, 코드는 완성)**: 폰
  adb 연결이 계속 끊겨 `flutter run`으로 실제 촬영→업로드 확인 못 함
  (`pytest`/`flutter analyze`만 확인). access token 10분 TTL 만료 시 자동
  재발급(refresh)도 미구현 — 만료되면 401, 재로그인 필요.
- **mova 추천 원격 GPU — 실제 Tunnel 연동(2026-08-03 신규, 코드는 완성)**:
  `_docs/lora-remote-gpu-ops.md` 절차대로 집 GPU에서 `lora_server` 기동 +
  Cloudflare Tunnel Public Hostname 추가 + EC2 `.env`
  (`RECOMMENDATION_BACKEND=lora`/`LORA_SERVER_URL`/`LORA_SERVER_TOKEN`)
  실제 반영·연동 테스트 필요. `is_ready()` 헬스체크가 코드 어디서도 안 불리는
  문제도 미해결(별도 이슈로 미룸 — 지금은 실패가 실제 `/generate` 호출
  타임아웃/에러로만 드러남).
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
- **mova TMDB credits 백필 EC2 실행(2026-07-30 신규, 2026-08-02 집 로컬
  완료·EC2는 아직)**: 집 로컬 Docker DB는 2026-08-02에 `alembic upgrade
  head` + `scripts/backfill_credits_cli.py` 전량 실행까지 완료(actors 389/
  characters 371/movie_directors 40, WORK_LOG 2026-08-02 참고). **EC2 DB는
  아직 미실행** — 동일하게 `alembic upgrade head` 적용 후
  `--limit 3 --dry-run`으로 먼저 시험 후 전량 실행 필요.
- **Neo4j 데이터 투입**: 스키마(제약+벡터 인덱스)만 있고 노드는 0건. TMDB/KOFIC
  import 파이프라인으로 채워야 함(착수 전).
- **`create_all()`/alembic 테이블 생성 이중 관리(2026-07-30 신규)**:
  `ensure_titanic_tables()`의 `create_all()`과 alembic이 테이블 생성을
  이중으로 관리하고 있어, 새 ORM 모델이 추가될 때마다 이번(`hub_knowledge`)과
  같은 `DuplicateTable`/`stamp` 우회가 반복될 수 있다. 근본 해결은
  `create_all()` 경로를 제거하고 alembic을 단일 소스로 삼는 것. 상세:
  WORK_LOG 2026-07-30.
- **mova 대량 영화 수집 실제 실행(2026-08-02 신규, 코드는 완성)**:
  `scripts/bulk_import_movies.py`를 아직 한 번도 실행하지 않음 — 목표는
  TMDB(해외)+KOFIC(한국) 합산 수만 편, 하루 배치(예: `--pages` 조절해 1000편
  안팎)로 점진 적재. 실행 전 TMDB API 요청량(수만 편×credits 1회씩)이
  일일 쿼터에 걸리는지 확인 필요. `scripts/backfill_hub_movies_rag.py`(정적
  JSONL 기반 구버전 hub_knowledge 백필)와 목적이 겹치므로, 대량 수집이
  안정화되면 이 구버전 스크립트를 정리(삭제 또는 문서화)할지도 함께 결정
  필요. 상세: WORK_LOG 2026-08-02.
- **`get_mova_session_factory()` 직접 사용 시 commit 누락 함정(2026-08-02
  신규, 경미)**: `HubKnowledgeRepository.upsert()`처럼 `flush()`만 하고
  `commit()`을 안 하는 레포지토리가 있음 — `get_mova_db()`(FastAPI
  의존성)는 응답 종료 시 자동 commit하지만, `get_mova_session_factory()`를
  일회성 스크립트에서 직접 쓸 땐 호출자가 명시적으로 `session.commit()`을
  해야 함(`scripts/ingest_hub_knowledge.py` 참고). 근본 해결(레포지토리
  commit 정책 통일)은 안 함 — 향후 유사 스크립트 작성 시 주의만 필요.
- **단독 `1` 문자 삽입 재발(2026-07-30, 2026-08-04) — `.env` 한정 문제 아님**:
  `suvisdev/.env` 29번째 줄(`GEMINI_API_KEY` 바로 다음)에서 2건(2026-07-29,
  2026-07-30) 발견된 것과 같은 종류의 단독 `1` 문자가, 2026-08-04엔
  `suvis/_docs/CLAUDE.MD`(IDE에서 열려 있던 상태)의 `---`와 `## C. 핵심 규칙`
  사이에서도 발견됨(git diff로 확인, 해당 파일은 이번 작업으로 삭제돼 자연
  소멸). `.env`(플레인 텍스트, 자동저장 없음)와 마크다운(IDE에서 열림) 둘 다
  나타나 파일 타입이 원인이 아님 — **IDE 확장이나 포맷터가 열린 파일에
  주기적으로 개입하는 쪽에 무게가 실림**. 재발하면 어떤 익스텐션이 활성인지
  확인 필요.
- **비전 02·05**(아래 감사표): 02 용도 결정, 05 용도+VRAM 전략(외부 GPU 분리?) 필요.
- **시크릿 (a)**: pydantic-settings 도입 시 mova·ontology 키 접근 함께 이관
  (단독 실행 금지 — WORK_LOG 2026-07-24 [2순위](a)).
- **`suvis/app/mail/contacts` 공개 레슨 데모 처리(2026-07-28 신규)**: adress
  엔드포인트에 `require_admin`을 걸면서 이 페이지는 이제 업로드 시도 시 401만
  받는다. 페이지 자체를 지울지, 로그인 요구 안내로 바꿀지, 별도 더미 데이터로
  분리할지 제품 결정 필요.
- **어드민 백엔드 인증 공백**: (2026-07-27 대응) 가드를 `shared/security/require_admin.py`로
  이동 후 dispatch `email/telegram/discord` POST·`receive` GET/DELETE, harvester
  `scrape/crawl/sites`에 `require_admin` 추가 + 프론트 프록시/클라가 세션 Bearer를
  백엔드까지 전달(3계층). 상세 WORK_LOG 2026-07-27 [2]. **2026-07-28 추가**:
  `watcher/judge/spam/adress` 전수 감사 완료 — watcher/judge는 위험 없는 스텁,
  spam은 미사용 코드, **adress는 실제 무인증 쓰기/조회 취약점이라 수정 완료**
  (위 "완료됨" 참고). `receive` POST는 외부 인입이라 의도적으로 무인증 유지.

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
