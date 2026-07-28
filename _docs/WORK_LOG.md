# 작업 일지

날짜별로 그날 한 작업·수정·오류·데이터를 기록한다. **최신 날짜가 맨 위**로
오게 추가한다(새 항목은 이 안내 바로 아래에 삽입). 요약용 재개 메모는
`SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(현재 상태·다음 할 일)를 따로 쓰고,
이 파일은 **그날그날 실제로 있었던 일의 상세 기록**(무엇을 왜 했는지,
어디서 막혔는지, 데이터가 어떻게 바뀌었는지)에 집중한다.

**항목 템플릿**:
```
## YYYY-MM-DD

### 작업 내용
- 무엇을 했는지, 왜 했는지(계기)

### 수정/구현
- 만들거나 고친 파일·코드, 핵심 변경점

### 오류·막힌 점
- 무슨 에러가 났는지, 원인, 어떻게 해결했는지(해결 안 됐으면 그것도 기록)

### 데이터
- 데이터셋 출처·규모·라벨 변경 등

### 산출물
- 커밋 해시, 문서 갱신 위치 등
```

---

## 2026-07-28

### 작업 내용
- suvis 프론트 LESSON 사이트에 LangChain 채팅 탭 신설 요청 — 처음엔 UI 틀만
  (SOCCER 섹션 아래 LANGCHAIN 섹션 추가, `/langchain/chat`), 이후 실제 파이프라인
  연결까지 확장 요청.
- silicon_valley 백엔드에 semantic_router(ontology) → LangChain 챗봇 엔진 파이프라인을
  클린 아키텍처(라우터→유스케이스→포트→리포지토리)로 구현.
- pnpm 로컬 개발환경 트러블슈팅(susu에 pnpm 잘못 로컬 설치, suvis `pnpm install`
  sharp 빌드 스크립트 차단) 지원.
- LangChain 활용 사례 문서 2건 추가(NCL, Elastic) + 기존 Morningstar 문서 접점
  섹션을 같은 형식으로 보강.

### 수정/구현
- **프론트(`suvis/`)**: `app/langchain/chat/page.tsx` 신규(soccer 채팅과 동일
  레이아웃, 인디고 테마, 실제 `/api/v1/langchain/chat` fetch). 사이드바에 LANGCHAIN
  섹션(채팅 링크)을 11개 페이지에 동일 추가(이 저장소가 사이드바 nav를 페이지마다
  복사하는 기존 관례를 따름). `pnpm-workspace.yaml`의 `allowBuilds.sharp`를
  자리표시자 텍스트에서 `true`로 수정. `susu/`에 잘못 로컬 설치됐던
  `node_modules`/`package.json`/`package-lock.json`/`pnpm-lock.yaml` 정리(삭제).
- **백엔드(`suvisdev/apps/silicon_valley/`)**: 신규 —
  `app/ports/output/rangchain_chat_engine_port.py`(`RangchainChatEnginePort`),
  `adapter/outbound/repositories/rangchain_chat_engine_repository.py`
  (`ChatPromptTemplate`+`MessagesPlaceholder`+`ChatOllama` LCEL 체인, destination별
  시스템 프롬프트 분기, `OLLAMA_BASE_URL` 반영), `app/dtos/rangchain_chat_dto.py`,
  `app/ports/input/rangchain_chat_use_case.py`, `app/ports/output/rangchain_chat_errors.py`,
  `adapter/inbound/api/schemas/rangchain_chat_schema.py`,
  `adapter/inbound/api/v1/rangchain_chat_router.py`(`POST /api/v1/langchain/chat`),
  `dependencies/rangchain_chat_provider.py`(ontology의 `get_semantic_router_use_case`를
  그대로 DI 재사용 — mova가 ontology를 참조하는 기존 cross-app 관례를 따름).
  `app/use_case/rangchain_interactor.py` — `semantic_router.route()` 호출 후 결과
  (destination/entities/answer)를 LangChain 엔진에 전달하도록 작성. `silicon_valley_router`에
  라우터 등록.
- **문서**: `apps/silicon_valley/_docs/ranchain-ncl-strategy.md`,
  `rangchain-elastic-strategy.md` 신규, `rangchain-monigstar-strategy.md` 접점
  섹션 보강 — 전부 "이 저장소엔 해당 데이터 소스 없음, 문서화만" 결론(실제
  데이터·구현은 보류).

### 오류·막힌 점
- **500 plain-text 파싱 오류**(`"Unexpected token 'I', "Internal S"... is not
  valid JSON"`): 원인은 `SemanticRouterInteractor.route()`(ontology)의
  general(잡담) 분기가 `HubRagError`를 잡지 않고 그대로 던지는데,
  `rangchain_chat_router.py`는 `RangchainChatError`만 캐치해서 미처리 예외가
  FastAPI 기본 500(plain text)으로 나간 것. `rangchain_interactor.py`에서
  `semantic_router.route()` 호출을 `HubRagError` 캐치 → `RangchainChatError`
  변환으로 고침. `GEMINI_API_KEY`는 `.env`에 설정돼 있어 정확한 실패 원인
  (quota/네트워크 등)은 재현 시 에러 메시지로 추가 확인 필요 — 이번 세션에서는
  백엔드 서버가 환경에 안 떠 있어 재기동 후 실제 검증은 못 함(코드 리뷰로만
  원인 특정).
- `[ERR_PNPM_IGNORED_BUILDS] sharp` — `pnpm-workspace.yaml`의 `allowBuilds.sharp`
  값이 `true` 대신 자리표시자 텍스트였던 게 원인.
- `[ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL] Command "dev" not found` — `susu`
  (Flutter, `package.json` 없음)에서 `pnpm dev`를 실행해 발생. `suvis`(Next.js)가
  맞는 위치.

### 데이터
- 해당 없음.

### 산출물
- 프론트: `suvis/app/langchain/chat/page.tsx`(신규) + 사이드바 11개 파일,
  `suvis/pnpm-workspace.yaml`.
- 백엔드: `apps/silicon_valley/` 내 `rangchain_chat_*`/`rangchain_interactor.py`
  8개 파일 신규, `adapter/inbound/api/__init__.py` 라우터 등록.
- 문서: `ranchain-ncl-strategy.md`, `rangchain-elastic-strategy.md`(신규),
  `rangchain-monigstar-strategy.md`(수정).
- 커밋 해시: 이번 커밋 참고.

---

### [2] PROGRESS 백로그 점검 — 진행 가능한 항목 처리

**배경**: 사용자가 `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 "다음/남은 작업"을
확인 후 지금 바로 진행 가능한 부분을 진행해달라고 요청. 비전 02·05(제품 결정
대기), 06 저장 지속화·S3(AWS 미연결), 시크릿(a)(단독 실행 금지 명시)는 외부
의존/결정 때문에 스킵하고, 실제 진행 가능한 두 항목만 처리.

**수정/구현**:
1. **`apps/mova/tests/test_import_interactor.py` 실패 2건 수정** — 원인은
   `ImportInteractor.__init__`에 `box_office`/`hub_rag` 파라미터가 추가됐는데
   테스트는 예전 3-인자 시그니처로 호출하던 것. 두 테스트 모두 이 두 의존성을
   실제로 쓰지 않는 경로라(`box_office` 미참조, `hub_rag.ingest_movie`는
   예외를 삼키는 try/except 안) `AsyncMock()` 2개만 추가해 해결. 8개 전부
   통과 확인(`/home/a/.venv/bin/python -m pytest apps/mova/tests/...`).
   `test_llm_error_handling.py`는 이미 통과 상태였음(PROGRESS 기록이 stale).
2. **dispatch `watcher/judge/spam/adress` 인증 공백 감사** — watcher·judge는
   `/myself` 스캐폴딩 스텁뿐이라 위험 없음. spam은 프론트·백엔드 어디서도
   호출하는 곳이 없는 미사용 코드라 위험 낮음. **adress는 실제 취약점**:
   `search`/`upload` 둘 다 인증이 전혀 없었는데, 어드민 UI
   (`admin/dispatch/contacts/page.tsx`)뿐 아니라 LESSON 공개 데모
   (`suvis/app/mail/contacts/page.tsx`, 로그인 개념 없음)도 같은 백엔드
   엔드포인트를 호출 — 2026-07-27 인증 공백 대응 당시 "어드민 UI 미사용"으로
   보고 범위에서 뺐던 판단이 틀렸음이 이번에 드러남. 사용자 확인 후(어드민만
   가드, 레슨 데모는 막기로 결정) 2026-07-27과 동일 패턴으로 수정:
   - BE: `adress_router.py`의 `search`/`upload`에
     `Depends(require_admin)` 추가.
   - FE 프록시: `suvis/app/api/dispatch/adress/{search,upload}/route.ts`가
     들어온 `Authorization` 헤더를 `backendFetch`로 전달하도록 수정(search는
     raw `fetch`에서 `backendFetch`로 교체).
   - FE 클라: `admin/dispatch/contacts/page.tsx` 업로드 호출에
     `suvis-session.ts`의 `authHeader()` 첨부.
   - `suvis/app/mail/contacts/page.tsx`(공개 레슨 데모)는 코드 변경 없음 —
     이제 업로드 시 401을 받게 됨(의도된 동작). 이 페이지 자체를 어떻게 할지는
     별도 결정 필요(PROGRESS 백로그에 남김).

**검증**: `python3 -m ast` 문법 검증 통과, `pnpm exec tsc --noEmit` 통과,
`pytest apps/mova/tests apps/dispatch`(jwt 미설치로 `test_whoami_router.py`
제외) 41 passed / 2 failed — 실패 2건은 `test_send_email_interactor.py`
(orchestrator 프롬프트 포맷 불일치, 이번 작업과 무관하게 기존에 깨져 있던
것을 우연히 발견 — 수정 안 함, PROGRESS 백로그에 신규 등록).

**오류·막힌 점**:
- `/home/a/.venv`에 `requirements.txt`엔 있는 `PyJWT[crypto]`가 실제로
  설치돼 있지 않아 `shared.security.require_admin`을 import하는 모든 모듈
  (email/telegram/discord/receive/harvester/adress 라우터,
  `test_whoami_router.py`)이 이 venv에서 import 실패함 — 내 변경으로 생긴
  문제가 아니라 기존 email_router.py로도 재현 확인. venv에
  `pip install -r requirements.txt` 재실행 필요(이번 세션에선 미설치 상태로
  둠, 별도 사용자 확인 필요해 임의 설치 안 함).

### 산출물 (2)
- `apps/mova/tests/test_import_interactor.py`(수정),
  `apps/dispatch/adapter/inbound/api/v1/adress_router.py`(수정),
  `suvis/app/api/dispatch/adress/search/route.ts`,
  `suvis/app/api/dispatch/adress/upload/route.ts`,
  `suvis/app/admin/dispatch/contacts/page.tsx`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신(완료 항목 반영 + 신규 백로그 3건:
  mail/contacts 공개 데모 처리, test_send_email_interactor 실패, PyJWT 미설치).

---

### [3] 프론트 프로덕션 API URL 설정 + LangChain 모델을 Gemini로 교체

**배경**: 강사가 `suvisdev/.cursorrules`에 `NEXT_PUBLIC_BASE_URL=https://api.suvisdev.cloud`를
넣으라고 지시했다는데, 이유를 물어와 확인해보니 지시 자체가 틀렸음. `.cursorrules`는
Cursor 에디터용 AI 코딩 규칙 문서일 뿐 어떤 코드도 환경변수로 읽지 않고,
`NEXT_PUBLIC_BASE_URL`이라는 이름도 이 저장소 어디에도 없음(실제 코드가 읽는
이름은 `NEXT_PUBLIC_API_URL`, `suvis/lib/backend-client.ts` 등 7곳). 게다가
`NEXT_PUBLIC_*`는 프론트(`suvis/`) 관례라 백엔드(`suvisdev/`) 쪽에 있을 이유도
없음. 올바른 위치·이름으로 바로잡아 설정.

