# A2A 멀티 에이전트 프로젝트 — pyproject.toml 하네스 스펙

> Claude Code용 실행 지침서. 실제로 스캐폴드를 만들 때는 이 문서를 그대로 따른다.
> **2026-07-20 확정본** — 초안(a2a-portfolio, uv workspace 방식)은 폐기하고 아래 최종 스펙으로 대체함.

---

## 0. 사전 확인 (필수)

작업 시작 전 아래를 먼저 확인하고, 이 문서와 실제 상태가 다르면 **실제 값을 우선**한다.

1. **디렉토리 구조 확인**: `ls` / `tree -L 2`로 `a2a-mcp/`가 이미 있는지 확인. 없으면 §2 구조대로 신규 생성.
2. **Python 버전 확인**: `python3 --version`. `requires-python = ">=3.11"` 가정 — 서버에 3.10만 있으면 낮추되 사용자에게 보고.
3. **uv 설치 여부**: `uv --version`. 없으면 설치를 먼저 제안하고 승인 후 진행.
4. **기존 파일 존재 여부**: 이미 `a2a-mcp/`가 있으면 덮어쓰지 말고 diff를 보여준 뒤 병합.
5. **생성 위치**: `cloud.suvisdev` 워크스페이스 루트(`suvisdev/`, `suvis/`, `susu/`, `_docs/`와 형제)에
   `a2a-mcp/`를 새로 만든다. **기존 suvisdev 저장소의 헥사고날/스타-토폴로지 코드는 옮기거나
   건드리지 않는다** — 이 프로젝트는 별도 독립 패키지 트리다.

### 0-1. 하드웨어/사양 확인 및 대체 (필수 — §1 "아키텍처 전제"의 수치는 전부 예시임)

**§1의 "RTX 3050 6GB", "t4g.micro" 등은 어느 한 컴퓨터의 예시 값일 뿐이다. 이 문서를 실제로
실행하는 컴퓨터는 사양이 다를 수 있으므로, 아래를 실측해서 §1과 모델 선택을 그 값으로
대체한다 — 절대 문서에 적힌 숫자를 그대로 믿고 진행하지 않는다.**

| 항목 | 확인 명령 | 확인되면 할 일 |
|------|-----------|----------------|
| GPU VRAM 총량 | `nvidia-smi --query-gpu=memory.total --format=csv` (WSL2면 PATH에 없을 수 있음 → `/usr/lib/wsl/lib/nvidia-smi`도 시도) | §1의 GPU 사양 문구를 실측값으로 교체. GPU가 없으면 온프레미스 에이전트는 Ollama CPU 모드이거나 아예 클라우드 추론으로 전환해야 함 — 사용자에게 확인 |
| GPU 여유(유휴 시) | `nvidia-smi --query-gpu=memory.used,memory.total --format=csv` | 다른 프로세스가 이미 VRAM을 점유하고 있으면(Ollama 상주 모델 등) 그만큼 빼고 계산 |
| Python 버전 | `python3 --version` | §0-2와 동일하게 처리 |
| uv 버전 | `uv --version` | 없으면 설치 제안 |
| AWS 배포 대상 | 사용자에게 직접 질문 | `t4g.micro`는 예시. 실제로 Lambda면 콜드스타트/패키지 크기 제약이 더 빡빡해지므로 §6 의존성 최소화 원칙을 더 엄격히 적용 |

**모델 크기 선택 기준(실측 VRAM 기반)** — 어떤 모델을 Ollama로 올릴지는 실측 여유에 맞춰
정한다. 참고로 이 저장소(suvisdev)의 실제 프로덕션 서빙에서 측정한 값:
- EXAONE-3.5-2.4B-Instruct-AWQ: 로드+서빙 시 전체 프로세스 VRAM 사용량 약 **2.6GB**
  (`_docs/EXAONE_LOCAL_AI_SETUP.md`, 2026-07-20 실측)
- Qwen2.5-1.5B-Instruct(fp16): 로드+LoRA 시 약 **3.09GB**

즉 GPU 여유가 4GB 미만이면 2.4B~1.5B급 모델 하나만, 6~8GB면 두 모델을 순차 언로드
(Router→Worker 방식, `core/lol/model_switch_guard.py` 참고)하는 전략이 필요하다. §1에
적힌 "Qwen2.5 3B"도 예시 선택일 뿐 — 실측 여유가 부족하면 더 작은 모델(1.5B 등)로,
넉넉하면 더 큰 모델로 사용자와 상의해 바꾼다.

