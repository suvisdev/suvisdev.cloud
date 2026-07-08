# Titanic 앱 — 헥사고날 기준선

> **역할:** CSV 업로드(James)·조회(Walter) — 전체 백엔드 앱의 **레이어 기준선**.  
> **상위 문서:** [[suvisdev/_docs/CLAUDE]] — 아키텍처 전체 규칙

새 앱(mova, viewer 등)을 만들 때 이 앱의 레이어 구조를 그대로 복사한다.

---

## A. 참조 파일 (기준선 구현)

| 역할 | 파일 |
|------|------|
| Router | `adapter/inbound/api/v1/crew_james_director_router.py` |
| Input Port | `app/ports/input/crew_james_director_use_case.py` |
| Interactor | `app/use_cases/crew_james_director_interactor.py` |
| Output Port | `app/ports/output/crew_james_director_repository.py` |
| PgRepository | `adapter/outbound/pg/crew_james_director_pg_repository.py` |
| DI | `dependencies/crew_james_director_provider.py` |
| DTO | `app/dtos/crew_james_director_dto.py` (`PersonCommand`, `JamesResponse`) |
| ORM | `adapter/outbound/orm/titanic_model.py` |
| Router 집약 | `adapter/inbound/api/__init__.py` → `titanic_router` |

---

## B. Titanic 특이점

### B.1 DTO = HTTP 계약 (변환 없음)

Mova와 달리 `JamesResponse` / `WalterResponse`가 곧 OpenAPI 응답 계약이다.  
Router에서 `Dto.to_schema()` 호출 없이 바로 반환한다.

```python
# titanic router (표준)
return await walter.introduce_myself(schema)  # WalterResponse 직접 반환
```

### B.2 DB 세션

```python
from core.matrix.grid_oracle_database_manager import get_db  # Titanic DB
```

- Mova는 `get_mova_db()`, Viewer는 `get_secom_db()` — Titanic은 `get_db()`.

### B.3 테이블 생성 순서

`create_tables()`에서 **Titanic이 첫 번째**로 생성된다 (`TitanicBase`).  
Mova·Viewer보다 먼저 생성되어야 하는 의존성은 없지만 순서를 바꾸지 않는다.

### B.4 ERD

[`TITANIC_ERD.md`](TITANIC_ERD.md) 참조.

---

## C. 앱 내 라우터 목록

| 라우터 파일 | prefix | 담당 |
|------------|--------|------|
| `crew_james_director_router.py` | `/titanic/james` | CSV 업로드 |
| `crew_walter_director_router.py` | `/titanic/walter` | 승객 조회 |
| `crew_smith_captain_router.py` | `/titanic/smith` | 선장 채팅·소개 |

---

## D. Smith Captain 특이점

Smith Captain은 **LLM 채팅** 기능을 포함한다.

- `chat()` — Ollama EEVE 모델과 대화 (`adapter/outbound/llm/` 경유 예정)
- `introduce_myself()` — 승객 정보 기반 소개

`SmithCaptainInteractor`는 `JackTrainerUseCase`, `RoseModelUseCase`를 DI로 받는다.  
Interactor 내부에서 직접 인스턴스화하지 않는다 (DIP).

---

## E. 새 Titanic 엔드포인트 추가 시

백엔드 CLAUDE.md [체크리스트](../../../CLAUDE.md#l-새-api-추가-체크리스트)를 따르되,  
`response_model`에 Schema 대신 **`JamesResponse` / `WalterResponse`** DTO를 직접 사용할 수 있다.



## 타이타닉 도메인 문서 연결

* 타이타닉 도메인 문서 연결
* 타이타닉 피처 정리 : [[titanic-features]]
* 타이타닉 머신 러닝 : [[titanic-machine-learning]]
* 타이타닉 ERD : [[titanic-erd]]
* 타이타닉 NF :  [[titanic-nf]]
* 타이타닉 알고리즘 : [[titanic-algorithm]] 
* 