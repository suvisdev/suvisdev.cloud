# EXAONE 로컬 소버린 AI 환경 구성 (Router/Worker)

> 이 문서 하나만 보고 새 PC(WSL2 + NVIDIA GPU)에서 그대로 재현할 수 있도록 작성함.
> sudo 없이 설치 가능한 방법만 사용한다 (WSL Docker Desktop 통합이 꺼져있어도 무관).

> **⚠️ 8장 lora-server 서빙 서술은 2026-08-19 기준으로 구식.** 이후
> 09-01 데스크톱 이전 + EXAONE-3.5-2.4B fp16 재구축, 09-02 **llama.cpp
> GGUF 전환**(`serve_gguf.py`, 재학습 후 `export_mova_gguf.py` 필수)으로
> 서빙 경로가 바뀜(구 `serve.py`는 롤백용 보존). 최신 상태는 루트
> `CLAUDE.md` "주의사항"과 `WORK_LOG_MOVA.md` 09-01·09-02 참고.
> Router/Worker(Ollama)·AWQ 설치 절차 자체는 여전히 유효.

## 0. 아키텍처 개요

- **Router model**: `exaone3.5:7.8b` — 라우팅/판단
- **Worker model**: `exaone3.5:2.4b` — 실행
- 8GB급 GPU(RTX 3050 등) 기준, **Router와 Worker를 동시에 GPU에 상주시키지 않는다** — 순차 호출
- Router/Worker 운영 경로는 Ollama(GGUF) 기반이 정답. vLLM은 이 스택에서 막혀서 폐기함(7번 참고)
- AWQ(`transformers`+`gptqmodel`)는 Router/Worker와는 별개로, RAG 서빙용 체크포인트 직접 로드
  경로로 `~/.venv-exaone`에서 성공시킴 — 7번 참고
- 코드: `suvisdev/core/lol/model_switch_guard.py`(순차 언로드 폴링) + `router_worker_pipeline.py`(조립) — 이 리포를 clone하면 같이 따라옴

## 1. 사전 확인

```bash
# WSL인지 확인
systemd-detect-virt   # "wsl"이 나오면 WSL2

# GPU 확인 — 일반 PATH에 nvidia-smi가 없으면 아래 경로 시도
nvidia-smi || /usr/lib/wsl/lib/nvidia-smi
```

`nvidia-smi: command not found`가 떠도 GPU가 없다고 단정하지 말 것 — WSL2는 GPU 패스스루 바이너리가
`/usr/lib/wsl/lib/`에 있고 일반 PATH에는 없는 경우가 흔하다.

## 2. uv 설치 (sudo 불필요)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# ~/.local/bin에 설치됨. 새 셸에서 자동으로 PATH에 잡힘 (.bashrc가 이미 export 해준다면)
export PATH="$HOME/.local/bin:$PATH"
```

## 3. Ollama 포터블 설치 (sudo 불필요)

공식 설치 스크립트(`curl https://ollama.com/install.sh | sh`)는 systemd 시스템 서비스를 sudo로
설치하려고 해서 쓰지 않는다. 대신 압축 바이너리를 홈 디렉터리에 직접 푼다.

```bash
mkdir -p ~/ollama
# 최신 릴리스 URL 확인 (tar.zst 형식)
curl -s https://api.github.com/repos/ollama/ollama/releases/latest \
  | grep -o '"browser_download_url": *"[^"]*ollama-linux-amd64\.tar\.zst"' \
  | cut -d'"' -f4

# 위에서 나온 URL로 다운로드
curl -L --progress-bar <URL> -o /tmp/ollama.tar.zst

# tar에 --zstd 옵션이 있어도 시스템에 zstd 바이너리가 없으면 실패한다.
# 그럴 땐 uv로 python zstandard를 깔아서 압축 해제:
uv venv ~/.venv-unzip --python 3.12
source ~/.venv-unzip/bin/activate
uv pip install zstandard
python3 -c "
import zstandard, tarfile
with open('/tmp/ollama.tar.zst', 'rb') as f:
    with zstandard.ZstdDecompressor().stream_reader(f) as reader:
        with tarfile.open(fileobj=reader, mode='r|') as tf:
            tf.extractall('$HOME/ollama', filter='data')
"
deactivate
chmod +x ~/ollama/bin/ollama
```

