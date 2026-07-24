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

## 5. H3 디버깅 기록 (2026-07-23) — additive vs subtractive anomaly, 범위 재정의

### 5.1 문제

Phase A(MVTec bottle, `verify_patchcore_mvtec_sanity.py`)는 image AUROC 1.0으로
파이프라인 정합성을 확인했으나, Phase B(포스터 도메인, 합성 손상 3종 — 블러/
검은막/워터마크)에서는 `engine.test()` 기준 AUROC가 0.525 수준으로 거의
랜덤에 가까웠다. 계측 버그 의심(min-max 정규화의 validation 클리핑,
val_split이 test를 절반 떼어가는 문제)을 먼저 배제했다 — 정규화 OFF +
`val_split_mode=SAME_AS_TEST`(test 117장 전부 평가)로도 전체 AUROC는
개선되지 않았다(`diagnose_sentinel_normalization.py`).

### 5.2 손상 유형별 분해 (`diagnose_sentinel_per_defect.py`)

합친 AUROC가 유형별 편차를 가리고 있었다. normal(test/good, n=42) 대비
유형별 AUROC:

| 유형 | AUROC | score mean | score std |
|------|-------|-----------|-----------|
| normal(기준) | — | 67.712 | 8.395 |
| blur | **0.5733** | 70.730 | 3.846 |
| black_bar | 0.5095 | 69.005 | 4.302 |
| watermark | 0.4838 | 68.685 | 4.589 |

blur만 랜덤보다 뚜렷이 낫고, black_bar/watermark는 사실상 랜덤(0.5) 수준.

### 5.3 근본 원인 확인 (`diagnose_sentinel_feature_norm.py`)

PatchCore의 NN-distance는 "정상 학습 분포가 점유한 feature-space 영역에서
벗어난 정도"를 잰다. memory bank에 들어가기 전 단계인 patch embedding의
L2 norm(정보량/구조 밀도 proxy)을 그룹별로 직접 뽑아 NN-distance와 대조:

| 그룹 | patch L2 norm 평균 | NN-distance 평균 |
|------|--------------------|--------------------|
| good(정상) | 77.320 | 50.167 |
| blur | **74.621**(↓ 뚜렷) | **53.595**(↑ 최대) |
| black_bar | 77.419(≈정상) | 51.207 |
| watermark | 77.634(≈정상, 소폭↑) | 50.886 |

- **blur**: 이미지 전체에 균일하게 적용되는 진짜 subtractive 손상 → 모든
  patch의 feature norm이 정상 학습 분포의 하한(73.6~80.6) 아래로 고르게
  밀려남 → 이미지 평균 feature가 "정상 posters가 점유한 영역" 바깥으로
  뚜렷이 벗어남 → NN-distance 최대, AUROC 최고(0.573), score 분산도 최소
  (std 3.846, blur가 있으면 항상 비슷하게 큼).
- **black_bar**: 이미지 높이의 ~20%만 가리는 **국소** 손상. 이미지 전체
  patch 평균으로 보면 나머지 80%가 정상이라 평균 feature norm이 거의
  안 움직인다(77.4 vs 77.3) — 국소 이상이 전역 통계에 희석됨. 그런데도
  compute_anomaly_score(사실상 max 기반)가 국소 patch의 이상치를 일부
  포착해 AUROC가 랜덤보다 살짝 높다(0.510) — 그 이상은 아니다.
- **watermark**: 반투명(alpha 110/255) 텍스트를 전체 타일링 — 형식적으론
  additive(정보 추가)지만 강도가 약해 norm을 정상 분포 범위 **안에서**
  살짝 올릴 뿐(77.6, 오히려 정상 평균보다 높음)이라 "정상이 점유한 영역
  안"에 머문다 → 사실상 구별 불가(AUROC 0.484, 랜덤 이하).

**정정된 결론**: 단순한 "additive=잘 잡힘 / subtractive=못 잡힘" 이분법보다
정확한 설명은 — *정상 학습 분포가 점유한 feature-space 영역(patch norm
73~80 부근)에서 얼마나, 얼마나 균일하게 벗어나는가*다. blur는 전역·균일하게
그 영역 아래로 벗어나 가장 잘 잡힌다. black_bar(국소)와 watermark(약한
강도)는 영역을 벗어나는 정도가 약하거나 이미지 평균에 희석돼 거의 안 잡힌다.
즉 PatchCore는 **"정상 도메인 내에서의 미세한 결함"**(MVTec의 긁힘·이물질처럼
국소적이고 강하게 대비되는 additive 신호)에 최적화돼 있고, **전역적 화질
저하**나 **약하고 국소적인 손상**에는 구조적으로 약하다.

