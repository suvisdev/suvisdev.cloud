# cloud.suvisdev 백엔드 인수인계

> **대상:** Claude Code·Cursor 등 코딩 에이전트.  
> **목적:** Clean Architecture + Hexagonal + FastAPI + SOLID(SRP·ISP·DIP) + **스타-토폴로지(Star Topology)** 규칙을 한 문서에서 인수인계한다.  
> **구조:** **모듈러 모놀리식(Modular Monolith)** — `ontology`가 Hub, 나머지 앱이 Spoke.  
> **기준 구현:** `apps/titanic/` (James/Walter/Smith) — Mova·Viewer는 **동일 레이어 규칙**으로 맞춘 상태.  
> **상위 원칙:** [[CLAUDE]] — Karpathy 네 원칙 (항상 유효)

---

## A. 에이전트가 코드를 쓰기 전에 읽을 것

| 순서 | 문서 | 용도 |
|------|------|------|
| 1 | **본 파일** (`suvisdev/_docs/CLAUDE.MD`) | 아키텍처·레이어·SOLID·패턴 |
| 2 | `entity-rules.md` (동일 `_docs/` 폴더) | PK `id` int 자동증감 |
| 3 | 해당 앱 `apps/<app>/_docs/CLAUDE.md` | §J 앱별 링크 참조 |

**규칙 문서를 읽지 않고 관례를 추측하여 구현하지 않는다.**

### 충돌 시 우선순위

1. 사용자의 **더 구체적·최근** 지시  
2. **`_docs/`** · **`apps/*/_docs/`** 내 해당 영역 규칙 MD  
3. 본 `CLAUDE.md` 백엔드 인수인계  

Karpathy 네 원칙(묵시적 가정 금지·최소 diff)은 **항상** 유지한다.

---

## B. 저장소 앱 구조 (`apps/`)

| 앱 | 역할 | 토폴로지 | 참조 |
|----|------|----------|------|
| `ontology/` | **Hub** — 공통 이벤트 버스·온톨로지·하네스 평가 엔진 | ⭐ Hub | — |
| `titanic/` | CSV 업로드(James)·조회(Walter)·선장채팅(Smith) — **헥사고날 기준선** | Spoke | `titanic/_docs/CLAUDE.md` |
| `mova/` | 영화·채팅·랭킹·리뷰 등 도메인 API | Spoke | `mova/_docs/CLAUDE.md` |
| `viewer/` | 인증(`groups`, `admins`, `users`) — login/signup | Spoke | `viewer/_docs/CLAUDE.md` |
| `silicon_valley/` | n8n·Slack 연동, 이벤트 발행 | Spoke | — |
| `friday13th/` | 개발 중 (스켈레톤 — main.py 미등록) | Spoke | — |
| `imitation_game/` | 개발 중 (스켈레톤 — main.py 미등록) | Spoke | — |
| `inception/` | 개발 중 (스켈레톤 — main.py 미등록) | Spoke | — |
| `social_network/` | 개발 중 (스켈레톤 — main.py 미등록) | Spoke | — |

- **인증은 `viewer/`** — 프로덕션 login/signup은 viewer만 사용.
- **DB:** Neon PostgreSQL. Mova·Viewer(Secom)는 동일 DB URL을 공유하는 경우가 많음 (`DATABASE_URL` / `MOVA_DATABASE_URL` / `SECOM_DATABASE_URL`).
- **진입점:** `main.py` — lifespan에서 `verify_connection()` → `create_tables()` → `seed_viewer_if_empty()`.
- **현재 main.py 등록 앱:** titanic, mova, viewer (나머지는 스켈레톤).
- **테스트:** `apps/<app>/tests/` (앱별). `suvisdev/tests/` 루트 폴더는 **사용하지 않음**.

---

## C. 아키텍처: Clean Architecture + Hexagonal (Ports & Adapters)

### C.1 개념

- **Clean Architecture:** 의존 방향은 **바깥 → 안쪽**. 도메인(앱 코어)은 FastAPI·SQLAlchemy·HTTP에 의존하지 않는다.
- **Hexagonal:** **입력 포트**(Use Case ABC)와 **출력 포트**(Repository ABC)로 외부와 연결. 구현체(Adapter)는 `adapter/`에 둔다.

