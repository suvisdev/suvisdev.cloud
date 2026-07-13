# 🎯 작업 지시서: K-리그 ERD 기반 테이블 생성 (Alembic Migration)

> **하네스 원칙**: 이 문서는 Claude Code에게 명확한 목표, 제약, 검증 기준을 제공하는 작업 사양서다.
> 아래 명세를 벗어나는 임의 판단이 필요하면 작업을 멈추고 질문할 것.

---

## 1. 목표 (Goal)

첨부된 ERD(K-리그 도메인: `stadium`, `team`, `player`, `schedule`)에 따라
**pgvector가 설치된 PostgreSQL**에 4개 테이블을 생성하는 **Alembic 마이그레이션**을 작성하고 적용한다.

## 2. 환경 (Environment)

| 항목 | 값 |
|---|---|
| OS | Ubuntu 24.04 (WSL2) |
| DB | **Docker 컨테이너**로 실행하는 PostgreSQL + pgvector (`pgvector/pgvector:pg16` 이미지) |
| 컨테이너 관리 | Docker Compose (기존 `docker-compose.yaml`에 서비스 추가) |
| ORM | SQLAlchemy 2.0 (Mapped / mapped_column 스타일) |
| Migration | Alembic (호스트 WSL에서 실행, 컨테이너 DB에 접속) |
| 접속 정보 | `.env`의 `DATABASE_URL` 사용 (하드코딩 금지) |

### 2.1 DB 컨테이너 명세

기존 `docker-compose.yaml`에 아래 요구사항을 만족하는 `db` 서비스를 추가한다.
(이미 pgvector 계열 DB 서비스가 존재하면 새로 만들지 말고 그것을 재사용할 것 — 중복 컨테이너 금지)

| 항목 | 요구사항 |
|---|---|
| 이미지 | `pgvector/pgvector:pg16` (pgvector 확장 내장 공식 이미지) |
| 인증 정보 | `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` 를 `.env`에서 주입 |
| 포트 | 호스트 `5432` → 컨테이너 `5432` (호스트 5432 점유 시 `.env`의 `DB_PORT`로 변경 가능하게) |
| 볼륨 | named volume 마운트 → 컨테이너 재생성해도 데이터 유지 |
| healthcheck | `pg_isready` 기반. Alembic 실행 전 healthy 상태 확인 |
| 확장 활성화 | 초기화 SQL(`docker-entrypoint-initdb.d/`)로 `CREATE EXTENSION IF NOT EXISTS vector;` 실행 |

- `.env`의 `DATABASE_URL` 예시 형태: `postgresql+psycopg://<user>:<password>@localhost:5432/<db>` (실제 값은 `.env`에서만 관리)
- `.env.example`을 함께 갱신하되, 실제 비밀번호는 커밋하지 않는다.

## 3. 아키텍처 규칙 (Constraints)

- SUVIS 플랫폼의 **헥사고날 클린 DDD** 구조를 따른다.
- ORM 모델은 `outbound/` 계층에 위치시킨다 (기존 앱 디렉토리 컨벤션 준수: `inbound/`, `use_cases/`, `outbound/`, `dto/`, `schema/`).
- 데이터 흐름 원칙 유지: `Schema → DTO → App → VO → Entity → ORM → DB`
- 이번 작업 범위는 **ORM 모델 + Alembic 마이그레이션까지만**. 유스케이스/엔드포인트는 만들지 않는다.
- 기존 titanic 앱의 ORM 파일 스타일을 참조 기준(baseline)으로 삼는다.

## 4. 테이블 명세 (Spec)

### 4.1 `stadium`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| stadium_id | VARCHAR(10) | **PK** |
| stadium_name | VARCHAR(40) | ERD 오타 `statdium_name`은 `stadium_name`으로 교정 |
| hometeam_id | VARCHAR(10) | |
| seat_count | INTEGER | |
| address | VARCHAR(60) | |
| ddd | VARCHAR(10) | |
| tel | VARCHAR(10) | |

### 4.2 `team`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| team_id | VARCHAR(10) | **PK** |
| region_name | VARCHAR(10) | |
| team_name | VARCHAR(40) | |
| e_team_name | VARCHAR(50) | |
| orig_yyyy | VARCHAR(10) | |
| zip_code1 | VARCHAR(10) | |
| zip_code2 | VARCHAR(10) | |
| address | VARCHAR(80) | |
| ddd | VARCHAR(10) | |
| tel | VARCHAR(10) | |
| fax | VARCHAR(10) | |
| homepage | VARCHAR(50) | |
| owner | VARCHAR(10) | |
| stadium_id | VARCHAR(10) | **FK → stadium.stadium_id** |

