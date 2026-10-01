# LangGraph 에이전트 루프 — 구현 계획 (2026-10-01 작성, 미착수)

> **목적: 면접용.** 직접 짠 에이전트 루프(`ontology/app/agent/agent_loop.py`)를 LangGraph로 옮기고,
> **기존과 결과가 같다는 걸 테스트·회귀 하네스로 증명**한다. 기능 개선이 목적이 아니다 — 동작은 1바이트도 바꾸지 않는다.
> 면접 문장: "프레임워크 없이 에이전트 루프를 먼저 짜서 문제(과호출·인자 창작·반복)를 코드로 막았고, 그걸 LangGraph
> 그래프로 옮겨 같은 하네스로 동등성을 검증했다. 그래서 LangGraph가 뭘 대신해 주고 뭘 대신 못 하는지 안다."
>
> **이 문서를 읽는 클로드에게:** 아래 "현재 구조"는 10-01에 코드를 읽어 정리한 사실이다. 착수 전에 파일이 그대로인지
> 다시 확인하라(특히 `agent_loop.py`·`chat_agent.py`·`action_protocol.py`). 응답은 한국어.

---

## 1. 현재 구조 (사실)

### 1.1 루프 — `apps/ontology/app/agent/agent_loop.py` (132줄, 허브 공용)
```text
AgentLoop(*, judge: JudgePort, system_prompt: str, tools: list[Tool], max_steps: int = 3)
  async run(message, history, *, trace_id="-") -> AgentDecision
Tool(name, params: tuple[str,...], run: ToolRunner | None, grounded: tuple[str,...])   # run=None → 터미널 도구
AgentDecision(terminal: dict|None, results: list[dict], steps: int, trace: list[str])
```
`run`의 한 스텝(최대 `max_steps`, 넘으면 `"BUDGET → FINAL"`):
1. `raw = await judge.decide(system, render_prompt(message, history, results))`
2. `action = parse_action(raw, spec)` — `None`이면 `"형식 아님 → FINAL"`, `FINAL`이면 종료
3. **근거 가드**: `tool.grounded` 인자가 `is_grounded(값, context)` 실패 → results에 error를 넣고 **다시 판단**(continue)
4. **반복 가드**: 같은 `name+args(JSON, sort_keys)`면 `"반복 호출 → FINAL"`
5. **터미널 도구**(`run is None`) → `d.terminal = action` 후 종료(호출자 트랙이 실행)
6. 데이터 도구 실행 → 예외는 `{"error": ...}`로 삼켜 계속, 성공 결과는 `context`에 누적(다음 근거 판정용)
- `JudgeError`는 잡지 않고 올린다 — 호출자(mova)가 예전 경로로 폴백한다. **이 계약 유지 필수.**
- `context` 초기값 = `normalize(message + 히스토리 content 이어붙임)`.

### 1.2 모델·프로토콜 — 바꾸지 않는다
- `JudgePort.decide(system, prompt) -> str` (`ontology/app/ports/output/judge_port.py`). 운영 판단 모델은 학습한
  `mova-agent-v9`(Ollama, CPU, `MOVA_AGENT_MODEL`).
- 응답 형식은 `<tool_call>{json}</tool_call>` 또는 `FINAL` — `ontology/domain/agent/action_protocol.py`의
  `render_prompt`·`parse_action`·`normalize`·`is_grounded`. **LangChain의 tool calling(bind_tools)으로 바꾸지 말 것** —
  학습 형식이 달라 모델이 깨진다. LangGraph 노드는 일반 함수라 `JudgePort`를 그대로 부를 수 있다.

### 1.3 사용처
- `apps/mova/app/use_cases/chat_agent.py` `MovaChatAgent.__init__` 93행에서 `AgentLoop(...)`를 직접 생성.
  도구: `search_movie`·`get_movie_details`·`now_showing`(데이터) + 추천·시간표 등 터미널 + `mark_watched`(터미널).