### C.2 표준 요청 흐름

```text
[Inbound Adapter]  Router (FastAPI)
       │  Schema in
       ▼
[Input Port]         XxxUseCase (ABC)     ← Schema in, Dto out
       │
       ▼
[Application]      XxxInteractor        ← Schema → Command → Repository
       │
       ▼
[Output Port]      XxxRepository (ABC)  ← Command in
       │
       ▼
[Outbound Adapter] XxxPgRepository      ← ORM read/write
       │
       ▼
[DB]               PostgreSQL (Neon)
```

**응답 경로 (Mova·Viewer):**

```text
ORM row → Dto.from_orm() → Interactor 반환
       → Router에서 Dto.to_schema() → HTTP JSON (OpenAPI response_model)
```

**Titanic 예외:** 응답 DTO(`JamesResponse`, `WalterResponse`, `SmithCaptainResponse`)가 곧 HTTP 계약이면 router에서 **변환 없이** 반환해도 된다.

### C.3 레이어별 책임 (반드시 지킬 것)

| 레이어 | 위치 | 할 수 있는 것 | 하면 안 되는 것 |
|--------|------|---------------|-----------------|
| **Router** | `adapter/inbound/api/v1/*_router.py` | Schema 수신, `Depends`, `await use_case`, Dto→Schema | 비즈니스 로직, DB 직접 접근 |
| **Input Port** | `app/ports/input/*_use_case.py` | ABC, Schema in / Dto out 시그니처 | 구현 코드, DB |
| **Interactor** | `app/use_cases/*_interactor.py` | Schema→Command, port 호출, Dto 반환 | `to_schema()`, `HTTPException`, ORM import |
| **Output Port** | `app/ports/output/*_repository.py` | ABC, Command in | 구현 코드 |
| **PgRepository** | `adapter/outbound/pg/*_pg_repository.py` | Command 처리, ORM, `RepositoryError` | `HTTPException`, Use Case import |
| **ORM** | `adapter/outbound/orm/` | 테이블 매핑 | Router·Interactor에서 직접 쓰지 않음(Repository 경유) |
| **Dto / Command** | `app/dtos/` | `from_schema`, `from_orm`, `to_schema`(Dto만) | HTTP·DB 세션 |
| **DI** | `dependencies/*_provider.py` | `get_*_use_case`, 구체 Repository→Interactor 조립 | 비즈니스 로직 |
| **Schema** | `adapter/inbound/api/schemas/` | Pydantic, OpenAPI | Repository·ORM |

### C.4 디렉터리 템플릿

```text
apps/{app}/
├── adapter/
│   ├── inbound/api/
│   │   ├── __init__.py         # v1 라우터 집약
│   │   ├── schemas/            # Pydantic Request/Response
│   │   └── v1/*_router.py      # FastAPI Router
│   └── outbound/
│       ├── pg/*_pg_repository.py
│       ├── orm/                # SQLAlchemy ORM
│       └── llm/                # 외부 LLM (필요 시)
├── app/
│   ├── dtos/                   # Command + Dto dataclass
│   ├── ports/
│   │   ├── input/*_use_case.py
│   │   └── output/*_repository.py
│   └── use_cases/*_interactor.py
└── dependencies/*_provider.py    # FastAPI Depends DI
```

---

## D. 데이터 객체 규칙

### D.1 종류와 역할

| 타입 | 예시 | 생성 | 사용처 |
|------|------|------|--------|
| **Schema** | `MovieCreateSchema`, `LoginSchema` | Pydantic | Router in, Input Port in, OpenAPI |
| **Command** | `MovieUpsertCommand`, `LoginUserCommand` | `from_schema()` | Interactor → Output Port → PgRepository |
| **Dto** | `MovieDto`, `LoginResponseDto` | `from_orm()` 또는 interactor 조립 | Input Port out, Interactor return |
| **ORM** | `MovaMovie`, `User` | SQLAlchemy | PgRepository 내부만 |

### D.2 변환 규칙

```python
# Interactor (표준)
command = MovieUpsertCommand.from_schema(payload)
row = await self._repository.upsert(command)
return MovieDto.from_orm(row)

# Router (Mova — HTTP 계약이 Schema일 때)
return (await movies.save_movie(req)).to_schema()

# Router (Titanic — DTO = HTTP 계약)
return await walter.introduce_myself(schema)  # WalterResponse 직접 반환
```