## 4. Ollama 서버 기동 + 모델 pull

```bash
export PATH="$HOME/ollama/bin:$PATH"

# 잠깐 수동으로 띄워서 모델부터 받는다 (5번에서 서비스로 전환)
nohup ollama serve > /tmp/ollama-serve.log 2>&1 &
disown
sleep 2

ollama pull exaone3.5:7.8b
ollama pull exaone3.5:2.4b
ollama list   # 둘 다 나오는지 확인
```

## 5. systemd 유저 서비스로 등록 (재부팅/재로그인에도 자동 기동)

```bash
pkill -f "ollama serve"   # 4번에서 수동으로 띄운 거 정리

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/ollama.service << 'EOF'
[Unit]
Description=Ollama (portable, no-sudo)

[Service]
ExecStart=%h/ollama/bin/ollama serve
Environment=PATH=%h/ollama/bin:/usr/bin:/bin
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now ollama.service
loginctl enable-linger   # 로그인 세션 없어도 계속 돌게. 아래 "알려진 문제" 참고
```

**알려진 문제**: `loginctl enable-linger`가 일부 WSL 인스턴스에서 `Could not enable linger:
No such device or address`로 실패할 수 있다 (원인 미확인, SSH로 붙는 서버에서는 성공했는데 로컬
WSL 터미널에서는 실패한 사례 있음). 이 경우 `systemctl --user enable`은 됐으니 서비스 자체는
정상 등록·기동되지만, 세션이 완전히 끊기면 같이 죽을 수 있다. 안전망으로 `.bashrc`에 아래를
추가해두면 새 셸을 열 때마다 죽어있으면 다시 살린다:

```bash
# ~/.bashrc 끝에 추가
export PATH="$HOME/ollama/bin:$PATH"
if [ -x "$HOME/ollama/start-ollama.sh" ]; then
    ( "$HOME/ollama/start-ollama.sh" & disown ) >/dev/null 2>&1
fi
```

```bash
# ~/ollama/start-ollama.sh (멱등 — 이미 떠 있으면 아무것도 안 함)
cat > ~/ollama/start-ollama.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
if curl -fsS --max-time 1 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    exit 0
fi
nohup "$HOME/ollama/bin/ollama" serve > "$HOME/ollama/ollama-serve.log" 2>&1 &
disown
EOF
chmod +x ~/ollama/start-ollama.sh
```

## 6. 검증