- 주입은 `apps/mova/dependencies/market_chat_provider.py` `get_chat_agent` — **`MOVA_CHAT_AGENT=1`일 때만**(기본 0).
  운영 `.env`에 이 키가 있으니 착수 시 값 확인. 0이면 운영 하네스는 에이전트를 안 탄다 → 로컬/노트북에서 켜고 비교.

### 1.4 검증 자산 (이미 있음)
- 단위: `apps/ontology/test/agent/test_agent_loop.py`(7개), `apps/mova/tests/test_chat_agent.py`
- 회귀 하네스(suvisdev 폴더에서):
  - `python scripts/eval_chat_queries.py --base-url <URL> --save <json>` — 단일턴 23질의
  - `python scripts/eval_chat_multiturn.py --base-url <URL>` — 실대화 멀티턴 장면
  - 노트북 NodePort 예: `http://127.0.0.1:31386`

---

## 2. 설계

### 2.1 원칙
- **drop-in**: `LangGraphAgentLoop`는 `AgentLoop`과 **같은 생성자·같은 `run` 시그니처·같은 `AgentDecision`**을 반환.
  `Tool`·`AgentDecision`·`action_protocol`은 공유(복제 금지).
- **엔진 스위치**: 환경변수 `AGENT_LOOP_ENGINE=native|langgraph`(기본 `native`). 허브에 팩토리 하나:
  `make_agent_loop(**kwargs)` → 엔진에 따라 둘 중 하나. `chat_agent.py` 93행은 `AgentLoop(` → `make_agent_loop(` 한 줄만.
  기본이 native라 머지·자동 배포(CD)돼도 운영 동작 불변.
- 포트(ABC) 추가는 하지 않는다 — 구현이 둘뿐이고 둘 다 같은 클래스 모양이라 팩토리로 충분(YAGNI). 면접에서 물으면
  "포트를 둘지 고민했고, 교체 지점이 한 곳이라 팩토리로 끝냈다"고 설명.

### 2.2 그래프
```text
State(TypedDict): message, history, context, results, seen, steps, trace, terminal, action, raw

START → decide ──(budget 초과)──────────────→ END   trace "BUDGET → FINAL"
          │
          └→ route ─ 형식 아님 ──────────────→ END   "형식 아님 → FINAL | ..."
                   ─ FINAL ──────────────────→ END   "FINAL"
                   ─ 근거 없음 → (error 결과 추가) → decide      ← 재판단(예산 안에서)
                   ─ 반복 호출 ──────────────→ END   "반복 호출 X → FINAL"
                   ─ 터미널 ─ (terminal 기록) → END   "터미널 X(...)"
                   ─ 데이터 도구 → execute → decide             ← 결과·context 누적
```
- 노드: `decide`(예산 확인 + `judge.decide` + `parse_action`), `route`는 **조건부 엣지 함수**(상태만 보고 다음 노드 이름 반환),
  `reject_ungrounded`, `execute`(도구 실행, 예외 → error 결과). 근거·반복 판정 로직은 `agent_loop.py`와 같은 함수/식을 쓴다.
- trace 문자열·로그 한 줄(`[AgentLoop] trace=.. steps=..`)까지 **기존과 같게** — 동등성 테스트가 trace까지 비교한다.
- `JudgeError`는 노드에서 잡지 말고 그대로 올라오게(`graph.ainvoke`가 전파하는지 테스트로 확인).
- `recursion_limit`: 근거 재판단 루프 때문에 LangGraph 기본 제한(25)과 별개로 **예산은 state의 steps로 직접** 센다.
  `ainvoke(config={"recursion_limit": max_steps*3+5})` 정도로 넉넉히.
- 그래프는 `__init__`에서 한 번 `compile()`(요청마다 컴파일 금지).

### 2.3 의존성
- `requirements.txt`에 `langgraph==<설치 시 최신 안정판>` 핀 추가. 이미 `langchain-core==1.5.1`이 있으니 호환 버전 확인
  (`pip install langgraph` 후 `pip check`). Python 3.13. 이미지 크기 영향 확인(`docker images`).