- **`model_dump()` → dict → Command** 패턴은 **금지**. 반드시 `Command.from_schema(schema)`.
- Interactor·Use Case 레이어에서 **`to_schema()` 호출 금지** — inbound adapter(Router) 책임.
- Dto의 `to_schema()`는 **lazy import**로 Schema를 가져와 순환 import를 피한다.

### D.3 엔티티 PK 요약

- 모든 테이블 PK: **`id`**, 타입 **`int`**, **자동 증가**.
- 비즈니스 키(`slug`, `username`)는 **UNIQUE 별도 컬럼**.
- FK: `{entity}_id` → `{table}.id`
- 세부: `entity-rules.md`

---

## E. FastAPI 규칙

### E.1 Router

```python
@movies_router.post("/movies", response_model=MovieSchema, status_code=201)
async def save_movie(
    req: MovieCreateSchema,
    movies: MoviesUseCase = Depends(get_movies_use_case),
) -> MovieSchema:
    return (await movies.save_movie(req)).to_schema()
```

- Router는 **얇게(thin)** — 파라미터·DI·`await use_case`·Dto→Schema만.
- Use Case는 **전역 변수 주입 금지** — `Depends(get_*_use_case)`만 사용.

### E.2 DI (`dependencies/*_provider.py`)

```python
def get_james_director(db: AsyncSession = Depends(get_db)) -> JamesUseCase:
    repository: JamesRepository = CrewJamesDirectorPgRepository(session=db)
    return CrewJamesDirectorInteractor(repository=repository)
```

- Interactor는 **Output Port(ABC)만** 생성자로 받는다.
- Titanic: `get_db()` / Mova: `get_mova_db()` / Viewer: `get_secom_db()`

### E.3 예외 처리

- PgRepository는 `HTTPException`을 쓰지 않는다 → `RepositoryError` 사용.
- Router에서 필요 시 `RepositoryError` → `HTTPException` 변환.
- LLM(Gemini/Ollama): `adapter/outbound/llm/` (outbound adapter).

### E.4 async

- Repository·Use Case·Router handler: **`async def`**
- DB: SQLAlchemy 2.0 **async** (`AsyncSession`, `postgresql+psycopg://`)

#### CPU-bound 메서드는 `async def` 금지

| 성격 | 형태 | 예시 |
|------|------|------|
| I/O-bound (DB·LLM·HTTP) | `async def` | `introduce_myself`, `chat` |
| CPU-bound (형태소 분석 등) | `def` | `analyze_intent` (Kiwi) |

`async def`는 코루틴을 만들 뿐, CPU 연산을 비블로킹으로 바꾸지 않는다.  
Kiwi처럼 동기 CPU 작업에 `async def`를 붙이면 이벤트 루프가 블로킹되면서 비블로킹처럼 보이는 더 나쁜 상태가 된다.

CPU 작업이 실제로 무거워 이벤트 루프 블로킹이 문제가 될 때는 메서드를 `async def`로 바꾸는 것이 아니라, **호출 측에서 스레드풀에 위임**한다.

```python
# Router 또는 Interactor에서
result = await asyncio.to_thread(use_case.analyze_intent, question)
```

---

## F. SOLID 적용 현황

| 원칙 | 상태 | 의미 |
|------|------|------|
| **SRP** | ✅ | Router=HTTP, Interactor=유스케이스, Repository=persistence |
| **ISP** | ✅ | 도메인별 작은 입력 포트 분리 |
| **DIP** | ✅ | Interactor → Port ABC; `dependencies/`에서 구현체 주입 |
| **OCP** | ✅ | `RoseModelStrategy` ABC — 새 알고리즘 추가 시 기존 코드 수정 불필요 (Strategy 패턴) |
| **LSP** | ✅ | Port ABC `@abstractmethod`로 계약 강제 — 구현체 간 대체 가능성 보장 |

**OCP/LSP를 이유로 과한 추상·팩토리·전략 패턴 남발 금지.**

---

## G. 사용 중인 디자인 패턴

