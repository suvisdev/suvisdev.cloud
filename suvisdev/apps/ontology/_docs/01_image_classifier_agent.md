# ConvNeXt-Nano 이미지 분류 에이전트 구현 지시서

> **대상**: Claude Code
> **방식**: 헤르메스 엔지니어링 (Harness 단계 분할 + 단계별 검증 산출물)
> **프로젝트**: SUVIS 플랫폼 내 신규 이미지 분류 에이전트

---

## 0. 이 문서를 읽는 Claude Code에게

이 작업은 **한 번에 다 짜지 마라.** 아래 Harness 단계(H0~H6)를 **순서대로** 진행하고, 각 단계 끝의 **검증 게이트(✅ Gate)** 를 통과하기 전에는 다음 단계로 넘어가지 않는다. 각 게이트는 사람이 눈으로 확인할 수 있는 구체적 산출물이다.

각 단계 시작 시:
1. 그 단계의 목표와 산출물을 한 줄로 재확인
2. 구현
3. Gate 검증 명령을 실제로 실행하고 결과를 보고
4. 통과하면 다음 단계, 실패하면 그 단계에서 수정

**절대 금지**: 게이트 건너뛰기, 여러 단계 한꺼번에 구현, VRAM 검증 없이 온프레미스 배포 코드 작성.

---

## 1. 내 사양 및 제약 (반드시 준수)

### 하드웨어
- **온프레미스**: Ubuntu 서버(ssu), **RTX 3050 8GB VRAM** ← 이게 최대 제약
  - 이미 EXAONE 2.4B + Qwen 에이전트 2개가 GPU 점유 중
  - **ConvNeXt inference는 남는 VRAM에서 돌아야 함** → 메모리 예산 관리 필수
- **AWS**: **현재 미사용, 곧 도입 예정** → 지금은 붙이지 말되, **나중에 갈아끼울 수 있게 인터페이스로 추상화**해둘 것

### 아키텍처 (SUVIS 규약 = 반드시 따를 것)
- **헥사고날 클린 DDD**
- 데이터 흐름: `Schema → DTO → App → VO → Entity → ORM → DB`
- **titanic 앱이 아키텍처 기준 규약**: `from_orm()` 팩토리 패턴, frozen dataclass VO, DIP로 교체 가능한 adapter
- 포트/어댑터 분리: inbound(API) / outbound(모델 추론, 저장소)

### 네트워크
- Cloudflare Tunnel: `api.suvisdev.cloud` → 온프레미스 FastAPI
- 로컬 PC(a) → 서버(ssu)는 VS Code Remote-SSH

### A2A / 에이전트
- **MCP 기반**으로 도구 노출
- LLM 에이전트가 `classify_image` 등의 tool을 호출하는 구조
- 최종 추론 결과는 Vercel로 내보내는 흐름과 연결 가능해야 함

---

## 2. 목표 아키텍처

```
[LLM Agent]  ──MCP──▶  [MCP Server]  ──port/adapter──▶  [ConvNeXt Inference (GPU)]
 오케스트레이터          tool 노출              헥사고날 outbound adapter      fine-tuned 가중치
```

**용어 정리** (혼동 방지):
- **tool** = MCP 서버가 LLM에 노출하는 함수 (`classify_image` 등)
- **skill** = 그 tool을 *언제/어떻게* 쓸지 알려주는 docstring + 에이전트 시스템 프롬프트
- 즉 "툴과 스킬을 준다" = MCP tool 정의 + 잘 쓰이게 하는 설명/프롬프트 설계

---

## 3. Harness 단계

### H0. 프로젝트 스캐폴딩 + 환경 검증

**목표**: SUVIS 헥사고날 구조에 맞는 빈 골격과 의존성 확인.

**작업**:
1. titanic 앱 구조를 참조해서 신규 앱 디렉토리 생성 (앱 이름은 나에게 물어볼 것 — 예: `visor`, `oculus` 등)
2. 헥사고날 레이어 디렉토리 생성:
   ```
   apps/<app>/
     domain/         # VO, Entity (frozen dataclass)
     application/    # 유스케이스, 포트 인터페이스(추상)
     adapter/
       inbound/api/  # FastAPI 라우터
       outbound/
         model/      # ConvNeXt 추론 어댑터
         storage/    # 이미지 저장 어댑터 (로컬 → 나중에 S3)
     schema/         # 요청/응답 DTO
   ```
3. `requirements` 확인 및 설치: `torch`, `timm`, `pillow`, `fastapi`, `mcp`, `httpx`

> ⚠️ **torch/CUDA는 서버(ssu)의 기존 EXAONE 환경과 버전 충돌 가능.** 새 venv를 쓸지, 기존 환경에 얹을지 **먼저 나에게 확인**하고, 기존 CUDA 버전을 `nvidia-smi`로 조회한 뒤 호환 torch를 설치할 것.

