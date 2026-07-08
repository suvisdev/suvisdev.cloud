# Mova 앱 — 영화·채팅·랭킹·리뷰 도메인

> **역할:** 영화 저장·조회·채팅·리뷰·랭킹·TMDB 수입 등 Mova 백엔드 API.  
> **상위 문서:** [[suvisdev/_docs/CLAUDE]]  
> **프론트:** `suvis/app/mova` · 채팅 UX `MOVA_CHAT_UX.md`  
> **스키마:** `MOVA_ERD.md`

Titanic(James)과 **동일한 레이어 규칙**을 따른다. 본 문서가 Mova `_docs/` 의 **SSOT**이다.

---

## A. 참조 파일 (실제 경로)

| 역할 | 파일 |
|------|------|
| Router 집약 | `adapter/inbound/api/__init__.py` → `mova_router` |
| Movies | `adapter/inbound/api/v1/studio_movies_router.py` |
| Import | `adapter/inbound/api/v1/import_router.py` |
| Chat | `adapter/inbound/api/v1/market_chat_router.py` |
| Collections | `adapter/inbound/api/v1/collections_router.py` |
| Rankings | `adapter/inbound/api/v1/market_rankings_router.py` |
| Input Port (movies) | `app/ports/input/studio_movies_use_case.py` |
| Interactor (movies) | `app/use_cases/studio_movies_interactor.py` |
| Interactor (import) | `app/use_cases/import_interactor.py` |
| Dto (movies) | `app/dtos/studio_movies_dto.py` |
| Dto (import) | `app/dtos/studio_import_dto.py` |
| Movies PgRepo | `adapter/outbound/pg/movies_pg_repository.py` |
| DI (movies) | `dependencies/studio_movies_provider.py` |
| DI (import) | `dependencies/import_provider.py` |
| LLM | `adapter/outbound/llm/gemini_client.py` · `gemini_recommendation_adapter.py` |
| LLM 포트·오류 | `app/ports/output/llm_output_port.py` · `llm_errors.py` |
| TMDB | `adapter/outbound/http/tmdb_adapter.py` · `tmdb_catalog_adapter.py` · `tmdb_mapper.py` |

### A.1 ORM 매핑 (`MOVA_ERD.md` 동기화)

| 테이블 | 모델 | 경로 |
|--------|------|------|
| `movies` | `MovaMovie` | `adapter/outbound/orm/studio_movies_orm.py` |
| `collections` | `MovaCollection` | `adapter/outbound/orm/market_collections_orm.py` |
| `actors` | `MovaActor` | `adapter/outbound/orm/studio_actors_orm.py` |
| `characters` | `MovaCharacter` | `adapter/outbound/orm/studio_characters_orm.py` |
| `tags` | `MovaTag` | `adapter/outbound/orm/studio_tags_orm.py` |
| `rankings` | `MovaRanking` | `adapter/outbound/orm/market_rankings_orm.py` |
| `chat` | `MovaChat` | `adapter/outbound/orm/market_chat_orm.py` |
| `picks` | `MovaPick` | `adapter/outbound/orm/market_picks_orm.py` |
| `reviews` | `MovaReview` | `adapter/outbound/orm/market_reviews_orm.py` |
| `assistants` | `MovaAssistant` | `adapter/outbound/orm/platform_assistants_orm.py` |

### A.2 도메인 그룹 (`studio_` / `market_` / `platform_`)

| 그룹 | 의미 | 예시 |
|------|------|------|
| `studio_` | 콘텐츠·카탈로그 | movies, actors, characters, tags, search, import |
| `market_` | 추천·흥행 | chat, picks, collections, rankings, reviews |
| `platform_` | 계정·페르소나 | assistants (+ viewer의 users/groups/admins FK) |

---

## B. Mova 특이점

### B.1 Dto → Schema (Titanic과 다름)

Router에서 반드시 `Dto.to_schema()` 후 반환한다.

### B.2 DB 세션

```python
from core.matrix.grid_oracle_database_manager import get_mova_db
```

### B.3 Cross-metadata FK (Viewer)

`chat` · `picks` · `reviews` → `ForeignKey(User.__table__.c.id)`.  
`create_tables()` 순서: **Viewer → Mova**.

### B.4 LLM (Gemini)

