# harvester 2차 스펙(TMDB/KOBIS + 동적 키워드) + mova ingest-harvest 진행 상황

컨텍스트가 끊길 경우를 대비한 재개용 메모. 최신 진행 상황은 이 파일 상단을 갱신한다.

## 현재 상태 — Track A/B 전부 완료 (2026-07-20)

Track A(harvester 2차 스펙)와 Track B(mova ingest-harvest) 모두 완료했다. 도커
재빌드 + 실 DB 수동 검증까지 전부 끝났다.

### 2026-07-20 — 도커 재빌드 + 실 DB 수동 검증 완료

- `docker compose --env-file suvisdev/.env up -d --build backend` 재빌드, 정상 기동
  확인(`Mova DB 엔진 초기화 성공`, `Application startup complete`)
- `.env`에 `KOFIC_API_KEY`/`TMDB_API_KEY` 둘 다 이미 설정돼 있음을 확인
- 실 스크랩 → ingest → DB 확인까지 end-to-end 검증:
  - `python scripts/harvester_cli.py scrape -s kobis -k daily -l 10` → 10건 →
    `datasets/kobis_daily_20260720.jsonl`
  - `python scripts/harvester_cli.py scrape -s tmdb -k 인터스텔라 -l 5` → 4건 →
    `datasets/tmdb_인터스텔라_20260720.jsonl`
  - `python scripts/mova_ingest_harvest.py {각 경로}` 실행 →
    kobis: `total=10 ingested=10 matched=3 unmatched=7`,
    tmdb: `total=4 ingested=4 matched=0 unmatched=4`
  - `psql`로 `hub_knowledge` 테이블 직접 조회: `source='kobis'` 10건, `source='tmdb'`
    4건 실제 적재 확인 (`SELECT source, count(*) FROM hub_knowledge WHERE source IN
    ('kobis','tmdb') GROUP BY source;`)
- 남은 작업 없음. harvester 2차 스펙 + mova ingest-harvest 트랙 종료.

### 이번 라운드에서 새로 한 작업 (Task #32 마무리 + Track B 전체)

- `harvester_provider.py`: `build_keyword_source(source_id, *, rate)` 추가, `UnknownKeywordSourceError`
  추가, `build_crawl_schedule_use_case()`에 `build_keyword_source=_build_keyword_source` 주입
- `harvester_router.py`: `MissingApiKeyError` → `HTTPException(503, ...)` 캐치를 scrape/crawl
  둘 다에 추가
- **API 키 이름 정정**: 애초에 kobis용으로 `KOBIS_API_KEY`라는 새 환경변수를 만들었는데,
  `apps/mova/adapter/outbound/http/kofic_adapter.py`가 이미 동일 키를 `KOFIC_API_KEY`로
  쓰고 있는 걸 발견해서 `api_keys.py`의 `get_kobis_api_key()`가 `KOFIC_API_KEY`를 읽도록
  통일함(같은 값을 두 변수에 중복 저장하지 않기 위함). 관련 테스트 3곳도 같이 수정.
  `.env.example`에는 이미 `TMDB_API_KEY`/`KOFIC_API_KEY`가 있었으므로 주석만 보강(새 키
  추가 안 함).
- mypy --strict 재검증 중 발견한 사전 존재 위반 수정(Track A 커밋에는 있었지만 strict
  통과 못 했던 부분): `kobis_client.py`/`kobis_scraper.py`/`tmdb_scraper.py`의 bare `dict`
  → `dict[str, Any]`, `KeywordSourcePort`에 `SiteScraperPort`와 동일한 고정 생성자
  (`fetcher`/`rate_limiter`) 추가하고 `KobisBoxofficeTitleSource`의 중복 `__init__` 제거
- Track A 전체 재검증 완료: pytest 46/46, ruff 클린, mypy --strict 클린(touched 파일
  기준 — 나머지 mypy 에러는 전부 core/matrix, viewer 등 이번 세션과 무관한 기존 파일),
  `python scripts/harvester_cli.py sites` → kobis/tmdb 노출 확인, DIP grep(ontology
  app/domain에 httpx/redis/spoke import 없음) 확인