### 5.4 Sentinel 범위 재정의

위 결과에 따라 Sentinel의 "이상"을 다음과 같이 재정의한다.

1. **이상탐지(PatchCore) 대상 = 포스터가 아닌 이미지**(예고편 스틸, 인물
   사진, 배너 등). 이는 진짜 additive/out-of-envelope 신호라 PatchCore가
   원래 잘하는 문제로 되돌아가는 것이고, harvester가 실제로 걸러야 하는
   운영 목적(포스터 크롤링 파이프라인에 엉뚱한 이미지가 섞여 들어오는 것
   차단)에도 더 부합한다.
2. **화질 저하(블러 등)는 분리**한다. PatchCore로는 AUROC 0.573이 한계이고
   기존 목적과도 안 맞는다 — Laplacian variance 등 무참조(no-reference)
   화질 지표로 별도 경량 체크를 둔다.
3. **검은막/워터마크류 국소·저강도 손상은 이번 스코프에서 제외**한다 —
   PatchCore가 구조적으로 약한 영역이라는 게 확인됐고, harvester 목적상
   우선순위도 낮다.

**다음 단계(미착수)**: `prepare_sentinel_poster_dataset.py`를 "정상 포스터
vs non-poster negative(TMDB 예고편 스틸 등)" 데이터셋으로 다시 짜고, blur
경로는 anomaly detection과 별개의 라이트웨이트 체크로 분리 구현.

## 6. §5.4 재정의 검증 결과 (2026-07-23) — PatchCore 도메인 부적합, 분류기로 전환

### 6.1 데이터셋

§5.4 재정의를 실제로 검증하려고 `prepare_sentinel_nonposter_dataset.py`로
TMDB에서 negative를 모았다(기존 genre_classifier_train의 tmdb id 190개
재사용). 검증 전 두 가지를 사용자가 먼저 지적해 반영했다:

1. **종횡비 누출 방지**: 기본 전처리 `Resize(256,256)`은 종횡비를 무시하고
   정사각형으로 찌그러뜨린다. 포스터(≈2:3)와 backdrop(16:9≈1.78)을 그대로
   섞으면 모델이 "많이 찌그러진 이미지=이상"이라는 내용과 무관한 지름길을
   학습할 위험이 있다 → 저장 전 모든 negative를 2:3으로 center crop.
2. **라벨 재정의**: TMDB posters 배열의 textless/비주력 언어판은 전부 공식
   포스터라 harvester가 수집해도 오류가 아니다 → 처음엔 "hard negative"로
   잘못 라벨링했다가, "정상인데 이상으로 라벨링하면 모델이 옳게 판단해도
   실패로 집계된다"는 지적을 받고 `test/alt_poster_control`(위양성 대조군,
   **정상** 취급)로 재정의했다. 진짜 이상은 `test/non_poster_easy`
   (backdrop 20 + cast profile 20)만 남았다.

| 그룹 | 구성 | 라벨 |
|------|------|------|
| test/good | 정상 포스터 42장(기존) | 정상 |
| test/non_poster_easy | backdrop 20 + cast profile 20, 2:3 center crop | **이상** |
| test/alt_poster_control | textless 15 + 비주력 언어판 15, 2:3 center crop | 정상(위양성 대조군) |

### 6.2 결과 — AUROC 0.44, "랜덤 이하"가 아니라 "신호 없음"

| 그룹 | score mean | std |
|------|-----------|-----|
| good | 67.699 | 8.591 |
| non_poster_easy | 68.355 | 5.835 |
| alt_poster_control | 67.133 | 7.973 |

- **AUROC(good vs non_poster_easy) = 0.4429**, 수동 pairwise 재계산(직접
  P(pos>neg)+0.5·P(pos==neg) 계산)도 동일값 — sklearn 라벨 극성 버그 아님을
  확인.
