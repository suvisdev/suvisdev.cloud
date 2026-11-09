# 덜미 공격 시험

임시 서버(`eval/attack_server.py`)는 운영과 같은 라우터·규칙·모델을 쓰고 사이트·로그만 메모리에 둔다. 운영 DB와 재학습 데이터를 건드리지 않는다. 시험 도구(`eval/attack_eval.py`)는 localhost만 받는다.

## 결과 (2026-11-09, 부트스트랩 모델, 단계당 15회)

| 단계 | 통과 | 확인 | 차단 | 점수 중앙값 |
|---|---|---|---|---|
| A0 Origin 헤더 없이 직접 호출 | HTTP 403으로 거부 | | | |
| A1 API 직접 호출, 빈 신호 | 0 | 0 | 15 | 0.823 |
| A2 API 직접 호출, 지어낸 사람 신호 | **14** | 1 | 0 | 0.362 |
| B1 기본 자동화(fill·click) | 0 | 0 | 15 | 0.85 |
| B2 고정 간격 타자 | 0 | 0 | 15 | 0.905 |
| B3 직선 마우스·랜덤 타자 | 0 | 2 | 13 | 0.873 |
| B4 곡선 마우스·사람 흉내 | 0 | 0 | 15 | 0.976 |
| B5 모델 표본에 맞춘 흉내 | **7** | 8 | 0 | 0.566 |
| A3 지어낸 신호 80회 연속(마지막 20회 집계) | 0 | 20 | 0 | 0.75 |

## 해석

- **쉬운 매크로는 잡는다.** B1·B2는 규칙이 전부 차단했다.
- **신호를 지어내면 통과한다(A2).** 신호는 브라우저가 보내는 값이고 Origin 헤더도 프로그램이 넣을 수 있다. 서버가 진위를 확인할 방법이 없다.
- **표본에 맞추면 차단은 0건이다(B5).** 코드가 공개돼 있어 맞출 범위를 누구나 알 수 있다.
- **속도 신호는 연속 호출을 확인 단계까지만 올린다(A3).** 사람 오차단을 피하려는 설계(`scoring_policy.py`)대로다.
- **B4 차단은 탐지 성공으로 볼 수 없다.** 점수를 끌어올린 값은 클릭 간격 편차와 키 간격 편차다. 키 간격 편차에는 입력란을 옮기는 시간이 들어가 B4에서 272~449가 나왔고, 표본의 95분위는 148이다. 사람이 마우스로 두 칸을 채워도 같은 값이 나올 수 있어 **사람 오차단 위험의 신호**로 본다. 사람 대조군은 아직 없다.

## 다음 판단에 필요한 것

사람 대조군이다. 사람 세션의 차단율을 모르면 위 탐지율은 의미가 없다. 아래로 임시 서버를 띄워 직접 눌러 보면 `verdict`와 신호가 페이지에 표시된다.

## 다시 돌리기

`suvisdev/`에서 실행한다.

```bash
docker run -d --rm --name atk-redis --network host redis:7-alpine redis-server --port 6390
docker run -d --rm --name atk-app --network host -v "$PWD":/suvisdev -w /suvisdev \
  -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/suvisdev:/suvisdev/apps \
  -e DEOLMI_TOKEN_SECRET=eval-only-secret-0123456789012345678901234567890 \
  -e REDIS_URL=redis://127.0.0.1:6390/0 suvisdev-app:latest \
  uvicorn --app-dir apps/deolmi/eval attack_server:app --host 127.0.0.1 --port 8321

# 사람 시험: 브라우저에서 http://localhost:8321/page
# 공격 시험:
docker run --rm --network host -v "$PWD/apps/deolmi/eval":/ev:ro \
  mcr.microsoft.com/playwright/python:v1.58.0-noble sh -c \
  "pip install -q playwright==1.58.0 && python /ev/attack_eval.py"

docker stop atk-app atk-redis
```
