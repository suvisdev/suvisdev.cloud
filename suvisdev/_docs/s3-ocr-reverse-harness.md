# vision_ocr_scan 하네스

## 목적

Flutter(susu)로 촬영된 이미지가 S3에 저장된 상태에서, 웹의 지정 화면 진입 시
서버가 그 이미지들을 읽어 OCR로 텍스트를 추출하고 `[{image_url, extracted_text}]`
목록을 반환하는 기능을, hexagonal clean 규칙대로 `apps/ontology`(vision 계열)에
추가한다.

## 스코프

- **포함**: S3 이미지 스캔, OCR 추출, 웹 응답까지의 read 경로
- **제외**: Flutter 촬영 → S3 업로드 자체, S3 이벤트 push 트리거
- **결정 대기**(아래 "결정 필요" 참조): 업로드 경로를 S3로 돌릴지, 스캔 대상을
  어떻게 좁힐지는 이 read 경로 설계보다 먼저 확정해야 한다 — "제외"라고 해서
  무관한 게 아니라, read 경로의 전제 조건이다.

---

## 개념 정정: inbound/outbound

hexagonal에서 in/out은 **데이터 방향이 아니라 제어(호출) 방향**으로 가른다.

| 구분 | 정의 | 이 기능에서 |
|------|------|------------|
| inbound (driving) | app을 *호출하는* 쪽 | 웹/HTTP router |
| outbound (driven) | app이 *호출하는* 쪽 | S3 read, OCR engine |

"S3 → app → 웹"은 데이터 흐름이 맞지만 제어는 여전히 웹 → app이다. "화면 진입 시
자동"은 프론트 mount 시점의 GET 호출이지 S3가 app을 깨우는 게 아니다.

→ **S3, OCR 둘 다 outbound port. 트리거는 inbound(웹).**

---

## 사전 확인: 지금 이 저장소의 실제 상태 (착수 전 필독)

아래 세 가지는 원안 초안과 실측 코드가 어긋나는 지점이라 먼저 바로잡는다.

### 1. Tank는 금지 대상이 아니라 재사용 대상이다

`core/matrix/aws_tank_s3_manager.py`의 `Tank`는 boto3 **기본 자격증명 체인**만
쓴다(`region_name`만 넘기고 키를 명시하지 않음). 그래서:

- 로컬: `.env`의 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`를 기본 체인이 집음
- EC2: 인스턴스 IAM Role을 기본 체인이 자동으로 집음

`VisionS3Repository.save_image`(`apps/ontology/adapter/outbound/repositories/
vision_s3_repository.py:33-48`)가 이미 `get_tank()`로 업로드를 구현해 뒀다.
**"Tank는 명시적 키라 EC2 IAM Role 대응이 안 된다"는 전제는 틀렸다** — 새 outbound
adapter(`S3ReadPort` 구현체)도 동일하게 `Tank`를 재사용한다. `download_bytes`,
`generate_presigned_url`도 이미 `Tank`에 있다(69-98행). 여기 없는 건 `list_objects`
하나뿐이다.

### 2. 지금 배선은 S3가 아니라 DB(VisionRepository)를 쓴다

`apps/ontology/dependencies/vision_provider.py:10-13`:

```python
def get_vision_repository() -> VisionPort:
    # S3(VisionS3Repository)는 AWS 자격증명 미연결로 보류 — 소프트 플래그
    # 지속화까지 필요해져 DB 폴백(VisionRepository)을 기본 배선으로 전환.
    return VisionRepository()
