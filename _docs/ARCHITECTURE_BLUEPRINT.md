# 아키텍처 블루프린트 — 새 프로젝트 기준 문서

> **용도:** 이 저장소(suvisdev.cloud)에서 검증된 아키텍처 패턴을 **새 프로젝트에
> 그대로 적용**할 때 기준이 되는 단일 문서.  
> **대상:** 개발자·코딩 에이전트 — 프로젝트 초기화부터 운영까지.  
> **출처:** suvisdev.cloud 실측 구조 (2026-08 기준).

---

## 목차

1. [설계 철학](#1-설계-철학)
2. [전체 토폴로지 — 모듈러 모놀리식 + 스타 토폴로지](#2-전체-토폴로지)
3. [앱 디렉터리 템플릿](#3-앱-디렉터리-템플릿)
4. [레이어별 책임과 규칙 (Clean Architecture + Hexagonal)](#4-레이어별-책임과-규칙)
5. [데이터 객체 4종 — Schema · Command · Dto · ORM](#5-데이터-객체-4종)
6. [도메인 레이어 (DDD)](#6-도메인-레이어)
7. [의존성 주입 (DI)](#7-의존성-주입)
8. [SOLID 적용 기준](#8-solid-적용-기준)
9. [디자인 패턴 카탈로그](#9-디자인-패턴-카탈로그)
10. [DB·ORM 규칙](#10-db--orm-규칙)
11. [인증·보안](#11-인증--보안)
12. [테스트 전략](#12-테스트-전략)
13. [진입점·부팅 순서](#13-진입점--부팅-순서)
14. [인프라 (Docker · 배포)](#14-인프라)
15. [금지·안티패턴 종합](#15-금지--안티패턴-종합)
16. [새 앱 추가 체크리스트](#16-새-앱-추가-체크리스트)
17. [새 API 추가 체크리스트](#17-새-api-추가-체크리스트)
18. [문서 배치 규칙](#18-문서-배치-규칙)

---

## 1. 설계 철학

### 1.1 Karpathy 네 원칙

| 원칙 | 핵심 |
|------|------|
| **구현 전 사고** | 가정을 명시한다. 불확실하면 질문한다. 임의로 고르지 않고 대안을 제시한다. |
| **단순성 우선** | 요청되지 않은 기능·추상·설정은 넣지 않는다. 발생 불가능한 시나리오를 위한 예외 처리는 하지 않는다. |
| **정밀한 수정** | 인접 코드를 임의로 "개선"하지 않는다. 기존 스타일을 따른다. |
| **목표 중심 실행** | 모호한 지시를 검증 가능한 목표로 바꾼다. |

### 1.2 속도보다 신중함

본 지침은 **속도보다 신중함**에 우선순위를 둔다. 사소한 작업(명백한 오타 수정, 한 줄 수정 등)은 상황에 맞게 판단한다.

---

## 2. 전체 토폴로지

### 2.1 모듈러 모놀리식 (Modular Monolith)

단일 배포 단위이지만 앱 간 경계가 명확히 분리된다.

### 2.2 스타-토폴로지 (Star Topology / Hub-and-Spoke)

```text
        app_a    app_b    app_c    app_d
           \       |       |       /
            \      |       |      /
             ★  hub (Hub)  ★
            /      |       |      \
           /       |       |       \
        app_e    app_f    app_g    app_h
```

### 2.3 의존 방향 규칙

| 방향 | 허용 여부 |
|------|----------|
| Spoke → Hub | ✅ 허용 |
| Spoke → Spoke (직접) | ❌ **금지** |
| Hub → Spoke | ❌ **금지** |
| Spoke → `core.*` / `shared.*` | ✅ 허용 |
| Hub → `core.*` / `shared.*` | ✅ 허용 |

- **Hub**는 공통 이벤트 정의, 온톨로지, 평가 로직이 위치한다. Spoke를 절대 import하지 않는다.
- **Spoke**는 Hub를 import할 수 있다. 다른 Spoke를 직접 import하는 것은 엄격히 금지된다.
- Spoke 간 데이터 교환이 필요하면 반드시 **Hub의 이벤트 버스**를 경유한다.

### 2.4 강제 도구

| 도구 | 파일 | 역할 |
|------|------|------|
| `import-linter` | `.importlinter` | Spoke 간 직접 import / Hub→Spoke import 차단 |
| `ruff` | `pyproject.toml` | 코드 스타일·포맷·lint |
| `mypy` | `pyproject.toml` | 정적 타입 검사 (strict) |
| `pre-commit` | `.pre-commit-config.yaml` | 커밋 시점 자동 검사 |

---

## 3. 앱 디렉터리 템플릿

새 앱을 만들 때 이 구조를 **그대로** 복제한다.

```text
apps/{app}/
├── __init__.py
├── adapter/
│   ├── __init__.py
│   ├── inbound/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py        # v1 라우터 집약 (APIRouter re-export)
│   │   │   ├── schemas/           # Pydantic Request/Response
│   │   │   │   ├── __init__.py
│   │   │   │   └── {feature}_schema.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── {feature}_router.py   # FastAPI Router
│   │   ├── cli/                   # CLI 진입점 (typer 등, 필요 시)
│   │   │   └── app.py
│   │   └── mcp/                   # MCP 서버 (필요 시)
│   └── outbound/
│       ├── __init__.py
│       ├── orm/                   # SQLAlchemy ORM 모델
│       │   ├── __init__.py
│       │   └── {feature}_orm.py
│       ├── pg/                    # PostgreSQL Repository 구현체
│       │   ├── __init__.py
│       │   └── {feature}_pg_repository.py
│       ├── repositories/          # 비-DB 구현체 (CSV, 외부 API 등)
│       │   └── {feature}_repository.py
│       ├── llm/                   # 외부 LLM 어댑터 (필요 시)
│       └── mappers/               # ORM ↔ Entity 매퍼 (필요 시)
│           └── {feature}_mapper.py
├── app/
│   ├── __init__.py
│   ├── dtos/                      # Command + Dto dataclass
│   │   ├── __init__.py
│   │   └── {feature}_dto.py
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── input/                 # 입력 포트 (Use Case ABC)
│   │   │   ├── __init__.py
│   │   │   └── {feature}_use_case.py
│   │   └── output/                # 출력 포트 (Repository ABC)
│   │       ├── __init__.py
│   │       └── {feature}_repository.py  (또는 {feature}_port.py)
│   └── use_cases/                 # Interactor (Use Case 구현체)
│       ├── __init__.py
│       └── {feature}_interactor.py
├── dependencies/                  # FastAPI DI (Depends 조립)
│   ├── __init__.py
│   └── {feature}_provider.py
├── domain/                        # 순수 도메인 (외부 의존 없음)
│   ├── __init__.py
│   ├── entities/                  # Entity (id로 식별, mutable)
│   │   └── {name}.py
│   ├── value_objects/             # Value Object (frozen, 불변)
│   │   └── {name}.py
│   ├── services/                  # Domain Service (순수 비즈니스 규칙)
│   │   └── {name}.py
│   └── events/                    # Domain Event (frozen dataclass)
│       └── {name}_events.py
├── tests/ (또는 test/)            # 앱별 테스트
│   ├── __init__.py
│   ├── conftest.py
│   ├── adapter/
│   │   ├── inbound/api/
│   │   └── outbound/
│   ├── app/
│   │   ├── fakes.py              # Fake 포트 구현
│   │   └── use_cases/
│   └── domain/
│       ├── entities/
│       ├── value_objects/
│       └── services/
├── scripts/                       # 배치·파이프라인 스크립트 (필요 시)
├── data/                          # 앱 로컬 데이터 (CSV, 캐시 등)
├── resources/                     # 학습 데이터, 정적 리소스 (필요 시)
└── _docs/                         # 앱별 문서
    └── CLAUDE.md                  # 앱별 도메인 규칙·ERD
```

### 3.1 저장소 루트 구조

```text
project_root/
├── apps/                          # 모든 앱 (Hub + Spoke)
│   ├── {hub_app}/                 # Hub 앱 (1개)
│   ├── {spoke_app_1}/             # Spoke 앱들
│   ├── {spoke_app_2}/
│   └── ...
├── core/                          # 공통 인프라 (DB 매니저, 시크릿 매니저 등)
├── shared/                        # 앱 간 공유 유틸리티 (보안 가드 등)
├── scripts/                       # 운영 스크립트
├── alembic/                       # DB 마이그레이션
├── _docs/                         # 프로젝트 공통 문서
├── main.py                        # FastAPI 진입점
├── CLAUDE.md                      # 아키텍처 SSOT
├── pyproject.toml                 # ruff, mypy, 의존성
├── pytest.ini                     # 테스트 설정
├── .importlinter                  # 의존 방향 강제
├── .pre-commit-config.yaml
├── docker-compose.yaml
├── Dockerfile
└── .env                           # 환경 변수 (gitignore)
```

---

## 4. 레이어별 책임과 규칙

### 4.1 표준 요청 흐름

```text
[Inbound Adapter]  Router (FastAPI)
       │  Schema in
       ▼
[Input Port]       XxxUseCase (ABC)     ← Schema in, Dto out
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
[DB]               PostgreSQL
```

### 4.2 응답 경로

```text
ORM row → Dto.from_orm() → Interactor 반환
       → Router에서 Dto.to_schema() → HTTP JSON (OpenAPI response_model)
```

### 4.3 레이어별 규칙표

| 레이어 | 위치 | 할 수 있는 것 | 하면 안 되는 것 |
|--------|------|---------------|-----------------|
| **Router** | `adapter/inbound/api/v1/*_router.py` | Schema 수신, `Depends`, `await use_case`, Dto→Schema | 비즈니스 로직, DB 직접 접근 |
| **Input Port** | `app/ports/input/*_use_case.py` | ABC, Schema in / Dto out 시그니처 | 구현 코드, DB |
| **Interactor** | `app/use_cases/*_interactor.py` | Schema→Command, port 호출, Dto 반환 | `to_schema()`, `HTTPException`, ORM import |
| **Output Port** | `app/ports/output/*_repository.py` | ABC, Command in | 구현 코드 |
| **PgRepository** | `adapter/outbound/pg/*_pg_repository.py` | Command 처리, ORM, `RepositoryError` | `HTTPException`, Use Case import |
| **ORM** | `adapter/outbound/orm/` | 테이블 매핑 | Router·Interactor에서 직접 쓰지 않음 |
| **Dto / Command** | `app/dtos/` | `from_schema`, `from_orm`, `to_schema`(Dto만) | HTTP·DB 세션 |
| **DI** | `dependencies/*_provider.py` | `get_*_use_case`, 구체 Repository→Interactor 조립 | 비즈니스 로직 |
| **Schema** | `adapter/inbound/api/schemas/` | Pydantic, OpenAPI | Repository·ORM |
| **Domain** | `domain/` | 순수 비즈니스 규칙, Entity, VO | FastAPI, SQLAlchemy, 외부 라이브러리 |

### 4.4 의존 방향 (Clean Architecture)

```text
바깥 → 안쪽 (단방향)

Router → Input Port → Interactor → Output Port → PgRepository
                                  ↗
                        Domain (Entity, VO, Service)
```

도메인은 어떤 레이어에도 의존하지 않는다.

---

## 5. 데이터 객체 4종

### 5.1 종류와 역할

| 타입 | 예시 | 생성 | 위치 | 사용처 |
|------|------|------|------|--------|
| **Schema** | `MovieCreateSchema` | Pydantic `BaseModel` | `adapter/inbound/api/schemas/` | Router in, Input Port in, OpenAPI |
| **Command** | `MovieUpsertCommand` | `@dataclass` + `from_schema()` | `app/dtos/` | Interactor → Output Port → PgRepository |
| **Dto** | `MovieDto` | `@dataclass` + `from_orm()` + `to_schema()` | `app/dtos/` | Input Port out, Interactor return |
| **ORM** | `MovaMovie` | SQLAlchemy `DeclarativeBase` | `adapter/outbound/orm/` | PgRepository 내부만 |

### 5.2 변환 규칙

```python
# Interactor (표준 흐름)
command = MovieUpsertCommand.from_schema(payload)
row = await self._repository.upsert(command)
return MovieDto.from_orm(row)

# Router (HTTP 계약이 Schema일 때)
return (await movies.save_movie(req)).to_schema()

# Router (DTO가 곧 HTTP 계약일 때)
return await use_case.execute(schema)  # Dto 직접 반환
```

### 5.3 변환 금지 사항

- `model_dump()` → dict → Command 패턴은 **금지**. 반드시 `Command.from_schema(schema)`.
- Interactor·Use Case 레이어에서 `to_schema()` 호출 **금지** — Router(inbound adapter) 책임.
- Dto의 `to_schema()`는 **lazy import**로 Schema를 가져와 순환 import를 피한다.

---

## 6. 도메인 레이어 (DDD)

### 6.1 Entity (엔티티)

- `id`로 **식별**되는 객체. mutable (`@dataclass`, frozen 아님).
- 외부 라이브러리에 의존하지 않는다.
- `from_orm()` 팩토리 메서드로 ORM → Entity 변환.

```python
@dataclass
class TreeSegment:
    id: int | None
    road_name: str | None
    start: Coordinate
    end: Coordinate
    species: TreeSpecies
    quantity: int
    managing_agency: str

    def midpoint(self) -> Coordinate:
        return Coordinate(
            latitude=(self.start.latitude + self.end.latitude) / 2,
            longitude=(self.start.longitude + self.end.longitude) / 2,
        )

    @classmethod
    def from_orm(cls, orm_obj: Any) -> TreeSegment:
        return cls(
            id=orm_obj.id,
            road_name=orm_obj.road_name,
            start=Coordinate(latitude=orm_obj.start_latitude, ...),
            ...
        )
```

### 6.2 Value Object (값 객체)

- **불변** (`@dataclass(frozen=True)`). 값으로 동등성을 판단한다.
- `__post_init__`에서 유효성 검증.
- 도메인 로직을 메서드로 캡슐화 (예: `distance_to()`).

```python
@dataclass(frozen=True)
class Coordinate:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"위도는 -90~90 범위여야 합니다: {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"경도는 -180~180 범위여야 합니다: {self.longitude}")

    def distance_to(self, other: Coordinate) -> float:
        # Haversine 공식
        ...
```

Enum 기반 값 객체:

```python
class SeasonMode(Enum):
    SPRING_AUTUMN = "spring_autumn"
    WINTER_SAFETY = "winter_safety"

    @classmethod
    def from_value(cls, value: str) -> SeasonMode:
        for mode in cls:
            if mode.value == value:
                return mode
        raise ValueError(f"알 수 없는 모드입니다: {value!r}")
```

### 6.3 Domain Service (도메인 서비스)

- Entity/VO에 속하지 않는 **순수 비즈니스 규칙**을 캡슐화한다.
- 외부 라이브러리에 의존하지 않는다.
- 상태를 갖지 않는다 (stateless).

```python
class RouteWeightCalculator:
    def calculate_edge_weight(
        self,
        edge: RouteEdge,
        mode: SeasonMode,
        nearby_segments: list[TreeSegment],
        nearby_hazards: list[HazardZone],
    ) -> RouteWeight:
        base = RouteWeight(edge.base_distance_m)
        if mode is SeasonMode.SPRING_AUTUMN:
            if self._matches_bonus_tree(edge, nearby_segments):
                return base.apply_discount(0.3)
            return base
        ...
```

### 6.4 Domain Event (도메인 이벤트)

- `@dataclass(frozen=True)` — 불변.
- Hub에 정의하고 Spoke가 발행한다.
- Spoke 간 직접 통신 대신 이벤트 경유.

```python
@dataclass(frozen=True)
class CrawlCompletedEvent:
    site_id: str
    keyword_count: int
    record_count: int
    jsonl_path: str
    completed_at: datetime
```

---

## 7. 의존성 주입 (DI)

### 7.1 Provider 패턴

`dependencies/*_provider.py`에서 구체 Repository → Interactor를 **조립**한다.

```python
# FastAPI Depends 체인
def get_james_director_repository(
    db: AsyncSession = Depends(get_db),
) -> JamesPort:
    return JamesRepository(session=db)

def get_james_director_use_case(
    repository: JamesPort = Depends(get_james_director_repository),
) -> JamesUseCase:
    return JamesInteractor(repository=repository)
```

### 7.2 규칙

- Interactor는 **Output Port(ABC)만** 생성자로 받는다.
- Use Case는 **전역 변수 주입 금지** — `Depends(get_*_use_case)`만 사용.
- Interactor 내부에서 `XxxPgRepository()`를 직접 생성하지 않는다 (DIP 위반).

### 7.3 다중 Repository 주입 예시

```python
class CalculateDogFriendlyRouteInteractor(CalculateDogFriendlyRouteUseCase):
    def __init__(
        self,
        tree_repository: TreeSegmentRepository,    # Output Port ABC
        hazard_repository: HazardZoneRepository,   # Output Port ABC
        route_graph: RouteGraphPort,               # Output Port ABC
        weight_calculator: RouteWeightCalculator,   # Domain Service
    ) -> None:
        self._tree_repository = tree_repository
        self._hazard_repository = hazard_repository
        self._route_graph = route_graph
        self._weight_calculator = weight_calculator
```

---

## 8. SOLID 적용 기준

| 원칙 | 적용 | 의미 |
|------|------|------|
| **SRP** | Router=HTTP, Interactor=유스케이스, Repository=persistence | 각 클래스는 하나의 책임만 |
| **OCP** | Strategy 패턴 (ABC) — 새 알고리즘 추가 시 기존 코드 수정 불필요 | 확장에 열려 있고 변경에 닫혀 있다 |
| **LSP** | Port ABC `@abstractmethod`로 계약 강제 — 구현체 간 대체 가능성 보장 | 하위 타입은 상위 타입을 대체할 수 있다 |
| **ISP** | 도메인별 작은 입력 포트 분리 | 클라이언트가 쓰지 않는 메서드에 의존하지 않는다 |
| **DIP** | Interactor → Port ABC; `dependencies/`에서 구현체 주입 | 상위 레벨이 하위 레벨에 의존하지 않는다 |

> **OCP/LSP를 이유로 과한 추상·팩토리·전략 패턴 남발 금지.** YAGNI 우선.

---

## 9. 디자인 패턴 카탈로그

| 패턴 | 위치 | 용도 |
|------|------|------|
| **Ports & Adapters (Hexagonal)** | `app/ports/`, `adapter/` | 외부와의 연결을 포트와 어댑터로 분리 |
| **Use Case / Interactor** | `*_use_case.py`, `*_interactor.py` | 입력 포트(ABC) + 구현체 |
| **Repository** | `*_repository.py`, `*_pg_repository.py` | 출력 포트(ABC) + 구현체 |
| **DTO / Command Object** | `app/dtos/` | 레이어 간 데이터 전달 |
| **Dependency Injection** | `dependencies/*.py`, FastAPI `Depends` | 런타임 구현체 바인딩 |
| **Strategy** | `*_strategy.py` (Port ABC) | 알고리즘 교체 (OCP) |
| **Domain Service** | `domain/services/` | Entity에 속하지 않는 비즈니스 규칙 |
| **Domain Event** | `domain/events/` | 앱 간 비동기 통신 |
| **Factory Method** | `Entity.from_orm()`, `Command.from_schema()` | 객체 생성 캡슐화 |
| **Mapper** | `adapter/outbound/mappers/` | ORM ↔ Entity 변환 (필요 시) |

---

## 10. DB · ORM 규칙

### 10.1 PK 규칙

- 모든 테이블 PK: **`id`**, 타입 **`int`**, **자동 증가**.
- PK 이름 변경 금지 — 항상 `id`.
- 비즈니스 키(`slug`, `username`)는 **UNIQUE 별도 컬럼**.
- FK: `{entity}_id` → `{table}.id`.

```python
# SQLAlchemy 2.0 Mapped (권장)
class Example(Base):
    __tablename__ = "examples"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
```

### 10.2 ORM 컬럼 타입 규칙

| 조건 | 타입 |
|------|------|
| 외부 API·LLM·사용자 입력 값 | **`Text`** |
| 형식이 고정된 식별자·코드 | `String(N)` — N의 근거를 주석에 남긴다 |
| URL | **`Text`** |
| 본문·요약·메모 | **`Text`** |

### 10.3 Cross-metadata FK

```python
ForeignKey(User.__table__.c.id)  # 문자열 "users.id" 금지
```

### 10.4 Async DB

- SQLAlchemy 2.0 **async** (`AsyncSession`, `postgresql+psycopg://`).
- `create_tables()` 순서를 지킨다 (FK 참조 순서).

### 10.5 배치에서 길이 초과 대응

DB 예외는 세션을 pending-rollback으로 만든다. 항목 단위 `try/except` 쓸 때 반드시 `await session.rollback()`을 함께 넣는다.

---

## 11. 인증 · 보안

### 11.1 인증 가드

```python
from shared.security.require_admin import AdminPrincipal, require_admin

@router.get("/sites")
async def sites(_: AdminPrincipal = Depends(require_admin)) -> list[SiteSchema]:
    ...
```

- `shared/security/`에 가드를 집중한다. 앱마다 따로 만들지 않는다.
- role은 **서버가 산출한 JWT claim만** 믿는다. 클라이언트가 보내는 값은 권한 판단에 쓰지 않는다.

### 11.2 3계층 토큰 전달

프론트에 프록시가 있으면 **클라이언트 → route.ts → 백엔드** 모두 토큰을 넘긴다.

### 11.3 소유권 검증 (IDOR)

- 리소스 ID만으로 갱신·삭제하지 않는다. 요청자와 리소스 소유자가 같은지 확인한다.
- `user_id`를 경로·바디로 받는 엔드포인트는 그 값을 신뢰하지 않는다 — 신원은 토큰에서만.

### 11.4 민감 정보

- 에러 응답을 UI에 그대로 흘리지 않는다.
- 서버 전용 키에 `NEXT_PUBLIC_` 접두사를 붙이지 않는다.
- 토큰·비밀번호를 로그에 남기지 않는다.

---

## 12. 테스트 전략

### 12.1 프레임워크

- 백엔드: **pytest**
- 프론트: `pnpm type-check` · `pnpm lint` (테스트 프레임워크 없음)

### 12.2 테스트 구조

```text
tests/
├── conftest.py                    # sys.path 부트스트랩 + 마커 자동 skip
├── adapter/
│   ├── inbound/api/               # Router 통합 테스트
│   └── outbound/                  # Repository 통합 테스트
├── app/
│   ├── fakes.py                   # Fake 포트 구현 (포트 ABC 상속)
│   └── use_cases/                 # Interactor 단위 테스트
└── domain/
    ├── entities/                  # Entity 테스트
    ├── value_objects/             # VO 불변성·유효성·동등성 테스트
    └── services/                  # Domain Service 테스트
```

### 12.3 테스트 더블 — Fake 포트 우선

- 유스케이스는 **출력 포트를 구현한 Fake**로 검증한다.
- Fake는 포트 ABC를 **실제로 상속**한다 — 인터페이스가 바뀌면 테스트가 먼저 깨진다.
- 포트에 추상 메서드를 추가하면 Fake에도 같이 구현한다.

```python
class FakeTreeSegmentRepository(TreeSegmentRepository):
    def __init__(self, segments: list[TreeSegment] | None = None) -> None:
        self._segments = list(segments or [])
        self.saved: list[TreeSegment] = []

    def find_all(self) -> list[TreeSegment]:
        return list(self._segments)

    def save_many(self, segments: list[TreeSegment]) -> None:
        self.saved.extend(segments)
```

### 12.4 마커

| 마커 | 의미 |
|------|------|
| `@pytest.mark.gpu` | 실제 GPU·모델 가중치 필요 |
| `@pytest.mark.ollama` | 실제 Ollama 서버 필요 |
| `@pytest.mark.asyncio` | async 테스트 |

- 외부 자원에 의존하면 **반드시 마커를 붙인다**.
- 마커 없는 테스트는 아무 환경에서나 즉시 통과해야 한다.
- 기본 실행: `pytest -m "not gpu and not ollama"`

### 12.5 검증 대상

| 레이어 | 검증 내용 |
|--------|----------|
| Domain | 불변성(frozen), 동등성, 유효성 검증, 비즈니스 규칙 |
| Interactor | 정책 판정(임계값, 게이트 통과·반려, 저장 호출 여부) |
| Adapter | 실제 DB·외부 API 통합 — 마커 붙인 통합 테스트로 분리 |

### 12.6 conftest.py 패턴

```python
# sys.path 부트스트랩
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[3]
for p in (_ROOT, _ROOT / "apps"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# 마커 자동 skip
def pytest_collection_modifyitems(config, items):
    if not config.option.markexpr:
        skip = pytest.mark.skip(reason="ollama 서버 필요")
        for item in items:
            if item.get_closest_marker("ollama"):
                item.add_marker(skip)

# 외부 다운로드 차단
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
```

---

## 13. 진입점 · 부팅 순서

### 13.1 main.py 구조

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 환경 변수 로드
    reload_env()
    # 2. DB 연결 검증
    await verify_connection()
    # 3. 테이블 생성 (FK 참조 순서 지켜야 함)
    await create_tables()
    # 4. 시드 데이터
    await seed_if_empty()
    yield
    # 5. 정리
    await dispose_engine()

app = FastAPI(lifespan=lifespan)
```

### 13.2 sys.path 설정

```python
_BACKEND_ROOT = Path(__file__).resolve().parent
_APPS_ROOT = _BACKEND_ROOT / "apps"
for _p in (_BACKEND_ROOT, _APPS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
```

### 13.3 Import 경로 규칙

| 범위 | 규칙 | 예시 |
|------|------|------|
| 앱 모듈 | `apps/`를 import root로 취급 | `from mova.app.ports.input.movies_use_case import MoviesUseCase` |
| Core 모듈 | `core.*` | `from core.matrix.grid_oracle_database_manager import get_db` |
| Shared 모듈 | `shared.*` | `from shared.security.require_admin import require_admin` |

`from suvisdev.apps.mova...` 같은 긴 접두사는 **금지**.

---

## 14. 인프라

### 14.1 Docker

- 컨테이너를 만들기 전에 `docker ps -a`로 기존 동일 서비스 확인.
- `docker compose --env-file {backend}/.env up -d` — **env-file 빠뜨리지 말 것**.
- 기존 컨테이너가 있으면 재사용·재시작을 먼저 제안한다.

### 14.2 구성

```yaml
# docker-compose.yaml 기본 구성
services:
  db:           # PostgreSQL (+ pgvector)
  redis:        # Redis (캐시·세션)
  backend:      # FastAPI 앱
  pgadmin:      # DB 관리 UI (선택)
  cloudflared:  # Cloudflare Tunnel (선택)
```

### 14.3 환경 변수

- `.env` 파일은 **하나** (백엔드 루트).
- 필수: `DATABASE_URL`, `JWT_SECRET`
- 외부 API: 필요한 API 키들
- OAuth: `{PROVIDER}_CLIENT_ID` / `_CLIENT_SECRET` / `_REDIRECT_URI`
- S3/Cloud Storage: AWS 키들

---

## 15. 금지 · 안티패턴 종합

| ❌ 금지 | ✅ 대신 |
|--------|--------|
| Router에서 Repository 직접 호출 | Use Case port 경유 |
| Interactor에서 `HTTPException` | `RepositoryError` → Router 변환 |
| Interactor에서 `to_schema()` | Router에서 `Dto.to_schema()` |
| `model_dump()` dict로 Command 생성 | `Command.from_schema(schema)` |
| Interactor 내부 `XxxPgRepository()` | 생성자 주입 (DIP) |
| 요청 없는 OCP용 인터페이스 남발 | YAGNI |
| PK를 slug/username만으로 | `id` PK + UNIQUE 보조키 |
| `from suvisdev.apps.*` 긴 접두사 | `from mova.*` / `from titanic.*` |
| Spoke → Spoke 직접 import | Hub 이벤트 버스 경유 |
| Hub → Spoke import | 아키텍처 위반 |
| PK 이름 변경 (`user_id`, `pk`, `seq`) | PK는 항상 `id` |
| 복합 PK만으로 테이블 설계 | surrogate `id` + UNIQUE 제약 |
| `id`를 애플리케이션에서 수동 할당 | DB 자동 증감에 맡김 |
| CPU-bound 작업에 `async def` | `def` + 호출 측에서 `asyncio.to_thread()` |
| 클라이언트 `role` 값 신뢰 | JWT claim만 믿는다 |
| 에러 응답을 UI에 그대로 노출 | 짧은 메시지로 변환 |
| 외부 데이터 컬럼에 `String(N)` | **`Text`** |
| Fake가 포트 ABC를 상속하지 않음 | 반드시 상속 |

---

## 16. 새 앱 추가 체크리스트

1. [ ] `apps/{app}/` 디렉터리 생성 — §3 템플릿 구조 복제
2. [ ] 모든 패키지에 `__init__.py` 배치
3. [ ] `domain/` — Entity, Value Object 정의 (외부 의존 없음)
4. [ ] `app/ports/input/` — Use Case ABC 정의
5. [ ] `app/ports/output/` — Repository ABC 정의
6. [ ] `app/use_cases/` — Interactor 구현
7. [ ] `app/dtos/` — Command + Dto dataclass
8. [ ] `adapter/inbound/api/schemas/` — Pydantic Schema
9. [ ] `adapter/inbound/api/v1/` — FastAPI Router
10. [ ] `adapter/outbound/orm/` — ORM 모델 (`id` int PK 자동 증가)
11. [ ] `adapter/outbound/pg/` — PgRepository 구현
12. [ ] `dependencies/` — Provider (Depends 조립)
13. [ ] `adapter/inbound/api/__init__.py` — Router re-export
14. [ ] `main.py`에 라우터 include
15. [ ] `pytest.ini`의 `testpaths`에 테스트 경로 추가
16. [ ] `.importlinter`에 의존 방향 계약 추가
17. [ ] `tests/conftest.py` — sys.path 부트스트랩 + 마커 skip
18. [ ] `tests/app/fakes.py` — Fake 포트 구현
19. [ ] `_docs/CLAUDE.md` — 앱별 도메인 규칙
20. [ ] `python -c "import main"` — import 오류 없음 확인

---

## 17. 새 API 추가 체크리스트

1. [ ] `schemas/*_schema.py` — Request/Response Pydantic
2. [ ] `app/dtos/` — `*Command.from_schema`, `*Dto.from_orm`
3. [ ] `app/ports/input/*_use_case.py` — ABC
4. [ ] `app/ports/output/*_repository.py` — ABC
5. [ ] `app/use_cases/*_interactor.py` — Schema→Command→Repo→Dto
6. [ ] `adapter/outbound/pg/*_pg_repository.py` — Command 처리
7. [ ] `adapter/outbound/orm/*_orm.py` — ORM 모델 (필요 시)
8. [ ] `dependencies/*.py` — `get_*_use_case`
9. [ ] `adapter/inbound/api/v1/*_router.py` — `Depends`, `await`, `to_schema`
10. [ ] 상위 Router에 include
11. [ ] 인증 가드 확인 (§11)
12. [ ] 테스트 — Fake 포트 + Interactor 단위 테스트
13. [ ] `python -c "import main"` — import 오류 없음 확인

---

## 18. 문서 배치 규칙

| 문서 성격 | 위치 |
|-----------|------|
| 공통·인프라·워크스페이스 설정 | `_docs/` (루트) |
| 백엔드 아키텍처·API·FastAPI 규칙 | `{backend}/_docs/` |
| 앱별 ERD·도메인 설계 | `apps/{app}/_docs/` |
| 프론트엔드 화면 설계·컴포넌트 | `{frontend}/_docs/` |
| 모바일 화면 설계·위젯 | `{mobile}/_docs/` |

---

## 부록 A. async 규칙

| 성격 | 형태 | 예시 |
|------|------|------|
| I/O-bound (DB·LLM·HTTP) | `async def` | `save_movie`, `chat` |
| CPU-bound (형태소 분석 등) | `def` | `analyze_intent` |

CPU 작업이 무거워 이벤트 루프 블로킹이 문제될 때는 `async def`로 바꾸는 것이 아니라, **호출 측에서 스레드풀에 위임**한다:

```python
result = await asyncio.to_thread(use_case.analyze_intent, question)
```

---

## 부록 B. 커밋 메시지 규칙

- Conventional Commits 형식: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- 제목은 50자 이내
- 본문에 **왜** 바꿨는지 적는다 (무엇을이 아니라)

---

## 부록 C. 한 줄 요약

> **Router(Schema) → Input Port(Schema→Dto) → Interactor(Schema→Command→Port) → PgRepository(Command→ORM) → Dto → Router(`to_schema`)**
>
> **SRP·ISP·DIP 지킨다. 도메인은 외부에 의존하지 않는다. 스타-토폴로지로 앱 간 경계를 강제한다.**