- **Track B(mova ingest-harvest) 전체 신규 구현**:
  - `apps/mova/app/dtos/harvest_ingest_dto.py` — `HarvestRow`, `HarvestIngestResultDto`
  - `apps/mova/app/ports/output/harvest_reader_port.py` — `HarvestReaderPort`
  - `apps/mova/adapter/outbound/harvest/harvest_jsonl_reader.py` — `HarvestJsonlReaderAdapter`
    (json.loads만 사용, harvester/ontology 모듈 import 없음 — grep+테스트로 확인)
  - `apps/mova/app/ports/input/harvest_ingest_use_case.py` — `HarvestIngestUseCase`
  - `apps/mova/app/use_cases/harvest_ingest_interactor.py` — `HarvestIngestInteractor`.
    source별 content 매핑(kowiki=content+sections, tmdb=content+infobox,
    kobis=content+metrics, 그외=content 그대로), `movies.find_by_title()`로 매칭
    시도(정확 제목 일치, DB에 링크 저장 안 함) + matched/unmatched 카운트,
    `HubRagUseCase.ingest_movie()`로 임베딩+upsert(dedup은 기존 source_ref 기준
    upsert가 그대로 처리)
  - `scripts/mova_ingest_harvest.py` — CLI 진입점. `python scripts/mova_ingest_harvest.py
    {jsonl경로}`. `export_chat_training_dataset.py`/`backfill_hub_movies_rag.py`와
    동일한 DI 패턴(reload_env → get_mova_session_factory → 세션 내 조립)
  - 테스트 9개(`test_harvest_jsonl_reader.py` 3개, `test_harvest_ingest_interactor.py`
    6개) 전부 통과, ruff/mypy --strict 클린, harvester 모듈 import 없음 grep 확인
  - **중요 설계 판단**: `HubRagInteractor.search_movies()`는 `source="mova_movie"`로
    고정 필터링돼 있어서, harvest 데이터(source=kowiki/google_news/kobis/tmdb로 적재)는
    지금 당장은 mova 채팅 RAG 검색에 안 걸린다. 이건 의도된 설계다 — 사용자가 "mova
    채팅/추천 응답 로직 자체는 이번에 변경 안 한다, RAG 저장소에 적재하는 것까지만"이라고
    명시했으므로 검색 로직(search_movies)은 건드리지 않았다. 나중에 harvest 데이터를
    실제로 채팅에서 검색하려면 별도 작업으로 source 필터를 확장해야 함.
  - 사전 존재하는 무관한 실패 확인함(내가 안 건드림): `apps/mova/tests/test_import_interactor.py`
    2건이 `ImportInteractor.__init__()`이 07-14에 인자 2개(box_office, hub_rag) 늘어난 뒤
    테스트가 갱신 안 돼서 깨져 있음(이번 세션과 무관, 07-14 커밋 vs 07-14 테스트 파일 시점
    확인함). `apps/mova/tests/test_llm_error_handling.py`는 `google.generativeai` 미설치로
    스크래치 venv에서 collection 자체가 안 됨(이것도 무관).

### 다음에 할 일 — 전부 완료 (2026-07-20)

1. [x] **도커 재빌드** — Track A 전체(kobis/tmdb 포함) + Track B(mova ingest-harvest) +
   `custom_url_scrape_out_path` 경로 수정까지 전부 한 번에 반영해서 재빌드
   (`docker compose --env-file suvisdev/.env up -d --build backend`)
2. [x] **실 DB 수동 통합 검증**: 실제로 `scrape`/`crawl-batch`로 kobis/tmdb JSONL 생성 →
   `python scripts/mova_ingest_harvest.py {경로}` 실행 → hub_knowledge 테이블에 실제로
   들어갔는지 확인 (matched/unmatched 카운트 출력 확인)
3. [x] `.env`(실제 파일, `.env.example` 아님)에 `KOFIC_API_KEY`가 이미 있는지 확인 —
   mova가 이미 쓰고 있었으므로 아마 있을 것, 없으면 사용자에게 요청

## 확정된 설계 (사용자와 합의 완료, 재질문 불필요)

- **harvester(ontology)는 SUVIS 공용 수집 인프라** — 산출물은 JSONL까지. mova 등 특정
  앱의 DB/모듈을 import하거나 직접 적재하지 않는다. `ScrapedRecord`는 앱 중립 유지
  (sections/infobox/metrics/external_ids 전부 Optional).
