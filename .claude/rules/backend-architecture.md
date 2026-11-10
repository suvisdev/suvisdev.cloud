---
paths:
  - "suvisdev/apps/**/*.py"
  - "suvisdev/core/**/*.py"
  - "suvisdev/shared/**/*.py"
  - "suvisdev/.importlinter"
---

# 백엔드 아키텍처 — 헥사고날·클린 + 스타 토폴로지 (강제되는 것만)

설계 원문(SSOT)은 `suvisdev/CLAUDE.md` §C(헥사고날·클린 레이어), §O(모듈러 모놀리식·스타 토폴로지),
§P(DDD는 필요한 곳에만)다. 이 파일은 그중 **검사로 강제되는 규칙**과 위반 시 대응만 적는다.

## 검사로 강제되는 규칙 (`suvisdev/.importlinter`)

| 계약 | 규칙 | 근거 |
|---|---|---|
| `hub-independence` | 허브 `ontology`는 어떤 스포크도 import하지 않는다 | §O.2 |
| `spoke-independence` | 스포크끼리 직접 import하지 않는다(교환은 허브 경유) | §O.3 |
| `domain-purity` | 모든 앱의 `domain`은 어느 앱의 `app`·`adapter`도 import하지 않는다 | §C.1·§P |
| `app-no-outbound` | `app`(유스케이스)은 `adapter.outbound`(DB·LLM·HTTP 구현)를 직접 import하지 않고 출력 포트를 거친다. `adapter.inbound.api.schemas`는 허용("Schema in", §C.2) | §C.3 |
| `core-no-frameworks` | `domain`·`app`은 `fastapi`·`starlette`·`sqlalchemy`를 import하지 않는다(타입 힌트 포함). 세션은 `Callable[[], AbstractAsyncContextManager[Any]]`로 받는다 | §C.1·§C.3 |
| `auth-isolation` | 기존 앱은 `auth`를 import하지 않는다 | §O |
| `shared-independence` | `shared`는 잎 의존이다 — 어떤 앱도 import하지 않는다 | §O |

- 검사: pre-commit(커밋마다)과 backend-ci. 직접 실행은
  `cd suvisdev && docker run --rm -e PYTHONPATH=/suvisdev:/suvisdev/apps -v "$PWD":/suvisdev -w /suvisdev suvisdev-app:latest sh -c "pip install -q import-linter==2.15 && lint-imports"`.
- 와일드카드(`*.domain`, `*.app`)라 새 앱도 자동으로 걸린다. 새 앱을 만들면 `[importlinter] root_packages`에 추가한다.

## 위반이 나면

- **예외(`ignore_imports`)를 늘려서 통과시키지 않는다.** 출력 포트(ABC)를 `app/ports/output/`에 두고 어댑터는
  `dependencies/*_provider.py`에서 주입한다. 상수·예외가 필요하면 `app/` 또는 `domain/`으로 옮긴다.
- `app-no-outbound`의 기존 예외 9건은 11-10에 모두 지웠다(저장소는 `reviews_repository=ReviewsPgRepository`처럼
  세션→포트 함수로, 모델·LLM 함수와 프롬프트는 생성자로 주입). 예외 추가가 불가피하면 이유를 주석으로 남기고 사용자에게 알린다.
- 어댑터 예외를 잡아야 하면 포트 파일에 예외를 두고 어댑터 예외가 상속하게 한다(예: `BoxOfficeError` ← `KoficAdapterError`).

## 환경 변수

- 코드에서 새 환경 변수를 읽으면 `suvisdev/.env.example`에 문서화한다. backend-ci의
  `python scripts/check_env_drift.py --code`가 새 누락을 막는다. 기존 누락 39개(`_UNDOCUMENTED_BASELINE`)는 줄이기만 한다.

## 검사하지 않는 규칙 (리뷰로 지킨다)

- 인터랙터는 `HTTPException`을 던지지 않는다 — 앱 예외를 던지고 라우터가 상태 코드로 바꾼다(§K·§P).
- 라우터에 비즈니스 로직·DB 직접 접근을 두지 않는다(§C.3).
- 도메인 객체는 §P의 신호(규칙 중복·생성 검증·독립 계산)가 있을 때만 만든다. 레이어를 채우려고 만들지 않는다.
