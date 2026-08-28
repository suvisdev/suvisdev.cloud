# 🎯 작업 지시서: mova 최종 ERD 기반 테이블 생성 (Docker + Alembic Migration, 통합본)

> **하네스 원칙**: 이 문서는 Claude Code에게 명확한 목표, 제약, 검증 기준을 제공하는 작업 사양서다.
> 아래 명세를 벗어나는 임의 판단이 필요하면 작업을 멈추고 질문할 것.
>
> 📌 본 문서는 개선 반영된 **최종 ERD(v2)** 기준의 통합본이다. 이전 v1/v2/v3 분할 지시서를 대체한다.

---

## 0. 선행 확인 (반드시 먼저 수행)

```bash
alembic current
docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt" 2>/dev/null || echo "DB 미기동"
```

- **DB에 mova 테이블이 하나도 없으면**: 본 문서 전체를 초기 리비전 하나로 생성한다.
- **일부/전부 이미 존재하면**: 작업을 멈추고 현황을 보고한 뒤, 차이만 새 리비전으로 만들지 사용자에게 확인받는다. 기존 리비전 수정 금지.

## 1. 목표 (Goal)

첨부된 mova 최종 ERD(14개 테이블)에 따라
**Docker 컨테이너로 실행되는 PostgreSQL + pgvector**에 전체 테이블을 생성하는 **Alembic 마이그레이션**을 작성하고 적용한다.

## 2. 환경 (Environment)

| 항목 | 값 |
|---|---|
| OS | Ubuntu 24.04 (WSL2) |
| DB | **Docker 컨테이너**로 실행하는 PostgreSQL + pgvector (`pgvector/pgvector:pg16` 이미지) |
| 컨테이너 관리 | Docker Compose (기존 `docker-compose.yaml`에 서비스 추가) |
| ORM | SQLAlchemy 2.0 (Mapped / mapped_column 스타일) |
| Migration | Alembic (호스트 WSL에서 실행, 컨테이너 DB에 접속) |
| 접속 정보 | `.env`의 `DATABASE_URL` 사용 (하드코딩 금지) |
| 추가 패키지 | `pgvector` (Python) — requirements.txt에 추가 |

### 2.1 DB 컨테이너 명세

기존 `docker-compose.yaml`에 아래 요구사항을 만족하는 `db` 서비스를 추가한다.
(이미 pgvector 계열 DB 서비스가 존재하면 새로 만들지 말고 그것을 재사용할 것 — 중복 컨테이너 금지)

| 항목 | 요구사항 |
|---|---|
| 이미지 | `pgvector/pgvector:pg16` (pgvector 확장 내장 공식 이미지) |
| 인증 정보 | `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` 를 `.env`에서 주입 |
| 포트 | 호스트 `5432` → 컨테이너 `5432` (점유 시 `.env`의 `DB_PORT`로 변경 가능하게) |
| 볼륨 | named volume 마운트 → 컨테이너 재생성해도 데이터 유지 |
| healthcheck | `pg_isready` 기반. Alembic 실행 전 healthy 상태 확인 |
| 확장 활성화 | 초기화 SQL(`docker-entrypoint-initdb.d/`)로 `CREATE EXTENSION IF NOT EXISTS vector;` 실행 |

- `DATABASE_URL` 형태: `postgresql+psycopg://<user>:<password>@localhost:5432/<db>` (실제 값은 `.env`에서만 관리)
- `.env.example`을 함께 갱신하되, 실제 비밀번호는 커밋하지 않는다.

## 3. 아키텍처 규칙 (Constraints)

- SUVIS 플랫폼의 **헥사고날 클린 DDD** 구조를 따른다.
- ORM 모델은 mova 앱의 `outbound/` 계층, 테이블당 1파일 (총 14개).
- 데이터 흐름 원칙 유지: `Schema → DTO → App → VO → Entity → ORM → DB`
- 이번 작업 범위는 **ORM 모델 + Alembic 마이그레이션까지만**. 유스케이스/엔드포인트는 만들지 않는다.
- 기존 titanic 앱의 ORM 파일 스타일을 참조 기준(baseline)으로 삼는다.
- mova v2 설계 결정 준수: mova 도메인은 내부 `User` 엔티티를 갖지 않고 `users.id`를 `UserId` VO로만 참조한다. 단, DB 테이블 차원에서는 ERD대로 `users`/`admins`/`groups`를 생성한다 (테이블 소유권 ≠ 도메인 엔티티 소유권).

## 4. 테이블 명세 (Spec)

### 4.0 공통 규칙

