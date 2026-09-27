---
paths:
  - "suvisdev/apps/mova/**/market_chat*.py"
  - "suvisdev/apps/mova/**/market_conversations*.py"
  - "suvisdev/apps/mova/adapter/outbound/llm/**"
  - "suvisdev/apps/mova/domain/value_objects/mood_expansion.py"
  - "suvisdev/apps/mova/domain/value_objects/franchise_expansion.py"
  - "suvis/components/mova/mova-ai-chat-bar.tsx"
  - "suvis/components/mova/mova-landing-chat-bar.tsx"
  - "suvis/lib/mova-chat-suggestions.ts"
  - "suvis/app/api/mova/chat/**"
---

## mova 채팅 규칙 (백엔드 파이프라인 + 프론트 UX)

`/mova/chat` 추천 채팅에 누적된 결정·불변식의 SSOT. **mova 채팅에만 적용한다**
— 다른 앱에 채팅이 생겨도 이 문서를 준용하지 않는다(앱별로 새로 정한다).
전부 실측·실사고 기반이며, 각 항목의 날짜는 `_docs/WORK_LOG_MOVA.md`의 상세
기록을 가리킨다.

### 1. 파이프라인 순서 (바꾸지 말 것)

```text
인텐트 분류(classifier) → general/crud면 Mycroft 직행(RAG·추천 안 탐)
  → 의도 추출(extract_intent, 히스토리 병합)
  → RAG 시맨틱 검색(hub_rag, k=8) + 태그 실매칭 합집합(RAG 우선, 캡 16)
  → RAG 실패·0건이면 tag catalog 폴백(mood 확장 포함)
  → dedup(스레드 내 기추천 제거) → LLM 추천 생성(카탈로그 한정)
  → 취향 벡터 재정렬 → chat+picks 저장 → 2차 dedup → 응답
```

핵심 파일: `market_chat_interactor.py`(오케스트레이션) ·
`intent_extraction.py`(결정론 의도 추출) · `chat_prompt.py`(프롬프트) ·
`market_chat_pg_repository.py`(태그 폴백·인기작 폴백).

### 2. 후보 생성 불변식

- **LLM은 카탈로그의 movie_id 중에서만 고른다.** 후보가 0이면 빈 목록 대신
  인기작 폴백을 준다 — 빈 후보를 주면 LLM이 movie_id를 지어내고 enrich에서
  전부 드롭돼 "reply는 자신 있는데 카드 0개"가 된다(2026-08-06 재현).
- **RAG(임베딩)가 죽어도 채팅은 계속 동작한다.** Gemini/Ollama 임베딩 장애·쿼터
  429 시 tag catalog 폴백으로 넘어간다. 폴백 제거 금지.
- **연도 하드 필터가 있으면 RAG 히트를 movies.release_year로 재검증한다**
  (2026-09-03, "클래식 명작 처음 보는 사람용" trace=f4552cee — year_max=1999
  요청에 시맨틱 tail의 2003·2007년작이 유입돼 '식객' 무관 픽): hub에는 연도
  메타데이터가 없으므로 `filter_movie_ids_by_year`로 위반 히트를 제거한다.
  release_year=0(미상)도 조건이 있으면 탈락. 연도 조건이 없는 질의는 이
  경로를 타지 않는다(재검증 호출 0). 이 재검증 제거 금지.
