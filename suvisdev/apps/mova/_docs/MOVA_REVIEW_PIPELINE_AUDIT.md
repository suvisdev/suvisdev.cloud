# MOVA 리뷰 이해 파이프라인 현황 진단 (2026-08-10)

> **진단 결과: A — 별점만 추천에 (간접) 반영, 리뷰 텍스트는 UI 표시 전용**
>
> 조사 범위: `apps/mova/` 전체 + `apps/ontology/`(Hub RAG·감정 분석) +
> `alembic/versions/` + `scripts/` + `suvis/`(프론트). **읽기 전용 조사**로,
> 이 문서 작성 시점에 코드 변경은 없다.

## 0. 한 줄 요약

리뷰 텍스트(`reviews.body`)를 읽는 곳은 **마이페이지 조회**와 **영화별 리뷰
목록** 두 군데뿐이고, 둘 다 화면에 그대로 뿌리는 경로다. 임베딩·감정 분석·
검색 인덱스 어디에도 들어가지 않는다.

다만 "별점도 안 쓴다"는 아니다 — 리뷰 저장 시 `movies.rating`을 리뷰 평균으로
덮어쓰고, 추천 후보 조회가 전부 `ORDER BY movies.rating DESC`라 **별점은 후보
순위에만 간접 반영**된다. 사용자별 취향 벡터 같은 건 없다.

```text
[별점]  reviews.rating ──평균──▶ movies.rating ──ORDER BY──▶ 추천 후보 순위   ✅ 동작 중
[본문]  reviews.body   ─────────────────────────────────────▶ 화면 표시로 끝   ❌ 소비처 없음
```

---

## 1. 데이터 모델

### 1.1 `reviews` 테이블

`apps/mova/adapter/outbound/orm/market_reviews_orm.py:12-43`

| 컬럼 | 타입 | 비고 |
|------|------|------|
| `id` | Integer PK | 자동증가 |
| `user_id` | Integer FK → `users.id` (CASCADE) | index |
| `movie_id` | Integer FK → `movies.id` (CASCADE) | index |
| `rating` | Float **nullable** | 0.5~5.0으로 저장 시 클램프 |
| `body` | Text **nullable** | 감상평 본문 |
| `created_at` / `updated_at` | DateTime(tz) | server_default now() |

제약: `UNIQUE(user_id, movie_id)` = `uq_reviews_user_movie` (user+movie당 1건,
재제출은 UPDATE)

**embedding · sentiment_score · 감정 관련 컬럼: 없음.**

### 1.2 pgvector

확장은 **쓰고 있다.** 단 `reviews`가 아닌 다른 테이블에서다.

| 테이블 | 컬럼 | 위치 |
|--------|------|------|
| `movies` | `embedding Vector(768)` | `apps/mova/adapter/outbound/orm/studio_movies_orm.py:71-75`, 마이그레이션 `alembic/versions/41f584bfcb4e_mova_v2_schema.py:107-112` |
| `hub_knowledge` | `embedding Vector(768)` | `alembic/versions/20260729_0002_create_hub_knowledge.py:29-47` |
| `dispatch_inbox` | `embedding` | `alembic/versions/20260702_0003_add_dispatch_inbox_embedding.py:26` |

확장 생성: `db/init/001_create_vector_extension.sql:1` + 위 두 마이그레이션의
`CREATE EXTENSION IF NOT EXISTS vector`.

### 1.3 벡터 인덱스 — **저장소 전체에 없음**

`HNSW`/`IVFFlat` grep 결과가 ORM 주석 한 줄뿐이다:
`studio_movies_orm.py:74` "추천용 임베딩. HNSW/IVFFlat 인덱스는 **별도 리비전**"
— 그 별도 리비전이 존재하지 않는다. 즉 모든 벡터 검색이 **순차 스캔**이다.

### 1.4 reviews 관련 Alembic 마이그레이션 (전부 2개)

