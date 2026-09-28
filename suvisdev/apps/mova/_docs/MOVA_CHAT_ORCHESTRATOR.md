# mova 채팅 오케스트레이터 (2026-09-27)

> "발화를 한 번 이해하고, 사실은 데이터로 검증한 뒤, 트랙은 실행만 한다."
> 09-27 예매 대화 할루시네이션 사고(WORK_LOG_MOVA 09-27) 뒤 사용자 결정으로 도입.
> 이 문서가 오케스트레이터 층의 SSOT다. 트랙별 규칙은 `.claude/rules/mova-chat.md`.

## 1. 왜

09-27 이전에는 "오케스트레이터"라 부를 층이 없었다. `core/lol/orchestrator.py`는
이름과 달리 Ollama HTTP 클라이언트(모델 한 번 호출)이고, 이해·판단은 셋으로 쪼개져 있었다:

| 역할 | 담당 | 문제 |
|---|---|---|
| 의도 분류 | Hub `LlmIntentClassifier` | destination 5종만. 작품명·지역 슬롯은 안 뽑음 |
| 디스패치 | `ChatInteractor.chat()` if 사슬 + 결정론 가드 5단 | 판단 없음. 가드끼리 어휘가 따로 놂 |
| 슬롯 추출 | 트랙별 정규식 15개(예매 5·해석기 2·인터랙터 8) | 같은 발화를 트랙마다 다르게 읽음 → "파과→파", "시간표 질의→잡담" |

그 결과 하루에 표현이 바뀔 때마다("시간표", "몇 시", "어디서", "체인 지점") 정규식이 하나씩 늘었다.

## 2. 구조

```text
요청 → 소유권 검증
 → ChatOrchestrator.plan()                         apps/mova/app/use_cases/chat_orchestrator.py
     ├ ChatUnderstandingPort.understand()           EXAONE 7.8B(Ollama, core.lol 클라이언트) — JSON 모드
     │    {intent, title, region, time, chain, followup}   ← 최근 4턴 + 발화
     ├ 정제(parse_understanding)                    "null"·"없음"·스키마 문구·발화에 없는 체인명 제거
     ├ 검증: title → 카탈로그 정확 일치만 확정      없으면 title_text만 넘겨 트랙이 되묻는다
     └ 안전망: 예매 어휘 있는데 LLM이 booking 아니면 booking (추천 발화 제외)
 → _dispatch_slots()
     booking  → BookingAssistService.assist_slots()  작품+지역 → 곧장 극장 검색 / 작품만 → 지역 되묻기
     evaluate → 평가 트랙(검증된 제목)
     recommend→ 기존 추천 파이프라인(무변경)
     general  → Gemini 잡담(상영작 근거 포함)
 이해 실패(Ollama 불가·형식 오류) → None → 기존 결정론 선분기 + 분류기 경로(폴백, 무변경)
```

지역은 여기서 검증하지 않는다 — 예매 트랙이 카카오 지오코딩으로 확인하고 못 찾으면 되묻는다.
LLM은 이해만, 사실(카탈로그·극장·시간표·상영 여부)은 전부 데이터가 확인한다.

## 3. 모델 선택 실측 (노트북 RTX 4060, 발화 6건, 09-27)

| 모델 | 평균 지연 | 품질 |
|---|---|---|
| exaone3.5:2.4b | 0.87s | 불가 — 제목 null, 스키마 문구("시각/날짜 표현") 그대로 출력, "옵세션 어때"→recommend |
| **exaone3.5:7.8b** | 0.85s(예열 후; 첫 호출 7.3s) | 파과·인턴·"군자" 이어받기(title=인턴, region=군자)·옵세션 evaluate 정확 |

7.8B가 기존 Qwen 분류기와 비슷한 지연이라 채택. 포트폴리오 채팅과 같은 모델을 공유해 VRAM 추가
부담 없음(keep_alive 30m). 노이즈("없음", 발화에 없는 chain)는 정제 단계가 걷어낸다.
`MOVA_ORCHESTRATOR_MODEL`로 교체, `MOVA_ORCHESTRATOR_ENABLED=0`이면 미주입(롤백 스위치).

