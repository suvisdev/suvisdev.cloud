# 홈 포트폴리오 AI 채팅 Implementation Plan

**Goal:** 메인페이지 입력창을 AI 대화 입구로 바꿔, 공개 문서(지킬 포스트·앱 소개·공개 프로필)를 근거로 "진수택과 그의 앱"에 대해 답하는 채팅을 붙인다.

**Architecture:** 새 앱을 만들지 않는다. 문서 RAG 스택(임베딩 포트·pgvector `hub_knowledge`·`HubLlmPort`·Gemini 폴백)이 전부 ontology(Hub)에 이미 있으므로, ontology에 `portfolio` 유스케이스·라우터 하나를 얹고 `hub_knowledge.source='portfolio_doc'` 행으로 문서를 분리한다. 답변은 도구 호출 없이 **매 질문마다 벡터 검색 상위 청크를 근거로 주입**해 EXAONE 7.8B(ollama)가 생성하고, 실패 시 Gemini로 폴백한다. 프론트는 홈 입력창 아래 대화 패널을 연다.

**Tech Stack:** FastAPI · SQLAlchemy async · pgvector(`hub_knowledge`, 1024차원 bge-m3) · ollama `exaone3.5:7.8b` · google-genai(폴백) · Next.js App Router(프록시 route + 클라이언트 컴포넌트) · pytest(unittest 스타일).

## Global Constraints

- 사용자 결정(2026-09-27): 오케스트레이터는 **로컬 EXAONE 7.8B**, 자료는 **공개용 세트만**, 개인정보는 **이름·학력 등 남들도 공개하는 선**(전화·이메일·주소 금지), 접근은 **누구나 + IP 레이트리밋**.
- 파인튜닝 없음. 문서 갱신은 인제스트 스크립트 재실행으로 반영.
- Clean Architecture(`suvisdev/CLAUDE.md`): Router→InputPort→Interactor→OutputPort→Repository, `Command.from_schema()`, Dto `to_schema()`는 lazy import, Interactor에서 HTTPException 금지. 스타 토폴로지: ontology(Hub)는 Spoke를 import하지 않는다.
- mypy strict · ruff line-length 100 · 테스트는 `unittest.TestCase`/`IsolatedAsyncioTestCase` + `TestClient` + `dependency_overrides`, 더블은 포트 ABC 상속 fake 또는 `AsyncMock`.
- 프론트: `.claude/rules/typescript.md`(any 금지, type 선호, React.FC 금지), `api-standards.md`(프록시는 `backendFetch`, 클라이언트는 `lib/*-api.ts` 경유). 홈 파일 관례대로 hex 색상 + `dark:` 쌍 병기.
- 실측 제약: 노트북 RTX 4060 8GB — 7.8B(num_ctx 8192 시 5.7GB) + lora-server(2.4GB) 동시 상주 가능, 콜드 로드 5s·근거 2,240토큰 응답 7s(웜 ~2s). ollama 기본 num_ctx 4096이라 **num_ctx 8192를 명시**해야 근거가 잘리지 않는다.
- 검증 명령(백엔드, `suvisdev/`): `python -m pytest apps/ontology/test core/lol/tests -m "not gpu and not ollama" -q` · `PYTHONPATH="$PWD:$PWD/apps" lint-imports` · `ruff check apps/ontology core/lol scripts/ingest_portfolio_docs.py` · `mypy apps/ontology/app apps/ontology/adapter/outbound/llm/exaone_llm_adapter.py core/lol` · `python -c "import main"` · `python scripts/check_env_drift.py`. 프론트(`suvis/`): `npx pnpm type-check` · `npx pnpm lint`.

---

## 파일 구조