```bash
curl -s http://localhost:11434/api/version

# Router→Worker 순차 호출 + VRAM 동시 상주 안 하는지 확인
curl -s http://localhost:11434/api/generate -d '{
  "model": "exaone3.5:7.8b", "prompt": "테스트", "stream": false, "keep_alive": 0
}' | python3 -c "import json,sys; print(json.load(sys.stdin)['response'])"

sleep 3   # keep_alive:0이어도 실제 언로드까지 몇 초 걸림
curl -s http://localhost:11434/api/ps   # {"models":[]} 여야 함

nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

이 리포(`suvisdev`)를 clone했다면 `core/lol/router_worker_pipeline.py`로 실제 코드 레벨 테스트도 가능:

```bash
cd suvisdev
python3 -c "
import sys; sys.path.insert(0, '.')
from core.lol.router_worker_pipeline import RouterWorkerPipeline
p = RouterWorkerPipeline()
r, w = p.route_then_run('한 단어로 답해: 테스트', '한 단어로 답해: 테스트')
print('Router:', r.strip())
print('Worker:', w.strip())
"
```
(`httpx`가 필요하다 — `uv venv ~/.venv && source ~/.venv/bin/activate && uv pip install httpx`)

## 7. AWQ 직접 서빙 경로 (RAG용 별도 환경)

> 2026-07-14 재시도에서 성공함 — 이전에 "폐기"로 적어뒀던 결론은 sudo 접근이 없다는 잘못된 전제
> 때문이었다. 이 머신은 실제로 sudo가 되므로, 빌드 도구만 깔면 `gptqmodel`이 정상 빌드/동작한다.
> **주의**: 이 경로는 위 0~6번(Ollama, no-sudo)과 별개의 목적(RAG 서빙용 원본 체크포인트 직접 로드)이다.
> Router/Worker 운영 경로를 이걸로 바꾸는 게 아니다 — `~/.venv-exaone` 전용 가상환경에만 격리한다.

**환경:**

- 전용 venv: `~/.venv-exaone` (`uv venv --python 3.12`로 생성, 메인 `suvisdev` venv와 완전히 분리)
- 패키지: `transformers==5.13.1`, `torch==2.13.0+cu126`, `gptqmodel==7.1.0` (uv로 PyPI에서 설치, 소스 빌드됨)
- 빌드 사전 준비 (sudo 필요 — 이 머신엔 sudo 권한이 있어서 가능했음):
  ```bash
  sudo apt update && sudo apt install -y build-essential cmake
  sudo apt install -y nvidia-cuda-toolkit
  ```
- 모델 체크포인트: `hf download LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct-AWQ --local-dir EXAONE-3.5-7.8B-Instruct-AWQ`
  (`/home/a/projects/suvis/EXAONE-3.5-7.8B-Instruct-AWQ`, 약 5.3GB, config상 4bit AWQ/group_size=128)
- `autoawq`는 여전히 설치 안 함(deprecated) — `transformers` 5.x가 AWQ 체크포인트를 로드할 때
  자동으로 `gptqmodel`을 백엔드로 선택한다 (`AwqMarlinLinear` 커널).

**로드 테스트:**

```bash
source ~/.venv-exaone/bin/activate
python -u -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
path = '/home/a/projects/suvis/EXAONE-3.5-7.8B-Instruct-AWQ'
tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True, device_map='cuda:0')
inputs = tok('안녕하세요, 오늘 날씨 어때요?', return_tensors='pt').to(model.device)
print(tok.decode(model.generate(**inputs, max_new_tokens=20)[0], skip_special_tokens=True))
"
```

가중치 로드까지는 8GB VRAM에서 정상 확인됨(약 6.2GB 사용). **첫 실행 시 Marlin fp16 커널을
JIT 컴파일**하는데(`~/.cache/gptqmodel/torch_extensions/`에 캐시됨) 예상보다 훨씬 오래 걸릴 수 있다
(견적 ~117초라고 뜨지만 실제로는 그 이상 소요된 사례 있음) — 멈춘 게 아니라 최초 1회만 그렇다.

- **vLLM**: `torch==2.11.0` 등 정확한 버전 재설치 필요, 수 GB 다운로드. 단일 GPU 순차 호출
  구조엔 이득이 없어서 중단함 (이 결론은 유지).

### 7-1. RAG 서빙 서버 기동 (mova 챗봇 연동, 2026-07-14~)

`model_servers/awq_server/serve.py`(저장소 루트) — Ollama와 동일하게 호스트에서 별도 프로세스로 상주시키고,
suvisdev 백엔드는 `core/lol/awq_exaone_orchestrator.py`(HTTP client)로 호출한다.

```bash
source ~/.venv-exaone/bin/activate
uv pip install fastapi "uvicorn[standard]"   # 최초 1회 (transformers/torch/gptqmodel은 이미 설치돼 있음)
cd /home/a/projects/suvis
uvicorn model_servers.awq_server.serve:app --host 0.0.0.0 --port 8100
```

- `GET /health`, `POST /generate {"prompt": "...", "system": "..."}` 로 검증.
- 기동 시 모델을 1회 로드해 상주시킨다 — 첫 `/generate` 요청은 위 Marlin JIT 컴파일 때문에 오래 걸릴 수 있음.
- suvisdev backend(docker-compose)는 `AWQ_SERVER_URL=http://host.docker.internal:8100`로 접근한다
  (`docker-compose.yaml`의 `OLLAMA_BASE_URL`과 동일 패턴).
- **주의**: Ollama Router/Worker(exaone3.5:7.8b/2.4b)와 이 AWQ 서버가 동시에 GPU에 상주하면
  RTX 3050 8GB에서 VRAM이 부족할 수 있다 — 다른 앱(soccer_chat 등)이 Ollama를 쓰는 동안 mova RAG
  채팅도 함께 호출되는 시나리오는 실측 필요.

