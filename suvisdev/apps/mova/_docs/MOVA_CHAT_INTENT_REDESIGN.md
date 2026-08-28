# Mova 채팅 응답 알고리즘 재설계 — 인텐트별 응답 트랙

> **상태:** 설계 확정 전 초안(2026-08-28, 사용자 지시로 작성) — 구현 착수 전
> 미결 결정(§8)을 해소할 것.
> **상위:** `.claude/rules/mova-chat.md`(채팅 규칙 하네스 — 이 문서의 요약
> 규칙이 §8에 있다) · `CLAUDE.md`(같은 폴더, mova SSOT)

---

## 1. 문제 정의 (왜 다시 짜는가)

현행 채팅은 **추천 단일 트랙**이다. 영화 관련 질의는 전부
`rag` → 후보 검색 → LLM 추천 → **카드 최대 3장**으로 수렴한다.

| 사용자 질의 | 기대 응답 | 현행 응답 |
|-------------|----------|----------|
| "코미디 영화 추천해줘" | 추천 카드 | ✅ 추천 카드 3장 |
| "호프 어때??" | 그 작품의 리뷰·평가를 종합한 **객관적 평가** | ❌ 유사 영화 추천 카드 |
| "호프 예매하고 싶어" | 상영 여부·근처 영화관·예매 경로 안내 | ❌ 유사 영화 추천 카드 |

질의의 **의도가 3종류인데 응답 트랙이 1종류**인 것이 근본 문제다.
(2026-08-28 "클래식 명작" 오추천 수정과는 별개 축 — 그쪽은 추천 트랙 내부의
후보 품질 문제, 이쪽은 트랙 자체의 부재.)

## 2. 현행 구조 실측 (2026-08-28 기준)

```text
ChatInteractor.chat()
  ├─ classifier.classify() → destination ∈ {rag, general, crud}   (ontology Hub)
  ├─ general/crud → Mycroft(Gemini) 대화체 답변, 추천 없음
  └─ rag → extract_intent(히스토리 병합)
          → hub_rag.search_movies(k=8) → 폴백 search_tag_catalog
          → LLM generate_recommendation(카탈로그 한정)
          → 취향 재정렬 → chat+picks 저장 → 카드 ≤3장
```

재설계에 쓸 수 있는 **기존 자산**(전부 실측 확인):

| 자산 | 위치 | 재사용처 |
|------|------|---------|
| 리뷰: `rating`(nullable)·`body`·`embedding`·`spoiler_spans` | `market_reviews_orm.py` | 평가 트랙의 리뷰 집계·요약·스포일러 필터 |
| 영화: `rating`(TMDB/2)·`synopsis`·`platforms`(OTT)·`age_rating`·`trailer_key`·`release_year` | `studio_movies_orm.py` | 평가 트랙 정량 지표, 예매 트랙 OTT 분기 |
| 랭킹 이력(`box_office`·`chat_trend`) | `market_rankings_orm.py` | 평가 트랙 "요즘 얼마나 언급되나" |
| KOFIC 박스오피스 어댑터 | `adapter/outbound/http/kofic_box_office_adapter.py` | 예매 트랙 "현재 상영 중" 근사 판정 |
| 카카오 로컬 API 키(`KAKAO_API_KEY`, gildle 지오코딩용으로 등재) | `suvisdev/.env` | 예매 트랙 근처 영화관 검색 후보 |
| 제목 부분일치·프랜차이즈 확장 검색 | `market_chat_pg_repository.py` | 두 트랙 공용 "제목→영화 확정" |

**없는 것**: 상영시간표 데이터, 영화관 DB, 영화관 리뷰, 사용자 위치.

## 3. 새 인텐트 체계 — 1차 분류 확장 (2026-08-28 사용자 확정)

**mova의 프로젝트 정의를 "영화를 추천하고, 평가하고, 예매까지 돕는
서비스"로 재정의**하고, 의도 분류는 2단계가 아니라 **1차 분류기에서 바로
나눈다** (초안의 "mova 내부 2차 분류"안은 사용자 결정으로 폐기):

```text
destination ∈ { recommend | evaluate | booking | general | crud }
              (기존 rag 하나가 recommend / evaluate / booking 3종으로 세분화)
```