| 구분 | 경로 | 책임 |
|---|---|---|
| 수정 | `core/lol/t1_mid_faker_orchestrator.py` | `generate`에 `num_ctx` 옵션 추가(본문 조립을 `_build_body`로 분리) |
| 생성 | `apps/ontology/adapter/outbound/llm/exaone_llm_adapter.py` | `ExaoneLlmAdapter(HubLlmPort)` — 7.8B, temperature 0, num_ctx 8192, keep_alive 5m |
| 생성 | `apps/ontology/app/dtos/portfolio_chat_dto.py` | `PortfolioChatTurn` · `PortfolioChatCommand.from_schema` · `PortfolioChatAnswerDto.to_schema` |
| 생성 | `apps/ontology/app/ports/input/portfolio_chat_use_case.py` | `PortfolioChatUseCase.chat(command) -> PortfolioChatAnswerDto` |
| 생성 | `apps/ontology/app/use_cases/portfolio_chat_interactor.py` | 검색→임계값→프롬프트 조립→LLM. 근거 없으면 LLM 호출 없이 고정 답 |
| 생성 | `apps/ontology/adapter/inbound/api/schemas/portfolio_chat_schema.py` | 요청/응답 스키마 |
| 생성 | `apps/ontology/adapter/inbound/api/rate_limit.py` | mova `chat_rate_limit` 복제(Spoke import 금지) |
| 생성 | `apps/ontology/adapter/inbound/api/v1/portfolio_chat_router.py` | `POST /portfolio/chat` |
| 수정 | `apps/ontology/adapter/inbound/api/__init__.py` | `portfolio_router` export |
| 생성 | `apps/ontology/dependencies/portfolio_chat_provider.py` | `get_portfolio_llm_port`(`PORTFOLIO_LLM_BACKEND`) · `get_portfolio_chat_use_case` |
| 수정 | `main.py` | `app.include_router(portfolio_router)` |
| 생성 | `scripts/ingest_portfolio_docs.py` | md 파일 → 청크 → `hub_knowledge(source='portfolio_doc')` upsert, `--reset` |
| 생성 | `datasets/portfolio_corpus/profile.md` | 공개 프로필(이름·학력·경력·기술·프로젝트, 연락처 제외) |
| 수정 | `.env.example` | `PORTFOLIO_LLM_BACKEND` · `PORTFOLIO_LLM_MODEL` 문서화 |
| 테스트 | `core/lol/tests/test_t1_mid_faker_orchestrator_body.py` · `apps/ontology/test/test_portfolio_chat_interactor.py` · `test_portfolio_chat_router.py` · `test_portfolio_llm_backend_switch.py` | |
| 프론트 생성 | `suvis/app/api/portfolio/chat/route.ts` · `suvis/lib/portfolio-api.ts` · `suvis/components/home/portfolio-chat-panel.tsx` | 프록시 · API 클라이언트 · 대화 패널 |
| 프론트 수정 | `suvis/components/home/app-launcher.tsx` | 입력창을 채팅 전송으로, 필터 제거, 패널 배치 |

---

### Task 1: 오케스트레이터 `num_ctx` 옵션

**Files:**
- Modify: `core/lol/t1_mid_faker_orchestrator.py` (`generate`)
- Test: `core/lol/tests/test_t1_mid_faker_orchestrator_body.py`

**Interfaces:**
- Produces: `T1MidFakerOrchestrator._build_body(prompt, *, system, temperature, num_ctx) -> dict[str, object]`, `generate(prompt, *, system=None, temperature=None, num_ctx=None) -> str`

- [ ] **Step 1: 실패 테스트**

```python
"""generate 요청 본문 조립 — num_ctx가 없으면 ollama 기본 4096으로 근거가 잘린다(2026-09-27)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lol.t1_mid_faker_orchestrator import T1MidFakerOrchestrator  # noqa: E402


class BuildBodyTests(unittest.TestCase):
    def test_options_omitted_when_nothing_set(self) -> None:
        body = T1MidFakerOrchestrator(model="m")._build_body("q", system=None, temperature=None, num_ctx=None)
        self.assertNotIn("options", body)
        self.assertEqual(body["messages"], [{"role": "user", "content": "q"}])

    def test_temperature_and_num_ctx_go_to_options(self) -> None:
        body = T1MidFakerOrchestrator(model="m")._build_body("q", system="s", temperature=0, num_ctx=8192)
        self.assertEqual(body["options"], {"temperature": 0, "num_ctx": 8192})
        self.assertEqual(body["messages"][0], {"role": "system", "content": "s"})
```

- [ ] **Step 2: 실행해 실패 확인** — `python -m pytest core/lol/tests/test_t1_mid_faker_orchestrator_body.py -q` → `AttributeError: _build_body`
- [ ] **Step 3: 구현** — `generate`의 본문 조립부를 `_build_body`로 빼고 `num_ctx` 추가:

```python
    def _build_body(
        self, prompt: str, *, system: str | None, temperature: float | None, num_ctx: int | None
    ) -> dict[str, object]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict[str, object] = {
            "model": self._model, "messages": messages, "stream": False, "keep_alive": self._keep_alive,
        }
        options: dict[str, float | int] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if num_ctx is not None:
            options["num_ctx"] = num_ctx   # ollama 기본 4096 — 긴 근거를 넣을 때 명시하지 않으면 앞부분이 잘린다
        if options:
            body["options"] = options
        return body

    def generate(self, prompt, *, system=None, temperature=None, num_ctx: int | None = None) -> str:
        body = self._build_body(prompt, system=system, temperature=temperature, num_ctx=num_ctx)
        ...(기존 HTTP 호출 그대로)
```
- [ ] **Step 4: 통과 확인** — 같은 명령 PASS. 기존 `core/lol/tests` 전체도 PASS.

### Task 2: `ExaoneLlmAdapter` + LLM 백엔드 스위치 + DTO/포트/인터랙터

**Files:**
- Create: `apps/ontology/adapter/outbound/llm/exaone_llm_adapter.py`, `apps/ontology/app/dtos/portfolio_chat_dto.py`, `apps/ontology/app/ports/input/portfolio_chat_use_case.py`, `apps/ontology/app/use_cases/portfolio_chat_interactor.py`, `apps/ontology/dependencies/portfolio_chat_provider.py`
- Test: `apps/ontology/test/test_portfolio_chat_interactor.py`, `apps/ontology/test/test_portfolio_llm_backend_switch.py`

**Interfaces (Produces):**
- `PortfolioChatTurn(role: str, content: str)` · `PortfolioChatCommand(message: str, history: tuple[PortfolioChatTurn, ...])` · `PortfolioChatAnswerDto(reply: str, sources: tuple[str, ...])`
- `PortfolioChatInteractor(*, repository: HubKnowledgePort, embedding: EmbeddingPort, llm: HubLlmPort).chat(command) -> PortfolioChatAnswerDto`
- `get_portfolio_llm_port() -> HubLlmPort` · `get_portfolio_chat_use_case(...) -> PortfolioChatUseCase`

- [ ] **Step 1: 인터랙터 실패 테스트** (`test_portfolio_chat_interactor.py`)

```python
class _FakeLlm(HubLlmPort):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append((prompt, system)); return "  답변  "

def _hit(title, content, score): return HubKnowledgeHitDto(source_ref="portfolio:x#0", title=title, content=content, score=score)
def _interactor(hits, llm): repo=AsyncMock(); repo.search.return_value=hits; emb=AsyncMock(); emb.embed.return_value=[0.1]*1024; return PortfolioChatInteractor(repository=repo, embedding=emb, llm=llm), repo

class PortfolioChatInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_hits_returns_fixed_reply_without_llm(self): ... assertEqual(dto.reply, NO_CONTEXT_REPLY); assertEqual(llm.calls, [])
    async def test_noise_hits_are_filtered_like_movie_search(self): hits score 0.05 → 고정 답, llm 미호출
    async def test_hits_build_grounded_prompt(self): prompt에 청크 content·질문·직전 히스토리 포함, system은 SYSTEM_PROMPT, reply strip, sources 중복 제거·순서 유지
    async def test_history_is_trimmed_to_last_six_turns(self): 8턴 주면 앞 2턴 문구가 prompt에 없음
    async def test_search_uses_portfolio_source(self): repo.search.assert_awaited_once_with(ANY, k=6, source="portfolio_doc")
```

- [ ] **Step 2: 실패 확인** — `ModuleNotFoundError`.
- [ ] **Step 3: 구현** — 인터랙터 핵심:

```python
SOURCE = "portfolio_doc"; TOP_K = 6; MIN_HIT_SCORE = 0.15; MAX_HISTORY_TURNS = 6
NO_CONTEXT_REPLY = ("제가 가진 자료에서는 그 내용을 찾지 못했어요. Mova·Gildle·ARDA 같은 프로젝트나 "
                    "진수택의 경력·기술 스택에 대해 물어봐 주세요.")
SYSTEM_PROMPT = """당신은 개발자 진수택의 포트폴리오 사이트(suvisdev.cloud) 안내 AI입니다.
규칙:
1. [자료]에 있는 내용만 근거로 답합니다. 자료에 없으면 "자료에서 찾지 못했다"고 말하고 지어내지 않습니다.
2. 개인정보는 이름·학력·경력·기술처럼 자료에 공개된 것만 말합니다. 전화번호·이메일·주소·생년월일은 답하지 않고 "사이트의 Contact 페이지를 참고해 달라"고 안내합니다.
3. 한국어 존댓말로 3~5문장 이내로 간결하게 답합니다. 필요하면 짧은 목록을 씁니다.
4. 자료 제목이나 출처를 답에 붙이지 않습니다."""

def build_prompt(hits, history, message) -> str:
    docs = "\n\n".join(f"### {h.title}\n{h.content}" for h in hits)
    turns = "\n".join(f"{'사용자' if t.role == 'user' else 'AI'}: {t.content}" for t in history)
    return f"[자료]\n{docs}\n\n[대화]\n{turns or '(없음)'}\n\n[질문]\n{message}"

async def chat(self, command):
    vector = await self._embedding.embed(command.message)          # HubRagError는 라우터가 처리
    raw = await self._repository.search(vector, k=TOP_K, source=SOURCE)
    hits = [h for h in raw if h.score >= MIN_HIT_SCORE]
    if not hits:
        return PortfolioChatAnswerDto(reply=NO_CONTEXT_REPLY, sources=())
    prompt = build_prompt(hits, command.history[-MAX_HISTORY_TURNS:], command.message)
    reply = await self._llm.generate(prompt, system=SYSTEM_PROMPT)
    return PortfolioChatAnswerDto(reply=reply.strip(), sources=tuple(dict.fromkeys(h.title for h in hits)))
```
  어댑터: `ExaoneLlmAdapter(model=os.getenv("PORTFOLIO_LLM_MODEL","exaone3.5:7.8b"), keep_alive=os.getenv("PORTFOLIO_LLM_KEEP_ALIVE","5m"))`, `generate` → `asyncio.to_thread(orch.generate, prompt, system=system, temperature=0, num_ctx=8192)`, `FakerOrchestratorError`→`HubRagError`(폴백이 걸리려면 필수).
  프로바이더: `PORTFOLIO_LLM_BACKEND`가 `gemini`면 `GeminiLlmAdapter()`, 아니면 `FallbackHubLlmAdapter(primary=ExaoneLlmAdapter(), fallback=GeminiLlmAdapter())`. 매 호출 `os.getenv`(테스트 `patch.dict`).
- [ ] **Step 4: 스위치 테스트** (`test_portfolio_llm_backend_switch.py`) — unset→`FallbackHubLlmAdapter`, `gemini`→`GeminiLlmAdapter`, ` GEMINI `→Gemini, `unknown`→Fallback.
- [ ] **Step 5: 통과 확인** — `python -m pytest apps/ontology/test/test_portfolio_chat_interactor.py apps/ontology/test/test_portfolio_llm_backend_switch.py -q`

### Task 3: 스키마·레이트리밋·라우터·등록

**Files:**
- Create: `.../api/schemas/portfolio_chat_schema.py`, `.../api/rate_limit.py`, `.../api/v1/portfolio_chat_router.py`
- Modify: `apps/ontology/adapter/inbound/api/__init__.py`, `main.py`
- Test: `apps/ontology/test/test_portfolio_chat_router.py`

**Interfaces:** `POST /portfolio/chat` 요청 `{message: str(1..1000), history: [{role:"user"|"assistant", content: str(≤2000)}] ≤10}` → 200 `{reply: str, sources: string[]}`; 422(검증) · 429(IP 20회/60s, `Retry-After`) · HubRagError.status_code(본문은 일반 문구, 원문은 로그).

- [ ] **Step 1: 실패 테스트** — `FastAPI()` + `include_router(portfolio_chat_router, prefix="/portfolio")`, `dependency_overrides[get_portfolio_chat_use_case] = lambda: _FakeUseCase()`; 케이스: 200 shape·`Command.from_schema` 변환(history 튜플), 빈 message 422, history 11개 422, `HubRagError(...,503)` → 503 + detail이 원문이 아닌 일반 문구, 21번째 호출 429(각 테스트는 `cf-connecting-ip` 헤더로 고유 키).
- [ ] **Step 2: 실패 확인** → **Step 3: 구현**: rate_limit.py는 mova 파일을 복사하고 docstring에 "mova 원본 복제 — Spoke↔Hub import 금지(.importlinter Rule 2), ontology `ollama_embedding_adapter.py`와 같은 선택" 명시. 라우터:

```python
@portfolio_chat_router.post("", response_model=PortfolioChatResponseSchema)
async def chat(req, use_case = Depends(get_portfolio_chat_use_case), _rate: None = Depends(chat_rate_limit)):
    try:
        dto = await use_case.chat(PortfolioChatCommand.from_schema(req))
    except HubRagError as e:
        logger.warning("[portfolio/chat] LLM/RAG 실패 | status=%s detail=%s", e.status_code, e.detail)
        raise HTTPException(status_code=e.status_code, detail=GENERIC_ERROR_DETAIL) from e
    return dto.to_schema()
```
  `__init__.py`에 `portfolio_router = APIRouter(prefix="/portfolio", tags=["portfolio"])`; `main.py` import + `app.include_router(portfolio_router)`(prefix 없음 → `/portfolio/chat`, mova 계열).
- [ ] **Step 4: 통과 + 등록 검증** — 라우터 테스트 PASS · `python -c "import main"` · `PYTHONPATH="$PWD:$PWD/apps" lint-imports` · `ruff check` · `mypy`.

### Task 4: 인제스트 스크립트 + 공개 프로필 + `.env.example`

**Files:**
- Create: `scripts/ingest_portfolio_docs.py`, `datasets/portfolio_corpus/profile.md`
- Modify: `.env.example`

**Interfaces:** `python scripts/ingest_portfolio_docs.py <path>... [--reset] [--dry-run] [--embedding-backend ollama|gemini]` — path는 파일 또는 디렉터리(`*.md`, `*.markdown` 재귀). source_ref `portfolio:<파일 stem>#<n>`.

- [ ] **Step 1: 청킹 함수 테스트**(`apps/ontology/test/test_portfolio_chunker.py`는 만들지 않고 스크립트에 `chunk_markdown(text, *, max_chars=1500) -> list[tuple[str, str]]`를 두고 `--dry-run`으로 검증 — 스크립트는 pytest 대상 밖). 동작: YAML front matter 제거, `title:`(없으면 첫 `# `)를 문서 제목으로, `## ` 헤딩 단위 분할, 1500자 초과 시 빈 줄 기준 재분할, 200자 미만 조각은 앞 조각에 합침. 반환 `(제목 — 헤딩, 본문)`.
- [ ] **Step 2: 구현** — `ingest_hub_knowledge.py` 골격(sys.path 부트스트랩·session factory·임베딩 어댑터 선택·`HubRagInteractor.ingest_movie`) 재사용. `--reset`은 `delete(HubKnowledgeOrm).where(source == "portfolio_doc")`. 파일마다 commit, 실패(False) 건수 집계.
- [ ] **Step 3: profile.md 작성** — `suvis/app/resume/_components/resume-content.tsx`의 공개 값(이름 진수택 · Education 타임라인 · Projects · TECH_STACK · GitHub/블로그 링크)을 옮기되 **Phone·Email 제외**. 상단에 "홈 AI 채팅 근거용 공개 프로필 — 연락처는 넣지 않는다" 주석.
- [ ] **Step 4: `--dry-run`으로 청크 수·제목 출력 확인**: `python scripts/ingest_portfolio_docs.py datasets/portfolio_corpus ~/projects/suvisjk/*.markdown ~/projects/suvisjk/_posts --dry-run`
- [ ] **Step 5: `.env.example`** 섹션 추가 후 `python scripts/check_env_drift.py` PASS:

```
# --- 홈 포트폴리오 AI 채팅(/portfolio/chat, 2026-09-27) ---
# 답변 LLM. exaone: 노트북 ollama exaone3.5:7.8b(기본, 실패 시 Gemini 자동 폴백) / gemini: Gemini만.
# 7.8B는 VRAM 5.7GB(num_ctx 8192) — mova lora-server(2.4GB)와 동시 상주 가능하나 2.4B 라우터는 밀려난다.
# mova 지연이 실측되면 PORTFOLIO_LLM_MODEL=exaone3.5:2.4b 또는 PORTFOLIO_LLM_BACKEND=gemini로 전환.
# PORTFOLIO_LLM_BACKEND=exaone
# PORTFOLIO_LLM_MODEL=exaone3.5:7.8b
# PORTFOLIO_LLM_KEEP_ALIVE=5m
# 문서 색인: python scripts/ingest_portfolio_docs.py datasets/portfolio_corpus <지킬 경로들> --reset
```

### Task 5: 프론트 — 프록시·API 클라이언트·대화 패널·입력창 연결

**Files:**
- Create: `suvis/app/api/portfolio/chat/route.ts`, `suvis/lib/portfolio-api.ts`, `suvis/components/home/portfolio-chat-panel.tsx`
- Modify: `suvis/components/home/app-launcher.tsx`

