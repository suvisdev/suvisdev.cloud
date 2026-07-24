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
  §5~§6.9. 미결 백로그는 아래 "다음 / 남은 작업" 참고.
- **02~08 H0 스캐폴딩**: 포트/인터페이스 껍데기 7개 태스크 전부 생성 완료
  (실제 추론 어댑터는 없음 — 아래 "진행 중" 참고).

---

## 진행 중 (현재 액티브)

### 03(Loom, 시맨틱 분할) — 이미지 수집 경로 조사, 종료조건 합의 단계 (2026-07-24)

용도 재정의: 결빙(§5.1 기각) → **"보도 유무/폭"(계절 무관 구조 신호)**. 소비처는
실재 — `RouteWeightCalculator`가 `_near_hazard` 페널티 패턴처럼 "보도 없음/좁음"을
상시 페널티로 얹으면 됨. **단 구멍 2개**: (a) 소비 walk 그래프가 데모
(`sample_walk_graph.json` 4간선), OSM 운영 미구현. (b) OSM walk 태그가 보도를 이미
주면 CV 불필요(중복 투자). → "용도 없음"이 아니라 "CV가 필수 수단이 아닐 수 있음".

**합의한 관문**(비용 낮은 순, 각 관문서 폐기 가능):
- 관문0(먼저·쌈): OSM 서울 walk가 보도를 별도 way/태그로 갖는지 → 충분하면 **폐기(CV 불필요)**.
- 관문1: 불충분 시 지상 스트리트뷰 소스(Street View Static ToS/과금/ML허용,
  Mapillary 서울 커버리지·라이선스) → 합법·저비용·충분커버리지 없으면 **폐기**.
- GO: 둘 다 통과 + 이미지 최소조건(지상뷰·≥512px·지오태그 ≤10~20m·주간비폐색·
  전 간선 커버리지) 만족 시만 H0.
- '폐기'를 정식 결론으로 수용(04·08 제외 선례와 동급).

**→ 다음 액션**: 사용자 종료조건 합의 후 **관문0(OSM 보도 태깅 확인)** 착수. 상세는
WORK_LOG 2026-07-24 §7, `03_semantic_segmentation_agent.md` §5.

---

## 다음 / 남은 작업 (백로그)

- **비전 02·05**(아래 감사표): 02 용도 결정, 05 용도+VRAM 전략(외부 GPU 분리?) 필요.
- **06 미결**: Sentinel 소프트 플래그 **저장 지속화 + 어드민 오버라이드 엔드포인트**
  (저장 계층 정리 후 — S3 배선인데 AWS 미연결, DB 폴백 `VisionRepository` 미배선).
- **시크릿 (a)**: pydantic-settings 도입 시 mova·ontology 키 접근 함께 이관
  (단독 실행 금지 — WORK_LOG 2026-07-24 [2순위](a)).
- **S3**: AWS 실연결(버킷+키 세팅) 후 Tank 단일 경로 실 업로드 검증.
- **어드민 백엔드 인증 공백**: `/admin/dispatch`·`/admin/harvester` 라우터에
  `require_admin` 없음 → 프론트 `AdminAuthGate` 우회로 직접 호출 시 뚫림. 추가 필요.
- **기존 실패 테스트**(이번 작업 무관): `apps/mova/tests/test_import_interactor.py`
  2건, `test_llm_error_handling.py`.

---

## 참고: 02~08 적합성 감사 (2026-07-23, `00_COMMON_conventions.md` §8)

06의 실패(기법 먼저·용도 나중)를 기준으로 재감사한 결과.

| # | 이름 | 상태 |
|---|------|------|
| 02 | Argus(객체 검출) | 보류 — 용도 위험/데이터 불확실, 제품 결정 전까지 착수 안 함 |
| 03 | Loom(분할) | **조사 중**(위 "진행 중") — 종료조건 합의 단계, 폐기 가능성 높음 |
| 04 | Atlas(자세 추정) | **제외** — mova/gildle에 용도 없음(문서 배너) |
| 05 | Prisma(이미지 생성) | 보류 — 용도 불확실 + 하드웨어 위험(SD1.5 LoRA vs lora-server VRAM 겹침) |
| 06 | Sentinel(이상 탐지) | **완료**(H0~H6, `/vision/upload` 게이트) |
| 07 | Echo(감정분석) | **완료**(H0~H6) |
| 08 | Chronos(영상 분류) | **제외** — mova/gildle에 용도 없음(문서 배너) |

## 참고: VRAM 정책 (확정, `00_COMMON_conventions.md` §1.1)

`lora-server`(mova 채팅용 EXAONE-2.4B AWQ)가 상시 기동 → **모든 학습 전
`systemctl --user stop lora-server`**, 학습 후 `start` + `:8200/health` 확인 필수.
`nvidia-smi` free 수치만 믿지 말 것(WSL2 계측 불안정, 290MB↔7975MB 편차 사례).