- 분류기 실체는 ontology Hub의 `IntentClassifierPort`. **소비자는 현재
  mova 채팅뿐임을 실측 확인**(2026-08-28, grep 전수) — 확장해도 다른
  스포크에 영향 없음.
- destination은 포트 docstring에 명시된 공용 계약이므로 확장 시
  ontology `semantic_router_interactor.py`의 destination 분기(현행 rag
  전제)를 **함께 갱신**한다 — 신설 3종을 라우터에서는 기존 rag 경로와
  동일 취급(라우터는 채팅 밖 경로라 세분화 불필요).
- 분류 우선순위(분류기 규칙·프롬프트에 반영):
  1. **booking**: "예매·표·티켓·상영관·영화관·몇 시" 등 어휘 + 제목 엔티티
  2. **evaluate**: "어때·평가·평점·볼만해·재밌어?" 등 어휘 + 제목 엔티티
  3. 그 외 영화 질의 → **recommend** (기존 트랙, 무변경)
- 제목 엔티티가 없으면 booking/evaluate 어휘가 있어도 recommend로 두지
  말고 **어느 작품인지 되묻는다** ("어떤 영화를 예매하시려나요?").

## 4. evaluate 트랙 — "호프 어때??"

```text
제목 추출 → 영화 확정 → 데이터 집계(병렬) → LLM 종합 → evaluation 응답
```

1. **영화 확정**: 제목 ILIKE + 임베딩 유사 검색. 동명·복수 후보면 연도/포스터
   를 제시하고 되묻는다(잘못 짚고 평가하는 것이 최악의 실패 모드).
2. **데이터 집계**:
   - 자체 리뷰: 건수·평점 분포·평균, 최신/대표 리뷰 발췌(embedding 유사도로
     중복 제거, `spoiler_spans` 구간 마스킹 후 인용)
   - 외부 리뷰: **TMDB 리뷰 API**(`/movie/{id}/reviews`) — 공식 API라 약관
     문제 없음, 기존 TMDB 어댑터 옆에 메서드 추가. 영어 위주라 LLM 요약 시
     한국어로 번역 요약. (왓챠피디아는 약관이 크롤링을 명시 금지해 **제외** —
     §8-1 판정 참고)
   - 정량 지표: `movies.rating`(TMDB 유래), 랭킹 등장 이력, 태그·장르
   - 시청 경로: `platforms`(OTT) — "지금 볼 수 있는 곳"까지 한 번에
3. **LLM 종합 생성** — 프롬프트 규칙:
   - **정량(집계 수치)과 정성(리뷰 요약)을 분리**해 서술하고, 정성 서술엔
     반드시 근거(리뷰 발췌·건수)를 붙인다. 데이터에 없는 평가 발명 금지.
   - 자체 리뷰가 적으면(예: 3건 미만) **표본 부족을 명시**한다 — "저희
     리뷰는 아직 N건이라 참고만" (0건 정직 안내·폴백 정직 문구 규칙의 연장).
   - 스포일러 마스킹된 구간은 인용하지 않는다.
4. **응답 형태**: `response_type="evaluation"` + **해당 영화 카드 1장** +
   평가 텍스트 + 지표 payload(평점·리뷰 수·OTT). 카드 3장 강제하지 않는다.

## 5. booking 트랙 — "호프 예매하고 싶어"

외부 데이터 의존이 커서 **단계(Phase)로 나눈다**. 각 Phase는 독립 배포 가능.

### Phase 1 — 지금 있는 것만으로 (신규 크롤링 없음)

```text
영화 확정 → 상영 중 판정 → [상영 중] 근처 영화관 + 예매 경로 안내
                        → [상영 종료/미개봉] OTT 안내 or 개봉일 안내
```

- **상영 중 판정**: KOFIC 박스오피스 최근 등재 여부로 근사
  (`kofic_box_office_adapter` 재사용). 박스오피스 밖 소규모 상영은 놓친다 —
  한계를 응답에 명시("현재 박스오피스 기준").