### 7-2. PEFT/QLoRA (AWQ 체크포인트 위에서 LoRA 학습, 2026-07-15~)

`~/.venv-exaone`에 `peft`, `optimum`을 추가해 이 AWQ 체크포인트 위에서 LoRA 학습이 되는 것까지
실측 확인함(1 옵티마이저 스텝 후 loss 10.06 → 8.28 하락 확인). 아래 3가지를 갖춰야 재현된다 —
하나라도 빠지면 각기 다른 지점에서 막힌다.

**설치:**
```bash
source ~/.venv-exaone/bin/activate
uv pip install peft optimum   # optimum>=1.24.0 — peft가 gptqmodel 백엔드를 인식하는 데 필요
```

**패치 1 — `EXAONE-3.5-7.8B-Instruct-AWQ/modeling_exaone.py`(리포에 커밋됨, 자동으로 따라옴):**
`ExaoneModel`에 `_input_embed_layer = "wte"` 클래스 속성 추가. transformers 5.13.1의
`EmbeddingAccessMixin`이 기본으로 `embed_tokens`라는 이름만 찾는데 EXAONE은 `wte`를 쓴다
(`get_peft_model()`이 `get_input_embeddings()`를 호출하면서 걸림 — `NotImplementedError`).

**패치 2 — `gptqmodel` site-packages 직접 수정 (venv 재생성 시 사라짐, 매번 재적용 필요):**
`nn_modules/qlinear/torch_awq.py`의 `AwqTorchLinear.forward()`에서
`weight = dequantize_gemm(...)` 호출을 `with torch.no_grad():`로 감싼다. 이게 없으면 이 자체는
문제 없어 보여도(그래도 위생상 필요), 아래 gradient checkpointing과 같이 안 하면 결국 OOM.

**패치 3 — 학습 스크립트 상단에 매번 넣어야 하는 런타임 셔임:**
```python
import gptqmodel.nn_modules.qlinear.gemm_awq as gemm_awq
gemm_awq.AwqGEMMQuantLinear = gemm_awq.AwqGEMMLinear
```
`peft==0.19.1`(released, main 브랜치도 동일)이 `gptqmodel`의 옛 클래스명(`AwqGEMMQuantLinear`)을
참조하는데 `gptqmodel==7.1.0`은 `AwqGEMMLinear`로 이름이 바뀌어 있음 — peft 쪽 미수정 버그.

**학습 스크립트에 반드시 필요한 것 (없으면 8GB VRAM에서 100% OOM):**
```python
base.enable_input_require_grads()
peft_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
# forward 호출 시 use_cache=False 필수
```
gradient checkpointing 없이는 32개 레이어의 역양자화된 fp16 가중치를 forward~backward 내내
전부 동시에 들고 있어야 해서(사실상 전체 모델 크기만큼) 8GB에서 무조건 터진다. 켜면 baseline
278MiB 수준까지 내려가며 정상 동작.

LoRA 초기화는 표준대로 `B=0`이라 **1스텝째는 `lora_A` 그래디언트가 0인 게 정상** (`lora_B`부터
그래디언트가 잡히고, 2스텝째부터 `lora_A`도 non-zero가 됨) — 버그 아님.

target_modules: `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj` (EXAONE도
Llama류 명명 규칙을 따름).

## 8. mova 채팅 자동 QLoRA 재학습 파이프라인 (2026-07-15~)

사용자가 채팅으로 영화를 고를수록(picks) 그 취향이 추천에 점점 반영되도록, DB에 쌓인
대화 기록으로 공용 LoRA 어댑터를 주기 재학습하는 파이프라인. **실측으로 개인화 확인됨**
— user_id 있는 사용자(과거 픽 이력=공포/스릴러)에게 "영화 하나 추천해줘"(장르 언급 없음)라고
물으면 실제로 공포 계열로 추천이 쏠리고, 익명 사용자는 전혀 다른 결과를 받음.

### 8-1. 왜 EXAONE-AWQ가 아니라 Qwen2.5-1.5B로 학습·서빙하는가