- **RAG 히트가 있어도 태그 실매칭은 합집합으로 합류한다**(2026-09-02, 09-01
  "좀비 영화" recs=0 실측 갭 수정): 원시 키워드(mood 확장 없이)로 태그 검색을
  함께 돌려 `popular_fallback`이 아닌 실매칭만 합류한다(dedup, 캡 16).
  **순서는 태그 실매칭 우선(상한 10) + 시맨틱 보충** — 결정론 신호가 시맨틱
  저유사 히트보다 정확하고, 2.4B LoRA가 목록 앞쪽에 끌려 RAG-우선 순서에선
  좀비 태그 후보를 두고 무관 시맨틱을 픽하는 것을 프로덕션 실측(2026-09-02).
  순수 mood 질의는 태그 실매칭이 없어 자연히 RAG 단독이 유지된다 — 합집합
  경로에 mood 확장을 넣으면 mood 질의가 장르 인기작으로 희석되니 넣지 말 것.
  합집합을 없애면 무관 시맨틱 히트가 태그 검색을 가리는 갭이 재발한다.
  **예외(2026-09-02, "최신영화 알려줘")**: 연도·국가 하드 필터가 있으면
  `popular_fallback`도 합류시킨다 — hub에 연도 메타데이터가 없어 시맨틱
  히트는 하드 필터를 못 지키는데("최신"→"작년에 봤던 새" 매칭 실사고),
  popular_fallback은 그 조건을 SQL로 만족한 인기작이다. mood 질의는 하드
  필터가 없어 이 예외의 영향을 받지 않는다.
- **의도 추출은 현재 턴만 결정론으로 처리한다**(2026-09-11 확정): 08-19 멀티턴
  오염 수정 2건(f59f1d4·5c9c24c)이 이전 턴 유입을 막으려고 Gemini 추출 산출물을
  전부 결정론 결과로 덮었고, 결과가 안 쓰이는 Gemini 호출(질의당 0.9~5s+쿼터)은
  09-11 제거됐다. 멀티턴 맥락은 interactor의 past_intents 프롬프트 주입이 담당
  — 히스토리를 다시 의도 추출에 흘리면 08-19 "주제 전환 시 이전 장르 잔존"
  사고가 재발한다. Gemini 배우 보강(구 QUALITY_PHASE1 §9)을 재도입하려면 현재
  턴만 Gemini에 주고 must.actors만 병합하는 별도 설계로 할 것.
- **시대 어휘는 연도 조건으로 해석한다**(2026-08-28 실사고): "클래식·고전·옛날"은
  명시 연대·연도가 없을 때 `year_max=1999`로 근사한다(`_guess_year_range`).
  "90년대 클래식"처럼 명시 연대가 있으면 그쪽이 우선. 연도 조건은 SQL 하드
  필터가 없는 RAG 경로를 위해 프롬프트 의도 섹션에도 `연도=` 로 표기한다.
- **콜드스타트 인기작 폴백은 최근 15년 우선 + 평점순**(2026-08-25) — 조건 없는
  질의에 5070년대 작품이 뜨는 것 방지. 연도 하드 필터가 잡히면 이 정렬은
  자연히 무력화된다. 정렬을 없애지도, 연도 필터를 무시하지도 말 것.
  (둘 중 하나만 살아 있으면 "클래식 요청에 최신작만" 사고가 재발한다.)
- **mood 자연어는 장르 태그로 확장**(`mood_expansion`, 2026-08-13), **프랜차이즈
  언급은 대표작 제목 매칭**(`franchise_expansion`, 2026-08-25)으로 폴백 경로가
  이해한다. 새 어휘는 이 두 value object에만 추가한다.
- **다중 태그 질의는 교집합 우선 + 합집합 보충**(2026-09-02): "SF 드라마"처럼
  태그에 실매칭된 키워드가 2개 이상이면 전부 가진 영화를 먼저 조회해 앞에
  두고, 남는 자리만 기존 합집합으로 채운다(`search_tag_catalog`). 합집합
  단독으로 평점순 limit을 자르면 교집합 영화가 통째로 밀린다. 매칭 0건
  키워드("영화" 등 비태그 어휘)는 교집합 판정에서 제외 — 순수 AND로 바꾸면
  mood 동의어 확장(OR가 정답)이 깨지니 보충 경로를 없애지 말 것.
  배우+태그 교집합(`actor+keyword`) 경로는 별개로 기존 동작 유지.

### 3. 중복·재추천 방지 (2단)

- 스레드에서 이미 소개한 슬러그는 후보에서 제거한다. dedup으로 후보가 다
  빠지면 조건 유지한 채 풀만 16→48로 넓혀 한 번 재검색한다(2026-08-26).