- **mova는 별도로 `ingest-harvest` 유스케이스를 추가** — harvester 코드는 일절 수정하지
  않고, JSONL "파일 포맷"만을 계약으로 삼는다. `mova/adapter/outbound/harvest/` 쪽에서는
  `ontology.app.dtos.scrape_dto`나 `ontology.adapter.outbound.scraper.*`를 import하면
  안 됨(직접 `json.loads`로 읽음). 단, `ontology`의 **기존 Hub RAG 인프라**
  (`HubRagInteractor`, `HubKnowledgeUpsertCommand`, `OllamaEmbeddingAdapter`,
  `HubKnowledgeRepository`)는 harvester가 아니라 Hub 자체 소유라 import 허용(Spoke→Hub).
- 진입점: `python -m apps.mova ingest-harvest {jsonl경로}`는 이 저장소 sys.path 구조와
  안 맞아서(1차 harvester CLI 때와 동일한 이유) `scripts/mova_ingest_harvest.py`로
  조정 예정 (scripts/harvester_cli.py와 동일한 sys.path 삽입 패턴).
- **movies 테이블에 tmdb_id/kobis_movie_cd 컬럼이 없음** (`mova/adapter/outbound/orm/studio_movies_orm.py`
  확인함, slug/title/release_year/rating/poster_url/platforms/age_rating/embedding/collection_id
  뿐). "external_ids로 매칭"은 스키마 변경 없이 기존 `movies_pg_repository.find_by_title()`
  (정확히 일치하는 title 검색)로 대체 — 매칭은 리포트 카운트 용도일 뿐 DB에 링크를
  새로 저장하지 않음.
- **hub_knowledge.upsert()는 이미 source_ref(=url) 기준 upsert**
  (`on_conflict_do_update`) — 중복 적재 방지 요구사항은 별도 코드 없이 그대로 재사용.
- KOBIS 상세 API는 실제로 "줄거리" 필드가 없음(공식 API 한계) — content는 감독/장르/
  관람등급/상영시간으로 구성(실측 가능한 필드만).
- VisitedStorePort의 `url` 파라미터를 kobis dedup에선 `movieCd:targetDt` 문자열로 씀
  (실제 URL 아님, 포트 재사용 위한 의도적 선택).

## 완료 (Track A — ontology harvester)

- [x] `ScrapedRecord`에 `external_ids`, `metrics` 필드 추가 + 직렬화 테스트
      (`apps/ontology/app/dtos/scrape_dto.py`, `test_scrape_dto_serialization.py`)
- [x] API 키 로더: `apps/ontology/adapter/outbound/config/api_keys.py`
      (`get_tmdb_api_key()`, `get_kobis_api_key()`, `MissingApiKeyError`)
- [x] `apps/ontology/adapter/outbound/scraper/kobis_client.py` (공유 HTTP client:
      `fetch_daily_boxoffice`, `fetch_movie_detail`, `yesterday_kst`)
- [x] `apps/ontology/adapter/outbound/scraper/kobis_scraper.py` (`KobisScraper`,
      site_id="kobis", "daily"/"daily:YYYYMMDD" 규약, dedup=movieCd:targetDt)
- [x] 테스트: `test_kobis_scraper.py` (5개 통과 — 매핑, dedup, 키 누락 에러, KST 자정
      경계 2건)
- [x] `KeywordSourcePort` (`app/ports/output/keyword_source_port.py`)
- [x] `KobisBoxofficeTitleSource` (`adapter/outbound/scraper/kobis_boxoffice_title_source.py`,
      kobis_client 재사용, top10 제목 반환, 정규화 안 함)
- [x] `KEYWORD_SOURCE_REGISTRY` (`adapter/outbound/scraper/keyword_source_registry.py`,
      SITE_REGISTRY와 동일한 비순환 등록 패턴)

## 남은 작업 (Track A)

- [x] KobisBoxofficeTitleSource 테스트(`test_kobis_boxoffice_title_source.py`, 1개 통과)
- [x] `tmdb` 어댑터 완료 (`adapter/outbound/scraper/tmdb_scraper.py`, `test_tmdb_scraper.py`
      3개 통과 — 매핑, infobox key 체계, 키 누락 에러)