- 모든 `id` PK는 `int` + auto increment (`Identity()`)
- **UK 컬럼은 `unique=True, nullable=False`**: `groups.code`, `admins.username`, `users.username`, `assistants.slug`, `collections.slug`, `movies.slug`
- PK/FK/UK 외 컬럼은 `nullable=True` (별도 명시 제외)
- FK `ondelete` 정책: 기본 `RESTRICT`
- `jsonb` → `postgresql.JSONB`, `timestamptz` → `DateTime(timezone=True)`
- `created_at`: `server_default=func.now()` / `updated_at`: `server_default=func.now()` + `onupdate=func.now()`
- 테이블 생성 의존성 순서:
  `groups → admins, users` / `collections → movies` / `assistants, users → chat` / `movies, actors → characters` / `movies, chat → rankings` / `users, movies → reviews, user_actions` / `chat, users, movies → picks` / `movies, characters → tags`

### 4.1 `groups`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| code | VARCHAR | UK |
| name | VARCHAR | |
| description | VARCHAR | |

### 4.2 `admins`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| group_id | INT | FK → groups.id |
| username | VARCHAR | UK |
| password_hash | VARCHAR | |
| nickname | VARCHAR | |
| email | VARCHAR | |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

### 4.3 `users`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| group_id | INT | FK → groups.id |
| username | VARCHAR | UK |
| password_hash | VARCHAR | |
| nickname | VARCHAR | |
| email | VARCHAR | |
| gender | VARCHAR | |
| birth_year | INT | |
| preferred_genres | JSONB | |
| bio | VARCHAR | |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

- ⚠️ `age_group` 컬럼은 **만들지 않는다** — 연령대는 `birth_year`에서 파생 계산 (파생 데이터 저장 금지)

### 4.4 `assistants`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| slug | VARCHAR | UK |
| display_name | VARCHAR | |
| avatar_url | TEXT | |
| system_prompt | TEXT | |
| default_model | VARCHAR | |
| is_active | BOOLEAN | |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

### 4.5 `collections`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| slug | VARCHAR | UK |
| name | VARCHAR | |
| description | TEXT | |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

### 4.6 `movies`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| slug | VARCHAR | UK |
| title | VARCHAR | |
| release_year | INT | |
| rating | FLOAT | |
| poster_url | TEXT | |
| platforms | JSONB | |
| age_rating | VARCHAR | |
| embedding | vector(n) | nullable=True, 차원은 아래 게이트 참조 |
| collection_id | INT | FK → collections.id |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

- ⚠️ `genres` 컬럼은 **만들지 않는다** — 장르는 `tags`에서 `tag_kind='genre'`로 표현 (single source of truth)
- **⛔ embedding 차원 게이트 — 작업 전 사용자에게 질문: "임베딩 모델이 무엇인가?"**
  (Gemini text-embedding-004 → 768 / gemini-embedding-001 → 3072 / OpenAI 3-small → 1536. 답변 전 확정 금지)
- `pgvector.sqlalchemy.Vector` 타입 사용, autogenerate 인식 위해 `env.py`에 import 처리
- HNSW/IVFFlat 인덱스는 생성하지 않는다 — 데이터 적재 후 별도 리비전

### 4.7 `actors`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| name | VARCHAR | |
| role_type | VARCHAR | |
| profile_photo_url | TEXT | |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

### 4.8 `characters`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| movie_id | INT | FK → movies.id |
| actor_id | INT | FK → actors.id |
| character_name | TEXT | nullable=False |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

- `character_name`은 원래 VARCHAR(50)이었으나 TMDB 실측 데이터(애니메이션
  다역 성우 등, 최댓값 332자)가 넘쳐 2026-08-05 TEXT로 확장(`20260805_0001`).
  자세한 근거는 마이그레이션 docstring·`_docs/WORK_LOG_MOVA.md` 2026-08-05 참고.
- **⛔ UNIQUE 게이트 — 작업 전 사용자에게 질문: "1인 다역을 허용하는가?"**
  - 불허 → `UniqueConstraint("movie_id", "actor_id", name="uq_characters_movie_actor")`
  - 허용 → `UniqueConstraint("movie_id", "actor_id", "character_name", name="uq_characters_movie_actor_name")`

### 4.9 `chat`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| user_id | INT | FK → users.id |
| assistant_id | INT | FK → assistants.id |
| raw_message | TEXT | |
| refined_query | VARCHAR | |
| keywords | JSONB | |
| intent_type | VARCHAR | |
| search_filters | JSONB | |
| hit_count | INT | |
| last_used_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | 공통 규칙 |

### 4.10 `reviews`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| user_id | INT | FK → users.id |
| movie_id | INT | FK → movies.id |
| rating | FLOAT | |
| body | TEXT | |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

- 복합 UNIQUE: `UniqueConstraint("user_id", "movie_id", name="uq_reviews_user_movie")` — 한 유저는 한 영화에 리뷰 하나 (수정은 UPDATE)

### 4.11 `user_actions`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| user_id | INT | FK → users.id |
| movie_id | INT | FK → movies.id |
| action_type | VARCHAR | nullable=False (`'like' \| 'click' \| 'watch' \| ...` 주석 문서화) |
| action_at | TIMESTAMPTZ | server_default=now() |