**✅ Gate H0**:
```bash
python -c "import torch, timm; print(torch.cuda.is_available(), timm.__version__)"
# → True 와 timm 버전이 출력되어야 통과
tree apps/<app> -L 3   # 레이어 구조 확인
```

---

### H1. VRAM 예산 측정 (배포 전 필수)

**목표**: 3050 8GB에서 ConvNeXt-Nano가 **실제로 올라갈 여유가 있는지** 먼저 확인. 이걸 안 하고 짜면 나중에 OOM으로 다 갈아엎게 된다.

**작업**:
1. 현재 GPU 점유 조회: `nvidia-smi --query-gpu=memory.used,memory.free --format=csv`
2. EXAONE/Qwen이 떠 있는 상태에서 **남은 free VRAM** 기록
3. ConvNeXt-Nano(약 15M 파라미터, fp32 기준 대략 60~250MB + 추론 버퍼)를 로드하는 최소 스크립트로 실측:
   ```python
   import torch, timm
   before = torch.cuda.memory_allocated()
   m = timm.create_model('convnext_nano', pretrained=True).eval().cuda()
   x = torch.randn(1,3,224,224).cuda()
   with torch.no_grad(): m(x)
   print("delta MB:", (torch.cuda.memory_allocated()-before)/1e6)
   ```
4. **결론 판정**: 남는 VRAM에 여유 있으면 GPU 상주, 빠듯하면 아래 전략 중 택1을 나에게 제안:
   - (a) GPU 상주 (여유 충분)
   - (b) 요청 시 로드 → 추론 → 언로드 (느리지만 안전)
   - (c) **CPU 추론** (ConvNeXt-Nano는 작아서 CPU도 실용적 — VRAM 경합 완전 회피)

> 💡 ConvNeXt-Nano는 매우 가벼워서 **(c) CPU 추론이 현실적 선택지**다. EXAONE/Qwen이 GPU를 꽉 쓰는 상황이면 CPU 추론을 우선 검토하라. 단, 배치·처리량 요구가 있으면 GPU. 이 판단을 Gate 산출물에 명시할 것.

**✅ Gate H1**:
- `nvidia-smi` free VRAM 값 + ConvNeXt 로드 delta MB를 **표로 보고**
- GPU 상주 / lazy load / CPU 중 **어느 전략을 왜 택했는지 1문단**으로 결론

---

### H2. Fine-tune 학습 파이프라인

**목표**: 내 데이터셋으로 ConvNeXt-Nano fine-tune, 재현 가능한 학습 스크립트 + 가중치 산출.

> ⚠️ **데이터셋 정보를 먼저 나에게 물어볼 것**: 클래스 수, 클래스별 이미지 장수, 디렉토리 구조(ImageFolder 형식인지), train/val 분할 여부. 이 값에 따라 freeze 전략과 lr이 달라진다.

**작업**:
1. `timm.create_model('convnext_nano', pretrained=True, num_classes=NUM_CLASSES)`
2. transform은 `timm.data.resolve_data_config` + `create_transform` 사용
3. **freeze 전략** (데이터 규모 기반, H2 시작 시 확정):
   - 소량(클래스당 <100장): backbone freeze, head만 학습
   - 중량: backbone 뒤쪽 stage만 unfreeze (layer-wise lr)
   - 충분: 전체 fine-tune, backbone lr을 head보다 낮게
4. optimizer AdamW, 학습 중 **best val acc 체크포인트 저장**
5. **가중치와 함께 `classes.json`(index↔label 매핑) 반드시 저장** — 추론 응답 라벨에 필수
6. 학습은 3050에서 돌리되 **batch size는 VRAM 여유에 맞춰** (H1 결과 참조, 작게 시작)

**✅ Gate H2**:
```
- weights.pth 파일 존재
- classes.json 파일 존재 (클래스 수 일치)
- val accuracy 로그 출력 (베이스라인 대비 개선 확인)
- 단일 샘플 이미지로 predict 스모크 테스트 1회 성공
```

---

### H3. Inference Adapter (헥사고날 outbound)

**목표**: DDD 규약대로 추론을 outbound adapter로 캡슐화. 모델을 **1회만 로드**하고 포트 인터페이스 뒤에 숨긴다.

**작업**:
1. `application` 레이어에 **포트(추상 인터페이스)** 정의:
   ```python
   class ImageClassifierPort(Protocol):
       def classify(self, image: bytes) -> list[Prediction]: ...
   ```