- [x] `CrawlPolicy.keyword_source` 필드 추가 완료
- [x] `CrawlScheduleInteractor._resolve_keywords()` 병합 로직 구현 완료(정적+동적 merge,
      dedup, max_dynamic_keywords 상한, resolve() 실패 시 정적만으로 계속) — 신규
      테스트 3개(병합+dedup, 상한, resolve 실패 복원력) 포함 전부 통과
  - `run_once()`는 그대로 둠(keyword_source 없이 명시적 keywords만) — 관리자 화면
    1회성이라 맞다고 확정함
- [x] `YamlCrawlPolicyAdapter`가 `keyword_source` 필드 파싱하도록 확장 완료
- [x] 스크래퍼 탭 custom URL 출력 경로를 `datasets/`에서
      `apps/ontology/resources/crawled/custom_{도메인}_{날짜}.jsonl`로 변경
      (`harvester_provider.custom_url_scrape_out_path`) — 코드 완료, **도커 재빌드는
      아직 안 함**
- [x] `crawl_config.yaml`에 kobis(daily) 정책 + google_news/kowiki dynamic
      (`keyword_source: kobis_boxoffice_titles`) 항목 추가 완료
- [x] `registry.py`에 kobis/tmdb 등록 완료
- [x] `harvester_provider.py`: `build_crawl_schedule_use_case`에 keyword source 빌더
      주입 완료 (`build_keyword_source()`)
- [x] `harvester_router.py`: `MissingApiKeyError` → `HTTPException(503, ...)` 캐치 완료
      (scrape/crawl 둘 다)
- [x] API 키는 `.env.example`에 이미 있던 `TMDB_API_KEY`/`KOFIC_API_KEY`를 그대로
      재사용(신규 키 안 만듦 — mova의 kofic_adapter.py와 이름 통일)
- [x] Track A 전체 ruff/mypy --strict/pytest 재확인 완료 (46/46 통과, touched 파일
      mypy 클린), DIP grep 클린, `sites` 커맨드에 kobis/tmdb 노출 확인 완료

## 완료 (Track B — mova ingest-harvest)

- [x] `apps/mova/adapter/outbound/harvest/harvest_jsonl_reader.py` — json.loads만 사용,
      ontology 모듈 import 없음(grep+테스트 확인), `HarvestRow`(app/dtos)로 파싱
- [x] source별 content 매핑 함수 — kowiki(content+sections 결합), google_news(content
      그대로), kobis(content+metrics를 한국어 문장으로), tmdb(content+infobox)
      (`harvest_ingest_interactor.py`의 `_map_content()`)
- [x] ingest interactor — 각 row → `HubKnowledgeUpsertCommand(source, source_ref=url,
      title, content)` → 기존 `HubRagUseCase.ingest_movie()` 재사용
- [x] `movies_pg_repository.find_by_title()`로 매칭 시도(정확 일치), matched/unmatched
      카운트 리포트 (`HarvestIngestResultDto`)
- [x] `scripts/mova_ingest_harvest.py` 진입점 — export_chat_training_dataset.py와
      동일한 DI 패턴
- [x] 테스트 9개(reader 3개 + interactor 6개) 전부 통과, ruff/mypy --strict 클린,
      harvester 모듈 import 없음 grep+테스트 확인
- [x] **수동 통합 검증(도커 재빌드 후)**: 실제 scrape/crawl-batch로 JSONL 만든 뒤
      ingest-harvest 실행 → hub_knowledge에 실제로 들어갔는지 확인 (2026-07-20, kobis
      10건/tmdb 4건 적재 확인)
- **알아둘 점**: `search_movies()`가 `source="mova_movie"`로 고정 필터링돼 있어서
  harvest 데이터는 지금 mova 채팅 검색에 안 걸림(의도된 범위 제한 — 위 "현재 상태"
  섹션 참고)

## 참고 — 이번 세션에서 이미 완료된 이전 작업 (harvester 1차, 커밋 완료·main 반영됨)

harvester CLI(scrape/crawl-batch), google_news/kowiki 어댑터, 어드민 화면(크롤러/
스크래퍼 탭, 사이트 선택 + URL 직접 입력 + 자연어 명령), robots.txt 체크, Gemini
기반 임의 URL 추출 — 전부 완료·커밋(`7850b60`, `9e4c805` 등)·`main` 브랜치에도 병합
푸시됨. kinolights는 robots.txt 전체 차단으로 제외.

