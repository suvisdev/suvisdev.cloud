# 백엔드 전체 코드 리뷰 — 2026-09-11

`suvisdev/` 전체(앱 12종 + core/shared/scripts/main.py) 점검 결과.
방법: 자동 검사 4종(pytest 774 passed · mypy 1,106파일 청정 · ruff 9건 ·
lint-imports 6계약 유지) + 영역별 병렬 심층 리뷰 5개(발견마다 호출 경로
재확인) + 높음 항목은 별도 재검증. **보고만, 수정 안 함.**

표기: [검증] = 세션에서 코드 직접 재확인 완료. 나머지는 리뷰 에이전트가
코드·호출처를 확인한 항목.

---

## 처리 현황 (같은 날 저녁 — 권장 순서 ①~⑤ 완주, 배포는 학습 종료 후)

- **① 인증 3건 + viewer login/signup 언마운트: 수정 완료.** H1 평문 비교
  제거+bcrypt 지원(viewer)·bcrypt 재해시 온 로그인(auth), H2 미검증 이메일
  role 차단, H3 시드 스킵. 회귀 테스트 신규
  (`test_oauth_role_from_verified_email.py` 등).
- **② 무인증 10곳 + gildle: 수정 완료.** jack/train은 스텁(메시지 반환뿐)으로
  판명돼 가드 제외. 프론트 토큰 배선 3곳(rankings 버튼·face predict·titanic
  업로드) 동반 수정. 가드 401 테스트 8건 신규.
- **③ 중간 1~5: 수정 완료.** rating 보존, editor_reviews cancel, 임베딩
  분기 재사용 2곳, rate limit CF-Connecting-IP+마지막 XFF+버킷 정리,
  OAuth state Redis 1회 소비+시크릿 미설정 즉시 실패.
- **④ 성능: 수정 완료.** gildle(그래프 캐시·nx 콜러블 weight로 전 간선 사전
  대입 제거·노드 그리드 인덱스·edge_lookup/그늘 슬롯 캐시·CSV mtime 캐시),
  mova 제목 (id,title) 10분 TTL 캐시, LotteCinema·TmdbCatalog 싱글턴.
- **⑤ 정리: 완료.** 데드 파일 42개 삭제(AWQ 체인·비전 스켈레톤 20·platform
  체인·빈 파일 등 — **titanic 빈 엔티티 8개는 mapper가 "미구현" 명시 참조하는
  의도적 스캐폴딩으로 판명, 보존**), 일회성 스크립트 30개 `scripts/_archive/`
  이동(+README), compose→kubectl 사용법 16건, utcnow 3곳, 레거시 Query 1곳,
  CLAUDE.md §B·§O 실측 갱신, EC2/compose 낡은 주석 11곳, `.env.example` AWQ
  제거, pyproject 유령 앱 제거·mypy 3.13(ruff 타깃은 py313 시 신규 룰 87건이라
  별도 작업으로 보류·주석 기록), requirements 미사용 10종 제거.
- **잔여(다음 라운드)**: 중간 6~15(세션 폐기 장치·admin 판정 소스 단일화·
  username 충돌·gildle pg 세션 close·dispatch 길이 상한·crawl 격리·GPU
  동시성 세마포어·GamesInteractor 레이어·api_auth 쿠키)와 낮음 전부,
  access TTL·localStorage(설계 필요), main.py 인코딩 깨짐(원문 복원 필요).
- 검증: pytest 784 passed · mypy 1,063파일 청정 · ruff 기존 9건 유지 ·
  lint-imports 6계약 · `import main` OK · 프론트 type-check/lint 청정.

---

## 높음 — 즉시 조치 권장

### H1. 해시/평문을 비밀번호로 제출하면 로그인되는 검증 로직 [검증]
- `apps/viewer/adapter/outbound/pg/login_pg_repository.py:25-27`,
  `apps/auth/repository.py:105-115`
- `stored == raw_password or stored == sha256(raw)` — ① DB의 sha256 해시
  문자열이 유출되면 그 해시를 비밀번호 칸에 그대로 넣어 로그인(pass-the-hash)
  ② 평문 저장 계정 통과 허용 ③ 무염 sha256이라 레인보우 테이블 취약.
  auth 게이트웨이(`/auth/login`, 프론트 실사용 경로)도 동일 로직 재현
  (bcrypt는 신규 signup 계정만).
- 수정: 평문 동등 비교 제거 + sha256 계정은 로그인 성공 시 bcrypt 재해시.

