# backfill·수동 스크립트 실행 가이드

`suvisdev/scripts/` 하위 CLI(대부분 `backfill_*_cli.py`)를 EC2 프로덕션에
돌릴 때의 표준 실행 형태. **로그 리다이렉트 없이 그냥 돌리면 stderr/stdout
이 EC2 어디에도 남지 않는다**(2026-08-11 실측 발견 — `docker compose exec`
가 컨테이너 stdout에 안 붙는 구조라, 세션 콘솔이 흐르면 사라진다).
아래 형식으로만 실행할 것.

## 표준 형태

```bash
cd ~/suvisdev.cloud
docker compose exec -T backend \
  python scripts/<스크립트_이름>.py [옵션] \
  >> ~/<스크립트_이름>.log 2>&1
```

핵심:
- **`-T`** — TTY 없이 실행. cron/nohup 환경 필수.
- **`>> ...log 2>&1`** — stdout·stderr 모두 append. 파일명은 스크립트명과
  같게 맞춰 여러 로그가 섞이지 않게.
- **`--env-file suvisdev/.env`** — 원래 필수인 상황(compose `up`)과 달리
  `exec`은 컨테이너 안에 이미 env가 실려 있어 생략 가능.

## 현재 자동화된 것

| 스크립트 | 크론 (EC2 `ec2-user` crontab) | 로그 |
|---------|-------------------------------|------|
| `backfill_movie_embeddings_cli.py --limit 950` | `0 3 * * *` (KST) | `~/backfill_embeddings.log` |

`ssh aws crontab -l` 로 확인. 자동화 라인을 편집할 때도 위 표준 형태를
유지할 것(로그 리다이렉트 빼면 조용한 실패가 감지 안 됨).

## 수동 실행이 정상인 것 (참고)

일회성·특정 상황에서만 도는 스크립트라 자동화하지 않는다. 아래 목록은
"돌릴 일이 생기면 위 표준 형태 그대로 쓸 것"이라는 뜻일 뿐이고, 지금 당장
돌려야 하는 건 아니다.

- `backfill_synopsis_cli.py`
- `backfill_credits_cli.py`
- `backfill_age_rating_platforms_cli.py`
- `backfill_trailer_cli.py`
- `backfill_original_language_cli.py`
- `backfill_origin_country_cli.py`
- `ingest_hub_knowledge.py` (재임베딩 등 특수 실행 시)

## 왜 이 문서가 필요한가

2026-08-10 movies.embedding 백필이 Gemini 무료 티어 일일 쿼터로 중단됐을
때, 다음 세션에서 "왜 중단됐는지"를 찾으려 했는데 실행 로그가 어디에도
남아 있지 않았다(`~/*.log` 없음, `docker logs backend`에도 흔적 0). WORK_LOG
2026-08-10 기록은 실행 당시 세션 콘솔에서 옮긴 것뿐이었다. 이후 세션이
"코드 문제 아니냐" 재확인하려면 다시 `--limit 10` 실증까지 해야 했다.
같은 상황을 다른 스크립트에서 반복하지 않기 위해 이 표준을 문서로 남긴다.

## 참고
- 이번 문서를 만든 사이클의 근거·경위: `_docs/WORK_LOG.md` 2026-08-11.
- 자동화 상태 추적: `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 1-b순위.