## 4. 남긴 것·없앤 것

- 남김: `_BOOKING_LEXICON` 안전망(오케스트레이터 안에서), 기존 결정론 경로 전부(폴백용).
- 트랙 정규식은 **삭제하지 않았다** — 폴백 경로가 아직 쓴다. 오케스트레이터가 프로덕션에서
  한 주 이상 안정되면 폴백 경로의 선분기 4단(지역 마커·후보 선택·평가 후속·어휘 가드)을
  걷어내는 것이 다음 단계다. 그 전엔 두 경로를 하네스가 같이 본다.
- 멀티턴 상태: 아직 『제목』 마커를 history에서 파싱하는 코드가 남아 있다. LLM followup이
  그 역할을 흡수하므로, 폴백 제거와 함께 구조화 슬롯(conversation meta)으로 옮긴다.

## 5. 검증

- 단위: `apps/mova/tests/test_chat_orchestrator.py`(정제·검증·디스패치·폴백 14건)
- 회귀: `scripts/eval_chat_multiturn.py`(17장면) · `scripts/eval_chat_queries.py`(28질의 + 카드 품질 지표)
- 실패 채굴: `scripts/mine_chat_failures.py`(chat_messages + 섀도 로그 → 규칙 판정 후보, 아래 §7)
- 로그: `[Orchestrator] trace= intent=…(llm=…) title= movie= region= followup=`

## 6. intent 경계 — "작품 하나가 무엇인지"는 evaluate (2026-09-28)

실사용: 스파이더맨 시리즈 추천 직후 "제일 최신 스파이더맨이 뭐야" → 7.8B가 title=브랜드 뉴 데이는 맞혔지만
intent=recommend → 추천 트랙은 슬롯 제목을 쓰지 않고 의도를 재추출, 브랜드 뉴 데이는 기추천 dedup으로
빠져 0건 "카탈로그에 없어요". 프롬프트 경계를 고쳤다:
- **evaluate** = 특정 작품 하나가 어떤지·**무엇인지**("무슨 영화야", "제일 최신 ○○가 뭐야"). 답이 작품
  하나로 정해지면 title에 그 작품.
- **recommend** = 여러 편 골라 달라는 것 + "최신 영화 뭐 있어" 같은 **작품이 특정되지 않은 목록 질문**.
- 예시는 스파이더맨이 아닌 쥬라기로(실패 문장은 평가에만 남겨 일반화를 잰다).
7.8B 프로브 12/13 → 20/20(첫 수정에서 "최신 영화 뭐 있어"가 evaluate로 새는 회귀를 잡아 경계 문구 추가).
한계: 앞 대화에 목록이 없을 때 "가장 최근 해리포터"는 7.8B가 세상 지식으로 제목을 지어낸다
(비밀의 방) — 프랜차이즈 최신작은 카탈로그 연도로 풀어야 한다(미해결).

## 7. 섀도 비교 — 학습한 이해 모델 v6 (2026-09-28 가동)

`MOVA_ORCHESTRATOR_SHADOW_MODEL=mova-understand`(Ollama, `~/models/mova-understand-v6/`)이면 주 모델(7.8B)로
응답한 뒤 같은 발화를 v6에 백그라운드로 한 번 더 읽혀 필드별로 비교해
`datasets/understanding/shadow_log.jsonl`(hostPath)에 쌓는다. 응답엔 영향 없음, 비우면 꺼짐.
- **v6는 CPU 전용**(Modelfile `PARAMETER num_gpu 0`): GPU 8GB에 lora-server 2.5 + 7.8B 4.7GB가 이미 올라가
  v6까지 올리면 Ollama가 요청마다 모델을 교체한다. 웜 1.7s·콜드 13s, `shadow_s`는 CPU 값이라 속도 비교 금지.
- **첫 판정(50건 중 불일치 15)**: v6는 맥락 제목 누락/오답("그거 줄거리"→스파이더맨 2, "26년꺼"), 일반어
  제목 환각('바로'·'영화'), followup 정의 불일치(8건) → **7.8B→v6 전환 불가**, v7 데이터 항목으로.
