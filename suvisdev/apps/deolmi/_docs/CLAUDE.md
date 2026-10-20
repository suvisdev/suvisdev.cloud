# deolmi(덜미) — 매크로·봇 탐지 앱

> 2026-10-20 신설. 바탕화면 `매크로/botguard`(독립 프로토타입, SQLite 단일 파일 서버)를 이 저장소의
> 헥사고날 스포크로 옮긴 것. 사업 문서(사업계획서·기획서·경쟁사비교·특허검토메모)는 바탕화면 `매크로/`에 있다.
> 상위 규칙: [`suvisdev/CLAUDE.md`](../../../CLAUDE.md). 고객용 연동 방법: [INTEGRATION.md](INTEGRATION.md). 할 일·계획: [ROADMAP.md](ROADMAP.md).

## 무엇을 하나

예매·로그인 같은 입구에 붙이는 **방어용** 탐지기. 고객 페이지의 SDK가 행동 신호(마우스 궤적·클릭/키 간격·체류 시간 —
**입력 글자는 안 본다**)를 보내면 0~1 의심 점수와 `allow / challenge / block`을 매긴다. 제재 판단은 고객이 한다.

```text
[고객 페이지 + SDK] --pk_ + 신호--> POST /api/deolmi/score  → 서명 토큰 + 참고용 verdict
[고객 서버]        --sk_ + 토큰--> POST /api/deolmi/verify → 점수·사유 전체 (토큰 1회용, 2분)
```

## API (`main.py`에서 prefix `/api`)

| 경로 | 인증 | 설명 |
|------|------|------|
| `GET /api/deolmi/sdk.js` | 없음(의도) | SDK(`sdk/deolmi.js`) 서빙 |
| `POST /api/deolmi/score` | 공개 키 + 사이트별 허용 도메인 | 채점. **모든 출처에 CORS 개방**(아래) |
| `POST /api/deolmi/verify` | 비밀 키 | 토큰 검증. 틀린 키면 토큰을 소모하지 않는다 |
| `POST/GET /api/deolmi/admin/sites` | `require_admin` | 키 발급(비밀 키는 응답에서 한 번만)·목록 |
| `GET /api/deolmi/admin/stats` | `require_admin` | 이벤트 수·모델 상태·최근 20건 |

오류: 모르는 키 401 · 남의 도메인 403 · 틀린 비밀 키/위조 토큰 401 · 만료/재사용 400 · `DEOLMI_TOKEN_SECRET` 미설정 503.

## 탐지 두 겹

1. **규칙**(`domain/services/scoring_policy.py`) — 일정한 키/클릭 간격, 직선 마우스, 마우스 없는 클릭, 너무 빠른 제출,
   같은 사이트·IP 속도(10초 창 20회 의심·60회 차단).
2. **모델**(`adapter/outbound/ml/isolation_forest_model_adapter.py`) — IsolationForest. 모델 파일이 없으면 **가짜 사람 표본**으로
   부트스트랩(현재 상태). 규칙만으로 차단 수준이면 모델을 건너뛴다(cheap_first, 폭주 대응). 최종 = max(규칙, 모델).

## 구조 메모

- 레이어: router → `ScoreUseCase`/`SiteAdminUseCase` → interactor → 포트(사이트·이벤트 저장소, 모델, 토큰, 속도) → 어댑터.
  PG 저장소는 이 앱 뼈대대로 `adapter/outbound/repositories/*_pg_repository.py`.
- 테이블: `deolmi_sites`(비밀 키는 **sha256 해시만**), `deolmi_events`(signals·reasons JSONB). 마이그레이션 `20261020_0001`.
- **CORS**: 전역 CORS는 suvisdev 프론트만 허용하므로 `adapter/inbound/api/public_cors.py`가 `/api/deolmi/score`만
  가장 바깥에서 가로채 `*`(자격증명 없음)로 처리한다. 출처 통제는 사이트별 `domains`가 한다.
- 모델·토큰 jti 기록·속도 창은 **프로세스 메모리** — backend `replicas: 1` 전제. 파드를 늘리면 jti·속도를 Redis로 옮길 것.
  재시작하면 속도 창과 jti가 비지만 토큰 TTL이 2분이라 영향이 작다.
- 특징(`FEATURE_ORDER`)을 늘리면 `SignalsSchema`·SDK `features()`·`bootstrap_samples` 열을 같이 늘리고, 기존 모델 파일은 버리고 재학습.

## 환경 변수

| 키 | 필수 | 설명 |
|----|------|------|
| `DEOLMI_TOKEN_SECRET` | ✓ | 점수 토큰 서명(HS256). 사용자 세션 `JWT_SECRET`과 분리. 비면 score/verify 503 |
| `DEOLMI_MODEL_PATH` | | 재학습 모델 파일. 기본 `apps/deolmi/runs/model.joblib`(gitignore) |

## 운영 절차

```bash
cd suvisdev
alembic upgrade head                                           # 테이블 생성(배포는 자동 적용 안 함)
PYTHONPATH="$PWD:$PWD/apps" python -m deolmi.scripts.retrain_model   # allow 로그 200건 이상일 때 재학습
```

키 발급은 어드민 토큰으로 `POST /api/deolmi/admin/sites {"name","plan","domains":[...]}`.

## 테스트

`apps/deolmi/test/` (fake 포트 + 어댑터 + main과 같은 미들웨어 순서의 라우터·CORS 테스트). 2026-10-20 45개 통과,
임시 Postgres로 마이그레이션 up/down·HTTP 전 흐름 확인.

## 할 일·로드맵

[ROADMAP.md](ROADMAP.md) — 지금 해야 할 것, 단계별 계획, 결정이 필요한 것.
