# 쿠모니지 규칙 변경 — 선도 패스할 수 있다 (계획 A)

**Goal:** 바닥이 빈 선 차례에서도 패스할 수 있게 하고, 선이 패스하면 다음 사람이 선이 된다.

**Architecture:** 규칙의 기준은 `cases.json` → `rules.py`(하네스) → `game.py`(한 수 진행) 순서다. 기대값부터 고치고 엔진 둘을 같이 맞춘다. 앱은 서버가 주는 상태만 그리므로 패스 버튼을 켜는 것만 바꾼다. 멀티의 20초 자동 패스(계획 C)가 이 규칙을 전제로 한다.

**Tech Stack:** Python 3.13 · pytest / Flutter 3.47

## Global Constraints
- 2026-11-21 사용자 결정: "선도 패스 허용(규칙 변경)". 싱글에도 같은 규칙을 적용한다(규칙은 하나).
- 선의 패스는 **바퀴 패스 수에 넣지 않는다**(바닥이 비어 가져갈 바퀴가 없음). 꽃잎·보너스·pot 변화 없음, 차례만 다음 사람.
- 봇은 선일 때 패스하지 않는다(지금 동작 그대로 — 테스트로 고정).
- 바탕화면 `타일게임_기획/기획문서_하네스/`의 `RULES.md`·`cases.json`·`rules.py`도 같이 고친다(기획 SSOT). 저장소 사본과 바이트 동일 유지.

---

### Task 1: 기대값·엔진

**Files:**
- Modify: `kumoniji/server/kumoniji/cases.json` (사례 2개 뒤집기 + 새 사례 1개)
- Modify: `kumoniji/server/kumoniji/rules.py:140-143`
- Modify: `kumoniji/server/kumoniji/game.py:52-54`
- Test: `kumoniji/server/tests/test_rules_cases.py`(기존, cases.json 전부 돌림), `tests/test_game.py`(Game == simulate 무작위 대조 — 무작위 수에 선 패스를 섞도록 확장)

- [ ] **Step 1: cases.json 고치기**

```json
{"id": "진행: 선도 바닥이 비었을 때 패스할 수 있다(11-21)", "type": "simulate", "hands": [["솜1", "잎9"], ["잎4"], ["잎5"], ["잎6"]], "moves": ["패스", ["잎4"]], "expect": {"error_at": null, "winner": 1}, "today": "잎"},
{"id": "진행: 새 선도 패스 → 다음 사람이 선(11-21)", "type": "simulate", "hands": [["솜1", "잎9"], ["잎4"], ["잎5"], ["잎6"]], "moves": [["솜1"], "패스", "패스", "패스", "패스", ["잎4"]], "expect": {"error_at": null, "winner": 1}, "today": "잎"},
{"id": "진행: 넷 다 선 패스해도 판은 이어짐(선 패스는 바퀴 패스 수에 안 셈 — 세면 3번째에서 빈 바닥을 가져가려다 깨짐)", "type": "simulate", "hands": [["솜1", "잎9"], ["잎4"], ["잎5"], ["잎6"]], "moves": ["패스", "패스", "패스", "패스", ["솜1"]], "expect": {"error_at": null}, "today": "잎"}
```
기존 `진행: 선은 바닥이 비었을 때 패스 불가`·`진행: 새 선은 패스 불가` 두 개는 위 첫 두 개로 **바꾼다**(삭제가 아니라 기대값 반전 — id에 날짜를 붙여 바뀐 규칙임을 남김).

- [ ] **Step 2: 실패 확인** — `cd kumoniji/server && uv run --no-project --python 3.13 --with pytest --with httpx --with fastapi==0.136.3 pytest -q tests/test_rules_cases.py` → 새 사례 FAIL.

- [ ] **Step 3: rules.py**

```python
        if move == "패스":
            if table:  # 바닥이 비었으면(선) 패스는 차례만 넘긴다 — 바퀴 패스 수에 안 셈(11-21)
                passes += 1
            if passes == 3:
```

- [ ] **Step 4: game.py** — 같은 모양:

```python
        if move is None:
            if self.table:  # 선 패스는 차례만 넘긴다(11-21)
                self.passes += 1
            if self.passes == n - 1:
```

- [ ] **Step 5: test_game.py 무작위 대조에 선 패스 섞기** — 무작위 진행 생성기가 바닥이 비었을 때 10% 확률로 `None`을 고르게 하고, `Game`과 `simulate` 결과가 같은지 500판.

- [ ] **Step 6: 서버 테스트 전체 통과** (135 + 새 사례).

### Task 2: API·봇·앱

**Files:**
- Modify: `kumoniji/server/kumoniji/api.py` — `reason()`의 `lead_pass` 분기 삭제(이제 이유가 아님). 앱 arb의 `lead_pass` 문구도 삭제.
- Modify: `kumoniji/app/lib/table_screen.dart` — 패스 버튼 `onPressed: !myTurn || g.table.isEmpty ? null : ...` → `!myTurn ? null : ...`
- Test: `tests/test_bots.py` — `test_bots_never_pass_as_leader`: 세 난이도 × 200판 동안 `pick`이 바닥이 비었을 때 `None`을 내지 않음. `tests/test_api.py` — 사람이 선일 때 빈 수(`[]`)로 패스하면 200·차례가 1번으로. `app/test/table_screen_test.dart` — 선 차례에 패스 버튼이 켜져 있음.

- [ ] 실패 테스트 → 구현 → 서버·앱 테스트 통과 → 바탕화면 기획 문서 3개 동기화(`cmp`로 바이트 동일 확인) → 커밋 `feat: 쿠모니지 선도 패스 가능`