- Outbound `gemini_client.py`만 Gemini 호출.
- Interactor는 `RecommendationPort` 경유.
- `LLMError` → 라우터 `try/except` → `HTTPException` (전역 exception_handler 없음).

### B.5 TMDB 수입 (Import)

- `POST /mova/import/tmdb` — `tmdb_id` \| `query` \| `popular_pages`
- Startup: 카탈로그 **5편 미만**이면 popular 2페이지 자동 수입 + `box_office` 랭킹
- slug 규칙: `tmdb-{id}` · 평점 TMDB 10점 → Mova 5점 스케일 (`/2`)
- `TmdbAdapterError` → 라우터 `HTTPException`
- KOFIC: `kofic_adapter.py`만 존재, 파이프라인은 후속

### B.6 `/myself` 엔드포인트

도메인 페르소나 스텁(장식·문서용). **삭제하지 않음.**

| 경로 | 페르소나 |
|------|----------|
| `GET /mova/movies/myself` | 감독 (Director) |
| `GET /mova/import/myself` | 수입 감독 (Import Director) |
| `GET /mova/chat/myself` | 시나리오 작가 (Screenwriter) |
| `GET /mova/rankings/myself` | 프로듀서 (Producer) |

### B.7 Router 집약

`main.py`에서 `mova_router`를 prefix `/mova`로 include.

---

## C. API 도메인 목록

| 도메인 | prefix | 비고 |
|--------|--------|------|
| Movies | `/mova/movies` | 목록·상세 |
| Import | `/mova/import` | TMDB 수입 |
| Search | `/mova/search` | |
| Characters | `/mova/characters` | |
| Tags | `/mova/tags` | |
| Chat | `/mova/chat` | Gemini 추천 |
| Picks | `/mova/picks` | |
| Rankings | `/mova/rankings` | `chat_trend` · `box_office` |
| Reviews | `/mova/reviews` | |
| Collections | `/mova/collections` | CRUD·소속 영화 |
| Assistants | `/mova/assistants` | |

---

## D. 금지·안티패턴

| ❌ | ✅ |
|----|-----|
| Router에서 Dto 직접 반환 | `Dto.to_schema()` |
| Interactor에서 Gemini 직접 호출 | `RecommendationPort` |
| `LLMError` 전역 handler | 라우터 `try/except` |
| 아웃바운드에서 `HTTPException` | 도메인 예외 + 인바운드 변환 |
| `"users.id"` 문자열 FK | `User.__table__.c.id` |
| `dict[str, Any]` · `dict[str, T \| None]`로 Dto·Interactor 전달 | `dataclass` / Pydantic Schema, 필드별 `T \| None` |
| `list[dict[str, str \| None]]` 등 **고정 형태** | `TypedDict` · 소형 dataclass · Schema (`platforms` 등) |
| Schema·API에 불필요한 `"field": null` | `model_config` / 직렬화 시 `exclude_none` · absent는 키 생략 |
| Router·Interactor에 `if` 3단 이상 중첩 | guard return · `match` · 케이스별 함수 |
| Interactor에 긴 `if/elif` 입력 모드 분기 | Command 타입·`match` · 전용 메서드로 분리 |
| `except Exception` · Interactor/Router마다 중첩 `try` | 구체 예외만 · Router **엔드포인트당 1겹** |
| 전역 `exception_handler` (Mova) | 라우터 `try/except` → `HTTPException` (§B.4) |
| Outbound에서 예외 삼키기 | 도메인 예외 raise (`LLMError`, `TmdbAdapterError`) |

### D.1 null · dict (루트 `CLAUDE.md` §5)

- `None`은 **해당 필드에 값이 없음**이 도메인·API 계약에 필요할 때만.
- **경계에서만 raw dict:** TMDB JSON, ORM JSONB 읽기 직후. Mapper·Repository에서 Dto/Schema로 좁힌 뒤 상위 레이어로 전달.
- 동적 맵(예: 메타데이터 키·값 쌍)이 아니면 `dict` 대신 명시적 필드 타입을 쓴다.
- 프론트 타입 규칙: `suvis/_docs/CLAUDE.MD` §C.5.

### D.2 분기 · if/else (루트 `CLAUDE.md` §6)