### 4.3 `player`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| player_id | VARCHAR(10) | **PK** |
| player_name | VARCHAR(20) | |
| e_player_name | VARCHAR(40) | |
| nickname | VARCHAR(30) | |
| join_yyyy | VARCHAR(10) | |
| position | VARCHAR(10) | |
| back_no | INTEGER | |
| nation | VARCHAR(20) | |
| birth_date | DATE | |
| solar | VARCHAR(10) | |
| height | INTEGER | |
| weight | INTEGER | |
| team_id | VARCHAR(10) | **FK → team.team_id** |

### 4.4 `schedule`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| sche_date | VARCHAR(10) | **복합 PK (1/2)** |
| stadium_id | VARCHAR(10) | **복합 PK (2/2), FK → stadium.stadium_id** |
| gubun | VARCHAR(10) | |
| hometeam_id | VARCHAR(10) | |
| awayteam_id | VARCHAR(10) | |
| home_score | INTEGER | |
| away_score | INTEGER | |

### 4.5 공통 규칙

- 모든 컬럼은 ERD상 N/A(nullable) → PK/FK 외에는 `nullable=True`
- FK에는 `ondelete` 정책을 명시하되, 참조 무결성 보존을 위해 `RESTRICT` 사용
- 테이블 생성 순서 의존성 주의: `stadium → team → player`, `stadium → schedule`
- `stadium.hometeam_id`, `schedule.hometeam_id/awayteam_id`는 ERD상 FK로 표시되지 않았으므로 **일반 컬럼으로 유지** (순환 참조 방지)

## 5. 작업 절차 (Steps)

0. **DB 컨테이너 기동**
   - `docker-compose.yaml`에 2.1 명세대로 `db` 서비스 작성 (기존 서비스 있으면 재사용)
   - `docker compose up -d db` 로 백그라운드 기동
   - `docker compose ps` 로 상태가 `healthy` 될 때까지 대기 후 다음 단계 진행
1. **환경 점검**
   - `alembic.ini` / `env.py` 존재 여부 확인. 없으면 `alembic init` 후 `env.py`가 `.env`의 `DATABASE_URL`과 ORM `Base.metadata`를 읽도록 구성
   - 컨테이너 DB 접속 및 pgvector 확장 상태 확인:
     `docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"`
   - 확장이 없으면 초기화 SQL이 적용되지 않은 것 → 볼륨 삭제 후 재기동으로 초기화 재실행 (`docker compose down -v` 는 데이터 전체 삭제이므로 **사용자에게 먼저 확인받을 것**)
2. **ORM 모델 작성**
   - 테이블당 1파일, SQLAlchemy 2.0 `Mapped`/`mapped_column` 스타일
3. **마이그레이션 생성**
   - `alembic revision --autogenerate -m "create kleague tables"`
   - 생성된 리비전 파일을 **사람이 검토 가능하도록 diff 요약 출력** 후 진행
4. **적용 및 검증**
   - `alembic upgrade head`
   - 검증 쿼리 실행 (아래 6번)
5. **롤백 검증**
   - `alembic downgrade -1` → 테이블 소멸 확인 → 다시 `upgrade head`

## 6. 완료 기준 (Definition of Done)

- [ ] `docker compose ps` 에서 `db` 서비스가 `healthy` 상태
- [ ] 컨테이너 내부에서 `SELECT extversion FROM pg_extension WHERE extname = 'vector';` 결과가 버전을 반환
- [ ] `alembic upgrade head` 성공, 에러 없음
- [ ] `docker compose exec db psql ... -c "\dt"` 결과에 4개 테이블 존재
- [ ] 컨테이너 재시작(`docker compose restart db`) 후에도 테이블/데이터 유지 (볼륨 검증)
- [ ] `schedule`의 복합 PK가 `(sche_date, stadium_id)`로 잡혀 있음 (`docker compose exec db psql ... -c "\d schedule"`로 확인)
- [ ] FK 3개 정상 생성: `team→stadium`, `player→team`, `schedule→stadium`
- [ ] `alembic downgrade -1` 시 4개 테이블 모두 정상 제거 (downgrade 함수 구현 필수)
- [ ] `ruff check` / `mypy` 통과

## 7. 금지 사항 (Do NOT)

- ❌ `Base.metadata.create_all()` 로 테이블 직접 생성 금지 — 반드시 Alembic 경유
- ❌ DB 접속 정보 하드코딩 금지
- ❌ ERD에 없는 컬럼/인덱스 임의 추가 금지 (vector 컬럼 포함 — 이번 범위 아님)
- ❌ 기존 마이그레이션 리비전 수정 금지 — 새 리비전으로만 작업
- ❌ 호스트 WSL에 PostgreSQL 직접 설치(`apt install postgresql`) 금지 — DB는 반드시 컨테이너로만
- ❌ 볼륨 없는 컨테이너 금지 — 데이터 유실 방지
- ❌ `docker compose down -v` 임의 실행 금지 — 데이터 삭제 명령은 사용자 확인 필수