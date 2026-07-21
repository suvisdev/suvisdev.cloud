# 02. 물체 감지 에이전트 — "Argus"

> **에이전트 이름 추천**: **Argus** (그리스 신화의 백 개 눈을 가진 거인 — 모든 걸 감지)
> 파일명: `object_detection_interactor.py`
> **원논문**: SSD (구식 CNN) → **최신 대체**: RT-DETR (트랜스포머) 또는 YOLOv8/v11
> **공통 규약(00_COMMON_conventions.md)을 먼저 읽어라.**

---

## 1. 모델 선택 근거

| 후보 | 아키텍처 | QLoRA/LoRA | 3050 8GB 파인튜닝 | 추천도 |
|------|---------|-----------|------------------|--------|
| SSD (원논문) | CNN | ❌ 이득 없음 | full ft만 | 구식 |
| **YOLOv8n/s** | CNN(효율적) | ❌ | ✅ full ft 매우 쉬움 | ⭐ 실용 1순위 |
| **RT-DETR-R18** | 트랜스포머 | ✅ LoRA 가능 | ⚠️ 되지만 무거움 | ⭐ QLoRA 학습용 |

**결정 가이드**:
- **바로 잘 되는 결과 원하면 → YOLOv8n/s** (full fine-tune, 8GB 여유롭게 돌아감, 데이터 준비도 표준화됨)
- **QLoRA/트랜스포머 경험이 목적이면 → RT-DETR + LoRA**
- 포트폴리오 임팩트: RT-DETR가 "트랜스포머 detection + LoRA"라 스토리가 좋음. 단 학습 안정성은 YOLO가 위.

> H0에서 사용자에게 **YOLO(쉬움/안정) vs RT-DETR(QLoRA 스토리)** 중 선택받아라.

## 2. 데이터셋 준비 가이드

물체 감지는 **bounding box 라벨**이 필요하다.

**형식**: YOLO 형식 권장 (RT-DETR도 변환 가능)
```
dataset/
  images/
    train/  img001.jpg ...
    val/    ...
  labels/
    train/  img001.txt ...   # 각 줄: <class_id> <cx> <cy> <w> <h> (0~1 정규화)
    val/    ...
  data.yaml               # train/val 경로 + 클래스 이름 목록
```

**라벨링 도구**: Roboflow, CVAT, LabelImg 중 택1 → YOLO 형식 export

**데이터 규모 기준 (fine-tune)**:
| 클래스당 박스 수 | 기대치 |
|-----------------|--------|
| ~50 | 데모용, 과적합 주의 |
| 200~500 | 실용 최소선 ✅ |
| 1000+ | 안정적 |

**주의**: 클래스 불균형 심하면 mAP 왜곡. augmentation(mosaic, flip)으로 보완.

## 3. Harness 단계

- **H0**: `ultralytics`(YOLO) 또는 `transformers`+`RT-DETR` 설치. 모델 방식 사용자 확정.
- **H1**: 3050 free VRAM 측정 → batch size 결정 (YOLOv8n이면 8~16, RT-DETR면 2~4)
- **H2**: 위 데이터셋 구조 검증, data.yaml 작성, 로더가 박스 정상 파싱하는지 확인
- **H3**: 파인튜닝
  - YOLO: `model.train(data='data.yaml', epochs=..., imgsz=640, batch=...)`
  - RT-DETR: LoRA 어댑터를 attention projection에 부착 후 학습
  - **best mAP 체크포인트 저장**
- **H4**: 추론 어댑터 — `ObjectDetectorPort.detect(image_bytes) -> list[Detection]`, Detection VO(label, bbox, confidence)
- **H5**: MCP tool
  ```python
  @mcp.tool()
  async def detect_objects(image_b64: str) -> dict:
      """이미지에서 물체를 감지해 각 객체의 클래스·위치(bbox)·신뢰도를 반환한다.
      '이 사진에 뭐가 있어', '객체 찾아줘' 등의 요청에 사용."""
  ```
- **H6**: 에이전트 시스템 프롬프트(스킬)
  ```
  너는 물체 감지 에이전트 Argus다.
  - 이미지 내 객체 위치·종류를 물으면 detect_objects를 사용한다.
  - confidence 0.5 미만 감지는 "불확실"로 표시한다.
  - 감지된 객체를 개수·위치와 함께 요약한다.
  ```

## 4. Gate 요약
- H1: VRAM 실측 + batch 상한
- H2: 로더가 (이미지, 박스) 배치 정상 반환
- H3: val mAP 로그 + 체크포인트
- H4: 포트 통해 Detection VO 반환
- H5: tool 호출 성공
- H6: "이 사진에 뭐 있어?" → 감지 결과 자연어 응답
