# deolmi(덜미) — 매크로·봇 탐지 앱

> 2026-10-20 신설. 바탕화면 `매크로/botguard`(독립 프로토타입, SQLite 단일 파일 서버)를 이 저장소의
> 헥사고날 스포크로 옮긴 것. 사업 문서(사업계획서·기획서·경쟁사비교·특허검토메모)는 바탕화면 `매크로/`에 있다.
> 상위 규칙: [`suvisdev/CLAUDE.md`](../../../CLAUDE.md). 고객용 연동 방법: [INTEGRATION.md](INTEGRATION.md). 할 일·계획: [ROADMAP.md](ROADMAP.md).

## 무엇을 하나

예매·로그인 같은 입구에 붙이는 **방어용** 탐지기. 고객 페이지의 SDK가 행동 신호(마우스·펜 궤적, 터치 횟수, 클릭/키 간격,
키보드로 누른 클릭 수, 체류 시간 — **입력 글자는 안 본다**)를 보내면 0~1 의심 점수와 `allow / challenge / block`을 매긴다.
제재 판단은 고객이 한다. **판정은 위험 신호이지 사람이라는 증명이 아니다**(아래 "신뢰 경계").

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

오류: 모르는 키 401 · 남의 도메인 403 · 틀린 비밀 키/위조 토큰 401 · 만료/재사용 400 · `DEOLMI_TOKEN_SECRET` 미설정 503 ·
`/verify` 때 Redis 불통 503(재사용을 못 막으니 통과시키지 않는다) · 범위 밖·무한대 신호 422.

## 탐지 두 겹

1. **규칙**(`domain/services/scoring_policy.py`) — 일정한 키/클릭 간격, 직선 마우스, 움직임 없는 클릭(터치·키보드 클릭은 제외),
   너무 빠른 제출, 같은 사이트·IP 속도(10초 창 20회 0.60·60회 0.75). **속도만으로는 차단하지 않는다**(challenge 상한) —
   PC방·회사·통신사 NAT는 사람 여럿이 IP 하나를 쓴다. 사유(reasons)에는 남는다.
2. **모델**(`adapter/outbound/ml/isolation_forest_model_adapter.py`) — IsolationForest. 모델 파일이 없으면 **가짜 사람 표본**으로
   부트스트랩(현재 상태). 규칙만으로 차단 수준이면 모델을 건너뛴다(cheap_first, 폭주 대응). 최종 = max(규칙, 모델).
   **마우스 없이 터치·키보드로 쓴 세션(`no_mouse_input`)도 모델을 건너뛴다** — 모델은 마우스 세션으로만 학습해
   (재학습도 `move_count > 0`만) 마우스 특징이 0이면 사람이어도 0.99로 나온다(10-20 실측). 이때 `model_score`는 `null`.
   키보드 사용자는 두 경우를 다 인정한다: 버튼을 Enter로 누름(`kbd_click_count > 0`), 제출 버튼 없는 폼에서 Enter로 바로
   제출(implicit submission — 클릭 이벤트 없이 키 입력만). 키 리듬 등 규칙은 그대로 적용된다(일정 간격 자동 입력은 차단).

터치·키보드 신호(10-20 추가): SDK가 궤적은 `pointermove`의 마우스·펜만 보고(모바일 탭이 흉내 내는 마우스 이벤트·띄엄띄엄한
손가락 좌표가 '직선 이동'으로 잡히지 않게), 터치는 `touchstart`·`touchmove` 횟수(`touch_count`)만, 키보드로 누른 클릭은
`isTrusted && detail === 0`(`kbd_click_count`, 스크립트의 `el.click()`은 isTrusted가 false)로 센다. 두 값은 모델 특징
(`FEATURE_ORDER`)이 아니라 규칙·모델 생략 판정에만 쓴다 — 기존 모델 파일·부트스트랩은 그대로.

## 구조 메모

- 레이어: router → `ScoreUseCase`/`SiteAdminUseCase` → interactor → 포트(사이트·이벤트 저장소, 모델, 토큰, 속도) → 어댑터.
  PG 저장소는 이 앱 뼈대대로 `adapter/outbound/repositories/*_pg_repository.py`.
- 테이블: `deolmi_sites`(비밀 키는 **sha256 해시만**), `deolmi_events`(signals·reasons JSONB). 마이그레이션 `20261020_0001`.
- **CORS**: 전역 CORS는 suvisdev 프론트만 허용하므로 `adapter/inbound/api/public_cors.py`가 `/api/deolmi/score`만
  가장 바깥에서 가로채 `*`(자격증명 없음)로 처리한다. 출처 통제는 사이트별 `domains`가 한다.
- 토큰 jti 기록·속도 창은 **Redis**(`REDIS_URL`, 키 `deolmi:jti:*`·`deolmi:vel:*`) — 서빙 기기가 노트북↔집컴으로 바뀌거나
  파드가 재시작돼도 두 기기가 집컴 Redis 하나를 보므로 재사용 차단·속도가 이어진다. jti는 `SET NX EX(토큰 만료까지)`,
  속도는 `INCR+EXPIRE` 10초 고정 창(ontology rate limiter와 같은 방식, 경계에서 덜 셀 수 있음 — 의심 신호라 충분).
  Redis 장애 시 `/verify`는 503(fail-closed), 속도는 0으로 보고 채점은 계속(fail-open). 동기 `redis` 클라이언트(저장소 관례)라
  인터랙터가 `asyncio.to_thread`로 부르고, 접속·명령 제한은 1초. 모델만 프로세스 메모리.
