# mova 추천 — 원격 GPU(lora_server) 운영 시나리오

> **용도:** 백엔드(EC2 등, GPU 없음)와 `lora_server`(GPU, 예: 집 노트북)를 다른
> 머신에 분리 배포할 때 참조한다. 관련 코드: `core/lol/lora_recommendation_orchestrator.py`,
> `model_servers/lora_server/serve.py`.

## 구조

```
[EC2 backend] --POST /generate(+X-LoRA-Token)--> [Cloudflare Tunnel] --> [집 GPU: lora_server:8200]
```

`RECOMMENDATION_BACKEND=lora`일 때만 이 경로를 탄다. `LORA_SERVER_URL`만 바꾸면
코드 수정 없이 원격으로 붙는다(어댑터가 이 값을 그대로 base URL로 씀).

## 1. 집 GPU 노트북에서 `lora_server`만 띄우기

```bash
cd model_servers/lora_server
source ~/.venv-exaone/bin/activate   # lora_server 전용 venv
uvicorn serve:app --host 0.0.0.0 --port 8200
```

- `~/lora_adapters/LATEST`가 있어야 파인튜닝 어댑터가 로드된다(없으면
  `LORA_FALLBACK_BASE_MODEL`/`LORA_FALLBACK_BACKEND`의 베이스 모델만으로 기동).
- 원격 노출 전, `LORA_SERVER_TOKEN` 환경변수를 이 프로세스에도 설정해야 인증이
  걸린다(아래 4번).
- **`~/.venv-exaone` 버전 핀(2026-09-22)**: `transformers==5.5.0`·`peft==0.20.0` —
  코랩 학습 노트북과 동일. `export_mova_gguf.py`(어댑터 병합)만 이 둘을 쓰고
  `serve_gguf.py`는 쓰지 않는다. 이 venv는 uv로 만들어 `pip`이 없다 →
  `uv pip install --python ~/.venv-exaone/bin/python "transformers==5.5.0" "peft==0.20.0"`.
  09-22에 5.13.1로 드리프트해 병합이 막혔던 전례가 있으니 재학습 전 확인할 것.

## 2. Cloudflare Tunnel로 외부에 노출

집 GPU 노트북에서 `cloudflared`가 이미 돌고 있다면(다른 용도로), 같은 터널에
Public Hostname만 추가하면 된다:

1. Cloudflare Zero Trust 대시보드 → **Tunnels** → 집 GPU 박스에 연결된 터널 선택
2. **Public Hostname 추가**: 서브도메인(예: `lora`), 도메인(`suvisdev.cloud`),
   서비스 `http://localhost:8200`
3. 저장 후 `https://lora.suvisdev.cloud/health`가 열리는지 확인

집에 별도 터널이 없다면 새 터널을 만들어 토큰을 발급받아야 한다(`docker-compose.yaml`의
기존 `cloudflared` 서비스와는 별개 — backend/auth용 터널과 GPU용 터널을 분리 운영).

## 3. EC2 쪽 env 전환

`suvisdev/.env`(EC2):
```dotenv
RECOMMENDATION_BACKEND=lora
LORA_SERVER_URL=https://lora.suvisdev.cloud
LORA_SERVER_TOKEN=<집 GPU와 동일한 값>
```
반영: `docker compose --env-file suvisdev/.env up -d --build backend`
(env만 바뀌어도 컨테이너 재시작이 필요 — `.env`는 컨테이너 기동 시점에만 주입됨.
`--build`까지는 필요 없고 `up -d`로 재기동만 해도 되지만, 다른 코드 변경이 같이
있으면 `--build`도 함께.)

## 4. 인증(X-LoRA-Token)

- `LORA_SERVER_TOKEN`이 **양쪽(EC2 backend, 집 lora_server)** 모두 같은 값이어야
  한다. 한쪽만 설정하면 401(서버는 검증하는데 클라가 헤더를 안 보냄) 또는
  무방비 노출(클라는 보내는데 서버가 비어있어 검증을 스킵) 상태가 된다.
- 로컬 개발(같은 머신, `host.docker.internal`)에서는 비워둬도 된다 — 이때는
  헤더 자체를 안 보내고 서버도 검증을 생략한다.

## 5. 장애 시 수동 폴백

집 GPU 서버가 죽거나 점검 중이면 **자동 폴백은 없다**(의도적 — 응답이 어떤
모델에서 나왔는지 불투명해지는 걸 막기 위함, `apps/mova/dependencies/market_chat_provider.py`
참고). 수동으로:
```dotenv
RECOMMENDATION_BACKEND=gemini
```
로 바꾸고 EC2에서 `docker compose up -d --build backend` 재기동.

## 알려진 한계

- `core/lol/lora_recommendation_orchestrator.py`의 `is_ready()`(헬스체크)는
  코드 어디에서도 호출되지 않는다 — 앱 부팅 시점에도, 요청 경로에서도 사전
  점검이 없다. 장애는 실제 `/generate` 호출이 타임아웃/연결 실패해야 드러난다.
  원격 전환 후 운영 데이터가 쌓이면 부팅 시 헬스체크 또는 모니터링 연동을
  별도 이슈로 검토.
- `generate()`는 네트워크 레벨 실패(타임아웃·연결 끊김)만 1회 재시도한다.
  HTTP 4xx/5xx 응답은 재시도 없이 즉시 실패 처리된다.