- import-linter: 외부 패키지라 계약 영향 없음 — 그래도 `lint-imports` 실행.
- mypy strict: langgraph 타입이 부족하면 `[[tool.mypy.overrides]] module="langgraph.*" ignore_missing_imports` 정도만.

### 2.4 2단계(선택, 시간 남으면 — 면접 소재)
- **그래프 그림**: `compiled.get_graph().draw_mermaid()` 결과를 이 문서와 블로그(jk.suvisdev.cloud)에 넣기.
- **checkpointer**: 지금 대화 기억은 클라이언트가 보내는 history다. `MemorySaver`/Postgres checkpointer로 서버 측 상태를
  두는 건 **동작이 바뀌므로 이번 범위 밖** — "다음 단계로 이렇게 쓸 수 있다"까지만 문서화.
- **interrupt(사람 확인)**: 예매 터미널 직전 확인 질문 — 역시 동작 변경이라 아이디어만.

---

## 3. 작업 순서 (집에서)

1. 브랜치 `feat/langgraph-agent-loop`(main에서). `pip install langgraph` 후 버전 핀. → 검증: `pip check`, `python -c "import langgraph"`
2. `apps/ontology/app/agent/langgraph_agent_loop.py` 작성(2.2). `make_agent_loop` 팩토리는 같은 패키지(`agent/__init__` 또는
   `agent/factory.py`). → 검증: mypy strict 0, ruff 0
3. **동등성 단위 테스트**: `test_agent_loop.py` 7개를 `@pytest.mark.parametrize("engine", ["native", "langgraph"])`로 두 엔진에
   돌린다 — `terminal`·`results`·`steps`·`trace` 전부 같아야 통과. 추가 케이스: 근거 실패 후 재판단 성공, 예산 초과,
   도구 예외, `JudgeError` 전파. → 검증: pytest 전부 통과
4. `chat_agent.py` 93행을 `make_agent_loop(...)`로. → 검증: `apps/mova/tests` 통과, 기본(native) 동작 불변
5. **하네스 동등성**: 백엔드를 `MOVA_CHAT_AGENT=1`로 두고 엔진만 바꿔 두 번 —
   `AGENT_LOOP_ENGINE=native` → `eval_chat_queries.py --save native.json`, `eval_chat_multiturn.py`
   `AGENT_LOOP_ENGINE=langgraph` → `--save langgraph.json`, `eval_chat_multiturn.py`
   → 검증: 23질의·멀티턴 통과 수 동일, 카드·도구 trace diff 없음(모델이 temperature 0이어도 llama 캐시로 흔들릴 수 있음 —
   다르면 같은 질의를 엔진별로 3번씩 돌려 분포로 비교, `.claude/rules/mova-chat.md` §2 마지막 항목 참고)
6. 지연 비교: 엔진별 질의당 평균 응답 시간(LangGraph 오버헤드가 수 ms 수준인지).
7. 그래프 mermaid 생성 → 이 문서 §5에 붙이기. 커밋은 ①의존성+구현+테스트 ②mova 연결 ③문서로 나눈다.
8. PR → CI 3종 통과 → 머지(CD 자동 배포, 기본 native라 운영 불변). 운영에서 켜 볼지는 사용자 결정.

## 4. 면접 대비 메모 (구현 후 채울 것)
- LangGraph가 대신해 준 것: 상태 전이를 그래프로 명시, 조건부 분기, 시각화, (원하면) 체크포인트·interrupt.
- 대신 못 한 것: 근거 가드·반복 가드·예산은 **도메인 규칙이라 여전히 직접 코드** — 프레임워크는 "어디서 판단하나"를
  정리해 줄 뿐 "무엇을 막나"는 정해 주지 않는다.
- 왜 tool calling(bind_tools)을 안 썼나: 판단 모델을 `<tool_call>` 형식으로 학습했기 때문 — 프레임워크에 맞추려고
  모델을 바꾸는 건 본말전도.
- 동등성 결과 수치(테스트 수·하네스 통과 수·지연)를 여기 기록.

## 5. 그래프 그림
(구현 후 `draw_mermaid()` 결과를 붙인다)
