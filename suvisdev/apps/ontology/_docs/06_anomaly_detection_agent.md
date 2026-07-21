# 06. 이상 화상 탐지 에이전트 — "Sentinel"

> **에이전트 이름 추천**: **Sentinel** (파수꾼 — 정상에서 벗어난 이상을 감시)
> 파일명: `anomaly_detection_interactor.py`
> **원논문**: AnoGAN / Efficient GAN (구식, 학습 불안정) → **최신 대체**: PatchCore 또는 EfficientAD
> **공통 규약(00_COMMON_conventions.md)을 먼저 읽어라.**

---

## 1. 모델 선택 근거 ⭐ 이 태스크는 오히려 가벼움

| 후보 | 방식 | 학습 부담 | 3050 8GB | 추천도 |
|------|------|----------|----------|--------|
| AnoGAN/EfficientGAN (원논문) | GAN | 무겁고 불안정 | 학습 어려움 | 구식 |
| **PatchCore** | 사전학습 특징 + memory bank | **학습 거의 없음** | ✅✅ 매우 가벼움 | ⭐ 1순위 |
| **EfficientAD** | 경량 distillation | 가벼움 | ✅ 빠름 | ⭐ 속도 우선 |

**핵심**: 이상 탐지는 **QLoRA가 안 맞는 대표 케이스**. 왜냐면:
- PatchCore는 **정상 이미지의 특징을 memory bank에 저장**해두고, 추론 시 거리로 이상 판단 → **파인튜닝(경사하강)이 거의 없음**
- 그래서 3050 8GB에서 가장 부담이 적은 태스크
- `anomalib`(Intel) 라이브러리가 PatchCore/EfficientAD 다 지원 → 이걸 쓰면 구현이 매우 간단

**공통 규약의 "학습이 거의 없는 방식"에 해당** → QLoRA 대신 정상 이미지 feature memory 구축.

## 2. 데이터셋 준비 가이드

이상 탐지는 **정상(good) 이미지 위주**로 학습하고, 이상은 테스트에만 있으면 된다 (unsupervised).

**형식**: MVTec AD 형식 표준 (`anomalib` 호환)
```
dataset/
  train/
    good/        정상 이미지만 ...   ← 학습은 정상만!
  test/
    good/        정상 테스트 ...
    defect_A/    이상 유형 A ...
    defect_B/    ...
  ground_truth/  (선택) 이상 영역 마스크
    defect_A/ ...
```

**데이터 규모**:
| 항목 | 장수 |
|------|------|
| train/good | 100~300장 (정상만) ✅ |
| test/good | 20~50장 |
| test/defect | 유형별 10~30장 |

**핵심 팁**: 이상 샘플은 **적어도 됨**(unsupervised). 정상 이미지를 충분히·일관되게 모으는 게 관건. 촬영 조건(조명·각도) 일정하게 → H2에 반영.

## 3. Harness 단계

- **H0**: `anomalib` 설치, PatchCore/EfficientAD 로드 확인. 방식 선택(정확도 PatchCore / 속도 EfficientAD).
- **H1**: VRAM 실측. 이 태스크는 가벼워 여유 클 것 → feature 추출용 backbone(WideResNet 등)만 로드.
- **H2**: MVTec 형식 검증. train은 good만 있는지 확인, test 구조 확인.
- **H3**: "학습" = 정상 이미지로 **memory bank / distillation 구축** (경사하강 최소)
  - PatchCore: 정상 특징 coreset 저장
  - metric: image/pixel AUROC
  - **모델 아티팩트 저장**
- **H4**: 추론 어댑터 — `AnomalyDetectorPort.detect(image_bytes) -> AnomalyResult` (anomaly score + 이상 영역 heatmap)
- **H5**: MCP tool
  ```python
  @mcp.tool()
  async def detect_anomaly(image_b64: str) -> dict:
      """이미지가 정상인지 이상(결함)인지 판정하고 이상 점수·위치를 반환한다.
      '불량 검사', '이상 있어?', '결함 찾아줘' 요청에 사용.
      반환: anomaly_score, is_anomaly(임계값 기준), heatmap."""
  ```
- **H6**: 시스템 프롬프트
  ```
  너는 이상 탐지 에이전트 Sentinel이다.
  - 정상/이상 판정을 물으면 detect_anomaly를 사용한다.
  - anomaly_score와 임계값을 함께 제시하고, 이상 영역을 heatmap으로 안내한다.
  - 임계값 근처면 "경계선"임을 알린다.
  ```

## 4. Gate 요약
- H1: VRAM 실측(여유 클 것)
- H2: train=good only, test 구조 통과
- H3: image AUROC 로그 + memory bank/모델 저장
- H4: 포트 통해 anomaly score+heatmap 반환
- H5: tool 호출 성공
- H6: "이상 있어?" → 판정 + 점수 응답