| 패턴 | 위치 |
|------|------|
| **Ports & Adapters (Hexagonal)** | `app/ports/`, `adapter/` |
| **Use Case / Interactor** | `*_use_case.py`, `*_interactor.py` |
| **Repository** | `*_repository.py`, `*_pg_repository.py` |
| **DTO** | `app/dtos/` |
| **Command Object** | `*Command`, `*UpsertCommand` |
| **Dependency Injection** | `dependencies/*.py`, FastAPI `Depends` |

---

## H. DB·스키마 관리

### H.1 `create_tables()` 순서

1. **Titanic** (`TitanicBase`)
2. **Viewer/Secom** (`SecomBase`) — `groups`, `admins`, `users` 먼저
3. **Mova** (`MovaBase`) — `users.id` FK 참조

### H.2 Cross-metadata FK

```python
ForeignKey(User.__table__.c.id)  # 문자열 "users.id" 금지
```

### H.3 검증 스크립트

```powershell
cd suvisdev
python scripts/verify_db_tables.py
```

---

## I. Import 경로 규칙

| 범위 | 규칙 | 예시 |
|------|------|------|
| **앱 모듈** | `apps/`를 import root로 취급 — `suvisdev.apps.` 생략 | `from mova.app.ports.input.movies_use_case import MoviesUseCase` |
| **Core 모듈** | `core.*` | `from core.matrix.grid_oracle_database_manager import get_db` |

---

## J. 앱별 참조 파일

### Titanic → [[suvisdev/apps/titanic/_docs/CLAUDE]]

| 역할 | 파일 |
|------|------|
| Router | `titanic/adapter/inbound/api/v1/crew_james_director_router.py` |
| Input Port | `titanic/app/ports/input/crew_james_director_use_case.py` |
| Interactor | `titanic/app/use_cases/crew_james_director_interactor.py` |
| DI | `titanic/dependencies/crew_james_director_provider.py` |
| Smith Captain Router | `titanic/adapter/inbound/api/v1/crew_smith_captain_router.py` |

### Mova → [[suvisdev/apps/mova/_docs/CLAUDE]]

| 역할 | 파일 |
|------|------|
| Router | `mova/adapter/inbound/api/v1/movies_router.py` |
| Input Port | `mova/app/ports/input/movies_use_case.py` |
| Interactor | `mova/app/use_cases/movies_interactor.py` |
| DI | `mova/dependencies/movies_provider.py` |

| Mova ORM 테이블 | 파일 |
|-----------------|------|
| Actors ORM | `mova/adapter/outbound/orm/studio_actors_orm.py` |
| Characters ORM | `mova/adapter/outbound/orm/studio_characters_orm.py` |
| Tags ORM | `mova/adapter/outbound/orm/studio_tags_orm.py` |
| Rankings ORM | `mova/adapter/outbound/orm/market_rankings_orm.py` |
| Chat ORM | `mova/adapter/outbound/orm/market_chat_orm.py` |
| Picks ORM | `mova/adapter/outbound/orm/market_picks_orm.py` |
| Reviews ORM | `mova/adapter/outbound/orm/market_reviews_orm.py` |
| Assistants ORM | `mova/adapter/outbound/orm/platform_assistants_orm.py` |

### Viewer → [[suvisdev/apps/viewer/_docs/CLAUDE]]

| API | 경로 |
|-----|------|
| Login | `POST /viewer/login/login` |
| Signup | `POST /viewer/signup/signup` |

---

## K. 금지·안티패턴

| ❌ 금지 | ✅ 대신 |
|--------|--------|
| Router에서 Repository 직접 호출 | Use Case port 경유 |
| Interactor에서 `HTTPException` | `RepositoryError` → router 변환 |
| Interactor에서 `to_schema()` | Router에서 `Dto.to_schema()` |
| `model_dump()` dict로 Command 생성 | `Command.from_schema(schema)` |
| Interactor 내부 `XxxPgRepository()` | 생성자 주입 (DIP) |
| 요청 없는 OCP용 인터페이스 남발 | YAGNI |
| PK를 slug/username만으로 | `id` PK + UNIQUE 보조키 |
| `from suvisdev.apps.*` 긴 접두사 | `from mova.*` / `from titanic.*` |

---

## L. 새 API 추가 체크리스트