### H2. admin role이 미검증 이메일로 산출됨 [검증(코드) / 공격경로는 네이버 전제]
- `apps/viewer/adapter/outbound/cache/redis_session_store_adapter.py:28-47`
- `issue_session → _resolve_role(email)`이 `email_verified`를 안 본다.
  네이버는 이메일 검증 여부를 확인할 수 없다고 어댑터 스스로 주석
  (`naver_oauth_adapter.py:84`). 공격자가 네이버 프로필 이메일을
  `ADMIN_EMAILS`의 주소로 설정하고 로그인하면 role=admin 세션 발급 →
  `require_admin` 통과.
- 수정: 미검증 이메일은 `_resolve_role`에 `None` 전달(인터랙터에서 분기).

### H3. 기본 관리자 시드 admin/admin1234 [검증]
- `apps/viewer/adapter/outbound/orm/admin_orm.py:62-66`
- `VIEWER_ADMIN_PASSWORD` 미설정 시 admin/admin1234(무염 sha256) 자동 생성.
  admins 테이블이 비어 있을 때만 발동하므로 현 프로덕션은 무사하나, 새
  환경/DB 초기화 시마다 지뢰. 이 계정으로 auth 게이트웨이 로그인하면
  admin RS256 토큰 발급.
- 수정: env 미설정이면 시드 스킵(또는 무작위 비밀번호 + 로그 안내).

### H4. 무인증 엔드포인트 군 — GPU 점유·쓰기·LLM 과금 (같은 패턴 10곳)
09-09 vision `/upload` 수정과 동일 클래스인데 형제 엔드포인트들이 빠짐:
| 엔드포인트 | 위치 | 영향 |
|---|---|---|
| `POST /face/train` [검증] | `ontology/.../face_router.py:13` | **epochs 상한 없음** — `?epochs=100000`로 프로덕션 GPU 무기한 점유. `/face/predict`도 가중치 없으면 30에폭 학습 자동 트리거 |
| `POST /face/predict` [검증] | 같은 파일:26 | 무제한 `file.read()` + GPU 추론 |
| `POST /sentinel/detect`·`/genre/classify` | `anomaly_detection_router.py:13`·`image_classifier_router.py:13` | 무제한 업로드 + 호출당 모델 로드 |
| `POST /nlp/sentiment/analyze` | `sentiment_analysis_router.py:17` | 호출당 EXAONE-2.4B 4bit 로드(수십 초) |
| `POST /ontology/semantic/ask` | `semantic_router.py:24` | Gemini 과금 호출 |
| `POST /mova/collections` [검증] | `collections_router.py:48` | 익명 컬렉션 무제한 생성(공개 목록 노출). 같은 라우터 PATCH/DELETE만 admin |
| `POST /mova/rankings/refresh` | `market_rankings_router.py:48` | 익명이 스냅샷 delete+insert 반복 트리거 |
| `POST /api/titanic/james/upload`·`jack/train`·`rose/train` | `crew_james_director_router.py:29` 등 | 무인증 DB 쓰기 + 무제한 `file.read()`(OOM) |
| `POST /execsuite/pdf/summarize` | `pdf_loader_router.py:15` | 무제한 PDF → Ollama 요약 → 전문 DB 저장 |
| `POST /dispatch/spam/classify` | `spam_router.py:17` | 익명 LLM 호출(프론트 호출처 0건 실측) |
- 수정: 일괄 가드 세션 1회 — 데모 필요한 것만 `require_user`+크기 상한,
  나머지 `require_admin`. train 계열은 파라미터 상한 추가.

### H5. gildle `/graph-edges` — 무파라미터 호출 시 23.4만 간선 전체 반환 [검증]
- `apps/gildle/adapter/inbound/api/v1/route_router.py:305-326`
- bbox 없으면 `return edges` (scored_edges.json 전체, 원본 80MB), bbox
  있어도 zoom≥15면 상한 없음. 익명 반복 호출로 CPU·메모리·대역폭 소진.
- 수정: bbox 4개 필수화 + 무조건 최대 건수 상한.

---

## 중간

1. **마지막 리뷰 삭제 시 `movies.rating` 0.0 파괴** [검증] —
   `market_reviews_pg_repository.py:440-455`. 리뷰 avg NULL이면 TMDB 유래
   기준 평점을 0.0으로 덮어쓰고 복원 경로 없음 → 가중평점 정렬 최하위,
   게임 풀(rating≥3.3) 탈락. 리뷰 0건이면 rating을 건드리지 말 것.
2. **main.py editor_reviews 스케줄러 cancel 누락** (리뷰 2개가 독립 발견) —
   `main.py:128` 생성, `:176-197` finally에서 이 태스크만 미취소 →
   종료 시 dispose된 엔진 참조/경고.
