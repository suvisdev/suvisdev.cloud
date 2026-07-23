# 08. 동영상 분류 에이전트 — "Chronos"

> ⛔ **제외됨 (2026-07-23)** — mova는 포스터(정지 이미지)+텍스트뿐이고 실제
> 영상 파일을 저장·처리하는 파이프라인이 없음(TMDB 트레일러는 외부 링크일
> 뿐 수집 대상 아님), gildle도 영상 없음(용도 위험). 데이터·하드웨어도 모두
> 위험(문서 스스로 "최난도"라 명시 + 상시 VRAM 점유 서비스와 겹침). 감사
> 근거: `00_COMMON_conventions.md` §8.

> **에이전트 이름 추천**: **Chronos** (시간의 신 — 시간축을 가진 영상을 이해)
> 파일명: `video_classification_interactor.py`
> **원논문**: 3DCNN / ECO (구식) → **최신 대체**: VideoMAE-small (트랜스포머, LoRA 가능) 또는 X3D(경량 CNN)
> **공통 규약(00_COMMON_conventions.md)을 먼저 읽어라.**
> ⚠️ **영상은 이 목록에서 VRAM 부담 최대. 프레임/해상도 관리가 핵심.**

---

## 1. 모델 선택 근거 ⚠️ 3050 8GB 최난도

| 후보 | 아키텍처 | QLoRA/LoRA | 3050 8GB | 추천도 |
|------|---------|-----------|----------|--------|
| 3DCNN/ECO (원논문) | 3D CNN | ❌ | 무거움 | 구식 |
| **VideoMAE-small** | 트랜스포머 | ✅ LoRA | ⚠️ 프레임 줄이면 가능 | ⭐ QLoRA 스토리 |
| **X3D-S** | 경량 3D CNN | ❌ | ✅ 효율적 | ⭐ 실용 |
| TimeSformer | 트랜스포머 | ✅ | ❌ 8GB 어려움 | 무거움 |

**핵심 현실**:
- 영상은 **여러 프레임을 동시에 처리** → 이미지보다 메모리 몇 배.
- 8GB 생존 전략: **프레임 수 8~16개로 제한, 해상도 224, batch 1~2, 프레임 샘플링(전체 아닌 균등 추출)**
- **QLoRA 목적 → VideoMAE-small + LoRA**(ViT 백본에 부착), **실용 속도 → X3D-S**
- 계속 OOM이면 → 프레임 8→4, 해상도 다운, 또는 AWS 도입 후로 연기(md 분기).

## 2. 데이터셋 준비 가이드

**형식**: 클래스별 영상 폴더 (video ImageFolder 스타일)
```
dataset/
  train/
    action_a/  vid001.mp4 ...
    action_b/  ...
  val/
    action_a/ ...
  (또는) annotations.csv  # columns: video_path, label
```
- 각 영상은 짧은 클립(수 초) 권장
- 전처리: 균등 프레임 추출 → 텐서 (T×C×H×W)

**데이터 규모**:
| 클래스당 영상 수 | 기대치 |
|-----------------|--------|
| ~50 | 데모(과적합 주의) |
| 200~500 | 실용 ✅ |
| 1000+ | 안정 |

**팁**:
- 영상은 용량 커서 **전처리로 프레임 미리 추출·캐시**하면 학습 빠름(디스크에 프레임 저장) → H2에 반영.
- 클립 길이·fps 통일. 긴 영상이면 대표 구간만.

## 3. Harness 단계

- **H0**: `transformers`(VideoMAE)+`peft` 또는 `pytorchvideo`(X3D), `decord`/`av`(영상 디코딩) 설치. 방식 확정.
- **H1**: ⭐ VRAM 실측 필수. 영상은 가장 빡셈 → **프레임 수·해상도·batch를 실측으로 확정**. OOM이면 프레임/해상도 다운.
- **H2**: 데이터셋 검증. 프레임 추출 파이프라인 구축(균등 샘플링), 클립-라벨 매핑, (권장)프레임 캐시.
- **H3**: 파인튜닝
  - VideoMAE: ViT 백본 LoRA, classification head 학습
  - X3D: 표준 파인튜닝
  - metric: top-1/top-5 accuracy, **best 체크포인트 저장**
- **H4**: 추론 어댑터 — `VideoClassifierPort.classify(video_bytes) -> list[Prediction]` (프레임 추출 내장)
- **H5**: MCP tool
  ```python
  @mcp.tool()
  async def classify_video(video_b64: str) -> dict:
      """짧은 영상 클립의 행동/카테고리를 분류해 top-3와 신뢰도를 반환한다.
      '이 영상 뭐 하는 거야', '동작 분류해줘' 요청에 사용.
      내부적으로 균등 프레임 샘플링 후 추론."""
  ```
  > ⚠️ 영상은 base64가 매우 큼 → 대용량이면 S3 URL/파일 참조 방식 권장(공통 규약 6항). H5에서 전달 방식 확정.
- **H6**: 시스템 프롬프트
  ```
  너는 동영상 분류 에이전트 Chronos다.
  - 영상 내용/행동을 물으면 classify_video를 사용한다.
  - top-1 confidence가 낮으면 상위 후보를 함께 제시한다.
  - 영상이 길면 대표 구간 기준임을 안내한다.
  ```

## 4. Gate 요약
- **H1: 프레임수·해상도·batch 실측 확정 (영상 최대 관문)**
- H2: 프레임 추출 파이프라인 + 클립-라벨 검증
- H3: val accuracy 로그 + 체크포인트
- H4: 포트 통해 Prediction 반환(프레임 추출 포함)
- H5: tool 호출 성공(대용량 전달 방식 확정)
- H6: 영상 입력 → 행동 분류 응답