- UNIQUE 없음 — 행동 로그는 중복 허용이 본질

### 4.12 `rankings`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| rank | INT | ⚠️ SQL 예약어 — `mapped_column("rank", ...)` 명시 매핑 |
| movie_id | INT | FK → movies.id |
| chat_id | INT | FK → chat.id |
| source | VARCHAR | |
| score | INT | |
| badge | VARCHAR | |
| ranked_at | DATE | |

### 4.13 `picks`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| chat_id | INT | FK → chat.id |
| user_id | INT | FK → users.id |
| movie_id | INT | FK → movies.id |
| pick_rank | INT | |
| hook | VARCHAR | |
| title_snapshot | VARCHAR | |
| batch_at | TIMESTAMPTZ | |
| feedback | VARCHAR | |

### 4.14 `tags`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | INT | PK |
| movie_id | INT | FK → movies.id, nullable=True |
| character_id | INT | FK → characters.id, nullable=True |
| tag_kind | VARCHAR | `'genre' \| 'cast_keyword' \| 'mood' \| ...` 주석 문서화 |
| slug | VARCHAR | |
| label | VARCHAR | |
| description | TEXT | |
| created_at / updated_at | TIMESTAMPTZ | 공통 규칙 |

- XOR CHECK 제약 — 태그는 영화 또는 캐릭터 둘 중 정확히 하나에만:

```
CheckConstraint("(character_id IS NULL) != (movie_id IS NULL)", name="ck_tags_exactly_one_target")
```

## 5. 작업 절차 (Steps)

0. **DB 컨테이너 기동**
   - `docker-compose.yaml`에 2.1 명세대로 `db` 서비스 작성 (기존 서비스 있으면 재사용)
   - `docker compose up -d db` → `docker compose ps` 로 `healthy` 대기
1. **환경 점검**
   - 선행 확인(0번) 분기 판별 + 보고
   - `alembic.ini` / `env.py` 확인, 없으면 `alembic init` 후 `.env`의 `DATABASE_URL` + `Base.metadata` 연결
   - pgvector 확인: `docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"`
   - 확장 없으면 초기화 SQL 미적용 → 볼륨 재초기화 필요 시 **사용자 확인 후** 진행
2. **사용자 질문 게이트** — embedding 차원(4.6), 1인 다역(4.8) 답변 확보
3. **ORM 모델 작성** — 테이블당 1파일, 총 14개, 제약은 `__table_args__`에
4. **마이그레이션 생성** — `alembic revision --autogenerate -m "create mova tables"` → **diff 요약 출력 후** 적용
5. **적용 및 검증** — `alembic upgrade head` → 아래 6번 검증
6. **롤백 검증** — `alembic downgrade -1` → 소멸 확인 → 재적용

## 6. 완료 기준 (Definition of Done)

- [ ] `docker compose ps` 에서 `db` 서비스 `healthy`
- [ ] pgvector 확장 버전 조회 성공
- [ ] `alembic upgrade head` 성공, `\dt`에 14개 테이블 존재
- [ ] UNIQUE 6개(UK) + `uq_reviews_user_movie` + characters UNIQUE(게이트 답변 기준) 존재
- [ ] `\d tags` 에 `ck_tags_exactly_one_target` 존재
- [ ] `\d movies` 에 확정 차원의 `embedding vector(n)` 존재, `genres` 없음, `release_year`가 integer
- [ ] `\d users` 에 `age_group` 없음
- [ ] `user_actions`와 `reviews`가 분리 존재 (reviews에 action 계열 컬럼 없음)
- [ ] 컨테이너 재시작 후 테이블/데이터 유지 (볼륨 검증)
- [ ] `alembic downgrade -1` 시 14개 테이블 정상 제거 (downgrade 구현 필수)
- [ ] `ruff check` / `mypy` 통과

## 7. 금지 사항 (Do NOT)

- ❌ `Base.metadata.create_all()` 금지 — 반드시 Alembic 경유
- ❌ DB 접속 정보 하드코딩 금지
- ❌ ERD에 없는 컬럼/인덱스 임의 추가 금지 (`age_group`, `genres` 재도입 포함)
- ❌ vector 인덱스(HNSW/IVFFlat) 생성 금지 — 데이터 적재 후 별도 리비전
- ❌ embedding 차원, 1인 다역 여부 **사용자 답변 없이 확정 금지**
- ❌ 기존 마이그레이션 리비전 수정 금지 — 새 리비전으로만
- ❌ 호스트 WSL에 PostgreSQL 직접 설치 금지 — DB는 반드시 컨테이너로만
- ❌ 볼륨 없는 컨테이너 금지 / `docker compose down -v` 임의 실행 금지 (데이터 삭제는 사용자 확인 필수)2