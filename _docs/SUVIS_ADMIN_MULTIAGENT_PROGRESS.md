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
  게이트('봤어요' 버튼)는 Phase B로 의도적으로 남김. 상세: WORK_LOG
  2026-07-31.
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

---

## 진행 중 (현재 액티브)

없음. (03 제외 확정으로 이번 트랙의 액티브 조사 종료. 착수 대기 항목은
아래 "다음 / 남은 작업" 참고.)

---

## 다음 / 남은 작업 (백로그)

- **어드민 통계 방문자 — alembic 적용 확인(2026-07-31 신규)**: 마이그레이션
  `20260731_0001_create_analytics_visitor_activity`가 `20260730_0001` 뒤에
  정상 연결돼 있음은 `alembic history`로 확인했지만, Docker(Postgres) 접근
  불가로 `alembic upgrade head` 실제 적용은 못 했다. 집/EC2에서 적용 후
  `/admin/stats/visitors` 탭이 실제 숫자를 보여주는지 확인 필요.
- **mova 리뷰 watched 게이트 Phase B(2026-07-31 신규)**: "watched로 기록한
  유저만 리뷰 작성 가능" 정책은 이번 Phase A에 포함 안 함 — '봤어요' 버튼
  프론트 UI + `ReviewsRepositoryPort.has_watched(user_id, movie_id)`(신설
  필요, `user_actions.action_type == "watched"` 조회) + `add_review()`에
  게이트 삽입이 남은 작업. rating을 watched 판정 근거로 쓰면 안 됨(순환
  논리 — 상세 WORK_LOG 2026-07-31 리뷰 사전조사 항목 참고).
- **mova TMDB credits 백필 집(GPU) 실행(2026-07-30 신규, 2026-07-31 사전준비
  완료)**: `alembic upgrade head`로 `20260730_0001`(actors.tmdb_person_id 등
  4건) 적용 후 `python scripts/backfill_credits_cli.py` 실행 필요. 2026-07-31에
  학원 환경에서 할 수 있는 사전 준비 끝: ① 마이그레이션 체인 정적 검증(단일
  head, 선형 연결, UNIQUE/DROP/downgrade 안전성 확인 — 단 Docker 미기동으로
  실제 upgrade/downgrade 왕복은 미검증), ② CLI에 `--limit N`(시험 실행)·
  `--dry-run`(DB write 없이 로그만) 추가, ③ TMDB 429 백오프 + 영화 간 sleep
  추가로 안정성 보강. **남은 건 집에서 실제 `alembic upgrade head` 적용 +
  `--limit 3 --dry-run`으로 먼저 시험 후 전량 실행뿐.** 실행 전
  `SELECT COUNT(*) FROM actors;`로 0행인지 먼저 확인 권장(마이그레이션이 그
  전제를 코드로 검증하지 않음). 상세: WORK_LOG 2026-07-31.
- **Neo4j 데이터 투입**: 스키마(제약+벡터 인덱스)만 있고 노드는 0건. TMDB/KOFIC
  import 파이프라인으로 채워야 함(착수 전).
- **`create_all()`/alembic 테이블 생성 이중 관리(2026-07-30 신규)**:
  `ensure_titanic_tables()`의 `create_all()`과 alembic이 테이블 생성을
  이중으로 관리하고 있어, 새 ORM 모델이 추가될 때마다 이번(`hub_knowledge`)과
  같은 `DuplicateTable`/`stamp` 우회가 반복될 수 있다. 근본 해결은
  `create_all()` 경로를 제거하고 alembic을 단일 소스로 삼는 것. 상세:
  WORK_LOG 2026-07-30.
- **`suvisdev/.env` 손상 재발(2026-07-30 신규, 경미)**: 29번째 줄
  (`GEMINI_API_KEY` 바로 다음)에 76번째 줄(2026-07-29 수정분)과 같은 종류의
  단독 `1` 문자가 또 발견됨. `NEO4J_PASSWORD` 로드엔 지장 없어 이번엔
  방치했지만, 반복되는 패턴이라 원인(에디터/스크립트 추정) 파악이 필요할 수
  있음.
- **비전 02·05**(아래 감사표): 02 용도 결정, 05 용도+VRAM 전략(외부 GPU 분리?) 필요.
- **시크릿 (a)**: pydantic-settings 도입 시 mova·ontology 키 접근 함께 이관
  (단독 실행 금지 — WORK_LOG 2026-07-24 [2순위](a)).
- **S3**: AWS 실연결(버킷+키 세팅) 후 Tank 단일 경로 실 업로드 검증.
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
