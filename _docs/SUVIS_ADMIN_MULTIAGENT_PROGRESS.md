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
- **06(Sentinel, 이상 탐지)**: H0~H6 전체 완료(CLIP 제로샷 포스터 판별 +
  Laplacian 블러, `/vision/upload` 게이트). `06_anomaly_detection_agent.md`
  §5~§6.9. 미결 백로그는 아래 "진행 중/다음" 1번.
- **02~08 H0 스캐폴딩**: 포트/인터페이스 껍데기 7개 태스크 전부 생성 완료
  (실제 추론 어댑터는 없음 — 아래 "진행 중" 참고).

---

## 진행 중 / 다음에 할 일

### 1. 06(Sentinel, 이상 탐지) — H0~H6 전체 완료 (2026-07-24)

방향 조사·전환·**H4(추론 어댑터)·H5(HTTP API + MCP tool)·H6(업로드 게이트 통합)
완료**. 포트 1개 통합, DTO(`AnomalyResult`)·어댑터(`sentinel_anomaly_adapter.py`,
CLIP 제로샷+Laplacian variance)·provider·라우터(`/api/vision/sentinel/detect`)·
MCP(`detect_anomaly`)까지 만들고 stdio MCP 클라이언트로 전체 체인 검증.

**H6 용도 = `POST /vision/upload` 업로드 게이트**(소거법 — harvester는 텍스트만
수집, TMDB는 URL 참조라 항상 포스터, lora-server는 텍스트 생성기, Prisma 미구현.
업로드만 입력이 불확실). 블러=하드 게이트(400), is_poster=소프트 플래그(경고+어드민
오버라이드 여지). 임계값은 `VisionInteractor`가 raw 값으로 소유. GATE_H6 3경로
통과(good/blur/non-poster). 상세: `06_anomaly_detection_agent.md` §6.7~§6.9.

**남은 미결(백로그)**: ① 소프트 플래그 저장 지속화 + 어드민 오버라이드 엔드포인트
(저장 계층 정리 후 — S3 배선인데 AWS 미연결, DB 폴백 `VisionRepository` 미배선).
② `vision_use_case`의 app→adapter 순환 임포트(WORK_LOG 2026-07-24 백로그).

방향 조사·전환 근거 전체는 `06_anomaly_detection_agent.md` §5~§6.6.

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
| 06 | Sentinel(이상 탐지) | **완료**(H0~H6, `/vision/upload` 게이트) — 미결 백로그는 1번 |
| 07 | Echo(감정분석) | 완료 |
| 08 | Chronos(영상 분류) | **제외** — mova/gildle에 용도 자체가 없음(문서 상단 배너 처리) |

**우선순위**: Echo(완료) → Sentinel(완료) → 나머지(02·03·05)는 각자
표에 적힌 전제조건(제품 결정/이미지 수집 경로/VRAM 여유)이 풀리기 전까지
착수 안 함.

### C. 알려진 기존 이슈 (이번 범위 밖, 별도 처리 필요)

- `/admin/dispatch`, `/admin/harvester` 백엔드 API 자체에 인증이 전혀
  없음 — `AdminAuthGate`는 프론트 URL 접근만 막을 뿐, 백엔드 엔드포인트를
  직접 호출하면 그대로 뚫림. 필요시 해당 라우터들에도 `require_admin` 추가.
- `apps/mova/tests/test_import_interactor.py` 2건, `test_llm_error_handling.py`
  — 이번 작업과 무관한 기존 실패.