3. **임베딩 백엔드 하드코딩 2곳** — `kofic_import_scheduler.py:40-43`,
   `ontology/dependencies/semantic_router_provider.py:47`이
   `EMBEDDING_BACKEND` 분기(`hub_rag_provider.get_hub_embedding_port`)를
   안 타고 `OllamaEmbeddingAdapter()` 고정. gemini 환경에서 신작 색인
   조용히 누락 / semantic ask RAG 퇴화. → `get_hub_embedding_port()` 재사용.
4. **채팅 rate limit 우회 + 메모리 성장** — `mova/.../rate_limit.py:17-24`.
   클라이언트 제공 `X-Forwarded-For` 첫 요소를 키로 신뢰(난수 헤더로 20회/분
   완전 우회) + 빈 deque 미삭제. → cloudflared `CF-Connecting-IP` 사용.
5. **viewer OAuth state 재사용 가능 + 서명키 빈 문자열 폴백** —
   `oauth_router.py:22,26-49`. 1회 소비 없음(10분 내 로그인 CSRF), JWT_SECRET
   미설정 시 HMAC 키 `b""`. → auth 게이트웨이의 Redis 1회 소비 방식으로 통일.
6. **세션 폐기 수단 부재** — `viewer:session:{jti}`는 쓰기만 되고 읽는 곳
   0건, `verify_viewer_session_token`은 Redis 미조회 → 서버가 토큰을 무효화할
   방법이 없음(TTL 7일 이슈와 별개).
7. **admin 판정 소스 드리프트** — viewer HS256은 `ADMIN_EMAILS`, auth
   게이트웨이 RS256은 `groups.code`. 같은 사람이 로그인 경로에 따라
   admin/user가 갈림. 소스 단일화 필요.
8. **auth signup·카카오 모바일 username 충돌 시 500** —
   `auth/services.py:91`, `repository.py:185-260`. UNIQUE 충돌 미처리(흔한
   닉네임이면 영구 로그인 불가) + 이메일 대소문자 미정규화(중복 계정).
9. **gildle 요청당 재계산·잠재 커넥션 누수** — 최근접 노드 233k 전수 스캔,
   해저드 CSV 매번 read_csv, shade lookup 매 요청 재구축
   (`route_router.py:51-56,192-201` 외); postgres 모드는 요청마다
   `create_engine`+세션 미close(현재 csv 모드라 잠복). → mtime 캐시 승격.
10. **dispatch receive 본문 길이 상한 없음** — `receive_schema.py:8-11`.
    의도된 무인증 경로에 수 MB 본문 반복 투입 가능(추론+임베딩 동반).
    → `max_length` 부여.
11. **crawl 배치 1개 정책 실패가 전체 중단** — `Crawler_interactor.py:59-67`.
    루프 내 예외 격리 없음. → per-policy try/except.
12. **GPU 호출당 로드에 동시성 가드 없음** — echo/sentinel/convnext/yolo
    어댑터. 동시 2건이면 VRAM OOM 경쟁(상주 lora-server 여파 가능).
    → 모듈 레벨 세마포어(1)로 직렬화.
13. **movies 전체 로드 제목 매칭 2곳** —
    `market_chat_pg_repository.py:255-306`. evaluate/booking 폴백마다 전
    행 로드+파이썬 순회. → 캐시 or pg_trgm.
14. **GamesInteractor가 앱 레이어에서 HTTPException** —
    `games_interactor.py` 다수 행. 레이어 규칙(§K) 위반, mova 내 유일 이탈.
15. **`api_auth` 쿠키에 자격증명 평문(base64) 저장 + 도달 불가 분기** —
    `main.py:307-319,400-404`. → HMAC 서명 토큰으로.

## 낮음 (요약)

- 스포일러 감지 실패가 "성공(스팬 없음)"으로 저장 — `spoiler_detection.py:90-94`
  가 예외를 삼켜 인터랙터 failed 분기 도달 불가.
- 리뷰 텍스트 프롬프트 펜싱 누락 2곳 — `spoiler_detection.py:89`,
  `market_chat_evaluation_interactor.py:205-208`.
- 게임 점수 상한 없음(`score=10^9`로 리더보드 1위 고정 가능).
- 요청마다 새로 만드는 어댑터의 인스턴스 캐시 무효(LotteCinema 24h 캐시,
  TMDB 장르맵) — `market_chat_provider.py:111-124`, `upcoming_router.py:29`.
- `save_picks`가 2차 dedup 이전 실행 — 노출 안 된 카드가 picks에 남음.
- viewer OAuth 외부 에러 원문 502 detail 노출, handoff 탭 구분 파싱,
  pending identity에서 `email_verified` 소실(자동 연결 분기 죽은 기능).
- main.py 인코딩 깨진 문자열(`/docs`·`/` 응답 노출), harvester Redis
  요청당 풀 생성, custom URL 스크랩 SSRF 여지(어드민 전용),
  `adress` `q` 기본값 검증 우회, ruff 9건(StrEnum 8·zip strict 1).