**Interfaces:**
- `route.ts`: `POST` → `backendFetch("/portfolio/chat")` 그대로 전달, 실패 502 `{ detail: BACKEND_DOWN }` (mova 프록시와 동일 형태).
- `lib/portfolio-api.ts`: `export type PortfolioChatTurn = { role: "user" | "assistant"; content: string }`, `export type PortfolioChatResponse = { reply: string; sources: string[] }`, `export async function sendPortfolioChat(message: string, history: PortfolioChatTurn[]): Promise<PortfolioChatResponse>` — 실패 시 `safeApiErrorMessage(detail, "답변을 가져오지 못했어요.", status)` 문구로 `Error` throw.
- `portfolio-chat-panel.tsx`: props `{ messages: PortfolioChatTurn[]; loading: boolean; error: string | null }` — 표시 전용(상태는 launcher가 소유).
- `app-launcher.tsx`: 입력창 제출 → 낙관적 user 메시지 추가 → `sendPortfolioChat(text, 이전 10턴)` → assistant 추가; 실패 시 user 메시지 롤백 + 입력 복원 + error. 앱 필터 제거(격자는 항상 전체). placeholder "무엇이든 물어보세요 — 진수택과 그의 앱에 대해". IME 가드(`isComposing`). 패널은 form과 격자 사이, 메시지가 있을 때만 렌더.

- [ ] **Step 1: 구현** (위 인터페이스대로)
- [ ] **Step 2: `npx pnpm type-check` · `npx pnpm lint` PASS**
- [ ] **Step 3: 로컬 스모크** — `npx next dev -p 3999` + 백엔드 `python main.py`(또는 NodePort로 `BACKEND_URL=http://127.0.0.1:31386`)로 질문 1건 왕복 확인.

### Task 6: 색인·배포·검증·기록

- [ ] **Step 1: 백엔드 배포** — 노트북에서 `./k8s/deploy.sh --external-db --build`, `kubectl -n suvisdev rollout status deploy/backend`, `printenv | grep PORTFOLIO`(미설정=기본 exaone).
- [ ] **Step 2: 색인** — 노트북 호스트에서 `.env`의 DB로 `python scripts/ingest_portfolio_docs.py datasets/portfolio_corpus ~/projects/suvisjk/about.markdown ~/projects/suvisjk/overview.markdown ~/projects/suvisjk/mova.markdown ~/projects/suvisjk/gildle.markdown ~/projects/suvisjk/devlog.markdown ~/projects/suvisjk/_posts --reset`. 호스트에서 DB에 못 붙으면 `kubectl cp`로 파드에 넣고 `kubectl exec`.
- [ ] **Step 3: 운영 스모크** — `curl -X POST http://127.0.0.1:31386/portfolio/chat -d '{"message":"진수택이 만든 앱이 뭐야?"}'` → 200·근거 있는 답. 연락처 질문("전화번호 알려줘") → Contact 안내. 무관 질문("오늘 날씨") → 고정 답. 응답 시간 기록. `eval_chat_queries.py` 23질의 재실행으로 mova 회귀 없음 확인.
- [ ] **Step 4: 프론트 배포** — 커밋·푸시 → Vercel, `https://suvisdev.cloud`에서 왕복 1건.
- [ ] **Step 5: 기록** — `_docs/WORK_LOG_MAINPAGE.md` 09-27, `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`, `INTERVIEW_QUESTIONS.md`, 메모리 갱신. 커밋 3개: `feat(ontology): 포트폴리오 문서 RAG 채팅`, `feat(suvis): 홈 입력창 AI 채팅 패널`, `docs:`.

---

## Self-Review
- 스펙 커버리지: 로컬 EXAONE(T2 어댑터·T4 env) · 공개 자료만(T4 profile·색인 대상 명시) · 개인정보 선(T2 SYSTEM_PROMPT 규칙 2 + profile에 연락처 미포함 이중 방어) · 누구나+IP 제한(T3 rate_limit, 인증 의존성 없음) · 파인튜닝 없음 · 모델 전환 가능(T2 프로바이더) — 모두 태스크에 대응.
- 타입 일관성: `PortfolioChatTurn`/`PortfolioChatCommand`/`PortfolioChatAnswerDto`/`get_portfolio_chat_use_case`/`sendPortfolioChat`/`PortfolioChatResponse` 명칭을 T2~T5에서 동일하게 사용.
- 미결·후속(YAGNI로 제외): 스트리밍 응답, 후속 질문의 검색어에 이전 턴 결합, Redis 분산 레이트리밋, 대화 저장.