이어서 랭체인 모델을 Gemini로 바꿀 수 있는지 요청받아 진행.

**수정/구현**:
1. `suvis/.env.production`(신규) — `NEXT_PUBLIC_API_URL=https://api.suvisdev.cloud`.
   `.gitignore`엔 `.env.local`만 있어 커밋 가능(NEXT_PUBLIC 값은 어차피 브라우저에
   노출되는 값이라 커밋해도 안전).
2. `rangchain_chat_engine_repository.py` — `ChatOllama(exaone3.5:2.4b)` →
   `ChatGoogleGenerativeAI`(langchain-google-genai)로 교체. 모델 ID는 새로 만들지
   않고 `core.matrix.vauly_keymaker_secret_manager.GEMINI_MODEL_MAP["flash15"]`
   (`gemini-3.1-flash-lite`)를 재사용, API 키도 `get_keymaker().gemini_api_key`
   재사용 — ontology `GeminiLlmAdapter` 등 다른 Gemini 사용처와 키·모델 관리
   일원화. LCEL 체인 구조(`ChatPromptTemplate`+`MessagesPlaceholder`+
   `StrOutputParser`)·destination별 프롬프트 분기·에러 래핑은 그대로 유지, LLM
   provider만 교체.
3. `requirements.txt` — `langchain-google-genai==4.3.2` 추가, `langchain-core`
   (1.4.8→1.5.1)·`langsmith`(0.9.3→0.10.10)는 설치 과정에서 자동으로 딸려 올라간
   실제 버전에 맞춰 갱신. `/home/a/.venv`에 실제 설치 완료.

**검증**: `RangchainChatEngineRepository().generate(...)`를 직접 호출해 실제
Gemini 응답("안녕하세요! 저는 SUVIS의 한국어 어시스턴트입니다...") 받는 것까지
확인.

**오류·막힌 점**: `langchain-ollama`도 `/home/a/.venv`에 실제로는 설치돼 있지
않았음(PyJWT와 같은 종류의 기존 venv-requirements.txt 드리프트) — 이번 작업으로
ChatOllama를 걷어내서 문제되진 않았지만, venv 전체가 `requirements.txt`와
계속 어긋나 있다는 신호라 언젠가 `pip install -r requirements.txt` 재실행 필요.

### 산출물 (3)
- `suvis/.env.production`(신규), `suvisdev/apps/silicon_valley/adapter/outbound/repositories/rangchain_chat_engine_repository.py`(수정),
  `suvisdev/requirements.txt`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 LangChain 파이프라인 항목에 Gemini
  교체 내용 반영.

---

### [4] CLAUDE.md 응답 언어 지침 + PROGRESS 백로그 추가 처리

**배경**: 사용자가 CLAUDE.md에 "한국어로만 답변, 다른 언어 금지" 지침 추가 요청.
이어서 PROGRESS.md를 다시 확인하고 진행 가능한 나머지 항목(테스트 실패, venv
드리프트) 처리 요청.

**수정/구현**:
1. `CLAUDE.md`에 "## 응답 언어" 섹션 추가 — 항상 한국어로만 답변, 다른 언어
   사용 금지.
2. **`test_send_email_interactor.py` 실패 2건 수정** — `SendEmailInteractor.send()`가
   이메일 품질 개선을 위해 `orchestrator.generate()` 호출에 `system=` 키워드
   인자를 추가한 게 실제 기능인데(수신자 정보 포함 프롬프트 + 이메일 작성
   전문가 시스템 프롬프트), 테스트 2건이 예전 시그니처(위치 인자 하나만)를
   가정하고 있어 깨졌던 것. `test_hub_record_called_before_orchestrator`의
   `mock_orc.generate.side_effect` 람다가 `system=` 키워드를 못 받아 TypeError,
   `test_orchestrator_generates_body`는 호출 인자 자체를 잘못 assert. 둘 다
   실제 호출 형태에 맞게 테스트 수정. 14개 전부 통과.
3. **PyJWT/langchain-ollama 미설치 해소** — `pip install -r requirements.txt`
   전체 실행을 시도했으나 두 단계로 실패:
   - 1차: `/tmp`가 WSL2 tmpfs(3.9G)라 torch(843MB) 등 받다가
     `[Errno 28] No space left on device` — `TMPDIR`을 디스크 쪽
     (`/home/a/.cache/pip-tmp`, `/`는 898G 여유)으로 돌려 재시도.
   - 2차: `catboost==1.2.8`이 Python 3.14에서 빌드 실패
     (`AttributeError: 'Distribution' object has no attribute 'dry_run'` —
     distutils가 Python 3.12+에서 빠지면서 구식 setup.py가 깨짐). titanic 앱이
     실제로 쓰는 패키지라 requirements.txt에서 못 뺌 — 전체 동기화는 별도
     결정(catboost 버전 업/Python 버전 조정) 필요해 백로그로 남김.
   - 실제 목적(PyJWT 미설치)은 전체 동기화 대신 `PyJWT[crypto]==2.10.1`,
     `langchain-ollama==1.1.0`만 개별 설치로 해결. `require_admin`을 쓰는
     `email_router`·`rangchain_chat_router` import 확인, `apps/mova/tests`+
     `apps/dispatch` 47개 전부 통과(이전엔 jwt 없어 수집 실패하던
     `test_whoami_router.py`도 포함).

### 산출물 (4)
- `CLAUDE.md`(수정), `suvisdev/apps/dispatch/test/test_send_email_interactor.py`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신 — 완료 항목 반영(테스트 수정,
  PyJWT/langchain-ollama 설치), catboost 빌드 실패를 신규 백로그로 등록.

---

### [5] catboost/Python 3.14 빌드 문제 해소 + 캐시 정리

**배경**: [4]에서 남긴 백로그(`catboost` 빌드 실패로 `pip install -r
requirements.txt` 전체 불가)를 이어서 처리. 이후 사용자가 `suvisdev/`의
`.import_linter_cache`/`.mypy_cache`/`.pytest_cache`/`.ruff_cache`가 필요한지
질문.

**수정/구현**:
1. `catboost==1.2.8`→`1.2.10` 버전 업 — PyPI에 Python 3.14용 사전빌드 wheel
   (`catboost-1.2.10-cp314-cp314-manylinux2014_x86_64.whl`)이 존재함을
   `pip download`로 먼저 확인 후 진행. titanic 앱의 실제 사용(`CatBoostClassifier(
   iterations=200, verbose=False, random_state=42)`)은 단순 API라 호환 문제
   없음.
2. `pip install -r requirements.txt` 재실행 — 이번엔 빌드 에러 없이 끝까지
   성공(torch-2.12.1+cu126 등 전체 설치). `catboost`/`jwt` import 확인.
3. `apps/mova/tests`+`apps/dispatch`+`apps/titanic` 전체 재실행 —
   mova/dispatch는 계속 통과. **`apps/titanic/tests` 4개가 새로 눈에 띔**
   (패키지 설치와 무관, 지금 코드에 없는 이름 import: `JackTrainerMapper`,
   `titanic.adapter.outbound.llm`, `PassengerEntity`,
   `passenger_jack_trainer_vo` 모듈) — 원인 조사·수정 안 함, 백로그 등록.
4. `.import_linter_cache`/`.mypy_cache`(18M)/`.pytest_cache`/`.ruff_cache`
   삭제 — 전부 재생성 가능한 도구 캐시. `.mypy_cache`/`.pytest_cache`/
   `.ruff_cache`는 `.gitignore`에 이미 명시, `.import_linter_cache`는 자체
   `.gitignore`(`*`)로 커밋 제외돼 있어 git 추적에는 영향 없음.

**오류·막힌 점**: `pip install` 1차 시도 시 `/tmp`가 WSL2 tmpfs(3.9G)라
torch(843MB) 받다가 공간 부족 — `TMPDIR`을 디스크 쪽(`/home/a/.cache/pip-tmp`)
으로 돌려 재시도. 이후 catboost 문제로 2차 실패, 버전 업으로 최종 해결.