---

## 낡은 코드 (데드/스테일 — 전 저장소 grep으로 참조 0 확인)

**삭제 후보(참조 0):**
- AWQ :8100 데드 체인: `core/lol/awq_exaone_orchestrator.py` +
  `ontology/.../awq_llm_adapter.py` + `mova/.../exaone_recommendation_adapter.py`
  (GGUF 롤백 대상은 :8200 serve.py라 이 체인은 무관)
- `core/lol/router_worker_pipeline.py`+`model_switch_guard.py`(RTX 3050 실험),
  `core/torch_test.py`(2줄 스크래치)
- 빈 파일 16개: `core/matrix/grid_{smith,morpheus,trinity}_*.py`(0바이트),
  execsuite 3개, titanic domain/entities `pass` 10개
- mova: `ollama_exaone`·`qwen_recommendation_adapter.py`(미배선),
  `platform_{users,admins,groups}` 인터랙터/포트 체인(라우터 없음),
  `schedule_review_embedding` 미사용
- ontology 비전 스켈레톤 5종(object_detection·pose·segmentation·video·
  image_generation 인터랙터/포트/DTO — docstring이 가리키는 라우터 부재)
- execsuite: `n8n_client.py`+`get_n8n_client`(placeholder URL), MCP 툴 5개
  (미등록), `langchain_interactor.py`의 미사용 `system` 파라미터
- gildle: `get_walk_graph_source/port`·`get_import_tree_segment_use_case`
  프로바이더, `PgRouteGraphRepository.load_edges`(경로 계산은 JSON 소스)
- viewer `login_router`·`signup_router` — 프론트 참조 0(실사용은 auth
  게이트웨이), H1 취약 로직만 공개 노출 중
- scripts: 적용 완료된 일회성 DDL ~24개(`add_*`·`rename_*`·`merge_*` 등,
  SSOT는 alembic) → `scripts/_archive/` 이동 권장. `extract_kofic.py`·
  `extract_adapters.py`는 Windows 경로 하드코딩으로 실행 불가.

**스테일 문서/주석(코드는 정상, 서술만 낡음):**
- `suvisdev/CLAUDE.md` §B 앱 표 — 존재하지 않는 앱 5개(silicon_valley 등)
  기재, "등록 앱: titanic·mova·viewer"도 실제(10앱 등록)와 불일치
- EC2 현역 전제 주석 7곳(hub_rag_provider·fallback 어댑터·Tank 등),
  keymaker "compose env_file" docstring
- scripts 12+개의 `docker compose exec backend ...` 사용법(compose 삭제됨)
- `.env.example` AWQ 주석, `pyproject.toml` isort known-first-party의 유령
  앱 5개 + target-version py312(실제 3.13)

**의존성(import 0 실측):** `firebase-admin`, `sqlmodel`, `langsmith`,
`langchain`(core·google-genai 제외 계열 전부), `langgraph` 3종 —
제거 후보. `bitsandbytes`는 간접 사용이라 유지.

**env 드리프트:** `.env`에 없는 키 9개 중 `AUTH_*_REDIRECT_URI` 3종은
기지(既知), `LORA_SERVER_TOKEN`은 데스크톱 `.env`에 없음(데스크톱
lora-server가 토큰 검증 시 개발 채팅이 Gemini 폴백으로 빠짐 — 확인 권장).

---

## 깨끗했던 영역

- IDOR/소유권(리뷰·워치리스트·마이페이지·픽스·대화) 전부 토큰 기준 —
  08-07 수정 이후 회귀 없음. 7월 dispatch/adress 취약점 회귀 없음.
- SQL 인젝션 표면 없음(전부 바인딩), 스타-토폴로지 위반 0건, alembic 체인
  선형·단일 head, async 세션 동시성 규칙 위반 0건, BackgroundTasks 세션
  팩토리 패턴 정상, shared/security JWT 검증(알고리즘 고정·aud/exp·빈
  시크릿 거부) 견고, auth 게이트웨이 refresh 로테이션·state 1회 소비·
  오픈 리다이렉트 차단 양호.

## 권장 착수 순서

1. H1~H3 인증 3건(+viewer login/signup 라우터 노출 정리 — H1과 한 묶음)
2. H4 무인증 엔드포인트 일괄 가드(패턴 동일, 한 세션에 10곳) + H5 gildle 상한
3. 중간 1~5(rating 파괴·스케줄러 cancel·임베딩 하드코딩·rate limit·OAuth state)
4. 성능 캐시류(gildle·제목 매칭·어댑터 싱글턴)
5. 데드 코드 아카이브/삭제 + 스테일 주석·CLAUDE.md §B·requirements 정리