7-2에서 EXAONE-AWQ 학습 성공(loss 10.06→7.52)까지 확인했었지만, 같은 세션 후반부에
**똑같은 레시피로 재현 가능한 OOM**이 남(모델+LoRA 로드만으로 이미 5.34GB를 써서, 학습 중
레이어 하나 역양자화에 필요한 448MB조차 못 넣음). AWQ 자체가 학습이 안 되는 게 아니라
**8GB GPU에서 7.8B를 학습하기엔 여유가 너무 빠듯한 것** — WSL GPU 메모리가 이 세션 내내
프로세스를 계속 띄우고 내리며 파편화된 것으로 추정.

Qwen2.5-1.5B-Instruct(원본 fp16, AWQ 아님)는 모델+LoRA 로드에 3.09GB만 써서 여유가
훨씬 크고, gptqmodel/AWQ 커널 복잡도 자체가 필요 없어 학습·서빙 둘 다 훨씬 단순하다.
**나중에 VRAM 여유가 생기면 설정만 바꿔서 EXAONE으로 되돌릴 수 있도록**, 아래 스크립트들은
전부 `MOVA_TRAIN_BACKEND`(`plain`|`awq_gptqmodel`) + `MOVA_TRAIN_BASE_MODEL` 환경변수로
백엔드·모델 경로를 분리해뒀다.

### 8-2. 파이프라인 3단계

```text
[1] scripts/export_chat_training_dataset.py   DB(chat+picks+users) → JSONL (prompt, completion)
              │
              ▼
[2] scripts/train_mova_lora.py                LoRA 재학습 → ~/lora_adapters/mova_<timestamp>/
              │                                             + ~/lora_adapters/LATEST 갱신
              ▼
[3] model_servers/lora_server/serve.py (systemd, :8200)      LATEST 어댑터 서빙, POST /reload로 무중단 교체
```

**[1] 데이터 추출** — `chat` 테이블엔 실제 답변 텍스트(intro)가 저장 안 되고 `picks`만
영속화되므로, intro는 합성한다(`취향에 맞는 작품 N편을 골라봤어요: ...`). picks가 있는
대화만 학습 예시로 씀. user_id가 있으면 `ChatPgRepository.get_recent_intents_by_user`로
**그 chat보다 이전 것만** past_intents로 포함해 미래 데이터 유출을 막는다. 프롬프트는
프로덕션과 동일한 `ChatPromptBuilder`로 재구성(HubRagInteractor로 RAG 컨텍스트도 실제로
다시 검색함) — 학습·서빙 프롬프트가 어긋나지 않게.

```bash
# 컨테이너 안에서 실행 (DB·Ollama 임베딩에 접근 가능해야 함)
docker exec -w /suvisdev suvisdev-backend-1 python scripts/export_chat_training_dataset.py
```

**[2] 재학습** — 위 JSONL을 읽어 `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`에
LoRA(r=16, alpha=32) 부착, prompt 토큰은 `label=-100`으로 마스킹해 completion에만 loss
계산. 버전 태깅된 디렉터리에 저장하고 `LATEST` 파일(어댑터 경로/백엔드/베이스모델 3줄)을 갱신.

```bash
source ~/.venv-exaone/bin/activate
cd suvisdev
python scripts/train_mova_lora.py --epochs 3
# VRAM 여유 생기면:
# MOVA_TRAIN_BACKEND=awq_gptqmodel MOVA_TRAIN_BASE_MODEL=../EXAONE-3.5-7.8B-Instruct-AWQ \
#   python scripts/train_mova_lora.py --epochs 3
```

**[3] 서빙** — `model_servers/lora_server/serve.py`가 기동 시 `LATEST`를 읽어 베이스 모델 + 어댑터를
로드. systemd 유저 서비스로 등록(`lora-server.service`, Ollama/awq-server와 동일 패턴).
재학습 후에는 프로세스 재시작 없이 `POST /reload`로 최신 어댑터만 다시 읽어 교체.

```bash
curl http://localhost:8200/health   # {"model_loaded":true,"adapter_dir":"...","backend":"plain"}
curl -X POST http://localhost:8200/reload
```

