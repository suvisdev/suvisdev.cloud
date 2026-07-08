# Viewer 앱 — 인증 (Login · Signup)

> **역할:** `groups`, `admins`, `users` 테이블 기반 인증 API.  
> **상위 문서:** [[suvisdev/_docs/CLAUDE]] — 아키텍처 전체 규칙

Titanic(James)과 **동일한 레이어 규칙**을 따른다. 아래는 Viewer만의 특이점만 기록한다.

---

## A. 참조 파일

| 역할 | 파일 |
|------|------|
| Login Router | `adapter/inbound/api/v1/login_router.py` |
| Signup Router | `adapter/inbound/api/v1/signup_router.py` |
| DI | `dependencies/login.py` (`get_secom_db`) |
| Dto | `app/dtos/auth_command_dto.py` |
| ORM — User | `app/dtos/user_model.py` |
| ORM — Admin | `app/dtos/admin_model.py` |
| ORM — Group | `app/dtos/group_model.py` |

---

## B. API 엔드포인트

| 메서드 | 경로 | 역할 |
|--------|------|------|
| `POST` | `/viewer/login/login` | 로그인 |
| `POST` | `/viewer/signup/signup` | 회원가입 |

---

## C. Viewer 특이점

### C.1 DB 세션

```python
from core.matrix.grid_oracle_database_manager import get_secom_db  # Viewer/Secom DB
```

Mova(`get_mova_db`), Titanic(`get_db`)과 다르다.

### C.2 예외 처리 패턴

Viewer는 Repository 에러를 Router에서 `HTTPException`으로 변환한다.

```python
# viewer router
try:
    return (await login.login(schema)).to_schema()
except LoginRepositoryError as e:
    raise HTTPException(status_code=401, detail=str(e))
```

### C.3 테이블 생성 순서

Viewer(SecomBase)는 **Mova보다 먼저** 생성되어야 한다.  
Mova의 `chat`/`picks`/`reviews`가 `users.id`를 FK로 참조하기 때문이다.

### C.4 시드 데이터

`seed_secom_if_empty()` — 앱 시작 시 자동 실행.

| 테이블 | 시드 내용 |
|--------|-----------|
| `groups` | 2개 (일반/관리자 그룹) |
| `admins` | 1개 (초기 관리자) |

### C.5 비밀번호

`bcrypt` 사용. Repository 레이어에서 해싱·검증.  
Router·Interactor에서 평문 비밀번호를 직접 다루지 않는다.

### C.6 수업용 앱 구분

- `friday13th/` — **수업용** 인증 앱. 프로덕션에서 사용하지 않는다.
- `viewer/` — **프로덕션** login/signup 전용.

---

## D. ORM 관계 (SecomBase)

```text
groups (1) ──< admins (N)
groups (1) ──< users (N)
```

- `User.__table__` — Mova cross-metadata FK의 참조 대상.

---

## E. 금지·안티패턴 (Viewer 추가)

| ❌ 금지 | ✅ 대신 |
|--------|--------|
| `friday13th` 경로 참조 | `viewer/` 경로 사용 |
| Router에서 bcrypt 직접 호출 | Repository 레이어에서 처리 |
| Viewer 테이블을 Mova보다 늦게 생성 | `create_tables()` 순서 유지 |
| `get_db()` / `get_mova_db()` 사용 | `get_secom_db()` 사용 |