- **정확한 서술**: n=(42,40)에서 AUROC의 근사 표준오차가 약 0.079, 부트스트랩
  95% CI = **[0.314, 0.566]**로 0.5를 포함한다 → "랜덤보다 나쁘다"가 아니라
  **"이 표본 크기로는 랜덤과 통계적으로 구분되지 않는다(신호 없음)"**가
  정확한 결론이다. 세 그룹 평균 차이(1점 내외)도 표준편차(6~9)보다 훨씬
  작다 — 애초에 그룹 간 분리가 거의 없다는 뜻.
- 하위유형 분해도 마찬가지: backdrop AUROC=0.4548, cast profile
  AUROC=0.4310 — 둘 다 0.5 근방, 한쪽이 평균을 끌어내린 게 아니다.
- alt_poster_control(정상) 중 good의 95th percentile 임계값을 넘는 비율
  20.0%(6/30) — 우연 수준(5%)보다 높긴 하나 n=30이라 이 자체도 노이즈일
  수 있다.

사용자가 사전에 정한 판정 기준("0.9+ 유효 / 0.6대면 PatchCore 자체
재검토")과 비교하면 0.44(CI가 0.5를 포함)는 재검토 기준선보다도 명백히
아래 — 결론은 바뀌지 않는다.

### 6.3 원인 추정

§5.3에서 확인했듯 PatchCore는 **patch 단위 지역 텍스처**를 memory bank와
비교한다. 영화 포스터는 실사 사진(배우 얼굴·장면) 위에 제목·크레딧 같은
그래픽 레이어를 얹은 합성물인 경우가 많다 — 즉 포스터 patch의 상당 부분이
"그냥 인물/장면 사진"과 지역 텍스처 수준에서 거의 동일하다. backdrop과 cast
profile은 바로 그 "포스터 안에 이미 들어있는 사진 자체"라서, patch-level
매칭으로는 구별 신호가 거의 없다. 포스터를 포스터답게 만드는 요소(레이아웃,
텍스트 블록, 여백 구성)는 이미지 전체에서 차지하는 patch 비중이 작고,
이미지 단위 점수(사실상 max 기반)에 묻힌다 — §5.3의 black_bar가 국소
손상이라 안 잡혔던 것과 같은 매커니즘이다. 종횡비 지름길을 제거하고 나니
바로 이 근본적인 약점이 드러난 것으로 보인다.

### 6.4 결론

**§5.4의 "이상탐지(PatchCore) 대상 = 포스터가 아닌 이미지" 재정의는 이
접근(PatchCore, wide_resnet50_2 기본 backbone, 이미지 단위 점수)으로는
기각한다.** patch-level 텍스처 비교는 "포스터냐 아니냐"라는 전역적·구성적
(compositional) 질문에 구조적으로 안 맞는다 — 이건 근본적으로 분류
문제(classification)에 가깝지, 정상 분포에서 벗어난 국소 이상을 찾는
문제(anomaly detection)가 아니다.

### 6.5 방향 결정 (2026-07-23)

세 갈래(① 분류기로 전환 / ② PatchCore 설정을 더 파본다 / ③ Sentinel 존재
이유 재검토) 중 **①을 선택**했다 — CLIP backbone으로 바꾸는 순간 사실상
분류 문제가 되어 버려 ②는 ①로 수렴한다고 판단했기 때문이다.

- **포스터 판별**: PatchCore/anomalib이 아니라 CLIP 제로샷 분류 또는
  01(장르 분류)에서 쓴 것과 같은 경량 분류기로 별도 구현한다.
- **화질 저하(blur)**: Laplacian variance 임계값으로 분리 구현한다. 임계값은
  정상 포스터 232장(genre_classifier_train 전체)의 Laplacian variance
  하위 5퍼센타일로 산출하고, 해상도 정규화(고정 크기로 resize) 후 계산해
  이미지 원본 해상도 차이가 임계값에 섞여 들어가지 않게 한다.
- **PatchCore/anomalib(Sentinel 원래 설계)**: Phase A(MVTec bottle, AUROC
  1.0, `verify_patchcore_mvtec_sanity.py`) 결과는 파이프라인 구현이
  정상 동작한다는 근거로 남긴다. 포스터 도메인에는 §5~§6에서 확인한 이유
  (patch-level 텍스처 비교가 전역적·구성적 판별에 구조적으로 안 맞음)로
  **도메인 부적합 판정, 기각**한다.

### 6.6 방향 결정 즉시 검증 (2026-07-23)

같은 라벨셋(test/good·non_poster_easy·alt_poster_control)과 정상 포스터
232장으로, 학습 없이 방향 전환이 실제로 맞는지 바로 확인했다.

- **CLIP 제로샷**(`diagnose_sentinel_clip_poster_classifier.py`,
  `openai/clip-vit-base-patch32`, 프롬프트 대비만으로 파인튜닝 없음):
  AUROC(포스터=good+alt_poster_control vs 이상=non_poster_easy) =
  **0.8844** — PatchCore의 0.44(신호 없음)와 비교하면 압도적으로 개선.
  0.5 임계값 기준 정답률: good 95.2%, alt_poster_control 90.0%,
  non_poster_easy 75.0%. §6.2가 설정한 "0.9+" 문턱에는 살짝 못 미치지만
  이건 이상탐지가 아니라 분류 프레이밍이라 같은 잣대를 그대로 적용할
  필요는 없다 — 프롬프트 튜닝이나 01처럼 소규모 파인튜닝하면 더 오를
  여지가 있다. **PatchCore→CLIP 전환이 방향적으로 맞다는 근거.**
- **Laplacian variance**(`compute_sentinel_blur_threshold.py`, 정상
  232장을 256x256으로 해상도 정규화 후 계산): 하위 5퍼센타일 임계값 =
  **345.77**(정상 분포 mean=1346.7, std=791.4). 대조군인 합성 블러
  25장(Phase B 잔존 리소스, Gaussian blur radius=10)은 mean=3.3으로
  전부(25/25, 100%) 임계값 아래로 떨어진다 — PatchCore의 blur AUROC
  0.573과 비교하면 사실상 완전 분리. **blur를 PatchCore가 아니라
  Laplacian variance로 넘긴 판단도 근거로 확인됨.**

### 6.7 H4(추론 어댑터) 완료 (2026-07-24)

`SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`가 남겨둔 미결정 사항(포트 1개
통합 vs 2개 분리)을 **1개 통합**으로 확정하고 진행했다 — 헥사고날
단일 책임 원칙상으로는 2개 분리가 더 맞지만, 두 체크(CLIP/Laplacian)가
항상 같은 호출에서 함께 쓰이고 별도로 교체될 계획이 없어 포트 1개로
단순화하는 쪽을 선택.

**DTO 재설계** (`app/dtos/anomaly_detection_dto.py`): 기존 PatchCore 가정
(`anomaly_score`, `is_anomaly`, `heatmap_b64`)을 버리고 두 신호를 그대로
반환하는 `AnomalyResult(is_poster, poster_confidence, is_blurry,
sharpness_score)`로 교체. CLIP/Laplacian 둘 다 히트맵을 만들지 않아
`heatmap_b64` 제거, 종합 판정(`is_anomaly`) 필드는 추가하지 않고 호출부가
`not is_poster or is_blurry`로 조합하도록 남김(요청되지 않은 필드 추가
안 함).

**어댑터** (`adapter/outbound/resource_adapters/sentinel_anomaly/
sentinel_anomaly_adapter.py`, 신규): `AnomalyDetectionPort.detect()` 안에서
`_check_poster`(CLIP 제로샷, §6.6 프롬프트·임계값 0.5 그대로)와
`_check_blur`(Laplacian, §6.5 임계값 345.77 그대로)를 순서대로 호출해
합친다. CLIP은 `echo_sentiment_adapter.py`와 동일하게 **호출당
로드→추론→언로드**(00_COMMON §1.1, lora-server 상시 점유 고려).
Laplacian은 opencv 경량 연산이라 로드/언로드 없음.

**Provider** (`dependencies/anomaly_detection_provider.py`, 신규):
`echo_sentiment_provider.py`와 동일 패턴.

**H4 게이트 검증** (`test/test_sentinel_anomaly_adapter.py`,
`@pytest.mark.gpu`, `suvisdev-backend-1` 컨테이너에서 실행):
- `test/good/0000.jpg` → `is_poster=True, is_blurry=False` — PASSED
- `test/blur/0000.jpg` → `is_blurry=True` — PASSED
- VRAM: 호출 전후 `nvidia-smi` 2879MB→2879MB로 동일(로드-언로드가 실제로
  해제됨 확인), lora-server(`:8200/health`) `model_loaded:true` 유지 —
  학습이 아닌 추론이라 00_COMMON §1.1의 사전 정지 절차는 적용 대상 아님.

### 6.8 H5(HTTP API + MCP tool) 완료 (2026-07-24)

01/07과 동일 패턴 — HTTP 라우터를 얹고 MCP 서버는 ontology 내부 모듈에
직접 의존하지 않고 HTTP로만 호출한다(AWS 전환 대비, 00_COMMON §6).

**HTTP 라우터** (`adapter/inbound/api/v1/anomaly_detection_router.py`, 신규):
`image_classifier_router.py` 패턴 그대로 — `UploadFile` 입력,
`POST /sentinel/detect`(전체 경로 `/api/vision/sentinel/detect`),
`asyncio.to_thread`로 호출당 CLIP 로드 블로킹 방지, 잘못된 이미지는
`UnidentifiedImageError` → 400. `adapter/inbound/api/__init__.py`의
`vision_router`에 등록.

**MCP 서버** (`adapter/inbound/mcp/anomaly_detection_mcp_server.py`, 신규):
`image_classifier_mcp_server.py` 패턴 — `detect_anomaly(image_b64) -> dict`
tool, base64 이미지를 받아 `/api/vision/sentinel/detect`로 HTTP POST.
`INFERENCE_URL` 환경변수로 base URL 교체 가능.

**H5 게이트 검증** (`scripts/test_mcp_sentinel_client.py`, 신규 — 01의
`test_mcp_classifier_client.py`와 동일한 stdio MCP 클라이언트,
`suvisdev-backend-1` 리빌드+재기동 후 컨테이너 안에서 실행):
- 라우트 등록 확인: `app.routes`에 `/api/vision/sentinel/detect` 존재.
- tool 목록에 `detect_anomaly` 등장.
- 전체 체인(MCP → HTTP → interactor → 어댑터 → CLIP+Laplacian) 호출 성공:
  - `test/good/0000.jpg` → `is_poster:true(0.699), is_blurry:false(2588)` — 정상 포스터 정답.
  - `test/blur/0000.jpg` → `is_blurry:true(1.82)` — 블러 정답.
  - 둘 다 `GATE_H5_PASS`.
- VRAM: 호출 2회에 걸쳐 2863→2984→3014MB(호출당 +30~120MB, CLIP 가중치
  수백MB가 쌓이지 않음 → 로드-언로드 정상, 잔여는 CUDA 컨텍스트로 안정).
  lora-server(`:8200/health`) `model_loaded:true` 유지.

### 6.9 H6(용도 확정 + 업로드 게이트 통합) 완료 (2026-07-24)

**용도 확정 = `POST /vision/upload` 업로드 게이트 (소거법).** 06이 처음 무너진
"기법 먼저, 용도 나중"을 피하려고, Sentinel의 `is_poster`/블러 신호가 **실제로
갈리는 입력**이 있는 경로만 정당하다는 기준으로 후보를 추적했다:
- **harvester 수집 경로 → 기각**: 수집 VO `ScrapedRecord`에 이미지 필드가
  없고 스크레이퍼(news/wiki/kobis/tmdb)는 전부 텍스트만 모은다. 포스터 이미지
  0장 → 검수 대상 없음.
- **TMDB poster → 기각**: mova는 `poster_url`(TMDB CDN URL 문자열)만 저장하고
  바이트를 안 내려받는다. 보장된 포스터라 `is_poster` 항상 True → 신호 없음.
- **lora-server 생성 → 기각**: lora-server는 텍스트 생성기(EXAONE/AWQ, mova
  채팅 RAG)라 포스터를 만들지 않는다. 포스터 생성은 Prisma(05)인데 `diffusion/`
  어댑터가 빈 껍데기(0줄)이고 05는 보류 → 생성 파이프라인 부재.
- **`vision/upload` → 채택**: 확장자·빈 파일만 검증하고 내용물은 미검증. 사용자/
  어드민이 뭘 올릴지 불확실 → 두 신호 모두 실제로 갈린다. 01 분류기에 쓰레기
  입력이 들어가는 것도 막는 전처리가 됨.

**설계 (사용자 지정 3조건)**:
1. **두 신호를 다른 강도로**: 블러(`sharpness_score`)는 **하드 게이트**(임계값
   345.77 미달 시 `ValueError`→라우터가 400), `is_poster`(CLIP 제로샷)는 **소프트**
   — 차단하지 않고 `is_poster_warning` 플래그만 세운다(제로샷이라 티저·캐릭터
   포스터 오탐 위험 → 어드민 오버라이드 여지).
2. **임계값은 `VisionInteractor`가 소유**: 어댑터의 부울(`is_poster`/`is_blurry`)이
   아니라 raw 값(`poster_confidence`/`sharpness_score`)을 받아 interactor가 판정.
   어댑터 부울은 `/sentinel/detect`·MCP 직접 소비자용으로 남기고, 업로드 게이트는
   자체 임계값 상수로 역할별 정책 분기 여지를 확보.
3. (raw 값 사용은 2에 포함.)

**구현**:
- `app/dtos/vision_dto.py`: `VisionUploadResponse`에 `poster_confidence`/
  `sharpness_score`/`is_poster_warning` 추가(기본값 있어 repository는 무변경).
- `app/use_cases/vision_interactor.py`: `AnomalyDetectionPort` 주입, `upload_image`가
  `asyncio.to_thread`로 detect 호출 → 블러 하드 게이트 + 포스터 소프트 플래그 →
  `dataclasses.replace`로 메타데이터 부착. 임계값(`_BLUR_THRESHOLD`=345.77,
  `_POSTER_CONFIDENCE_THRESHOLD`=0.5) interactor 소유.
- `dependencies/vision_provider.py`: 기존 `get_anomaly_detection_port` 재사용해 주입.

**H6 게이트 검증** (`test/test_vision_upload_sentinel_gate.py`, `@pytest.mark.gpu`):
저장 백엔드(S3/DB)와 무관하게 게이트 로직만 보려고 **fake VisionPort** + 실제
Sentinel 어댑터를 `VisionInteractor`에 주입해 3경로 검증(컨테이너에서 실행):
- `good/0000.jpg` → 통과 + 저장, `is_poster_warning=False`, sharpness≥345.77 — PASSED
- `blur/0000.jpg` → `ValueError`(하드 게이트), 저장 안 됨 — PASSED
- `non_poster_easy/cast_0001.jpg`(conf 0.003, sharp 497) → 소프트 플래그 + 저장 — PASSED
- VRAM 3034→3034MB 동일(로드-언로드 정상), lora-server 정상.

**동기 요청 지연 · VRAM 경합 판단 (감수)**: 업로드가 동기 요청이라 호출당 CLIP
로드로 ~20초 지연되고 EXAONE(lora-server)과 VRAM을 공유한다. 그래도 감수한다 —
(a) 이 경로는 어드민/간헐 업로드 검수라 고빈도 사용자 트래픽이 아니고(Echo가
호출당 수십 초 로드를 "보조 에이전트용"으로 감수한 것과 동일 판단), (b)
`asyncio.to_thread`로 이벤트 루프는 안 막으며, (c) CLIP-ViT-B/32는 가벼워 H5·H6
실측상 로드-언로드 후 baseline 복귀(경합 위험 낮음). 트래픽이 늘면 상주 서빙/
배치로 전환한다.

**알아둘 점**: 블러 임계값(345.77)은 포스터(텍스트·그래픽으로 고주파 많음)로
보정돼서, 디테일 적은 비포스터 사진(backdrop 등)이 "블러"로 하드 반려되기도
한다(예: backdrop 상당수가 sharp<345.77). 업로드 게이트 용도(선명한 포스터를
원함)에선 허용 가능한 동작이라 그대로 둔다.

**미결/백로그**:
- 소프트 플래그의 **저장 지속화 + 어드민 오버라이드 엔드포인트**는 저장 계층이
  정리된 뒤로 미룸(지금 배선은 S3인데 AWS 미연결, DB 폴백 `VisionRepository`는
  존재하나 미배선 — `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 참고). 이번 H6은 게이트
  로직 + 응답 메타데이터까지만 확정하고, 플래그를 스토어에 남기는 건 별도.
- 기존 순환 임포트: `app/ports/input/vision_use_case.py`가 어댑터 계층
  `api.schemas.vision_schema`를 임포트(app→adapter DIP 위반)해서 import 순서에
  따라 순환이 터진다. H6 테스트에서 드러났고 프로덕션은 `main.py` 순서 덕에
  회피 중. 테스트는 `api` 애그리게이터 선(先)로드로 우회. 근본 수정은 백로그
  (WORK_LOG 2026-07-24).
