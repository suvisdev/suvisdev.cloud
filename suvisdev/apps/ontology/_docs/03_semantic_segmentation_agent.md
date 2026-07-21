# 03. 시맨틱 분할 에이전트 — "Loom"

> **에이전트 이름 추천**: **Loom** (베틀 — 픽셀 단위로 이미지를 짜서 영역을 나눈다)
> 파일명: `loom_interactor.py`
> **원논문**: PSPNet (CNN) → **최신 대체**: SegFormer-B0 (트랜스포머) — LoRA 적용 가능
> **공통 규약(00_COMMON_conventions.md)을 먼저 읽어라.**

---

## 1. 모델 선택 근거

| 후보 | 아키텍처 | QLoRA/LoRA | 3050 8GB | 추천도 |
|------|---------|-----------|----------|--------|
| PSPNet (원논문) | CNN | ❌ | full ft만, 무거움 | 구식 |
| **SegFormer-B0** | 트랜스포머(경량) | ✅ LoRA | ✅ 실용적 | ⭐ 1순위 |
| Mask2Former | 트랜스포머 | ✅ | ⚠️ 8GB 빡셈 | 무거움 |

**결정**: **SegFormer-B0**. MiT 백본이 트랜스포머라 LoRA를 attention에 붙일 수 있고, B0는 가장 경량이라 3050에 맞음. `transformers`의 `SegformerForSemanticSegmentation` 사용.

## 2. 데이터셋 준비 가이드

시맨틱 분할은 **픽셀별 마스크**가 필요하다 (박스가 아님).

**형식**:
```
dataset/
  images/
    train/  img001.png ...
    val/    ...
  masks/
    train/  img001.png ...   # 각 픽셀값 = 클래스 id (0,1,2,...), 팔레트 PNG
    val/    ...
```
- 마스크는 **이미지와 동일 크기**, 픽셀값이 클래스 인덱스
- 배경도 하나의 클래스(보통 0)

**라벨링 도구**: CVAT, Roboflow(segmentation), Segment Anything(SAM)으로 반자동 마스크 생성 후 보정

**데이터 규모**:
| 이미지 수 | 기대치 |
|-----------|--------|
| ~100 | 데모 |
| 300~800 | 실용 ✅ |
| 1000+ | 안정 |

**주의**: 분할은 라벨링 비용이 태스크 중 가장 큼. SAM으로 초벌 마스크 뽑고 사람이 수정하는 워크플로우 강력 추천 → md H2에 반영.

## 3. Harness 단계

- **H0**: `transformers`, `datasets`, `evaluate`, `peft`(LoRA) 설치. SegFormer-B0 로드 확인.
- **H1**: VRAM 실측. 분할은 고해상도라 메모리 큼 → **imgsz 512 이하, batch 2~4**로 시작, OOM이면 512→384.
- **H2**: 데이터셋 검증. 마스크-이미지 크기 일치, 클래스 인덱스 범위 확인. SAM 초벌 마스크 파이프라인(선택).
- **H3**: LoRA 파인튜닝
  - `peft`로 SegFormer attention에 LoRA 부착
  - loss: cross-entropy(픽셀별), metric: mIoU
  - **best mIoU 체크포인트 저장**
- **H4**: 추론 어댑터 — `SegmenterPort.segment(image_bytes) -> SegmentationResult` (mask 배열 + 클래스별 영역)
- **H5**: MCP tool
  ```python
  @mcp.tool()
  async def segment_image(image_b64: str) -> dict:
      """이미지를 픽셀 단위로 분할해 각 영역의 클래스와 마스크를 반환한다.
      '이 이미지 영역별로 나눠줘', '어디가 무엇인지' 요청에 사용.
      반환: 클래스별 영역 비율 + (선택)마스크 오버레이 base64."""
  ```
- **H6**: 시스템 프롬프트
  ```
  너는 시맨틱 분할 에이전트 Loom이다.
  - 이미지의 영역 구분을 물으면 segment_image를 사용한다.
  - 클래스별 면적 비율을 요약하고, 필요시 마스크 시각화를 제공한다.
  ```

## 4. Gate 요약
- H1: VRAM + 해상도/batch 상한
- H2: 마스크-이미지 정합성 통과
- H3: val mIoU 로그 + 체크포인트
- H4: 포트 통해 마스크 결과 반환
- H5: tool 호출 성공
- H6: 자연어 질의 → 영역 분할 요약 응답