---

## 1. 목적

3개 에이전트(온프레미스 EXAONE, 온프레미스 Qwen, AWS 라우터)로 구성된 A2A-over-MCP 포트폴리오
프로젝트의 파이썬 패키징 구조를 생성한다. 패키지 관리자는 uv.

## 아키텍처 전제

> ⚠️ 아래 GPU·인스턴스 사양은 **예시**다. 실제로 실행할 때는 반드시 §0-1을 먼저 실행해
> 실측값으로 교체한 뒤 진행한다.

- **온프레미스 우분투 서버 (예시: RTX 3050 6GB — §0-1로 실측 후 교체)**: EXAONE 3.5 2.4B,
  Qwen2.5 3B를 Ollama로 구동(모델 크기도 §0-1 기준으로 조정). 그래프 DB(Neo4j) 동거.
- **AWS (예시: t4g.micro 또는 Lambda — 실제 배포 대상은 사용자에게 확인)**: LLM 없는
  오케스트레이터/라우터 에이전트. 온프레미스와 Cloudflare Tunnel/Tailscale 경유 통신.
- 각 에이전트는 MCP 서버로 노출되며, 상대 에이전트를 MCP 클라이언트로 호출한다 (A2A over MCP).
- 그래프 DB는 온프레미스 에이전트만 직접 접근한다. AWS 라우터는 MCP 경유로만 데이터에 접근한다.
- 결과물은 Vercel 프론트엔드로 전달된다 (온프레미스 FastAPI → Vercel fetch).

---

## 2. 디렉터리 구조 (생성 대상)

```
a2a-mcp/
├── shared/
│   ├── pyproject.toml
│   └── src/
│       └── a2a_shared/
│           ├── __init__.py
│           └── schemas.py          # A2A 메시지 스키마 (pydantic)
├── agents/
│   ├── exaone/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── agent_exaone/
│   │           └── __init__.py
│   ├── qwen/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── agent_qwen/
│   │           └── __init__.py
│   └── aws_router/
│       ├── pyproject.toml
│       └── src/
│           └── agent_aws_router/
│               └── __init__.py
└── README.md
```

**주의**: uv workspace를 사용하지 않는다. 배포 대상이 물리적으로 분리되어 있으므로(우분투
서버 vs AWS), 각 에이전트 디렉터리가 독립적인 `uv sync` 단위가 된다. `a2a-shared`는 각
에이전트에서 `path`+`editable` 로컬 의존성으로 참조한다 — 스키마 변경은 반드시 `shared/`에서만
한다. 에이전트 개별 디렉터리에 스키마를 복제하지 않는다.

---

## 3. 파일 1 — `shared/pyproject.toml`

```toml
[project]
name = "a2a-shared"
version = "0.1.0"
description = "A2A 메시지 스키마 및 공통 타입 (에이전트 간 단일 소스)"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/a2a_shared"]
```

---

## 4. 파일 2 — `agents/exaone/pyproject.toml`

```toml
[project]
name = "agent-exaone"
version = "0.1.0"
description = "온프레미스 주 추론 에이전트 (EXAONE 3.5 2.4B via Ollama)"
requires-python = ">=3.11"
dependencies = [
    "a2a-shared",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "ollama>=0.3",
    "neo4j>=5.20",
    "mcp>=1.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
    "mypy>=1.10",
]

[tool.uv.sources]
a2a-shared = { path = "../../shared", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agent_exaone"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
strict = true
```

---

## 5. 파일 3 — `agents/qwen/pyproject.toml`

파일 2(`agent-exaone`)와 동일한 구조. 아래 항목만 다르다:

- `[project] name = "agent-qwen"`
- `description = "온프레미스 보조 에이전트 (Qwen2.5 3B via Ollama)"`
- `[tool.hatch.build.targets.wheel] packages = ["src/agent_qwen"]`

나머지(`dependencies`, `dependency-groups`, `tool.uv.sources`, `build-system`, `tool.ruff`,
`tool.mypy`)는 파일 2와 완전히 동일하게 복제한다.

---

## 6. 파일 4 — `agents/aws_router/pyproject.toml`

**LLM·GPU·그래프 DB 의존성을 절대 포함하지 않는다** (`ollama`, `neo4j` 금지). t4g.micro
메모리와 콜드스타트를 위해 최소 의존성을 유지한다.