- LLM 응답 뒤 최종 반환 직전에 한 번 더 거른다(2차 안전망) — 후보 필터가
  뚫려도 같은 영화가 다시 나가지 않게.

### 4. 응답 문구 규칙

- **reply와 카드 수는 어긋나면 안 된다.** 추천 0건이면 reply도 0건임을 정직하게
  안내한다("추천해 드릴게요" + 카드 0개 금지).
- **0건 안내는 문구를 다양화한다**(random.choice 변형 풀) — 고정 문구는 재시도마다
  같은 답이 반복돼 "봇 반복" 불만을 유발했다(2026-08-13 실측).
- **폴백 추천은 확신 문구로 포장하지 않는다**(2026-08-28 결정): 태그 매칭 실패로
  인기작 폴백(`popular_fallback`)에서 나온 카드에 "엄선했습니다" 같은 문구 금지 —
  "조건에 딱 맞는 게 없어 인기작에서 골랐어요" 톤으로 낮춘다.
  (프롬프트 구현은 백로그 — 신규 문구·프롬프트 작성 시 이 규칙을 따를 것.)

### 5. 실행·보안 규칙

- **CPU-bound(Kiwi 형태소 등)는 `async def` 금지** — 호출 측 `asyncio.to_thread`
  위임(루트 suvisdev/CLAUDE.md §E.4).
- `self._repo`와 `self._preferences`는 **같은 DB 세션을 공유**한다 —
  `asyncio.gather`로 동시에 돌리면 SQLAlchemy가 "concurrent operations"로 막는다.
  사용자 컨텍스트 조회는 순차 함수로 묶어서 gather에 넣는다.
- `/mova/chat`은 `optional_user` — 비로그인 허용하되 **Bearer가 왔는데 무효면
  401 명시**(조용히 익명 처리 금지).
- 대화 스레드 소유권 검증은 **LLM 호출 전에** 한다(쿼터 소모 전 raise).
- 대화 저장(threads)·picks 저장·취향 재정렬은 로그인 유저 한정, 포트 미주입이어도
  채팅 자체는 동작해야 한다(optional 주입 유지).
- 취향 벡터 재정렬 후 **카드 순서와 picks 저장 순서를 일치**시킨다(2026-08-18).

### 6. 프론트 UX (suvis)

| 규칙 | 구현 |
|------|------|
| 대화 영속성 | `sessionStorage` 키 `mova-ai-chat-history-v2`(실측 2026-08-28), 탭·세션 단위 |
| 복원 시 자동 전송 | 히스토리에 user 메시지 있으면 `?q=` 자동 전송 생략(`autoSentRef`) |
| Enter 전송 | `Shift+Enter` 줄바꿈, IME 조합 중(`isComposing`) 전송 안 함 |
| 전송 실패 | 사용자 메시지 롤백 + 입력값 복원 + `error` 배너 |
| 로딩 중 | 전송·힌트 버튼 비활성 |
| 추천 칩 | 풀 18개(`SUGGESTION_POOL`), 날짜+FNV-1a 해시로 일일 3개 로테이션 |
| 칩 표시 조건 | `messages`에 user 메시지가 없을 때만 렌더(대화 시작 후 숨김) |
| 요청 형식 | `{message, history(최대 10턴), model, user_id?}` — 프록시 `suvis/app/api/mova/chat` |
| 카드 렌더 | `recommendations` 최대 3편, `refined_query`는 말풍선 하단 intentLabel |

문구 추가·수정은 `SUGGESTION_POOL` 배열만 편집한다. 칩 문구를 바꾸면
백엔드 폴백 어휘(§2의 mood/시대 어휘)가 그 문구를 이해하는지 같이 확인한다
— "클래식 명작 처음 보는 사람용" 칩이 어느 어휘에도 안 걸려 인기작 폴백으로
빠진 것이 2026-08-28 실사고다.

### 7. 검증