2. `Prediction`은 **frozen dataclass VO** (label: str, confidence: float)
3. `adapter/outbound/model/`에 ConvNeXt 구현체 — 앱 시작 시 모델·transform·classes 1회 로드
4. H1에서 정한 전략(GPU/CPU/lazy) 반영
5. **DIP 준수**: 유스케이스는 포트에만 의존, 구현체는 주입. 나중에 AWS SageMaker 등으로 갈아끼울 수 있게.

**✅ Gate H3**:
```python
# 포트를 통해 호출했을 때 Prediction VO 리스트가 나오는지 단위 테스트
preds = classifier_port.classify(sample_bytes)
assert all(isinstance(p, Prediction) for p in preds)
assert preds[0].confidence <= 1.0
```

---

### H4. FastAPI Inbound + Cloudflare Tunnel 노출

**목표**: 추론 유스케이스를 HTTP로 노출, `api.suvisdev.cloud` 경유로 접근 가능하게.

**작업**:
1. `adapter/inbound/api/`에 라우터: `POST /<app>/classify` (이미지 업로드 → top-k 예측)
2. 요청/응답은 **DTO(schema)** 로 (`Schema → DTO → App → VO` 흐름 준수)
3. 유스케이스는 H3 포트를 주입받아 호출
4. 기존 SUVIS FastAPI 앱 조립 방식(prefix `/viewer` 같은 패턴)에 맞춰 라우터 등록
5. Cloudflare Tunnel 통해 `https://api.suvisdev.cloud/<app>/classify` 로 접근되는지 확인

> ⚠️ **이미지 전달 방식 결정**: 에이전트(추후 AWS)와 추론(온프레미스)이 파일시스템을 공유하지 않는다. tool 인자로 로컬 경로를 쓰지 말고 **base64 또는 (추후) S3 URL** 로 넘기도록 설계. 지금은 base64/멀티파트 업로드, AWS 도입 시 S3 URL 어댑터를 추가할 수 있게 추상화.

**✅ Gate H4**:
```bash
curl -X POST https://api.suvisdev.cloud/<app>/classify \
  -F "file=@sample.jpg"
# → {"predictions":[{"label":..., "confidence":...}, ...]} 정상 응답
```

---

### H5. MCP Server (tool 노출 = "툴을 준다")

**목표**: 위 추론 서비스를 MCP tool로 감싸 LLM 에이전트가 호출 가능하게.

**작업**:
1. `FastMCP` 서버 생성
2. tool 정의 — **docstring이 곧 skill**이니 정성껏:
   ```python
   @mcp.tool()
   async def classify_image(image_b64: str) -> dict:
       """이미지를 분류해 top-3 클래스와 신뢰도를 반환한다.
       사용자가 '이 사진이 뭐야', '무슨 이미지야' 등 이미지 내용을
       물을 때 사용한다. image_b64는 base64 인코딩된 이미지."""
       # H4의 /classify 엔드포인트를 httpx로 호출
   ```
   ```python
   @mcp.tool()
   async def list_supported_classes() -> list[str]:
       """이 분류기가 인식 가능한 클래스 목록을 반환한다.
       지원 여부가 불확실할 때 먼저 호출한다."""
   ```
3. MCP 서버는 온프레미스 또는 (추후) AWS 어디든 뜰 수 있게 `INFERENCE_URL`을 환경변수로

**✅ Gate H5**:
```
- MCP inspector 또는 테스트 클라이언트로 tool 목록에 classify_image가 뜨는지 확인
- base64 이미지 넣고 호출 → 예측 결과 반환 확인
```

---

### H6. 에이전트 통합 + Skill(시스템 프롬프트) 부여

**목표**: LLM 에이전트에 MCP tool 연결 + 행동 규칙으로 "스킬" 완성.

**작업**:
1. 에이전트(온프레미스 EXAONE/Qwen 또는 오케스트레이터)에 H5 MCP 서버 연결
2. **에이전트 시스템 프롬프트에 도메인 스킬 규칙** 삽입:
   ```
   너는 이미지 분류 에이전트다.
   - 이미지 관련 질문이면 classify_image tool을 사용한다.
   - top-1 confidence < 0.6 이면 "확실하지 않다"고 명시하고 상위 후보를 함께 제시한다.
   - 지원 클래스가 의심되면 list_supported_classes로 먼저 확인한다.
   - 결과는 사용자 친화적으로 요약해 전달한다.
   ```
3. 결과를 Vercel로 내보내는 기존 A2A 흐름과 연결 지점 확인

**✅ Gate H6 (최종 통합 테스트)**:
```
샘플 이미지로 에이전트에게 "이거 뭐야?" 질문
→ 에이전트가 classify_image 호출
→ confidence 기반으로 자연어 응답
→ (연결 시) Vercel로 결과 전달
전 과정 1회 성공
```

