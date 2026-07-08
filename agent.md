# cloud.suvisdev — 에이전트 안내

## Titanic 모듈 — 사용할 경로 (삭제·옛 경로 사용 금지)

| 역할              | 경로                                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------------- |
| CSV 업로드 API     | `POST /api/titanic/james/upload` → `crew_james_director_router.py`                                                        |
| Schema          | `adapter/inbound/api/schemas/crew_james_director_schema.py`                                                               |
| 입력 포트 (ABC)     | `app/ports/input/crew_james_director_use_case.py`                                                                         |
| 업로드 유스케이스       | `app/use_cases/crew_james_director_interactor.py`                                                                         |
| 업로드 호출 흐름       | `crew_james_director_router` → `JamesInteractor` → `crew_james_director_repository` → `crew_james_director_pg_repository` |
| 업로드 출력 포트 (ABC) | `app/ports/output/crew_james_director_repository.py`                                                                      |
| 업로드 DB          | `adapter/outbound/pg/crew_james_director_pg_repository.py`                                                                |
| Person ORM      | `adapter/outbound/orm/passenger_rose_model_orm.py`                                                                        |
| Booking ORM     | `adapter/outbound/orm/passenger_jack_trainer_orm.py`                                                                      |
| Walter 소개 API   | `GET /api/titanic/walter/myself` → `crew_walter_roaster_router.py`                                                        |
| Walter Schema   | `adapter/inbound/api/schemas/crew_walter_roaster_schema.py`                                                               |
| Walter 입력 포트    | `app/ports/input/crew_walter_roaster_use_case.py`                                                                         |
| Walter 유스케이스    | `app/use_cases/crew_walter_roaster_interactor.py`                                                                         |
| Walter 출력 포트    | `app/ports/output/crew_walter_roaster_repository.py`                                                                      |
| Walter DB       | `adapter/outbound/pg/crew_walter_roaster_pg_repository.py`                                                                |
| DTO             | `app/dtos/crew_james_director_dto.py`, `crew_walter_roaster_dto.py`                                                       |
| DI              | `dependencies/{schema_base}_provider.py` — 예: `crew_smith_captain_provider.py` → `get_smith_captain`                      |

### Schema 파일명 = 레이어 접두·접미사 기준

| schema | router | use_case | interactor | repository | pg_repository | dependencies |
|--------|--------|----------|------------|------------|---------------|--------------|
| `crew_james_director_schema` | `crew_james_director_router` | `crew_james_director_use_case` | `crew_james_director_interactor` | `crew_james_director_repository` | `crew_james_director_pg_repository` | `crew_james_director_provider.py` |
| `crew_walter_roaster_schema` | `crew_walter_roaster_router` | … | … | … | … | `crew_walter_roaster_provider.py` |
| `crew_andrews_architect_schema` | `crew_andrews_architect_router` | … | … | … | … | `crew_andrews_architect_provider.py` |
| `crew_hartley_violin_schema` | `crew_hartley_violin_router` | … | … | … | … | `crew_hartley_violin_provider.py` |
| `crew_smith_captain_schema` | `crew_smith_captain_router` | … | … | … | … | `crew_smith_captain_provider.py` |
| `crew_lowe_boat_schema` | `crew_lowe_boat_router` | … | … | … | … | `crew_lowe_boat_provider.py` |
| `passenger_cal_tester_schema` | `passenger_cal_tester_router` | … | … | … | … | `passenger_cal_tester_provider.py` |
| `passenger_isidor_couple_schema` | `passenger_isidor_couple_router` | … | … | … | … | `passenger_isidor_couple_provider.py` |
| `passenger_jack_trainer_schema` | `passenger_jack_trainer_router` | … | … | … | … | `passenger_jack_trainer_provider.py` |
| `passenger_rose_model_schema` | `passenger_rose_model_router` | … | ORM: `passenger_rose_model_orm` | … | … | `passenger_rose_model_provider.py` |
| `passenger_ruth_validation_schema` | `passenger_ruth_validation_router` | … | … | … | … | `passenger_ruth_validation_provider.py` |
| `passenger_molly_scaler_schema` | `passenger_molly_scaler_router` | … | … | … | … | `passenger_molly_scaler_provider.py` |

ORM(James 업로드): `passenger_rose_model_orm`(Person), `passenger_jack_trainer_orm`(Booking)

## Viewer 인증 — login / signup (`friday13th`는 수업용, 인증은 viewer)

| 역할 | 경로 |
|------|------|
| Router 집약 | `adapter/inbound/api/__init__.py` → `viewer_router` (`main.py` 1회 등록) |
| 로그인 API | `POST /viewer/login/login` → `v1/login_router.py` |
| 로그인 DI | `dependencies/login_provider.py` → `get_login_use_case` |
| 로그인 흐름 | `login_router` → `LoginInteractor` → `login_pg_repository` |
| 회원가입 API | `POST /viewer/signup/signup` → `v1/signup_router.py` |
| 회원가입 DI | `dependencies/signup_provider.py` → `get_signup_use_case` |
| 계정 ORM | `adapter/outbound/orm/` — `group_orm`, `admin_orm`, `user_orm` |
| DTO | `app/dtos/auth_command_dto.py`, `role.py`, `user_profile.py` |

## Mova — ERD·문서

- `suvisdev/apps/mova/_docs/MOVA_ERD.md` — Mova ERD **단일 문서** (mermaid + `mova-erd.png` 미리보기)

## 존재하지 않음 (참조하지 말 것)

- `/friday13th/jason/*`, `jason_router`, `JasonInteractor` (login/signup으로 이전됨)
- `suvisdev/apps/titanic/app/walter_reader.py` (삭제됨)
- `suvisdev/apps/titanic/app/use_cases/james_command.py` (삭제됨 — `crew_james_director_interactor.py` 사용)
- `mova/adapter/inbound/api/http_errors.py`, `gemini_reply.py` (삭제됨 — Titanic 스타일 direct `await`, Gemini는 `outbound/llm/gemini_client.py`)
- `viewer/adapter/inbound/api/http_errors.py`, `dependencies/login.py`, `dependencies/signup.py` (삭제됨 — `*_provider.py`, `api/__init__.py` lazy router)
- `viewer/app/dtos/*_model.py` (삭제됨 — ORM은 `adapter/outbound/orm/`)
- `core/matrix/oracle_database.py`, `keymaker_api.py` (삭제됨 — `grid_oracle_database_manager.py`, `vauly_keymaker_secret_manager.py`)
- `docs/` · `vault/` 위키 경로 (이전됨 — `suvisdev/_claude/`, `apps/*/_docs/` 사용)
- `services/cloud.suvisdev.agora/...` (이 repo 아님)
