# SUVIS 어드민 대시보드 + 멀티에이전트 진행 상황

컨텍스트가 끊길 경우를 대비한 재개용 메모. 완료된 작업은 상세 로그 대신
**위치만** 남긴다(중복 기록 방지). 관련 상세 지시서:
- `suvisdev/_docs/RBAC_agent_dashboard.md` (RBAC + 어드민 대시보드 H0~H4)
- `suvisdev/apps/ontology/_docs/00_COMMON_conventions.md` + `01~08_*.md` (에이전트별 지시서)

---

## 완료됨 (상세는 각 문서 참고, 여기선 재기록 안 함)

- **어드민 대시보드**: 홈/사용자/앱관리/통계/캘린더/설정 전 화면 구현 + 실 연동
  (`suvis/app/admin/*`, `suvis/lib/admin-*-api.ts`). RBAC 가드(`require_admin`,
  `AdminAuthGate`)까지 포함.
- **01(이미지 분류, 포스터→장르)**: H0~H6 전체 완료. `01_image_classifier_agent.md` §7.
- **07(Echo, 감정분석)**: H0~H6 전체 완료(NSMC 기반, val acc 87.75%).
  `07_sentiment_analysis_agent.md` §5~§10.
- **02~08 H0 스캐폴딩**: 포트/인터페이스 껍데기 7개 태스크 전부 생성 완료
  (실제 추론 어댑터는 없음 — 아래 "진행 중" 참고).

---

## 진행 중 / 다음에 할 일

### 1. 06(Sentinel, 이상 탐지) — H4(포트 통합)부터 재개

방향 조사·전환은 완료, **구현은 전혀 안 됨**(H0 스캐폴딩 4파일만 존재,
router·DI provider·실제 어댑터 없음 — 2026-07-23에 직접 확인). 근거 전체는
`06_anomaly_detection_agent.md` §5~§6.6.

**결정된 방향**:
- PatchCore(anomalib)로 "이상=포스터가 아닌 이미지"를 시도했으나 AUROC 0.44
  (신호 없음)로 실패 → **CLIP 제로샷**(즉석 검증 AUROC 0.8844, `openai/clip-vit-base-patch32`)으로 전환.
- 화질 저하(blur)는 PatchCore 대신 **Laplacian variance**(정상 232장을
  256x256 정규화 후 계산한 하위 5퍼센타일 임계값 **345.77**, 합성 블러
  100% 분리)로 분리.
- PatchCore는 Phase A(MVTec AUROC 1.0) 결과만 구현 검증 근거로 남기고
  포스터 도메인에서는 기각(재사용 안 함).

**H4에서 실제로 만들어야 할 것** (현재 존재/미존재 확인 완료):

| 파일 | 상태 | 할 일 |
|------|------|------|
| `app/dtos/anomaly_detection_dto.py` | 있음(구식) | `AnomalyResult`가 지금 PatchCore 가정(단일 `anomaly_score: float`, `is_anomaly: bool`, `heatmap_b64: str`)으로 돼 있음 — CLIP·Laplacian은 히트맵을 안 만들고 신호가 2개(포스터 여부 / 블러 여부)라 **DTO 재설계 필요**. 예: `is_poster: bool`, `poster_confidence: float`, `is_blurry: bool`, `sharpness_score: float` |
| `app/ports/output/anomaly_detection_port.py` | 있음(구식) | 위 DTO 변경에 맞춰 시그니처 수정 |
| `app/ports/input/anomaly_detection_use_case.py` | 있음(구식) | 동일 |
| `app/use_cases/anomaly_detection_interactor.py` | 있음(구식) | **미결정 사항(사용자 확인 필요)**: 포트 1개(`AnomalyDetectionPort.detect()`가 내부에서 CLIP+Laplacian 둘 다 호출) vs 포트 2개(`PosterClassifierPort` + `ImageQualityPort`를 interactor가 조합) — 헥사고날 원칙(단일 책임)상 후자가 더 맞을 수 있음. **H4 착수 전에 결정하고 시작할 것.** |
| `adapter/outbound/resource_adapters/clip_poster_classifier/` | 없음, 신규 | CLIP 어댑터. `adapter/outbound/resource_adapters/echo_sentiment/echo_sentiment_adapter.py`와 동일하게 **호출당 로드→추론→언로드** 패턴 따를 것(00_COMMON 관례) |
| Laplacian variance 어댑터 | 없음, 신규 | opencv만 쓰는 경량 체크라 로드/언로드 불필요 — 위치는 CLIP과 같은 폴더 or `image_quality/`로 분리할지 결정 필요 |
| `dependencies/anomaly_detection_provider.py` | 없음, 신규 | `echo_sentiment_provider.py`와 동일 패턴 |
| `adapter/inbound/api/v1/anomaly_detection_router.py` | 없음, 신규(H5) | `sentiment_analysis_router.py`와 동일 패턴, `POST /api/vision/anomaly/detect` 급 |
| `adapter/inbound/mcp/anomaly_detection_mcp_server.py` | 없음, 신규(H5) | `image_classifier_mcp_server.py`/`sentiment_analysis_mcp_server.py`와 동일 패턴, HTTP만 호출 |

