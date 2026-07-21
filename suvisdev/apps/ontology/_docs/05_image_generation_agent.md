# 05. 이미지 생성 에이전트 — "Prisma"

> **에이전트 이름 추천**: **Prisma** (프리즘 — 무에서 색과 형상을 만들어냄)
> 파일명: `prisma_interactor.py`
> **원논문**: DCGAN / Self-Attention GAN (구식) → **최신 대체**: Stable Diffusion + LoRA(DreamBooth/LoRA 파인튜닝)
> **공통 규약(00_COMMON_conventions.md)을 먼저 읽어라.**

---

## 1. 모델 선택 근거 ⚠️ 3050 8GB 최대 난관 중 하나

| 후보 | 아키텍처 | 파인튜닝 | 3050 8GB | 비고 |
|------|---------|---------|----------|------|
| DCGAN/SAGAN (원논문) | GAN(CNN) | full ft | ✅ 저해상도만 | 품질 낮음, 구식 |
| **SD 1.5 + LoRA** | Diffusion(UNet+트랜스포머) | ✅ **LoRA** | ⚠️ 8GB 빠듯하지만 가능 | ⭐ 실용/포폴 1순위 |
| SDXL | Diffusion | LoRA | ❌ 8GB로 매우 어려움 | 비추천 |

**핵심 현실**:
- **생성 모델은 이 목록 중 VRAM이 가장 빡센 축.** SD 1.5 LoRA 학습은 8GB에서 **가능하지만** xformers/8bit optimizer/gradient checkpointing 필수.
- DCGAN을 쓰면 학습은 가볍지만 결과 품질이 포폴용으로 약함.
- **권장**: SD 1.5 + LoRA(스타일/객체 학습). 해상도 512, batch 1, gradient accumulation.
- **대안**: VRAM 문제로 학습이 계속 실패하면 → 소형 GAN(경량)으로 폴백하거나 AWS 도입 후 진행하도록 md에 분기.

> H1(VRAM)에서 SD LoRA 학습이 8GB에 실제로 들어가는지 **반드시 먼저 실측**. 안 되면 사용자에게 폴백 선택 요청.

## 2. 데이터셋 준비 가이드

무엇을 생성할지에 따라 다름:

**(A) 스타일/객체 LoRA (권장)**
```
dataset/
  images/   img001.jpg ...   # 학습할 스타일·객체 10~30장이면 충분(LoRA)
  captions/ img001.txt ...   # 각 이미지 캡션(트리거 워드 포함)
```
- LoRA는 **소량(10~30장)** 으로도 특정 스타일/객체 학습 가능
- 캡션에 트리거 워드(예: `sks dog`) 넣어 개념 주입

**(B) 처음부터 GAN 학습(비권장, 폴백)**
- 도메인 이미지 수천 장 필요, 저해상도(64~128)로 제한

**데이터 규모**:
| 목적 | 장수 |
|------|------|
| SD LoRA 스타일 | 10~30 ✅ |
| SD LoRA 객체(DreamBooth) | 5~20 ✅ |
| GAN from scratch | 3000+ (비권장) |

## 3. Harness 단계

- **H0**: `diffusers`, `peft`, `accelerate`, `xformers`, `bitsandbytes` 설치. SD 1.5 로드 확인.
- **H1**: ⭐ **VRAM 실측이 이 태스크의 생사 결정.** SD LoRA 학습 스텝 1회를 실제로 돌려 OOM 여부 확인.
  - 필수 최적화: gradient checkpointing, 8bit Adam, mixed precision, batch 1, res 512
  - 실패 시 → 폴백(경량 GAN or AWS 연기) 사용자에게 제안
- **H2**: 이미지-캡션 쌍 검증, 트리거 워드 설정
- **H3**: LoRA 파인튜닝 (DreamBooth-LoRA 스크립트)
  - **LoRA 가중치(.safetensors) 저장** — 원본 SD와 분리
- **H4**: 추론 어댑터 — `ImageGeneratorPort.generate(prompt) -> bytes(png)`
- **H5**: MCP tool
  ```python
  @mcp.tool()
  async def generate_image(prompt: str, style: str = "") -> dict:
      """텍스트 프롬프트로 이미지를 생성해 base64 png로 반환한다.
      '~한 이미지 만들어줘', '그려줘' 요청에 사용.
      학습된 LoRA 스타일/객체는 트리거 워드로 호출."""
  ```
- **H6**: 시스템 프롬프트
  ```
  너는 이미지 생성 에이전트 Prisma다.
  - 이미지 생성 요청 시 generate_image를 사용한다.
  - 학습된 스타일이 있으면 트리거 워드를 프롬프트에 포함한다.
  - 생성에 시간이 걸림을 사용자에게 안내한다.
  ```

## 4. Gate 요약
- **H1: SD LoRA 학습 1스텝이 8GB에서 OOM 없이 도는지 (이 태스크 최대 관문)**
- H2: 이미지-캡션 쌍 + 트리거 워드 확정
- H3: LoRA safetensors 생성 + 샘플 생성 이미지 확인
- H4: 포트 통해 생성 이미지(bytes) 반환
- H5: tool 호출 성공
- H6: "~그려줘" → 생성 이미지 응답