```toml
[project]
name = "agent-aws-router"
version = "0.1.0"
description = "AWS 오케스트레이터/라우터 에이전트 (LLM 없음, MCP 경유 위임)"
requires-python = ">=3.11"
dependencies = [
    "a2a-shared",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "mcp>=1.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
    "mypy>=1.10",
]

[tool.uv.sources]
a2a-shared = { path = "../../shared", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agent_aws_router"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
strict = true
```

**대응되는 기존 코드 없음** — suvisdev 저장소에 AWS/Lambda 라우팅 대응 코드가 없으므로
이 패키지는 완전히 신규로 작성해야 한다(2026-07-20 확인).

---

## 7. 파일 5 — `shared/src/a2a_shared/schemas.py` (최소 골격)

```python
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AgentName(StrEnum):
    EXAONE = "exaone"
    QWEN = "qwen"
    AWS_ROUTER = "aws_router"


class A2AMessage(BaseModel):
    """에이전트 간 표준 메시지. 모든 A2A 호출은 이 스키마를 사용한다."""

    sender: AgentName
    receiver: AgentName
    task: str
    payload: dict = Field(default_factory=dict)
    trace_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class A2AResult(BaseModel):
    trace_id: str
    responder: AgentName
    success: bool
    output: dict = Field(default_factory=dict)
    error: str | None = None
```

---

## 8. 실행 지침 (클로드코드용)

1. §2 디렉터리 구조를 생성한다. 각 `__init__.py`는 빈 파일로 둔다.
2. 파일 1~5를 명시된 경로에 작성한다. 파일 3은 파일 2를 기반으로 §5에 명시된 차이점만 반영한다.
3. 각 에이전트 디렉터리에서 `uv sync` 실행이 성공하는지 검증한다:
   ```bash
   cd shared && uv sync && cd ..
   cd agents/exaone && uv sync && cd ../..
   cd agents/qwen && uv sync && cd ../..
   cd agents/aws_router && uv sync && cd ../..
   ```
4. 각 에이전트 환경에서 공통 스키마 import를 검증한다:
   ```bash
   cd agents/exaone && uv run python -c "from a2a_shared.schemas import A2AMessage; print('ok')"
   # qwen, aws_router도 동일하게 반복
   ```
5. `aws_router` 환경에 `ollama`, `neo4j`가 설치되지 않았음을 확인한다:
   ```bash
   cd agents/aws_router && uv pip list | grep -E "ollama|neo4j" && echo "FAIL: 금지 의존성 발견" || echo "ok"
   ```

**2026-07-20 검증 이력**: 위 1~5단계를 실제로 실행해 전부 통과 확인함(`uv sync` 4회 성공,
스키마 import 3개 전부 `ok`, aws_router 금지 의존성 없음 확인). 다만 사용자가 "지금은 코드
스캐폴드가 아니라 문서만 원함"이라고 정정해서, 실제로 생성했던 `a2a-mcp/` 디렉터리는 검증
직후 삭제했다 — **디스크에는 없고 이 문서만 남아있는 상태**. 다음에 실제로 만들어달라고 하면
이 문서 그대로 따라 재생성하면 된다(재현 확인된 스펙).

---

## 9. 제약 사항

- 파이썬 버전은 3.11 고정 (`requires-python = ">=3.11"`). 서버와 AWS 인스턴스 간 버전 일치
  확인 필요.
- `a2a-shared`는 editable 로컬 경로 의존성이다. 배포 시 각 서버에 `shared/` 디렉터리가
  함께 복사되어야 한다 (git clone 단위가 모노레포 전체이므로 충족됨).
- 버전 상한(`<`)은 지정하지 않는다. 잠금은 `uv.lock`이 담당한다.
- 스키마 변경은 반드시 `shared/`에서만 한다. 에이전트 개별 디렉터리에 스키마를 복제하지 않는다.

## 10. 하지 말 것

- 기존 suvisdev 저장소의 헥사고날/스타-토폴로지 코드를 이 구조로 옮기거나 재배치하지 않는다
  (2026-07-20 사용자 확인: 지금은 구조 설계·문서화 단계, 코드 이동 없음).
- `requirements.txt` 별도 생성 (uv로 일원화).
- `agent-aws-router`에 `ollama`, `neo4j` 등 LLM·GPU·그래프 DB 의존성 추가.
- 사용자 확인 없이 Python 버전·디렉토리 구조 임의 변경.
- 사용자가 명시적으로 "만들어줘/스캐폴드해줘"라고 하기 전까지는 이 문서 내용을 실제
  파일·디렉터리로 생성하지 않는다 — 이 문서 자체는 참고용 스펙이다.