- **Router:** 입력 검증·`LLMError` 변환은 **앞에서 처리**하고, 정상 흐름은 한 갈래로 유지. 비즈니스 분기는 Interactor에 둔다.
- **Interactor:** `tmdb_id` / `query` / `popular_pages`처럼 **상호 배타 모드**는 `match` 또는 전용 private 메서드. Router에 긴 `elif` 체인 금지.
- **짧은 2갈래** (`found` / `not found`, `count < 5`)는 plain `if/else` — 추상화하지 않는다.
- **Outbound adapter:** HTTP 상태·파싱 실패는 도메인 예외로 raise. Router에서 `try/except`로 HTTP 변환 (§D.3).
- 프론트 분기 규칙: `suvis/_docs/CLAUDE.MD` §C.6.

### D.3 try · except (루트 `CLAUDE.md` §7)

- **Router (인바운드 경계):** 엔드포인트당 **한 겹**. 알려진 outbound 실패만 포착한다.
  - `LLMError` → `HTTPException` (`market_chat_router.py` 등)
  - `TmdbAdapterError` → `HTTPException` (`import_router.py`)
- **전역 `exception_handlers` 사용하지 않음** — §B.4. 동일 HTTP 계약은 라우터 `try/except`로 유지 (`apps/mova/tests/test_llm_error_handling.py`).
- **Interactor:** `try/except`로 HTTP·FastAPI 타입 변환 금지. 실패는 그대로 올리거나 도메인 예외만 처리.
- **Outbound (LLM·TMDB·HTTP):** 외부 API·파싱 실패를 **구체 예외**로 변환해 raise. `except Exception: pass` 금지.
  - JSON 파싱 fallback(`JSONDecodeError`)은 **해당 adapter 내부·짧게**만 허용.
- **Startup / DI (`import_provider.seed_catalog_if_sparse`):** 시드 실패 시 앱 기동은 계속 — `TmdbAdapterError`만 잡고 로그/무시. 비즈니스 요청 경로와 동일하게 취급하지 않는다.
- 프론트 `try/catch`: `suvis/_docs/CLAUDE.MD` §C.7.

---

## E. 진행 상태 (2026-06-26 기준)

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 영화 카탈로그 (movies·actors·characters·tags·search) | ✅ 백엔드 |
| 2 | Chat 추천 + LLM 포트 + picks + 콜드스타트 포트 | ✅ |
| 3 | reviews · rankings(`chat_trend`) · **collections 풀스택** | ✅ 백엔드 |
| Import | TMDB 자동 시드 + `POST /import/tmdb` | ✅ B1 |
| 프론트 | `/mova` 랜딩·메인·movies·title·collections·채팅 UX | ✅ 연결됨 |

**다음 후보:** KOFIC 수입 · 컬렉션 브라우즈 UI · `studio_*` 파일명 Titanic식 정리 · chat 레거시(`chat_reply.py`) 정리

**테스트:** `apps/mova/tests/` — collections, import, chat_trend, LLM 에러

---

## F. 문서 인덱스 (본 폴더)

| 문서 | 용도 |
|------|------|
| **본 파일** | Mova 백엔드 규칙·진행·API SSOT |
| `MOVA_ERD.md` | 테이블·FK·ORM |
| `MOVA_CHAT_UX.md` | 프론트 AI 채팅 UX |
| [`.cursorrules`](.cursorrules) | Cursor 진입 요약 (본 문서 링크) |

**통합·삭제됨 (내용은 본 문서·ERD·suvis로 이전):**  
`260625_mova_progress.md` · `260506_cine_app_naming.md` · `mova_blueprint.md` · `mova_screen_design.md` · `mova-casting.md`  
(초기 FlutterFlow 프로토타입·네이밍 브레인스토밍·중복 진행 보고서)

---

## G. 프론트 연결 (`suvis/app/mova`)

| 경로 | API 프록시 |
|------|------------|
| `/mova` | 랜딩 |
| `/mova/main` | chat, rankings |
| `/mova/movies` | `GET /mova/movies` |
| `/mova/title/[slug]` | `GET /mova/movies/{slug}` |
| `/mova/collections` | collections API |
| `/api/mova/*` | Next.js → `:8000/mova/*` |

영화 상세 로더: `suvis/lib/load-mova-title.ts` (API + 정적 카탈로그 병합).