`mova/adapter/outbound/llm/lora_recommendation_adapter.py`(`LoraRecommendationAdapter`)가
`RecommendationPort` 구현체로 `market_chat_provider.py`에 연결돼 있다 —
`ExaoneRecommendationAdapter`/`QwenRecommendationAdapter`/`OllamaExaoneRecommendationAdapter`와
정확히 같은 자리(`get_recommendation_port()`)를 교체하는 구조라, 나중에 다른 백엔드로
되돌리는 것도 그 함수 한 줄만 바꾸면 된다.

### 8-3. 겪은 이슈

- **peft AWQ 디스패처 셔임은 `plain` 백엔드에서도 필요하다**: peft의 LoRA 디스패처가
  실제 모델 종류와 무관하게 AWQ 체커부터 항상 먼저 시도하기 때문에, `gptqmodel`의 옛
  클래스명(`AwqGEMMQuantLinear`) import가 비양자화 모델 로드 시에도 걸린다
  (7-2의 패치 3과 동일한 셔임을 무조건 모듈 최상단에 둬야 함).
- **`apply_chat_template(return_tensors="pt")`는 여기서도 BatchEncoding을 반환**한다
  (7번에서 겪은 것과 동일) — `["input_ids"]`로 실제 텐서를 꺼내야 `.shape` 접근이 된다.
- **경로 계산 실수**: `suvisdev/scripts/*.py`는 리포 루트 기준 2단계 깊이라
  `Path(__file__).resolve().parents[1]`은 `suvisdev/`까지만 간다. 리포 루트의 모델
  체크포인트(`Qwen2.5-1.5B-Instruct/` 등)를 가리키려면 `.parent`를 한 번 더 타야 한다.

### 8-4. 시맨틱 인텐트 분류를 실제 채팅에 연결 (Qwen 기반, QLoRA 불필요)

이 파이프라인과 별개로, mova/chat 자체도 질문을 `crud`/`rag`/`general` 세 갈래로 분류해
영화와 무관한 질문은 Gemini로 보내도록 연결함. 분류·RAG 답변 모두 QLoRA 파인튜닝 없이
Qwen2.5-1.5B 하나에 **역할별 시스템 프롬프트만 갈아 끼우는 동적 프롬프팅**으로 충분했다.

- `ontology/app/ports/output/intent_classifier_port.py` + `llm_intent_classifier.py`
  (`LlmIntentClassifier`) — 독립 게이트웨이(`POST /api/ontology/semantic/ask`)와
  `mova/app/use_cases/market_chat_interactor.py`가 이 분류기를 공유.
- **분류 프롬프트 실측 이슈**: "rag" 기준을 "저장된 지식에서 사실을 찾아야 하는 질문"처럼
  추상적으로 적으니 "슬픈 영화 추천해줘" 같은 실제 요청을 매번 "general"로 오분류했다 —
  "영화 추천/검색 요청은 전부 rag"라고 few-shot으로 못박아서 해결.
- **`crud` 오분류 대응**: mova/chat엔 실제 CRUD 기능이 없는데, "안드레 카파시가 주장한
  코딩 원칙은?"처럼 영화와 무관한 질문이 `crud`로 오분류되면 예전 코드는 그냥 `rag`와
  동일하게 영화 추천 파이프라인을 태워서 엉뚱한 영화 제목을 추천해버렸다(독립
  게이트웨이엔 crud 분기가 있었는데 `ChatInteractor`엔 빠뜨렸었음). `crud`도 `general`과
  동일하게 Gemini 위임으로 처리하도록 수정 — 분류기가 완벽하지 않아도 안전망이 됨.
- **DB 세션 동시성 버그(부수 발견)**: `ChatInteractor.chat()`이 `asyncio.gather`로
  `get_recent_intents_by_user`와 `get_preferences`를 동시 실행했는데, 이 둘은 FastAPI가
  요청당 캐싱하는 같은 `get_mova_db()` 세션을 공유해서 SQLAlchemy가
  `"concurrent operations are not permitted"`로 막았다. `user_id`를 채운 실제 요청을
  이번에 처음 테스트하며 발견(그 전까진 전부 익명 호출이라 이 분기 자체가 안 탔음).
  이 둘은 순차 실행으로, RAG 검색(다른 세션)만 병렬로 남기도록 수정.