```bash
cd suvisdev && python -m pytest apps/mova/tests -m "not gpu and not ollama" -q
# 라이브 진단: EC2 backend 로그에서 trace 라인 확인
#   [ChatInteractor] destination= / fallback search_tag_catalog 사용
#   [HubRagInteractor] embed 실패(쿼터 429면 RAG 생략됨) / vector_search hits=
```

### 8. 응답 3트랙 (2026-08-28 결정 5건 반영 — Phase 1 구현 완료)

**mova는 "영화를 추천하고, 평가하고, 예매까지 돕는" 프로젝트로 재정의됐다**
(2026-08-28). 현행 "모든 영화 질의 → 추천 카드 3장" 단일 트랙을 인텐트별
3트랙으로 확장한다. 상세 설계·Phase·결정 기록은
`suvisdev/apps/mova/_docs/MOVA_CHAT_INTENT_REDESIGN.md`가 SSOT다.
채팅 응답 로직을 새로 만지는 세션은 다음 방향과 충돌하지 않게 작업할 것:

- **트랙 3종**: `recommend`(기존, 무변경) · `evaluate`("호프 어때?" → 자체
  리뷰+TMDB 리뷰 API 집계 기반 객관 평가) · `booking`("호프 예매하고 싶어"
  → 상영 중 판정+지역명 기반 근처 영화관+예매 경로 안내).
- **분류는 1차 분류기 확장으로 한다**(2단 분류안 폐기, 사용자 결정) — Hub
  `IntentClassifierPort` destination을 5종(recommend/evaluate/booking/
  general/crud)으로 확장. 소비자가 mova뿐임을 실측 확인했고, 확장 시
  ontology `semantic_router_interactor.py` 분기를 반드시 함께 갱신한다.
- **외부 리뷰는 TMDB 공식 API만** — 왓챠피디아 등 크롤링 금지(약관 명시
  금지·DB권 판례 리스크로 제외 확정). booking 시간표(Phase 2)는 진행하되
  체인 약관 실확인·단건 조회·딥링크 폴백 선행 조건을 지킬 것.
- **chat_trend는 조건부 반영** — 단순 평가/예매 질의는 미집계, 사용자의
  긍정 평가 반응 또는 예매 의지가 확인될 때만 반영. picks는 recommend
  트랙만.
- **카드 3장 고정을 가정한 코드를 새로 쓰지 않는다** — 응답은
  `response_type`(recommendation | evaluation | booking) 분기이며,
  evaluate/booking은 카드 1장+전용 payload다(스키마
  `MovaChatEvaluationSchema`·`MovaChatBookingSchema`).
- **booking 지역 이어받기는 결정론 마커**(`REGION_ASK_MARKER` + 『제목』)로
  동작한다 — "강남" 단독 발화는 분류기가 오분류하기 쉬워 분류기를 거치지
  않는다. 되묻기 문구를 바꿀 때 마커·『』 포맷을 깨뜨리지 말 것.
- **지역-선행 발화는 직전 턴 영화를 이어받는다**(2026-09-11 실사용 — 옵세션
  평가 직후 "군자쪽에 예매할 시간"이 지명 퍼지 매칭돼 군체/구원자/감자로
  되묻던 오류): title resolver가 실패했고 지명 신호(`_extract_region_signal`,
  쪽/역/근처/주변/인근 접미)가 있으면 직전 assistant 응답에서
  `find_movie_titled_in_text` 역조회로 영화를 복원해 곧장 지역 검색으로
  간다. 맥락 영화도 없으면 지명을 퍼지 후보로 되묻지 않고 제목을 묻는다.
  지명 접미에 동·구 단독을 추가하지 말 것(제목 오탐), 신호 판정은 resolver
  실패 후에만(명시 제목이 항상 우선).