- **위치**(2026-08-28 사용자 확정): 사용자가 프롬프트에 지역명을 입력하면
  그 지역 기준 **가까운 거리 순**으로 영화관을 추천한다. 지역명이 없으면
  되묻는다. 거리 순위가 상황에 따라 달라질 수 있는 경우(차량 이용 여부,
  대중교통 등)는 **임의로 가정하지 말고 사용자에게 질문한 뒤** 답한다
  (슬롯 필링: 지역=필수, 이동수단=순위에 영향 있을 때만 질문).
  지역명 → 카카오 로컬 API 키워드 검색("○○ 영화관")으로 영화관 목록·주소·
  거리. gildle이 이미 쓰는 키·호출 패턴 재사용(단, gildle 코드 직접 import
  금지 — mova 안에 자체 outbound adapter를 둔다. 스포크 간 직접 import 금지
  규칙).
- **예매 경로**: 상영관 체인(CGV·롯데·메가박스) 공식 예매 페이지 딥링크
  (영화명 검색 URL). 시간표를 직접 보여주는 척하지 않는다 — **모르는 것은
  링크로 위임**(정직성 규칙).
- **응답 형태**: `response_type="booking"` + 영화 카드 1장 + 영화관 목록
  payload + 안내 텍스트.

### Phase 2 — 상영시간표 (진행 확정, 선행 조건 있음)

국내 상영시간표 공식 공개 API는 없어 체인별 조회 경로를 쓴다.
**진행 확정(2026-08-28 사용자)**, 단 착수 시 선행 단계 필수:

1. 각 체인(CGV·롯데시네마·메가박스) 약관·robots.txt **실확인 후 기록** —
   왓챠를 제외시킨 것(§8-1)과 동일한 약관·DB권 리스크가 여기에도 있음을
   고지했고, 그 위에서 진행 결정됨.
2. 완화책: 사용자 질의 시점 단건 조회만(대량 선수집 금지), 결과 단기 캐시,
   저빈도 호출, 차단·실패 시 Phase 1 딥링크로 자동 폴백(기능이 죽지 않게).
3. 시간표 출처를 응답에 명시한다.

### Phase 3 — 영화관 리뷰 종합 (결정 보류)

영화관 자체 리뷰 데이터가 없다. 카카오 플레이스 평점은 API로 제공 범위가
제한적이고, 자체 수집은 콜드 스타트다. Phase 1 배포 후 수요를 보고 결정.

## 6. 아키텍처 배치 (클린 아키텍처 준수)

| 레이어 | 계획 |
|--------|------|
| 인텐트 분류 | ontology `IntentClassifierPort` destination 5종 확장 + `semantic_router_interactor.py` 분기 갱신(신설 3종은 rag 동일 취급). mova `ChatInteractor`는 destination별 위임 분기 |
| Use Case | `ChatInteractor`는 이미 516줄 — 트랙별 서브 유스케이스로 분리: `MovieEvaluationInteractor`·`BookingAssistInteractor` 신설, ChatInteractor는 분류·위임만. 추천 트랙은 무변경 |
| Output Port | 평가 집계용 `ReviewAggregationPort`(리뷰 분포·발췌), 예매용 `TheaterSearchPort`(카카오 로컬) — ABC 신설 |
| Outbound | `adapter/outbound/pg/`에 리뷰 집계 쿼리, `adapter/outbound/http/kakao_local_adapter.py` 신설 |
| Schema/Dto | `ChatResponseDto`·응답 Schema에 `response_type: "recommendation"\|"evaluation"\|"booking"` + 트랙별 payload 필드(absent는 키 생략). 기존 응답과 하위호환 — `response_type` 없으면 프론트는 recommendation으로 간주 |
| 프론트 | `mova-ai-chat-bar.tsx` 렌더 분기: evaluation 패널(지표+발췌 인용)·booking 패널(영화관 리스트). 카드 3장 고정 가정 제거 |
| 저장 | 트랙별 `intent_type`을 chat 테이블에 그대로 저장(`evaluate`·`booking` 값 추가) — picks 저장은 recommend 트랙만. chat_trend는 **조건부**: 단순 질의 미반영, 긍정 평가 반응·예매 의지 확인 시만 반영(§8-5) |

## 7. 기존 하네스 불변식과의 관계