| 리비전 | 내용 |
|--------|------|
| `alembic/versions/20260604_0000_create_baseline_v1_tables.py:235-253` | 최초 생성. 당시엔 `action_type`·`action_at`을 갖고 행동 로그를 겸했다 |
| `alembic/versions/41f584bfcb4e_mova_v2_schema.py:145-160` | `created_at`/`updated_at` 추가, `action_type`/`action_at` 제거, `uq_reviews_user_movie` 추가. 행동 로그는 `user_actions` 테이블로 분리 |

---

## 2. 리뷰 생성/저장 파이프라인

- **엔드포인트**: `POST /mova/reviews`
  — `apps/mova/adapter/inbound/api/v1/market_reviews_router.py:46-57`
  (그 외 `POST /activity`, `GET /by-movie/{id}`, `GET /rating/{id}`,
  `PATCH /{id}`, `DELETE /{id}`)
- **Interactor**: `apps/mova/app/use_cases/market_reviews_interactor.py:25-43`
  — `watched` 기록 게이트 → 빈 제출 거부 → upsert. **그게 전부다.**
- **PgRepository**: `apps/mova/adapter/outbound/pg/market_reviews_pg_repository.py:68-88`

### 부가 처리 여부

| 항목 | 상태 |
|------|------|
| 임베딩 생성 호출 | **없음** |
| 감정 분석 호출 | **없음** |
| 태그/키워드 추출 | **없음** |
| 백그라운드 작업 큐 | **없음** (Celery/RQ/ARQ 부재) |

유일한 부가 처리는 `_update_movie_rating()`
(`market_reviews_pg_repository.py:202-216`) — 해당 영화의 리뷰 평균으로
`movies.rating`을 덮어쓴다. add/update/delete 세 곳에서 호출된다
(`:80`, `:162`, `:199`).

> mova의 백그라운드는 APScheduler 기반 임포트·랭킹 스케줄러뿐이고
> (`apps/mova/adapter/inbound/scheduler/`), 리뷰와는 무관하다.

---

## 3. 추천 로직에서의 리뷰 소비

- **진입점**: `apps/mova/app/use_cases/market_chat_interactor.py:49-170`
  (`POST /mova/chat`)

```text
인텐트 분류(semantic router)
  └ general/crud → Gemini(Mycroft) 직행, 추천 없음
인텐트 추출(Kiwi, CPU-bound → to_thread)          :65
Hub RAG 벡터 검색(hub_knowledge, k=8)             :70
  └ 0건이면 태그·배우 키워드 폴백                  :103-110
     └ 그것도 0건이면 인기작 폴백(rating DESC)
LLM 추천 생성(lora | gemini | exaone …)           :113-122
chat + picks 저장                                  :126-140
```

### 3.1 사용자 취향 벡터 구성 — **벡터 자체가 없다**

프롬프트에 문자열로 붙는 개인화 신호는 딱 셋이다.

| 신호 | 출처 | 프롬프트 조립 |
|------|------|---------------|
| 선호 장르 | `users.preferred_genres` (가입 시 선택) — `apps/mova/adapter/outbound/pg/user_preference_pg_repository.py:17-28` | `apps/mova/adapter/outbound/llm/chat_prompt.py:76-86` |
| 최근 질의 3건 | `chats.refined_query` — `apps/mova/adapter/outbound/pg/market_chat_pg_repository.py:150-163` | `chat_prompt.py:104-110` |
| 후보 카탈로그 | RAG 히트 또는 태그/배우 매칭 | `chat_prompt.py:88-102` |

**별점 집계도, 리뷰 텍스트 임베딩도, 좋아요 기반 영화 임베딩 평균도 없다.**

### 3.2 리뷰가 추천에 닿는 유일한 경로 (간접)

`reviews.rating` 평균 → `movies.rating` → 후보 **정렬**:

- `market_chat_pg_repository.py:99` (태그 매칭 후보 정렬)
- `market_chat_pg_repository.py:146` (인기작 폴백 정렬)
- `studio_search_pg_repository.py:44`
- `movies_pg_repository.py:151-169` (`min_rating` 필터 + rating DESC 정렬)

### 3.3 유사도 계산

| 경로 | 방식 | 위치 |
|------|------|------|
| Hub RAG | cosine distance, `score = 1 - distance`, 임계값 **0.15** | `apps/ontology/adapter/outbound/repositories/hub_knowledge_repository.py:49-66`, `apps/ontology/app/use_cases/hub_rag_interactor.py:21,52-76` |
| 유사 영화 `GET /mova/movies/{slug}/similar` | `movies.embedding` cosine | `apps/mova/adapter/outbound/pg/movies_pg_repository.py:327-355`, 라우터 `studio_movies_router.py:41-50` |

**하이브리드 없음** — RAG 벡터 실패 시 키워드로 넘어가는 *순차 대체* 구조다.

### 3.4 임베딩 입력 텍스트에 리뷰가 없다

| 대상 | 입력 텍스트 | 위치 |
|------|-------------|------|
| `movies.embedding` | title / 장르 / 출연(5명) / synopsis | `scripts/backfill_movie_embeddings_cli.py:53-64` |
| `hub_knowledge` (임포트 훅) | overview / 장르 / 출연 | `apps/mova/app/use_cases/import_interactor.py:178-193` |
| `hub_knowledge` (1회 백필) | overview / 장르 / 출연 | `scripts/backfill_hub_movies_rag.py:33-42` |

셋 다 **리뷰 텍스트 미포함**.

### 3.5 LoRA 재학습 데이터에도 없다

`scripts/export_chat_training_dataset.py` — `chat` + `picks`만으로
(prompt, completion) JSONL을 만든다. 리뷰는 학습 신호에 들어가지 않는다.

---

## 4. 검색

- `GET /mova/search`: `tags.label` + `movies.title` **ILIKE만**
  — `apps/mova/adapter/outbound/pg/studio_search_pg_repository.py:24-55`
- **Full-text search(tsvector): 저장소 전체에 0건**
  (`tsvector` / `to_tsquery` / `plainto_tsquery` grep 무결과)
- vector search: 검색 엔드포인트에는 없다. 벡터는 채팅(RAG)·유사영화 두 경로뿐
- **리뷰 텍스트는 어떤 검색 인덱스에도 없다**

---

## 5. 감정 분석 흔적

### mova — **없음**

`apps/mova/` 전체 grep(`sentiment|emotion|polarity|tone|감정`) 히트 3건이
전부 무관하다:

- `adapter/outbound/llm/intent_extraction.py:23,25` — 인텐트 분류 프롬프트의
  `"mood": 감정·분위기` 설명 문구
- `adapter/outbound/llm/chat_prompt.py:32` — "感情 말고 감정으로 쓰라"는
  한자 금지 지시

### ontology — **완결된 구현이 이미 있으나 연결선이 없음**

- `apps/ontology/app/use_cases/sentiment_analysis_interactor.py`
- `apps/ontology/adapter/inbound/api/v1/sentiment_analysis_router.py`
- `apps/ontology/adapter/outbound/resource_adapters/echo_sentiment/echo_sentiment_adapter.py`
- 학습 스크립트: `scripts/train_echo_sentiment.py`,
  `scripts/prepare_echo_sentiment_dataset.py`

mova에서 이 포트/유스케이스를 import하는 곳: **0건**.

---

## 6. 갭 분석

