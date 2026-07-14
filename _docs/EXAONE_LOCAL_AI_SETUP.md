# EXAONE 로컬 소버린 AI 환경 구성 (Router/Worker)

> 이 문서 하나만 보고 새 PC(WSL2 + NVIDIA GPU)에서 그대로 재현할 수 있도록 작성함.
> sudo 없이 설치 가능한 방법만 사용한다 (WSL Docker Desktop 통합이 꺼져있어도 무관).

## 0. 아키텍처 개요

- **Router model**: `exaone3.5:7.8b` — 라우팅/판단
- **Worker model**: `exaone3.5:2.4b` — 실행
- 8GB급 GPU(RTX 3050 등) 기준, **Router와 Worker를 동시에 GPU에 상주시키지 않는다** — 순차 호출
- Ollama(GGUF) 기반. AWQ/vLLM은 시도했으나 이 스택(최신 Python, 사전빌드 wheel 부재)에서 막혀서 폐기함 — GGUF/Ollama가 정답
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

## 7. 참고 — 시도했다가 폐기한 경로

- **AWQ (`transformers` + `autoawq`/`gptqmodel`)**: `autoawq`는 deprecated, 최신 `transformers`는
  `gptqmodel`을 요구하는데 PyPI에 사전빌드 wheel이 없어 소스 빌드(gcc/nvcc/Rust) 필요. 하지 말 것.
- **vLLM**: `torch==2.11.0` 등 정확한 버전 재설치 필요, 수 GB 다운로드. 단일 GPU 순차 호출
  구조엔 이득이 없어서 중단함.
