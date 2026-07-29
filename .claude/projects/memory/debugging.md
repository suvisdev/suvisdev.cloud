# 디버깅 인사이트

한 번 원인을 밝힌 문제와 그때 쓴 진단 방법. 같은 증상이 다시 나올 때 처음부터
파지 않기 위한 기록이다.

---

## lint-imports는 baseline부터 실패 상태다 (2026-07-29 확인)

`suvisdev/`에서 import-linter를 돌리면 **아무것도 고치기 전부터**
"Hub (ontology) must not depend on any spoke" 계약이 깨져 있다. 실패를 보고 방금
내 변경이 만든 회귀라고 결론짓지 말 것.

- **원인**: `core/matrix/grid_oracle_database_manager.py`가 `create_all()`·
  `ensure_titanic_tables()`를 위해 dispatch·mova·titanic·viewer의 ORM을 전부
  import한다. 그래서 ontology의 어떤 모듈이든 이 매니저를 import하면
  `ontology → core.matrix.… → 각 spoke` 경로가 생겨 위반으로 잡힌다.
- **정적 분석이라 DI 배선과 무관**하다. 파일이 존재하기만 하면 걸린다.
- **회귀 판정법**: 반드시 변경 전후를 비교한다.
  ```bash
  git stash && PYTHONPATH="$PWD:$PWD/apps" lint-imports; git stash pop
  PYTHONPATH="$PWD:$PWD/apps" lint-imports
  ```
- **실행 시 주의**: `PYTHONPATH`에 저장소 루트와 `apps/`를 **둘 다** 넣어야 한다.
  그냥 `lint-imports`만 치면 `Could not find package 'ontology'`로 죽는다.
- 근본 수정(ORM 일괄 import 제거)은 별도 과제이며 아직 착수하지 않았다.

---

## HF 모델 다운로드 hang (CLIP, 2026-07-28 발생 → 07-29 해결)

`apps/ontology/test` 실행 중 `openai/clip-vit-base-patch32` 다운로드가 1시간+
멈추던 문제.

- **hang 단계 특정이 먼저다**: collection(import) 단계인지 테스트 실행 단계인지
  `--collect-only`로 나눠 돌려 확인한다. 이 건은 **실행 단계**였다 — 어댑터가
  함수 본문 안에서 import되고 `from_pretrained()`도 `detect()` 호출 시점에만
  돌기 때문에 collection은 멀쩡했다.
- **결정적 증거**: `~/.cache/huggingface/hub/models--openai--clip-vit-base-patch32/
  blobs/*.incomplete` — 490MB를 다 받아놓고 확정만 안 된 채 멈춘 파일. 캐시 상태를
  먼저 보면 네트워크 문제인지 코드 문제인지 바로 갈린다.
- **근본 원인은 코드가 아니라 구조**였다. 캐시가 있어도 매 호출마다 HF Hub에 etag
  확인을 하고, 그게 걸리면 무한정 기다린다.
- **해결**: `apps/ontology/test/conftest.py`에서 `HF_HUB_OFFLINE=1` ·
  `TRANSFORMERS_OFFLINE=1` 설정. 네트워크 경로를 아예 막아 "캐시 있으면 즉시 통과,
  없으면 즉시 에러"로 바뀐다. `huggingface_hub.constants`가 이 값을 **import 시점에
  한 번만** 읽으므로 반드시 conftest에서 설정해야 한다.
- **검증 결과**: 캐시 완전 → GPU 테스트 5개 8.9초 통과. 캐시 일부 누락 → hang 대신
  4.5초 만에 `OSError`로 즉시 실패.
- **전제**: GPU 테스트는 모델이 **미리 캐시돼 있어야** 한다. 새 머신에서는 오프라인을
  잠시 끄고 한 번 받아둬야 한다.

---

## 로컬 Postgres가 안 떠 있는 환경이 있다

`suvisdev/.env`의 `DATABASE_URL`은 `localhost:5432`를 보는데, WSL 환경에 Postgres가
기동돼 있지 않을 수 있다(docker 명령도 없는 경우가 있음).

- 증상: `alembic current` → `connection refused`.
- 이때 마이그레이션은 **문법·체인만** 검증 가능하다: `alembic history`로 단일 head인지,
  `down_revision`이 직전 head를 가리키는지 확인.
- 실제 `alembic upgrade head` 적용은 DB가 뜬 환경에서 따로 해야 한다. 검증 못 한
  부분은 보고할 때 명시할 것.

---

## 테스트 실패가 원래 있는 것들

새로 깨뜨린 게 아닌지 먼저 의심할 대상.

- `apps/ontology/test/test_echo_sentiment_adapter.py` — 학습 산출물
  `apps/ontology/runs/echo_sentiment/adapter`가 `.gitignore` 대상이라 클론 직후엔 없다.
- `apps/titanic/tests/test_korean_ai.py::test_real_ollama_korean_question` — 실제
  Ollama 서버 필요.
- 일반 실행은 `pytest -m "not gpu"`로 돌린다.
