# 04. 자세 추정 에이전트 — "Atlas"

> **에이전트 이름 추천**: **Atlas** (몸으로 하늘을 떠받친 거인 — 신체·자세의 상징)
> 파일명: `pose_estimation_interactor.py`
> **원논문**: OpenPose (CNN) → **최신 대체**: ViTPose (트랜스포머, LoRA 가능) 또는 RTMPose(초경량)
> **공통 규약(00_COMMON_conventions.md)을 먼저 읽어라.**

---

## 1. 모델 선택 근거

| 후보 | 아키텍처 | QLoRA/LoRA | 3050 8GB | 추천도 |
|------|---------|-----------|----------|--------|
| OpenPose (원논문) | CNN | ❌ | 무거움 | 구식 |
| **ViTPose-small** | 트랜스포머 | ✅ LoRA | ✅ | ⭐ QLoRA 스토리 |
| **RTMPose-s** | CNN(초경량) | ❌ | ✅✅ 매우 빠름 | ⭐ 실용 1순위 |
| MoveNet | CNN | ❌ | ✅ 초경량 | 실시간용 |

**결정 가이드**:
- **QLoRA/트랜스포머 목적 → ViTPose-small** (ViT 백본에 LoRA 부착)
- **가볍고 빠른 실용 → RTMPose-s** (`mmpose`)
- 자세 추정은 보통 **top-down**(사람 감지 후 각자 자세) 방식. 사람 검출기(YOLO)와 조합 필요할 수 있음 → md H0에서 결정.

## 2. 데이터셋 준비 가이드

자세 추정은 **키포인트(관절 좌표) 라벨**이 필요하다.

**형식**: COCO keypoint 형식 표준
```
dataset/
  images/  train/ val/
  annotations/
    person_keypoints_train.json   # COCO 형식
    person_keypoints_val.json
```
- 각 사람마다 관절 17개(COCO 기준) `[x, y, visibility]`
- bbox + keypoints 함께 라벨

**라벨링 도구**: CVAT(keypoint 템플릿), COCO Annotator

**데이터 규모**:
| 인물 인스턴스 수 | 기대치 |
|-----------------|--------|
| ~200 | 데모 |
| 1000~3000 | 실용 ✅ |
| 5000+ | 안정 |

**팁**: 자세 추정은 라벨링이 까다로움(관절 하나하나 찍기). 공개 데이터셋(COCO, MPII) 일부 + 도메인 소량 파인튜닝 전략 권장 → H2에 반영.

## 3. Harness 단계

- **H0**: `mmpose`(RTMPose) 또는 `transformers`+ViTPose 설치. top-down 여부(사람 검출기 필요성) 결정.
- **H1**: VRAM 실측. ViTPose-s면 batch 4~8, 사람 검출기 동시 로드 시 VRAM 합산 주의.
- **H2**: COCO keypoint 형식 검증. 관절 수·visibility 플래그 확인. 공개셋+도메인셋 병합 전략.
- **H3**: 파인튜닝
  - ViTPose: ViT 백본에 LoRA, keypoint head 학습, metric: AP(OKS 기반)
  - RTMPose: 표준 파인튜닝
  - **best AP 체크포인트 저장**
- **H4**: 추론 어댑터 — `PoseEstimatorPort.estimate(image_bytes) -> list[PersonPose]` (각 사람의 keypoints VO)
- **H5**: MCP tool
  ```python
  @mcp.tool()
  async def estimate_pose(image_b64: str) -> dict:
      """이미지 속 사람들의 관절 위치(자세)를 추정해 반환한다.
      '자세 분석해줘', '이 사람 무슨 동작이야' 등에 사용.
      반환: 사람별 관절 좌표 + (선택)스켈레톤 시각화."""
  ```
- **H6**: 시스템 프롬프트
  ```
  너는 자세 추정 에이전트 Atlas다.
  - 사람의 자세/동작을 물으면 estimate_pose를 사용한다.
  - 관절 좌표로부터 동작을 해석(서 있음/앉음/팔 들기 등)해 요약한다.
  - 사람이 없으면 그렇게 알린다.
  ```

## 4. Gate 요약
- H1: VRAM + (검출기 포함) batch 상한
- H2: COCO keypoint 파싱 통과
- H3: val AP 로그 + 체크포인트
- H4: 포트 통해 keypoints 반환
- H5: tool 호출 성공
- H6: 자연어 질의 → 자세/동작 해석 응답