- **제목 없는 탐색형 예매 질의는 상영작 목록으로 답한다**(2026-09-02 실사용
  수정): "지금 예매할 수 있는 영화 뭐 있어" 류는 `_DISCOVERY_PATTERN`이
  title resolver보다 **먼저** 갈라 주간 박스오피스 목록(출처 명시)으로
  응답한다 — 일반어("영화")가 제목 퍼지 매칭돼 무관 후보로 "어떤 작품을
  예매하시려나요?" 되묻던 오류의 수정. 패턴 제거·title 해석 선행 금지.
- **예매 어휘 없는 booking 분류는 recommend로 교정한다**(2026-09-02 실사고,
  "최신영화 알려줘"): 분류기(`qwen_intent_classifier`)가 booking을 반환해도
  질문에 `_BOOKING_VOCAB`(예매·예약·티켓·표 끊·상영·극장·영화관·보러·
  시간표·어디서)이 하나도 없으면 결정론 가드가 recommend로 되돌린다 —
  '요즘 상영작 알려줘' 프롬프트 예시와 표면이 비슷한 소개 요청이 booking으로
  새어 제목 퍼지 매칭(간신/변신/실)으로 되묻던 사고. 가드 제거 금지, 어휘를
  좁힐 때는 기존 booking 예시들이 전부 걸리는지 확인할 것.
- **예매·시간표 어휘가 있으면 분류기와 무관하게 booking으로 간다**(2026-09-27
  실사고, "인턴 영화 시간표 보여줘"가 general로 새어 Gemini가 '롯데시네마 군자점
  14:10·17:30'을 지어냄): interactor의 `_is_booking_lexicon`(시간표·상영 시간/회차·
  예매·예약·상영관·영화관/극장+어디/찾/근처 …, '추천' 포함 발화 제외)이 분류기
  **앞**에서 booking으로 보낸다. booking은 모르는 시간표를 체인 검색 링크로
  위임하므로 안전하다. 위 09-02 가드(booking→recommend 교정)와 짝이다 —
  둘 다 `_BOOKING_VOCAB`류 어휘 기준이니 한쪽을 좁히면 다른 쪽도 확인할 것.
- **general 트랙은 실시간 사실을 지어내지 않되, 예매 도우미로 넘긴다**(같은 사고 +
  사용자 지적): 시스템 프롬프트에 시간표·회차·지점·예매 가능 여부는 "이 대화에서
  조회하지 못하니 추측·지어내기 금지, 대신 '작품명 + 예매/시간표'로 말하면 근처
  영화관(카카오 지도)과 롯데시네마 시간표를 찾아준다"고 안내하도록 했다
  (`_GENERAL_CHAT_SYSTEM_PROMPT`). "모른다"로만 끝내면 실제로 있는 극장·시간표
  데이터를 없는 척하는 것이다. 이 문장을 빼지 말 것.
- **booking 어휘는 넓게**: 영화관·극장·지점·체인·체인명·"어디서 봐/볼"·"몇 시"까지
  포함한다(추천 발화만 제외). 좁히면 데이터가 있는 질문이 잡담으로 새어 "모른다"가 된다.
- **제목 후보에서 1자 어간·1자 엔티티는 버린다**(같은 사고의 세 번째 원인):
  조사 분리가 "파과"의 '과'를 조사로 보고 '파'를 만들어 부분일치로 스파이더맨·
  임파서블을 되물었다. `_title_terms`는 문장 앞 1~2어절(원형)을 후보로 넣고,
  길이 2 미만 어간·엔티티는 검색에 쓰지 않는다. 2자 제목(파과·인턴)은 그대로 산다.
- **최신 어휘도 연도 조건으로 해석한다**(2026-09-02, 클래식→year_max의 대칭):
  최신·신작 → `year_min=올해-1`, 최근 → `year_min=올해-5`
  (`_guess_year_range`). 명시 연대·연도가 있으면 그쪽이 우선.
- **정직성 규칙이 전 트랙에 적용된다** — 리뷰 표본 부족 명시(evaluate),
  "박스오피스 기준 근사"·시간표 출처 명시(booking). 모르는 것을 아는 척하는
  문구 금지.