**임계값 하드코딩 위치**: Laplacian 345.77은 지금 스크립트 실행 결과로만
존재(`scripts/compute_sentinel_blur_threshold.py` 출력) — 어댑터 코드에
상수로 박아넣을지, 설정 파일로 뺄지도 H4에서 정할 것.

**VRAM 관점**: CLIP-ViT-B/32는 가벼워서(H4 시점 실측 필요하지만) 이 두
체크는 기존 PatchCore/EXAONE만큼 무겁지 않을 가능성이 높음 — 그래도 H1
관례(VRAM 실측 없이 코드 작성 금지, `00_COMMON` §4)는 그대로 지킬 것.

### 2. VRAM 정책 (확정 — 앞으로 모든 파인튜닝에 적용)

`00_COMMON_conventions.md` §1.1에 명문화.

- `lora-server`(EXAONE-3.5-2.4B AWQ, mova 채팅용)가 상시 기동, 부팅마다
  자동 시작 → **모든 학습 전 `systemctl --user stop lora-server`**, 학습
  후 `start` + `curl localhost:8200/health` 복구 확인 필수.
- **`nvidia-smi` free 수치만 믿고 학습 시작하지 말 것** — 같은 세션에서도
  같은 프로세스에 290MB↔7975MB로 크게 다른 값을 보고한 사례 확인됨(WSL2
  계측 불안정 추정, 재시작 정황 없음).

### 3. 02~08 적합성 감사 반영 (2026-07-23)

06의 실패(기법을 먼저 정하고 용도를 나중에 붙임)를 기준으로 전체 재감사.
근거: `00_COMMON_conventions.md` §8.

| # | 이름 | 상태 |
|---|------|------|
| 02 | Argus(객체 검출) | 보류 — 용도 위험/데이터 불확실, 제품 결정 전까지 착수 안 함 |
| 03 | Loom(분할) | 보류 — gildle 결빙 재정의 검토했으나 이미지 수집 경로 미확정(`03_semantic_segmentation_agent.md` §5) |
| 04 | Atlas(자세 추정) | **제외** — mova/gildle에 용도 자체가 없음(문서 상단 배너 처리, 삭제는 안 함) |
| 05 | Prisma(이미지 생성) | 보류 — 용도 불확실 + 하드웨어 위험(SD1.5 LoRA와 lora-server 상시 점유 겹침) |
| 06 | Sentinel(이상 탐지) | 위 1번 참고 — 진행 중 |
| 07 | Echo(감정분석) | 완료 |
| 08 | Chronos(영상 분류) | **제외** — mova/gildle에 용도 자체가 없음(문서 상단 배너 처리) |

**우선순위**: Echo(완료) → Sentinel(H4~ 재개) → 나머지(02·03·05)는 각자
표에 적힌 전제조건(제품 결정/이미지 수집 경로/VRAM 여유)이 풀리기 전까지
착수 안 함.

### C. 알려진 기존 이슈 (이번 범위 밖, 별도 처리 필요)

- `/admin/dispatch`, `/admin/harvester` 백엔드 API 자체에 인증이 전혀
  없음 — `AdminAuthGate`는 프론트 URL 접근만 막을 뿐, 백엔드 엔드포인트를
  직접 호출하면 그대로 뚫림. 필요시 해당 라우터들에도 `require_admin` 추가.
- `apps/mova/tests/test_import_interactor.py` 2건, `test_llm_error_handling.py`
  — 이번 작업과 무관한 기존 실패.