| 기존 규칙(`.claude/rules/mova-chat.md`) | 새 트랙 적용 |
|------|------|
| 카탈로그 밖 movie_id 금지 | 두 트랙 모두 동일 — DB에 없는 영화면 정직하게 "저희 카탈로그에 없다" + 검색 제안 |
| 0건 정직 안내 | evaluate: 리뷰 표본 부족 명시 / booking: 상영 정보 한계 명시로 확장 |
| 폴백 확신 문구 금지 | booking Phase 1의 "박스오피스 기준 근사"도 같은 원칙 — 모르는 것을 아는 척 금지 |
| dedup(재추천 방지) | recommend 전용 — evaluate/booking은 같은 영화를 다시 물으면 다시 답하는 게 맞다 |
| 히스토리 병합 인텐트 | 2차 분류에도 적용 — "호프 어때?" → "예매하고 싶어"(제목 생략)가 이어지게 |
| CPU-bound async 금지·세션 공유 주의 | 동일 적용 |

## 8. 결정 기록 (2026-08-28 사용자 인터뷰)

1. **외부 리뷰 소스 — 왓챠피디아 제외 확정.** 사용자 지시가 "법적 문제
   없으면 진행"이었고 실확인 결과 문제 있음: 왓챠피디아 약관이 크롤링·
   스크래핑·캐싱·미러링을 명시적으로 금지하고 차단 권한을 명시. 국내
   판례도 크롤링 데이터 사용에 DB권 침해 민사 배상을 인정(사람인 vs
   잡코리아 — 2심 배상 4.5억; 야놀자 vs 여기어때 — 형사 무죄였으나 이는
   정보통신망 침입죄 요건 문제로, 민사 리스크와 별개). 리뷰 본문 자체의
   저작권(작성자 귀속)도 있음. → **대안: TMDB 리뷰 API(공식) + 자체 리뷰**
   로 진행(§4 반영).
2. **booking Phase 2(시간표) — 진행 확정.** 단 §5의 선행 조건(체인 약관
   실확인·저빈도 단건 조회·딥링크 폴백)을 지킨다.
3. **위치 입력 — 프롬프트 지역명 입력 방식 확정.** 근거리 순 추천, 이동수단
   등 상황 변수가 순위를 바꿀 땐 되물은 뒤 답변(§5 반영).
4. **분류 방식 — 1차 분류 확장으로 확정(2단 분류안 폐기).** mova 정의를
   "영화를 추천·평가·예매까지 돕는 프로젝트"로 재정의하고, Hub
   `IntentClassifierPort`의 destination을 5종으로 확장한다(소비자가 mova
   뿐임을 실측 확인, semantic router 분기 동반 갱신 — §3 반영).
5. **chat_trend — 조건부 반영.** 단순 질문("호프 어때?" 질의 자체)은
   집계에 넣지 않는다. **사용자의 긍정적 평가 반응**(평가를 듣고 "재밌겠다·
   볼래" 등) **또는 예매 의지**가 확인된 경우에만 그 영화를 chat_trend에
   반영한다. picks는 recommend 트랙 추천 결과만 저장(기존 유지).
   → 후속 발화의 긍정/의지 판정 로직이 새 구현 항목(§9).

## 9. 구현 체크리스트 (Phase 1 기준)

1. [ ] Hub 분류기 destination 5종 확장 + `semantic_router_interactor.py`
   분기 갱신 + 단위 테스트(booking/evaluate/recommend/제목 없음 4축)
1-b. [ ] 후속 발화 긍정 반응·예매 의지 판정 → chat_trend 조건부 반영 로직
   + 테스트(§8-5)
2. [ ] `ReviewAggregationPort` + pg 구현 + 테스트(분포·발췌·스포일러 마스킹)
3. [ ] `MovieEvaluationInteractor` + 프롬프트(정량/정성 분리·표본 부족 명시)
4. [ ] `TheaterSearchPort` + 카카오 로컬 어댑터(+ `KAKAO_API_KEY` 재사용) + 테스트
5. [ ] `BookingAssistInteractor`(상영 중 판정 → 분기) + 테스트
6. [ ] `ChatResponseDto`/Schema `response_type` 확장(하위호환 확인)
7. [ ] ChatInteractor 위임 배선 + DI provider
8. [ ] 프론트 렌더 분기(evaluation·booking 패널)
9. [ ] `pytest -m "not gpu and not ollama"` + `pnpm type-check` + 프로덕션
   실호출 검증("호프 어때?"·"호프 예매하고 싶어" 시나리오)
10. [ ] `.claude/rules/mova-chat.md` §8을 실측 결과로 갱신(설계→관례 승격)