```

이 주석의 전제("AWS 자격증명 미연결")는 2026-08-03 media 앱(`apps/media`, susu
카메라 → S3) 커밋으로 이미 깨졌다 — S3 자격증명은 연결돼 있다. 하지만 이 read
하네스가 스캔할 이미지가 **어느 경로로 S3에 들어오는지**는 별개 결정이다:

- (A) `POST /vision/upload`의 기본 배선을 `VisionS3Repository`로 바꾼다 →
  `VisionS3Repository.update_poster_flag`가 `NotImplementedError`라서 어드민
  소프트 플래그 오버라이드 기능이 깨진다(52-55행). 되돌리려면 별도 결정 필요.
- (B) vision 업로드는 DB 배선 그대로 두고, **media 앱이 이미 쓰고 있는 S3 경로**
  (`media/{user_id}/...` prefix)를 이 하네스가 읽는다. 그러나 media 앱은
  `apps/ontology`의 spoke가 아니라 완전히 별개 앱이라 소유권·인증 모델이 다르다.
- (C) 이 하네스 전용으로 새 업로드 표면을 만들지 않고, `vision/` prefix(flat,
  `VisionS3Repository.save_image`가 현재 쓰는 키)를 그대로 스캔 대상으로 삼되,
  배선 전환(A)은 다음 이터레이션으로 미룬다.

**결정 필요 항목에 추가함.** 이 문서는 (C)를 기본 가정으로 설계를 적되, 실제
착수 전 확정한다.

### 3. "폴더" 개념은 지금 코드에 없다

`VisionS3Repository.save_image`의 키는 `vision/{YYYYMMDD_HHMMSS}_{filename}`
평면 구조다(35행) — 카테고리별 하위 폴더(`receipts/` 등)를 나누는 로직이 없다.
`GET /vision/ocr/scan?folder=<prefix>`를 그대로 쓰려면:

- 업로드 경로를 손대 폴더 세그먼트를 추가하거나(스코프의 "업로드 경로 미수정"과
  충돌),
- 아니면 1차 구현은 `folder` 파라미터 없이 `vision/` prefix 전체를 스캔하고,
  폴더 분리는 후속 이터레이션으로 미룬다.

**1차 구현 권장: `folder` 파라미터를 생략하고 고정 prefix(`vision/`)를 스캔.**
폴더링이 실제로 필요해지면 그때 업로드 경로 변경을 별도 스코프로 연다.

---

## 아키텍처 흐름

```
[제어 방향] ─────────────────────────────▶
웹 mount → GET /vision/ocr/scan
        │
   ┌────▼─────────────┐        ┌── outbound ────────────┐
   │ inbound: router  │        │ S3ReadPort (list+get   │─▶ S3 (vision/ prefix)
   │  schema→query    │        │   +presign)             │
   └────┬─────────────┘        │ OcrPort (bytes→text)    │─▶ OCR engine
        ▼                      └──────────▲─────────────┘
   VisionInteractor.scan_and_ocr ─(port)──┘
        │  OcrScanResult DTO 조립
        ▼  router가 응답 schema로 직렬화
   [{ image_url, extracted_text }, ...] ─▶ 웹 렌더