---

## 4. AWS 마이그레이션 대비 (지금은 구현 X, 설계만)

곧 AWS 도입 예정이므로 아래를 **인터페이스로만 뚫어두고 실제 구현은 미루기**:

| 컴포넌트 | 현재 (온프레미스) | AWS 도입 시 |
|----------|------------------|------------|
| 이미지 저장 | 로컬/base64 | S3 URL 어댑터 추가 |
| 추론 | 온프레미스 GPU/CPU | SageMaker endpoint 어댑터로 교체 가능 |
| MCP/Agent | 온프레미스 | AWS로 이전 가능 (INFERENCE_URL만 변경) |

**DIP 덕분에 포트만 유지하면 어댑터 교체로 끝난다.** H3/H4에서 포트 추상화를 지키는 게 이 마이그레이션의 전제다.

---

## 5. 진행 규칙 요약 (Claude Code 체크리스트)

- [ ] 각 Harness 단계는 **순서대로**, Gate 통과 후 다음으로
- [ ] H0에서 **venv/CUDA 버전을 나에게 확인**
- [ ] H1(VRAM 측정)을 **배포 코드보다 먼저** — 3050 8GB 경합 판정
- [ ] H2 전 **데이터셋 정보(클래스 수/장수/구조)를 나에게 질문**
- [ ] 앱 이름을 나에게 확인
- [ ] titanic 앱 규약(from_orm, frozen VO, DIP) 준수
- [ ] 이미지 전달은 경로 X, base64/S3 URL
- [ ] AWS는 인터페이스만, 구현 미루기
- [ ] 각 단계 산출물/Gate 결과를 나에게 보고 후 진행

---

## 6. 시작

**H0부터 시작하되, 먼저 아래 3가지를 나에게 물어본 뒤 진행하라:**
1. 새 앱 이름
2. 서버(ssu) CUDA 버전 및 기존 EXAONE 환경에 얹을지 새 venv를 쓸지
3. 데이터셋: 클래스 수, 클래스당 대략 이미지 장수, 디렉토리 구조

---

## 7. 완료 기록 (2026-07-21, 커밋 `2ed8fd2`)

이 지시서는 **ConvNeXt-Nano 포스터→장르 분류** 에이전트로 구체화되어 H0~H6 전 단계 완료됐다. 새 앱을 따로 만들지 않고 기존 `ontology` 앱 안에 리소스 어댑터로 붙였다.

| 단계 | 결과 |
|------|------|
| **H0** | `ontology` 앱 내 `adapter/outbound/resource_adapters/convnext/` 스캐폴딩, `timm` 의존성 추가(`requirements.txt`) |
| **H1** | VRAM 실측 — EXAONE/Ollama와 공유 시 여유 최저 429MB. **"요청 시 로드→추론→언로드"** 전략 채택(평소엔 VRAM 점유 없음) |
| **H2** | TMDB API로 포스터 232장 확보(`scripts/prepare_genre_classifier_dataset.py`), TMDB 세부 장르 19종 → 6개 대분류로 재매핑, backbone freeze + head만 학습(`scripts/train_genre_classifier.py`). best val_acc **53.3%**(랜덤 베이스라인 16.7% 대비 개선) |
| **H3** | `ImageClassifierPort` / `ImageClassifierUseCase` / `image_classifier_interactor.py` — YOLO(face) 선례와 동일한 헥사고날 패턴, DIP 준수 |
| **H4** | `POST/GET /api/vision/genre/{classify,classes}` — Cloudflare Tunnel 경유 실제 응답 확인 |
| **H5** | `image_classifier_mcp_server.py`(FastMCP, `classify_image`/`list_supported_classes`) — stdio 클라이언트로 tool 목록·왕복 호출 검증(`scripts/test_mcp_classifier_client.py`) |
| **H6** | `vision_genre_agent.py` — qwen2.5:1.5b가 tool_calls를 신뢰성 있게 생성하지 않음을 실측 확인하고, tool 트리거는 결정적 규칙(이미지 첨부 시 항상 호출)으로 처리, LLM은 confidence 기반 자연어 요약만 담당. 고/저신뢰도 케이스 모두 실제 왕복 검증 |

**가중치**(`apps/ontology/runs/`)는 기존 YOLO 관례대로 `.gitignore` 대상, **학습 데이터셋**(`resources/genre_classifier_train/`)은 yolo_train 선례처럼 커밋됨.

**이 에이전트가 07(Echo)의 H5/H6 구현 시 참고한 원형 패턴**이다 — `sentiment_analysis_mcp_server.py`/`sentiment_echo_agent.py`가 각각 이 파일들의 구조를 그대로 따른다.