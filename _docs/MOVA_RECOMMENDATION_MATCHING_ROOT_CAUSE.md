# mova 추천 오귀속 근본 원인 조사

`_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`에서 발견된 두 버그("동명이인
오귀속 — 괴물→The Thing", "제목 포맷 취약성 — 빽 투 더 퓨쳐")가 같은 결함인지
특정하고 근본 해결안을 비교한다. **코드 변경 없음 — 조사만.**

---

## 1. 매칭 계층 코드 경로

```
GeminiRecommendationAdapter.generate_recommendation()   (gemini_recommendation_adapter.py:33-61)
  → gemini_reply(prompt, model)                          # Gemini 원문 텍스트
  → ChatReplyService.parse_gemini_reply(raw)              # JSON 파싱, title/hook만 추출 — DB 조회 없음
  → ChatReplyService.enrich_from_db(recs)                 # ★ movie_id를 여기서 확정
```

**`enrich_from_db()`(`chat_reply.py:93-171`)의 매칭 체인**(106~111행):
```python
canonical = resolve_canonical_slug(rec.id, title=rec.title)
movie = (
    await repo.get_by_slug(canonical)      # 1단계: 수동 큐레이션 맵(12개 고정 항목)
    or await repo.get_by_slug(rec.id)      # 2단계: slugify_movie(title) 결과로 재조회
    or await repo.find_by_title(rec.title) # 3단계: title 완전일치, LIMIT 1, ORDER BY 없음
)
```
- 1단계 `resolve_canonical_slug`(`studio_movies_vo.py:25-35`): `TITLE_TO_CANONICAL_SLUG` 12개
  고정 항목("기생충"→"parasite" 등)에 없으면 그대로 통과 — 대부분의 제목은 이 단계에서 그냥 미스.
- 2단계 `get_by_slug(rec.id)`: `rec.id = slugify_movie(title)`(Gemini가 준 title 그대로 슬러그화,
  공백→하이픈, 특수문자 제거). DB에 저장된 실제 slug는 `tmdb-{tmdb_id}` 형식이라 **이 경로는
  구조적으로 항상 미스**(TMDB 수입 영화 기준) — 사실상 죽은 경로.
- 3단계 `find_by_title(title)`(`movies_pg_repository.py:76-83`): `SELECT ... WHERE title = :title
  LIMIT 1` — **완전 문자열 일치, 정규화 없음, ORDER BY 없음**. 실질적으로 거의 모든 grounding이
  이 3단계에서 일어난다.
- **`enrich_from_db()` 전체에 로깅이 0건**(저장 실패 시 `logger.debug` 1곳뿐) — 어느 단계에서
  매칭됐는지 로그로는 알 수 없다. 슬러그 생성 규칙을 정적으로 추적해 2단계가 죽은 경로임을
  코드 분석만으로 확정했다(§2 참고).

---

## 2. "괴물" 케이스 재현

**DB 조회**(`movies WHERE title ILIKE '%괴물%'`): **1건만 존재** — `id=426`,
`slug=tmdb-1091`, `title=괴물`, `release_year=1982`.

TMDB에 `tmdb_id=1091`을 직접 조회하면 원제 `The Thing`, 1982년, 존 카펜터
감독 — **송강호와 무관한 영화**다. 봉준호 감독의 `괴물`(2006, 송강호 주연)은
DB에 아예 없다(TMDB popular 50페이지 수집 범위 밖으로 추정).

**당초 가설(동명이인 2건 중 tiebreaker 없이 아무거나 고름)은 기각** — DB에
"괴물"이라는 제목이 **딱 하나뿐**이라 애초에 고를 대상이 여럿이지도 않았다.
진짜 메커니즘은 더 단순하고 더 심각하다: **`find_by_title()`은 문자열이
일치하기만 하면 그 영화가 원래 요청 맥락(배우="송강호")과 실제로 관련
있는지 전혀 검증하지 않는다.** Gemini의 JSON 응답(`picks[].title`,
`picks[].hook`)엔애초에 배우 이름이 안 들어있어서(§1 참고), `enrich_from_db()`
입장에선 "제목이 괴물인 아무 영화나" 매칭될 뿐 그게 송강호 영화인지 검증할
수단 자체가 없다.

**재현**: `curl -X POST /mova/chat -d '{"message":"송강호 출연 스릴러 영화"}'`을
다시 실행 → 동일하게 `id=426`(`The Thing`)이 픽에 포함됨(2/2 재현). 백엔드
로그(`trace=5e415c87`)로 확인: `destination=rag` → `HubRagInteractor embed 실패`
(Ollama 없음, 예상대로) → `fallback search_tag_catalog 사용`. **이 로그로는
어느 매칭 단계였는지 구분 안 됨**(§1의 관측성 부재 그대로) — 다만 위 슬러그
분석으로 3단계(`find_by_title`)임을 정적으로 확정할 수 있다.

---

## 3. "빽 투 더 퓨쳐" 케이스 재현

Phase 1에 저장된 원문 그대로(`chat_reply.py`가 `title`을 한자 제거 외엔
가공 안 하므로 이게 Gemini의 리터럴 출력):
- 4번 쿼리(코미디): `"title": "빽 투 더 퓨쳐"` → `movie_id=194` 매칭 성공
- 8번 쿼리(80년대 SF): `"title": "빽 투 더 퓨쳐 (1985)"` → `movie_id=null` 매칭 실패

**실패 이유 확정**: `find_by_title()`이 완전 일치(`title = :title`)라
DB의 `"빽 투 더 퓨쳐"`와 Gemini가 준 `"빽 투 더 퓨쳐 (1985)"`는 문자열이
다르므로 미스. 2단계(slug)도 `slugify_movie("빽 투 더 퓨쳐 (1985)")`가
`"빽-투-더-퓨쳐-1985"`가 돼(괄호는 제거되지만 숫자는 남음) DB의
`"tmdb-194"`와 다르므로 역시 미스. **exact match / regex 여부를 묻는다면
정규식이 아니라 순수 `==` 비교이고, 연도 접미사·공백·문장부호에 대한
정규화 로직이 어디에도 없다.**

---

## 4. 두 버그는 같은 결함인가?

**예 — 정확히 같은 코드(`enrich_from_db()`의 3단계 매칭 체인), 다른 발현
형태.** 공통 원인은 "Gemini가 자유 텍스트로 뱉은 문자열을 사후에 DB
title/slug와 정확히 맞춰보려는 구조" 그 자체다:
- 문자열이 **정확히 일치**하지 않으면(포맷 차이) → 미스(null) — 8번 사례
- 문자열이 **우연히 정확히 일치**하지만 다른 영화면(동명이인) → 오귀속 —
  6번 사례, 검증 수단(장르/배우 대조) 없음

즉 "매칭이 너무 느슨해서(fuzzy) 잘못 걸리는" 게 아니라 반대로 **매칭이
너무 빡빡해서 정상 사례를 놓치는 것(false negative)과, 빡빡한 매칭이
우연히 성공했을 때 그 성공을 아무도 검증 안 하는 것(false positive
undetected)이 같은 코드에서 동시에 나오는** 구조적 결함이다.

---

## 5. 근본 해결 방향 비교

### (a) 매칭 계층 강화 — 정규화 + fuzzy + 컨텍스트 tiebreaker
- **구현**: `find_by_title()`에 정규화(공백·괄호·연도 접미사 제거, 예:
  `"빽 투 더 퓨쳐 (1985)"` → `"빽 투 더 퓨쳐"`) + ILIKE/trigram 유사도 +
  복수 매치 시 tiebreaker(장르 일치·release_year 근접·rating) 추가.
- **난이도**: 낮음~중간 — 순수 백엔드 함수 수정, 스키마 변경 없음.
- **재발 가능성**: 포맷 취약성(8번류)은 정규화로 대부분 해결. **동명이인
  오귀속(6번류)은 이 방향으로 근본 해결이 안 된다** — "괴물"이 하나뿐인
  DB에서조차 배우 검증 수단이 없었던 게 문제였는데, tiebreaker를 추가해도
  Gemini 응답에 배우/감독 정보가 없으면 무엇을 기준으로 tie를 깰지 근거가
  없다.
- **응답 품질**: 카탈로그 자체가 안 넓어지므로 순수 커버리지 부족
  (5·12·13번류)엔 영향 없음.

### (b) Grounded prompting — 후보 목록 제시 + id 응답 강제 (권장)
- **이미 절반은 존재한다**: `format_tag_catalog_section()`(`chat_prompt.py:82-92`)
  이 이미 DB 후보 목록(`MovaSearchItemSchema`, **`id` 필드 포함**)을 프롬프트에
  넣고 있다. 다만 (1) 지시가 "가능하면 여기서 고르세요"로 **약한 권고**일 뿐
  강제가 아니고, (2) 프롬프트엔 title만 노출하고 id는 안 보여주며, (3) Gemini
  응답 JSON 스키마(`{"picks":[{"title","hook"}]}`)도 id를 요구 안 해서, 결국
  `enrich_from_db()`가 또 title 문자열로 처음부터 다시 찾는다 — **애초에
  후보의 id를 이미 갖고 있었으면서 그 정보를 버리고 재매칭하는 구조.**
- **구현**: 프롬프트에 후보별 id 노출 + "반드시 이 목록의 id 중에서만
  골라라"로 지시 강화 + picks JSON에 `id` 필드 요구 + `enrich_from_db()`는
  title 재매칭 대신 응답받은 id로 `get_by_slug()`만 호출(검증 목적).
  Gemini function calling/response_schema를 쓰면 형식 자체를 API 레벨에서
  강제 가능(현재 미사용 — §0에서 이미 확인한 "런타임 강제 없음"과 같은 지점).
- **난이도**: 중간 — 새 인프라 불필요, 기존 tag_catalog 배관 재사용.
- **재발 가능성**: 후보 목록 안에서 고르게 하면 동명이인·포맷 문제가
  **원천 차단**된다(id로 응답받으므로 문자열 매칭 단계 자체가 없어짐).
  다만 후보 목록에 원하는 영화가 없으면(커버리지 부족) 여전히 놓친다 —
  이 경우 "카탈로그에 없으면 없다고 답하라"를 프롬프트에 명시하면 최소한
  환각성 이탈(카탈로그 밖 자유 추천)은 막을 수 있다.
- **주의**: `search_tag_catalog()`(`market_chat_pg_repository.py:26-55`)가
  `tags.label ILIKE`로만 검색하는데 `tags`엔 genre 태그만 있고 **cast 태그가
  전혀 없다**(Phase 1에서 이미 확인) — 배우 쿼리(5·6·7번)는 (b)를 도입해도
  후보 목록 자체가 안 채워져 효과가 제한적이다. (b)의 효과를 완전히
  끌어내려면 배우 검색 경로도 같이 보강해야 한다(예: `characters`/`actors`
  조인 검색 추가) — 이건 (b)의 하위 작업으로 별도 스코프.

### (c) hub_knowledge 벡터 검색 우선 경로 (Phase 2 이후)
- **배관은 이미 있다**: `ChatInteractor`(`market_chat_interactor.py:70,86-97`)가
  `hub_rag.search_movies()` 결과가 있으면 그걸 우선 쓰고, 없을 때만
  `search_tag_catalog`로 폴백하는 구조가 이미 구현돼 있다 — Phase 2에서
  hub_knowledge만 채우면 **코드 변경 없이 자동 활성화**된다.
- **난이도**: hub_knowledge 백필(별도 작업, Phase 1 문서 §4)만 하면 됨.
- **재발 가능성**: 의미 기반 검색이라 배우·무드까지 커버 가능해 **커버리지
  문제(5·12·13번류)는 크게 개선 기대**. 하지만 **(b) 없이는 오귀속·포맷
  문제가 그대로 남는다** — hub_rag 히트도 결국 title 매칭으로 이어지면
  같은 취약점을 물려받는다(현재 `hits`가 있을 때 `id=h.source_ref`를 바로
  쓰기는 하지만, Gemini가 그 candidate를 그대로 픽했는지 확인하는 절차가
  없는 건 (b)와 동일한 구조적 갭).
- **제약**: Ollama 임베딩(로컬 GPU 의존)이라 EC2 자체 검증 불가, Phase 2가
  집에서만 가능하다는 제약은 그대로.

### 권장 순서

**(b) 먼저, (c)는 Phase 2와 함께 병행.** (b)가 오늘 발견된 두 버그를 가장
직접적으로, 새 인프라 없이 근절한다. (c)는 (b)와 별개로 커버리지를 넓히는
효과가 있어 서로 배타적이지 않다 — 최종적으로는 (b)+(c) 조합이 이상적.
(a)의 정규화 일부(공백·괄호 트리밍 정도)는 저비용이라 (b) 도입 후에도
"카탈로그 밖 자유 응답"에 대한 최소 안전망으로 남겨둘 가치는 있다. **착수는
다음 세션** — 이번 조사에서는 코드 변경 안 함.

---

## 6. `RECOMMENDATION_BACKEND` EC2 미설정 경위

**정확한 경위**: `.env.example`에 이 변수가 추가된 건 커밋 `db6623b`
("feat(lora): 원격 GPU 서버 대응", 2026-08-03, PROGRESS.md 기록과 일치)다.
diff를 직접 확인한 결과 **주석 처리된 예시 줄**로 추가됐다:
```
# --- mova 추천 백엔드 스위치 ---
# lora: 자체 파인튜닝 모델(GPU 필요) / gemini: Google Gemini API(GPU 불필요
# — GPU 없는 EC2는 이 값이어야 함). 기본값: lora.
# RECOMMENDATION_BACKEND=lora
```
즉 **"EC2는 gemini여야 한다"는 사실 자체는 커밋 시점에 이미 주석으로
명시돼 있었다.** 하지만 `.env.example`은 템플릿일 뿐이고 실제 `.env`는
`.gitignore` 대상(비밀번호 보호 목적)이라 git 이력으로 언제 사라졌는지
추적이 안 된다(애초에 git 관리 밖) — **"있다가 사라진" 게 아니라 "템플릿에
새로 추가된 뒤 실제 `.env`엔 한 번도 반영된 적이 없었던" 것으로 결론.**
사람이 `.env.example`을 보고 실제 `.env`에 수동으로 옮겨 적어야 하는데
그 단계가 통째로 누락됐다 — 코드 버그가 아니라 배포 절차 누락.

**`.env` 로딩 메커니즘**(`docker-compose.yaml` 직접 확인): 두 경로가 있다.
1. `env_file: [./suvisdev/.env]` — `.env` 전체를 그대로 주입(범용 폴백).
2. 서비스별 `environment:` 블록 — 컨테이너 네트워킹 때문에 값이 달라져야
   하는 소수 변수(`DATABASE_URL`, `MOVA_DATABASE_URL`, `OLLAMA_BASE_URL`,
   `AWQ_SERVER_URL`, `LORA_SERVER_URL`, `REDIS_URL`)를 **compose 파일 안에
   하드코딩**해서 `.env` 내용과 무관하게 항상 올바른 값(예: `redis://redis
   :6379/0`, `localhost` 아님)을 강제한다. **`RECOMMENDATION_BACKEND`은
   호스트냐 컨테이너냐에 따라 값이 달라질 이유가 없는 순수 기능 플래그라
   (1)번 경로(`.env` 단독 의존)에 놓인 게 설계상 맞다** — 문제는 그 `.env`
   자체가 안 채워졌다는 것.

**다른 앱 감사 결과 — 대부분은 이 클래스의 위험에서 안전**: `os.getenv`
기본값 전수 조사(`REDIS_URL`, `OLLAMA_BASE_URL`, `AWQ_SERVER_URL`,
`LORA_SERVER_URL`, `FRONTEND_URL` 등) 결과, **네트워킹에 민감한 변수는
전부 위 (2)번 경로로 compose에 하드코딩돼 있어 `.env` 내용과 무관하게
안전**하다(`FRONTEND_URL`도 EC2 `.env`에 `https://suvisdev.cloud`로 정확히
설정돼 있음을 직접 확인). **`RECOMMENDATION_BACKEND`이 유독 취약했던 이유는
"컨테이너 네트워킹과 무관한 순수 기능 플래그라서 (2)번 안전망 대상이
아니었던" 것** — 즉 이번 사고는 특정 앱(auth/gildle/titanic)의 결함이
아니라 "새 순수-기능-플래그성 env var를 추가할 때 `.env.example` 갱신과
실제 `.env` 반영 사이에 아무 강제 장치가 없다"는 배포 프로세스의 일반적
공백이다. `apps/ontology/adapter/inbound/mcp/*`의 `INFERENCE_URL`·
`VISION_AGENT_MODEL` 등은 MCP 개발 도구 연동용이라 이번 프로덕션 요청
경로와 무관해 이번 감사에서 제외했다.

**권장(착수는 다음 세션)**: 코드 수정 없이도 즉시 적용 가능한 완화책 —
`market_chat_provider.py`의 `os.getenv("RECOMMENDATION_BACKEND", "lora")`
호출부에 `logger.warning`을 추가해 **기본값(lora)으로 폴백될 때마다 로그를
남기게** 하면, 다음에 같은 누락이 생겨도 조용히 실패하는 대신 로그로
바로 드러난다 — 이번 사고가 "로그도 없이 계속 실패만 하고 있었을 가능성"을
막는 가장 저비용 안전장치.
