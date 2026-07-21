# 공통 규약 (모든 에이전트 md 공유)

> 2~8번 각 에이전트 md는 이 파일을 **먼저 읽고** 개별 지시를 따른다.
> Claude Code는 각 작업 시작 시 이 규약을 준수한다.

---

## 1. 하드웨어 제약 (절대 기준)

- **GPU: RTX 3050, VRAM 8GB** ← 모든 설계의 최상위 제약
- **온프레미스 3050 단일에서 전부 실행** (파인튜닝 + 추론)
- 이미 EXAONE 2.4B + Qwen 에이전트가 GPU를 점유 중일 수 있음
  → 각 태스크 파인튜닝 시 **다른 LLM은 내리고** 진행하거나, VRAM 여유 실측 후 batch/해상도 조정
- **모든 파인튜닝은 8GB 안에서 끝나야 함**: batch size 작게 시작(1~4), gradient accumulation 활용, mixed precision(fp16/bf16) 기본

## 2. QLoRA / LoRA 적용 원칙

| 아키텍처 | 파인튜닝 방식 |
|----------|--------------|
| 트랜스포머 계열 (ViT, DETR, SegFormer, Transformer 등) | **QLoRA/LoRA** (4bit + adapter) |
| 소량 데이터 + 트랜스포머 | LoRA (양자화 없이도 8GB에 맞으면) |
| 학습이 거의 없는 방식 (PatchCore 등) | 파인튜닝 대신 feature memory 구축 |
| GAN/Diffusion 생성 | LoRA(diffusion) 또는 소형 full ft |

**원칙**: 트랜스포머면 QLoRA/LoRA를 1순위로. VRAM 이득이 없거나 구조가 안 맞으면 md에 이유를 명시하고 대안 사용.

## 3. 아키텍처 규약 (SUVIS DDD)

- **헥사고날 클린 DDD**, 데이터 흐름 `Schema → DTO → App → VO → Entity → ORM → DB`
- 기존 프로젝트 구조에 맞춰 아래 위치에 배치:
  ```
  app/
    ports/           # 추상 포트 인터페이스 (태스크별 Port 정의)
    use_cases/       # <task>_interactor.py  ← 에이전트 유스케이스
    dtos/            # 요청/응답 DTO
  adapter/
    outbound/model/  # 모델 추론 어댑터 (포트 구현체)
  ```
- **interactor 패턴 준수**: 기존 `*_interactor.py`(hub_rag_interactor 등)와 동일한 컨벤션
- **DIP**: use_case는 추상 포트에만 의존, 모델 구현체는 주입 → 추후 AWS/다른 모델로 교체 가능
- VO는 frozen dataclass, `from_orm()` 팩토리 패턴(titanic 규약)

## 4. 헤르메스 엔지니어링 (harness 단계)

각 md는 아래 공통 뼈대를 태스크에 맞게 채운다. **순서대로, Gate 통과 후 다음 단계.**

| 단계 | 목표 | Gate(검증 산출물) |
|------|------|------------------|
| **H0** | 환경/의존성/데이터 구조 확인 | import 성공 + 폴더 구조 |
| **H1** | VRAM 예산 실측 | free VRAM + 모델 로드 delta, batch 상한 결정 |
| **H2** | 데이터셋 준비 및 검증 | 데이터 로더가 정상 배치 반환 |
| **H3** | 파인튜닝 (QLoRA/LoRA/기타) | 학습 곡선 + best 체크포인트 |
| **H4** | 추론 어댑터 (헥사고날 포트) | 포트 통해 VO 반환 단위테스트 |
| **H5** | interactor + MCP tool 노출 | tool 목록에 등장 + 호출 성공 |
| **H6** | 에이전트 통합 + 시스템 프롬프트(스킬) | 자연어 질의 → tool 호출 → 응답 |

**금지**: Gate 건너뛰기, 여러 단계 동시 구현, VRAM 실측(H1) 없이 학습 코드 작성.

## 5. "툴과 스킬을 준다"의 의미

- **tool** = MCP 서버가 노출하는 함수 (예: `detect_objects`, `segment_image`)
- **skill** = ① tool의 docstring(언제/어떻게 쓸지) + ② 에이전트 시스템 프롬프트의 행동 규칙
- 각 md의 H5/H6에서 이 둘을 반드시 정성껏 작성

## 6. AWS 대비 (지금은 설계만)

- 곧 AWS 도입 예정 → 포트 추상화만 유지, 실제 구현 미룸
- 이미지/영상 전달은 로컬 경로 대신 **base64 또는 (추후) S3 URL**
- 추론 어댑터를 SageMaker 등으로 교체 가능하게 DIP 준수

## 7. 진행 규칙

- 각 단계 산출물을 사용자에게 보고 후 다음으로
- 데이터셋/환경 관련 불확실한 값은 **추측하지 말고 질문**
- 파인튜닝 방식(QLoRA/full/head) 확정 전 사용자 확인