- 이벤트 로그는 **응답을 보낸 뒤** 라우터의 `BackgroundTasks`가 `record_event`로 쓴다(폭주 때 응답이 DB 쓰기를 기다리지
  않게). `EventPgLogWriter`가 쓸 때마다 세션 팩토리에서 새 세션을 뽑는다(mova 리뷰 임베딩과 같은 방식). 저장 실패는 로그만
  남긴다. 재시작 직전 몇 건이 빠질 수 있다(재학습 원천일 뿐이라 허용).
- **score·verify는 요청 세션(`get_db`)을 쓰지 않는다.** 요청 세션은 응답 뒤 백그라운드 작업이 끝날 때까지 연결을 쥐는데,
  그 로그가 같은 풀에서 연결을 하나 더 기다려 동시 요청이 풀을 채우면 서로 막혔다(풀 1개 E2E에서 20건 중 500·풀 타임아웃
  재현 → 수정 후 전부 200). 키 조회는 `SitePgLookup`이 조회 동안만 연결을 빌리고 바로 돌려준다. 어드민 경로는 그대로 `get_db`.
- 신호 상한(`score_schema.py`): 횟수 100만, 거리 10억 px, 시간 10억 ms. NaN·무한대는 422. JSON `1e309`는 파이썬에서 inf가
  되고 FastAPI 기본 422 처리기가 그 inf를 응답에 되돌려 쓰다 500이 나므로, 공개 요청 바디는 검증 전에 inf를 None으로 바꾼다.
- 특징(`FEATURE_ORDER`)을 늘리면 `SignalsSchema`·SDK `features()`·`bootstrap_samples` 열을 같이 늘리고, 기존 모델 파일은 버리고 재학습.

## 신뢰 경계 (10-20 리뷰로 명시)

신호는 **방문자 브라우저가 스스로 보고하는 값**이다. 공개 키(`pk_`)는 페이지에 박혀 있으므로, SDK를 쓰지 않고
사람다운 숫자를 지어내 `/score`에 보내면 정상 서명 토큰(allow)을 받는다. 서명은 "덜미가 이 점수를 매겼다"만 보장하지
"사람이 보냈다"는 보장하지 않는다. 지금 막는 것은 **SDK를 그대로 돌리는 단순 매크로와 실수로 드러나는 자동화**까지다.

- 고객에게는 verdict를 **위험 신호**로 쓰고 자체 통제(로그인·1인 매수 제한·결제 검증 등)와 함께 쓰라고 안내한다(INTEGRATION.md).
- 터치·키보드 신호도 위조 가능하다 — 마우스 없는 세션은 모델을 건너뛰므로 위조자는 규칙만 피하면 된다. 같은 한계 안의 일이다.
- 계획(ROADMAP 단계 3): 서버측 교차검증(속도·기기 지문·같은 기기 시도 횟수), 고객 서버가 발급한 세션별 nonce를 토큰에
  묶어 `/verify`가 되돌려 주기, 작업증명(PoW)으로 대량 위조 비용 올리기.

## 환경 변수

| 키 | 필수 | 설명 |
|----|------|------|
| `DEOLMI_TOKEN_SECRET` | ✓ | 점수 토큰 서명(HS256). 사용자 세션 `JWT_SECRET`과 분리. 비면 score/verify 503 |
| `DEOLMI_MODEL_PATH` | | 재학습 모델 파일. 기본 `apps/deolmi/runs/model.joblib`(gitignore) |
| `REDIS_URL` | (기존) | jti·속도. 새 키 아님 — k8s `backend.yaml`이 `redis://redis:6379/0`(집컴 Redis)로 넣는다 |

## 운영 절차

```bash
cd suvisdev
alembic upgrade head                                           # 테이블 생성(배포는 자동 적용 안 함)
PYTHONPATH="$PWD:$PWD/apps" python -m deolmi.scripts.retrain_model   # allow 로그 200건 이상일 때 재학습
```

키 발급은 어드민 토큰으로 `POST /api/deolmi/admin/sites {"name","plan","domains":[...]}`.

## 테스트

`apps/deolmi/test/` (fake 포트 + `_FakeRedis` + 어댑터 + main과 같은 미들웨어 순서의 라우터·CORS 테스트). 2026-10-20 75개,
임시 Postgres·Redis로 마이그레이션·HTTP 전 흐름(터치·키보드 사람 allow, 새 프로세스에서도 재사용 400, 풀 1개 동시 20건) 확인.
`test_sdk_signals.py`는 `sdk_driver.js`로 **SDK를 node에서 실제로 돌려** 브라우저 이벤트 순서(Enter 바로 제출·버튼 Enter·
터치·`el.click()`)에서 나온 신호를 서버에 넣는다. node가 없으면 건너뛴다(운영 이미지엔 없음, GitHub ubuntu 러너엔 있음).
Redis 어댑터 폴더는 `adapter/outbound/kvstore/` — `cache/`라 하면 `suvisdev/.gitignore`의 `cache/` 규칙에 걸려 커밋에서 빠진다.

## 할 일·로드맵

[ROADMAP.md](ROADMAP.md) — 지금 해야 할 것, 단계별 계획, 결정이 필요한 것.