### 산출물 (5)
- `suvisdev/requirements.txt`(catboost 버전만 수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신 — catboost 백로그 완료 처리,
  titanic 테스트 4건 신규 백로그 등록.

---

### [6] silicon_valley → execsuite 앱 이름 변경 + labs/ 04·08 독립 실습 데모

**배경**: 사용자가 `apps/silicon_valley`를 `admin`으로 바꿔달라고 요청 —
이미 `suvis/app/admin/*`(어드민 대시보드)·`viewer`(RBAC)가 "admin"이라는
이름을 다른 의미로 쓰고 있어 충돌 우려를 짚고 대안을 물으니 `execsuite`로
확정. 이어서 "04·08은 mova/gildle에 안 쓰더라도 만들어둘 수 있냐"는 질문에,
`00_COMMON_conventions.md` §8의 "기법 먼저·용도 나중" 실패 사례를 짚고
독립 실습 영역으로 분리할 것을 확인받아 진행.

**수정/구현**:
1. **이름 변경**: `git mv apps/silicon_valley apps/execsuite`(102개 파일
   rename). 앱 내부 46개 `.py` 파일 + 외부 3곳(`main.py`, `alembic/env.py`,
   `.importlinter`)의 `silicon_valley`/`silicon-valley` 참조를 전부
   `execsuite`로 치환. `apps/ontology/_docs/star-craft-pipeline.md`의 앱
   목록, `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 완료 항목 라벨도 "구
   silicon_valley" 표기로 갱신(WORK_LOG 과거 기록은 당시 이름 그대로 유지).
   검증: `execsuite_router` 단독 import, `main.py` 전체 import 모두 성공,
   라우트(`/pdf/summarize`, `/langchain/chat` 등) 정상 확인.
2. **`suvisdev/labs/` 신설** — `apps/`의 어떤 앱과도 엮이지 않는 완전 고립
   영역(`main.py` 미등록, `.importlinter` 미포함). README에 명시한 원칙:
   Port(`ports.py`)는 참조 구현일 뿐 실제 편입 시 그 앱 컨벤션에 맞춰
   재배치, DTO는 도메인 중립이라 그대로 재사용 가능. GPU 없는 환경
   (m7i-flex.large)이라 학습 없이 사전학습 모델 추론만.
   - `pose_estimation/`(04·Atlas): YOLOv8n-pose(ultralytics, 3.3M 파라미터).
     `yolov8n-pose.pt`는 최초 실행 시 자동 다운로드(`*.pt`는 `.gitignore`에
     이미 있어 커밋 걱정 없음). 샘플은 ultralytics 기본 내장 `zidane.jpg`
     복사. 실행 검증 완료 — 샘플에서 사람 2명, 각 17개 COCO keypoint 정상
     출력.
   - `video_classification/`(08·Chronos): torchvision.models.video 중 실제
     파라미터 수 비교(s3d 8.3M < mc3_18 11.7M < r3d_18 33.4M)로 가장 가벼운
     `s3d`(Kinetics-400, 400개 레이블) 선택. 가중치는 torch hub가
     `~/.cache/torch/hub/checkpoints/`에 자동 캐시. 이 저장소엔 실제 동영상
     샘플이 없어 `samples/source.jpg`(ultralytics 기본 내장 `bus.jpg`)를
     확대하며 프레임을 늘린 합성 클립을 매 실행 즉석 생성(디스크 미저장)해
     분류 — 진짜 동작이 없으니 결과 자체보다 파이프라인이 CPU에서 학습 없이
     끝까지 도는지 확인용임을 demo 출력·README에 명시.

**검증**: 두 데모(`python -m labs.pose_estimation.demo`,
`python -m labs.video_classification.demo`) 실제 실행해 결과 확인.
`labs/` 전체 `ast.parse` 문법 검증 통과.

**오류·막힌 점**: 없음(이름 변경·labs 구현 모두 실행 검증까지 완료).
다만 이름 변경 후 회귀 확인용으로 돌린 `mova+dispatch+ontology` 전체
테스트는 ontology 쪽 비전 모델 로딩이 무거워 커밋 시점까지 계속 실행 중이었음
— `execsuite_router`/`main.py` 자체는 별도로 직접 import 검증을 마쳐 이름
변경 자체의 정합성은 확인됨.

### 산출물 (6)
- `apps/execsuite/`(구 `apps/silicon_valley/`, rename), `main.py`,
  `alembic/env.py`, `.importlinter`(수정).
- `suvisdev/labs/`(신규): `README.md`, `pose_estimation/`(`dto.py`,
  `ports.py`, `adapters/yolov8_pose_adapter.py`, `demo.py`,
  `samples/sample.jpg`), `video_classification/`(`dto.py`, `ports.py`,
  `adapters/s3d_adapter.py`, `demo.py`, `samples/source.jpg`).
- `apps/ontology/_docs/star-craft-pipeline.md`,
  `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(execsuite 라벨 갱신).

---

### [7] labs/ 03(시맨틱 분할) 추가 + mova 부팅 작업 ENABLE_MOVA_STARTUP 플래그

**배경**: [6]에 이어 "03도 04·08처럼 labs에 만들 수 있냐"는 질문에, 03은
04·08과 제외 사유가 다름을 짚었다 — 04·08은 순수 "용도 없음"이지만 03은
"용도(서울 보도 검출)는 있었는데 검증 데이터(OSM sidewalk 태그)가 없어서"
막힌 케이스. 사용자 확인 후 04·08과 동일 패턴으로 labs에 추가.

이어서 별개 요청: 이 프로젝트가 집(GPU/EXAONE)·AWS EC2(GPU 없음, Gemini)
두 환경에 배포되는데, mova의 부팅 자동 작업(TMDB 시드·랭킹/KOFIC 스케줄러 —
전부 Ollama 의존)이 EC2에서 연결 실패 WARNING을 계속 뿜는 문제를 코드
제거·브랜치 분리 없이 환경변수 플래그로 해결.

**수정/구현**:
1. **`suvisdev/labs/semantic_segmentation/`**(03·Loom) — 04·08과 동일 구조
   (`dto.py`/`ports.py`/`adapters/`/`demo.py`/`samples/`). 모델은
   torchvision.models.segmentation 4종 실측 비교(lraspp_mobilenet_v3_large
   3.2M < deeplabv3_mobilenet_v3_large 11.0M < fcn_resnet50 35.3M <
   deeplabv3_resnet50 42.0M) 후 가장 가벼운 `lraspp_mobilenet_v3_large`
   선택. Pascal VOC 21클래스 사전학습(도로/보도 클래스 없음 — 그래서 이
   데모가 막힌 용도인 "서울 보도 검출"과 구조적으로 무관함을 README에 명시).
   전처리가 짧은 변을 520px로 리사이즈해 마스크 크기가 원본과 달라짐을
   실측으로 확인 → DTO의 width/height는 원본이 아니라 실제 마스크 크기로
   정확히 반영. 가중치(~12.5MB)는 torch hub가 `~/.cache/torch/hub/checkpoints/`
   에 자동 캐시(리포에 안 남음, gitignore 불필요 확인). `samples/sample.jpg`
   (ultralytics 기본 내장 `bus.jpg`)로 실행 검증 완료(bus 31.0%, person
   12.2%, 배경 56.8% 정상 검출).
2. **`main.py`에 `ENABLE_MOVA_STARTUP` 플래그 추가** — `lifespan()` 안
   TMDB 카탈로그 시드·chat_trend 랭킹 스케줄러·KOFIC 박스오피스 스케줄러
   3개 try 블록을 `if _ENABLE_MOVA_STARTUP:`로 감싸고 `else:`에 "비활성화됨"
   info 로그 추가. 기본값 `true`(안 넣으면 기존 집 환경 동작 그대로).
   "HubRagInteractor 임베딩 ingest"는 별도 호출이 아니라 TMDB 시드
   (`ImportInteractor._persist_snapshots` → `_ingest_to_hub`) 안에 이미
   포함돼 있어 TMDB 시드 하나만 감싸면 같이 꺼짐 — 별도 지점 불필요.
   `seed_viewer_if_empty()`, Ollama 워밍업, 다른 앱(dispatch/execsuite/
   vision 등)의 부팅 작업은 건드리지 않음.

**부수 발견(건드리지 않음, 백로그 등록)**: `main.py`의 `seed_assistants_if_empty`
import(`mova.adapter.outbound.pg.assistants_pg_repository`)가 실제로
존재하지 않는 모듈 — 실제 파일명은 `platform_assistants_pg_repository.py`고
`seed_assistants_if_empty` 함수 자체가 코드베이스 어디에도 없음. 매 부팅마다
`ModuleNotFoundError`가 나서 기존 try/except로 조용히 삼켜지고 있던 기존 버그.

**검증**: 실제 DB/Ollama 없이 `verify_connection`/`create_tables`/
mova 시드·스케줄러 함수를 전부 mock으로 대체해 `lifespan()`의 분기만
격리 검증.
- `ENABLE_MOVA_STARTUP=false` → "비활성화됨" info 로그만, 3개 함수
  (`seed_catalog_if_sparse`/`run_chat_trend_scheduler`/
  `run_kofic_import_scheduler`) 전부 `called=False` 확인.
- 미설정(기본값) → 3개 함수 전부 `called=True`, 기존 로그(랭킹/KOFIC
  스케줄러 시작) 정상 출력 확인.

**오류·막힌 점**: [6]에서 백그라운드로 남겨둔 `mova+dispatch+ontology`
전체 회귀 테스트가 `openai/clip-vit-base-patch32`(Sentinel 이상탐지가
쓰는 CLIP 모델) Hugging Face Hub 다운로드에서 1시간 넘게 멈춰 있는 걸
발견해 프로세스 종료 — execsuite 이름 변경 자체는 별도 직접 import
검증으로 이미 확인이 끝난 상태라 이 hang은 이번 작업과 무관.

### 산출물 (7)
- `suvisdev/labs/semantic_segmentation/`(신규): `dto.py`, `ports.py`,
  `adapters/lraspp_adapter.py`, `demo.py`, `samples/sample.jpg`.
- `suvisdev/labs/README.md`(03 절 추가, §03 특수 사정 명시).
- `suvisdev/main.py`(`ENABLE_MOVA_STARTUP` 플래그 추가).

---

### [8] PROGRESS 백로그 마저 처리 — titanic 도메인 테스트 재작성 + seed_assistants 죽은 코드 제거

**배경**: [7]에서 남긴 백로그 중 진행 가능한 2건(titanic 테스트 4개 수집
실패, `seed_assistants_if_empty` import 버그) 처리.

**수정/구현**:
1. **titanic 테스트 4개** — 조사해보니 단순 이름 변경 드리프트가 아니라
   도메인이 재설계된 상태였음(관련 VO·엔티티·깨진 테스트 4개가 전부 같은
   커밋 `251ae61`(2026-07-08, "하위 파일 구조 통째로 업로드 성공")에서
   한꺼번에 들어옴 — 시간이 지나며 리팩터링된 게 아니라 애초부터 서로 안
   맞는 버전이 같이 업로드된 것). mova(`platform_users_vo.py` 등)·gildle
   (`route_edge.py` 등) 둘 다 "필드 하나당 VO 하나"가 아니라 "개념당 VO
   하나"로 묶는 방식을 쓰고 있어, 지금 titanic의 `PassengerIdentity`/
   `Survived` 방식이 이 프로젝트의 실제 컨벤션과 일치함을 확인(titanic은
   `.cursorrules`상 "기준선"). 사용자 확인 후:
   - `test_korean_ai_adapter.py` 삭제 — `titanic.adapter.outbound.llm.
     korean_ai_adapter`는 한 번도 만들어진 적 없고, 실제 구현은
     `tests/korean_ai.py`(프로토타입 스크립트)에 있으며 이미 통과 중인
     `test_korean_ai.py`가 커버 중인 중복 고아 테스트였음.
   - 나머지 3개(vo/entity/mapper) 삭제 후, 현재 도메인
     (`PassengerIdentity`/`Survived`/`Title`/`Gender`/`PassengerJackTrainer`/
     `PassengerJackTrainerMapper`) 기준으로 41개 테스트 새로 작성 — frozen
     불변성, 팩토리 검증(from_raw/from_name 성공·실패), DDD 동등성 규칙
     (passenger_id만으로 동등성 판단), DIP 어댑터 스왑(`SimpleNamespace`로
     실제 SQLAlchemy ORM 대신 같은 모양의 가짜를 넣어도 매퍼 결과가 같음을
     검증) 포함 — titanic이 기준선이라 mova/gildle이 참고할 모범 형태로
     작성.
   - **작성 중 실제 버그 발견**: `PassengerJackTrainer.summary()`와
     `PassengerJackTrainerMapper.to_orm_fields()` 둘 다 존재하지 않는
     `entity.identity.age`를 참조해 `AttributeError`(`PassengerIdentity`는
     title+gender만 갖고 age는 의도적으로 안 가짐 — docstring에 명시).
     `identity.age` 참조가 이 두 곳뿐임을 grep으로 확인 후 두 메서드 모두
     age 참조 제거로 수정.
   - 검증: `apps/titanic/tests` 44개 전부 통과(1개 ollama 마커 skip).
2. **`seed_assistants_if_empty` 죽은 코드 제거** — `AssistantsPgRepository`
   (실제 파일 `platform_assistants_pg_repository.py`)엔 `list_active`/
   `get_by_slug`만 있고 count/insert 메서드 자체가 없으며, 기본 시드
   데이터도 어디에도 없음 — 즉 이 시드 기능은 리네임된 게 아니라 애초에
   구현된 적이 없는 죽은 코드로 확인됨. 사용자 확인 후 `main.py`의 해당
   try/except 블록 통째로 제거. `ENABLE_MOVA_STARTUP=false`/미설정 두
   시나리오 mock 하네스로 재검증 — `assistants` WARNING이 완전히 사라지고
   플래그 동작은 그대로 정상임을 확인.

**검증**: `apps/mova/tests`+`apps/dispatch`+`apps/titanic/tests` 전체
91 passed, 1 skipped. `main.py` import 정상.

### 산출물 (8)
- `apps/titanic/domain/entities/passenger_jack_trainer_entity.py`,
  `apps/titanic/adapter/outbound/mappers/passenger_jack_trainer_mapper.py`
  (버그 수정).
- `apps/titanic/tests/domain/value_objects/test_passenger_jack_trainer_vo.py`,
  `apps/titanic/tests/domain/etitites/test_passenger_jack_trainer_entity.py`,
  `apps/titanic/tests/adapter/outbound/mappers/test_passenger_jack_trainer_mapper.py`
  (새로 작성), `test_korean_ai_adapter.py`(삭제).
- `suvisdev/main.py`(`seed_assistants_if_empty` 블록 제거).

---

### [9] LangGraph 하네스 문서 작성

**배경**: 사용자가 LangChain 선형 체인의 한계(분기·루프·상태관리 불가)와
LangGraph 도입 근거, Neo4j 기반 GraphRAG(지식그래프 구축·Text-to-Cypher·
하이브리드 검색) 자료를 제공하며, 시멘틱 라우터가 reasoning이 필요한
질문을 받았을 때 LangGraph를 활용하는 하네스 문서 작성을 요청. 이번엔
문서만 요청받아 코드는 건드리지 않음.

**작성**: `apps/execsuite/_docs/ranggraph-harness.md` — LangGraph 도입
근거, GraphRAG/Neo4j 활용법, 장단점, "이 프로젝트와의 접점" 절 작성.
접점 절은 실제 코드 기준으로 현재 상태를 짚음: `semantic_router_interactor`
(ontology)는 아직 `crud`/`rag`/`general` 3갈래뿐 "reasoning" 신호 없음,
`rangchain_chat_engine_repository.py`는 단일 선형 LCEL 체인, `langgraph`/
`neo4j-graphrag`는 `requirements.txt`에 설치만 돼 있고 코드베이스 어디서도
미사용, Neo4j 서버 자체가 `.env`에 `NEO4J_URI`/`NEO4J_USER` 없이 미배포
상태(`neo4j-hanress.md` 기존 확인 내용과 일치). 그 위에 제안 흐름(semantic_router
"reasoning 필요" 신호 추가 → LangGraph StateGraph의 retrieve→generate→
verify→재시도/종료 루프 → Neo4j 배포 후 GraphRAG로 retrieve 노드 보강)을
다이어그램과 단계적 도입 순서로 남김 — 실제 구현은 보류.

### 산출물 (9)
- `apps/execsuite/_docs/ranggraph-harness.md`(신규 작성).

---

## 2026-07-27

### [5] pdf_summary → pdf_loader 네이밍 환원 + LangChain 문서 2건

**배경**: 사용자가 [4]에서 만든 `pdf_summary_*` 네이밍을 원래 자신이 만들었던
파일명 `pdf_loader_interactor.py` 기준으로 되돌려달라고 요청.

**수정**: 13개 파일 `git mv`로 `pdf_summary_*` → `pdf_loader_*` 리네임,
클래스명도 동반 변경(`PdfSummaryUseCase`→`PdfLoaderUseCase`,
`PdfSummaryInteractor`→`PdfLoaderInteractor`, `PdfSummaryPort`→`PdfLoaderPort`,
`PdfSummaryRepository`→`PdfLoaderRepository`, `PdfSummaryOrm`→`PdfLoaderDocumentOrm`).
DB 테이블명 `pdf_summaries`→`pdf_loader_documents`(아직 실 DB 미적용 마이그레이션이라
새 리비전 없이 기존 파일 내용만 수정). 사용되지 않던 `PdfSummaryCommand` 죽은
코드 제거. `alembic/env.py` import, `adapter/inbound/api/__init__.py` 라우터
등록도 함께 갱신. import + 라우터 등록(`/pdf/summarize`) 재검증 완료.

**추가**: `apps/silicon_valley/_docs/rangchain-monigstar-strategy.md` —
LangChain 활용 사례(Morningstar 금융 인사이트 엔진) 문서화. 사용자가 실제
코드 구현은 원치 않아(이 저장소에 금융/시장 데이터 소스가 없음) 문서만 작성.

### 산출물 (5)
- 리네임된 13개 파일(경로는 위 커밋 diff 참고), `alembic/env.py`,
  `apps/silicon_valley/adapter/inbound/api/__init__.py`,
  `apps/silicon_valley/_docs/rangchain-monigstar-strategy.md`(신규).

---

### 작업 내용
- **03(Loom, 시맨틱 분할) 관문0 실측 조사** — "OSM 서울 walk가 보도를
  별도 way/태그로 갖는가(있으면 CV 불필요, 폐기)"를 Overpass API로 실측.
  용도 재정의 "보도 유무/폭" 기준으로 판정.
- 조사 중 사용자 지시로 **스코프 재조정**('폭' 폐기 → '유무'만, OSM
  `footway=sidewalk` 부분 데이터로 갈 수 있는지 재검토)까지 진행.

### 데이터 (Overpass API 실측, overpass-api.de)
- 서울 3개 지역 `sidewalk=*` 도로 속성 밀도:
  - 강남(37.495,127.025,37.515,127.050): 도로 903 / sidewalk 태그 11 (**1.2%**)
  - 성북 주거(37.585,127.010,37.605,127.035): 도로 1127 / sidewalk 태그 5 (**0.4%**),
    `footway=sidewalk` way 131, footway 전체 545, `width` 태그 5
  - 종로: footway 전체 922 (레이트리밋으로 일부 셀만)
- **커버리지 실측**(성북 소구역 37.590,127.010,37.605,127.030):
  도로 643 way/**96.85km** vs `footway=sidewalk` 25 way/**3.47km**
  → **보도길이/도로길이 = 0.04** (완전 양방향=2.0, 편측 완전=1.0 기준).
  도로 길이의 ~96%에 매핑된 보도 없음.

### 결론
- **관문0: "폐기(CV 불필요)" 불성립** — `sidewalk=*` 도로 속성은 사실상
  전무(0.4~1.2%), `width` 태그도 전무(재정의 용도 '폭'은 OSM에서 못 얻음).
- **스코프 재조정('유무'만)도 불가** — 두 각도 수렴: (1) 개념: OSM open-world라
  "매핑 없음 ≠ 보도 없음", "보도 없음→페널티" 규칙의 *부재* 신뢰 불가.
  (2) 실측: 커버리지 4% → 페널티가 도로 ~96%에 발화 = 노이즈.
- **최종: 03(Loom)을 04·08과 동급의 정식 '폐기/제외'로 확정(사용자 승인).**
  보도 신호 자체가 서울 OSM에 존재하지 않음이 실측 확인됨. 관문1(스트리트뷰+CV)은
  소비처 walk 그래프가 데모(4간선)이고 CV는 전 간선 이미지 필요 → 관문1
  이미지 비용 문제로 회귀.

### 오류·막힌 점
- Overpass 공개 서버(overpass-api.de) 과부하로 다수 쿼리 timeout/406/empty.
  미러(kumi.systems, private.coffee)도 무응답. curl+User-Agent로 서버 여유
  시점에만 성공 → 강남·종로 일부 셀 미수집(결론엔 영향 없음).

### 산출물
- 본 로그, `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(03 제외 확정 반영 —
  완료 목록 이동 + 진행 중 비움 + 감사표 갱신),
  `apps/ontology/_docs/03_semantic_segmentation_agent.md`(⛔ 제외 배너 + §5.4
  최종 확정) 갱신.

---

### [2] 어드민 dispatch/harvester 백엔드 인증 공백 차단

**배경**: PROGRESS 백로그 "어드민 백엔드 인증 공백" — `/api/v1/dispatch/*`·
`/api/ontology/harvester/*` 라우터에 `require_admin`이 없어 프론트 `AdminAuthGate`
우회 직접 호출 시 무인증 통과. `_ApiAuthMiddleware`는 `/docs`류만 막고 API
경로는 미들웨어 레벨 상시 공개임을 확인(인증은 라우터별 Depends로만).

**조사에서 드러난 것(구현 전 확인)**:
- 인증 스킴 2종 — auth 게이트웨이(RS256/roles/aud, `shared/security/token_verifier.py`)
  vs viewer 세션(HS256/role, `require_admin`). 어드민 UI가 실제로 보내는 건
  후자라 dispatch/harvester도 `require_admin`을 써야 일관.
- 어드민 UI의 dispatch/harvester 호출은 Next 프록시(`backendFetch`, Basic
  서비스 자격증명)를 거쳐 **사용자 세션 Bearer가 백엔드까지 안 감** → 백엔드
  가드만 추가하면 정상 호출도 401. 3계층 동시 수정 필요.
- import-linter: `require_admin`을 `core`가 아니라 "cross-app 토큰 검증 전용"
  리프 패키지 `shared`로 이동하는 게 계약(shared-independence)·구조에 맞음.
  실측 검증 결과 shared/spoke/auth 계약 모두 KEPT, 내 변경으로 인한 신규 위반
  0건(hub-independence BROKEN은 `core→viewer.orm` 기존 커플링, baseline 동일).

**수정·구현 (3계층)**:
1. 가드 이동: `viewer/dependencies/require_admin.py` → `shared/security/require_admin.py`
   (viewer 두 어드민 라우터 import 재지정, 원본 삭제).
2. 백엔드 가드 추가(어드민 UI 구동분만): dispatch `email/telegram/discord` POST(발송),
   `receive` GET·DELETE(수신함), ontology harvester `scrape/crawl/sites`. **`receive`
   POST(외부 인입)는 제외**.
3. 프론트 프록시 7개(`suvis/app/api/{dispatch,harvester}/*`)가 들어온 `Authorization`을
   `backendFetch`로 전달.
4. 프론트 클라 4개(mail/telegram/receive 페이지 + harvester-command-form)가 세션
   Bearer 첨부. `suvis/lib/suvis-session.ts`에 `authHeader()` 헬퍼 추가.

**검증**:
- import-linter(uv 일시 설치, PYTHONPATH=apps:.): 5 kept / 1 broken(기존) — baseline 동일.
- 백엔드 변경 파일 `py_compile` OK, 잔여 `viewer.dependencies.require_admin` 참조 0.
- 프론트 `npm run type-check` exit 0.
- 가드 런타임 실측: no-auth→401, 무효서명→401, 비관리자 role→403, 관리자→AdminPrincipal.

**남긴 것(후속 백로그)**: dispatch `watcher/judge/spam/adress` 라우터는 어드민 UI
미사용이라 이번 범위 밖. 각 엔드포인트가 외부 인입인지 개별 확인 후 보호 판단할 것
(검증 없이 가드 씌우지 말 것).

### 산출물 (2)
- BE: `shared/security/require_admin.py`(신규·이동), dispatch
  `email/telegram/discord/receive_router.py`, ontology `harvester_router.py`,
  viewer `admin_agents_router.py`·`admin_users_router.py`(import 재지정).
- FE: `suvis/app/api/{dispatch/email,dispatch/telegram,dispatch/discord,dispatch/receive,harvester/scrape,harvester/crawl,harvester/sites}/route.ts`,
  `suvis/app/admin/dispatch/{mail,telegram,receive}/page.tsx`,
  `suvis/app/admin/harvester/_components/harvester-command-form.tsx`,
  `suvis/lib/suvis-session.ts`.

---

### [3] alembic 마이그레이션 체인 누락 테이블 수정 + neo4j-graphrag 설치

**배경**: 사용자 보고 — 완전히 빈 DB에서 `alembic upgrade head`를 실행하면
`20260701_0001`에서 `relation "dispatch_adress" does not exist`로 실패.
지금까지는 backend startup의 `create_all()`이 테이블을 만들어줘서 드러나지
않았음. Google 로그인 500(새 DB에 `users`/`user_identities` 없음)도 같은
원인 의심.

**원인 조사**: `alembic/env.py`의 `target_metadata`(6개 Base) 대비 마이그레이션
체인의 `create_table` 호출을 전수 비교. `dispatch_adress`뿐 아니라 `users`,
`groups`, `admins`, mova 앱의 `movies`/`actors`/`characters`/`assistants`/
`collections`/`tags`/`chat`/`rankings`/`reviews`/`picks`/`watchlist`,
`titanic_passengers`, `vision_uploads`까지 전부 마이그레이션 체인에 CREATE가
없이 `create_all()`로만 존재해온 테이블이었음(alembic을 프로젝트 중간에
도입하면서 베이스라인 마이그레이션을 만든 적이 없었던 게 근본 원인).

**수정·구현**: 체인 맨 앞(20260604_0001보다 앞)에 베이스라인 마이그레이션
`20260604_0000_create_baseline_v1_tables.py` 신설, `20260604_0001`의
`down_revision`을 여기로 변경. 각 테이블은 뒤따르는 `41f584bfcb4e`(mova v2
스키마) 등이 적용되기 **직전 상태**로 생성하도록 설계(예: `movies.release_year`는
VARCHAR(8), `genres` 컬럼 존재, `characters.character_name` 없음,
`users.age_group` 있음) — 이후 리비전이 그 위에 그대로 ALTER 적용돼야 최종
스키마가 현재 ORM과 일치하기 때문. FK 의존 순서(groups→users→collections→
movies→actors→characters→assistants→tags→chat→rankings→reviews→picks→
watchlist) 고려해 테이블 순서 배치.

**검증**: 로컬엔 Docker/Postgres가 없어 EC2의 실제 `pgvector/pgvector:pg16`
이미지로 별도 테스트용 컨테이너(`suvisdev_migration_test_db`, 포트 15432,
기존 운영 DB 컨테이너와 별개)를 띄우고 SSH 터널로 연결. 백엔드 최소 venv
(`.venv_migration_test`, gitignore됨, sqlalchemy/alembic/psycopg/pgvector/
fastapi만 설치)로 완전히 빈 DB에 `alembic upgrade head` 실행 → 전체 10개
리비전 끝까지 성공, `alembic current`가 단일 head(`f3a7c9e21b6d`)로 확인.
`movies`/`users`/`characters`/`reviews` 최종 스키마를 `\d`로 대조해 현재
ORM과 일치 확인. 시행착오: `movies.release_year` VARCHAR→INTEGER 타입 변경
시 서버 디폴트(`''`)가 자동 캐스팅되지 않아 실패 → 베이스라인에서 해당
컬럼 디폴트를 제거해 해결.

**설계 의도(기존 배포 DB 영향 없음)**: 새 베이스라인은 체인의 새 루트로
삽입되므로, 이미 `alembic_version`이 어떤 리비전에든 스탬프돼 있는 기존
DB(운영 DB 포함)에는 적용되지 않음 — `None`에서 시작하는 완전히 빈 DB에만
적용된다.

**추가**: `requirements.txt`에 `neo4j-graphrag==1.18.0` 추가, 실제 백엔드
venv(`~/.venv`)에 설치·import 확인. `apps/silicon_valley/_docs/neo4j-hanress.md`에
그래프 데이터 모델 개념 + 연결 확인 절차(Python 드라이버/cypher-shell/브라우저)
문서화 — 실제 Neo4j 인스턴스는 아직 미배포(`.env`에 `NEO4J_PASSWORD`만 있고
`NEO4J_URI`/`NEO4J_USER` 없음, docker-compose에도 서비스 없음 확인).

### 산출물 (3)
- `suvisdev/alembic/versions/20260604_0000_create_baseline_v1_tables.py`(신규),
  `suvisdev/alembic/versions/20260604_0001_create_titanic_person_booking.py`(down_revision 변경),
  `suvisdev/requirements.txt`(neo4j-graphrag 추가),
  `suvisdev/apps/silicon_valley/_docs/neo4j-hanress.md`(신규).

---

---

### [4] PDF 업로드→추출→요약 파이프라인 (silicon_valley, **완료**)

**배경**: 사용자가 `neo4j-graphrag`의 `PdfLoader` 예시를 참조해 PDF 업로드→텍스트
추출→요약 파이프라인을 inbound router~outbound repository까지 완성형으로
요청. 헥사고날 컨벤션은 ontology `vision` 슬라이스(`vision_router.py` 등)를
그대로 참고.

**설계**: `pdf_summary_*` 네이밍. 포트 3개 — 추출(`PdfExtractorPort`, neo4j-graphrag
`PdfLoader` 어댑터), 요약(`PdfSummarizerPort`, 기존 `T1MidFakerOrchestrator`/exaone
Ollama 재사용), 저장(`PdfSummaryPort`, `NeoTheOneBase` + `get_mova_session_factory()`
— vision_uploads와 동일 패턴). `ensure_titanic_tables()` 같은 create_all() 폴백은
**의도적으로 안 씀**(오늘 [3]에서 고친 문제 재발 방지) — 대신 정식 alembic
마이그레이션(`20260727_0001_create_pdf_summaries`, head `f3a7c9e21b6d` 뒤에 추가)로
테이블 생성, `alembic/env.py`에 ORM import 등록 완료.

**완료된 파일**:
- `alembic/env.py`(pdf_summary_orm import 추가)
- `alembic/versions/20260727_0001_create_pdf_summaries.py`(신규 — 아직 미검증)
- `apps/silicon_valley/adapter/outbound/orm/pdf_summary_orm.py`
- `apps/silicon_valley/app/dtos/pdf_summary_dto.py`
- `apps/silicon_valley/app/ports/input/pdf_summary_use_case.py`
- `apps/silicon_valley/app/ports/output/pdf_summary_extractor_port.py`

**추가 완료된 파일**: `pdf_summary_summarizer_port.py`, `pdf_summary_repository_port.py`,
`app/use_case/pdf_summary_interactor.py`(자리표시자 `pdf_loader_interactor.py`는
삭제), `adapter/outbound/extractor/pdf_summary_pdfloader_extractor.py`(temp file로
`PdfLoader.run(filepath=Path)`에 전달), `adapter/outbound/llm/pdf_summary_ollama_summarizer.py`
(T1MidFakerOrchestrator 재사용, 입력 12000자 상한), `adapter/outbound/repositories/pdf_summary_repository.py`,
`adapter/inbound/api/v1/pdf_summary_router.py`(`POST /pdf/summarize`), `dependencies/pdf_summary_provider.py`,
`adapter/inbound/api/__init__.py`에 등록(최종 경로 `/api/v1/pdf/summarize`).

**검증**: `~/.venv`(neo4j-graphrag 포함)에서 라우터 import + `/pdf/summarize`
등록 확인, 마이그레이션 파일 `py_compile` OK, ORM 테이블 컬럼 확인. **미검증**:
실제 빈 DB에 `alembic upgrade head`(간단한 단일 create_table이라 위험 낮음,
필요시 EC2 임시 컨테이너로 재검증 가능), Ollama 서버 연동 실사용 테스트.

### 산출물 (4)
- 위 파일 전체. 커밋 전.

---

## 2026-07-24

### 작업 내용
- 06(Sentinel, 이상 탐지) **H4(추론 어댑터) + H5(HTTP API + MCP tool) 구현**
  — H3까지의 방향 전환(CLIP 제로샷 + Laplacian variance)을 실제 코드로
  반영하고 MCP tool까지 노출.
- **[1순위 백로그 해결] vision app→adapter DIP 위반 + 순환 import 근본 수정**
  — H6에서 드러난 순환(테스트만 우회 중)을 제거.
- **[2순위 (c)+(d)] S3 경로 Tank 단일화 + boto3 기본 자격증명 체인 전환.**
- **03(Loom, 분할) 이미지 수집 경로 조사 — 종료조건 합의(읽기 전용 분석).**
- 커밋 워크플로우 훅 설정 — 커밋 요청 시 두 추적 문서를 먼저 갱신하도록
  리마인더(공유용 `.claude/settings.json`, 커밋됨).

### 수정/구현

**1) 06 Sentinel H4**
- 미결정 사항(포트 1개 vs 2개) 확인 후 **포트 1개 통합**으로 확정하고 진행.
- `app/dtos/anomaly_detection_dto.py`: `AnomalyResult`를 PatchCore 가정
  (`anomaly_score`/`is_anomaly`/`heatmap_b64`)에서 `is_poster`/
  `poster_confidence`/`is_blurry`/`sharpness_score`로 재설계.
- `adapter/outbound/resource_adapters/sentinel_anomaly/sentinel_anomaly_adapter.py`
  (신규): CLIP 제로샷(`openai/clip-vit-base-patch32`, 임계값 0.5)과
  Laplacian variance(256x256 정규화, 임계값 345.77)를 한 어댑터에서 순서대로
  호출. CLIP은 `echo_sentiment_adapter.py`와 동일하게 호출당 로드→추론→언로드.
- `dependencies/anomaly_detection_provider.py`(신규), port/interactor
  docstring을 PatchCore→CLIP/Laplacian으로 갱신.
- `test/test_sentinel_anomaly_adapter.py`(신규, `@pytest.mark.gpu`) —
  `test/good`·`test/blur` 샘플로 포트→VO 반환 검증.

**2) 06 Sentinel H5**
- `adapter/inbound/api/v1/anomaly_detection_router.py`(신규):
  `image_classifier_router.py` 패턴, `POST /sentinel/detect`(전체 경로
  `/api/vision/sentinel/detect`), `UploadFile` 입력.
- `adapter/inbound/mcp/anomaly_detection_mcp_server.py`(신규):
  `image_classifier_mcp_server.py` 패턴, `detect_anomaly(image_b64) -> dict`
  tool이 HTTP로 라우터 호출.
- `adapter/inbound/api/__init__.py`: `vision_router`에
  `anomaly_detection_router` 등록.
- `scripts/test_mcp_sentinel_client.py`(신규): stdio MCP 클라이언트로 tool
  목록 + 호출 검증.
- 검증: 백엔드 리빌드+재기동 후 `app.routes`에 경로 등록 확인,
  MCP tool 호출 2회 성공(good→`is_poster:true`, blur→`is_blurry:true`),
  VRAM 2863→3014MB(호출당 +30~120MB로 CLIP 가중치 누적 아님 → 로드-언로드
  정상), lora-server 정상. GATE_H5_PASS.

**3) 06 Sentinel H6 — `/vision/upload` 업로드 게이트 통합**
- 용도 확정(소거법): harvester=텍스트만 수집, TMDB=poster_url 참조(항상 포스터),
  lora-server=텍스트 생성기, Prisma(05)=미구현 → 이미지 입력이 불확실한 유일한
  경로가 `POST /vision/upload`라 여기에 게이트로 붙임(근거 추적은 이 세션 대화).
- `app/dtos/vision_dto.py`: `VisionUploadResponse`에 `poster_confidence`/
  `sharpness_score`/`is_poster_warning` 추가(기본값 있어 repo 무변경).
- `app/use_cases/vision_interactor.py`: `AnomalyDetectionPort` 주입,
  `upload_image`가 `to_thread`로 detect → 블러 하드 게이트(임계값 345.77 미달
  `ValueError`→400) + 포스터 소프트 플래그(`poster_confidence`<0.5 경고, 차단 안
  함). 임계값을 interactor가 raw 값으로 소유(어댑터 부울은 /sentinel·MCP용).
- `dependencies/vision_provider.py`: `get_anomaly_detection_port` 재사용 주입.
- 검증: `test/test_vision_upload_sentinel_gate.py`(gpu, fake VisionPort+실제
  Sentinel) 3경로 PASSED — good(통과+저장), blur(하드 반려+미저장),
  cast_0001(소프트 플래그+저장). 앱 import 무결성(`main` 7 vision routes) 확인,
  VRAM 3034→3034 안정.
- 동기 지연(~20s CLIP 로드)·VRAM 경합은 감수(어드민 간헐 경로, to_thread, CLIP
  경량) — 근거 `06 §6.9`.

**4) AWS S3 매니저(Tank) 신설** — 향후 AWS 이전(이미지/객체를 S3 URL로
전달, ontology 00_COMMON §6) 대비. mova/gildle 도메인과 무관한 인프라 작업.
- `core/matrix/aws_tank_s3_manager.py`(신규): `Tank` 클래스. IAM 액세스 키를
  하드코딩하지 않고 Keymaker에서 받아 boto3 S3 클라이언트 생성. 키 없으면
  `ready=False` + 클라이언트 접근 시 graceful `RuntimeError`. 메서드:
  `list_buckets`/`upload_bytes`/`download_bytes`/`generate_presigned_url`.
  모듈 싱글턴 `tank`/`get_tank()`(Keymaker 패턴).
- `core/matrix/vauly_keymaker_secret_manager.py`: AWS 자격증명·리전·버킷을
  Keymaker가 단일 관리하도록 `aws_access_key_id`/`aws_secret_access_key`/
  `aws_region`/`vision_s3_bucket` 속성 추가. Tank는 `os.getenv`를 직접 읽지
  않고 이 값을 받아 씀(사용자 요청으로 os.getenv 직접 접근 → Keymaker 경유로
  리팩터).
- `.env.example`: AWS IAM 액세스 키 블록 추가(`AWS_ACCESS_KEY_ID`/
  `AWS_SECRET_ACCESS_KEY`/`AWS_REGION`/`VISION_S3_BUCKET`). 변수명은 기존
  `vision_s3_repository.py`(boto3 기본 자격증명 체인)와 맞춰 재사용.
- 검증: 컨테이너에서 import + graceful degradation(키 없을 때 `ready=False`,
  클라이언트 접근 에러) 확인. 실 버킷 연동은 키 주입 후 별도.

**5) [1순위 백로그] vision app→adapter DIP 위반 + 순환 import 근본 수정**
- 위반: `app/ports/input/vision_use_case.py`·`app/use_cases/vision_interactor.py`가
  어댑터 pydantic 스키마 `VisionIntroduceSchema`를 인자 타입으로 임포트 →
  `vision_use_case→vision_schema→api/__init__→vision_router→vision_use_case` 순환.
- 수정: 포트·interactor를 앱 DTO `VisionIntroduceQuery`(이미 존재, repository 포트도
  이걸 받음)로 바꾸고, schema→query 변환을 어댑터 계층(`vision_router`)으로 올림.
  interactor는 query를 repository로 직행(변환 제거). dead가 된 `vision_schema.py`
  삭제(`schemas/__init__` 빔, 다른 참조 없음 확인).
- H6 테스트에서 넣었던 우회(`import ontology.adapter.inbound.api` 선로드) 제거 —
  이게 통과한다는 게 근본 해결의 증거(테스트 로드 경로 = 프로덕션 경로).
- 검증: 이전에 순환으로 실패하던 `import ontology.dependencies.vision_provider`가
  성공, `from main import app` 부팅(vision routes 7), H6 게이트 3/3 PASSED(우회 없이).
- semantic_router_dto도 어댑터 스키마 참조하나 `TYPE_CHECKING`/지역 임포트라 런타임
  순환 없음 → 이번 범위 밖(DIP 냄새만, 위험 아님).

**6) [2순위 백로그 (c)+(d)] S3 경로 Tank로 단일화 + 기본 자격증명 체인 전환**
- 배경: `VisionS3Repository`가 자체 `boto3.client`(기본 체인), Tank는 명시적 키
  전달 — S3 경로가 둘로 갈리고 자격증명 전략도 반대. 사용자 결정: (c)+(d) 함께,
  기본 체인으로 통일.
- Tank(d): `_access_key`/`_secret_key`/`ready`/키 전달 제거 →
  `boto3.client("s3", region_name=...)`만 사용(기본 체인). region/bucket은 계속
  Keymaker에서. boto3 기본 체인이 로컬은 `.env`가 os.environ에 실은 AWS_* env를,
  EC2는 인스턴스 IAM Role을 집는다 → 단일 경로.
- VisionS3Repository(c): 자체 boto3/os 제거, `get_tank()` 위임. 키 네이밍·
  content_type만 도메인 로직으로 남기고 put은 `tank.upload_bytes`(to_thread).
- Keymaker: `aws_access_key_id`/`secret` 속성은 vestigial(아무도 안 읽음, 기본
  체인이 env 직접 집음)로 남김 + 주석 정정. `.env.example`에 EC2 IAM Role이면
  키 비워도 된다는 노트 추가.
- 검증: `tank.client`가 명시적 키 없이 S3 클라이언트 빌드(전엔 ready=False로
  raise), `VisionS3Repository`가 Tank 싱글턴에 위임(save_image→Tank 버킷 체크
  RuntimeError 도달로 위임 경로 증명), `from main import app` 부팅 OK. 실 업로드는
  AWS 연결(버킷+키) 후 확인.

**7) 03(Loom, 분할) 이미지 수집 경로 조사 — 종료조건 합의(코드 변경 없음, 읽기 전용)**
착수 전 종료조건부터 합의하기로 하고 03 문서(§5)·gildle 라우팅 코드
(`route_weight_calculator.py`)를 읽어 3가지를 정리:
- **용도/소비처**: 재정의 스코프는 "보도 유무/폭"(계절 무관 구조 신호, 결빙은
  §5.1에서 기각). 소비처는 실재 — `RouteWeightCalculator.calculate_edge_weight`가
  `_near_hazard`(20m 근접→6배 페널티) 패턴처럼 "보도 없음/좁음"을 상시 페널티로
  얹으면 됨. **단 구멍 2개**: (a) 소비 그래프가 데모(`sample_walk_graph.json` 4간선),
  OSM 운영 미구현(코드에 osmnx 없음 확인). (b) OSM walk 태그가 보도를 이미 주면
  CV 불필요(중복). → "용도 없음"이 아니라 "CV가 필수 수단이 아닐 수 있음".
- **이미지 최소 조건**: 지상 스트리트뷰(항공 아님 — 가로수 canopy 폐색), 유효크롭
  ≥512px, 지오태그 정밀도 ≤~10~20m(간선 매칭 반경), 주간·비폐색(구조라 계절 무관,
  단 적설 배제), **커버리지=라우팅 그래프 전 간선(킬러 조건)**. 실질 판정 기준은
  해상도가 아니라 커버리지×합법성×비용.
- **폐기 수용**: 04·08 제외 선례와 동급으로 '폐기'를 정식 결론으로 수용하기로 제안
  (쓸 소스 없음 / OSM으로 충분함 둘 다 유효 종료).
- **합의한 관문 순서**: 관문0(OSM 보도 태깅으로 CV 불필요한지, 가장 쌈, 먼저) →
  관문1(스트리트뷰 소스 ToS/과금/커버리지) → GO는 둘 다 통과+최소조건 만족 시만.
- **상태**: 사용자 종료조건 합의 대기 → 합의되면 관문0부터 착수(아직 소스 조사 미착수).

**8) 커밋 워크플로우 훅 설정**
- 규칙 확정: 커밋 **요청 시** WORK_LOG(오늘 작업)·PROGRESS(완료 삭제·남은 작업)를
  **먼저 갱신 후** 문서+코드 함께 커밋(커밋 후 갱신은 순서가 거꾸로라 폐기).
- `.claude/settings.json`(공유용, 커밋됨)에 `UserPromptSubmit` 훅 — 프롬프트에
  `commit|커밋` 있으면 문서 먼저 갱신 리마인더 주입. grep 기반(호스트에 jq 없음).
  개인 permissions는 `.claude/settings.local.json`(전역 gitignore)에 유지.
- 검증: python3로 두 파일 JSON 유효성·훅 매칭/비매칭 재현, 이번 세션에서 실제
  발화 확인(이 프롬프트에 리마인더 주입됨).

### 오류·막힌 점
- **로컬 `.venv`/`.venv-exaone`에 pytest/opencv 없음** — 이 프로젝트의 실제
  런타임 의존성(`transformers==4.47.1`, `opencv-python`, `pytest`)은
  `requirements.txt` 기반으로 `suvisdev-backend-1` 도커 이미지에만 있고,
  compose에는 코드 전체가 아니라 `datasets`·`resources/crawled`만 바인드
  마운트돼 있어 새 파일이 컨테이너에 자동 반영 안 됨 → `docker cp`로
  변경/신규 파일 6개를 컨테이너에 직접 복사해 그 안에서 pytest 실행,
  둘 다 PASSED. VRAM은 호출 전후 2879MB로 동일(로드-언로드 정상 확인),
  lora-server(`:8200/health`) 정상 유지.
- **기존 순환 임포트 노출(H6 테스트)** — `app/ports/input/vision_use_case.py`가
  어댑터 계층 `adapter/inbound/api/schemas/vision_schema.py`를 임포트(app→adapter
  DIP 위반)해서, `vision_interactor`를 `api/__init__` 애그리게이터보다 먼저
  임포트하면 `vision_use_case → vision_schema → api/__init__ → vision_router →
  vision_use_case(partial)` 순환이 터진다. 프로덕션은 `main.py` 임포트 순서
  덕에 회피 중(앱 import 무결성 확인함). H6 테스트는 `api` 애그리게이터를 선
  로드해 우회. **근본 수정(포트가 어댑터 스키마를 안 보게)은 백로그 — 아래.**

### 산출물
- 문서 갱신: `apps/ontology/_docs/06_anomaly_detection_agent.md` §6.7(H4)·
  §6.8(H5)·§6.9(H6) 신규, `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 06을 H0~H6
  완료로 갱신(완료 목록 이동, 감사표·우선순위 반영).
- 백엔드 이미지 리빌드(H5 코드 반영) — `suvisdev-backend-1` 재기동됨.
- 커밋/푸시/머지(모두 main 반영): Sentinel H4·H5 `df5a56b`, S3 매니저(Tank)
  `53bd4de`, Sentinel H6 `2da0762`, 블러 상수 주석+백로그 `e91d9c7`, Keymaker
  계약+시크릿 감사 `9994ed7`, vision DIP 순환 수정 `6098955`, S3 Tank 단일화+
  기본 체인 `dc9afbd`, 03 조사 기록+진행 메모 프루닝 `b8628bb`, 커밋 워크플로우
  훅(.claude/settings.json)+WORK_LOG(이 커밋).

### 백로그 (우선순위 조정 — 2026-07-24)

**[1순위] app→adapter DIP 위반 + 순환 import — ✅ 해결(2026-07-24, 위 수정/구현 5)**
- `vision_use_case`/`vision_interactor`가 어댑터 스키마 `VisionIntroduceSchema`를
  받던 것을 앱 DTO `VisionIntroduceQuery`로 교체, 변환을 `vision_router`로 올림,
  dead `vision_schema.py` 삭제. 테스트 우회 제거 후에도 통과 = 근본 해결.

**[2순위] 시크릿·S3 접근 경로 정리 (묶음)**

시크릿 관리 현황 감사 결과, Keymaker(`vauly_keymaker`)는 단일 관문이 아니라
여러 시크릿 접근 경로 중 하나였다(GEMINI/TMDB/KOFIC/AWS/DATABASE_URL만 관리,
나머지 JWT·OAuth·API_USERNAME 등은 각 app이 `os.getenv`로 직접 읽음).

**방향 결정 — Keymaker 전면 통합은 채택 안 함.** core/matrix가 TMDB_API_KEY·
JWT 키 같은 앱별 시크릿을 알게 되면 core → apps 역방향 의존이 생겨 헥사고날
원칙에 어긋난다. 나중에 정리한다면 core는 `SecretProvider` 인터페이스(메커니즘)
만 갖고, 키 목록은 각 app의 Settings가 소유하는 방향으로 간다.

- (a) TMDB/KOFIC 코드 중복(ontology `api_keys.py` / mova `keymaker.tmdb_api_key`):
  둘 다 같은 env 이름을 읽어 **값 divergence 위험 없음(상태 중복 아니라 코드
  중복)**, 앱별로 하나씩 가진 건 "app이 자기 키를 소유" 목표 방향과 오히려 일치.
  지금 mova에 accessor를 신설하면 pydantic-settings 이관 때 또 뜯게 됨 →
  **app별 Settings(pydantic-settings) 도입 시 mova·ontology 키 접근을 함께 이관.
  현재는 무해. 단독 실행 금지.**
- (b) `load_dotenv` 3곳 감사 완료(2026-07-24): **세 곳 모두 같은 파일**
  (`suvisdev/.env`) 로드 — vauly_keymaker·grid_oracle는 `override=True`,
  alembic/env.py는 `override=False`. 파일이 같아 값 분기는 없으나 override
  플래그가 불일치. **단일화 안 함** — Keymaker의 임포트 시 self-load는 scripts/를
  떠받치는 **기능(계약)**이라 제거 대상 아님(Keymaker docstring에 계약 명시함).
  override 불일치는 인지만 하고 현행 유지.
- (c)+(d) **✅ 해결(2026-07-24, 위 수정/구현 6)**: S3 경로를 Tank로 단일화 +
  Tank를 boto3 기본 자격증명 체인으로 전환. `VisionS3Repository`가 자체
  `boto3.client`를 버리고 Tank에 위임, Tank는 명시적 키 전달을 제거하고
  `region_name`만 지정 → 로컬(.env 키)·EC2(IAM Role)가 단일 경로로 처리됨.

**[유지] 하위 우선순위**
- 블러 임계값(345.77)은 포스터 분포 보정값이라 저디테일 비포스터(backdrop 등)가
  미달해 하드 반려될 수 있음 — 업로드 게이트 용도상 허용(현행 유지).
- Sentinel 소프트 플래그의 **저장 지속화 + 어드민 오버라이드 엔드포인트** — 저장
  계층(S3 배선인데 AWS 미연결, DB 폴백 미배선) 정리 후 처리(현행 유지).

---

## 2026-07-23

### 작업 내용
- 06(Sentinel, 이상 탐지) H3 디버깅 이어서 진행 — 이전 세션이 도중에
  끊긴 상태(포스터/노이즈/회색 점수 순서가 정보량 순서와 일치한다는 관찰까지만
  하고 중단)에서 재개.
- PatchCore(anomalib) 기반 접근을 근본 원인까지 추적 → 실패로 판정 →
  CLIP 제로샷 + Laplacian variance로 방향 전환.
- 02~08 나머지 비전 에이전트 전체에 대해 "용도/데이터/하드웨어" 적합성
  사전 감사(06의 실패에서 얻은 교훈 적용).
- VRAM 점유 정책 확정(실측 기반).
- 관련 문서·재개 메모 정리, git 커밋/푸시/머지 2회.

### 수정/구현

**1) additive/subtractive anomaly 원인 규명**
- `scripts/diagnose_sentinel_per_defect.py`(기존) 재실행 → normal/blur/black_bar/watermark
  그룹별 AUROC 분해(blur 0.573, black_bar 0.510, watermark 0.484).
- `scripts/diagnose_sentinel_feature_norm.py`(신규) — memory bank 진입 전
  patch embedding의 L2 norm을 그룹별로 추출해 NN-distance와 대조. blur만
  전역·균일하게 정상 분포 영역을 벗어나 잘 잡히고, black_bar(국소)·watermark
  (저강도)는 거의 안 잡힌다는 걸 확인(`06_anomaly_detection_agent.md` §5.3).

**2) "이상=포스터가 아닌 이미지" 재정의 시도 1차 (실패)**
- `scripts/prepare_sentinel_nonposter_dataset.py`(신규) — TMDB API로
  backdrop(예고편 스틸)·cast profile(인물 사진)·대체 포스터(textless/
  비주력 언어판) 수집.
- 사용자 지적 반영: (a) 종횡비 누출 방지 — Resize(256,256)이 종횡비를
  무시해 16:9 backdrop이 포스터보다 훨씬 심하게 찌그러지는 문제 →
  저장 전 전부 2:3 center crop. (b) 라벨 오류 — textless/비주력 언어판은
  TMDB 공식 포스터라 정상인데 처음에 "hard negative"로 잘못 라벨링 →
  `test/alt_poster_control`(위양성 대조군, 정상)로 재정의.
- `scripts/diagnose_sentinel_nonposter.py`(신규) — good/non_poster_easy/
  alt_poster_control 3그룹 점수 분포 + AUROC.
- 결과: AUROC 0.4429, 부트스트랩 95% CI [0.314, 0.566] → 0.5 포함 →
  "랜덤 이하"가 아니라 **"신호 없음"**(통계적으로 구분 불가). 수동
  pairwise 재계산으로 sklearn 라벨 극성 버그 아님도 확인.
- 결론: patch-level 텍스처 비교는 "포스터냐 아니냐"라는 전역적·구성적
  질문에 구조적으로 안 맞음 → 이 접근 기각.

**3) 방향 전환 — CLIP 제로샷 + Laplacian variance**
- `scripts/diagnose_sentinel_clip_poster_classifier.py`(신규) —
  `openai/clip-vit-base-patch32` 제로샷, 파인튜닝 없이 기존 라벨셋으로
  즉시 검증 → AUROC 0.8844(PatchCore 0.44 대비 압도적 개선).
- `scripts/compute_sentinel_blur_threshold.py`(신규) — 정상 포스터
  232장(256x256 정규화)의 Laplacian variance 하위 5퍼센타일 = 345.77.
  합성 블러 25장 전부(100%) 임계값 아래로 분리.
- PatchCore/anomalib은 Phase A(MVTec bottle AUROC 1.0, 파이프라인 정합성
  검증)만 근거로 남기고 포스터 도메인에서는 기각.
- 전체 근거를 `apps/ontology/_docs/06_anomaly_detection_agent.md` §5~§6.6에
  기록. H4(포트 통합)는 아직 미착수 — 상세 다음 단계는
  `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` §1 참고.

**4) 02~08 적합성 감사**
- mova(포스터 1장/영화 + 텍스트뿐)·gildle(이미지 자체가 없는 지오/테이블
  도메인) ERD·코드를 직접 확인해 용도/데이터/하드웨어 3항목 판정.
- 04(Atlas, 자세 추정)·08(Chronos, 영상 분류) — mova/gildle 어디에도
  용도가 없어 **제외**. 해당 문서 상단에 배너만 추가(내용 삭제 안 함).
- 03(Loom, 분할) — gildle `HazardZone`(결빙구역)과 엮는 재정의 검토.
  결빙 자체는 Cityscapes/Mapillary에 클래스가 없어(계절성 현상 vs 구조적
  클래스) 기각. 대안(보도/차도 구조 분할)은 라우팅 반영 방법은 명확하나
  이미지 수집 경로(gildle의 Kakao 연동은 지오코딩뿐, 로드뷰 API 아님)가
  미확정이라 **보류**(착수 안 함). `03_semantic_segmentation_agent.md` §5.
- 02(Argus)·05(Prisma) — 용도 위험/불확실이라 보류(제외는 아님).
- 감사 표 전체를 `00_COMMON_conventions.md` §8에 기록.

**5) VRAM 점유 정책 확정**
- `nvidia-smi`, `ollama ps`, `systemctl --user status lora-server`로
  실측. `00_COMMON_conventions.md` §1.1에 정책 명문화(아래 오류 항목 참고).

**6) 재개 메모 정리**
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 전면 재작성 — 완료된 항목(어드민
  대시보드, 01, 07)은 상세 삭제하고 위치만 남김, 06 H4의 다음 할 일은
  파일 단위로 구체화(DTO 재설계 필요성, 미결정 설계 질문 등).

**7) 작업 일지 체계 신설**
- 이 파일(`_docs/WORK_LOG.md`) 신설 — 날짜별 상세 작업 기록(재개 메모와
  역할 분리: 재개 메모=현재 상태 요약, 작업일지=그날 있었던 일 상세).
- `CLAUDE.md`에 규칙 추가: **세션이 끝나기 전에 이 파일에 기록**. 중간에
  "커밋 시점을 트리거로" 잠깐 바꿨다가 사용자가 다시 세션 종료 기준으로
  정정(최종: 세션 종료 트리거).

### 오류·막힌 점

- **정규화 클리핑 버그 재발**: `diagnose_sentinel_nonposter.py` 1차 작성 시
  `PostProcessor(enable_normalization=False)`를 빠뜨려 min-max 정규화가
  다시 켜진 채로 실행 → score가 0.98~1.000에 몰려 AUROC가 0.4369라는
  의미 없는 값이 나옴(§5.1~5.2에서 이미 확인했던 문제인데 신규 스크립트에
  재도입). `PostProcessor(enable_normalization=False)` 추가 후 재실행해
  0.4393(raw score 기준)으로 정정 — 결론(신호 없음)은 안 바뀜.
- **TMDB `include_image_language` 필터 버그**: 대체 포스터(altlang) 수집 시
  API 요청 자체를 `include_image_language: "null,en,ko"`로 제한해놓고
  "en/ko가 아닌 포스터"를 찾으려 해서 항상 0건. `ja,zh,fr,de,es,it,ru`
  추가해 해결(15/15 확보).
- **정상 포스터 카운트 assert 실패**: `compute_sentinel_blur_threshold.py`
  초안이 `tmdb-*.jpg` 패턴만 찾아 190장(실제는 232장, 일부는 슬러그
  파일명이라 tmdb- 접두사 없음)에서 assert 실패. 패턴을 `*/*/*.jpg`로
  넓혀 해결.
- **컨테이너/호스트 데이터 비동기화**: `apps/ontology/resources/sentinel_poster`가
  컨테이너 안에서는 bind mount가 아니라 이미지 빌드 시점 복사본이라는 걸
  뒤늦게 발견 — 컨테이너 안에서 생성한 `non_poster_easy`/`alt_poster_control`가
  호스트에 자동 반영 안 됨. `docker cp`로 양방향 수동 동기화(스크립트는
  host→container, 데이터 산출물은 container→host)하는 방식으로 우회.
  디렉토리 이름을 `non_poster_hard`→`alt_poster_control`로 바꿀 때도 호스트에
  먼저 `mv`했다가 파일이 없어서 실패 → 컨테이너에서 먼저 rename 후
  `docker cp`로 새로 가져오는 순서로 정정.
- **`nvidia-smi` 계측 불안정**: 같은 세션 안에서 같은 `lora-server` 프로세스에
  대해 290MB(유휴)와 7975~7988MB(피크 직후로 추정)로 크게 다른 값이 나옴 —
  재시작 로그는 없어서 WSL2 GPU 패스스루 계측 문제로 판단. VRAM 정책에
  "free 수치만 믿지 말 것" 명시.

### 데이터

- `apps/ontology/resources/sentinel_poster/` 구성(2026-07-23 기준):
  - `train/good`: 190장(정상 포스터, 기존)
  - `test/good`: 42장(정상 포스터, 기존)
  - `test/blur`·`test/black_bar`·`test/watermark`: 각 25장(합성 손상, Phase B 잔존 — 스코프 제외됐지만 삭제 안 함, blur 임계값 검증용으로 재사용)
  - `test/non_poster_easy`: 40장(신규, backdrop 20 + cast profile 20, TMDB, 2:3 center crop)
  - `test/alt_poster_control`: 30장(신규, textless 15 + 비주력 언어판 15, TMDB, 2:3 center crop)
  - 소스: `apps/ontology/resources/genre_classifier_train`(232장)의 TMDB id 190개 재사용

### 산출물

- 커밋 `bac5565` — 06 additive/subtractive 원인 규명 + 범위 재정의(스크립트 6개 신규, 데이터셋 확장, 문서 §5~§6)
- 커밋 `e420d3f` — 02~08 감사 반영(00_COMMON §1.1/§8, 03/04/08 문서 수정)
- 둘 다 `suvisdev` → `main` fast-forward 머지 + 푸시 완료
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 전면 갱신(미커밋, 사용자 확인 대기)