◀────────────── [데이터 방향: S3 → app → web] ──────────────
```

---

## 레이어 매핑 (Schema→DTO→App→VO/Entity 준수)

이 저장소의 실제 vision 레이어 구조(`vision_router.py` / `vision_port.py` /
`vision_interactor.py` / `vision_dto.py`)를 그대로 따른다.

### 1. inbound / `vision_router.py`

- `GET /vision/ocr/scan` 신설(기존 `vision_introduce_router`에 추가, 새
  라우터를 만들지 않는다 — 지금 vision에 라우터가 하나뿐이다).
- 이 라우터의 기존 엔드포인트(`/myself`, `/upload`)는 무인증이고
  `/{upload_id}/poster-flag`만 `require_admin`이 붙어 있다(`vision_router.py:40-53`).
  신규 스캔 엔드포인트의 인증 여부는 **결정 필요**(아래 참조) — 결정 없이
  무인증으로 두지 않는다(`.claude/rules/security/auth.md` §4: 무인증 근거를
  주석에 남길 것).
- 쿼리 파라미터가 필요하면 `VisionOcrScanSchema`(adapter, `vision_schema.py`에
  추가) → `VisionOcrScanQuery`(app DTO, `vision_dto.py`에 추가) 변환은 반드시
  router에서. app 포트가 adapter 스키마를 직접 받지 않는다(DIP 위반 재발 금지 —
  아래 "주의점" 참조).
- 응답: `OcrResult` VO list → 새 응답 schema(`vision_schema.py`)로 직렬화.

### 2. app / `VisionInteractor`에 `scan_and_ocr` 메서드 추가

기존 `VisionInteractor`(`vision_interactor.py`)는 `VisionPort` + `AnomalyDetectionPort`
두 outbound port를 조합하는 오케스트레이션만 한다(로직은 정책 임계값 정도). 같은
패턴으로:

1. `VisionPort.list_scan_targets()` (신규 추상 메서드) → key 목록
2. key별 `VisionPort.get_bytes(key)` (신규) → 이미지 bytes,
   또는 `VisionPort.presign_url(key)` (신규) → 웹이 직접 fetch할 URL
3. `OcrPort.extract(bytes)` (신규 포트) → 텍스트

OCR 호출은 `asyncio.to_thread`로 감싼다 — `upload_image`가 `AnomalyDetectionPort.detect`를
감싸는 것과 동일한 이유(동기 무거운 추론이 이벤트 루프를 막지 않게, `vision_interactor.py:61`).

> `VisionPort`는 현재 `introduce_myself` / `save_image` / `update_poster_flag`
> 세 추상 메서드뿐이다(`vision_port.py`). 여기에 read 계열 메서드를 추가하면
> **`VisionRepository`(DB 구현체)에도 같이 구현해야** `TypeError` 없이 인스턴스화된다
> (`.claude/rules/testing.md` §4). DB 구현체는 스캔 대상이 없으므로 빈 목록을
> 반환하거나 `NotImplementedError`(기존 `update_poster_flag`의 S3 쪽과 대칭되는
> 패턴)로 명시한다.

### 3. VO/Entity

- 신규 frozen VO: `OcrResult(image_key, image_url, extracted_text, confidence)`
  — `vision_dto.py`에 `AnomalyResult`(`anomaly_detection_dto.py`)와 같은 스타일로
  추가.
- 지속화(옵션 B 선택 시)는 `VisionUploadOrm`에 `ocr_text` 컬럼 확장 — 절차는
  아래 마이그레이션 절 참조.

### 4. outbound adapter

| Port | Adapter | 비고 |
|------|---------|------|
| `VisionPort`(확장) | 기존 `VisionS3Repository` 확장 | `Tank` 재사용(위 "사전 확인 1" 참조). `Tank`에 `list_objects` 메서드가 없으므로 **`Tank`에 먼저 추가**해야 한다(`core/matrix/aws_tank_s3_manager.py`) |
| `OcrPort` | 신규 `ocr_adapter.py` | `sentinel_anomaly_adapter.py` 구조 복제(포트 하나, `__init__`에 `device` 옵션, 호출당 로드/추론/언로드) |

`Tank.list_objects` 추가 시그니처 제안(기존 메서드 스타일과 통일):

```python
def list_objects(self, prefix: str, *, bucket: str | None = None) -> list[str]:
    """prefix로 시작하는 객체 key 목록(list_objects_v2 기반)."""
