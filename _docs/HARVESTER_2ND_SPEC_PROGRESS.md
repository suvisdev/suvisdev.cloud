# harvester 2차 스펙(TMDB/KOBIS + 동적 키워드) + mova ingest-harvest 진행 상황

컨텍스트가 끊길 경우를 대비한 재개용 메모. 최신 진행 상황은 이 파일 상단을 갱신한다.

## 지금 당장 재개할 지점 (사용자가 "멈추고 커밋해줘"라고 해서 여기서 중단함)

Task #32(harvester_provider 배선) 진행 중이었고, 방금 한 작업:
- `registry.py`에 kobis/tmdb 등록 완료 (SITE_REGISTRY[KobisScraper.site_id]=... 등)
- import 확인하다가 로컬 검증용 파이썬(시스템 python3, venv 아님)에 `feedparser`가
  없어서 에러 났음 — **코드 버그 아님**, 테스트용 venv
  (`/tmp/claude-1000/.../scratchpad/testvenv`)에는 이미 설치돼 있었음. 재개 시
  `$VENV/bin/python`으로 다시 확인할 것, 시스템 `python3`로 확인하지 말 것.

다음 할 일 순서 (Task #32 나머지):
1. `harvester_provider.py`의 `build_crawl_schedule_use_case()`에 `build_keyword_source`
   콜러블 주입 — `KEYWORD_SOURCE_REGISTRY`에서 source_id로 찾아 fetcher/rate_limiter
   조립해서 `KobisBoxofficeTitleSource` 생성하는 함수를 만들어 넘겨야 함
   (`build_site_scraper`와 비슷한 패턴, 다만 KeywordSourcePort는 visited_store가 없음)
2. `harvester_router.py`에서 `MissingApiKeyError` → `HTTPException(503, detail=str(e))`
   캐치 추가 (scrape/crawl 두 엔드포인트 다)
3. `.env.example`에 `TMDB_API_KEY=`, `KOBIS_API_KEY=` 키 이름만 추가
4. Track A 전체 재검증: `$VENV/bin/python -m pytest apps/ontology/test/ --ignore=.../yolo_test.py -q`,
   ruff, mypy --strict, `sites` 커맨드에 kobis/tmdb 노출 확인, DIP grep
5. Task #32 완료 후 Task #33~36 (Track B, mova ingest-harvest) — 이 파일 하단
   "남은 작업 (Track B)" 섹션 그대로 유효, 아직 착수 전
6. 도커 재빌드 아직 안 함 — Track A 전체(kobis/tmdb 포함) + 아까 요청받은
   `custom_url_scrape_out_path` 변경사항까지 한 번에 재빌드해서 검증할 것

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
      dedup, max_dynamic_keywords 상한, resolve() 실패 시 정적만으로 계속) — 기존
      3개 테스트 재통과 확인함. **동적 키워드 merge 자체의 신규 테스트 3개(병합+dedup,
      상한, resolve 실패 복원력)는 아직 작성 중 — 다음 재개 지점**
  - `run_once()`는 그대로 둠(keyword_source 없이 명시적 keywords만) — 관리자 화면
    1회성이라 맞다고 확정함
- [ ] `YamlCrawlPolicyAdapter`가 `keyword_source` 필드 파싱하도록 확장 (아직)
- [x] **[추가 요청, 완료]** 스크래퍼 탭 custom URL 출력 경로를 `datasets/`에서
      `apps/ontology/resources/crawled/custom_{도메인}_{날짜}.jsonl`로 변경
      (`harvester_provider.custom_url_scrape_out_path`) — 사용자가 namu.wiki 테스트
      중 위치 헷갈려서 요청함. 크롤러 탭의 `custom_{날짜}.jsonl`과 파일명 겹치지 않음.
      **아직 도커 재빌드 안 함 — Track A-6 재빌드 때 같이 반영 예정**
- [ ] `crawl_config.yaml`에 kobis(daily) 정책 + google_news/kowiki dynamic
      (`keyword_source: kobis_boxoffice_titles`) 항목 추가 (스펙 §6.4 예시 참고,
      `targets:`/`options:` 대신 기존 policies 스키마 유지 — 1차 때와 동일한 이유)
  - `max_dynamic_keywords`는 YAML `options:`로 안 빼고 `build_crawl_schedule_use_case`
    파이썬 기본값(20)으로 유지 예정(1차 때의 diff 최소화 원칙과 동일)
- [ ] `registry.py`에 kobis/tmdb 등록 (import + `SITE_REGISTRY[...]=...` 패턴)
- [ ] `harvester_provider.py`: `build_crawl_schedule_use_case`에 keyword source 빌더
      주입 로직 추가
- [ ] `harvester_router.py`: `MissingApiKeyError` → `HTTPException(503, ...)` 캐치 추가
- [ ] `.env.example`에 `TMDB_API_KEY=`, `KOBIS_API_KEY=` 키 이름만 추가(값 없이)
- [ ] Track A 전체 ruff/mypy --strict/pytest 재확인, DIP grep(Service/Domain에
      httpx/redis 등 import 없는지), `sites` 커맨드에 kobis/tmdb 노출 확인

## 남은 작업 (Track B — mova ingest-harvest, 아직 착수 전)

- [ ] `mova/adapter/outbound/harvest/harvest_jsonl_reader.py` — json.loads만 사용,
      ontology 모듈 import 금지, mova 자체 dataclass(예: `HarvestRow`)로 파싱
- [ ] source별 content 매핑 함수 — kowiki(content+sections 결합), google_news(content
      그대로, 이미 title+summary 결합돼있음), kobis(content+metrics를 한국어 문장으로),
      tmdb(content+infobox), 그 외 fallback(content 그대로)
- [ ] ingest interactor — 각 row → `HubKnowledgeUpsertCommand(source, source_ref=url,
      title, content)` → 기존 `HubRagInteractor.ingest_movie()` 재사용(임베딩+upsert
      전부 재사용, 새 DB/임베딩 코드 없음)
- [ ] `movies_pg_repository.find_by_title()`로 매칭 시도(정확 일치), matched/unmatched
      카운트 리포트
- [ ] `scripts/mova_ingest_harvest.py` 진입점 — `get_mova_session_factory()` 세션으로
      `HubKnowledgeRepository`+`OllamaEmbeddingAdapter` 구성(export_chat_training_dataset.py
      패턴 그대로)
- [ ] 테스트: source 4종 매핑 fixture, upsert dedup(같은 url 2번 → 1건), matched/unmatched
      리포트, **`mova/adapter/outbound/harvest/`에 harvester 모듈 import 없는지 grep 확인**
- [ ] ruff/mypy --strict
- [ ] 수동 통합 검증: 실제 scrape/crawl-batch로 JSONL 만든 뒤 ingest-harvest 실행 →
      hub_knowledge에 실제로 들어갔는지 확인 (mova 채팅 RAG 검색으로 간접 확인 가능)

## 참고 — 이번 세션에서 이미 완료된 이전 작업 (harvester 1차, 커밋 완료·main 반영됨)

harvester CLI(scrape/crawl-batch), google_news/kowiki 어댑터, 어드민 화면(크롤러/
스크래퍼 탭, 사이트 선택 + URL 직접 입력 + 자연어 명령), robots.txt 체크, Gemini
기반 임의 URL 추출 — 전부 완료·커밋(`7850b60`, `9e4c805` 등)·`main` 브랜치에도 병합
푸시됨. kinolights는 robots.txt 전체 차단으로 제외.

