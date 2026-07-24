# 작업 일지

날짜별로 그날 한 작업·수정·오류·데이터를 기록한다. **최신 날짜가 맨 위**로
오게 추가한다(새 항목은 이 안내 바로 아래에 삽입). 요약용 재개 메모는
`SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(현재 상태·다음 할 일)를 따로 쓰고,
이 파일은 **그날그날 실제로 있었던 일의 상세 기록**(무엇을 왜 했는지,
어디서 막혔는지, 데이터가 어떻게 바뀌었는지)에 집중한다.

**항목 템플릿**:
```
## YYYY-MM-DD

### 작업 내용
- 무엇을 했는지, 왜 했는지(계기)

### 수정/구현
- 만들거나 고친 파일·코드, 핵심 변경점

### 오류·막힌 점
- 무슨 에러가 났는지, 원인, 어떻게 해결했는지(해결 안 됐으면 그것도 기록)

### 데이터
- 데이터셋 출처·규모·라벨 변경 등

### 산출물
- 커밋 해시, 문서 갱신 위치 등
```

---

## 2026-07-24

### 작업 내용
- 06(Sentinel, 이상 탐지) **H4(추론 어댑터) + H5(HTTP API + MCP tool) 구현**
  — H3까지의 방향 전환(CLIP 제로샷 + Laplacian variance)을 실제 코드로
  반영하고 MCP tool까지 노출.

### 수정/구현

**1) 06 Sentinel H4**
- 미결정 사항(포트 1개 vs 2개) 확인 후 **포트 1개 통합**으로 확정하고 진행.
- `app/dtos/anomaly_detection_dto.py`: `AnomalyResult`를 PatchCore 가정
  (`anomaly_score`/`is_anomaly`/`heatmap_b64`)에서 `is_poster`/
  `poster_confidence`/`is_blurry`/`sharpness_score`로 재설계.
- `adapter/outbound/resource_adapters/sentinel_anomaly/sentinel_anomaly_adapter.py`
  (신규): CLIP 제로샷(`openai/clip-vit-base-patch32`, 임계값 0.5)과
  Laplacian variance(256x256 정규화, 임계값 345.77)를 한 어댑터에서 순서대로
  호출. CLIP은 `echo_sentiment_adapter.py`와 동일하게 호출당 로드→추론→언로드.
- `dependencies/anomaly_detection_provider.py`(신규), port/interactor
  docstring을 PatchCore→CLIP/Laplacian으로 갱신.
- `test/test_sentinel_anomaly_adapter.py`(신규, `@pytest.mark.gpu`) —
  `test/good`·`test/blur` 샘플로 포트→VO 반환 검증.

**2) 06 Sentinel H5**
- `adapter/inbound/api/v1/anomaly_detection_router.py`(신규):
  `image_classifier_router.py` 패턴, `POST /sentinel/detect`(전체 경로
  `/api/vision/sentinel/detect`), `UploadFile` 입력.
- `adapter/inbound/mcp/anomaly_detection_mcp_server.py`(신규):
  `image_classifier_mcp_server.py` 패턴, `detect_anomaly(image_b64) -> dict`
  tool이 HTTP로 라우터 호출.
- `adapter/inbound/api/__init__.py`: `vision_router`에
  `anomaly_detection_router` 등록.
- `scripts/test_mcp_sentinel_client.py`(신규): stdio MCP 클라이언트로 tool
  목록 + 호출 검증.
- 검증: 백엔드 리빌드+재기동 후 `app.routes`에 경로 등록 확인,
  MCP tool 호출 2회 성공(good→`is_poster:true`, blur→`is_blurry:true`),
  VRAM 2863→3014MB(호출당 +30~120MB로 CLIP 가중치 누적 아님 → 로드-언로드
  정상), lora-server 정상. GATE_H5_PASS.

**3) AWS S3 매니저(Tank) 신설** — 향후 AWS 이전(이미지/객체를 S3 URL로
전달, ontology 00_COMMON §6) 대비. mova/gildle 도메인과 무관한 인프라 작업.
- `core/matrix/aws_tank_s3_manager.py`(신규): `Tank` 클래스. IAM 액세스 키를
  하드코딩하지 않고 Keymaker에서 받아 boto3 S3 클라이언트 생성. 키 없으면
  `ready=False` + 클라이언트 접근 시 graceful `RuntimeError`. 메서드:
  `list_buckets`/`upload_bytes`/`download_bytes`/`generate_presigned_url`.
  모듈 싱글턴 `tank`/`get_tank()`(Keymaker 패턴).
- `core/matrix/vauly_keymaker_secret_manager.py`: AWS 자격증명·리전·버킷을
  Keymaker가 단일 관리하도록 `aws_access_key_id`/`aws_secret_access_key`/
  `aws_region`/`vision_s3_bucket` 속성 추가. Tank는 `os.getenv`를 직접 읽지
  않고 이 값을 받아 씀(사용자 요청으로 os.getenv 직접 접근 → Keymaker 경유로
  리팩터).
- `.env.example`: AWS IAM 액세스 키 블록 추가(`AWS_ACCESS_KEY_ID`/
  `AWS_SECRET_ACCESS_KEY`/`AWS_REGION`/`VISION_S3_BUCKET`). 변수명은 기존
  `vision_s3_repository.py`(boto3 기본 자격증명 체인)와 맞춰 재사용.
- 검증: 컨테이너에서 import + graceful degradation(키 없을 때 `ready=False`,
  클라이언트 접근 에러) 확인. 실 버킷 연동은 키 주입 후 별도.

### 오류·막힌 점
- **로컬 `.venv`/`.venv-exaone`에 pytest/opencv 없음** — 이 프로젝트의 실제
  런타임 의존성(`transformers==4.47.1`, `opencv-python`, `pytest`)은
  `requirements.txt` 기반으로 `suvisdev-backend-1` 도커 이미지에만 있고,
  compose에는 코드 전체가 아니라 `datasets`·`resources/crawled`만 바인드
  마운트돼 있어 새 파일이 컨테이너에 자동 반영 안 됨 → `docker cp`로
  변경/신규 파일 6개를 컨테이너에 직접 복사해 그 안에서 pytest 실행,
  둘 다 PASSED. VRAM은 호출 전후 2879MB로 동일(로드-언로드 정상 확인),
  lora-server(`:8200/health`) 정상 유지.

### 산출물
- 문서 갱신: `apps/ontology/_docs/06_anomaly_detection_agent.md` §6.7(H4)·
  §6.8(H5) 신규, `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` H4·H5 완료로
  갱신(스테일해진 H4 체크리스트·미결정 표 제거, 다음은 H6).
- 백엔드 이미지 리빌드(H5 코드 반영) — `suvisdev-backend-1` 재기동됨.
- Sentinel H4·H5는 커밋/푸시/머지 완료(`df5a56b`, main 반영). S3 매니저(Tank)
  관련 3파일은 아직 커밋 안 함(사용자 확인 전).

---

## 2026-07-23

### 작업 내용
- 06(Sentinel, 이상 탐지) H3 디버깅 이어서 진행 — 이전 세션이 도중에
  끊긴 상태(포스터/노이즈/회색 점수 순서가 정보량 순서와 일치한다는 관찰까지만
  하고 중단)에서 재개.
- PatchCore(anomalib) 기반 접근을 근본 원인까지 추적 → 실패로 판정 →
  CLIP 제로샷 + Laplacian variance로 방향 전환.
- 02~08 나머지 비전 에이전트 전체에 대해 "용도/데이터/하드웨어" 적합성
  사전 감사(06의 실패에서 얻은 교훈 적용).
- VRAM 점유 정책 확정(실측 기반).
- 관련 문서·재개 메모 정리, git 커밋/푸시/머지 2회.

### 수정/구현

**1) additive/subtractive anomaly 원인 규명**
- `scripts/diagnose_sentinel_per_defect.py`(기존) 재실행 → normal/blur/black_bar/watermark
  그룹별 AUROC 분해(blur 0.573, black_bar 0.510, watermark 0.484).
- `scripts/diagnose_sentinel_feature_norm.py`(신규) — memory bank 진입 전
  patch embedding의 L2 norm을 그룹별로 추출해 NN-distance와 대조. blur만
  전역·균일하게 정상 분포 영역을 벗어나 잘 잡히고, black_bar(국소)·watermark
  (저강도)는 거의 안 잡힌다는 걸 확인(`06_anomaly_detection_agent.md` §5.3).

**2) "이상=포스터가 아닌 이미지" 재정의 시도 1차 (실패)**
- `scripts/prepare_sentinel_nonposter_dataset.py`(신규) — TMDB API로
  backdrop(예고편 스틸)·cast profile(인물 사진)·대체 포스터(textless/
  비주력 언어판) 수집.
- 사용자 지적 반영: (a) 종횡비 누출 방지 — Resize(256,256)이 종횡비를
  무시해 16:9 backdrop이 포스터보다 훨씬 심하게 찌그러지는 문제 →
  저장 전 전부 2:3 center crop. (b) 라벨 오류 — textless/비주력 언어판은
  TMDB 공식 포스터라 정상인데 처음에 "hard negative"로 잘못 라벨링 →
  `test/alt_poster_control`(위양성 대조군, 정상)로 재정의.
- `scripts/diagnose_sentinel_nonposter.py`(신규) — good/non_poster_easy/
  alt_poster_control 3그룹 점수 분포 + AUROC.
- 결과: AUROC 0.4429, 부트스트랩 95% CI [0.314, 0.566] → 0.5 포함 →
  "랜덤 이하"가 아니라 **"신호 없음"**(통계적으로 구분 불가). 수동
  pairwise 재계산으로 sklearn 라벨 극성 버그 아님도 확인.
- 결론: patch-level 텍스처 비교는 "포스터냐 아니냐"라는 전역적·구성적
  질문에 구조적으로 안 맞음 → 이 접근 기각.

**3) 방향 전환 — CLIP 제로샷 + Laplacian variance**
- `scripts/diagnose_sentinel_clip_poster_classifier.py`(신규) —
  `openai/clip-vit-base-patch32` 제로샷, 파인튜닝 없이 기존 라벨셋으로
  즉시 검증 → AUROC 0.8844(PatchCore 0.44 대비 압도적 개선).
- `scripts/compute_sentinel_blur_threshold.py`(신규) — 정상 포스터
  232장(256x256 정규화)의 Laplacian variance 하위 5퍼센타일 = 345.77.
  합성 블러 25장 전부(100%) 임계값 아래로 분리.
- PatchCore/anomalib은 Phase A(MVTec bottle AUROC 1.0, 파이프라인 정합성
  검증)만 근거로 남기고 포스터 도메인에서는 기각.
- 전체 근거를 `apps/ontology/_docs/06_anomaly_detection_agent.md` §5~§6.6에
  기록. H4(포트 통합)는 아직 미착수 — 상세 다음 단계는
  `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` §1 참고.

**4) 02~08 적합성 감사**
- mova(포스터 1장/영화 + 텍스트뿐)·gildle(이미지 자체가 없는 지오/테이블
  도메인) ERD·코드를 직접 확인해 용도/데이터/하드웨어 3항목 판정.
- 04(Atlas, 자세 추정)·08(Chronos, 영상 분류) — mova/gildle 어디에도
  용도가 없어 **제외**. 해당 문서 상단에 배너만 추가(내용 삭제 안 함).
- 03(Loom, 분할) — gildle `HazardZone`(결빙구역)과 엮는 재정의 검토.
  결빙 자체는 Cityscapes/Mapillary에 클래스가 없어(계절성 현상 vs 구조적
  클래스) 기각. 대안(보도/차도 구조 분할)은 라우팅 반영 방법은 명확하나
  이미지 수집 경로(gildle의 Kakao 연동은 지오코딩뿐, 로드뷰 API 아님)가
  미확정이라 **보류**(착수 안 함). `03_semantic_segmentation_agent.md` §5.
- 02(Argus)·05(Prisma) — 용도 위험/불확실이라 보류(제외는 아님).
- 감사 표 전체를 `00_COMMON_conventions.md` §8에 기록.

**5) VRAM 점유 정책 확정**
- `nvidia-smi`, `ollama ps`, `systemctl --user status lora-server`로
  실측. `00_COMMON_conventions.md` §1.1에 정책 명문화(아래 오류 항목 참고).

**6) 재개 메모 정리**
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 전면 재작성 — 완료된 항목(어드민
  대시보드, 01, 07)은 상세 삭제하고 위치만 남김, 06 H4의 다음 할 일은
  파일 단위로 구체화(DTO 재설계 필요성, 미결정 설계 질문 등).

**7) 작업 일지 체계 신설**
- 이 파일(`_docs/WORK_LOG.md`) 신설 — 날짜별 상세 작업 기록(재개 메모와
  역할 분리: 재개 메모=현재 상태 요약, 작업일지=그날 있었던 일 상세).
- `CLAUDE.md`에 규칙 추가: **세션이 끝나기 전에 이 파일에 기록**. 중간에
  "커밋 시점을 트리거로" 잠깐 바꿨다가 사용자가 다시 세션 종료 기준으로
  정정(최종: 세션 종료 트리거).

### 오류·막힌 점

- **정규화 클리핑 버그 재발**: `diagnose_sentinel_nonposter.py` 1차 작성 시
  `PostProcessor(enable_normalization=False)`를 빠뜨려 min-max 정규화가
  다시 켜진 채로 실행 → score가 0.98~1.000에 몰려 AUROC가 0.4369라는
  의미 없는 값이 나옴(§5.1~5.2에서 이미 확인했던 문제인데 신규 스크립트에
  재도입). `PostProcessor(enable_normalization=False)` 추가 후 재실행해
  0.4393(raw score 기준)으로 정정 — 결론(신호 없음)은 안 바뀜.
- **TMDB `include_image_language` 필터 버그**: 대체 포스터(altlang) 수집 시
  API 요청 자체를 `include_image_language: "null,en,ko"`로 제한해놓고
  "en/ko가 아닌 포스터"를 찾으려 해서 항상 0건. `ja,zh,fr,de,es,it,ru`
  추가해 해결(15/15 확보).
- **정상 포스터 카운트 assert 실패**: `compute_sentinel_blur_threshold.py`
  초안이 `tmdb-*.jpg` 패턴만 찾아 190장(실제는 232장, 일부는 슬러그
  파일명이라 tmdb- 접두사 없음)에서 assert 실패. 패턴을 `*/*/*.jpg`로
  넓혀 해결.
- **컨테이너/호스트 데이터 비동기화**: `apps/ontology/resources/sentinel_poster`가
  컨테이너 안에서는 bind mount가 아니라 이미지 빌드 시점 복사본이라는 걸
  뒤늦게 발견 — 컨테이너 안에서 생성한 `non_poster_easy`/`alt_poster_control`가
  호스트에 자동 반영 안 됨. `docker cp`로 양방향 수동 동기화(스크립트는
  host→container, 데이터 산출물은 container→host)하는 방식으로 우회.
  디렉토리 이름을 `non_poster_hard`→`alt_poster_control`로 바꿀 때도 호스트에
  먼저 `mv`했다가 파일이 없어서 실패 → 컨테이너에서 먼저 rename 후
  `docker cp`로 새로 가져오는 순서로 정정.
- **`nvidia-smi` 계측 불안정**: 같은 세션 안에서 같은 `lora-server` 프로세스에
  대해 290MB(유휴)와 7975~7988MB(피크 직후로 추정)로 크게 다른 값이 나옴 —
  재시작 로그는 없어서 WSL2 GPU 패스스루 계측 문제로 판단. VRAM 정책에
  "free 수치만 믿지 말 것" 명시.

### 데이터

- `apps/ontology/resources/sentinel_poster/` 구성(2026-07-23 기준):
  - `train/good`: 190장(정상 포스터, 기존)
  - `test/good`: 42장(정상 포스터, 기존)
  - `test/blur`·`test/black_bar`·`test/watermark`: 각 25장(합성 손상, Phase B 잔존 — 스코프 제외됐지만 삭제 안 함, blur 임계값 검증용으로 재사용)
  - `test/non_poster_easy`: 40장(신규, backdrop 20 + cast profile 20, TMDB, 2:3 center crop)
  - `test/alt_poster_control`: 30장(신규, textless 15 + 비주력 언어판 15, TMDB, 2:3 center crop)
  - 소스: `apps/ontology/resources/genre_classifier_train`(232장)의 TMDB id 190개 재사용

### 산출물

- 커밋 `bac5565` — 06 additive/subtractive 원인 규명 + 범위 재정의(스크립트 6개 신규, 데이터셋 확장, 문서 §5~§6)
- 커밋 `e420d3f` — 02~08 감사 반영(00_COMMON §1.1/§8, 03/04/08 문서 수정)
- 둘 다 `suvisdev` → `main` fast-forward 머지 + 푸시 완료
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 전면 갱신(미커밋, 사용자 확인 대기)