1. [ ] `schemas/*_schema.py` — Request/Response Pydantic
2. [ ] `app/dtos/` — `*Command.from_schema`, `*Dto.from_orm`
3. [ ] `app/ports/input/*_use_case.py` — ABC
4. [ ] `app/ports/output/*_repository.py` — ABC
5. [ ] `app/use_cases/*_interactor.py` — Schema→Command→Repo→Dto
6. [ ] `adapter/outbound/pg/*_pg_repository.py` — Command 처리
7. [ ] `dependencies/*.py` — `get_*_use_case`
8. [ ] `adapter/inbound/api/v1/*_router.py` — `Depends`, `await`, `to_schema`
9. [ ] `main.py` 또는 상위 router에 include
10. [ ] `python -c "import main"` — import 오류 없음 확인

---

## M. 한 줄 요약

> **Router(Schema) → Input Port(Schema→Dto) → Interactor(Schema→Command→Port) → PgRepository(Command→ORM) → Dto → Router(`to_schema`)**  
> **SRP·ISP·DIP 지킨다. Titanic 기준선 레이어를 모든 앱에서 동일하게 유지한다.**

---

## O. 모듈러 모놀리식 & 스타-토폴로지

### O.1 개념

이 저장소는 **모듈러 모놀리식(Modular Monolith)** 구조다. 단일 배포 단위이지만 앱 간 경계가 명확히 분리된다.
앱 간 통신 토폴로지는 **스타-토폴로지(Star Topology / Hub-and-Spoke)** 로 강제된다.

```text
        titanic   mova   viewer   silicon_valley
           \       |       |       /
            \      |       |      /
             ★  ontology (Hub)  ★
            /      |       |      \
           /       |       |       \
     friday13th  inception  social_network  imitation_game
```

### O.2 Hub 규칙 (`ontology`)

- 공통 이벤트 정의, 온톨로지, 하네스 평가 로직이 위치한다.
- **Spoke를 절대 import하지 않는다.** Hub → Spoke 의존은 아키텍처 위반.
- `core.*` 및 외부 라이브러리만 import 가능.

### O.3 Spoke 규칙 (나머지 앱)

- Hub(`ontology`)는 import 가능하다.
- **다른 Spoke를 직접 import하는 것은 엄격히 금지된다.**
- Spoke 간 데이터 교환이 필요하면 반드시 Hub의 이벤트 버스를 경유한다.

### O.4 의존 방향 요약

| 방향 | 허용 여부 |
|------|----------|
| Spoke → Hub (`ontology`) | ✅ 허용 |
| Spoke → Spoke (직접) | ❌ 금지 |
| Hub → Spoke | ❌ 금지 |
| Spoke → `core.*` | ✅ 허용 |
| Hub → `core.*` | ✅ 허용 |

### O.5 강제 도구

| 도구 | 파일 | 역할 |
|------|------|------|
| `import-linter` | `suvisdev/.importlinter` | Spoke 간 직접 import / Hub→Spoke import 차단 |
| `ruff` | `suvisdev/pyproject.toml` | 코드 스타일·포맷·lint |
| `mypy` | `suvisdev/pyproject.toml` | 정적 타입 검사 (strict) |
| `pre-commit` | `suvisdev/.pre-commit-config.yaml` | 커밋 시점 자동 검사 |

위반 시 커밋이 차단된다.

---

## N. 머신러닝 데이터 분석 원칙

### Categorical

데이터가 카테고리로 묶일 때 사용한다.

| 척도 | 설명 | 예시 |
|------|------|------|
| **nominal** | 이름 기반 — 순서 없이 셀 수 있는 데이터 | 청팀, 홍팀, 백팀 |
| **ordinal** | 순서 기반 — 자료 사이에 서열이 있는 데이터 | 1.매우낮음 2.낮음 3.보통 4.높음 5.매우높음 |

### Quantitative

숫자로 셀 수 있을 때 사용한다.

| 척도 | 설명 | 예시 |
|------|------|------|
| **interval** | 간격 기반 — 기준점 없이 일정한 측정 구간 ("10배 덥다" 불가) | 시간대, 온도, pH |
| **ratio** | 비율 기반 — 절대적 원점 기준 ("10배 많다" 가능) | 나이, 돈, 몸무게 |