```

---

## OCR 엔진 후보 (Port 뒤 스왑 대상)

| Engine | 실행 | 한국어 | 배치 |
|--------|------|--------|------|
| Tesseract (pytesseract) | CPU | 인쇄체 약함 | EC2 경량 |
| PaddleOCR / EasyOCR | GPU 유리 | 좋음 | 집 노트북/데스크톱 GPU |
| Google Vision / Gemini | API | 최상 | AWS=Gemini 노선과 일관 |

→ **DIP로 `OcrPort` 하나 두고 EC2=Gemini 어댑터, 집=EasyOCR 어댑터 주입 스왑.**
집 환경은 `lora-server`(EXAONE-2.4B AWQ)가 상시 VRAM을 점유하므로(`CLAUDE.md`
"주의사항"), GPU 기반 OCR을 로컬에서 돌릴 땐 `sentinel_anomaly_adapter.py`처럼
호출당 로드→추론→언로드 패턴을 따르거나, 학습 전 `lora-server` 정지 절차와
동일하게 리소스 경합을 고려한다.

---

## 결정 필요 (착수 전)

1. **OCR 엔진 1차 구현체** — Gemini / EasyOCR / Tesseract 중 어느 어댑터부터?
2. **스캔 대상 S3 경로** (위 "사전 확인 2, 3") — `vision/` prefix 그대로 스캔할지,
   업로드 배선을 S3로 전환할지, media 앱의 `media/{user_id}/` 경로를 참조할지.
3. **엔드포인트 인증 여부** — 무인증(`/upload`, `/myself`와 동일)으로 둘지,
   `require_admin`(`/poster-flag`와 동일)을 붙일지. 사진이 사용자 개인 소유
   데이터라면 무인증은 위험 — `.claude/rules/security/auth.md` 체크리스트 참조.
4. **지속화 여부**:
   - (A) 무저장 — 매 진입마다 OCR 재실행. 단순하나 API 비용/지연 발생
   - (B) `vision_uploads`에 `ocr_text` 캐시 컬럼 추가 — S3 key 기준 캐시.
     `20260729_0001_add_vision_upload_soft_flags.py`(poster_confidence 등 컬럼
     추가)와 동일한 절차.

---

## 웹 이미지 표시 방침

- 백엔드로 bytes 프록시 **금지**
- S3 outbound에서 **presigned GET URL** 발급(`Tank.generate_presigned_url`,
  이미 구현돼 있음, 기본 만료 1시간) → 브라우저가 S3 직접 fetch
- 응답 스키마: `{ image_url: <presigned>, extracted_text: str }`

---

## 참조 구현 (필수 정독)

| 파일 | 참조 이유 |
|------|-----------|
| `apps/ontology/adapter/outbound/resource_adapters/sentinel_anomaly/sentinel_anomaly_adapter.py` | outbound adapter 구조(호출당 로드/추론/언로드) |
| `apps/ontology/app/ports/output/anomaly_detection_port.py` | Port ABC 시그니처(단일 메서드) |
| `apps/ontology/adapter/inbound/api/v1/vision_router.py` | 기존 라우터에 엔드포인트 추가하는 방식, `require_admin` 적용 예 |
| `apps/ontology/adapter/outbound/repositories/vision_s3_repository.py` | `Tank` 사용법(기본 자격증명 체인) |
| `core/matrix/aws_tank_s3_manager.py` | `download_bytes`/`generate_presigned_url` 기존 구현, `list_objects` 추가 위치 |
| `alembic/versions/20260729_0001_add_vision_upload_soft_flags.py` | 컬럼 추가 마이그레이션 절차(리비전 체인은 `alembic history`로 최신 head 확인 — 2026-08-04 기준 최신 날짜 리비전은 `20260731_0001`) |

---

## 주의점

- **`.importlinter`의 hub-independence 계약**: `ontology`는 hub이고 다른 spoke
  앱을 import할 수 없다(`.importlinter` `[importlinter:contract:hub-independence]`).
  media 앱의 S3 경로를 참조하기로 하더라도 media 앱 모듈을 직접 import하지 않는다
  — 필요하면 `core.matrix`(공용 계층)를 경유한다.
- **app→adapter DIP 재발 금지** — 지난 DIP 사이클(2026-07)에서 `vision_schema`를
  삭제하고 DTO로 교체한 이력이 있다. 신규 포트 시그니처가 스키마가 아닌 DTO를
  받는지 반드시 확인.
- **push 모델 회피** — S3 event→SQS→websocket은 오버킬. pull(웹 GET) 유지.
- **업로드 경로 미수정** — Flutter→S3 자체는 건드리지 않는다. 다만 위 "사전 확인
  2, 3"에서 다룬 대로, 업로드가 지금 **어디로** 가고 있는지(DB vs S3, 어느 prefix)
  확인 없이는 read 경로가 스캔할 대상이 비어 있을 수 있다.

---

## 마일스톤

1. "결정 필요" 4개 확정
2. `Tank.list_objects` 추가(`core/matrix/aws_tank_s3_manager.py`)
3. `OcrPort` + `OcrResult` VO + (필요 시) `VisionOcrScanQuery` DTO
4. `ocr_adapter.py` 1차 구현체
5. `VisionPort`에 read 메서드 추가 → `VisionS3Repository`(신규 구현) +
   `VisionRepository`(DB 쪽 스텁, 빈 목록 또는 `NotImplementedError`)
6. `VisionInteractor.scan_and_ocr` 오케스트레이션 + `VisionUseCase`에 추상 메서드 추가
7. router + schema (+ 인증 가드)
8. (지속화 B 선택 시) 마이그레이션 `<오늘 날짜>_0001_add_vision_ocr_text.py`
   (`alembic history`로 현재 head 확인 후 `down_revision` 지정)
9. 테스트: `apps/ontology/test/`에 `test_vision_ocr_scan.py` — `_FakeTank`/
   `SimpleNamespace` fake `OcrPort`로 interactor 단위 테스트
   (`apps/media/tests/test_router.py`의 `_FakeTank` 패턴 참조)
