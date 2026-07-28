# labs/ — 독립 실습 데모 (제품 코드 아님)

`suvisdev/apps/`의 어떤 앱(mova/gildle/execsuite 등)과도 엮이지 않는 완전히
고립된 실습 영역이다. `main.py`에 등록하지 않고, `.importlinter`
계약에도 포함하지 않는다 — 이 폴더를 import하는 앱은 없고, 이 폴더도
apps/의 어떤 것도 import하지 않는다.

## 왜 여기 있나

`apps/ontology/_docs/00_COMMON_conventions.md` §8에 따르면, 04(자세 추정)·
08(영상 분류)은 mova/gildle 어디에도 실제 용도가 없어 비전 에이전트 트랙에서
**제외**됐다. 같은 문서 §8은 06(Sentinel)이 "기법을 먼저 정하고 용도를
나중에 붙이면 도메인 불일치로 무너진다"는 걸 실측으로 확인한 사례도
남기고 있다.

이 `labs/`는 그 실패를 반복하지 않기 위한 절충안이다 — **용도가 정해지지
않은 채로 기법만 먼저 연습**하되, 실제 제품 코드에는 절대 섞지 않는다.
나중에 이 기법을 실제로 쓸 프로젝트가 생기면, 그때 그 앱의 컨벤션에 맞춰
가져다 쓴다.

## Port는 참조 구현일 뿐이다

여기 있는 `ports.py`(예: `PoseEstimationPort`)는 **참조 구현**이다. 실제
앱에 편입할 때는 이 Protocol을 그대로 쓰지 말고, 그 앱의 `app/ports/output/`
컨벤션(네이밍, 예외 타입, 동기/비동기 여부 등)에 맞춰 **재배치**한다.

반면 DTO(`PoseResult`, `Keypoint` 등)는 좌표·신뢰도 같은 순수 데이터만
담고 있어 **도메인 중립적**이다 — 특정 앱에 종속된 필드가 없으므로 그대로
가져다 재사용해도 된다.

## 하드웨어 제약

이 환경은 GPU 없이 CPU만 있다(m7i-flex.large). 그래서:
- **학습은 하지 않는다.** 사전학습된 가중치로 추론만 한다.
- 가장 가벼운 모델 크기(n/nano)를 쓴다.
- 학습이 필요한 실험은 여기서 실행하지 않고 별도 노트로만 남긴다.

## 하위 실습

| 디렉토리 | 대응 트랙 | 사전학습 모델 | 상태 |
|---------|----------|--------------|------|
| `pose_estimation/` | 04(Atlas, 자세 추정) | YOLOv8n-pose(ultralytics, 3.3M) | 완료 |
| `video_classification/` | 08(Chronos, 영상 분류) | S3D(torchvision, Kinetics-400, 8.3M) | 완료 |

### `pose_estimation/`

`yolov8n-pose.pt` 가중치는 **최초 실행 시 ultralytics가 자동으로
다운로드한다**(인터넷 필요, 이후엔 실행 위치에 저장된 파일을 재사용 —
`*.pt`는 `.gitignore`에 이미 있어 커밋 걱정 없음). 샘플 이미지
(`samples/sample.jpg`)는 ultralytics 패키지에 기본 내장된 `zidane.jpg`를
그대로 복사해 왔다(자세 추정 데모용으로 널리 쓰이는 표준 샘플).

실행:
```bash
python -m labs.pose_estimation.demo
```

### `video_classification/`

torchvision.models.video 중 가장 가벼운 `s3d`(약 8.3M 파라미터, Kinetics-400
사전학습, 400개 행동 레이블)를 쓴다. 가중치는 **최초 실행 시 torch hub가
자동으로 다운로드한다**(인터넷 필요, 이후엔 `~/.cache/torch/hub/checkpoints/`
캐시 재사용).

이 저장소엔 실제 동영상 샘플이 없어서, `samples/source.jpg`(ultralytics
기본 내장 `bus.jpg`)를 살짝 확대하며 여러 프레임으로 늘린 **합성 클립**을
매 실행 즉석에서 만들어 분류한다(디스크에 저장하지 않음). 진짜 동작이 없는
가짜 움직임이라 분류 결과는 정답이 아니라 **파이프라인이 끝까지 도는지
확인용**이다 — 실제 편입 시에는 이 부분을 진짜 영상 입력으로 교체한다.

실행:
```bash
python -m labs.video_classification.demo
```