| 항목 | 상태 |
|------|------|
| 리뷰 텍스트 임베딩 파이프라인 | ❌ 컬럼·생성 호출·백필 전부 없음 |
| 사용자 취향 벡터(리뷰 기반) | ❌ 벡터 개념 자체가 사용자 측에 없음 (현재는 `preferred_genres` 문자열 + 최근 질의 3건) |
| 감정 축(sentiment score, aspect tags) | ❌ mova에 없음 (ontology에 재사용 가능한 구현체 존재, 연결만 필요) |
| 자연어 검색(RAG) 파이프라인 | ⚠️ 영화 개요 기준으로는 **있음**(`hub_knowledge`). 리뷰는 리트리버 소스에 미포함 |
| 리뷰 텍스트가 검색·추천 양쪽 인덱스에 | ❌ 양쪽 다 없음 |
| 별점 → `movies.rating` → 후보 정렬 | ✅ 유일하게 동작 중인 리뷰 소비 경로 |

### 부수 발견 2건

1. **HNSW/IVFFlat 인덱스가 하나도 없다.** `movies`(2014행)·`hub_knowledge`
   규모에선 아직 견디지만, 리뷰 임베딩을 추가하면 행 수가 자릿수로 늘어난다
   — 인덱스 리비전이 선행돼야 한다.
2. **`movies.embedding` 백필이 962/2014에서 중단** 상태
   (`_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md:797-806`, Gemini 무료 티어
   일일 한도). ⚠️ 이건 **문서 기재값이고 DB로 실측한 값이 아니다** — 조사
   시점 로컬 WSL에서 docker CLI·psql 접근이 안 됐다. 착수 전 실측할 것.

---

## 7. 다음 스텝 추천 (3순위 이내)

### 1순위 — `reviews.embedding Vector(768)` + 저장 시 임베딩 생성

기존 `movies.embedding` 경로를 그대로 복제하면 되는 최소 변경이다
(`GeminiEmbeddingAdapter` 재사용, 백필 스크립트 패턴 동일).

**선행 결정 1건**: 리뷰 저장이 동기 LLM 호출을 타면 `POST /mova/reviews`
응답이 느려진다. 저장은 즉시 반환하고 임베딩은 뒤로 미루는 구조를 먼저
정해야 하는데, 현재 저장소에 작업 큐가 없으므로 이 선택 자체가 설계
결정이다 — FastAPI `BackgroundTasks` / 주기 백필 스크립트 / 큐 도입.

### 2순위 — 사용자 취향 벡터 = 본인 리뷰 임베딩의 별점 가중 평균

1순위가 끝나면 순수 SQL/numpy로 계산 가능하고, `movies.embedding`과 cosine
하나로 개인화 후보를 뽑아 지금의 RAG 후보와 합칠 수 있다. 여기서 처음으로
"리뷰가 추천의 핵심 입력"이라는 전제가 실제 코드가 된다.

**전제**: `movies.embedding` 백필(962/2014)을 먼저 끝내야 절반이 후보에서
조용히 빠지지 않는다.

### 3순위 — 감정 축은 ontology의 기존 sentiment 유스케이스를 Hub 경유로 연결

새로 만들 게 아니라 이미 있다. 다만 Spoke→Spoke 직접 import 금지
(`suvisdev/CLAUDE.md` §O.4)라 mova가 Hub(ontology)의 **입력 포트**를 쓰는
형태여야 하고, 이 방향(Spoke→Hub)은 허용된다.

실익은 **별점 5점인데 본문이 "기대보다 별로"인 불일치 케이스**를 잡는 것이라,
1·2순위 이후 우선순위로 둔다.

---

## 부록: 조사 방법·한계

- 모든 경로는 grep → 실제 호출부 추적까지 확인했다(설정만 있고 안 쓰이는
  경우를 배제하기 위함).
- **DB 실측은 하지 못했다** — 이 WSL 배포판에서 `docker` CLI가 없고
  (Docker Desktop WSL 통합 비활성), `psql`도 없다. 따라서 §1의 스키마는
  **ORM + 마이그레이션 기준**이며 프로덕션 실제 컬럼과의 대조는 미확인이다.
  DB 실측이 필요하면 `python scripts/verify_db_tables.py` 또는 pgAdmin.
