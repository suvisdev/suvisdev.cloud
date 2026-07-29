---
paths:
  - "suvisdev/**/test/**/*.py"
  - "suvisdev/**/tests/**/*.py"
---

## 테스트 규칙

테스트는 **백엔드(`suvisdev/`)의 pytest**가 전부다(현행 58개 파일). 프론트
`suvis/`에는 테스트 코드·테스트 의존성이 없으며, 검증은 `pnpm type-check`·
`pnpm lint`로 한다. 새로 테스트 프레임워크를 도입하지 않는다.

### 1. 위치·이름

- 파일명은 `test_*.py`. 디렉터리는 앱마다 `test/` 또는 `tests/`로 갈리는데
  (`apps/ontology/test`, `apps/mova/tests`) **그 앱의 기존 이름을 따른다** —
  통일하겠다고 옮기지 않는다.
- 새 앱의 테스트 경로는 `suvisdev/pytest.ini`의 `testpaths`에 추가해야 수집된다.

### 2. 마커

- `@pytest.mark.gpu` — 실제 GPU·모델 가중치가 필요한 테스트.
- `@pytest.mark.ollama` — 실제 Ollama 서버가 필요한 테스트.
- `@pytest.mark.asyncio` — async 테스트(pytest-asyncio).
- 외부 자원(GPU·모델·서버·네트워크)에 의존하면 **반드시 마커를 붙인다.** 마커 없는
  테스트는 아무 환경에서나 즉시 통과해야 한다.
- 기본 실행은 `pytest -m "not gpu"`. 마커를 안 붙이면 CI·동료 환경에서 깨진다.

### 3. conftest.py — 환경 격리는 여기서

- `sys.path` 부트스트랩은 각 테스트 파일이 아니라 앱의 `conftest.py`에서 한 번만
  한다(`apps/titanic/tests/conftest.py`가 원형).
- 마커 자동 skip도 conftest에서 처리한다. 명시적으로 고르지 않으면 건너뛰게 한다.
  ```python
  def pytest_collection_modifyitems(config, items):
      if not config.option.markexpr:
          skip = pytest.mark.skip(reason="ollama 서버 필요: pytest -m ollama 로 실행")
          for item in items:
              if item.get_closest_marker("ollama"):
                  item.add_marker(skip)
  ```
- **외부 다운로드를 타는 라이브러리는 conftest에서 오프라인으로 막는다.**
  `apps/ontology/test/conftest.py`가 `HF_HUB_OFFLINE`·`TRANSFORMERS_OFFLINE`을
  설정한다 — 켜 두지 않으면 캐시가 있어도 매번 HF Hub에 접속하고, 네트워크가
  불안정하면 스위트 전체가 hang처럼 멈춘다. 이런 환경변수는 라이브러리가 import
  시점에 한 번만 읽으므로 반드시 conftest에서 설정해야 한다.

### 4. 테스트 더블 — 포트 구현 fake 우선

- 유스케이스는 **출력 포트를 구현한 fake**로 검증한다. 저장 백엔드(S3/DB)나 실제
  모델에 의존하지 않게 한다. 이름은 `_Fake<대상>`(`_FakeVisionRepository`,
  `_FakeRepository`, `_FakeRedis`).
- fake는 포트 ABC를 실제로 상속한다. 그래야 인터페이스가 바뀌면 테스트가 먼저 깨진다.
- 협력자가 여럿이고 호출 여부만 보면 될 때는 `unittest.mock.AsyncMock()`을 쓴다.
- **포트에 추상 메서드를 추가하면 fake에도 같이 구현한다.** 안 하면 인스턴스화
  시점에 `TypeError`가 난다.

### 5. 무엇을 검증하나

- 도메인은 불변성(frozen dataclass), 동등성, 어댑터 교체 가능성(DIP)까지 본다 —
  `apps/titanic/tests`가 기준선이다.
- 인터랙터는 **정책**을 본다(임계값 판정, 게이트 통과·반려, 저장 호출 여부).
- 어댑터의 실제 추론·실제 DB는 마커를 붙인 통합 테스트로 분리한다.

### 6. 실패를 다룰 때

- 시그니처가 바뀌어 깨진 테스트는 **실제 호출 형태에 맞게 테스트를 고친다.**
  프로덕션 코드를 옛 시그니처로 되돌리지 않는다.
- 다만 고치기 전에 "리네임 드리프트인지 도메인 재설계인지" 먼저 확인한다. 테스트가
  옳고 코드가 틀린 경우도 있다(실제로 `summary()`가 없는 필드를 참조하던 버그를
  테스트 작성 중 발견한 사례가 있다).
- 학습 산출물(`apps/ontology/runs/`)이나 실행 중인 Ollama가 없어서 나는 실패는
  기존 조건이다. 내가 깨뜨린 것과 구분해서 보고한다.
