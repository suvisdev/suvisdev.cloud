1# 작업 일지

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

## 2026-08-11

### 작업 내용
- 0순위 착수 전 사전 진단 요청. 어제(08-10) 백필 중단이 문서엔 "Gemini
  1일 1000건 한도"로 기록돼 있지만 **사용자가 "혹시 코드/데이터 에러
  아니냐"**고 확인 요청 — 자동화 등록 전 실 원인을 실측으로 재검증.
- 원인 확정 후 사용자 지시로 즉시 대량 실행(오늘 쿼터 창) + crontab
  자동화 등록 + 로그 리다이렉트 인프라 정비까지 한 사이클로 완료.

### 진단 (문서 재검증)
- EC2 prod 실측 초기값: `total=2014 with_embedding=962 remaining=1052`
  — 08-10 WORK_LOG 값과 정확히 일치.
- `--limit 10` 재현: `succeeded=10 failed=0 skipped=0` → 962→972 반영
  확인. **코드/데이터 문제 아님**, 스크립트 idempotent 재확인.
- 원인은 문서 기록 그대로 **Gemini 무료 티어 EmbedContent 일일 쿼터**
  (`EmbedContentRequestsPerDayPerProjectPerModel-FreeTier`, limit 1000,
  `gemini-embedding-1.0`). 어제 창은 이미 소진, 지금은 다음 창이라 재현
  시점 성공. 스크립트 `HubRagError`를 catch해서 continue하므로(74~78행)
  개별 movie 데이터로 죽는 경로 자체가 코드상 없음.

### 로그 인프라 부재 발견
- **이전 실행 stderr/stdout이 EC2 어디에도 남아 있지 않다** — `~/*.log`
  없음, `docker logs suvisdevcloud-backend-1`에도 `backfill_movie_embeddings`
  흔적 0. `docker compose exec`가 컨테이너 stdout에 안 붙는 구조라 세션
  콘솔이 흐르면 조용히 사라진다. 자동화 등록 시 **로그 리다이렉트 없이는
  silent 실패를 감지할 방법이 없음**을 확인 — 이번 crontab에는 필수로 포함.

### 수정/구현 — 이번 사이클 실행

- **즉시 수동 실행(오늘 쿼터 창 최대 활용)**: EC2에서 nohup+background로
  `--limit 950` 실행. `>> ~/backfill_embeddings.log 2>&1`로 리다이렉트.
  ```bash
  cd ~/suvisdev.cloud && nohup docker compose --env-file suvisdev/.env \
    exec -T backend python scripts/backfill_movie_embeddings_cli.py \
    --limit 950 >> ~/backfill_embeddings.log 2>&1 &
  ```
  - SSH 세션 timeout에도 nohup으로 컨테이너 안 python 프로세스 정상 생존
    (PID 확인). ssh session 종료 후에도 진행됨.

- **crontab 등록(매일 KST 03:00 = PDT 자정 직후 신규 쿼터 창)**: EC2
  `ec2-user` crontab에 추가.
  ```cron
  0 3 * * * cd ~/suvisdev.cloud && docker compose exec -T backend \
    python scripts/backfill_movie_embeddings_cli.py --limit 950 \
    >> ~/backfill_embeddings.log 2>&1
  ```
  - `-T`(TTY 없음)로 cron 환경에서도 exec 가능.
  - `>>` + `2>&1`은 옵션 아니라 필수(위 진단 근거).
  - 확인: `ssh aws crontab -l`.

### 데이터
- 진단 후: `total=2014 with_embedding=972 remaining=1042` (--limit 10 반영).
- 오늘 대량 실행 리포트: `대상 950편 → succeeded=950 failed=0 skipped=0`.
  실행 시간 약 16분(00:32~00:48 UTC).
- 최종: **`total=2014 with_embedding=1922 remaining=92`**. 남은 92편은
  익일 03:00 KST 자동화가 처리(오늘 쿼터는 950건 사용 + 이전 10건 =
  총 960건으로 한도 근접, 나머지는 새 창).

### 오류·막힌 점
- (없음. 진단 → 실행 → 등록 순으로 막힘 없이 진행)

### 산출물
- EC2 `~/backfill_embeddings.log` 신규 생성.
- EC2 `ec2-user` crontab에 백필 라인 추가(기존 `auto-deploy.sh`는 주석
  처리 상태 유지, 이번엔 건드리지 않음).
- 문서 갱신: `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 1-b순위 항목을
  "자동화 등록 완료" 취지로 갱신 + 재확인 결과 반영.
- **후속 티켓 분리**: 로그 인프라 부재는 embedding 스크립트에 국한된
  문제 아님(다른 `scripts/backfill_*_cli.py`도 같은 패턴일 가능성).
  이번 사이클은 embedding만 처리하고, 전면 정비는 PROGRESS.md에 별건으로.

### 작업 내용(추가) — 0.5순위: HNSW 벡터 인덱스 도입

- 위 1-b 완결 사이클에 이어, 리뷰 임베딩(1순위) 진입 전 선행 조건인 벡터
  인덱스 부재(진단 세션의 부수 발견) 처리.
- Part A(remaining=0 통과) 원칙은 사용자 결정으로 완화 — 남은 92편은 익일
  자동화가 처리, 지금은 1922편 실측을 Before 기준선으로 활용.

### 수정/구현 — Part B

- **pgvector 버전 확인**: EC2 prod `0.8.5` — HNSW 완전 지원(0.5.0+).
- **Alembic 리비전 `20260811_0001`** 신설:
  `suvisdev/alembic/versions/20260811_0001_add_hnsw_indexes_on_embedding_columns.py`.
  `movies.embedding`·`hub_knowledge.embedding` 각각 `USING hnsw (embedding
  vector_cosine_ops) WITH (m=16, ef_construction=64)`. downgrade에서 인덱스
  drop. `CREATE INDEX CONCURRENTLY`는 alembic 트랜잭션과 충돌해 미사용
  (지금 규모는 락 몇 초로 무시 가능).
- **로컬 검증 불가 → EC2 컨테이너 직접 반영**: 로컬은 WSL Docker Desktop
  미통합 상태라 alembic 실행 불가. scp로 EC2 `/tmp/` 이동 → `docker cp`로
  `suvisdevcloud-backend-1:/suvisdev/alembic/versions/`에 넣고 `alembic
  upgrade head` 실행. 정식 이미지 통합은 다음 배포 사이클 몫.
- **downgrade→upgrade 왕복 검증**: 인덱스 2건 삭제 확인 → 다시 upgrade해
  2건 재생성 확인. 리비전 파일 안전성 확인.

### 벤치마크 — 실 라우터 경로 20회 (`curl` `real` time)

| 지표 | Before(seq scan) | After(planner default) |
|------|------------------|------------------------|
| median | 37.5ms | 30ms |
| p95 | 269ms | 73ms |
| max | 842ms | 117ms |

- **정직한 해석**: After 개선이 인덱스 직접 효과인지 캐시/워밍인지 애매.
  EXPLAIN을 뜯어 보니 planner가 2014행 규모에선 cost 오판(HNSW cost=860 >
  Seq cost=416)으로 인덱스 스캔을 **자동 선택하지 않는다** — Before/After
  둘 다 실제로는 seq scan. 표의 개선폭은 이번 사이클의 핵심 성과가 아님.
- **잠재력 별도 실측(EXPLAIN 강제)**:
  - 순수 seq scan: **10.178 ms** (`WHERE embedding IS NOT NULL AND id!=1
    ORDER BY embedding <=> ... LIMIT 10`)
  - `SET LOCAL enable_seqscan = off` 강제 시 HNSW 사용: **1.482 ms** —
    **약 6.8배**. 실제 EXPLAIN 계획에 `Index Scan using
    idx_movies_embedding_hnsw` 확인.

### 오류·막힌 점

- 없음. 다만 planner가 인덱스를 자동 선택 안 하는 pgvector의 알려진 특성
  탓에 이번 사이클의 취업 어필용 벤치마크가 애매해짐 → 아래 "다음 단계"에
  후속 티켓으로 분리했다.

### 데이터
- movies 인덱스 크기: 7.7 MB (HNSW m=16, ef_construction=64, 1922 벡터).
- hub_knowledge 인덱스 크기: 8.0 MB (HNSW 같은 파라미터, 2014 벡터).
- 카운트 변화 없음(2014/1922). 인덱스는 순전히 조회 경로 개선용.

### 산출물(추가)
- 리비전 파일: `suvisdev/alembic/versions/20260811_0001_add_hnsw_indexes_on_embedding_columns.py`
- PROGRESS.md 1-c순위 아래에 "0.5순위 완료 / 코드 힌트 후속" 블록 추가.
- 삭제: `suvisdev/apps/mova/_docs/MOVA_REVIEW_PIPELINE_AUDIT.md` (사용자
  판단으로 정리, 결론은 PROGRESS 1-c순위 본문에 이미 요약돼 있음).

### 후속 사이클(같은 날) — A·B·C 세 항목 즉시 처리

사용자 요청으로 남아 있던 후속 티켓 두 건(HNSW 힌트, 로그 인프라 문서화)
+ 문서 수치 갱신 1건을 같은 세션에서 마무리.

**A. MOVA_UI_AUDIT.md §5 embedding 수치 갱신**
- `embedding 962/2014 미완` → `1922/2014 거의 완료, 잔여 92는 자동화`.
- 각주도 "962편에서만 뜬다" → "잔여 92편만 임베딩 없음"으로 정합.

**B. HNSW planner 힌트 코드 추가 + 실 API 벤치마크 재측정**
- 어제 남긴 정직한 미해결 — planner cost 오판(HNSW 860 > Seq 416)으로
  실 라우터가 여전히 seq scan이던 것 — 해결.
- 수정: `movies_pg_repository.find_similar_movies` 시작부에
  `await self._session.execute(text("SET LOCAL enable_seqscan = off"))`
  한 줄. `SET LOCAL`이라 트랜잭션 종료 시 자동 원복(다른 세션 무영향).
- EC2 반영: 로컬 → `scp` → `docker cp` → `docker restart suvisdevcloud-
  backend-1`. 재기동 후 헬스체크(`GET /mova/movies` 200) 확인.
- EXPLAIN 재확인: `Index Scan using idx_movies_embedding_hnsw`, Execution
  Time **1.214 ms**(seq scan 시 10.2 ms).
- 벤치마크(실 API 20회):
  | 지표 | Before(인덱스 없음) | After(인덱스, seq scan) | **After+Hint(HNSW)** |
  |---|---|---|---|
  | median | 37.5 ms | 30 ms | **30 ms** |
  | p95 | 269 ms | 73 ms | **33 ms** |
  | max | 842 ms | 117 ms | 134 ms |
- **정직한 해석**: median은 힌트 유무 차이 미미 — 네트워크 RTT가 응답
  시간의 대부분을 차지해 DB 개선이 묻힌다. **tail latency(p95)가 확실히
  안정** — 인덱스 없음 대비 269 → 33 ms(약 87% 개선). EXPLAIN의 6.8배는
  순수 DB 이야기고, curl로 재는 실 API에는 nginx+FastAPI+psycopg+왕복
  오버헤드가 실려 그대로 재현되지 않는다.

**C. `_docs/SCRIPTS_EXECUTION_GUIDE.md` 신설**
- 표준 실행 형태(`docker compose exec -T backend python ... >> ~/*.log
  2>&1`) + 현재 자동화 대상 + 왜 이 문서가 필요한지(이번 사이클에서 발견한
  로그 인프라 부재 사고). CLI별 `--log-file` 옵션은 문서 강제로 충분해
  별건 티켓으로 승격하지 않는다.

### 산출물(A·B·C)
- `_docs/MOVA_UI_AUDIT.md` §5 갱신
- `suvisdev/apps/mova/adapter/outbound/pg/movies_pg_repository.py` +5줄
  (import `text`, 힌트 4줄 + 주석)
- `_docs/SCRIPTS_EXECUTION_GUIDE.md` 신설
- PROGRESS.md 0.5순위 항목 "힌트 적용 완료" 갱신, 로그 인프라 티켓 종결
- **남은 후속 일**: 리비전 + 힌트 코드 모두 아직 `docker cp` 임시 반영
  상태. 정식 배포는 다음 사이클(main 병합 → backend 재빌드).

### 정리(추가) — PROGRESS.md 종결 항목 전면 삭제

CLAUDE.md 원칙("완료된 항목은 상세 대신 WORK_LOG 날짜만 남기고")과
사용자 요청("종결된건 어차피 worklog에 기록될텐데 그냥 삭제해줘")에 따라
PROGRESS.md의 "종결됨 —" 대형 블록 8건 + "~~취소선~~ — **종결(...)**"
개별 항목 10건 전부 삭제(168줄 축소). 각 항목의 경위·상세는 원래도
WORK_LOG의 해당 날짜에 남아 있어서 정보 손실은 없음. 이후 종결되는
항목은 이 사이클 이후 규칙대로 상세 대신 WORK_LOG 날짜만 남길 것.

---

## 2026-08-10

### 작업 내용
- "어제 한 작업 이어서 해줘" 요청. 실측해 보니 2026-08-09 세션은 **코드는
  전부 끝났지만 프로덕션에 배포되지 않은 상태**였다 — `ec2/main`이 08-09
  커밋 2개(`023d40a`·`9a0c521`)만큼 뒤처져 있었고, 마이그레이션
  `20260809_0001`도 미적용, 백필은 로컬 dev DB 39편에만 돌아 있었다.
- 사용자 확인 후 범위를 "전부(배포 + 프로덕션 백필까지)"로 확정하고 진행.

### 수정/구현
- **연도 필터 드롭 버그 수정(08-09 이월분)**: `suvis/app/api/mova/movies/route.ts`의
  `FORWARD_PARAMS`에 백엔드가 받지 않는 `release_year`(단수)만 있고, 클라이언트
  (`lib/mova-api.ts`)가 실제로 보내는 `release_year_min`/`release_year_max`가
  빠져 있어 `/mova/movies`의 연대 필터가 프록시에서 조용히 버려지고 있었다.
  `release_year` 단수는 저장소 전체에서 이 허용목록 1곳에만 있던 죽은
  이름이라 함께 제거. PR #66.
- 문서 정리: `_docs/MOVA_UI_AUDIT.md`를 **종결 문서**로 전환(10건 종결 내역 +
  의도적으로 남긴 2건: 프로필 이미지 업로드는 S3 미연결, 번호 페이지네이션은
  UX 선택지), PROGRESS.md의 구 6순위(age_rating/platform 백필)·구 10순위
  (UI 감사 잔여 10건)를 "종결됨"으로 이동, 08-09 항목의 미기입 커밋 해시
  2곳 채움.

### 배포·백필(EC2)
- `git merge origin/main` → `docker compose --env-file suvisdev/.env up -d
  --build backend`(캐시 히트, COPY 레이어만 재생성) → `alembic upgrade head`
  (`20260807_0002` → `20260809_0001`).
- 마이그레이션 전 백엔드 로그에 `movies.trailer_key` 미존재 에러가 실제로
  찍혔다(KOFIC 박스오피스 스케줄러가 부팅 직후 `movies`를 조회) — 코드가
  먼저 올라가고 컬럼이 나중에 생기는 순서라 예상된 창(window)이었고
  마이그레이션 직후 해소.
- 백필 3종을 컨테이너 안에서 **병렬** 실행(`docker compose exec -d`).
  병렬로 돌려도 안전한 근거: 세 `update_*` 메서드가 전부 ORM 객체의 단일
  속성만 바꾸고 커밋해 SQLAlchemy가 **변경된 컬럼만** UPDATE하므로
  같은 행을 동시에 건드려도 다른 컬럼을 덮어쓰지 않는다. 순차로 돌리면
  2배 이상 걸릴 상황이었다(TMDB 재조회가 분당 20~50편).

### 오류·막힌 점
- 없음. (백필 로그에서 `print` 출력이 파일 리다이렉트 시 블록 버퍼링돼
  "대상 N편" 줄이 늦게 보이는 점만 확인 — 진행률은 로깅(stderr)의 HTTP
  요청 수와 DB 카운트로 추적했다.)
- **관찰(수정 안 함)**: `backfill_age_rating_platforms_cli.py`가 이미
  `append_to_response=...,videos`로 트레일러 정보까지 받아오는데
  `trailer_key`는 안 쓴다 — `backfill_trailer_cli.py`가 같은 TMDB 상세
  엔드포인트를 한 번 더 호출한다. 일회성 스크립트라 이번엔 병렬 실행으로
  덮었고, 통합은 하지 않았다.

### 데이터
- 백필 전 프로덕션(`movies` 2014편): age_rating 38 / platforms 13 /
  trailer_key 3 / embedding 3 (전부 이 세션의 `--limit` 시험 실행분 포함).
- 백필 후: **age_rating 1538 / platforms 1510 / trailer_key 1877 /
  embedding 962** (모수 2014).
  - age·platforms가 100%가 아닌 건 정상 — 스크립트 리포트가
    `succeeded=1697 empty=289`로, TMDB에 **KR 등급·플랫폼 정보가 아예 없는**
    영화가 289편이다(`empty`는 실패가 아니라 "찾아봤지만 없음").
    trailer도 같은 이유로 `empty=113`.
  - **embedding만 미완(962/2014)** — 아래 참고.

### 오류·막힌 점(추가①) — Gemini 임베딩 일일 쿼터

- `backfill_movie_embeddings_cli.py`가 **429 `EmbedContentRequestsPerDayPerProject
  PerModel-FreeTier`, limit: 1000, model: `gemini-embedding-1.0`**으로 중단됐다.
  리포트: `대상 2011편 → succeeded=959 failed=1052`.
- 기존 백로그 9순위(Gemini 레이트 리밋)는 **분당 15요청**(생성 모델) 얘기였는데,
  이건 **임베딩 모델의 하루 1000건** 제한이라 성격이 다르다. 분당 간격을 늘려도
  오늘 안에는 못 채운다.
- 스크립트가 `embedding IS NULL`만 대상으로 잡아 **idempotent**하므로 다음 날
  그대로 재실행하면 이어서 채워진다(남은 약 1052편 → 하루 1000건 한도라 이틀치).
- 이 쿼터는 **프로젝트 단위**라, 같은 날 `hub_knowledge` 재임베딩(PROGRESS 1순위)을
  돌리려 했다면 그것도 함께 막혔을 것이다.
- 영향: "비슷한 영화" 섹션은 **임베딩이 있는 962편에서만** 뜬다(원본 영화에
  임베딩이 없으면 `find_similar_movies`가 None을 반환해 섹션이 안 보인다).
  회귀가 아니라 데이터 미완 상태다.

### 작업 내용(추가②) — 아바타 업로드 구현 + "S3 미설정" 전제 정정

`MOVA_UI_AUDIT.md`에 마지막으로 남아 있던 §1-d(프로필 이미지 업로드)를 두고
"무엇을 설정해야 하냐"는 질문이 나와 실측했더니, **전제 자체가 틀렸다**.

- 루트 `CLAUDE.md`는 "`AWS_ACCESS_KEY_ID`·`VISION_S3_BUCKET` 미설정"이라고
  적어 뒀고 08-09 세션도 그걸 믿고 "S3 미설정으로 보류"했지만, 실제로는
  네 키(`AWS_ACCESS_KEY_ID`·`AWS_SECRET_ACCESS_KEY`·`AWS_REGION`·
  `VISION_S3_BUCKET`)가 **로컬·EC2 양쪽 `.env`에 다 채워져 있었다**.
- EC2 컨테이너에서 `Tank.list_buckets()` 호출 →
  `suvisdev-s3-584569945696-ap-northeast-2-an` 반환, `list_objects("")`에
  susu가 올린 `media/4/20260804_*.jpg`가 이미 들어 있었다. 즉 S3는 **쓰이고
  있는 중**이었다.
- 진짜 막고 있던 건 설정이 아니라 코드였다 — `users`에 아바타 컬럼 없음,
  업로드 엔드포인트 없음, 프론트 UI 없음.
- 버킷은 비공개다(객체 공개 URL 직접 호출 → 403). 그래서 표시는 presigned URL로
  간다.

### 수정/구현(추가②)

- **마이그레이션 `20260810_0001`**: `users.avatar_key TEXT NULL`. **URL이 아니라
  S3 객체 key만** 저장한다 — presigned URL은 1시간 만료값이라 DB에 넣으면 즉시
  낡는다.
- **viewer 자체 아바타 라우터**(`avatar_router.py`, `POST /viewer/avatar/upload`):
  media 앱의 `POST /media/photos`를 재사용하지 않았다 — 그쪽은 susu(Flutter)의
  RS256 `aud=suvis-susu` 토큰 전용이고, media·viewer 둘 다 Spoke라 직접 import가
  금지돼 있다(`suvisdev/CLAUDE.md` O.4). 공용 자원인
  `core.matrix.aws_tank_s3_manager`만 함께 쓴다.
  - 인증은 `require_user`(HS256). **대상 user_id를 경로·바디로 받지 않고 토큰에서만
    뽑는다** — 남의 아바타를 바꿀 경로 자체가 없어 IDOR 표면이 없다.
  - MIME 화이트리스트(jpeg/png/webp) → 415. **확장자는 파일명이 아니라 MIME에서
    유도**한다(`evil.php.jpg` 같은 이중 확장자 방지).
  - 5MB 상한을 **청크 누적 검사**로 건다 → 초과 즉시 413.
    `UploadFile.spool_max_size`는 메모리→디스크 스풀 전환 임계값이지 업로드
    상한이 아니라 검증에 못 쓴다. media 선례(전부 읽고 `len()`)는 상한 초과
    요청도 통째로 메모리에 올리는 문제가 있어 따르지 않았다.
  - S3 key는 `avatars/{user_id}/{uuid}.{ext}` — susu의 `media/` 아래와 분리.
- **레이어**: `AvatarStorage` 출력 포트 + `TankAvatarStorageAdapter`
  (`adapter/outbound/s3/`) 신설, `ProfileInteractor`가 둘(프로필 repo + 스토리지)을
  받아 조립. `GET /viewer/profile/{user_id}` 응답에 `avatar_url`(presigned) 추가 —
  DTO는 `avatar_key`(저장값)와 `avatar_url`(조회 시 파생값)을 둘 다 들고 있는다.
  presigned URL 발급이 실패해도 `None`으로 두고 프로필 조회 자체는 막지 않는다.
- **프론트**: `MovaAvatarUploader`(신규 컴포넌트) + `lib/profile-api.ts`의
  `uploadAvatar()` + 프록시 `app/api/viewer/avatar/route.ts`(multipart는 FormData를
  그대로 재전송 — `Content-Type`을 직접 넣으면 boundary가 깨진다).
  `URL.createObjectURL`로 즉시 미리보기하고 `revokeObjectURL`로 해제한다.
  mova mypage의 정적 아바타 원을 이 컴포넌트로 교체(그 자리에서만 쓰이던
  `User` 아이콘 import 제거).
  - mova mypage 응답(`MypageData`)엔 아바타가 없어 업로더가 `fetchProfile()`로
    초기값을 따로 읽는다 — mova mypage DTO에 아바타를 끼워 넣으면 mova가
    viewer 소유 데이터와 S3까지 알아야 해서 그쪽이 더 나쁘다.

### 검증(추가②)

- **마이그레이션 up→down→up 왕복**: 이 노트북엔 docker도 Postgres도 없어
  EC2 Postgres에 **일회용 DB `avatar_roundtrip`**을 만들어 검증했다(프로덕션
  무접촉). base부터 전체 체인 실행 → `20260810_0001 (head)` 도달 →
  `avatar_key text YES` 확인 → `downgrade -1` → 컬럼 0건 확인 → 재 upgrade →
  1건 확인 → 스크래치 DB 삭제.
- **테스트**: `apps/viewer/tests` **18개 통과**(기존 11 + 신규 7 — 200/415/413/
  400(빈 파일)/401/경계값 정확히 5MB/확장자를 MIME에서 유도하는지).
  로컬에 파이썬 환경이 없어 uv로 경량 venv를 새로 만들었다(torch 제외).
- `pnpm type-check` 클린. `lint-imports`: **"Spokes must not import each other
  directly" KEPT** — 아바타 어댑터가 스타-토폴로지를 깨지 않음을 확인
  (전체는 5 kept / 1 broken이며, broken은 기존 baseline인
  `ontology → core.matrix → titanic/viewer ORM` 경유 건으로 이번 변경과 무관).

### 배포·프로덕션 실측(추가②)

- EC2 배포 + `alembic upgrade head`(`20260809_0001` → `20260810_0001`).
- 프로덕션 실 업로드 왕복(임시 토큰을 컨테이너 안에서 `JWT_SECRET`으로 10분짜리
  발급, 대상은 `users.id=3 suvisdev`):
  - 무인증 `POST /viewer/avatar/upload` → **401**
  - 업로드 → **200**, `avatar_key=avatars/3/85a060cf....png`
  - `Tank.list_objects("avatars/")`에 객체 실재 확인
  - `GET /viewer/profile/3` → `avatar_url`(presigned) → 그 URL로 **GET 200**
  - PDF → **415**, 6MB → **413**(nginx `client_max_body_size`가 10M이라
    5MB 초과분이 앱까지 도달해 앱 가드가 낸 응답이 맞다)
- 프론트(Vercel `main` 자동 배포): `/mova/mypage` 200,
  프록시 `POST /api/viewer/avatar` 무인증 **401**(3계층 토큰 경로 연결 확인).
- **검증 후 흔적 제거**: S3 테스트 객체 삭제(`avatars/` 0건),
  `users.id=3`의 `avatar_key`를 NULL로 되돌림.
- **못 한 검증**: 실제 브라우저로 파일 선택 → 미리보기 → 업로드 → 갱신 렌더까지
  클릭해 본 것은 아니다(이 세션에 브라우저 구동 수단 없음). 프론트 근거는
  `pnpm type-check`와 위 프록시 401 실측까지다.

### 작업 내용(추가③) — PROGRESS.md 백로그 청소 + `EMBEDDING_BACKEND` 전제 오류 발견

"PROGRESS.md에 남은 작업이 뭐냐"는 질문에 답하려고 백로그를 훑다가 **문서
전제가 또 틀린 걸 하나 찾았다**(이 문서에서 반복되는 패턴).

- **1순위(hub_knowledge 재임베딩)의 "이미 끝난 것"에 "EC2 `.env`에
  `EMBEDDING_BACKEND=gemini` 설정"이라고 적혀 있었으나, 실측하니 EC2 `.env`는
  `EMBEDDING_BACKEND=ollama`였다**(`docker-compose.yaml`에 오버라이드도 없음).
  WORK_LOG 2026-08-07이 "설정 + 컨테이너에서 어댑터 교체 확인"이라고 적은
  것과 다르다 — 되돌아간 건지 애초에 반영이 안 된 건지는 확인할 수 없었다.
- 프로덕션 로그(최근 24시간)에 지금도 그대로 찍힌다:
  `[HubRagInteractor] embed 실패, 검색 생략 | Ollama 서버에 연결할 수
  없습니다` → `[ChatInteractor] fallback search_tag_catalog 사용`,
  `[QwenIntentClassifier] 라우팅 호출 실패, rag로 폴백`.
  즉 **벡터 검색 경로는 여전히 한 번도 돌지 않았다.**
- 결론: 재임베딩(프로덕션 2014행 삭제라 사용자 판단 대기 중)보다 **스위치를
  켜는 게 먼저**다. 1순위 항목을 "남은 것 ①(스위치) / ②(재임베딩)"로 쪼갰다.
- 참고: 오늘 돌린 `movies.embedding` 백필은 이 스위치와 무관하다 — 스크립트가
  `GeminiEmbeddingAdapter`를 직접 임포트해서 쓴다(그래서 429가 났다).

**낡은 항목 정리**(같은 문서 안에서 이미 종결인데 활성 목록에 남아 있던 것):
- "구현과 의도 갭" 감사 사이클 — 본문엔 "2026-08-07 종결"이라 적혀 있으면서
  취소선 없이 활성 목록에 있어 미결로 읽혔다. 압축 + 취소선 처리하고,
  남는 것은 작업이 아니라 습관(새 배치 추가 시 자체 점검)임을 명시.
- "SUVIS 저장소 컬럼 길이 정책 부재" — `.claude/rules/orm-columns.md`로
  종결된 항목이 **같은 문서에 두 번** 적혀 있었다(한쪽은 이미 취소선). 정리.
- "EC2 hub_knowledge 임베딩 어댑터 부재" — 어댑터는 PR #55로 생겼으므로
  제목이 더는 맞지 않는다. "코드는 있고 스위치가 꺼져 있음"으로 재정의하고
  위 실측 근거를 붙였다.

### 작업 내용(추가④) — 9순위 Gemini 레이트 리밋 완화 (b) 완료

"남은 작업 시작해줘" 지시로 백로그 착수. 사용자 결정·물리 접근이 필요한 셋
(1순위 재임베딩=프로덕션 삭제, 5순위=노트북, `/api` prefix 변경)은 제외하고
9순위부터.

- **여기서도 전제가 하나 틀렸다**: 9순위는 "쿼터 초과 시 `recs=0`으로 조용히
  나가 장애로 안 보인다"고 적고 있었으나, 코드 전 경로를 따라가 보니
  추천 생성 호출의 429는 `gemini_client`(`LLMError(429)`) → 라우터
  (`HTTPException`) → 프론트(`safeApiErrorMessage`가 문자열 detail을 그대로
  통과)까지 전달돼 **"Gemini 할당량이 초과되었습니다"로 이미 표시된다**.
  삼켜지는 건 의도 추출 호출뿐이고 그건 정규식 폴백으로 이어지는 의도된
  설계다. 즉 백로그가 요구한 세 가지 중 "안내 구분"은 이미 돼 있었다.
- **동시에 "무 rate-limit"도 오해였다**: `/mova/chat`엔
  `adapter/inbound/api/rate_limit.py`(IP 기준 분당 20회)가 이미 붙어 있다.
  백로그의 "LLM 챗 3개 무인증+무 rate-limit" 항목은 titanic smith·execsuite
  langchain·contents soccer **다른 세 엔드포인트** 얘기였고, 그 항목 본문도
  "mova는 있는 것과 대조"라고 정확히 적고 있었다(내 오독).

### 수정/구현(추가④)

- **Gemini 호출 2회 → 1회**(`intent_extraction.py`): `extract()`가
  `_fallback_raw()`(결정론적)를 **먼저** 돌리고, `_has_hard_signal()`로
  장르·배우·국가·연도가 잡혔는지 본다. 잡혔으면 Gemini 의도 추출을 건너뛴다.
  - 판단 기준을 "하드 조건"으로 잡은 이유: 그게 `search_tag_catalog`이 실제로
    후보를 좁히는 데 쓰는 신호라서다. **키워드만 나온 경우는 일부러 거짓**으로
    뒀다 — 토큰을 자른 것뿐이라 무드 질의를 정규식으로 처리하면 품질이 떨어진다.
  - `_fallback_raw()`가 내부에서 만들고 버리던 `search_filters`를 반환값에
    포함시켰다(연도가 거기에만 있음). 원문에서 다시 유도하면 정규화 기준
    (`_FILLER` 제거 여부)이 갈릴 수 있어 같은 산출물을 보게 했다.
- **429 재시도 1회**(`gemini_client.py`): 쿼터성 오류일 때만 2초 뒤 1회
  재시도. 분당 한도는 고정 윈도우라 창이 막 넘어가는 순간의 요청이 구제된다.
  하루 한도엔 소용없으므로 1회로 끝낸다(사용자를 40초씩 붙잡지 않기 위해).
  쿼터가 **아닌** 실패는 재시도하지 않는다 — 장애 시 부하만 두 배가 된다.

### 검증(추가④)
- 신규 테스트 9건(`test_gemini_quota_retry.py` 4 — 재시도 성공/재실패 429/
  비쿼터 오류는 재시도 안 함/대소문자 무시, `test_intent_gemini_skip.py` 5 —
  장르·연도·국가·복합("2020년대 한국 액션") 스킵 + 무드 질의는 Gemini 유지).
- `apps/mova/tests` + `apps/viewer/tests` **197개 전부 통과**.
- `lint-imports` 5 kept / 1 broken(기존 baseline과 동일).

### 작업 내용(추가⑤) — 잡다한 미결 6건 처리

사용자 지시로 "지금 할 수 있는 6건"을 착수. 결과는 **처리 4건 + 전제 정정 1건 +
착수 불가 1건**이다.

**1) 단독 `1` 문자 — 추정이 아니라 실제로 살아 있었다**
- 로컬·EC2 **양쪽** `suvisdev/.env` 29번째 줄(`GEMINI_API_KEY` 바로 다음)에
  단독 `1`이 그대로 있었다. 백로그는 "재발하면 확인 필요"로 관망 상태였는데
  이미 재발해 있었던 것.
- 양쪽 백업(`.env.bak-20260810`) 후 그 줄만 삭제 → `docker compose config` 정상,
  컨테이너 키 주입 3개 확인. (변수를 정의하는 줄이 아니라 런타임 영향은 없었다.)
- **재발 탐지 자동화**: `scripts/check_env_drift.py`에 "`KEY=`도 주석도 아닌 줄"
  검출을 추가(줄번호와 함께 출력, exit 1). 백업본으로 실제 탐지되는지 확인.

**2) `bulk_import_movies.py` rollback — "죽은 코드"가 아니었다**
- `HubRagInteractor.ingest_movie()`가 삼키는 건 임베딩 실패(`HubRagError`)뿐이고,
  그 뒤 `repository.upsert()`(INSERT ... ON CONFLICT, `source_ref` UNIQUE)는
  try **밖**이라 DB 오류는 그대로 올라온다. 2026-08-05 배치 1000편에서 한 번도
  안 걸린 건 임베딩이 매번 먼저 실패해 upsert까지 간 적이 없어서다.
- 즉 **아직 도달 못 한 코드**이고, 임베딩이 도는 순간 살아난다. 지우면 세션이
  pending-rollback으로 남아 도미노가 재현된다. 제거하지 않고 **호출부에 근거
  주석**을 남겨 다음 사람이 지우지 않게 했다. 백로그의 (a)/(b) 판단은 소멸.

**3) `get_mova_session_factory()` commit 누락 함정**
- 레포지토리 commit 정책 통일(트랜잭션 경계 변경)은 여전히 안 한다. 대신 함정이
  있는 자리인 `HubKnowledgeRepository.upsert()` docstring에 "flush만 하고 commit은
  호출자 몫", 대조군(`MoviesPgRepository.update_*`는 내부 커밋), 올바른 예
  (`scripts/ingest_hub_knowledge.py`)를 적었다. 백로그에 묻어 두는 것보다
  코드에서 마주치게 하는 편이 낫다.

**4) EC2 `backend`/`auth` 이미지 중복 태깅**
- `docker-compose.yaml`의 두 서비스에 같은 `image: suvisdev-app:latest`를 부여.
  빌드는 한 번만 일어나고 디스크엔 한 벌만 남는다(차이는 `command:`뿐).
  8.84GB짜리 pip 레이어 중복 보유가 해소된다.

**5) `create_all()`/alembic 이중 관리 — 실측으로 안전 확인 후 제거**
- 착수 전 검증: EC2에 일회용 DB를 만들어 **빈 DB에 `alembic upgrade head`만**
  돌린 결과가 **프로덕션과 정확히 같은 36개 테이블(차집합 0)**. 즉 create_all은
  완전히 중복이었다.
- 도중에 내가 두 번 헛짚었다 — 처음엔 ORM 테이블명을 `passengers`/`bookings`로
  잘못 알고 "alembic이 못 만든다"고 봤고(실제는 `titanic_passengers`/
  `titanic_bookings`), 프로덕션 조회 IN 목록에도 `titanic_passengers`를 빠뜨려
  "프로덕션에 없다"고 잘못 읽었다. 테이블 집합 전체를 diff해서 확정.
- `ensure_titanic_tables()`에서 `create_all()`과 그것 때문에만 있던 ORM import·
  `Base` import를 제거하고, DB 준비 확인만 남겼다(docstring에 근거 기록).

**6) pydantic-settings 이관 — 착수 불가(설계상)**
- 백로그에 "단독 실행 금지"라 적혀 있고, 근거인 2026-07-24 조사 결론이
  "mova·ontology가 같은 env 이름을 읽어 값 divergence 없음(상태 중복이 아니라
  코드 중복), 현재는 무해. 지금 accessor를 신설하면 이관 때 또 뜯게 됨"이다.
  **app별 Settings 도입 여부가 먼저 결정돼야 열리는 항목**이라 손대지 않았다.

### 검증(추가⑤)
- `apps/mova/tests` + `apps/viewer/tests` **197개 통과**(create_all 제거 후 재실행).
- 스크래치 DB(`alembic_only_test`)는 비교 후 DROP.

### 산출물
- 커밋 `1bde7e8` → PR #66 → `main` 머지(`5dd0b49`). EC2 머지 커밋 `b69255c`.
- 아바타: 커밋 `386462b` → PR #67 → `main` 머지(`81ee6ff`).
  배포 기록 `cc1416c` → PR #68(`d1ac421`).
  UI 감사 §5 수치 정정 `67ba9a7` → PR #69.
- 프론트(Vercel)는 `main` 자동 배포 — 배포 후 실측으로 연도 필터 수정 확인
  (`release_year_min=2020&release_year_max=2029` → 550편,
  `1990~1999` → 169편. 수정 전이라면 둘 다 전체 1735편이 나왔을 것).
- 프로덕션 신규 엔드포인트 스모크 테스트: `GET /mova/movies/{slug}/similar`
  200, `DELETE /mova/reviews/{id}` 무인증 401(엔드포인트 존재 확인),
  배우 필터·관람등급 필터 정상 응답.

### 추가⑥: MOVA 리뷰 이해 파이프라인 현황 진단 (읽기 전용)

- 계기: "리뷰가 추천의 핵심 입력"이라는 전제가 실제 코드에서 어디까지
  구현돼 있는지 확인 요청. **코드 수정 없이 조사만** 했다.
- **결론: A — 별점만 추천에 (간접) 반영, 리뷰 텍스트는 UI 표시 전용.**
  - `reviews.body`를 읽는 곳은 마이페이지 조회와 영화별 리뷰 목록 둘뿐이고
    둘 다 화면 표시로 끝난다. 임베딩·감정 분석·검색 인덱스 어디에도 없다.
  - 별점은 `_update_movie_rating()`
    (`market_reviews_pg_repository.py:202-216`)이 `movies.rating`을 리뷰
    평균으로 덮어쓰고, 추천 후보 조회가 전부 `ORDER BY movies.rating DESC`라
    **후보 순위에만 간접 반영**된다. 사용자별 취향 벡터는 없다 — 프롬프트에
    붙는 개인화 신호는 `users.preferred_genres`와 최근 질의 3건뿐이다.
  - 임베딩 입력 텍스트(`movies.embedding`·`hub_knowledge`) 셋 다
    title/장르/출연/synopsis 구성이고 리뷰가 안 들어간다. LoRA 재학습
    데이터(`export_chat_training_dataset.py`)도 chat+picks만 쓴다.
- 조사 중 부수 발견 2건:
  - **HNSW/IVFFlat 인덱스가 저장소 전체에 하나도 없다.** 유일한 언급이
    `studio_movies_orm.py:74`의 "인덱스는 별도 리비전" 주석인데 그 리비전이
    존재하지 않는다 — 지금은 전부 순차 스캔이다. 리뷰 임베딩을 추가하면
    행 수가 자릿수로 늘어나므로 인덱스 리비전이 선행돼야 한다.
  - 감정 분석은 **ontology에 완결된 구현이 이미 있다**
    (`sentiment_analysis_interactor.py`, `echo_sentiment_adapter.py`,
    `train_echo_sentiment.py`). mova에서 import하는 곳은 0건 — 새로 만들
    게 아니라 Hub 경유로 연결하면 되는 항목이다.
- 한계(명시): **DB 실측은 못 했다.** 이 WSL 배포판에 `docker` CLI가 없고
  (Docker Desktop WSL 통합 비활성) `psql`도 없어, 스키마 기술은 ORM +
  마이그레이션 기준이다. `movies.embedding` 백필 962/2014도 PROGRESS.md
  기재값이지 실측값이 아니다.
- 산출물: `suvisdev/apps/mova/_docs/MOVA_REVIEW_PIPELINE_AUDIT.md` 신설
  (레이어별 진단 + 갭 분석 + 다음 스텝 3순위). 커밋 `493c702` → PR #73 →
  `main` 머지(`0f1d799`). 문서만 바뀌어 EC2 배포는 없음.

### 추가⑦: 프론트 전용 스킬 `ponytail` 커밋

- 그동안 untracked로 남아 있던 `suvis/.claude/skills/ponytail/SKILL.md`를
  저장소에 넣었다. `suvis/`(프론트) 안에서만 발동하는 코딩 스타일 스킬로,
  YAGNI→기존 코드 재사용→표준 라이브러리→네이티브 기능→기설치 의존성→한 줄
  순의 "사다리"를 강제해 불필요한 추상화·보일러플레이트를 막는다.
  백엔드(hexagonal DDD 레이어)에는 적용하지 않는다고 스킬 자체에 명시돼 있다.
- 스킬 파일이 **저장소 안 `.claude/`**에 있으므로 팀·다른 에이전트와 공유된다
  (홈 `~/.claude/`의 개인 메모리와 구분 — 루트 `CLAUDE.md` "메모리 두 곳의 차이").

---

## 2026-08-09

### 작업 내용
- `_docs/MOVA_UI_AUDIT.md` 잔여 10건 전부 착수·완료(1-c·1-d·1-e·3-a·3-c·2-a는
  세션 전반부, 3-b·4-c·4-b·4-a는 세션 후반부 "위 내용 이어서 하자" 요청으로 이어감).

### 추가 구현(세션 후반부 — 3-b·4-c·4-b·4-a)
- **3-b·4-c 연령등급/플랫폼**: TMDB `release_dates`/`watch/providers`를
  `append_to_response`로 한 번에 받아옴(추가 API 호출 없음). `map_kr_certification`
  ("ALL/12/15/19"→"전체/12세/15세/청불")·`map_kr_watch_providers`(provider_name
  정규화, TMDB엔 provider별 개별 딥링크가 없어 국가 단위 링크 하나 공유) 신설.
  `list_missing_age_rating_or_platforms`/`update_age_rating_and_platforms`
  리포지토리 메서드 + `scripts/backfill_age_rating_platforms_cli.py`. 프론트:
  `platforms[].url` 매핑 누락 수정(§4-c 원인), `/mova/movies` 관람등급·플랫폼
  select 활성화(§3-b).
- **4-b 트레일러**: TMDB `videos`(`include_video_language=ko,en,null`로 한국어
  없어도 폴백) 연동, `map_youtube_trailer`(Trailer·official·ko 우선순위) 신설.
  **신규 컬럼** `movies.trailer_key` TEXT(마이그레이션 `20260809_0001`) +
  `scripts/backfill_trailer_cli.py`. 상세 페이지에 유튜브 iframe 임베드 추가.
- **4-a 유사 영화**: `movies.embedding`(768차원, 지금까지 한 번도 안 채워짐 —
  hub_knowledge 재임베딩 이슈와 무관한 별개 컬럼)을 `ontology` Hub의
  `GeminiEmbeddingAdapter` 재사용(Spoke→Hub 임포트, 허용됨)으로 백필.
  `title/genres/cast(5명)/synopsis` 텍스트로 임베딩 생성.
  `find_similar_movies()`(pgvector `cosine_distance`, 자기 자신 제외) +
  `GET /mova/movies/{slug}/similar` 신설. 상세 페이지에 "비슷한 영화" 가로 스크롤
  섹션 추가.
- 공통: `age_rating`/`platforms`/`trailer_key` 전부 **인터랙티브 단건 임포트
  경로**(`_to_upsert`)에도 연결 — 다음부터 신규 임포트 시 자동으로 채워짐(대량
  카탈로그 확장은 PROGRESS.md 방침대로 안 함).

### 검증(세션 후반부)
- 백엔드: 경량 venv로 `apps/mova/tests`·`apps/viewer/tests`·`shared/tests`·
  ontology 임베딩 관련 2개 파일 194개 전부 통과(신규 mapper/DTO 테스트 포함).
  기존 `MovieDetailDto(...)` 직접 생성 테스트 2곳이 새 필수 필드로 깨져서 같이 고침.
  `pnpm type-check` 매 단계 클린.
- 실제 TMDB API로 로컬 dev DB(39편, `suvisdev-db-1`) 전량 백필 실행 확인:
  age_rating 27편·platforms 12편·trailer_key 36편·embedding 39편 채워짐.
  `find_by_slug`→DTO→schema 경로도 실측(`trailer_key` 끝까지 보존 확인).

### 오류·막힌 점(세션 후반부)
- `backfill_movie_embeddings_cli.py` 첫 실행이 "Mova URL이 설정되지 않았습니다"로
  실패 — 원인은 `.env` 로드가 `core.matrix.grid_oracle_database_manager`가 아니라
  `core.matrix.vauly_keymaker_secret_manager`(모듈 import 시점 `Keymaker()` 싱글턴
  생성)의 부작용이었는데, 이 스크립트만 `get_keymaker()` 워밍업 호출을 빠뜨렸음
  (다른 backfill_*_cli.py는 우연히 먼저 호출하고 있었음). `get_keymaker()`를
  `get_mova_session_factory()`보다 먼저 호출하도록 추가해 해결.

### 산출물
- 커밋 `9a0c521`(세션 후반부 4건 — 연령등급/플랫폼·트레일러·유사 영화).
  `origin/main`에 직접 푸시. **EC2 배포·프로덕션 백필은 이 세션에서 안 함 —
  2026-08-10 항목 참고.**

### 수정·구현
- **1-c 찜 삭제**: mypage 찜 카드에 삭제 버튼 배선(`removeFromWatchlist` 재사용).
- **1-d 닉네임 편집**: mova mypage에 편집 UI 추가(`updateNickname` 재사용, 아바타
  업로드는 S3 미설정으로 보류). — **정정(2026-08-10)**: "S3 미설정"은 사실이
  아니었다. 네 키가 로컬·EC2 `.env`에 이미 다 채워져 있었고 EC2에서
  `Tank.list_buckets()`가 실제 버킷을 반환한다(루트 `CLAUDE.md`의 "미설정" 기술을
  검증 없이 믿은 것). 아바타 업로드는 2026-08-10에 구현됐다.
- **1-e 리뷰 삭제**: `DELETE /mova/reviews/{review_id}` 신설(포트·인터랙터·
  리포지토리·라우터 전 레이어 + IDOR 소유권 검증) + 프론트 프록시·API·mypage
  배선. 리뷰 전량 삭제 시 `movies.rating`이 stale하게 남던 기존 버그도 같이 수정
  (`_update_movie_rating`이 결과 0건일 때 0.0으로 리셋하도록).
- **사용자 요청 추가**: 찜/리뷰 삭제를 작성자 본인 또는 관리자만 가능하도록.
  `UserPrincipal`에 `role` 필드 추가(JWT `role` claim, 기본값 `"user"`로 기존
  테스트 호환). 찜 삭제·리뷰 삭제 라우터에 소유자-또는-관리자 가드 적용(찜의
  조회·추가는 여전히 본인 전용, 우회는 삭제로 한정).
- **3-a 배우 필터**: `/mova/movies`에 `actor` 쿼리 파라미터 신설(백엔드
  `MovieFilterQuery`+EXISTS 서브쿼리, 프론트 디바운스 입력 필드). 겸사겸사
  프론트 프록시(`app/api/mova/movies/route.ts`)가 `release_year_min`/
  `release_year_max`는 안 잊고 forward하되 실제로는 `release_year`(단수)만
  허용리스트에 있어 **연도 필터가 조용히 드롭되고 있던 기존 버그**를 발견함
  (수정은 안 함 — 별도 이슈로 남김).
- **3-c 0건 대안 제안**: 헤더/랜딩 검색바 0건 드롭다운에 "AI에게 물어보기" 버튼
  추가(`onEmptySubmit` 전파, `/mova/main?q=`로 이동). `/mova/movies` 필터 0건
  화면에 "필터 초기화" 버튼 + 인기 검색 영화 대체 제안 추가.
- **2-a 홈 개인화**: `MovaPreferredGenresBadge` 신규 — 선호 장르가 채워진
  로그인 사용자에게 홈에 배지+편집 링크 노출(온보딩 카드와 상호 배타적).

### 검증
- 백엔드: 이 노트북에 없던 pytest 환경을 경량 venv(uv, torch 제외)로 임시
  구성 — `apps/mova/tests`·`apps/viewer/tests`·`shared/tests` 171→179개 전부
  통과(신규 delete 테스트 8건 포함).
- 로컬 dev DB(`suvisdev-db-1`, 39편)가 `20260731_0001`에 멈춰 있어
  `alembic upgrade head`로 `20260807_0002`까지 올리고 배우 필터를 실 쿼리로
  검증(`톰 홀랜드`→4편, `젠데이아`→3편, 존재하지 않는 이름→0편).
- 프론트: `pnpm type-check` 매 단계 클린 통과. `pnpm lint`는 저장소에 `eslint`
  패키지 자체가 없어(기존 환경 문제) 여전히 실행 불가.

### 오류·막힌 점
- `.env`의 `TMDB_API_KEY`에 CRLF 개행이 섞여 있어(`\r\n`) 쉘 변수로 그대로
  치환하면 curl이 "Malformed input to a URL function"으로 실패 — `tr -d
  '\r\n'`으로 제거해야 함. `.env` 파일 자체는 건드리지 않음.
- 3-b·4-c(연령등급·플랫폼)용 TMDB API 조사만 마침: `append_to_response=
  credits,release_dates,watch/providers`로 상세 조회 1번에 다 가져올 수 있음.
  KR `certification`은 `"ALL"/"12"/"15"/"19"` 형태(청불 확정 사례는 못 봄),
  `watch/providers`엔 provider별 URL이 없고 국가 단위 링크 하나뿐(JustWatch
  경유). 코드 작성은 토큰 예산상 다음 세션으로 이월.

### 산출물
- 커밋 `023d40a`(세션 전반부 6건 — 찜/리뷰 삭제·배우 필터·0건 대안·홈 개인화).
  `origin/main`에 직접 푸시.

---

## 2026-08-07

### 작업 내용
- 502 두 종류 상태 재확인 요청에 답변(어제 mova 챗 502는 gemini 폴백으로
  해결·유지 중, EC2 Cloudflare Tunnel 간헐적 502는 이번 확인 시점엔 6/6
  200으로 정상 — 완전 해결 선언은 아님, 백로그 0순위 유지).
- 사용자가 "DB에 태국어 같은 한국어/영어 아닌 영화는 제외해야 할 것 같다"고
  제기 — 조사 결과 `movies` 테이블에 TMDB `original_language` 자체가
  저장된 적이 없어(제목 텍스트로 태국 문자 스크립트만 세면 2014편 중 3편뿐,
  신뢰 불가) 언어 필터 신호가 DB에 없던 것으로 확인. 사용자 확인 후
  (1) 카탈로그/추천에서만 제외(행은 유지) (2) 지금 바로 착수, 두 가지로
  범위 확정 후 구현.

### 수정/구현
- 마이그레이션 `20260807_0001`(`movies.original_language` String(8) NULL).
- `tmdb_mapper.map_tmdb_row()`가 TMDB 응답의 `original_language`를 추출
  (기존엔 안 받아옴, 소문자 정규화), `TmdbCatalogAdapter.fetch_by_id()`의
  genre 재구성 분기(수동으로 DTO를 다시 만드는 코드)도 함께 수정 — 안 하면
  이 경로(백필 CLI가 쓰는 경로)에서 값이 유실됨.
- 저장 배선: `MovieUpsertCommand`/`TmdbMovieSnapshotDto`에 필드 추가,
  `bulk_import_movies.py`·`import_interactor.py` 양쪽 TMDB upsert 경로,
  `MoviesPgRepository.upsert_movie()` insert/update 양쪽 — synopsis
  컬럼(2026-08-06)과 동일 패턴 재사용.
- 필터링: `ALLOWED_ORIGINAL_LANGUAGES = ("ko", "en")` 상수를
  `studio_movies_orm.py`에 신설, `MoviesPgRepository.list_movies()`
  (`/mova/movies` 카탈로그)와 `ChatPgRepository`의 후보 쿼리 2곳
  (`_movies_by_ids` — 태그/배우 매칭, `search_tag_catalog`의 인기작
  폴백)에 `original_language IS NULL OR IN ('ko','en')` 조건 추가.
  **NULL(백필 전 레거시 로우)은 배제 아님으로 취급** — 백필이 끝나기
  전까지 기존 영화가 갑자기 안 보이는 회귀를 피하기 위한 설계.
- 신규 `scripts/backfill_original_language_cli.py`(`backfill_synopsis_cli.py`
  구조 그대로 재사용, `--limit`/`--dry-run`, idempotent — KOFIC 원산은
  TMDB id가 없어 대상 밖, 애초에 전부 한국 영화라 필터 관심사도 아님).
- 테스트 9건 신규(`test_tmdb_mapper.py` 3건 — original_language 추출/대소문자
  정규화/필드 부재 시 빈 문자열, `test_backfill_original_language_cli.py`
  6건 — 인자 파싱 2 + `_backfill_one` 4). `apps/mova/tests` 119개 전부
  통과, import-linter mova 관련 위반 0건.

### 오류·막힌 점
- 없음(마이그레이션 신설 자체는 character_name/synopsis와 동일 패턴이라
  막힌 지점 없었음).

### 데이터
- 로컬 실행 전 실측: EC2 `movies` 2014편 중 태국 문자 스크립트 포함 제목
  3편(참고용 하한선일 뿐, 실제 비한국어/비영어 편수는 백필 후에나 정확히
  나옴).

### 산출물
- 커밋 `4231991`(suvisdev) → PR #53 → `main` 머지(`c3fe524`). 병합 중
  `origin/main`이 로컬보다 3커밋 앞서 있던 걸 발견(hub_knowledge Phase 2
  완료분 + cloudflared 502 근본 수정 — 다른 세션이 직접 `main`에 반영,
  아래 참고) — `git merge origin/main`으로 충돌 없이 합류.
- **EC2 배포·백필 완료**: `git merge origin/main`(EC2 로컬에 미푸시
  `.gitignore` 커밋 1개 있었음, 트리비얼 — 함께 병합) → `docker compose
  up -d --build backend` → `alembic upgrade head`(20260806_0001→
  20260807_0001) → `--limit 5` 시험 성공 확인 → 전체 백필(1965편) 백그라운드
  실행, Monitor로 진행 추적(총 소요 약 25분). 최종 분포: en 1677/ja 56/
  ko 35/fr 33/es 31/zh 28/it 26/기타 다수, **총 279편이 언어 필터로
  제외**. NULL 23편은 전부 `tmdb-` 슬러그가 아닌 레거시 수동 등록 영화
  (도둑들·윤희에게·엽기적인 그녀 등, 기존 "레거시 무태그 로우" 백로그와
  동일 그룹) — 백필 대상 자체가 아니었고 설계대로 노출 유지. 프로덕션
  API로 확인(`GET /mova/movies` 총계 2014→1735) — 필터 정상 작동.

### 작업 내용(추가①) — PROGRESS.md 백로그 일괄 처리(노트북 필요 항목 제외)

사용자 지시로 `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 백로그 중 집
노트북이 필요한 것(5순위 lora-server 복구 등)을 빼고 전부 착수. 순서는
"빠른 것(문서·감사) 먼저", 제품 결정이 필요한 항목은 마주칠 때마다 질문.

### 수정/구현(추가①)

**1) 1순위 hub_knowledge 벡터 검색 — 조사 결과 백로그 가정이 틀림**
- 백로그는 "데이터는 채워졌으니 품질 비교만 남았다"고 봤으나, 프로덕션
  로그 실측 결과 **EC2에서 벡터 검색이 한 번도 작동한 적 없음**을 확인.
  `/mova/chat`은 `search_movies()`를 실제로 호출하지만 쿼리 임베딩에
  Ollama가 필요하고 EC2엔 Ollama가 없다 → 매 요청
  `[HubRagInteractor] embed 실패, 검색 생략` → `fallback search_tag_catalog
  사용`. 노트북에서 백필한 2014편이 전혀 안 읽히고 있었음.
- 덤으로 `QwenIntentClassifier`도 같은 원인으로 죽어 destination이 항상
  `rag`로 폴백되는 것도 로그에서 확인.
- 컨테이너 안에서 `OllamaEmbeddingAdapter().embed()` 직접 호출로 재확인
  (`HubRagError: Ollama 서버에 연결할 수 없습니다`).

**2) GeminiEmbeddingAdapter 신설(위 1의 해결책, PR #55)**
- `gemini-embedding-001`은 기본 3072차원인데 `hub_knowledge.embedding`이
  `Vector(768)`이라 `output_dimensionality=768`로 맞춤. MRL 절단이라 L2
  norm이 1이 아니지만(실측 0.586) 검색이 `cosine_distance`(스케일 불변)만
  써서 순위에 영향 없음을 확인하고 재정규화는 넣지 않음.
- `EMBEDDING_BACKEND` 스위치(기본 `ollama` — 하위호환), EC2 `.env`에 `gemini`
  설정 + 배포 후 컨테이너에서 어댑터 교체·768차원 반환 확인.
- **재임베딩은 사용자 판단으로 보류** — Ollama(nomic)와 Gemini는 의미
  공간이 달라 벡터가 호환되지 않아(차원은 768로 같아서 에러도 안 남)
  전량 재임베딩이 필요한데, 프로덕션 2014행 삭제가 걸려 있어 멈춤.
  `ingest_hub_knowledge.py`에 `--embedding-backend`/`--reset`/`--limit`를
  추가해 실행 준비만 해둠. 벡터 경로는 현행(폴백) 유지 — 회귀 없음.
- 테스트 8건(백엔드 스위치 4 + 어댑터 계약 4). 작성 중 `patch.dict(sys.modules)`가
  `import x.y as z`를 가로채지 못해 테스트 2건이 실제 Gemini API를 때리고
  있던 것을 발견 → `patch("google.generativeai.embed_content")`로 교체.

**3) 백엔드 `CLAUDE.md` 깨진 Windows 심볼릭 링크 복구**
- 백로그엔 "`_docs/CLAUDE.MD` 구버전 잔존"으로 적혀 있었으나 실제는 정반대 —
  `suvisdev/CLAUDE.md`가 문서가 아니라 `C:/Users/hi/Documents/...` 경로
  문자열만 든 **61바이트 텍스트 파일**이었다(Windows 심볼릭 링크가 일반
  파일로 커밋됨). 즉 백엔드 레이어·SOLID·스타-토폴로지 규칙이 에이전트
  컨텍스트에 **한 번도 로드된 적이 없었음**(이 세션 시작 시 시스템이 그
  경로 문자열을 그대로 읽어온 것으로도 확인).
- 저장소 전체를 훑어 같은 패턴이 이 1건뿐임을 확인. 2026-08-04 `suvis/`
  선례대로 본문(431줄)을 `suvisdev/CLAUDE.md`로 이동, 옛 경로 참조 6곳
  (README 4·entity-rules 1·앱 문서 3) 정정. 참조된 앱 문서·entity-rules가
  실재하는지 먼저 확인 후 수정.

**4) `.claude/rules/orm-columns.md` 신설**
- `character_name` VARCHAR(50) 사고의 재발 방지. 외부 API·LLM·사용자 입력은
  `Text`, 우리가 형식을 정하는 식별자·코드만 `String(N)`.
- 규칙에 쓸 사실을 전부 실측: 저장소 전체 컬럼 타입 분포, 현행 `Text` 컬럼
  목록, 프로덕션 최대 길이 대비 여유(`movies.title` 77/255, `actors.name`
  31/128 등) → **기존 컬럼은 여유 3배 이상이라 당장 옮길 필요 없고 신규
  컬럼에만 적용**이라는 결론까지 근거와 함께 기록. 초안에 `tag_kind` 크기를
  확인 안 하고 썼다가 실제 값(`String(16)`)으로 정정.

**5) `scripts/check_env_drift.py` 신설**
- `.env.example` 키가 실제 `.env`에 있는지 비교(값은 비교 안 함 — 비밀 유출
  방지). 누락 시 exit 1이라 CI·배포 게이트로 쓸 수 있음.
- 즉시 유용성 확인: 로컬 13개·EC2 9개 누락 키 탐지. EC2 배포 스크립트
  (`auto-deploy.sh`)는 저장소에 없고 EC2에만 있어 자동 배선은 스코프 밖.

**6) 4순위 "구현과 의도 갭" 감사 — 가설 반증 + 신규 2건**
- 백로그 가설("다른 앱에도 퍼져 있을 통계적 근거")은 **반증**. gildle·
  contents·auth·analytics·media를 훑은 결과 배치 루프·외부 API 호출 지점
  자체가 없어 패턴이 성립하지 않음 — mova/ontology 배치 파이프라인에 집중.
- **신규 #9(심각)**: `hub_knowledge.source_ref`를 `source="mova_movie"`로
  쓰는 5곳 중 **4곳이 slug, 1곳만 `movie.id`**. 읽는 쪽
  (`chat_reply.enrich_from_db`)은 후보 id 집합을 `int(item.id)`로 만들고
  파싱 실패 시 조용히 `continue`하므로, slug 색인이 벡터 검색에 걸리면
  후보가 빈 셋 → **추천 전부 드롭("카드 0개")**. 실사용자가 신고했던 증상과
  동일. 지금은 (a) 벡터 경로가 죽어 있고 (b) 현재 2014행이 마침 `movie.id`
  키라 가려져 있을 뿐, **오늘 배포한 Gemini 스위치를 켜고 bulk_import를
  돌리면 바로 재현**되는 상태였음. `source_ref`가 전역 UNIQUE라 중복 색인
  문제도 있었음.
- **신규 #10(경미)**: `backfill_hub_movies_rag.py`의 `ingested` 카운터가
  시도 횟수를 셈 — `HubRagInteractor`가 임베딩 실패를 삼켜서 0건 성공해도
  "N편 색인 완료"로 보고.
- 사용자 확인 후 #9·#10 둘 다 수정(구버전 스크립트는 삭제 대신 "고쳐서
  유지" 선택). `backfill_hub_movies_rag.py`는 JSONL에 slug만 있어
  `list_all_slugs()`로 slug→movie.id 조회 후 색인(미등록 slug는 스킵).
- 회귀 테스트 1건 추가 후 **일부러 slug로 되돌려 실제로 실패하는지 확인**
  (통과만 확인하면 무의미한 테스트가 되므로) → 확인 후 원복.

### 오류·막힌 점(추가①)
- 테스트가 실제 외부 API를 때리고 있던 것(위 2 참고) — `import x.y as z`는
  `sys.modules` 패치를 우회하고 실제 모듈을 바인딩한다. 모듈 속성을 직접
  패치해야 함.
- EC2 `git pull`이 divergent branches로 실패(로컬에 미푸시 `.gitignore`
  커밋 1개 존재) → 내용 확인 후 `git merge origin/main`으로 병합.

### 데이터(추가①)
- EC2 `hub_knowledge`: 2014행 전부 `movie.id` 키(slug형 0건) — 수정 전
  데이터는 오염되지 않은 상태임을 확인.
- 프로덕션 컬럼 길이 실측: `movies.title` max 77/255, `actors.name` 31/128,
  `tags.label` 5/255, `picks.hook` 40/120.

### 산출물(추가①)
- PR #55(Gemini 임베딩 어댑터, 머지·EC2 배포 완료), 커밋 `17400b2`(CLAUDE.md
  복구)·`4c15087`(ORM 규칙)·`56f1d94`(env drift)·`8ca0e3c`(source_ref 통일).
- `apps/mova/tests` + `apps/ontology/test` 182개 통과, import-linter 위반
  baseline(4건, 전부 기존 `core.matrix` 경유)과 동일.

### 작업 내용(추가②) — UI 감사 §6 잔여 3건 + 마이페이지 무인증 노출 수정

사용자 지시로 `_docs/MOVA_UI_AUDIT.md`(2026-08-05 작성) 실행. 착수 전 실측
검증 결과 **§6 여섯 항목 중 3건은 이미 완료**돼 있었다(§6-1 `/mova/movies`
필터 UI, §6-2 죽은 컴포넌트 4개, §6-3 `ActorInMovieSchema.character_name` —
문서가 지적한 synopsis 하드코딩도 해결됨). 남은 마이페이지 3건을 구현.

### 수정/구현(추가②)

**0) 보안 — `GET /mova/mypage/{user_id}` 무인증 노출(작업 중 발견)**
- 가드가 전혀 없어 **user_id만 알면 남의 닉네임·AI 추천 기록·검색 기록을
  조회 가능**했다. 프로덕션에서 `curl .../mova/mypage/1` → 200 + 실제 개인
  데이터로 재현 확인. 2026-07-28 `adress` 건과 같은 유형.
- 이번 작업이 여기에 리뷰·시청 통계를 **더 얹는 것**이라 유출 범위를
  넓히게 되므로 사용자 확인 후 함께 수정 — `require_user` + 본인 확인(403),
  프론트 3계층 토큰 배선(`authHeader()` → `route.ts` → 백엔드).
  `.claude/rules/security/auth.md` 절차 그대로.

**1) 활동 요약(§6-6)**: `watched_count`/`review_count`/`average_rating`.
`user_actions`는 행동 로그라 같은 영화가 여러 번 쌓이므로(UNIQUE 없음)
`count(distinct movie_id)`로 집계. 별점 없이 본문만 쓴 리뷰가 허용되므로
(2026-07-31) 개수는 전체, 평균은 `AVG`가 NULL을 자동 제외.

**2) 내 리뷰 목록(§6-4)**: 최근 20건, `movies` JOIN으로 제목·포스터 동반.
별점/본문 각각 nullable이라 조건부 렌더.

**3) 취향 편집(§6-5)**: 백엔드에 `preferred_genres` 수정 경로가 아예 없던
항목. **별도 엔드포인트 대신 기존 `PATCH /viewer/profile/{id}`를 부분 수정
으로 확장** — 프록시(`app/api/viewer/profile/route.ts`)가 이미 바디를 그대로
넘겨주고 있어 새 프록시·클라이언트 경로가 불필요했다(처음엔
`/{user_id}/preferred-genres`로 만들었다가 이 사실을 확인하고 되돌림).
둘 다 생략 시 400. 장르 선택지는 프론트 하드코딩 12종이 아니라 **실 DB
`tags` 라벨 기준 16종**(실측: 액션 691·드라마 652…, 프론트 상수엔 DB에 없는
"뮤지컬"이 있고 모험·판타지·가족 등 큰 장르가 빠져 있었음).

**4) `/mova` 랜딩 헤더 정렬**: 사용자 스크린샷 지적 — 랜딩만 네비가
`inset-x-0 justify-center`라 우측으로 밀려 보이고 활성 밑줄도 없었다.
공통 `MovaHeader`와 같은 좌측 정렬(`left-32` — 랜딩 로고가 `size="md"`라
공통 헤더 `left-28`보다 한 단계 넓게) + `mova-nav-active` 밑줄로 통일.

**5) 부수 — `CLAUDE.md` 테스트 명령 정정**: 전체 스위트 실행 시
`test_korean_ai.py`가 실패해 조사한 결과, 내 변경과 무관한 사전 존재 문제
였다(stash 후 재현 확인). 원인은 `apps/titanic/tests/conftest.py`의 ollama
자동 skip이 `markexpr`이 **비어 있을 때만** 걸리는데, `CLAUDE.md`가 표준
명령으로 안내하는 `-m "not gpu"`가 markexpr을 채워 자동 skip을 꺼버리는 것.
문서를 `-m "not gpu and not ollama"`로 정정(테스트 코드는 마커가 이미
올바르게 붙어 있어 안 건드림).

### 오류·막힌 점(추가②)
- `UserPrincipal`에 `role` 필드가 있는 줄 알고 테스트를 썼다가 `TypeError` —
  실제 필드는 `user_id`/`username`뿐이었다.
- `apps/viewer`엔 테스트 디렉터리 자체가 없어 신설 + `pytest.ini` `testpaths`
  등록 필요했다.

### 산출물(추가②)
- 커밋 `742ff81`. 테스트 428개 전부 통과(신규 12건: mypage 라우터 4 +
  profile 라우터 8), import-linter 위반 baseline(4건)과 동일,
  `pnpm type-check` 클린. (`pnpm lint`는 eslint 미설치로 실행 불가 — 기존 상태)

### 작업 내용(추가③) — 2순위 origin_country + 국가·연도 필터, 그리고 **내가 낸 프로덕션 회귀**

사용자 지시로 백로그 2순위 착수. 착수 전 검증에서 백로그 전제가 낡았음을
확인했고, 작업 도중 **같은 날 내가 만든 회귀**를 발견해 복구했다.

### 수정/구현(추가③)

**1) 착수 전 검증 — 백로그 전제 정정**
- 백로그: "제작국 컬럼이 없어 '한국' 조건을 검증할 수단이 없음".
- 실측: 같은 날 추가한 `original_language='ko'`로 이미 검증 가능했다 —
  #9 정답 후보 7편(반도·마녀 2·휴민트·오케이 마담 등)이 그대로 쿼리됨.
- 표본 40편으로 `origin_country`(KR 포함) vs `original_language`('ko') 대조 →
  **불일치 0건**. 즉 한국 판별엔 추가 이득 없음. `origin_country`의 실익은
  **영어권 구분**(영국/미국은 둘 다 `en`)뿐임을 확인.
- **진짜 막힌 곳은 읽는 경로**: 인텐트 스키마에 국가·연도 필드가 아예 없고
  `search_tag_catalog`이 `keywords`/`actor_names`만 받는다. 프로덕션에서
  #9가 0카드인 것도 재확인. 사용자가 "컬럼까지 함께"를 선택해 둘 다 진행.

**2) `origin_country` 컬럼(PR #58)**: 마이그레이션 `20260807_0002`(JSONB —
TMDB가 공동제작을 `["US","GB"]` 배열로 준다), ORM/DTO/매퍼/양쪽 upsert 배선,
`backfill_origin_country_cli.py`. **TMDB가 빈 배열을 줘도 `[]`를 기록** —
NULL로 두면 "미백필"과 구분이 안 돼 매 실행마다 재조회된다.
`@>` 컨테인먼트 실측 검증: `["GB"]` 단독 13편 vs containment 23편 —
공동제작 10편을 정확히 잡아냄(배열 설계가 맞았음).

**3) 국가·연도 하드 필터 배선**: `intent_extraction`에 `must.countries`
(ISO 3166-1) + `year_min`/`year_max` 추가. Gemini 프롬프트뿐 아니라
**결정론적 추출**(정규식 — "한국"/"국내", "2020년대"/"90년대")도 넣어 LLM
응답이 비어도 동작하게 함. LLM이 지어낸 국가 코드는 화이트리스트로 거른다.
`search_tag_catalog`은 이 조건을 **완화하지 않고** 태그/배우 결과와 인기작
폴백 **양쪽 모두**에 적용 — 폴백에 안 걸면 "2020년대 한국 액션"에 헐리우드
인기작을 후보로 줘서 LLM이 전부 거절해 0카드가 된다.

### 오류·막힌 점(추가③)

**🔴 프로덕션 회귀 — 내가 만들고 내가 발견**
- 골든셋 기준선을 찍다가 15개 중 **9개가 0카드**, 나머지도 "Freek de
  Jonge"(네덜란드)·"Excitation au soleil"(프랑스) 같은 엉뚱한 결과인 걸 발견.
  오늘 넣은 언어 필터(ko/en)와도 모순이라 회귀로 판단하고 추적.
- **원인**: 오늘 `EMBEDDING_BACKEND=gemini`를 EC2 `.env`에 설정했는데
  재임베딩은 사용자 판단으로 보류된 상태였다 → **Gemini 쿼리 벡터를 nomic
  문서 벡터와 비교**하게 됨. 차원이 768로 같아 에러가 안 나고, 유사도
  **0.04짜리 무작위 이웃 8건**이 "정상 히트"로 반환돼 `hits`가 비지 않으니
  **정상 동작하던 태그 검색 경로를 통째로 건너뛰었다**(언어 필터도 이 경로에선
  우회됨). 로그의 `vector_search hits=8 top1=증오 score=0.046`이 결정적 증거.
- **복구**: EC2 `.env`를 `ollama`로 원복 + backend 재기동 → "액션 영화
  추천해줘"가 다크 나이트·탑건 매버릭·인셉션으로 정상화 확인.
- **재발 방지**: `HubRagInteractor.search_movies`에 유사도 하한 0.15 추가 —
  미만이면 잡음으로 버리고 태그 폴백으로 넘긴다(관측 잡음 0.04 ≪ 0.15 ≪
  정상 매칭 0.5+). 경고 로그로 "의미 공간 불일치 가능성"도 남긴다. 테스트 3건.
- **교훈**: 코드 주석·`.env.example`·PR 본문 세 곳에 "재임베딩 없이 백엔드를
  바꾸면 안 된다"고 써놓고, 정작 그 `.env`를 내가 바꿨다. 문서화는 방어가
  아니다 — 코드가 강제해야 한다(그래서 임계값을 넣음).

**🔴 백필 프로세스 재차 사망 — 2026-08-06과 같은 실수 반복**
- 위 회귀를 복구하려고 `docker compose up -d --force-recreate backend`를
  실행했는데, 그 컨테이너 안에서 돌던 origin_country 백필이 함께 죽었다
  (1103편 남은 시점). **2026-08-06 synopsis 백필에서 똑같이 겪고 "컨테이너
  재생성 전 백그라운드 작업 완료 여부부터 확인할 것"이라고 이 파일에 적어둔
  교훈을 그대로 반복**했다. 스크립트가 idempotent라 데이터 손상은 없었고
  이어받기로 재개.

**🟠 골든셋 측정이 Gemini 무료 티어 쿼터에 오염됨 — 측정 방법 문제**
- 배포 후 골든셋을 1초 간격으로 15개 던졌더니 0카드가 8건으로 오히려 늘어
  "개선이 회귀를 만들었나" 싶었는데, 로그 확인 결과 원인은 기능이 아니라
  **레이트 리밋**이었다: `Quota exceeded ... limit: 15, model:
  gemini-3.1-flash-lite`(분당 15요청). **챗 1건당 Gemini를 2회 호출**하므로
  (의도 추출 + 추천 생성) 15개를 빠르게 던지면 30콜이라 즉시 초과한다.
- 같은 쿼리(#9)가 단건 호출로는 3장, 배치에서는 0장으로 나온 게 단서였다.
  간격을 13초로 늘려 재측정.
- **부수 함의(프로덕션)**: 동시 사용자가 몇 명만 돼도 같은 한도에 걸린다 —
  실사용 부하에서 조용히 0카드가 되는 구조. 유료 티어 전환이나 의도 추출
  호출 축소(2회→1회)를 검토할 필요. 백로그 신규 항목으로 등록.

### 데이터(추가③)
- 골든셋 기준선(회귀 복구 후, 배포 전): 0카드 5건 = #5(전지현 — 레거시
  무태그 로우가 원인, 3순위 백로그)·#9·#10(90년대 로맨스)·#12·#15.
  회귀 상태에서 찍은 첫 기준선(0카드 9건)은 폐기.
- `origin_country` 백필 완료: 1991편 전량(NULL 23은 레거시 로우, 정상).
  KR 36 / GB **142** / 빈 배열 0. **GB 142편이 `origin_country`의 실익을
  실증한다** — `original_language`로는 전부 `en`이라 미국과 구분 불가였다.
  실제로 "영국 영화 추천해줘" → 해리 포터·트레인스포팅(전부 GB) 확인.
- #9 해결 확인: "2020년대 한국 액션 영화" → 마녀 2(2022)·오케이 마담(2020)·
  반도(2020). 배포 전 0카드에서 3카드 전부 조건 충족으로 전환.
- **골든셋 최종 비교(둘 다 13초 간격, 쿼터 오염 없음)**: 0카드 **5건 → 2건**.
  - 해결: **#9**(2020년대 한국 액션 → 마녀 2·오케이 마담·반도),
    **#10**(90년대 로맨스 → 타이타닉·비포 선라이즈·귀여운 여인),
    **#12**(혼자 볼 감성적인 영화 → 쇼생크 탈출·그린 마일)
  - 남은 0카드 2건은 둘 다 **기존에 알려진 원인**:
    - #5 "전지현 나오는 코미디" — 레거시 무태그 로우 12편에 장르 태그도
      배우 크레딧도 없어서(3순위 백로그가 근본 해결책)
    - #15 "상영시간 짧은 SF 드라마…" — `runtime` 컬럼 자체가 없음(골든셋
      문서 §1.5가 이미 "시스템이 검증 불가능한 조건"으로 규정)
  - 연도 필터 부수 효과로 **#8**(80년대 SF)도 제국의 역습·빽 투 더 퓨쳐·
    블레이드 러너로 정확해짐(1980·1985·1982 — 전부 구간 내).
- `origin_country` 분포(백필 중간): `["US"]` 222, `["GB"]` 13, `["JP"]` 11,
  `["KR"]` 9, `["FR"]` 7, `["IT"]` 6 …

### 작업 내용(추가④) — UI 감사 정리 + 선호 장르 온보딩(§1-a)

사용자 요청으로 `_docs/MOVA_UI_AUDIT.md`에서 완료 항목을 걷어내고 남은 것만
남긴 뒤, 그중 §1-a(취향 온보딩)를 구현했다.

### 수정/구현(추가④)

**1) UI 감사 문서 정리(145줄 → 89줄)**: 완료 8건을 걷어내고 미해결 11건만
남김. 남은 항목은 전부 코드·DB로 재실측. **원본의 오기 1건 정정** —
`movies.embedding`을 "채워짐(Gemini 768차원)"이라 적었으나 실측 **0/2014**.
유사 영화 추천(§4-a)이 "UI만 붙이면 되는 일"이 아니라 임베딩 백필이 선행인
작업이라는 뜻이라 우선순위 판단이 달라진다.

**2) 선호 장르 온보딩(§1-a)**
- **가입 폼이 아니라 로그인 후 홈 카드로 붙였다.** 실측 결과 사용자 4명 중
  **2명이 카카오·구글 OAuth 가입자**라 회원가입 폼을 아예 거치지 않는다 —
  폼에만 넣으면 그 절반과 기존 가입자가 영구히 미설정으로 남는다. 홈 카드는
  가입 경로와 무관하게 전원을 커버하고, 닫으면 localStorage 플래그로 재노출 안 함.
- 장르 칩을 `MovaGenrePicker`로 공용화 — 마이페이지 편집(2026-08-07 추가②)과
  온보딩이 같은 목록을 쓰게 함(따로 두면 실 DB `tags` 라벨과 드리프트한다).
- 프로필 조회 실패는 조용히 무시 — 온보딩은 부가 기능이라 홈을 막으면 안 됨.

**3) 🔴 `GET /viewer/profile/{user_id}` 무인증 이메일 노출 수정**
- 온보딩이 이 엔드포인트를 쓰게 되어 확인하다 발견 — 가드가 없어 user_id만
  알면 **남의 이메일**을 그대로 읽을 수 있었다(프로덕션에서
  `curl .../viewer/profile/1` → 200 + `ssuvisdev@gmail.com` 재현).
  **오늘 아침 고친 `/mova/mypage/{user_id}`와 정확히 같은 유형이 하나 더
  있었던 것.**
- `require_user` + 본인 확인(403) + 프론트 3계층 토큰 배선. 호출부가
  `/mypage` 한 곳뿐임을 확인 후 적용. 배포 후 401 전환 검증 완료.

### 오류·막힌 점(추가④)
- 없음(온보딩 자체는 기존 `PATCH /viewer/profile/{id}`를 그대로 써서 백엔드
  신규 작업이 없었다).

### 산출물(추가④)
- PR #61 머지·EC2 배포. 테스트 454개 통과(신규 3건 — GET 401/403/200),
  import-linter baseline 동일, `pnpm type-check` 클린.
- 배포 후 검증: 무인증 `GET /viewer/profile/1` → **401**, 회귀 스모크
  (랭킹·목록·챗) 전부 200.

### 작업 내용(추가⑤) — 라우터 무인증·IDOR 전수 조사

하루에 같은 유형(`user_id`를 받는데 소유권 검증이 없음)을 두 번 고치자
(마이페이지·프로필) 사용자가 나머지 라우터도 훑어달라고 요청. 60개 라우터
전수 조사.

### 수정/구현(추가⑤)

**조사 방법**: 라우터 60개에서 `require_user|require_admin|RoleChecker|
get_current_user` 부재 + `user_id` 사용을 교차해 후보를 좁힘. 무가드 45개
중 대부분은 정상 공개(로그인·가입·OAuth·공개 카탈로그·레슨 데모)라 제외.
`whoami`는 `RoleChecker`라는 다른 가드를 써서 첫 grep에 안 잡힌 **오탐**이었음.

**발견 3건, 전부 수정**:
1. **`/mova/watchlist/*` 4개 — 무인증 읽기+쓰기(가장 심각)**. `user_id`만
   알면 남의 찜 목록 조회는 물론 **추가·삭제까지** 가능했다(프로덕션 GET
   200 + 실 데이터 재현). 앞선 두 건은 읽기만 샜는데 이건 조작이 된다.
   쓰기 엔드포인트는 실데이터 변조라 프로덕션 테스트는 안 했다.
2. **`PATCH /mova/picks/{pick_id}/feedback` — IDOR**. 코드 TODO·`auth.md`
   §5에 "복사하지 말 것"으로 이미 기록돼 있던 항목. 소유권을 리포지토리
   `WHERE id=? AND user_id=?`로 한 번에 판정하고, 없는 pick과 남의 pick을
   **구분해 알려주지 않는다**(id를 훑어 존재를 캐내는 것 방지).
   부수 확인: pick 270개 중 **265개가 익명**(user_id NULL)이라 가드를 걸면
   대부분이 갱신 불가가 되는데, **프론트에 호출부도 프록시도 없어**
   (`app/api/mova/picks` 자체가 없음) 실사용 영향이 없음을 확인하고 진행.
3. **`POST /mova/chat` — 바디 `user_id` 무검증**. 임의 값을 넣으면 그 사람의
   과거 대화·선호로 개인화된 답을 받고 **그 사람 이력에 기록까지 남았다**.
   비로그인 사용은 유지해야 해서 `optional_user` 가드를 신설 — 토큰이 있으면
   신원을 주고 없으면 익명. **토큰이 붙었는데 무효면 익명 강등이 아니라 401**
   (개인화가 왜 끊겼는지 알 수 있어야 한다).

**부수**: `.claude/rules/security/auth.md` §5를 갱신 — "미해결 사례"로
적혀 있던 picks IDOR이 해결됐고, 대신 참고 구현 두 가지(라우터 대조 /
쿼리 소유권)와 `optional_user` 사용 지침을 명시.

### 오류·막힌 점(추가⑤)
- 테스트에서 `WatchlistDto(items=[], total=0)`·`ChatResponseDto(...)` 필드를
  추측해 썼다가 실제 시그니처와 달라 실패 — 실제 DTO 확인 후 정정.

### 산출물(추가⑤)
- PR #63 머지·EC2 배포. 테스트 461개 통과(신규 11건). **가드를 일부러 빼서
  테스트가 실제로 실패하는지 확인 후 원복**(통과만 확인하면 무의미하므로).
- 배포 후 프로덕션 검증: `GET /mova/watchlist/1` → **401**,
  `GET /mova/watchlist/1/check/18` → **401**,
  `PATCH /mova/picks/1/feedback` → **401**, 익명 챗은 그대로 200(카드 3개).
  바디에 `user_id: 1`을 넣은 챗이 `chat` 테이블에 **user_id NULL(익명)로
  기록**되는 것까지 확인 — 수정 전이라면 1번 사용자 이력에 쌓였을 요청.

### 부수 발견 — `origin/main`이 로컬 세션 인지보다 앞서 있던 사고
- 이 세션 시작 시 안내한 백로그 우선순위(1순위 hub_knowledge Phase 2 "착수
  전", 0순위 Cloudflare Tunnel 502 "미해결")가 **실제로는 이미 다른
  세션이 같은 날(2026-08-06 저녁) `main`에 직접 커밋해 둘 다 완료된
  상태**였다는 걸 `git fetch`로 뒤늦게 발견. 502의 진짜 원인은 AWS
  보안그룹이 아웃바운드 UDP 7844(QUIC)를 TCP로 잘못 설정해 막고 있던
  것 — 보안그룹 정정 후 QUIC 정상 협상 확인, 기존에 시도했던
  `--edge-ip-version 4`/`--protocol http2` 강제는 전부 근본 원인이
  아니었던 우회였음이 판명돼 제거됨. hub_knowledge는 `limit=100`
  제거 + 영화별 개별 커밋으로 EC2 프로덕션 2014편 전량 백필 완료.
  **교훈**: 세션 시작 시 로컬 브랜치만 보고 백로그 상태를 판단하면
  다른 세션의 병렬 작업을 놓칠 수 있음 — `git fetch && git log
  <local>..origin/main`으로 대조하는 습관 필요(2026-08-06에도 한 번
  같은 패턴 있었음, 재발).

---

## 2026-08-06

### 작업 내용
- PROGRESS.md 1순위(mova 카탈로그 커버리지 확장) 착수: `bulk_import_movies.py`로
  TMDB popular 53~102페이지(960편) 실전 수집 후, Phase 1 골든셋 15개를
  동일 조건(EC2 Gemini 경로)으로 재검증해 확장 효과를 실측.
- 세션 시작 시 로컬 `suvisdev` 브랜치가 `origin/main` 대비 4커밋 뒤처져
  있던 걸 발견(EC2에서 직접 반영된 lora 전환 관련 커밋들) — `git merge
  origin/main`으로 동기화 후 진행.

### 수정/구현
- EC2 사전 점검: alembic head `20260805_0001`(character_name TEXT
  마이그레이션) 확인, `session.rollback()` 5곳·per-member try/except
  배포 확인, 디스크 여유(12GB/30GB) 확인.
- 시험 배치(53~54페이지, 40편) 선행 실행 후 이상 없음 확인 → 본배치
  (55~102페이지, 48페이지)를 `docker compose exec -d`로 EC2 백그라운드
  실행, 완료까지 SSH 폴링으로 대기.
- 골든셋 재검증을 위해 EC2 `RECOMMENDATION_BACKEND`을 `lora`(2026-08-05
  이후 기본값 변경분, 이 세션 시작 시 `git merge`로 처음 인지)에서
  `gemini`로 임시 전환(`.env` 백업 후 sed, `docker compose up -d
  --force-recreate --no-deps backend`) → 골든셋 15개 실행 → 검증 완료 후
  `lora`로 원복.
- 문서 갱신: `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md` §7 신설(집계
  비교표, #14·#6 재분류/재검토, `search_tag_catalog()` 근본 원인 4가지,
  레거시 무태그 로우 12편 목록), `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`
  백로그 재정렬(카탈로그 확장 종결 + 신규 트랙 3개 추가 + 8번째 "구현과
  의도 갭" 항목).

### 오류·막힌 점
- **배치 완료 대기 로직이 한 번 오탐**: 완료 마커를 `\[bulk_import\] 완료`
  (넓은 패턴)로 기다렸는데, 진행 중 캐치된 예외(`HubRagInteractor` Ollama
  연결 실패 등)의 `logger.warning(..., exc_info=True)` 출력에 포함된
  "Traceback (most recent call last):" 텍스트가 우연히 매칭돼 배치가 아직
  75페이지인데 대기가 먼저 끝남 — 완료 마커를 `완료 source=`(스크립트
  최종 요약 줄에만 나오는 문자열)로 좁혀 재대기해 해결. 스크립트 자체는
  끝까지 정상 실행 중이었음(중단 아님).
- **골든셋 재검증 결과가 가설과 반대로 나옴**: 카탈로그를 2배로 늘리면
  Phase 1의 "커버리지 부족" 실패 4~6건이 풀릴 것으로 예상했으나 실제로는
  0건 해소 — 코드 조사(`search_tag_catalog()`)로 원인을 배우 필터 부재·
  top-12 rating 컷·키워드 OR 결합·`origin_country` 부재로 특정. 이
  발견으로 카탈로그 확장 트랙을 종결하고 다음 세션 우선순위를 전면
  재배열함(PROGRESS.md).
- **레거시 무태그 로우 12편 발견**: 골든셋 실패 대상 영화(도둑들·윤희에게
  등)를 DB에서 직접 조회하다가, TMDB 배치 이전부터 존재했던 것으로 보이는
  `release_year=0`·비-TMDB slug·태그 0개 로우 12개(id 1056~1067) 발견 —
  title 매칭 시절 골든셋을 통과시키려 수동으로 끼워 넣은 임시 데이터로
  추정(확정 근거는 없음). grounded prompting 전환 이후 태그가 없어
  후보에 못 들어가는 죽은 데이터가 됨.

### 데이터
- EC2 실 DB, 배치 실행 전/후:
  - movies: 1067 → 2014 (+947 net, succeeded=960 attempts — 소량 재수집
    중복 추정)
  - actors: 7148 → 11945 (+4797)
  - characters: 10152 → 19348 (+9196)
  - movie_directors: 1141 → 2193 (+1052)
  - credits 백필 완전 실패 1건(`tmdb-64682`) — 배치 리포트 `failed=0`에는
    안 잡힘(백로그 "구현과 의도 갭" 8번째 항목으로 기록).
- 골든셋 15개 재검증: 통과 8·실패 7(이전 9/0/6 대비 통과 -1, #14 재분류).

### 산출물
- 문서: `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`(§7 신설),
  `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(백로그 재정렬 + 완료 항목
  추가), `_docs/WORK_LOG.md`(이 항목).

### 작업 내용(추가①) — 죽은 컴포넌트 트랙 종결(MovaGenreCatalog 배선) + synopsis 컬럼 신설 착수

UI 마무리 트랙으로 전환. 죽은 컴포넌트 4개 중 마지막 미판정이던
`MovaGenreCatalog`를 `/mova/main` 홈 피드에 배선(PR #43 머지 완료).
이어서 UI 저수확 3건 중 `movies.synopsis` 컬럼 신설을 character_name
패턴(2026-08-05, `9eb9c2e`/`5e8e022`/`6f594fc`) 그대로 재사용해 착수.

### 수정/구현(추가①)
- `MovaGenreCatalog` 배선: `fetchMovaMoviesFromApi()`→`apiMovieToMovaMovie()`
  →`groupMovaMoviesByGenre()` 기존 파이프라인 재사용, 신규 유틸 코드 없음.
  장르 19종 중 상위 8개만 슬라이스(`HOME_GENRE_ROWS`). `fetchHotRankings`와
  `Promise.all` 병렬 fetch(서로 다른 백엔드 엔드포인트라 병합 불가 확인).
  로컬 `pnpm dev`를 `NEXT_PUBLIC_API_URL=https://api.suvisdev.cloud`로
  프로덕션 API 겨냥해 기동, SSR HTML에서 8개 장르 행·포스터 카드 345개
  렌더 확인 후 종료.
- synopsis 컬럼(백엔드, 이번 항목에서 코드까지 완료 — EC2 배포·백필은
  다음 항목): 마이그레이션 `20260806_0001`(movies.synopsis TEXT NULL),
  ORM 컬럼, `MovieUpsertCommand`/`MovieDetailDto`/`MovieDetailSchema`에
  `synopsis` 필드 추가, `bulk_import_movies.py`·`import_interactor.py`
  양쪽 TMDB upsert 경로에 `synopsis=snap.overview` 배선(`chat_reply.py`의
  포스터 갱신 전용 upsert는 TMDB 재조회가 없어 미배선 — 의도적).
  `MoviesRepositoryPort`에 `list_missing_synopsis`/`update_synopsis` 신설
  (구현체가 `MoviesPgRepository` 하나뿐이라 다른 fake 영향 없음 확인).
  신규 `scripts/backfill_synopsis_cli.py`(`backfill_credits_cli.py`류
  이름 관례, `--limit`/`--dry-run`) — 영화 1편 처리 로직을
  `_backfill_one()`으로 분리해 AsyncMock으로 dry-run 단위 테스트 가능하게
  구성(`bulk_import_movies.py`식 인라인 오케스트레이션과 달리 테스트
  가능한 형태 선택).
- 테스트: `test_studio_movies_dto.py`에 synopsis 관통 2건(from_orm/
  to_schema) 추가, 신규 `test_backfill_synopsis_cli.py` 6건(인자 파싱 2 +
  `_backfill_one` 4 — non-tmdb 스킵/dry-run 미기록/실행 시 기록/overview
  빈 문자열 스킵). `MovieDetailDto`에 `synopsis` 필수 필드 추가로
  `test_chat_reply_service.py`의 `_movie()` 헬퍼가 깨진 것 발견해
  `synopsis=None` 추가로 수정(리네임 드리프트, 도메인 재설계 아님).
  `apps/mova/tests` 108개 전부 통과, import-linter 위반 0건(mova 관련
  — pre-existing ontology↔mova 위반 1건은 `core/matrix/grid_oracle_
  database_manager.py`가 원인이라 이번 변경과 무관, 그대로 둠).

### 오류·막힌 점(추가①)
- `MovieDetailDto`에 `synopsis`를 기본값 없는 필수 필드로 추가하자
  `test_chat_reply_service.py`가 `MovieDetailDto(...)`를 직접 생성하는
  헬퍼(`_movie()`)에서 즉시 깨짐 — `from_orm()`을 거치지 않는 테스트
  전용 생성 경로가 있다는 걸 이번에 발견, `synopsis=None` 추가로 해결.

### 산출물(추가①)
- 커밋: `7972c53`(MovaGenreCatalog 배선, PR #43 머지) — synopsis 백엔드
  커밋은 EC2 배포까지 마친 뒤 별도 기록(다음 항목).

### 작업 내용(추가②) — synopsis EC2 배포·백필 + mova 챗 502 긴급 수정 + MovaHeroBanner 삭제

synopsis 백엔드(추가①에서 코드 완료)를 PR #44로 머지 후 EC2 배포·백필
진행 중, 사용자가 실사용 중 `/mova/main`에서 두 가지를 신고 — (1)
AI 챗바가 502로 응답 없음, (2) 히어로 배너("오늘의 픽" 기생충 카드)
삭제 요청. 둘 다 이번 항목에서 처리.

### 수정/구현(추가②)
- synopsis 배포: EC2 `git pull`(안전 병합) → `docker compose up -d --build
  backend` → `alembic upgrade head`(20260805_0001→20260806_0001) → curl로
  `GET /mova/movies/tmdb-1368337` 응답에 `synopsis` 필드 존재(백필 전
  `null`) 확인 → `backfill_synopsis_cli.py --limit 3 --dry-run` 시험
  성공(실제 한국어 줄거리 확인) → 전체 백필 백그라운드 실행.
- **사고 — 백필 도중 컨테이너 재기동으로 프로세스 중단**: RECOMMENDATION_
  BACKEND를 gemini로 전환하려고 `docker compose up -d --force-recreate
  --no-deps backend`를 실행했는데, 이게 그 안에서 `docker compose exec -d`
  로 돌고 있던 synopsis 백필 프로세스를 함께 죽였다(컨테이너 재생성 =
  `/tmp` 로그 파일도 같이 사라짐). 진행 상황을 DB로 직접 확인한 결과
  1991편 중 209편까지만 채워진 상태로 중단 — 데이터 손상은 없음(스크립트가
  idempotent라 `list_missing_synopsis()`가 이미 채워진 209편은 자동
  제외) — 즉시 재실행으로 이어받기.
- **mova 챗 502 진단**: 백엔드 로그에서 `POST https://lora.suvisdev.cloud
  /generate "HTTP/1.1 530 <none>"` 확인 — Cloudflare 530(터널/오리진 완전
  무응답). 이 세션이 도는 호스트엔 `lora-server.service` 자체가 없어(다른
  물리 노트북) 원격 재기동 불가 — 문서화된 수동 폴백 절차대로
  `RECOMMENDATION_BACKEND=gemini` 전환 + backend 재기동으로 즉시 정상화
  (`POST /mova/chat` 200 확인, 실제 추천 3건 응답).
- **MovaHeroBanner 삭제**: 사용자 확인 결과 섹션 전체 삭제(어제 배선한
  기능 자체를 되돌리는 것) — `/mova/main`에서 import·사용 제거, 다른
  사용처 없음 확인 후 `mova-hero-banner.tsx` 파일 삭제. `fetchHotRankings`
  호출은 `MovaRankingSection`(사이드바)이 여전히 써서 그대로 유지.
  `pnpm type-check` 클린.

### 오류·막힌 점(추가②)
- 위 "백필 도중 컨테이너 재기동" 사고 — 원인은 배경 작업(synopsis 백필)이
  떠 있는 상태에서 그 프로세스가 사는 컨테이너 자체를 재생성하는 명령을
  실행한 순서 실수. 재발 방지: 컨테이너 내부에서 장시간 백그라운드
  스크립트가 돌고 있을 땐 그 컨테이너를 `--force-recreate`하기 전에
  반드시 완료 여부부터 확인할 것.

### 데이터(추가②)
- synopsis 백필: 1991편 대상 중 첫 실행에서 209편 반영 후 중단, 이어받기
  실행 진행 중(완료 결과는 다음 항목 예정).

### 작업 내용(추가③) — synopsis 백필 완료 + 프론트 하드코딩 제거·배포

이어받기 백필 완료 확인 후 프론트(`fetchMovaTitle()`) 하드코딩 제거,
로컬 실측 검증까지 마치고 main 머지.

### 수정/구현(추가③)
- 백필 최종 결과: `succeeded=1578 failed=3 skipped=201`(이어받기 실행분).
  누적 `movies.synopsis IS NOT NULL` = 1787/1991(tmdb 원산 기준) — 나머지
  204는 skipped 201(TMDB `overview` 자체가 빈 문자열인 정상 케이스) +
  failed 3(`tmdb-41387`/`tmdb-220289`/`tmdb-13597`, TMDB fetch 실패 —
  재시도 가능, 이번엔 미처리).
- 프론트: `lib/mova-api.ts`의 `MovieDetailApiRow`에 `synopsis: string | null`
  추가, `fetchMovaTitle()`의 `synopsis: ""` 하드코딩을 `row.synopsis ?? ""`
  로 교체. **목록 매퍼(`apiMovieToMovaMovie()`, 651행)의 `synopsis: ""`는
  의도적으로 안 건드림** — 목록 응답(`MovieListItemSchema`)엔 애초에
  synopsis 필드가 없음(상세 전용 스코프로 결정한 대로). `MovaTitleView.tsx`
  는 이미 `movie.synopsis ? <섹션> : null` 조건부 렌더가 돼 있어 코드
  변경 불필요 — 빈 문자열이면 섹션 자체가 안 뜨는 기존 동작 그대로 재사용.
- 검증: 로컬 `pnpm dev`(`NEXT_PUBLIC_API_URL=https://api.suvisdev.cloud`)로
  `tmdb-1368337`(오디세이) 상세 페이지 SSR HTML에서 "줄거리" 섹션 +
  실제 시놉시스 텍스트 렌더 확인. `pnpm type-check` 클린.

### 산출물(추가③)
- 커밋 `614a1d1`(PR #46, main 머지 완료).

### 작업 내용(추가④) — mova 챗 0추천 실사용 버그 진단 + /mova/movies 필터 UI 확장

사용자가 실사용 중 `/mova/chat`에서 "주말에 몰아볼 시리즈 느낌 영화" 요청에
텍스트는 "준비했습니다"라면서 카드가 0개 나오는 걸 신고 — 원인만 진단하고
수정은 다음 세션으로 미룸(사용자 판단). 이어서 `/mova/movies` 필터 UI
확장(연도·평점·정렬) 진행.

### 수정/구현(추가④)
- **0추천 버그 진단(수정 안 함, 관찰만)**: 백엔드 로그 확인 결과 Gemini는
  실제로 적절한 답(무빙/오징어 게임/수리남 — "시리즈 느낌" 요청에 정확히
  부합하는 실존 작품)을 생성했으나, `search_tag_catalog()`가 "주말"·
  "몰아보기"·"시리즈" 같은 키워드로는 장르/무드 태그에 전혀 안 걸려
  후보를 0개 만들었고, Gemini가 빈 후보 목록 대신 자기 지식으로 만든
  `movie_id`(1,2,3 같은 그럴듯한 값)가 "제시한 적 없는 id"로 안전장치에
  걸려 전부 드롭됨 — reply 텍스트만 자신 있게 나가고 카드는 0개. 오늘
  §7.3에서 찾은 `search_tag_catalog()` 구조적 결함(배우 미지원·top-12
  컷·키워드 OR)과 **완전히 같은 근본 원인**이 실사용에서 재현된 것 —
  기존 백로그(2순위) 우선순위 재확인만 하고 이번 세션엔 수정 안 함
  (사용자가 필터 UI를 먼저 하기로 결정).
- **release_year 필터 — 정확 일치 → 범위(min/max)로 백엔드 확장**:
  원래 계획(연대 드롭다운: 2020년대/2010년대/2000년대/그 이전)이 백엔드의
  `release_year == 특정 연도` 정확 일치만 지원하는 것과 충돌함을 사전
  조사에서 발견 — 사용자 확인 후 `MovieFilterQuery.release_year`를
  `release_year_min`/`release_year_max`로 교체(유일한 호출부인
  `studio_movies_router.py`만 영향, 다른 곳·테스트 무영향 확인),
  `list_movies()`도 범위 조건으로 교체. `apps/mova/tests` 108개 전부 통과.
- **min_rating 버킷값 스케일 오류 사전 수정**: 사용자 계획엔 "7.0+/8.0+/
  9.0+"였으나 실측 결과 `rating`은 0~5 스케일(백엔드 `min_rating` 검증도
  `ge=0.0, le=5.0`, 실 DB `min=0 max=5 avg=3.33`)이라 그대로 쓰면 결과가
  전부 0건이거나 422 에러가 날 상황 — 3.5+(1062편)/4.0+(235편)/
  4.5+(8편)로 스케일에 맞게 교정.
- 프론트 `/mova/movies` 페이지: 장르 탭까지 포함해 **URL query param
  sync 신규 추가**(기존엔 장르 탭조차 URL에 없어 새로고침하면 항상
  "전체"로 리셋됐음 — `useSearchParams`/`useRouter().replace()`로
  genre·decade·min_rating·sort 전부 URL에 반영, 뒤로가기 복원 가능).
  `Suspense` 경계로 `useSearchParams()` 요구사항 충족. age_rating/platform
  은 방침 (i)대로 비활성 select + `title` 툴팁("데이터 준비 중")으로
  흔적만 남김(실측 0/2014 재확인). "필터 초기화" 버튼(필터 활성 시에만
  노출). `lib/mova-api.ts`의 `fetchMovaMovies` 필터 타입도
  `release_year_min`/`max`로 함께 교체. `pnpm type-check` 클린.

### 오류·막힌 점(추가④)
- 사전 조사 없이 계획대로(연대 드롭다운 + 7~9점 버킷) 바로 구현했다면
  둘 다 실제로 작동 안 했을 것 — release_year는 백엔드 정확 일치 제약,
  rating은 스케일 불일치. 두 건 다 구현 전 실측(백엔드 코드 읽기 + DB
  쿼리)으로 미리 잡음.

### 작업 내용(추가⑤) — `search_tag_catalog()` 개선(1순위 착수)

필터 UI 완료 후 사용자가 이어서 진행을 요청 — 오늘 골든셋 재검증(§7.3)과
실사용 재현(추가④)으로 이미 확정된 `search_tag_catalog()` 구조적 결함을
수정.

### 수정/구현(추가⑤)
- **배우 이름 매칭 추가**: `ChatRepositoryPort.search_tag_catalog()`에
  `actor_names: list[str] | None` 키워드 인자 신설.
  `ChatPgRepository`가 `characters`+`movie_directors`를 `actors`와 JOIN해
  배우/감독 이름으로도 후보를 찾도록 확장(기존엔 `tags.label` ILIKE만
  검색해 배우 이름이 애초에 매칭 대상에 없었음).
- **AND→완화 하이브리드**: 태그 매칭 집합과 배우 매칭 집합이 둘 다 있으면
  **교집합**(둘 다 만족)을 우선 쓰고, 교집합이 0건이면 **합집합**으로
  완화 — "전지현 코미디"처럼 배우+장르가 둘 다 있는 카탈로그 항목이
  있으면 정밀하게, 없으면 최소한 배우 후보나 장르 후보 중 하나라도
  제공.
- **인기작 폴백 신설**: 태그·배우 매칭이 전부 0건이면(예: "주말에
  몰아볼 시리즈"처럼 순수 무드 키워드) 완전히 빈 후보를 주는 대신
  평점순 인기작을 폴백으로 반환 — Gemini가 카탈로그에 없는 movie_id를
  스스로 지어내고 enrich 단계에서 전부 드롭돼 "reply는 자신있는데 카드
  0개"가 되던 패턴(추가④에서 실사용 재현)을 완화.
- `market_chat_interactor.py`: `intent["search_filters"]`의
  `must.actors`+`similar_to.actors`를 합쳐 `actor_names`로 전달, 후보
  개수도 12→16으로 소폭 완화.
- **의도적으로 안 한 것**: 순수 다중 장르 AND(예: "SF+드라마" 둘 다
  만족, §7.3 결함 (3))는 이번 스코프 밖 — 배우+장르 조합만 교집합
  로직을 적용했고, 일반 키워드끼리의 AND 엔진은 별도 설계가 필요해
  보류.
- 테스트: `market_chat_interactor.py`의 rag 경로에서 `must.actors`/
  `similar_to.actors`가 `search_tag_catalog(actor_names=...)`로 정확히
  전달되는지 검증하는 신규 테스트 2건(`test_market_chat_interactor.py`).
  리포지토리 SQL 조합 로직(교집합/합집합/폴백) 자체는 이 저장소 관례상
  실 DB 없이 단위테스트하지 않음(`movies_pg_repository.py`의 다른
  필터 로직들도 동일 — 기존 테스트 커버리지 패턴을 따름). `apps/mova/tests`
  110개 전부 통과, import-linter mova 관련 위반 0건.
- **EC2 배포·실 쿼리 재검증**: 배포 후 골든셋 실패 쿼리 재실행 —
  "키아누 리브스 액션영화" 실패(0개)→통과(존 윅/매트릭스/**스피드**,
  top-12 컷에 가려졌던 바로 그 영화 포함 3/3 grounded), "송강호 스릴러"
  는 이제 우연이 아니라 배우 매칭으로 정당하게 근거 있음(기생충/살인의
  추억), 실사용 신고 버그("주말에 몰아볼 시리즈")도 인기작 폴백으로
  카드 3개 정상 반환. "전지현 코미디"는 여전히 실패(정직한 0개) —
  원인이 레거시 무태그 로우(4순위→3순위 백로그)로 확인, 배우 매칭
  자체는 정상 작동하지만 그 로우들엔 배우 크레딧이 아예 없음.

### 작업 내용(추가⑥) — mova 랜딩(`/mova`) 상단 네비 추가 + "마이" 로그인 게이트

사용자 요청: "mova 메인페이지 상단에 홈·컬렉션 부분"(확인 결과 `/mova`
랜딩 스플래시 페이지를 지칭 — 이 페이지는 자체 헤더를 써서 홈/영화/
컬렉션/랭킹/마이 네비가 아예 없었음) + "마이페이지는 로그인하면
나타나게".

### 수정/구현(추가⑥)
- `MovaHeader`(`/mova/main` 등 기존 네비 보유 페이지들): `getSuvisSession()`
  으로 로그인 여부 판정(`MovaLoginButton`과 동일 패턴) 후 `MOVA_NAV`에서
  `/mova/mypage`(마이) 항목을 로그아웃 상태면 필터링 — 기존엔 로그인
  여부 무관하게 항상 노출됐음.
- `/mova/page.tsx`(랜딩): 기존엔 로고+검색+로그인 버튼만 있던 자체
  헤더에 `MOVA_NAV` 재사용 네비 신규 추가 — `lg:` 이상은 헤더 행 중앙에
  인라인, 그 미만은 `MovaHeader`의 모바일 네비와 동일 패턴(헤더 아래
  가로 스크롤 행)으로 반응형 분리. "마이" 항목은 여기도 동일하게
  로그인 게이트.
- 로컬 `pnpm dev`(프로덕션 API 겨냥) SSR HTML로 `/mova`·`/mova/main`
  둘 다 로그아웃 상태에서 홈/영화/컬렉션/랭킹만 렌더되고 "마이"가
  빠지는 것 확인. `pnpm type-check` 클린.

### 작업 내용(추가⑦) — `/mova/collections`·`/mova/rankings` 실태 조사 + 컬렉션 시드 5개

네비 정리 후 사용자 요청으로 두 페이지 실태 조사(30분 스코프) 진행 —
결과: 컬렉션은 백엔드 전 레이어 완성·데이터만 0(case c), 랭킹은 이미
정상 작동 중(case d, 예상 밖 정상). 조사 직후 사용자 승인으로 컬렉션
시드 5개 큐레이션까지 같은 사이클에서 실행.

### 수정/구현(추가⑦)
- **실태 조사**: `collections`/`movies.collection_id` 둘 다 실측 0 —
  다만 클린 아키텍처 전 레이어(domain/dto/port/interactor/repository/
  orm/router/schema)와 `POST/GET /collections` 라우트는 이미 완성돼
  있었음. 영화→컬렉션 **배정** API/CLI만 없었음(스키마 생성 스크립트뿐).
  랭킹은 `chat_trend`(6시간 주기 스케줄러, 실제 채팅 집계)·`box_office`
  (KOFIC) 둘 다 curl로 실 데이터 확인, 코드 변경 불필요.
- **컬렉션 시드 5개**(SQL 직접, `scripts/seed_collections.sql` 신규):
  크리스토퍼 놀란의 세계(12편, 놀란 전 필모그래피)·90년대 로맨스(8)·
  SF 클래식(8)·가족과 함께(8)·액션의 정수(8) = 총 44편.
  `movies.collection_id`가 단일 FK라 데이터 정찰 중 발견한 겹침 3건
  (프레스티지: 놀란∩SF클래식, 다크나이트·인셉션·스타워즈5:
  놀란/SF클래식∩액션)을 우선순위(감독 기반 > 시대+장르 > 장르 단독)
  대로 상위 컬렉션에 배정하고 하위 후보 목록에서 사전 제외. 부수 발견:
  가족/액션 태그의 평점 상위권에 TMDB 한글 타이틀 미확보작(한자 원제
  그대로 노출, 예: 仙逆剧场版)이 다수 섞여 있어 정규식으로 제외 후
  재선정 — "저수확 순위 판단" 없이 실측하며 즉석 큐레이션 판단.
  `cover_image_url` 컬럼 자체가 없음을 사전 확인(스키마: slug/name/
  description만) — 프론트도 애초에 커버 이미지를 렌더하지 않아 갭
  없음, 이미지 없이 시드.
- 검증: SQL 실행 직후 컬렉션별 count 쿼리로 12/8/8/8/8 정확히 일치
  확인(겹침 있었다면 마지막 UPDATE가 덮어써 합계가 안 맞았을 것).
  로컬 `pnpm dev`(프로덕션 API)로 목록 페이지 5개 카드 + 놀란 상세
  페이지 영화 목록 SSR 렌더 확인.

### 작업 내용(추가⑧) — `/mova/rankings` 순위 뒤죽박죽 버그 수정

사용자가 "랭킹 순위가 이상하다, 중간에 1위가 또 나온다"고 신고 — 원인
조사·수정.

### 오류·막힌 점(추가⑧)
- `GET /mova/rankings/hot?source=chat_trend&limit=20`을 직접 호출해
  재현: `rank`가 1~10까지 갔다가 **다시 1로 돌아가서** 1~10을 반복.
  `ranked_at` 필드를 같이 찍어보니 원인이 바로 나옴 — 앞 10개는
  `ranked_at=2026-08-06`, 뒤 10개는 `ranked_at=2026-08-05`. `limit=30`
  으로 넓혀보니 `2026-08-04`까지 3일치가 누적돼 있었음.
- 근본 원인: `save_chat_trend_ranking()`/`save_box_office_ranking()`은
  스냅샷 저장 시 **그날(`ranked_at`) 행만** 지우고 새로 넣는 구조라
  이전 날짜 행이 테이블에 계속 쌓이는데, 조회 쪽(`get_hot()`)이
  `source`로만 필터링하고 `ranked_at`을 걸지 않아서 여러 날짜의
  `rank 1~10`이 그대로 섞여 나왔다 — `limit`이 하루치(10)보다 크면
  항상 재현되는 구조적 버그(오늘 `/mova/movies` 페이지가 `limit=20`을
  쓰니 실사용자가 100% 겪는 상태였음).

### 수정/구현(추가⑧)
- `RankingsPgRepository.get_hot()`에 `ranked_at == (해당 source의 최신
  ranked_at 서브쿼리)` 조건 추가 — 항상 가장 최근 스냅샷 한 건만
  반환하도록 수정. `order_by`도 `ranked_at desc, rank asc`에서
  `rank asc` 단독으로 단순화(이미 단일 날짜로 좁혔으니 불필요).
  포트 docstring에 원인 남김.
- 리포지토리 SQL 로직이라 이 저장소 관례상(다른 mova 리포지토리들도
  동일) 실 DB 없이 단위테스트 안 함 — EC2 배포 후 실 API 응답으로
  검증(다음 항목). `apps/mova/tests` 110개 회귀 통과.

### 작업 내용(추가⑨) — `_docs/` 문서 정리(백로그 스테일 항목 제거 + WORK_LOG 압축)

사용자 요청으로 `_docs/` 안의 "해야 할 일"을 한곳(PROGRESS.md 백로그)에
모으고, WORK_LOG의 중복 서술을 정리. 실측 결과 WORK_LOG 자체엔 문자
그대로 복붙된 중복 문단은 없었음 — 대신 PROGRESS.md 백로그에 이미
완료됐는데 안 지워진 항목들과, 같은 내용이 PROGRESS.md 안에서 두 번
서술되는 부분을 정리.

### 수정/구현(추가⑨)
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 백로그: 완료된 `movies.synopsis`
  항목 삭제(08-06 완료됨 섹션과 중복), 카탈로그 확장 종결 서술이 두 곳
  (722행 종결됨 노트 / 782행 취소선 항목)에 반복되던 걸 하나로 통합,
  `hub_knowledge` 백필 스크립트 정비 항목을 1순위 "시작 조건"과 중복이라
  포인터로 축약, `upsert_movie` except 조사 항목(37줄)을 저장소 자체
  규칙("완료된 항목은 WORK_LOG 날짜만 남김")대로 결론+링크로 축약,
  "mova 대량 수집 실제 실행"이 08-05·08-06에 이미 실행됐는데 "아직 안 함"
  으로 스테일하게 남아있던 걸 갱신, "어드민 백엔드 인증 공백" 항목이
  완료됨 섹션과 완전 중복이라 삭제.
- `_docs/MOVA_UI_QUICK_WINS.md` §5: synopsis·`MovaGenreCatalog`·필터 UI
  확장 3건이 08-06에 완료됐는데 미완료로 남아있던 걸 취소선+완료 표기.
- WORK_LOG 자체는 08-05 추가⑬의 "오류·막힌 점" 첫 줄이 바로 위 "수정/구현"
  에서 이미 상세히 설명한 지시서 전제 3개(venv 경로·cloudflared 설치
  경로·EC2 프로젝트 경로)를 요약으로 한 번 더 반복하던 것 1건 발견해 제거.
  그 외엔 각 "추가N" 항목이 실제로 서로 다른 작업이라 압축할 반복이
  거의 없었음.

### 산출물(추가⑨)
- 문서만 수정, 코드 변경 없음. (커밋은 이 항목 갱신 이후 세션 종료
  시점에 진행 — 아래 산출물 참고)

### 작업 내용(추가⑩) — EC2 기존 Cloudflare Tunnel 502 재조사(0순위) — 근본 원인 특정, 완전 해결은 못 함

PROGRESS.md 0순위(약 50% 확률 502)를 실제로 붙잡고 원인 규명 시도.
결과적으로 **진짜 설정 오류 하나를 찾아 고쳤지만, 그것만으로는 완전히
해소되지 않았고 남은 증상은 Cloudflare 쪽 요인(SJC PoP 예정 유지보수와
시간대가 겹침)일 가능성이 높다고 잠정 결론**.

### 오류·막힌 점(추가⑩)
- **재현율이 기록보다 나쁨**: 세션 시작 시점 재현 결과 50%가 아니라
  이 세션의 테스트 클라이언트 기준 **100% 502**(EC2 자신이 보내는
  요청은 반대로 100% 성공). `readyConnections: 4/4`(cloudflared 자체
  보고), nginx·도커 브리지 iptables·nsenter로 cloudflared 컨테이너의
  정확한 네트워크 네임스페이스에서 실제 요청 헤더(Host·CF-Ray·
  CF-Connecting-IP 등)까지 재현해도 즉시 200 — origin은 완전히 무죄로
  확인됨.
- **진짜로 찾은 설정 오류**: AWS 보안 그룹 아웃바운드 규칙에 UDP 7844
  (QUIC)가 **TCP로 잘못 설정**돼 있었음(2026-08-02부터 QUIC precheck이
  매번 실패해온 원인). 사용자가 UDP로 정정 + TCP 7844도 별도 규칙으로
  추가(양쪽 다 열어둠) → cloudflared 재기동 후 `UDP Connectivity ...
  PASS QUIC connection successful`로 확정 확인. `docker-compose.yaml`의
  `--protocol http2` 강제도 이 시점에 제거해 QUIC 자동 협상으로 복귀
  (커밋 `e8067d4`/`151d8eb`).
- **그런데도 외부 요청은 그대로 100% 502**: QUIC 수정 후에도 무변화 —
  `auth.suvisdev.cloud`(같은 터널, `auth:9000` 직결)는 계속 100% 성공,
  `api.suvisdev.cloud`(`nginx:80` 경유)만 100% 실패해서 "터널 전체가
  아니라 이 호스트네임 하나만" 문제라는 게 재확인됨. DNS 레코드 중복
  없음(api/auth 둘 다 정확히 같은 터널 1건), Access Applications 완전히
  비어있음(Zero Trust 정책 무관), lora-notebook 터널 껐다 켜도 무변화,
  Published application route(`api.suvisdev.cloud`) 삭제 후 재등록해도
  무변화 — 전부 배제.
- **잠정 결론**: Cloudflare 상태 페이지 확인 결과 인천(ICN)은 정상이나
  **SJC(산호세) PoP가 이 조사 시각(2026-08-06 UTC 08~16시)과 겹치는
  예정 유지보수 중**("트래픽이 재라우팅될 수 있음" 공지) — 사용자
  스크린샷의 진단 패널도 "Los Angeles" PoP를 명시. 미국 서부 PoP를
  거치는 클라이언트가 한국(icn05/06) 커넥터로 가는 경로에서만 문제가
  나는 정황과 일치. 유지보수 종료(UTC 16시) 이후 재검증 필요 — 이번
  세션에선 확정하지 못함.

### 데이터(추가⑩)
- 해당 없음(설정 조사·변경만, DB 변경 없음).

### 산출물(추가⑩)
- 커밋: `e8067d4`(`--edge-ip-version 4` 추가, 이후 무효로 판명),
  `151d8eb`(프로토콜 강제 플래그 전부 제거, QUIC 자동 협상 복귀).
  AWS 보안 그룹: UDP 7844 규칙 정정 + TCP 7844 규칙 추가(콘솔에서
  사용자가 직접 반영, 코드 변경 아님).
- 백로그: `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 0순위 갱신 예정
  (다음 항목 이후 한 번에 반영).

### 작업 내용(추가⑪) — hub_knowledge Phase 2: 백필 스크립트 정비 + EC2 실 카탈로그 2014편 전체 백필 완료(1순위)

이 세션이 실제로는 **노트북(WSL2, GPU 보유)에서 직접 돌고 있다는 걸
뒤늦게 확인** — `lora-server`·Ollama(`nomic-embed-text` 포함)·로컬
docker compose 스택이 전부 이 환경에 있었음. 1순위 "시작 조건" 3가지를
전부 충족하고, 예상보다 더 나아가 실제 EC2 프로덕션 백필까지 완료.

### 수정/구현(추가⑪)
- `scripts/ingest_hub_knowledge.py`: (i) `MovieFilterQuery(limit=100)`
  하드코딩을 `limit`/`offset` 페이지네이션 루프(200개씩)로 교체해
  카탈로그 크기와 무관하게 전량 조회, (ii) 예외 처리에 `await
  session.rollback()` 추가. **다만 이 리포지토리는 `HubKnowledgeRepository
  .upsert()`가 `flush()`만 하고 `commit()`을 안 해서 원래 루프 끝에
  단 한 번만 커밋하는 구조** — rollback만 추가하면 실패 1건이 그 이전
  까지 성공한 전체를 날려버리는 역효과가 남을 발견해, 영화 1편 성공할
  때마다 `await session.commit()`도 같이 추가(실패 시 rollback은 그
  영화 1건에만 국한되도록 격리 — `bulk_import_movies.py`/
  `CreditsBackfillInteractor`와 같은 원칙).
- 로컬 39편 카탈로그로 먼저 실행 검증(39/39 성공, 2.84초 — 영화당
  약 0.073초, 2014편 환산 시 약 2.5~3분 예상). **이 로컬 검증이
  처음엔 컨테이너에 옛날 버전 스크립트가 여전히 떠 있는 상태로
  돌아간 것도 모르고 "통과"로 오판할 뻔함** — `scripts/`가 백엔드
  Dockerfile에 이미지로 구워지는 구조라 호스트 파일 수정이 컨테이너에
  반영 안 됨(바인드마운트 아님), 로컬 카탈로그가 39편(<100)이라 옛
  코드의 `limit=100`도 우연히 전량을 커버해 차이가 안 드러났던 것.
  `docker cp`로 수정본을 컨테이너에 직접 반영해 재확인.
- EC2 프로덕션 DB(2014편, hub_knowledge 0건)에 실제 백필: 보안 그룹이
  5432를 막고 있어(양호한 설정) SSH 로컬 포트 포워딩(`-L
  0.0.0.0:15432:localhost:5432`, `host.docker.internal` 경유로 로컬
  컨테이너가 접근) 터널로 우회 — 첫 실행은 옛 버전 스크립트로 100편
  에서 조용히 멈췄던 걸 뒤늦게 발견(카탈로그 크기 이슈 없이 100<200
  이라 페이지네이션 버그가 아니라 옛 코드가 실행된 것으로 확정 후)
  → `docker cp`로 수정본 반영 → 재실행.
- DB 접속정보(비밀번호 포함)는 EC2 `.env`에서 SSH로만 옮기고 대화창엔
  값을 출력하지 않음(임시 파일 사용 후 작업 종료 시 삭제, SSH 터널도
  종료) — 2026-08-04 S3 자격증명 처리와 동일 원칙.

### 오류·막힌 점(추가⑪)
- 위 "컨테이너가 옛 코드로 돎" 문제가 로컬 검증·EC2 1차 실행 둘 다에서
  똑같이 재현됨 — `docker exec`가 호스트 파일 수정을 자동 반영한다고
  착각한 게 원인. `scripts/` 디렉터리가 바인드마운트가 아니라 이미지
  빌드 시점에 고정된다는 걸 이번에 명확히 확인(교훈: 이 저장소의
  backend/auth 컨테이너는 코드 수정 후 재빌드 또는 `docker cp` 없이는
  절대 반영 안 됨).
- SSH 터널이 기본적으로 `127.0.0.1`에만 바인딩돼(`-L 15432:...`) 도커
  브리지(`172.17.0.1`)에서 컨테이너가 못 봄 — `-L
  0.0.0.0:15432:...`로 재실행해 해결.

### 데이터(추가⑪)
- EC2 프로덕션: `hub_knowledge` 0 → 2014(전량, `embedding IS NOT NULL`
  2014/2014). `succeeded=2014/2014 failed=0`.

### 산출물(추가⑪)
- 수정: `suvisdev/scripts/ingest_hub_knowledge.py`(페이지네이션 +
  per-item commit/rollback).
- EC2: `hub_knowledge` 테이블 전량 백필(코드 배포는 아직 안 함 — 이
  스크립트 자체는 수동 실행용이라 컨테이너 이미지 반영은 다음 정식
  배포 사이클에 포함하면 됨, 로컬 `docker cp`로 이번 1회성 실행만
  처리).
- 커밋: 이 항목 갱신 직후 진행 예정(아래 참고).

---

## 2026-08-05

### 작업 내용
- 어제(2026-08-04) 로컬 미커밋 상태로 남아 있던 mova 대량 수집 도미노 실패
  수정을 실전 배포하고, PROGRESS.md의 "옵션 1"(TMDB popular 50페이지,
  `--start-page 3`)을 실제로 EC2에서 처음 실행. 실행 중간(25페이지 시점)·
  완료 후 count 검증, hub_knowledge WARNING 개수 대조까지 추적.
- 겸사겸사 `.claude/skills/{systematic-debugging,verification-before-completion,
  writing-plans}` 도그푸딩 — 스킬을 명시적으로 부르지 않고 실제 작업만
  진행하면서 트리거 상황에서 auto-invoke가 실제로 발동하는지 관찰(결과는
  PROGRESS.md "부수 관찰" 절 참고, 이 세션에선 두 번의 "예상 밖 동작" 모두
  auto-invoke 없이 직접 조사로 해결됨).

### 수정/구현
- 로컬 확인 결과 EC2(`main`)에 어제 수정(`session.rollback()` 5곳)이
  전혀 반영 안 돼 있었음(커밋 자체가 안 됨) — 커밋→push→PR #33→main
  머지(`bf53dda`) → EC2 `git pull`(로컬 main이 `origin/main` 대비
  ahead 6/behind 2로 이미 발산 상태였음 — 내용 diff 확인 결과 EC2 로컬의
  `.gitignore`에 `tmp/` 한 줄만 추가돼 있던 것 외엔 실질 차이 없어
  `git pull --no-rebase --no-edit`로 안전하게 병합) → `docker compose
  --env-file suvisdev/.env up -d --build backend`로 재빌드·재기동.
  컨테이너 내 `grep -c session.rollback scripts/bulk_import_movies.py`로
  5건 확인 후 실행.
- `scripts/bulk_import_movies.py --source tmdb_popular --pages 50
  --start-page 3`를 `docker exec -d`로 backend 컨테이너 안에서 백그라운드
  실행(로그는 컨테이너 내 `/tmp/bulk_import.log`).

### 오류·막힌 점
- **원래 계획했던 "25페이지 도달 시 stdout 텍스트 매칭" 추적 방식이
  실패**: 스크립트의 페이지별 `print(f"page={page} 처리 완료...")`가
  파일로 리다이렉트된 stdout 블록 버퍼링에 걸려 실시간으로 안 찍힘
  (`logger.warning`/httpx 자체 INFO 로그는 즉시 flush돼 정상 노출).
  25페이지 체크포인트 시점엔 이미 실제로는 31페이지까지 진행돼 있었음 —
  요청 URL의 `page=N`을 직접 파싱 + DB count 직접 조회로 우회 확인.
  일반화하면: 배치 스크립트의 진행 상황을 실시간 로그 매칭으로 자동
  추적하려면 `print()`가 아니라 `logger`를 써야 한다.
- **완료 후 WARNING 총계(1013건)가 처음 집계한 "credits 백필 실패
  13건"과 안 맞음** → 재조사 결과 hub_knowledge 실패 WARNING(1000건, 처리
  영화 수와 정확히 1:1)이 `bulk_import_movies.py` 자체의 `except` 블록이
  아니라 `HubRagInteractor` 내부에서 이미 예외를 삼키고 자체 로그만 남기는
  경로에서 나온 것이었음 — 즉 어제 그 경로에 추가한 `session.rollback()`은
  이 경로에서는 예외가 애초에 안 올라와 한 번도 실행되지 않는 죽은 코드.
  동작 자체엔 문제없음(1:1 유지, 추가 silent failure 없음)이라 이번엔
  코드 수정 없이 관찰만 기록(백로그로 정리).
- **"어제 수정이 실전에서 검증됨"은 재확인 결과 과잉 결론이었음** — 사용자
  지적으로 로그를 다시 대조. 어제 수정한 `session.rollback()` 5곳 중:
  - `_ingest_tmdb_movie`의 **credits 백필 except**(92~96행)만 오늘 진짜로
    발동(13회, `credits 백필 실패` WARNING과 정확히 일치)했고, 이후
    `PendingRollbackError`가 로그 전체에 0건이라 rollback이 실제로
    작동해 후속 영화로 도미노가 안 번진 것을 직접 확인 — **이 지점은
    검증됨**.
  - 정작 어제 418건 도미노를 유발했던 **upsert_movie except**(같은 함수
    76~84행)는 오늘 배치에서 예외가 단 한 번도 안 나서(`upsert_movie 실패`
    0건, `failed=0`) 발동 자체를 안 함 — **이 지점은 "재발 없음 관찰"이지
    "검증"이 아님**(원래 버그를 유발한 조건 자체가 오늘 재현되지 않았다는
    뜻).
  - **hub_knowledge except**(111~115행)는 바로 위에서 정리한 죽은 코드 —
    발동 0건.
  - KOFIC 쪽 두 곳(154~158·180~182행)은 오늘 소스가 `tmdb_popular`라
    아예 실행 안 됨 — 미확인.
  결론: 도미노 자체는 재발하지 않았고 rollback 메커니즘이 실제 예외
  상황(credits 경로)에서 한 번은 제대로 작동한 것까지는 확인됐지만,
  "어제 수정 5곳이 전부 검증됨"은 부정확한 표현이었음 — PROGRESS.md 문구
  정정.

### 데이터
- EC2 실 DB(`suvisdevcloud-db-1`), 실행 전/후:
  - movies: 142 → 1055 (+913, 순증 91.3%)
  - actors: 1163 → 7058 (+5895)
  - characters: 1204 → 10041 (+8837)
  - movie_directors: 142 → 1116 (+974)
  - hub_knowledge: 0 → 0 (불변, EC2 Ollama 부재로 전량 실패 — 백로그
    "EC2 hub_knowledge 임베딩 어댑터 부재" 참고)
  - 스크립트 자체 리포트: `succeeded=1000 failed=0 skipped=0 last_page=52`
    (다음 배치는 `--start-page 53`).
  - 중간(31페이지 도달 시점) 스냅샷: movies 633(순증 87%대) — 초반 40건의
    27.5%보다 크게 상승, `--start-page 3`로 겹치는 초반 페이지를 건너뛴
    효과로 해석.

### 산출물
- 커밋: `6935352`(로컬), PR #33 머지 `bf53dda`(main), EC2 `git pull`로
  반영·`--build backend` 재배포 완료. 검증 범위 정정 문서 커밋 `2c76e3a`,
  `b32055d`.
- 문서: `_docs/WORK_LOG.md`(이 항목), `_docs/SUVIS_ADMIN_MULTIAGENT_
  PROGRESS.md`(실행 결과 + 부수 관찰 절 + 백로그 보강, 검증 범위 정정).

### 작업 내용(추가①) — upsert_movie except(76~84행) 0회 발동 원인 특정

사용자가 "원래 418건 도미노를 유발한 지점이 오늘은 왜 한 번도 안 걸렸는지"를
데이터 우연(가)인지 근본 원인 제거(나)인지 판별해달라고 요청 — 코드 변경 없이
로그·소스 재조사만 진행.

### 오류·막힌 점(추가①)
- **원래 트리거 재확인**: EC2 로그에서 오늘도 재현된 credits 백필 실패의
  실제 예외를 직접 확인 — `psycopg.errors.StringDataRightTruncation: value
  too long for type character varying(50)`(`characters.character_name`
  초과). 발생 지점은 `CharactersPgRepository.upsert_character()`의
  `self._session.commit()`(`studio_characters_pg_repository.py:58`) —
  `upsert_character`는 이 메서드 안에서 자체 `commit()`을 호출하는
  구조라 이 실패가 바로 여기서 터진다. 이 호출은 `credits_interactor
  ._backfill_one()`을 통해 **credits 백필 except(92~96행)** 안에서
  일어나며, `upsert_movie()`(76~84행이 감싸는 대상) 자체는 애초에
  `character_name`을 다루지 않아 이 데이터 문제를 직접 겪을 수 없다.
- **76~84행이 어제 418번 발동했던 진짜 메커니즘**: 어제는 92~96행·
  111~115행에 rollback이 없어, 92~96행의 커밋 실패로 세션이
  pending-rollback 상태가 된 채 방치됐고, **다음 영화**의 첫 세션
  작업인 `upsert_movie()` 호출이 그 오염을 그대로 상속받아
  `PendingRollbackError`를 던진 것이 76~84행에서 "upsert_movie 실패"로
  기록된 정체였음(그 영화 자신의 데이터 문제가 아니라 이전 영화의
  오염 검출). 어제 커밋(`6935352`) diff를 다시 확인해 `character_name`
  길이 제한·검증·트렁케이션 관련 변경이 전혀 없었음(rollback 5곳
  추가뿐)도 재확인 — 오늘 같은 에러가 13번 그대로 재현된 것과 일치.
- **판정**: 92~96행에 rollback이 생기면서 오염이 다음 영화로 전파되는
  경로 자체가 막혔으므로, 원래 418-도미노를 만들었던 "상속된 오염으로
  76~84행 발동" 경로는 **구조적으로 닫혔다**(나)에 해당). 다만 76~84행은
  `upsert_movie()` 자신의 독립적 실패(movies 테이블 자체 문제)에도
  반응하도록 남아 있고 이 클래스는 관측된 적이 없어 (가)(데이터 우연/
  미검증) 상태로 남음 — 다만 `movies.title`이 `String(255)`로
  `characters.character_name`(`String(50)`)보다 훨씬 여유가 있어 이
  클래스의 발생 확률 자체는 낮다고 판단.
- 코드 변경 없음(사용자 지시대로 조사만).

### 데이터(추가①)
- 해당 없음(로그 재조회만).

### 산출물(추가①)
- 문서: `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 백로그에 조사 결과
  추가(코드 변경 없음, 문서만).

### 작업 내용(추가②) — character_name VARCHAR(50) truncation 데이터 유실 규모 조사

사용자가 "13건 truncation이 실제로 데이터를 얼마나 유실시켰는지, 원인(TMDB
데이터 이상 여부), 수정 옵션(컬럼 확장/앱 레벨 truncate/둘 다)"을 조사해달라고
요청 — 코드 변경 없이 로그·DB·TMDB API 대조만 진행.

### 오류·막힌 점(추가②)
- **유실 범위가 예상(캐릭터 1건)보다 훨씬 컸음**: `CreditsBackfillInteractor
  ._backfill_one()`의 cast 순회 `for` 루프에 per-member try/except가 없어,
  루프 중간의 캐릭터 1건이 `StringDataRightTruncation`으로 실패하면 예외가
  `_backfill_one()` 밖으로 그대로 전파돼 **그 시점 이후 나머지 cast 전원 +
  directors 루프 전체**가 통째로 스킵됨. TMDB API를 직접 재조회해 13개
  영화 전부 대조한 결과 `cast 458명 중 421명 유실`(DB엔 characters 37건만
  남음), `directors 21명 전원 유실`(movie_directors 0건) — 영화 자체는
  `succeeded`로 집계돼 `failed=0` 리포트엔 전혀 안 잡힘. 실패한 cast
  멤버 자신의 `actors` 행은 `upsert_actor()`가 캐릭터 upsert보다 먼저
  별도 커밋을 해버려서 이미 저장돼 있음(이 영화와의 연결만 없는 고아
  상태).
- **샘플 확인 결과 데이터 이상 아님**: 13건 전부 TMDB `credits.cast[]
  .character` 필드가 합법적으로 긴 값 — 애니메이션 다역 성우(최댓값 The
  Simpsons Movie 332자), 1인 다역 배우(Split 84자), 생애주기·자막 병기
  표기(59자) 등. 파싱·인코딩 오류 없음, TMDB 원본 그대로.
- 코드 변경 없음(조사만).

### 데이터(추가②)
- EC2 실 DB + TMDB API 실시간 재조회로 13개 영화(`movie_id` 142/157/447/
  567/676/782/818/832/858/884/889/955/1031) 전수 대조:
  - cast: TMDB 458명 vs DB characters 37건 (유실 421)
  - directors: TMDB 21명 vs DB movie_directors 0건 (유실 21, 전원)
  - character_name 길이 분포(관측 13건 기준): 최소 52자 ~ 최대 332자.

### 산출물(추가②)
- 문서: `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 백로그에 유실 규모 표 +
  수정 옵션(a/b/c) 비교 + ERD 교차 확인 + 재실행 필요 여부 판단 추가.
  판단: 오늘 배치(50페이지) 전체 재실행은 불필요 — movies 카탈로그
  1000편은 정상이라 컬럼 마이그레이션 적용 후 `scripts/backfill_credits_
  cli.py`(idempotent 전체 재실행, TMDB 재조회 약 4~5분)만으로 13편의
  누락 credits 복구 가능.

### 작업 내용(추가③) — character_name 유실 구조적 수정 + 데이터 복구

사용자가 (1) 구조적 원인 제거, (2) 오늘 유실 데이터 복구, (3) 회귀 방지 3가지
목표로 실제 수정+복구를 지시 — 조사(추가②)에서 나온 옵션 (c)를 그대로 채택.

### 수정/구현(추가③)
- **Alembic `20260805_0001`**: `characters.character_name` VARCHAR(50) →
  TEXT. docstring에 실측 근거(최댓값 332자, 애니메이션 다역 성우 구조적
  상한 없음, PG에서 TEXT/VARCHAR(n) 성능 동일, 인덱스 대상 아님) 명시.
  **downgrade는 의도적으로 미지원** — TEXT로 넓힌 뒤 저장된 50자 초과
  데이터를 truncate 없이 되돌릴 방법이 없고, 이 리비전의 존재 이유 자체가
  "50자가 틀렸다"는 것이라 되돌리는 게 무의미하다는 판단(호출 시
  `RuntimeError`로 안내). ORM(`studio_characters_orm.py`)·ERD 문서
  (`mova_database.md`, `MOVA_ERD.md`) 동기화.
- **`CreditsBackfillInteractor._backfill_one()` cast/directors 루프에
  per-member try/except 추가**: 한 명 실패가 나머지 전원을 더 이상 안
  날림 — 실패한 멤버만 `skipped_cast`/`skipped_directors`로 집계하고
  WARNING 로그(영화 slug, tmdb_person_id, character/name, exc_info) 남긴
  뒤 다음 멤버로 진행. rollback은 세션을 쥔 리포지토리가 담당해야
  Clean Architecture 경계(인터랙터는 세션을 모른다)를 안 깨서,
  `ActorsRepositoryPort`에 `rollback()` 추상 메서드를 신설하고
  `ActorsPgRepository`가 `session.rollback()`으로 구현 — 인터랙터는
  `await self._actors.rollback()`만 호출.
  `BackfillOneResultDto`(신규 dto) 반환값으로 두 카운트 노출,
  `CreditsBackfillResultDto`에도 누적값 추가.
- **`scripts/bulk_import_movies.py`**: `_ingest_tmdb_movie()` 반환값을
  `str` → `tuple[str, int, int]`(outcome, skipped_cast, skipped_directors)로
  변경, `_run()`의 stats에 `skipped_cast`/`skipped_directors` 필드 추가해
  페이지별·최종 리포트에 노출 — "failed=0인데 credits는 유실"이 이제는
  리포트에서 바로 보임.
- **회귀 테스트**: `test_credits_backfill.py`에 2건(cast 1명 실패해도
  나머지 cast+directors 정상 처리, director 1명 실패해도 나머지 director
  정상 처리) — 둘 다 `rollback()` 호출 확인 포함.
  `test_bulk_import_movies.py` 기존 3건을 새 튜플 반환값에 맞게 수정 +
  skipped_cast/skipped_directors가 반환값에 그대로 노출되는지 확인하는
  신규 1건 추가. `apps/mova/tests` 90건 전부 통과, `lint-imports` mova
  계약 위반 없음.

### 오류·막힌 점(추가③)
- 로컬 WSL의 Docker 통합이 이 세션에서도 계속 불가(기존에 여러 번 기록된
  같은 증상) — 로컬 DB로 마이그레이션 실제 적용 검증은 못 하고 pytest
  (DB 불필요, mock 기반)로만 로컬 검증. 실제 마이그레이션 적용·데이터
  복구는 EC2에서 진행(아래 산출물 참고).

### 데이터(추가③)
- 아래 항목에서 계속(EC2 실행 결과는 이 항목 갱신 후 별도로 기록).

### 산출물(추가③)
- 신규: `suvisdev/alembic/versions/20260805_0001_widen_character_name_to_text.py`.
- 수정: `apps/mova/adapter/outbound/orm/studio_characters_orm.py`,
  `apps/mova/adapter/outbound/pg/studio_actors_pg_repository.py`,
  `apps/mova/app/dtos/studio_import_dto.py`,
  `apps/mova/app/ports/output/studio_actors_repository.py`,
  `apps/mova/app/use_cases/credits_backfill_interactor.py`,
  `apps/mova/tests/{test_bulk_import_movies,test_credits_backfill}.py`,
  `scripts/bulk_import_movies.py`,
  `apps/mova/_docs/{mova_database.md,MOVA_ERD.md}`.

### 작업 내용(추가④) — EC2 배포 중 디스크 부족 재발 + 데이터 복구 + 유실 규모 재계산 정정

PR #34 머지 후 EC2 `docker compose up -d --build backend` 실행 중
`pip install`이 torch 다운로드 도중 `[Errno 28] No space left on device`로
반복 실패(2026-07-30·2026-08-02에도 있었던 디스크 부족 재발). 원인 규명 후
해결하고 실제 데이터 복구까지 완료했는데, 복구 결과를 검증하다가 이전
조사(추가②)의 유실 규모 계산이 틀렸다는 것도 발견해 함께 정정한다.

### 오류·막힌 점(추가④)
- **디스크 부족 근본 원인**: `docker system df`로 확인 결과 `backend`·`auth`
  두 서비스가 `docker-compose.yaml`에서 **완전히 동일한 Dockerfile·빌드
  컨텍스트**(`./suvisdev`)를 쓰는데 이미지가 따로 태깅돼 있어, 8.84GB짜리
  pip 설치 레이어를 중복으로 디스크에 물고 있었음(`backend` 이미지를
  지워도 `auth`가 같은 레이어를 참조 중이라 공간이 전혀 안 풀림으로 확인).
  `docker image prune -a`·`docker builder prune -a`로는 8.8GB짜리 실패한
  빌드 캐시(19GB)만 정리됐고, 실제 재빌드엔 여전히 부족(13GB 여유로 설치
  마지막 파일 직전에서 재실패). **사용자 승인 받아 `auth`까지 잠깐 내려서
  중복 레이어 해제**(22GB 확보) → `backend` 재빌드 성공 → `auth` 재빌드는
  동일 컨텍스트라 캐시 100% 히트로 즉시 완료(추가 디스크 0). 두 서비스 다시
  정상 기동 확인. **근본 해결 아님**(같은 이미지를 두 개 태그로 관리하는
  구조 자체가 문제) — 백로그로 남김(아래 산출물 참고).
- **유실 규모 재계산 필요 — 추가②의 "cast 458명 중 421명 유실"은 과대
  집계였음**: 복구 후 검증 중 `characters_cnt`가 전부 정확히 10건(또는
  TMDB cast가 10명 미만인 영화는 그 실제 수)으로 고정되는 것을 발견 →
  원인은 `tmdb_mapper.map_credits(cast_limit=10)`이 **2026-07-30부터 이미
  있던 의도된 설계**(영화당 상위 10명만 저장, 오늘 버그와 무관, 내가
  건드리지 않음)였음. 추가②에서 TMDB 원본 cast 총원(458명)과 DB를 그대로
  비교해 유실을 계산한 게 실수 — **앱이 실제로 저장하려 했던 양(각 영화
  min(TMDB cast, 10))** 기준으로 다시 계산하면 실제 유실은 cast
  **90명**(directors는 상한이 없어 21명 전원 유실은 그대로 맞음). 아래
  "완료됨"에 정정된 표로 갱신.
- 코드 변경 없음(디스크 정리·데이터 복구만, 재계산은 순수 재검증).

### 데이터(추가④)
- **13편 dry-run 사전 검증**: 전부 예외 없이 통과(임시 검증 스크립트로
  `_backfill_one(dry_run=True)` 직접 호출, 저장소에 커밋 안 함·작업 후 삭제).
- **`scripts/backfill_credits_cli.py` 전체 재실행**(1055편 대상):
  `succeeded=1044 failed=0 skipped=11`(스킵은 tmdb- 접두사 아닌 기존
  hand-curated 슬러그, 이번 문제와 무관·기존 정상 동작).
- **13편 재검증(정정된 기준)** — TMDB cast/directors vs DB characters/
  movie_directors, 복구 전(추가②) → 복구 후:

  | movie_id | 제목 | 앱 의도(min(TMDB,10)) | 복구 전 | 복구 후 | TMDB directors | 복구 전 | 복구 후 |
  |---|---|---|---|---|---|---|---|
  | 142 | KPop Demon Hunters | 10 | 8 | **10** | 2 | 0 | **2** |
  | 157 | Coraline | 10 | 7 | **10** | 1 | 0 | **1** |
  | 447 | Corpse Bride | 10 | 4 | **10** | 2 | 0 | **2** |
  | 567 | The Simpsons Movie | 10 | 0 | **10** | 1 | 0 | **1** |
  | 676 | Karuppu | 10 | 0 | **10** | 1 | 0 | **1** |
  | 782 | SpongeBob SquarePants Movie | 10 | 3 | **10** | 1 | 0 | **1** |
  | 818 | Nightmare Before Christmas | 10 | 0 | **10** | 1 | 0 | **1** |
  | 832 | Cinema Paradiso | 10 | 4 | **10** | 1 | 0 | **1** |
  | 858 | Snow White and the Seven Dwarfs | 10 | 4 | **10** | 6 | 0 | **6** |
  | 884 | Escoriandoli | 7(TMDB 총원 7명) | 4 | **7** | 2 | 0 | **2** |
  | 889 | Split | 10 | 0 | **10** | 1 | 0 | **1** |
  | 955 | Who Framed Roger Rabbit | 10 | 3 | **10** | 1 | 0 | **1** |
  | 1031 | The Secret Agent | 10 | 0 | **10** | 1 | 0 | **1** |

  **13편 전부 앱이 의도한 양과 정확히 일치 — 100% 복구 확인**(사용자가
  콕 짚은 KPop Demon Hunters·The Simpsons Movie·Split 포함). 실제 유실은
  cast 90명(458명 아님) + directors 21명 전원.

### 산출물(추가④)
- EC2: `docker system prune`류 정리, `auth` 이미지 삭제 후 재빌드(캐시
  히트), `backend` 재빌드·`alembic upgrade head`(`20260805_0001`),
  `scripts/backfill_credits_cli.py` 전체 재실행.
- 문서: 이 항목 + `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` "완료됨" 갱신
  (유실 규모 정정 포함) + 백로그 1건 추가(backend/auth 중복 이미지 태깅).

### 작업 내용(추가⑤) — mova 추천 품질 검증 Phase 1(EC2 Gemini 경로)

학원 PC(GPU·LoRA 접근 없음)에서 EC2 `/mova/chat`의 Gemini 경로만 대상으로
골든셋 15개를 만들어 실제 호출·판정 + hub_knowledge 백필 절차 사전 조사.
`_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md` 신규.

### 오류·막힌 점(추가⑤)
- **실행 전 발견 — `RECOMMENDATION_BACKEND` EC2 미설정**: 코드 기본값이
  `"lora"`인데 EC2 `.env`엔 이 변수가 아예 없어 mova chat이 붙지도 않는
  집 GPU를 호출하려던 상태였음(2026-08-02에 env 분기 코드만 추가되고
  실제 값 설정은 안 됐던 것으로 추정). `RECOMMENDATION_BACKEND=gemini`를
  EC2 `.env`에 추가 + `docker compose up -d backend`로 반영 후 골든셋
  진행 — 배포 체크리스트 누락 항목으로 백로그 등록.
- **핵심 발견 — 배우 오귀속(title-collision)**: "송강호 출연 스릴러"
  쿼리에서 봉준호 감독의 `괴물`(2006, 송강호 주연)을 의도한 것으로 보이는
  추천이, 한국어 로컬라이즈 제목이 똑같이 "괴물"인 `The Thing`(1982, 존
  카펜터 감독, 송강호 무관)에 잘못 매칭됨. `movie_id`가 있어도(grounded로
  보여도) 실제로는 다른 영화일 수 있다는 뜻 — null보다 더 위험한 실패
  모드로 판단, 근본 원인은 제목 문자열 매칭 구조.
- **부수 발견 — 포맷 차이로 미매칭**: 같은 "빽 투 더 퓨쳐"가 한 쿼리에선
  `movie_id` 매칭 성공, 다른 쿼리에선 Gemini가 연도를 괄호로 덧붙였다는
  이유만으로 매칭 실패(null) — 제목 매칭이 문자열 완전일치에 의존하는
  취약한 구조임을 보여주는 구체 사례.
- **hub_knowledge 백필 스크립트(`ingest_hub_knowledge.py`) 재확인 중
  발견**: `limit=100` 하드코딩(오늘 카탈로그 1055편 기준 955편 스킵),
  루프 끝 단일 커밋 + rollback 없는 except(오늘 고친 도미노 패턴과 동일
  위험) — Phase 2 착수 전 수정 필요 항목으로 문서에 정리, 이번엔 코드
  수정 안 함(사용자 지시로 조사만).

### 데이터(추가⑤)
- 골든셋 15개 실행: 통과 6 · 부분 5 · 실패 4. intent 분류(`filter_and`/
  `mood`)는 15/15 전부 의도대로 동작, 카드 vs 산문 분기에서 산문 회귀는
  0건. "환각"으로 분류될 만한, 존재하지 않는 영화를 지어낸 사례는 0건 —
  실패 원인은 전부 카탈로그 커버리지 부족 또는 제목 매칭 취약성.

### 산출물(추가⑤)
- 신규: `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`.
- EC2: `.env`에 `RECOMMENDATION_BACKEND=gemini` 추가, `docker compose up
  -d backend`로 반영.
- 코드 변경 없음(조사·실측만).

### 작업 내용(추가⑥) — mova 추천 오귀속 근본 원인 조사

Phase 1에서 발견한 두 버그(동명이인 오귀속·제목 포맷 미매칭)가 같은 결함인지
특정하고 해결 방향 3가지를 비교. `_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md`
신규. 코드 변경 없음(조사만).

### 오류·막힌 점(추가⑥)
- **당초 가설 기각**: "괴물"이 DB에 동명 영화 여러 건이라 tiebreaker 없이
  아무거나 골랐다"는 가설을 세우고 확인했으나, 실제론 DB에 "괴물" 제목이
  **1건뿐**(`The Thing`, 1982, 존 카펜터 — 송강호와 무관). 진짜 원인은
  `ChatReplyService.enrich_from_db()`의 3단계 매칭 체인 중 3단계
  `find_by_title()`이 문자열이 일치하면 그걸로 끝 — 원래 요청 맥락(배우
  등)과 실제로 관련 있는지 전혀 검증하지 않는 것. 동일 함수가 완전일치
  요구 때문에 "빽 투 더 퓨쳐 (1985)"처럼 사소한 포맷 차이엔 반대로 너무
  깐깐해서 미스 — **매칭이 너무 빡빡해 정상 케이스를 놓치는 것과, 그
  빡빡한 매칭이 우연히 성공했을 때 아무도 검증 안 하는 것이 같은 코드에서
  동시에 나오는 구조적 결함**임을 확정.
- `RECOMMENDATION_BACKEND` 미설정 경위: `.env.example`엔 커밋 `db6623b`
  (2026-08-03)로 "EC2는 gemini여야 함"이 주석으로 이미 명시돼 있었으나,
  이건 템플릿일 뿐이고 실제 `.env`(git 미추적)엔 반영된 적이 없었음 —
  코드 버그가 아니라 배포 절차 누락. 다른 네트워킹 민감 변수(`REDIS_URL`
  등)는 전부 `docker-compose.yaml`의 `environment:` 블록에 하드코딩돼
  `.env` 내용과 무관하게 안전함을 확인 — `RECOMMENDATION_BACKEND`은 순수
  기능 플래그라 이 안전망 대상이 아니었던 게 유독 취약했던 이유.

### 데이터(추가⑥)
- "송강호 출연 스릴러 영화" 쿼리 재실행 2/2 재현(동일하게 `The Thing` 포함).
  DB `movies WHERE title ILIKE '%괴물%'` 결과 1건(`id=426`) 직접 확인.

### 산출물(추가⑥)
- 신규: `_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md`.
- 수정: `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md` 백로그 항목 갱신
  (근본 원인 문서로 링크).
- 코드 변경 없음(조사만, 착수는 다음 세션).

### 작업 내용(추가⑦) — mova 추천 매칭 오귀속 근본 수정: Grounded Prompting

추가⑥에서 권장한 (b) Grounded prompting 구현. Gemini 응답을 title 재매칭
없이 movie_id로 직접 확정하도록 프롬프트·파싱·매칭 계층을 함께 교체.

### 수정/구현(추가⑦)
- **`chat_prompt.py`**: `MOVA_SYSTEM_PROMPT`에 "반드시 카탈로그 목록의
  movie_id만 사용, 목록에 없는 영화 추천 금지, 부족하면 있는 만큼만(0~2편)"
  규칙 추가 + 출력 형식에 `movie_id` 필드 명시. `format_tag_catalog_section`
  이 후보마다 `movie_id=N`을 표시하고 "가능하면"(권고) → "반드시"(강제)로
  지시 강도 변경.
- **`chat_reply.py`**: `_GeminiPickSchema`(pydantic) 신설 — `movie_id: int`
  필수, `ValidationError`면 그 pick만 드롭 + WARNING 로그(전체 응답은 안
  죽음, 2026-08-04 도미노 수정과 같은 원칙). `enrich_from_db()`를 완전히
  교체 — 기존 3단계 완전일치 체인(canonical map→slug 재조회→
  `find_by_title` 완전일치)을 전부 제거하고 `repo.find_by_id(rec.movie_id)`
  단일 조회로 대체. DB에 없는 movie_id(카탈로그 무시 — 프롬프트 위반)는
  그 pick만 드롭 + WARNING, 나머지는 반환. **부수 변경**: 예전엔 매칭
  실패 시 Gemini의 title 그대로 placeholder movie를 DB에 새로 만들었는데
  (분석 결과 이 자체가 카탈로그 밖 데이터가 섞이는 위험이었음), 이제는
  드롭만 하고 DB에 아무것도 안 씀 — 의도된 동작 변경.
- **`movies_pg_repository.py`/`movies_repository.py`(포트)**: `find_by_id()`
  신설(`find_by_title`과 동일 패턴, `MovaMovie.id`로 조회 후
  `get_by_slug()` 위임). `find_by_title()`은 `import_interactor.py`/
  `harvest_ingest_interactor.py`가 여전히 쓰고 있어 **그대로 유지**(제거
  안 함, grep으로 다른 호출부 확인 후 판단).
- **`studio_movies_vo.py`**: `resolve_canonical_slug()` 제거 — `chat_reply.py`
  가 유일한 호출부였는데 그 호출을 없앴으므로 죽은 코드가 됨. `TITLE_TO_
  CANONICAL_SLUG` 딕셔너리·`title_for_canonical_slug()`는 무관한
  기존(별도) 죽은 코드라 손 안 댐.
- **아키텍처 확인 — 이 수정은 Gemini 전용이 아니라 4개 추천 백엔드
  (Gemini/LoRA/Qwen/EXAONE) 공유 코드**: `ChatPromptBuilder`·
  `ChatReplyService`를 `lora_recommendation_adapter.py`·
  `qwen_recommendation_adapter.py`·`exaone_recommendation_adapter.py`가
  전부 그대로 재사용하고 있음을 확인 — 프롬프트·매칭 계층 변경이 네 경로
  모두에 동일하게 적용됨(로컬 모델이 movie_id 요구에 덜 순응하면 그만큼
  pick이 더 드롭될 뿐, 크래시하지 않는 방향으로 설계해 안전).
- **`market_chat_schema.py`는 의도적으로 안 건드림**: 사용자 요청은 이
  파일의 `MovaChatRecommendationSchema.movie_id`를 required로 바꾸는
  것이었으나, 이 스키마가 `ChatResponseDto.to_schema()`를 통해 4개 백엔드
  전부의 최종 응답 조립에 쓰이는 공유 타입임을 확인 — required로 바꾸면
  movie_id가 None인 케이스(다른 백엔드가 향후 그런 값을 만들 수 있음)에서
  Pydantic 검증이 깨진다. 대신 **Gemini 파이프라인 전용**
  `_GeminiPickSchema`를 `chat_reply.py`에 신설해 movie_id 필수 검증은
  거기서만 하고, 공유 응답 스키마의 `movie_id: int | None = None`은
  그대로 유지 — 요청받은 파일이 아니라 이 파일에 넣은 이유를 명시.

### 오류·막힌 점(추가⑦)
- 없음 — 기존 90개 + 신규 8개 = `apps/mova/tests` 98개 중 실제로는
  `test_chat_reply_service.py` 신규 8건이라 95개 전부 통과(아래 산출물
  참고), `lint-imports` mova 계약 위반 없음(사전부터 있던 ontology↔mova
  위반 1건은 무관).

### 데이터(추가⑦)
- 해당 없음(코드·테스트만, 데이터 검증은 EC2 배포 후 Phase 1 골든셋
  재실행에서 진행 — 이 항목 갱신 후 별도 기록).

### 산출물(추가⑦)
- 신규: `apps/mova/tests/test_chat_reply_service.py`(8건 — 파싱 검증 4,
  enrich_from_db 2, "괴물"·"빽 투 더 퓨쳐" 재현 회귀 2).
- 수정: `apps/mova/adapter/outbound/llm/{chat_prompt,chat_reply}.py`,
  `apps/mova/adapter/outbound/pg/movies_pg_repository.py`,
  `apps/mova/app/ports/output/movies_repository.py`,
  `apps/mova/domain/value_objects/studio_movies_vo.py`.
- `apps/mova/tests` 95개 전부 통과, `lint-imports` mova 계약 위반 없음.

### 작업 내용(추가⑧) — EC2 배포 + 재검증 중 세 번째 버그 발견·수정 + 골든셋 최종 재확인

추가⑦ 배포 직후 "송강호 출연 스릴러" 재현 쿼리로 1차 확인(괴물→The Thing
사라짐)까지는 성공했으나, 골든셋 15개 전체 재실행 결과를 DB와 대조하는
과정에서 **세 번째 버그**를 발견해 같은 사이클 안에서 추가 수정·재배포.

### 오류·막힌 점(추가⑧)
- **DB 존재 검증만으론 불충분했음**: 13번("스트레스 풀고 싶을 때") 응답의
  `movie_id=101, title="극한직업"` 카드를 DB에서 직접 대조하니 `id=101`의
  실제 title은 `"캡틴 아메리카: 브레이브 뉴 월드"`였다(`slug=tmdb-822119`로
  확인, TMDB API 원본과도 일치). 같은 응답의 `movie_id=105, title="베테랑"`
  도 실제로는 `"양탐정 릴리"`였음. Gemini가 title/hook은 자신이 실제로
  의도한(그러나 카탈로그엔 없었던) 영화 설명을 그대로 남긴 채, movie_id만
  — 아마 다른 문맥에서 봤음직한 — DB에 실존하는 엉뚱한 작은 번호를 끼워
  보낸 것으로 추정. `enrich_from_db()`가 "movie_id가 DB에 있는가"만 확인
  하고 "내가 실제로 그 id를 후보로 제시했는가"는 확인 안 해서 이걸 못
  걸렀다 — 오귀속을 원천 차단하려던 수정 자체가 새로운(더 교묘한) 오귀속
  패턴에 뚫릴 뻔한 것을 배포 직후 검증에서 잡음.
- **수정**: `enrich_from_db()`에 `tag_catalog`(그 요청에서 실제로 제시한
  후보 id 집합) 파라미터 추가 — DB 존재 여부 확인 **이전에** 이 집합에
  속하는지부터 검사, 없으면 드롭. 최종 `title`도 항상 DB 값으로 덮어쓰는
  안전망 추가(움직일 수 없는 사실: id가 맞으면 title도 그 id의 진짜
  제목이어야 한다). Gemini/LoRA/Qwen/EXAONE(x2) 5개 어댑터 전부
  `enrich_from_db(recs, tag_catalog=tag_catalog)`로 갱신.
- 재배포 후 같은 시나리오(스트레스·재밌는 거 뭐 있어 등) 재확인 — 이제
  카탈로그에 없는 movie_id는 DB 존재와 무관하게 정직하게 드롭되어 빈
  응답으로 처리됨(오귀속 카드 자체가 안 나감).

### 데이터(추가⑧)
- **골든셋 15개 최종 재실행**(수정 2건 다 반영된 버전 기준):
  통과 9(1,2,3,4,6,8,10,11,14) · 실패 6(5,7,9,12,13,15) — "부분" 판정
  소멸(이분법적 설계: 정확히 grounded되거나 정직하게 빈 응답이거나).
  **애초 목표였던 두 버그(6번 동명이인, 8번 포맷 미매칭) + 조사 중
  발견됐던 연도 이탈(10번, 시네마 천국 1988이 90년대 로맨스에 섞이던
  것)까지 전부 재현 후 수정 확인**. 통과 건수 자체도 6→9로 증가.
  반대로 5·7·9·12·13·15번은 예전 "부분"에서 "실패(정직한 빈 응답)"로
  바뀌었는데, 이는 회귀가 아니라 설계 의도대로의 트레이드오프(카탈로그
  밖 근거로 자신 있게 틀린 답 대신 정직한 미확인) — 커버리지 부족은
  이번 스코프 밖(§ Phase 2 hub_knowledge에서 개선 기대)으로 이미
  합의됨. 상세 비교표는 `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`
  §6.
- **한계**: 재검증이 실제 Gemini API 재호출이라 intent 키워드·카탈로그
  구성이 Phase 1 시점과 완전히 같지 않을 수 있음(7·13번처럼 이번 호출엔
  후보가 카탈로그에 안 걸렸을 가능성) — 코드 효과로 명확히 귀속 가능한
  건 6·8·10번의 구조적 개선.
- **부수 발견**: 12·13·14번에서 `reply` 텍스트("두 편을 추천해 드릴게요")
  와 실제 `recommendations: []` 개수가 안 맞는 경우 관측 — Gemini가
  intro를 picks 필터링 전 기준으로 작성해서 생기는 카피 불일치(데이터
  정확성 문제 아님, UX 다듬기 대상) — 백로그 등록.

### 산출물(추가⑧)
- 커밋: `c3b61bd`(로컬), PR #37 머지 `5c68a75`(main), EC2 pull+backend
  재빌드(캐시 히트, 수 초) 완료.
- 문서: `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md` §6 신규(재검증 비교표
  + 세 번째 버그 발견 경위 + 한계 + UX 백로그).

### 작업 내용(추가⑨) — 세션 마무리: 골든셋 재사용성 확보 + 다음 세션 후보 정리

사용자 요청으로 코드 변경 없이 문서만 2건 보완. (1) Phase 1 문서가
"다음 세션에 이 파일만 열면 재실행 가능"한지 (a)쿼리 원문 (b)실행 방법
(c)판정 기준 (d)비교표 4개 기준으로 점검, (2) PROGRESS.md 백로그에 다음
세션 후보 4개를 우선순위와 함께 명시.

### 오류·막힌 점(추가⑨)
- **사용자가 최종 결과를 "9/2/4"로 언급했으나 실제 기록은 "9/0/6"**(부분
  판정이 소멸)이었음 — Phase 1 문서 §6에 이미 명시된 공식 집계와 대조해
  확인, 사용자 진술을 그대로 옮기지 않고 문서 자체에 "9/2/4는 오기"라는
  주의 문구를 남김(대화 중 숫자보다 문서를 신뢰하라는 원칙 재확인).

### 데이터(추가⑨)
- 해당 없음(문서만).

### 산출물(추가⑨)
- 수정: `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`(재실행용 스크립트
  §2 추가, 판정 기준 재확인 문단 §1 추가, 집계 비교표+오기 정정 §6 추가),
  `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(백로그에 "다음 세션 후보"
  하위 섹션 4개 우선순위 신규).
- 코드 변경 없음.

### 작업 내용(추가⑩) — 루트 `_docs/` 전면 감사·정리(Cursor 시대 잔재 제거)

사용자 요청으로 `_docs/` 전체를 실제 저장소 구조와 대조 — Cursor 하네스
시절(`backend/`·`frontend/` 경로 전제) 문서가 대거 남아 있었고, 그중
다수가 `suvisdev/`·`suvis/` 하위에 이미 있는 최신판의 stale 중복이었다.

### 오류·막힌 점(추가⑩)
- **`DevOps/Backend/TITANIC_ERD.md`**가 `suvisdev/apps/titanic/_docs/
  titanic-erd.md`와 **byte-identical** — 완전 중복.
- **`DevOps/Backend/MOVA_ERD.md`**(494줄)가 `suvisdev/apps/mova/_docs/
  MOVA_ERD.md`(674줄)의 v1 스냅샷 — 2026-06~07 스키마 리비전(v2/v3:
  `members`/`member_groups` 제거, `viewer` 3테이블 분리, `characters
  .character_name` 추가, `embedding vector(768)` 확정 등)이 전혀 반영 안
  된 채 방치돼 있었음. 짝인 `mova-erd.png`도 구버전 이미지(md5 다름,
  `suvisdev/apps/mova/_docs/`의 것과 별개 파일).
- **`DevOps/Backend/ENTITY_RULE.md`**가 `suvisdev/_docs/entity-rules.md`
  로 이미 이관돼 있었음(경로만 `backend/`→`suvisdev/`로 바뀐 버전).
- **`DevOps/Frontend/REACT_RULES.md`**가 `suvis/_docs/react-rules.md`로
  이미 이관돼 있었고 `suvis/CLAUDE.md`가 실제로 그쪽을 참조 중이었음.
- **`타이타닉 개발/james_fastapi_context.md`**는 2026-05-07 시점
  `james.py`/`walter.py` 단일 파일 프로토타입 기록 — 현재 `suvisdev/
  apps/titanic/`은 Clean Architecture 전면 재구축(엔티티 12개, 44 테스트)
  으로 완전히 다른 구조라 참고 가치가 없어짐.
- **`SUVISDEV_RULES.md`**는 인덱스(루트)와 상세(`DevOps/Frontend/`) 두
  파일로 쪼개져 있었는데, 상세 쪽 내용("UI 변경 스코프 판별" — 지시 없는
  위치 이동·구조 개편 금지)은 다른 곳에 이관된 적 없는 **유일한 원본**
  이라 삭제 대신 두 파일을 하나로 병합(`frontend/`→`suvis/` 경로 수정
  포함).

### 데이터(추가⑩)
- 해당 없음(문서만).

### 산출물(추가⑩)
- 삭제: `_docs/DevOps/Backend/{TITANIC_ERD.md,MOVA_ERD.md,mova-erd.png,
  ENTITY_RULE.md}`, `_docs/DevOps/Frontend/REACT_RULES.md`,
  `_docs/DevOps/Frontend/SUVISDEV_RULES.md`(병합 후 삭제), `_docs/타이타닉
  개발/james_fastapi_context.md`(폴더째 제거) — `DevOps/` 트리 전체 소멸.
- 병합: `_docs/SUVISDEV_RULES.md`(인덱스+상세 통합, 경로 수정).
- 재작성: `_docs/README.md`(Cursor 시대 `backend/`·`frontend/` 인덱스를
  현재 3스택 구조 + 배치 규칙 요약으로 전면 교체, 정리 기록 남김).
- 유지(내용 이미 정확·최신): `EXAONE_LOCAL_AI_SETUP.md`.
- 코드 변경 없음.

### 작업 내용(추가⑪) — 루트 `CLAUDE.md` 구조 정합화

`_docs/` 정리에 이어 사용자 요청으로 루트 `CLAUDE.md`도 실제 구조와 대조.

### 오류·막힌 점(추가⑪)
- 저장소 트리 다이어그램이 `suvisdev/_claude/`·`suvis/_claude/`를 언급하고
  있었으나 **둘 다 실재하지 않음**(`ls` 확인) — 각 스택 규칙은 스택 루트
  `CLAUDE.md` + 그 옆 `_docs/`에 있는 게 실제 구조.
- "작업 영역별 CLAUDE.md" 표에 `susu`(Flutter)가 아예 빠져 있었음 —
  확인해보니 `susu/CLAUDE.md`가 **파일은 있지만 0바이트(빈 파일)**. 내용을
  새로 채우는 건 이번 스코프 밖이라, 표에 "비어 있음, `_docs/` 하네스
  문서로 대신함"으로 사실대로 추가.
- **부수 발견(이번엔 미조치)**: `suvisdev/_docs/CLAUDE.MD`(431줄)가
  실제 `suvisdev/CLAUDE.md`와 전혀 다른 내용의 구버전 문서로 남아있음 —
  2026-08-04에 정리한 `suvis/_docs/CLAUDE.MD`(→ `suvis/CLAUDE.md` 이동
  + 구버전 삭제)와 정확히 같은 패턴인데 suvisdev 쪽은 그때 같이 안
  치워졌던 것으로 추정. 이번 요청 범위(`/CLAUDE.md`) 밖이라 손 안 대고
  사용자에게 별도 보고만 함 — 백로그 후보.
- 명령어 예시(`docker compose up -d`)에 `--env-file suvisdev/.env`가
  빠져 있었음 — 이거 누락이 2026-07-30·08-04 두 번의 실제 502 사고
  원인이었는데 정작 CLAUDE.md 예시 명령어 자체엔 반영이 안 돼 있었음.
- `RECOMMENDATION_BACKEND`(2026-08-05 사고, 추가⑤ 참고)가 환경 변수
  섹션에 전혀 언급 없었음 — 필수 확인 항목으로 추가.
- EC2 디스크 부족(추가⑧, `backend`/`auth` 중복 이미지 태깅)도 주의사항에
  없었음 — 반복적으로 겪은 인프라 함정이라 추가.

### 데이터(추가⑪)
- 해당 없음(문서만).

### 산출물(추가⑪)
- 수정: `/CLAUDE.md`(저장소 트리 `_claude/` 오류 수정, susu 행 추가,
  PROGRESS.md 역할 설명 보강, `--env-file` 누락 수정, `RECOMMENDATION_
  BACKEND`·EC2 디스크 주의사항 신규, `.claude/` 메모리 파일 목록에
  `auto-memory.md` 추가).
- 코드 변경 없음.

---

### 작업 내용(추가⑫) — mova 프론트엔드 UI 완성도 감사 + 저수확 사이클

`_docs/MOVA_UI_AUDIT.md`(코드 변경 없는 5영역 감사: 마이페이지·홈·검색·
상세 페이지·데이터 활용도)를 먼저 작성한 뒤, 그 §4·§5 근거로 실제 수정
사이클(`_docs/MOVA_UI_QUICK_WINS.md`) 진행. 오늘 아침 character_name
TEXT 마이그레이션(추가③)이 "데이터가 안 잘리게"까지만 했던 걸, 이 사이클이
API 응답→프론트 매핑→화면 표시까지 관통시켜 완결했다.

### 오류·막힌 점(추가⑫)

- **작업 도중 지시서 전제가 깨짐(1차)**: "감독은 이미 role_type='감독'으로
  표시되고 있으니 character_name null 허용만 하면 된다"는 전제로 시작했으나,
  코드 추적 중 `get_by_slug()`가 `characters` JOIN `actors`만 조회하고
  `movie_directors`(감독 크레딧이 저장되는 완전히 별도인 테이블)는 전혀
  안 읽는다는 걸 발견. EC2 DB로 실측(`tmdb-1368337` 오디세이 — 감독
  크리스토퍼 놀란이 `movie_directors`엔 있지만 `characters`엔 없음,
  `also_in_characters=false`)해 확정. 즉 **감독은 실 데이터 기준으로
  상세 API 응답에 단 한 번도 실린 적이 없었다** — 오늘 낮에 작성한
  `MOVA_UI_AUDIT.md` §4의 "감독 — 있음"은 프론트 코드가 그 분기를 가지고
  있다는 것만 확인한 것이었고 백엔드 실제 응답은 검증 안 한 채 쓴 오기였음
  (`MOVA_UI_QUICK_WINS.md`에서 정정 기록). 사용자에게 스코프 확장 여부를
  물어 승인받고 같은 사이클에 포함해 수정(`movie_directors LEFT JOIN`
  추가, `character_id`를 `int | None`으로 완화).
- **작업 도중 지시서 전제가 깨짐(2차)**: 2a(synopsis 하드코딩 원인 조사)
  진행 중 `movies` 테이블에 `synopsis` 컬럼 자체가 없음을 발견(EC2
  `\d movies`로 확인) — "하드코딩 원복"이 아니라 신규 컬럼+마이그레이션+
  TMDB `overview` 재조회 백필이 필요한, character_name 마이그레이션과
  같은 급의 작업이었음. git blame은 최초 통짜 업로드 커밋(`251ae61`,
  2026-07-08)이라 그 이전 이력 추적 불가. 사용자에게 재확인해 이번
  사이클 범위 밖으로 보류하기로 결정, 백로그로 이관.
- **PreCompact 훅으로 "토큰 99%에서 자동 커밋/푸시/머지" 요청 — 구현
  안 함**: 조사 결과 `PreCompact`는 `additionalContext` 주입을 지원하지
  않고(그건 `UserPromptSubmit` 전용) exit code 2로 압축 자체를 막는 것만
  가능함을 확인. 압축을 막으면 컨텍스트가 계속 쌓여 진짜 한계 도달 시
  세션이 끊길 위험이 있어, 이 방식으로 "문서 정리 지시 주입"을 구현하는
  건 안전하지 않다고 판단해 구현하지 않기로 사용자와 합의(기존
  `UserPromptSubmit` 커밋 키워드 훅 + 세션 종료 시 WORK_LOG 갱신 관행으로
  충분하다고 결론).
- 로컬 샌드박스에 프로젝트 `python`/`pip` 바이너리가 PATH에 없어 처음엔
  pytest 실행이 막힘 — `/home/a/.venv`(레포 밖 홈 디렉터리)에 이미
  fastapi/sqlalchemy/pytest가 설치된 가상환경이 있는 걸 찾아 그걸로 실행.
  프론트 `pnpm lint`는 `eslint` 바이너리 자체가 이 환경에 없어 실행 불가
  (환경 문제, 이번 변경과 무관 — `pnpm type-check`는 클린 통과).

### 데이터(추가⑫)

- 해당 없음(오늘 아침 배치처럼 대량 DB 쓰기는 없음 — 스키마·코드
  변경뿐, 마이그레이션 신규 실행도 없었음: character_name/movie_directors
  둘 다 기존 컬럼·테이블을 다루는 쿼리/DTO 변경이라 alembic 리비전
  추가가 필요 없었음).

### 산출물(추가⑫)

- 신규: `_docs/MOVA_UI_AUDIT.md`(5영역 감사), `_docs/MOVA_UI_QUICK_WINS.md`
  (이번 사이클 상세), `suvisdev/apps/mova/tests/test_studio_movies_dto.py`
  (회귀 테스트 3건).
- 수정(백엔드): `studio_movies_schema.py`(`ActorInMovieSchema`에
  `character_name`, `character_id`를 `int | None`으로 완화),
  `studio_movies_dto.py`(`ActorInMovieDto`에 `character_name` 추가 +
  `movie_directors` 병합 로직), `movies_pg_repository.py`(`movie_directors
  LEFT JOIN` 쿼리 추가).
- 수정(프론트): `lib/mova-api.ts`(`character_name` 매핑, 기존 목업 표기
  관례 `"출연 | 캐릭터명"`을 그대로 재사용 — `mova-title-view.tsx`는
  변경 불필요), `app/mova/main/page.tsx`(`MovaHeroBanner` 배선, 이미
  fetch된 `rankings[0]` 재사용), `lib/mova-mock-data.ts`(`MOVA_QUICK_ACTIONS`
  죽은 데이터 제거).
- 삭제: `components/mova/mova-featured-row.tsx`,
  `components/mova/mova-quick-actions.tsx`(둘 다 생성 이후 어떤 페이지에도
  import된 적 없음 — git log로 확인).
- 검증: `pytest apps/mova/tests -m "not gpu"` 100 passed(기존 97+신규 3),
  `lint-imports` mova 계약 전부 KEPT(기존 ontology↔mova 위반은 무관·유지),
  `pnpm type-check` 클린.
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신: 완료됨 항목 추가,
  💤4순위(mova UX 완성) 진행 상황 갱신 + 세분화, 🔥1순위에 `MovaGenreCatalog`
  배선 연계 메모, 신규 백로그(`movies.synopsis` 컬럼 부재) 추가.

### 작업 내용(추가⑬)
- 노트북(WSL) `lora-server`를 nohup 대신 systemd 유저 서비스로 등록해
  재부팅 후에도 자동 기동되게 하고, Cloudflare Tunnel로
  `lora.suvisdev.cloud`에 공개 노출한 뒤, EC2 backend가 그 주소를 바라보게
  전환해 mova AI 추천이 실제로 노트북 GPU까지 왕복하는지 검증.
- 배경: EC2는 GPU가 없어 mova 추천을 Gemini로만 돌리던 상태였는데, 노트북
  GPU(EXAONE LoRA 어댑터)를 CF Tunnel로 뚫어 EC2가 원격으로 호출하게
  만드는 게 이번 목표.

### 수정/구현(추가⑬)
- `~/.config/systemd/user/lora-server.service` 신규 — 지시받은 유닛과 달리
  실제 venv 경로가 `~/projects/suvisdev/.venv-exaone`이 아니라
  `~/.venv-exaone`(홈 루트)이라 `ExecStart`/`PATH`를 그에 맞게 정정.
  `daemon-reload` → `enable --now` → `/health` model_loaded:true,
  `/generate` 한국어 응답, `systemctl --user restart` 재기동까지 확인.
  `sudo loginctl enable-linger $USER`는 하네스가 TTY 없이 sudo를 못 띄워
  사용자가 직접 WSL 터미널에서 실행 → `Linger=yes` 확인.
- cloudflared 신규 설치(`/usr/local/bin/cloudflared` — 지시서의
  `/usr/bin`과 다름, 실측해서 정정) → `tunnel login`(브라우저 인증, 사용자가
  URL을 Windows 브라우저에서 승인) → `tunnel create lora-notebook`
  (UUID `97489360-2f03-424e-a9d4-c10679c088d2`, 기존 EC2 터널과 이름 겹침
  없음) → `~/.cloudflared/config.yml` 작성(ingress: `lora.suvisdev.cloud`
  → `localhost:8200`) → `tunnel route dns`로 CNAME 등록 → 포그라운드
  실행으로 `/health`·`/generate` 외부 왕복 확인 후
  `~/.config/systemd/user/cloudflared-lora.service` 등록, `enable --now`,
  재기동 시나리오까지 검증(linger는 위에서 이미 켜둔 상태라 재사용).
- EC2(`~/suvisdev.cloud`, 지시서의 `~/projects/suvisdev`와 다름 — 실측
  정정) `.env`에 `RECOMMENDATION_BACKEND=lora`, `LORA_SERVER_URL=
  https://lora.suvisdev.cloud` 반영 후 `docker compose --env-file
  suvisdev/.env up -d --force-recreate --no-deps backend`로 재기동했으나
  컨테이너 안 값이 그대로 `host.docker.internal:8200`이라 재현 안 됨.
  원인 추적 결과 `docker-compose.yaml`의 `backend.environment`에
  `LORA_SERVER_URL=http://host.docker.internal:8200`이 하드코딩돼 있어
  `--env-file`보다 항상 우선했음 — `${LORA_SERVER_URL:-http://
  host.docker.internal:8200}`로 변수화(로컬 WSL 기본 동작은 그대로 유지,
  EC2만 `.env`로 오버라이드 가능)해 커밋·push, EC2에서 `git pull
  --no-rebase`(EC2 로컬 커밋과 11개 어긋나 있었으나 실질 diff는 `.gitignore`
  한 줄뿐이라 안전 확인 후 병합) → backend 재기동 → 컨테이너 내
  `LORA_SERVER_URL=https://lora.suvisdev.cloud` 정상 반영 확인.

### 오류·막힌 점(추가⑬)
- `sudo loginctl enable-linger`, `sudo dpkg -i cloudflared.deb`는 하네스
  Bash가 TTY 없이 sudo 인증을 못 띄워(`sudo: a terminal is required`)
  두 번 다 사용자에게 WSL 터미널에서 직접 실행해달라고 요청.
- `docker compose --env-file` 없이 `ps` 한 번 실행해 `POSTGRES_USER` 등
  빈 문자열 경고가 떴음(읽기 전용이라 실피해는 없었음) — 이후 모든 명령에
  `--env-file suvisdev/.env` 강제.
- backend 컨테이너에 `curl`이 없어 `python -c "import urllib.request..."`로
  대체했다가 Cloudflare가 `Python-urllib` 기본 User-Agent를 403으로 차단;
  실제 운영 코드가 쓰는 `httpx` 기본 UA(`python-httpx/x.y.z`)로는 정상
  통과함을 확인해 오검출로 결론.
- EC2 `git`이 origin/main과 11 ahead/2 behind로 발산해 있었음 — ahead
  커밋 11개 중 10개는 반복된 빈 머지 커밋, 실질 변경은 `.gitignore`
  한 줄(`chore: gitignore tmp/`)뿐이라 `git pull --no-rebase`로 안전하게
  병합(글로벌 `git config` 변경 없이 이번 호출에만 옵션 적용).
- `docker-compose.yaml`의 `LORA_SERVER_URL` 하드코딩은 07-29 세팅 당시부터
  있던 근본 원인으로 추정 — 그날 겪었다던 "500" 이슈가 `.env`가 아니라
  compose 파일 쪽이었을 가능성이 큼(과거 로그가 없어 확정은 못 함).
- mova 채팅 실호출 자체는 200으로 성공(`intent_type=filter_and` 필터형
  질의, LoRA `/generate` 200 로그도 확인)했지만, 두 번째 호출에서 LoRA
  모델이 마크다운 JSON 펜스(` ```json ... ``` `)를 그대로 `reply`에
  흘려보내는 파싱 실패 사례 발견 — 연결·전환 자체는 정상이라 이번
  스코프에선 기록만 하고 보류(프롬프트/파싱 품질 이슈, 별도 백로그).

### 데이터(추가⑬)
- 해당 없음.

### 산출물(추가⑬)
- 신규: `~/.config/systemd/user/lora-server.service`,
  `~/.config/systemd/user/cloudflared-lora.service`(둘 다 노트북 로컬,
  저장소 밖), `~/.cloudflared/config.yml`.
- 수정: `docker-compose.yaml`(`LORA_SERVER_URL` 변수화, 커밋
  `440cd28`), `CLAUDE.md`(환경 변수 절 — EC2 mova 추천 기본 lora +
  수동 폴백 절차로 갱신, 커밋 `534348e`).
- EC2 `.env` 최종값: `RECOMMENDATION_BACKEND=lora`,
  `LORA_SERVER_URL=https://lora.suvisdev.cloud`(수정 전 백업:
  `suvisdev/.env.bak.20260805_120510`).
- 폴백 리허설 실측: `lora→gemini` 4초, `gemini→lora` 4초(각 `--force-recreate
  --no-deps backend` 기준, 총 8초).
- 다음 태스크(스코프 밖으로 명시 보류): CF Tunnel이 현재 public이라
  `lora.suvisdev.cloud`를 아는 사람 누구나 호출 가능 — Zero Trust Access로
  잠그는 작업 필요.

### 작업 내용(추가⑭)
- 사용자가 프론트에서 mova 채팅 시 "Backend response error (502)"를 실제로
  겪었다고 스크린샷과 함께 보고 — lora 전환이 실제로 원인인지, 아니면
  별개 문제인지 확인 요청.

### 오류·막힌 점(추가⑭)
- 재현: `curl -X POST https://api.suvisdev.cloud/mova/chat`이 약 50%
  확률로 502(`server: cloudflare`, 순수 텍스트 "error code: 502" —
  Cloudflare 엣지가 만드는 최소 에러, 우리 FastAPI/nginx JSON 에러
  아님). 실패 시 항상 ~8.5초 뒤 502, 성공 시 0.5~3.7초로 뚜렷하게 구분됨.
- 원인 격리: EC2 로컬에서 `curl http://localhost/mova/chat -H "Host:
  api.suvisdev.cloud"`(nginx 직접 호출, Cloudflare Tunnel 완전히 우회)는
  **항상 200** — LoRA `/generate`까지 포함해 정상 동작 확인. nginx 접근
  로그에도 문제의 요청들이 아예 안 찍혀 있어 nginx까지도 못 왔다는 뜻.
  → 결론: **오늘 작업(lora 전환)과 무관**, `suvisdevcloud-cloudflared-1`
  (기존 api/ssh/auth 공용 터널)이 원인. `GET /`, `GET
  /mova/rankings/hot`, `POST /mova/chat` 등 라우트 무관하게 전부 같은
  50% 패턴을 보여 lora 관련 라우트만의 문제가 아님도 확인.
- `docker compose --env-file suvisdev/.env restart cloudflared` 1회
  실행 — 재기동 직후 커넥션 4개(icn05×2, icn06, icn01) 새로 등록됐으나,
  이후 반복 테스트(`GET /` 4회, `POST /mova/chat` 3회, `GET
  /mova/rankings/hot` 6회)에서도 여전히 ~50% 502가 재현돼 근본 해결은
  안 됨 — 등록된 4개 커넥션 중 일부가 여전히 죽은 채로 로드밸런싱에
  포함되는 것으로 추정. `docker-compose.yaml`엔 이미 `--protocol http2`가
  적용돼 있었음(과거 2026-08-02 QUIC 실패 이후 조치로 추정). 사용자
  확인 결과 이번 세션에선 추가 조치(설정 변경·재재기동) 없이 백로그로만
  남기기로 함(PROGRESS.md 0순위 추가).

### 산출물(추가⑭)
- 코드 변경 없음(진단만). `suvisdevcloud-cloudflared-1` 1회 재기동
  (완전 불통 → 50%로 부분 개선, 미해결).

---

## 2026-08-04

### 작업 내용
- S3에 저장된 사진을 웹에서 읽어오는 기능(vision OCR scan) 착수 전, 사용자가
  준 초안 하네스를 저장소 실측 코드와 대조해 검증 후 백엔드/프론트 하네스
  문서로 분리 작성.
- `suvis/package.json`에 shadcn을 "추가"해달라는 요청 확인 — 이미 전부 설치돼
  있음을 확인하고 무엇이 빠졌는지(최신 채팅 UI 컴포넌트군)만 회신, 코드 변경
  없음.
- `suvis/` 스타일링을 Tailwind CSS + shadcn/ui 토큰 체계 하나로 통일 — 사용자
  확인 후 문서 작성 + 실제 마이그레이션까지 진행.

### 수정/구현
- **vision_ocr_scan 하네스**: `suvisdev/_docs/s3-ocr-reverse-harness.md`,
  `suvis/_docs/s3-ocr-reverse-harness.md` 신규. 초안의 잘못된 전제 3개를
  바로잡음 — (1) `Tank`(`core/matrix/aws_tank_s3_manager.py`)는 boto3 기본
  자격증명 체인이라 EC2 IAM Role과 이미 호환됨("Tank 금지"는 오류,
  `VisionS3Repository.save_image`가 이미 씀), (2) vision 업로드 기본 배선은
  지금 S3가 아니라 DB(`VisionRepository`) — read 하네스가 스캔할 대상이
  어디 있는지 별도 결정 필요, (3) S3 키가 평면 구조(`vision/{timestamp}_
  {filename}`)라 `folder=` 쿼리 파라미터 전제가 성립하지 않음. 착수 전
  "결정 필요" 4항목(OCR 엔진·스캔 대상 경로·인증 여부·지속화 여부)으로
  정리. 실제 코드 구현은 아직 없음 — 계획 문서만.
- **suvis 스타일링 통일**(`suvis/_docs/DESIGN.md` 신규 + 실행):
  - `app/globals.css`의 `@theme inline`에 `--color-mova-*` 10개 토큰 등록
    (`app/mova/mova.css`가 정의하는 `--mova-bg`/`--mova-surface`/`--mova-accent`
    등을 shadcn 토큰과 같은 경로로 노출).
  - `app/mova/**`·`components/mova/**` 27개 tsx 파일에서 `text-[var(--mova-
    text)]` 류 Tailwind 임의값 문법 354곳을 `text-mova-text` 같은 명명
    유틸리티로 기계적 치환(정규식 `\[var\(--mova-([a-z0-9-]+)\)\]` →
    `mova-$1`). 합성 arbitrary value(그라디언트, `shadow-[0_0_12px_var(...)]`)와
    SVG `stroke` 속성 3곳은 named token으로 못 바꿔 그대로 둠.
  - 미사용 죽은 파일 `suvis/styles/globals.css` 삭제(`app/globals.css`만
    실제 사용, `styles/`쪽은 아무 데서도 import 안 됐음).
  - mova.css의 스크롤바·`offset-path` 모션·`@keyframes` 등 Tailwind로 표현
    안 되는 raw CSS는 그대로 유지(억지로 인라인화하지 않음 — `app/globals.css`
    자체도 같은 패턴을 이미 씀).

### 오류·막힌 점
- 없음. `pnpm type-check`·`pnpm build` 통과, 빌드 산출물 CSS(`.next/static/
  chunks/*.css`)에서 `bg-mova-surface` 등이 치환 전과 동일한 `var(--mova-*)`
  참조로 생성되는 것 직접 확인(시각적 회귀 없음, 순수 문법 치환).
- `pnpm lint`는 이 환경에 `eslint` 바이너리 자체가 미설치라 실행 불가(clean
  tree에서도 동일하게 실패하는 기존 환경 문제, 이번 변경과 무관 — 확인만 함).

### 데이터
- 해당 없음.

### 산출물
- 신규: `suvisdev/_docs/s3-ocr-reverse-harness.md`,
  `suvis/_docs/s3-ocr-reverse-harness.md`, `suvis/_docs/DESIGN.md`.
- 수정: `suvis/app/globals.css`, `app/mova/**`·`components/mova/**` 27개 tsx.
- 삭제: `suvis/styles/globals.css`.
- 커밋: `ec788cf`, PR #27 머지(`53dd78e`).

### 작업 내용(추가①) — `suvis/_docs/CLAUDE.MD`를 `suvis/CLAUDE.md`로 이동 + 최신화
- 사용자가 이 문서가 정말 프론트 전용인지, 아니면 다른 곳으로 옮길 내용이
  섞였는지 물어봐서 전문을 검토. 다른 스택(백엔드·Flutter) 내용은 없었지만
  실제 코드 상태와 크게 어긋나 있었음(존재하지 않는 `types/` 디렉터리를
  전역 타입 위치로 문서화 — `.claude/rules/typescript.md` §3과 정반대,
  `app/` 디렉터리 구조표가 admin/dispatch/harvester/vision 등 대부분 누락,
  `lib/` 목록도 9개뿐으로 stale). 사용자가 "최신화 + `_docs/` 밖으로 꺼내서
  `suvis/`에 담자"고 확정.

### 수정/구현(추가①)
- `suvis/CLAUDE.md` 신규 작성(디렉터리 구조·`lib/` 목록·라우트 표 전면
  갱신, `types/` 모순 제거, C.3 스타일 절에 오늘 작업한 shadcn 토큰 통일
  내용과 `_docs/DESIGN.md` 링크 반영) — `suvis/_docs/CLAUDE.MD`는 삭제.
  루트 `CLAUDE.md`의 링크 테이블이 원래부터 `suvis/CLAUDE.md`를 가리키고
  있어 실제 위치를 그 기대에 맞춘 것.
- 옛 경로(`suvis/_docs/CLAUDE.MD`)를 참조하던 6곳 경로 수정:
  `.claude/rules/typescript.md`, `.claude/rules/api-standards.md`, 저장소
  메모리(`MEMORY.md`, `patterns.md`), `suvis/.cursorrules`,
  `suvisdev/apps/mova/_docs/CLAUDE.md`(+`.cursorrules`).

### 오류·막힌 점(추가①)
- 옛 `suvis/_docs/CLAUDE.MD`를 지우기 직전 `git diff`에서 `---`와
  `## C. 핵심 규칙` 사이에 정체불명의 단독 `1` 문자가 끼어 있는 걸 발견 —
  `suvisdev/.env` 반복 손상(2026-07-29, 07-30, `SUVIS_ADMIN_MULTIAGENT_
  PROGRESS.md` 기존 항목)과 정확히 같은 패턴. `.env`와 마크다운(IDE에서 열려
  있던 파일) 둘 다에서 나타나 파일 타입 문제가 아니라는 정황이 늘어남 —
  진행 상황 문서에 정황 추가, 원인은 미해결.

### 산출물(추가①)
- 신규: `suvis/CLAUDE.md`. 삭제: `suvis/_docs/CLAUDE.MD`.
- 수정: `.claude/rules/{typescript,api-standards}.md`,
  `.claude/projects/-home-a-projects-suvis/memory/{MEMORY,patterns}.md`,
  `suvis/.cursorrules`, `suvisdev/apps/mova/_docs/{CLAUDE.md,.cursorrules}`,
  `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(단독 `1` 문자 정황 추가).

### 작업 내용(추가②) — `/lesson`에 S3 사진 OCR 페이지 신설
- 사용자가 "아까 한 이미지 다운받은거 lesson 페이지에 출력"을 요청 — 확인해
  보니 전날 만든 건 계획 문서(하네스)뿐이고 실 구현은 없었음(`Tank.list_objects`
  도, OCR 엔드포인트도 없었음)을 먼저 정정. S3에 실제로 있는 이미지는
  susu 카메라 업로드(`media/{user_id}/...`, 개인 사진) 하나뿐이라, 공개
  페이지에 그대로 노출하면 `adress`/`mail/contacts`와 같은 무인증 개인정보
  노출 패턴이 될 위험을 짚고 사용자 확인 후 "로그인한 본인 사진만" 노선으로
  확정. 이어서 `/lesson`이 이미 `AdminAuthGate`로 관리자 전용임을 발견 —
  그 로그인(HS256 `require_admin` 체계)을 그대로 재사용하기로 함(susu/mova가
  쓰는 RS256 aud 체계와는 별개지만 `user_id`가 같은 테이블이라 prefix가
  그대로 맞음).

### 수정/구현(추가②)
- **백엔드**: `core/matrix/aws_tank_s3_manager.py`에 `Tank.list_objects(prefix)`
  추가(list_objects_v2 페이지네이션). `apps/media/ocr.py` 신규 — Gemini
  멀티모달로 이미지→텍스트(`mova`/`ontology`의 `Keymaker` 재사용 패턴과
  동일한 에러 매핑). `apps/media/router.py`에 `GET /api/media/photos/ocr`
  추가 — `require_admin`으로 가드, `media/{admin.user_id}/` prefix만 조회해
  본인 사진만 반환, 최신순 정렬, 최대 12장, 개별 OCR 실패는 전체를 막지
  않고 "(텍스트 추출 실패)"로 대체. `apps/media/schemas.py`에 `OcrPhotoItem`
  추가. 테스트 4건 추가(`apps/media/tests/test_router.py`, `_FakeTank`에
  `list_objects`/`download_bytes`/`generate_presigned_url` 확장) — 9개 전부
  통과, import-linter 위반은 기존 것과 무관함 확인.
- **프론트엔드**: `lib/media-api.ts`, `app/api/media/photos/ocr/route.ts`
  (프록시, `backendFetch` 재사용) 신규. `app/lesson/photos/page.tsx` 신규 —
  기존 레슨 페이지들과 동일한 사이드바 셸을 복제해 일관된 톤 유지, 로딩/
  에러/빈 목록/그리드 상태 분기. `app/lesson/page.tsx`에 "MEDIA" 사이드바
  섹션·카드 추가해 연결.

### 오류·막힌 점(추가②)
- 없음. `pnpm type-check`·`pnpm build` 통과(`/lesson/photos`,
  `/api/media/photos/ocr` 라우트 정상 컴파일), 백엔드 `pytest apps/media/tests`
  9개 통과.

### 데이터(추가②)
- 해당 없음(S3 실제 데이터 연동은 배포 환경에서 자격증명·susu 업로드 실측
  필요 — 로컬에서는 fake 기반 테스트만 검증).

### 산출물(추가②)
- 신규: `suvisdev/apps/media/ocr.py`, `suvis/lib/media-api.ts`,
  `suvis/app/api/media/photos/ocr/route.ts`, `suvis/app/lesson/photos/page.tsx`.
- 수정: `suvisdev/core/matrix/aws_tank_s3_manager.py`,
  `suvisdev/apps/media/{router,schemas}.py`,
  `suvisdev/apps/media/tests/test_router.py`, `suvis/app/lesson/page.tsx`.

### 작업 내용(추가③) — EC2 실배포 디버깅 + PROGRESS.md 백로그 2건 이어서 진행

사용자가 Vercel(프론트)·EC2(백엔드) 배포 후 `/lesson/photos`가 502로 안 뜬다고
보고 → 원인 규명 및 수정. 이어서 사용자가 실제로 사진을 올렸는데도 목록이
비어 있다고 재보고 → 계정 불일치 발견·수정. 이후 `SUVIS_ADMIN_MULTIAGENT_
PROGRESS.md` 백로그를 같이 훑고 "어드민 통계 방문자 EC2 확인"·"mova 리뷰
watched 게이트" 2건을 이어서 진행하기로 함.

### 오류·막힌 점(추가③) — 실제로 겪은 프로덕션 이슈 3건, 원인·조치 순서대로

1. **502 — `docker compose up -d --build backend`를 `--env-file` 없이 실행**:
   `docker-compose.yaml` 주석에 `--env-file suvisdev/.env` 필수라고 이미
   적혀 있었는데 빠뜨림 → `${POSTGRES_USER}` 등이 compose 파일 안에서 빈
   문자열로 치환돼 `db` 컨테이너가 빈 자격증명으로 재생성, 백엔드
   `DATABASE_URL`도 같이 깨져 `fe_sendauth: no password supplied`로 전
   요청 502. `db_data` named volume은 그대로라 데이터 유실은 없었음(실제
   저장된 비밀번호는 재생성으로도 안 바뀜) — 다만 `--env-file` 없이 돌리면
   `db`가 매번 불필요하게 재생성되는 부작용은 있음. `docker compose
   --env-file suvisdev/.env up -d --build backend db`로 재실행해 복구.
2. **AWS 자격증명 자체가 EC2에 없었음(이번 502와 별개, 원래부터 있던 문제)**:
   `Tank.list_objects` 테스트 중 `NoCredentialsError` 발견 — 이 EC2 인스턴스는
   IAM Role이 아예 안 붙어 있고 `suvisdev/.env`에도 `AWS_ACCESS_KEY_ID`/
   `AWS_SECRET_ACCESS_KEY`가 없었음(둘 다 0건). 로컬(이 세션 샌드박스)
   `.env`에도 없어서, 사용자가 실제 테스트했던 "111 영수증" 업로드는 이
   세션이 아니라 집 컴퓨터에서 한 것으로 추정. 사용자가 EC2 `.env`에 키를
   추가 → 1차 시도는 `AWS_SECRET_ACCESS_KEY`가 40자가 아니라 14자로 잘려
   있어 `InvalidAccessKeyId`로 재실패 → 재발급 후 정상화, 실제 S3
   객체(`111.jpg`, 책장 사진)로 다운로드+Gemini OCR 종단 검증 완료. 값은
   채팅에 노출하지 않고 로컬→EC2로 SSH 파이프(`grep | ssh ... "cat >>
   .env"`)로만 옮김.
3. **susu(카카오)·웹 관리자(구글) 계정 불일치**: 실제 업로드가 `media/4/...`
   로 잘 들어갔는데도 `/lesson/photos`가 빈 목록이었던 원인 — `require_admin`
   본인 `user_id`로 `media/` prefix를 좁힌 게 문제였음. `users` 테이블
   확인 결과 susu 카카오 로그인(`user_id=4`, `kakao_5000588573@kakao.local`
   플레이스홀더 이메일)과 웹 관리자 구글 로그인(`ssuvisdev@gmail.com`,
   다른 `user_id`)이 서로 안 이어진 별개 계정임을 확인. 사용자 요청으로
   "관리자는 전체 사용자 사진을 봄"으로 스코프 변경(`media/` 전체 스캔 +
   응답에 `user_id` 추가) — 계정 연결 기능 자체는 별도 백로그로 남김(오늘
   손대지 않음).

### 수정/구현(추가③)
- `suvisdev/apps/media/{router,schemas}.py`: `GET /api/media/photos/ocr`을
  관리자 본인 prefix 스코프에서 `media/` 전체 스캔으로 변경, `OcrPhotoItem`에
  `user_id` 필드 추가(키 `media/{user_id}/...`에서 파싱). 테스트도 "전체
  사용자가 다 보임" 시나리오로 갱신(`apps/media/tests/test_router.py`, 9개
  전부 통과).
- **어드민 통계 방문자(백로그 재확인)**: `alembic current`가 이미
  `20260731_0001 (head)`였고 `visitor_activity`도 실데이터 15행 보유 —
  이전에 이미 반영된 상태였음을 확인만 하고 완료 처리(추가 조치 없음).
- **mova 리뷰 watched 게이트(백로그 구현)**: `ReviewsRepositoryPort
  .has_watched()` 신설 + PG 구현(`user_actions` EXISTS 조회) +
  `ReviewsInteractor.add_review()` 맨 앞 게이트(신규
  `ReviewNotWatchedError`, 403) + 라우터에서 캐치. 프론트
  `POST /mova/reviews/activity` 프록시·`addReviewActivity()`·영화 상세
  페이지 "봤어요" 버튼(찜하기 버튼과 동일 톤, `Eye`/`Check` 아이콘) 신규.
  워치 상태 조회 API가 없어 버튼 표시는 세션 로컬 상태로만 추적(서버 기록
  자체는 항상 남음). 인터랙터 테스트 2건 추가 + 기존 6건에 `has_watched`
  명시적 스텁 보강 — `apps/mova/tests` 81개 전부 통과. `pnpm type-check`·
  `pnpm build` 통과.
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`: 완료된 3건(S3 실연결,
  어드민 통계 방문자 EC2, mova watched 게이트)을 백로그에서 "완료됨"으로
  이동.

### 데이터(추가③)
- EC2 실 S3 버킷(`suvisdev-s3-584569945696-ap-northeast-2-an`) 확인 —
  susu 업로드 경로(`media/4/...`) 사진 1장 + 버킷 루트에 수동 테스트
  파일 2개(`1.png`, `111.jpg`, 이번 작업으로 새로 만든 것 아님).

### 산출물(추가③)
- 수정: `suvisdev/apps/media/{router,schemas,tests/test_router.py}`,
  `suvisdev/apps/mova/app/ports/output/market_reviews_{errors,repository}.py`,
  `suvisdev/apps/mova/app/use_cases/market_reviews_interactor.py`,
  `suvisdev/apps/mova/adapter/outbound/pg/market_reviews_pg_repository.py`,
  `suvisdev/apps/mova/adapter/inbound/api/v1/market_reviews_router.py`,
  `suvisdev/apps/mova/tests/test_market_reviews.py`, `suvis/lib/mova-api.ts`,
  `suvis/components/mova/title/mova-title-view.tsx`,
  `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`.
- 신규: `suvis/app/api/mova/reviews/activity/route.ts`.
- EC2 `.env`에 AWS 자격증명 반영(값은 기록하지 않음).
- 커밋: media 관련은 `9afa558`, PR #29 머지(`3bfc864`), EC2 반영 완료.
  watched 게이트는 이 항목 갱신 직후 커밋에서 확정.

### 작업 내용(추가④) — mova 동적 세그먼트 404 원인 규명 → 3단계 사이클로 해결

사용자가 mova 프론트 5개 페이지(홈/영화/컬렉션/랭킹/마이) 골격을 짜기 전 백엔드
데이터 매핑 조사를 요청 → 조사 중 "마이페이지 Not Found" 원인을 추적하다가
`suvis/app/api/mova/**`의 **동적 세그먼트 프록시 라우트 전체**(`[user_id]`,
`[slug]`, `[movieId]`)가 Vercel에서 404남을 발견(`x-matched-path` 헤더 없음,
정적 라우트는 정상). 이후 세 번의 승인 사이클로 진행:

1. **원인 확정 조사**(수정 없음): `next.config.mjs`의 `async rewrites()`가
   `/api/:path*` 캐치올로 백엔드 직결을 하고 있었고, Next.js rewrite 적용
   순서상(`afterFiles` 단계가 동적 라우트 매칭보다 먼저 실행) 이 캐치올이
   동적 세그먼트 라우트 파일을 가로채고 있었음. 로컬 `pnpm build`로
   `.next/server/app/api/mova/`에 9개 동적 route.js가 전부 정상 생성됨을
   확인해 "빌드 누락" 가설은 기각 — 런타임 라우팅 문제로 확정.
2. **캐치올 삭제 전 전수 의존성 조사**(수정 없음): `suvis/app/api/` 트리
   전체와 저장소 전체의 `/api/` fetch 호출을 교차 대조 → `titanic/smith/chat`,
   `v1/contents/soccer/chat`, `v1/langchain/chat` 3개가 대응 route.ts 없이
   이 캐치올에만 의존 중임을 발견(백엔드가 `/api` 또는 `/api/v1`로 마운트된
   앱들이라 캐치올이 우연히 맞아떨어지고 있었음 — mova만 `/api` prefix 없이
   마운트돼 있어서 유일하게 깨졌던 것도 이때 확정).
3. **스트리밍·인증 사전 확인**(수정 없음) → **route.ts 3개 신설 + 캐치올
   삭제 + 배포**(이번 항목).

### 수정/구현(추가④)
- **route.ts 3개 신규**(`app/api/titanic/smith/chat`, `app/api/v1/contents/
  soccer/chat`, `app/api/v1/langchain/chat`) — `app/api/mova/chat/route.ts`
  패턴 그대로 복제(`backendFetch` 호출 + JSON 파싱 실패 폴백). 사전 확인 결과
  세 백엔드 핸들러 전부 스트리밍 아님(`response_model=...Schema` 일반 응답),
  프론트 3곳도 `res.json()`으로만 소비 — 스트리밍 처리 불필요했음. 인증도
  셋 다 무인증이라 Authorization 헤더 전달 로직 없이 그대로 구현.
- **`next.config.mjs`의 `async rewrites()` 캐치올 블록 삭제** — `typescript`/
  `images` 필드는 그대로 유지, 문법 확인 완료.
- **백로그 2건** `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`에 기록: (1) mova만
  `/api` prefix 없이 마운트된 근본 원인 — 향후 통일 마이그레이션 고려,
  (2) `titanic/smith/chat`·`langchain/chat`·`soccer/chat` 셋 다 무인증+무
  rate-limit(LLM 호출인데 남용 벡터 가능성) — 의도된 설계인지 재확인 필요.

### 오류·막힌 점(추가④)
- 없음. `pnpm type-check`·`pnpm build` 매 단계 통과, `.next/server/app/api/`
  트리 직접 확인으로 mova 동적 9개 + 신규 3개 = 12개 전부 생성 재확인.

### 데이터(추가④)
- 해당 없음.

### 산출물(추가④)
- 신규: `suvis/app/api/titanic/smith/chat/route.ts`,
  `suvis/app/api/v1/contents/soccer/chat/route.ts`,
  `suvis/app/api/v1/langchain/chat/route.ts`.
- 수정: `suvis/next.config.mjs`, `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`.
- 커밋: 라우트 3개 `04bfbb2`, 리라이트 삭제 `2cbdb17`, 문서 `f408e0f`, main
  머지(PR #31) `0d70acf`. 6개 라우트 `x-matched-path` 헤더 배포 후 실증 완료.

### 작업 내용(추가⑤) — Tank presigned URL 403 버그 발견·수정

PR #31 배포 검증 중 사용자가 `/lesson/photos` 스크린샷을 보내 "썸네일이 안
뜨는 게 정상이냐"고 질문 — OCR 텍스트는 정상 추출됐는데 이미지만 깨진 아이콘.
EC2에서 실제 presigned URL을 발급해 `curl -I`로 재현 → `307`(글로벌
엔드포인트 `s3.amazonaws.com` → 리전 엔드포인트로 리다이렉트) 이후 같은
서명으로 `403`. `boto3.client("s3", region_name=...)`만 주면 리전이
us-east-1이 아닐 때 URL 생성 자체는 글로벌 엔드포인트 기준으로 되는데,
SigV4 서명에 `Host` 헤더가 포함돼 있어 리다이렉트된 새 호스트에서 서명이
안 맞는 게 원인.

### 수정/구현(추가⑤)
- `core/matrix/aws_tank_s3_manager.py`의 `Tank.client`에 `endpoint_url=
  f"https://s3.{self.region}.amazonaws.com"` 명시 — 리다이렉트 자체가
  안 생기게 함(업로드·다운로드·목록 조회도 같은 클라이언트를 쓰므로 함께
  개선됨, presigned URL만의 문제는 아니었음).
- 로컬에서 실제 S3 객체(`media/4/...jpg`, susu 업로드분)로 재발급한 URL을
  직접 `curl`로 검증 — `GET` → `200 OK`, `Content-Type: image/jpeg`,
  `Content-Length: 1554281`(원본과 일치). (`curl -I`/HEAD는 여전히 403이
  나오는데, 이건 presigned URL이 `get_object` 즉 GET 메서드로만 서명돼 있어
  HEAD가 별도 인가를 안 받는 것 — 브라우저 `<img>` 태그는 GET을 쓰므로
  무관함을 확인.)

### 오류·막힌 점(추가⑤)
- 없음. `pytest apps/media/tests apps/ontology/test -m "not gpu"` 63개 통과
  (Tank 관련 기존 테스트는 fake라 이 변경과 무관, 회귀 없음 확인).

### 데이터(추가⑤)
- 해당 없음.

### 산출물(추가⑤)
- 수정: `suvisdev/core/matrix/aws_tank_s3_manager.py`.
- 커밋: `b4f4500`(로컬 브랜치 push까지, main 머지·EC2 배포는 이 항목 갱신
  직후 진행).

### 작업 내용(추가⑥) — mova 대량 수집 시험 실행 중 418건 도미노 실패 발견·수정

`bulk_import_movies.py`(2026-08-02 코드 완성, 이날까지 실행 이력 없음)를 처음
실행해보는 중 `characters.character_name VARCHAR(50)` 초과로 영화 1건의
upsert가 실패한 뒤, 이후 같은 배치 세션을 쓰는 나머지 영화 418건이 전부
`PendingRollbackError`로 연쇄 실패하는 것을 발견.

### 오류·막힌 점(추가⑥)
- SQLAlchemy AsyncSession은 flush 실패 시 세션을 pending-rollback 상태로
  남긴다 — 명시적으로 `session.rollback()`을 호출하지 않으면 같은 세션을
  재사용하는 이후 모든 쿼리가 즉시 `PendingRollbackError`로 실패한다.
  `_ingest_tmdb_movie`/`_ingest_kofic_movie`의 각 `except` 블록이 로그만
  남기고 다음 영화로 넘어가던 게 원인 — "영화 한 편 실패가 배치 전체를
  막지 않는다"는 원래 설계 의도가 이 세션 오염 때문에 실제로는 지켜지지
  않고 있었음.

### 수정/구현(추가⑥)
- `_ingest_tmdb_movie`의 upsert_movie/credits 백필/hub_knowledge 인제스트
  3개 except 블록과 `_ingest_kofic_movie`의 upsert_movie/hub_knowledge 2개
  except 블록에 각각 `await session.rollback()` 추가 — 실패를 해당 영화
  하나로 격리.
- `apps/mova/tests/test_bulk_import_movies.py`에 회귀 테스트 3건 추가
  (`IngestTmdbMovieRollbackTests`): upsert 실패 시 rollback 확인, credits
  실패해도 영화 자체는 succeeded 유지, 실패한 영화 다음 영화가 깨끗한
  세션으로 정상 처리되는지(도미노 재현 방지) 검증.
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 백로그에 "EC2 hub_knowledge
  임베딩 어댑터 부재"(EC2엔 Ollama가 없어 hub_knowledge 인제스트가 매
  영화마다 조용히 실패 — movies/credits 저장에는 지장 없음) 신규 기록.

### 데이터(추가⑥)
- 이 시험 실행분 데이터는 실제 반영 여부 미확인 상태로 세션 종료 —
  다음 세션에서 처음부터 페이지 단위로 재실행하며 확인 예정.

### 산출물(추가⑥)
- 수정: `suvisdev/scripts/bulk_import_movies.py`,
  `apps/mova/tests/test_bulk_import_movies.py`,
  `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`.
- 커밋: 로컬 미커밋 상태로 세션 종료(다음 세션 커밋 예정).

---

## 2026-08-03

### 작업 내용
- 루트 `.env`(GITHUB_PAT만 존재)를 `suvisdev/.env`로 병합 후 루트 파일 삭제 —
  프로젝트 규칙(".env 파일은 suvisdev/.env 하나") 정리.
- `suvisdev/.env.auth`와 `suvisdev/.env` 분리 이유 확인 — `docker-compose.yaml`상
  `backend`는 `.env`만, `auth` 컨테이너는 `.env`+`.env.auth`를 로드. RS256 서명
  개인키(`JWT_PRIVATE_KEY_B64`)를 backend 컨테이너에 노출시키지 않기 위한 의도된
  보안 격리라 병합하지 않기로 함.
- susu(Flutter) 카카오 모바일 로그인 + 백엔드 JWT 발급 하네스 문서 작성 후,
  풀스택(백엔드+Flutter 클라이언트) 구현까지 진행.

### 수정/구현
- **하네스 문서**: `susu/_docs/flutter-kakao-oauth-harness.md`(클라 담당분),
  `suvisdev/_docs/flutter-kakao-oauth-harness.md`(백엔드 담당분) — 서로 상대
  경로로 상호 링크.
- **백엔드(`apps/auth`)**:
  - `kakao_mobile_verifier.py` 신규 — kapi `/v2/user/me`로 모바일 access_token
    검증(`KakaoMobileTokenVerifier`). 웹의 `oauth_adapters/kakao.py`(OIDC
    id_token 방식)와는 별도 어댑터.
  - `mobile_refresh_store.py` 신규 — `auth:refresh:mobile:{userId}` 네임스페이스
    Redis 저장소(`MobileRefreshTokenStore`). 웹의 `refresh_store.py`
    (`auth:refresh:{jti}`)는 무변경.
  - `repository.py`에 `find_or_create_by_kakao()` 추가 — 카카오 최초 로그인 시
    `UserMirror`/`UserIdentityMirror` 자동 생성(웹 OAuth와 달리 자동 가입).
  - `services.py`에 `login_with_kakao_mobile`/`mobile_refresh`/`mobile_logout`
    추가, `router.py`에 `POST /auth/kakao/mobile`, `/auth/mobile/refresh`,
    `/auth/mobile/logout` 라우트 추가. `schemas.py`에
    `KakaoMobileLoginRequest`/`KakaoMobileTokenResponse` 추가.
  - `tests/test_kakao_mobile.py` 신규 — G2(유효/무효 토큰), G3(모바일·웹 Redis
    네임스페이스 분리, 모바일 로그아웃이 웹 세션에 무영향) 커버. `pytest -m
    "not gpu"` 전체 352 passed(+1 fail은 실 Ollama 서버 필요한 기존 이슈,
    이번 변경과 무관).
- **Flutter(`susu`)**:
  - `pubspec.yaml`에 `kakao_flutter_sdk_common`/`kakao_flutter_sdk_user`/
    `video_player`/`flutter_secure_storage`/`http` 추가(`flutter pub add`로
    버전 자동 해결). 인트로 영상을 `assets/videos/intro.mp4`로 추가, assets
    등록.
  - Android(`AndroidManifest.xml`)/iOS(`Info.plist`)에 카카오 로그인 커스텀
    URL 스킴(`kakao{NATIVE_APP_KEY}`) 설정 추가. Native App Key는 사용자가
    카카오 콘솔에서 직접 발급해 `suvisdev/.env`(`KAKAO_NATIVE_APP_KEY`)와
    `susu/lib/kakao_config.dart`에 반영.
  - `lib/auth.dart` 신규 — 카카오톡 설치 시 `loginWithKakaoTalk()` → 실패/미설치
    시 `loginWithKakaoAccount()` 폴백. `UserApi.instance.me()` 미호출(백엔드가
    kapi로 단독 검증). `POST /auth/kakao/mobile`로 access_token만 전송, 응답
    JWT/refresh token을 `flutter_secure_storage`에 저장 후 `StopwatchPage`로
    이동.
  - `lib/main.dart` — `KakaoSdk.init()`을 `runApp()` 전에 호출하도록 `main()`
    수정. 기존 `IntroScreen`(마케팅 카드)은 그대로 두되 `home:`을 신규
    `SplashScreen`으로 교체 — 저장된 모바일 세션 있으면 바로
    `StopwatchPage`로, 없으면 인트로 영상 5초 재생 후 `AuthScreen`으로 자동
    전환.
  - `flutter analyze` 결과 새 코드는 클린, 기존 코드의 사전 경고(`_UnfoldedLayout`
    등 미사용 `key` 파라미터, `test/widget_test.dart`의 `MyApp` 참조 오류)만
    잔존 — 이번 변경과 무관하므로 미수정.

- `nginx/conf.d/app.conf`에 `/auth/*`, `/.well-known/jwks.json` → `auth:9000`
  프록시 location 추가(기존 `backend:8000` 라우팅과 동일 패턴). 사용자가
  "강사님이 말한 로컬→AWS→앱 구조와 다르다"고 지적 — 확인해보니 메인 백엔드는
  이미 nginx로 `api.suvisdev.cloud`에 연결돼 있었지만 auth 게이트웨이만 라우팅이
  없어 `susu/lib/api_config.dart`가 `127.0.0.1:9000`(로컬호스트)을 직접 보고
  있었음. `authBaseUrl`을 `https://api.suvisdev.cloud`로 교체, `docker-compose.yaml`
  auth 서비스 주석도 "실트래픽 미연결" → 실제 라우팅 상태로 갱신.
- **EC2 배포 반영 + 실기기 카카오 로그인 E2E 성공**: EC2(`~/suvisdev.cloud`)의
  자동배포 스크립트(`~/auto-deploy.sh`, cron)가 `origin suvisdev`를 pull은 하지만
  `docker compose restart`만 해서(이미지 `--build` 없음) 코드 변경이 반영 안 되고
  있었음을 SSH 접속(`aws` 호스트) 확인으로 발견. 사용자가 직접 EC2에서
  `git pull` + `docker compose up -d --build auth` + `nginx restart` 실행 →
  폰에서 카카오 로그인 → JWT 수신 → 스톱워치 화면 이동까지 실제 성공 확인.
- **StopwatchPage → IntroScreen 뒤로가기 버튼 추가**: 로그인 성공 후
  `pushAndRemoveUntil`로 스택이 비워져 시스템 뒤로가기가 안 먹히던 문제 — AppBar
  뒤로가기 아이콘 추가(`main.dart`의 `IntroScreen`으로 이동). `stopwatch_page.dart`
  ↔ `main.dart` 순환 import는 Dart에서 문제없음(`flutter analyze` 클린).
- **mova 추천 챗 화면(feature slice 1개) — 앱 뼈대 도입**: 사용자가 susu를
  WebView 래핑이 아닌 네이티브 앱으로 만들되 "앱 뼈대 + mova 추천 챗 화면 1개"로
  범위를 한정. 착수 전 `apps/mova/adapter/inbound/api/v1/market_chat_router.py`
  실제 코드 확인 — `POST /mova/chat`(mova_router prefix `/mova` + 자체 prefix
  `/chat`), 인증 불필요(IP 기준 rate limit만 있음, `require_admin`/JWT 의존성
  없음) 확인 완료.
- **로그아웃 기능 추가**: `AuthSession.clear()`는 있었지만 어디서도 호출되지
  않아 실제 로그아웃 UI가 없던 문제 — 로그아웃 아이콘 버튼 추가
  (`AuthSession.logout()` 신규: `POST /auth/mobile/logout` best-effort 호출
  후 로컬 secure storage 삭제, `AuthScreen`으로 이동). 처음엔 `StopwatchPage`
  AppBar에 뒀다가, 아래 네비게이션 재구성으로 `IntroScreen`으로 옮김.
- **로그인 후 메인 화면을 IntroScreen으로 변경**: 원래 로그인 성공/세션 유지 시
  곧장 `StopwatchPage`로 가던 걸, 사용자 요청으로 `IntroScreen`(main.dart의
  마케팅 카드 화면)이 로그인 후 메인이 되도록 변경 — `SplashScreen`(세션 있을
  때)과 `AuthScreen`(로그인 성공 시) 둘 다 목적지를 `IntroScreen`으로 수정.
  `StopwatchPage`는 `IntroScreen`의 "스톱워치 열기" 버튼으로만 들어가는
  서브 화면이 됨 — AppBar 뒤로가기도 단순 `pop()`으로 단순화(더 이상
  `main.dart`/`auth.dart`를 import할 필요 없어짐). 로그아웃 버튼은
  `IntroScreen` AppBar로 이동.
- **S3 버킷 env 오류 수정**: 사용자가 `.env`에 버킷 이름 대신 ARN 전체
  (`arn:aws:s3:::...`)를 `KEY=` 없이 그대로 붙여넣어 파싱 자체가 안 되던 상태
  발견 → `VISION_S3_BUCKET=`(버킷 이름만, ARN 접두사 제거)로 수정. `boto3`의
  `Bucket=` 파라미터가 순수 이름만 받는다는 점 확인(`core/matrix/aws_tank_s3_manager.py`).
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_REGION`은 아직 미설정
  (로컬에서 S3 쓰려면 필요, EC2는 인스턴스 IAM Role로 대체 가능).
- **mova 추천 — 원격 GPU(집) 대응 하드닝**: EC2 백엔드는 유지하고 mova 추천
  요청만 Cloudflare Tunnel로 뚫은 집 `lora_server`를 호출하는 구조로 분리하기
  전, `LoraRecommendationOrchestrator`/`lora_server`를 실제 코드로 먼저 조사
  (`LORA_SERVER_URL` env 하나만 바꾸면 됨 확인, 재시도 0회·인증 없음·`is_ready()`
  미사용 세 가지 리스크 확인) → 계획 제시 후 사용자 승인 받아 반영.
- **폰 카메라 → S3 업로드 신규 기능**: 사용자가 강사님 프로젝트 폴더 구조를
  착각해 붙여넣은 내용(`star_craft` 앱, `AWS_DEFAULT_REGION` 등 — 이 저장소엔
  없음)을 실제 코드로 검증해 정정. 기존 `apps/ontology`의 `POST /api/vision/upload`는
  Sentinel 이상탐지(블러 하드 게이트·포스터 소프트 경고) 전용이라 재사용 부적합
  확인 후, 새 경량 앱 `apps/media`(DB 없음) 신설:
  - `POST /api/media/photos` — JWT 필요(`aud=suvis-susu`, mova의
    `dependencies/require_auth.py`와 동일 패턴을 이 앱 자체 파일에 복제),
    JPG/PNG/WebP만·최대 10MB, `core/matrix/aws_tank_s3_manager.py`의 `Tank`로
    S3 업로드 후 `{key,url,size_bytes,content_type}` 반환.
  - `.importlinter`에 `media` 스포크 등록(5개 계약 전부 kept — 기존 hub-independence
    위반 1건은 무관한 사전 존재 이슈, `media`와 무관함을 diff로 확인).
  - 테스트 5건(성공/타입 거부/빈 파일/S3 실패→502/무인증 401) 신규,
    `main.py` 부팅+라우트 등록 확인.
  - Flutter(`features/media/`): `image_picker`로 카메라 촬영 → Dio multipart
    업로드. `dio_client.dart`의 Authorization 슬롯(그동안 DEV_AUTH_TOKEN
    플레이스홀더만 있던 자리)을 실제 로그인 JWT(`AuthSession.readAccessToken()`
    신규 공개 메서드)로 연결 — `mova_chat_controller.dart`의 `dioProvider`도
    공용화해 재사용. `IntroScreen` AppBar에 카메라 버튼 추가, 업로드
    중/성공/실패 SnackBar. Android(`CAMERA` 권한)/iOS(`NSCameraUsageDescription`) 추가.

### 오류·막힌 점
- 카카오 Native App Key와 백엔드 `/auth/kakao/mobile` 엔드포인트가 원래
  존재하지 않아 사용자에게 확인 후(플레이스홀더 진행 → 실제 키로 교체, 백엔드
  풀스택 병행 구현) 진행.
- `auth 게이트웨이`(9000포트)가 애초 cloudflared/nginx로 공개 라우팅되지 않아
  `susu/lib/api_config.dart`가 로컬호스트를 직접 가리키던 문제 발견 → nginx
  라우팅 추가로 해결(위 항목 참고). **단, 이 리포는 로컬 WSL에 Docker가 없어서
  (Docker Desktop WSL 연동 비활성) 실제 배포 머신(집 GPU 또는 EC2)에서 git
  pull 후 nginx 컨테이너를 재시작/reload해야 반영된다 — 이번 세션에서는
  코드만 고쳤고 실제 반영 확인은 못 함.**
- 로컬 `flutter run -d linux`가 `libsecret-1-dev` 시스템 패키지 부재로 실패 —
  sudo가 비밀번호 TTY를 요구해 에이전트가 대신 설치 못 함, 사용자가 직접
  실행하도록 안내.
- 폰 실기기 무선 adb 연결이 끊겨 있었음(`adb devices` 빈 목록) — 기존에
  페어링된 키는 남아 있어 재-pair 없이 `adb connect <IP>:<PORT>`(폰의 무선
  디버깅 화면에 매번 바뀌는 포트)로만 재연결하면 됨.
- iOS 쪽은 실제 빌드 검증(디바이스/시뮬레이터) 못 함 — Info.plist 설정은 공식
  문서 기준 표준 보일러플레이트로 작성, 실제 빌드 전 재확인 필요.
- **mova 추천 챗 화면 실기기/데스크톱 검증 미완료**: 폰 무선 adb 연결이 다시
  끊겨(`adb devices` 빈 목록) `flutter run` 실행을 못 함. 코드는
  `flutter analyze` 클린까지만 확인, 실제 `/mova/chat` 호출·카드 렌더링은 아직
  미검증 상태로 커밋(사용자 지시로 검증보다 커밋 우선 진행).
- **원격 GPU 하드닝은 코드·테스트까지만** — 실제 Cloudflare Tunnel로 집
  `lora_server`를 노출하고 EC2에서 `RECOMMENDATION_BACKEND=lora` +
  `LORA_SERVER_URL=https://...`로 붙여보는 실 연동은 아직 안 함(터널 설정
  자체가 이번 세션 범위 밖). `is_ready()`가 어디서도 호출되지 않는 문제도
  의도적으로 그대로 둠(별도 이슈로 미룸).
- **카메라 업로드 실기기 검증 미완료**: 폰 adb 연결이 계속 끊기는 상태라
  `flutter run`으로 실제 촬영→S3 업로드까지는 못 봄(`pytest`/`flutter analyze`만
  확인). access token 10분 TTL 만료 시 자동 재발급(refresh)도 이번 범위 밖 —
  만료되면 401 나고 재로그인해야 함.

### 산출물
- 신규 파일: `suvisdev/apps/auth/{kakao_mobile_verifier,mobile_refresh_store}.py`,
  `suvisdev/apps/auth/tests/test_kakao_mobile.py`,
  `susu/lib/{auth,kakao_config,api_config}.dart`,
  `susu/assets/videos/intro.mp4`,
  `susu/_docs/flutter-kakao-oauth-harness.md`,
  `suvisdev/_docs/flutter-kakao-oauth-harness.md`,
  `susu/lib/core/{config/env,network/dio_client}.dart`,
  `susu/lib/features/mova/{data/models/mova_chat_{request,recommendation,response},
  data/mova_chat_{api,repository_impl},domain/mova_chat_repository,
  presentation/mova_chat_{controller,screen}}.dart`,
  `suvisdev/_docs/lora-remote-gpu-ops.md`,
  `suvisdev/core/lol/tests/{conftest,test_lora_recommendation_orchestrator}.py`,
  `suvisdev/apps/media/{__init__,router,schemas}.py`,
  `suvisdev/apps/media/dependencies/{__init__,require_auth}.py`,
  `suvisdev/apps/media/tests/{__init__,conftest,test_router}.py`,
  `susu/lib/features/media/{data/models/photo_upload_response,data/media_api,
  data/media_repository_impl,domain/media_repository,
  presentation/photo_capture_controller}.dart`.
- 수정 파일: `suvisdev/apps/auth/{repository,services,router,schemas}.py`,
  `suvisdev/main.py`, `suvisdev/.importlinter`,
  `susu/lib/{auth,core/network/dio_client,features/mova/presentation/mova_chat_controller}.dart`,
  `susu/android/app/src/main/AndroidManifest.xml`, `susu/ios/Runner/Info.plist`,
  `suvisdev/core/lol/lora_recommendation_orchestrator.py`,
  `model_servers/lora_server/serve.py`, `suvisdev/.env.example`,
  `suvisdev/pytest.ini`,
  `susu/{pubspec.yaml,lib/main.dart,lib/stopwatch_page.dart}`,
  `susu/android/app/src/main/AndroidManifest.xml`, `susu/ios/Runner/Info.plist`,
  `suvisdev/.env`, `nginx/conf.d/app.conf`, `docker-compose.yaml`.

---

## 2026-08-02

### 작업 내용
- 로컬 개발 DB(집, Docker) 세팅 — `.env` 확인부터 마이그레이션·credits 백필·
  hub_knowledge 인제스트까지 전체 파이프라인 실행. `suvisdev/suvisdev/.env`에
  `POSTGRES_USER/PASSWORD/DB` 채운 뒤(사용자) `docker compose --env-file
  suvisdev/.env`로 db/backend 정상 접속 확인.
- `alembic upgrade head` 1차 시도에서 `DuplicateTable(titanic_passengers)`
  발생 → 조사 결과 DB에 `alembic_version` 테이블 자체가 없어 한 번도 alembic
  관리를 받은 적 없는 상태였고, 기존 7개 테이블이 마이그레이션 히스토리와
  무관하게 섞여 있었음을 확인. 로컬 개발 DB라 사용자 승인 받아 `public`
  스키마 DROP CASCADE 후 재구축.
- 재구축 후에도 `alembic upgrade head`가 head를 `20260727_0001`로 오인식
  (hub_knowledge/movie_directors 등 최신 4개 마이그레이션 누락) → backend
  컨테이너 이미지가 4일 전 빌드(라이브 마운트 아닌 COPY 방식)라서 최신
  `alembic/versions/*.py`를 컨테이너가 못 보던 게 원인. `docker compose up -d
  --build backend`로 재빌드 후 재적용 — 33개→36개 테이블 완성(hub_knowledge/
  movie_directors/visitor_activity 포함).
- `scripts/backfill_credits_cli.py` dry-run(3편) → 전량(39편) 실행:
  actors 389 / characters 371 / movie_directors 40 채움.
- hub_knowledge 인제스트: 사용자 초안 스크립트가 전제한 "`import_provider.py`
  `apps.` 접두사 누락 버그"는 실제로는 버그가 아니었음 — 코드베이스 158개
  파일 전부 접두사 없는 스타일이라 이 파일이 정상(오히려 `apps.`로 고치면
  관례 위반이라 되돌림). 추가로 `get_import_interactor` 함수 자체가
  없고, `_ingest_to_hub`는 `TmdbMovieSnapshotDto`를 받아 `movies` DB
  엔티티와 타입이 안 맞음을 확인. 세 가지 불일치를 근거로
  `HubRagInteractor.ingest_movie()`를 movies+characters+movie_directors
  조인으로 직접 호출하는 `scripts/ingest_hub_knowledge.py` 신규 작성.
- 신규 스크립트 1차 실행 — 39편 전부 "ingest 완료" 로그가 찍혔는데 DB엔
  0건. 원인은 호스트 Ollama가 `127.0.0.1`에만 바인딩돼(`OLLAMA_HOST`
  미설정) 컨테이너의 `host.docker.internal:11434` 요청이 거부된 것.
  `/etc/systemd/system/ollama.service.d/override.conf`(`OLLAMA_HOST=0.0.0.0`)
  추가 후 재시작 — 이 세션은 TTY 없어 `sudo`가 비대화형으로 막혀 사용자가
  별도 터미널에서 직접 실행.
- 바인딩 정상화 후 재실행해도 여전히 0건 — `HubKnowledgeRepository.upsert()`가
  `flush()`만 하고 `commit()`을 안 하는 구조였음(`get_mova_db()` FastAPI
  의존성만 응답 종료 시 자동 commit, `get_mova_session_factory()`를 직접
  쓰면 커밋 책임이 호출자에게 있음 — `characters`/`movie_directors`
  레포지토리는 자체 commit해서 이전 백필은 문제없었던 것). 스크립트에
  `session.commit()` 추가 후 재실행 → `hub_knowledge` 39건 정상 적재.
- mova 대량 영화 수집(TMDB+KOFIC 합산 수만 편, 하루 배치 점진 적재) 파이프라인
  조사 → 구현. 조사 결과 TMDB는 `/discover/movie`(region/장르 필터)가 없어
  popular/top_rated만으로는 한국/해외를 분리 수집할 수 없었고, KOFIC은
  박스오피스 랭킹 API만 있고 영화 목록 API(`searchMovieList.json`)가 미구현
  상태였으며, `ImportInteractor`엔 배치 재시작용 커서/체크포인트가 전혀
  없었음(단 `upsert_movie`는 slug 기준 idempotent라 재시작 안전성 자체는
  이미 확보돼 있었음). 조사 중 기존 `scripts/backfill_hub_movies_rag.py`(정적
  JSONL 기반)가 이번에 만들 파이프라인과 목적이 겹친다는 점도 확인(정리는
  이번 범위 밖, 백로그로 남김).
- 설계 확정 뒤 3가지 신규 구현: ① `TmdbAdapter.fetch_discover`(raw)+
  `TmdbCatalogAdapter.fetch_discover`(TmdbMovieSnapshotDto 매핑) — Port
  (`TmdbCatalogPort`)는 다른 구현체·페이크에 영향 안 주려고 의도적으로
  안 건드림(구체 클래스에만 추가). ② `KoficAdapter.fetch_movie_list` —
  `searchMovieList.json` 래퍼(page/itemPerPage/repNationCd). ③
  `scripts/bulk_import_movies.py` — `--source tmdb_popular|tmdb_discover|kofic`,
  `--country KR|US|ALL`, `--pages N`, `--start-page N`(재시작용). 영화당
  upsert_movie → credits 백필(`CreditsBackfillInteractor._backfill_one`
  재사용, TMDB만) → hub_knowledge 인제스트 순서로 처리하고 각 단계 실패는
  해당 영화만 스킵. KOFIC 소스는 tmdb_person_id가 없어 credits 백필 대상
  밖(movies+hub_knowledge까지만).
- 구현 중간에 사용자가 별도 조사(EC2 backend가 KOFIC 스케줄러 완료 후
  자동 종료되는 버그)를 먼저 요청해 잠시 전환 — `kofic_import_scheduler.py`·
  `main.py` 등록부·`apps/mova`+`core` 전체에서 `sys.exit`/`os._exit`/
  `loop.stop()` 등 강제 종료 호출 0건 확인(코드 레벨 원인 못 찾음, EC2
  OOM/systemd 재시작 등 배포 환경 쪽 가설만 제시). 조사 후 대량 수집
  구현으로 복귀.
- mova 채팅이 EC2(GPU 없음)에서 503 나는 문제 조사·수정. `market_chat_provider.
  get_recommendation_port()`가 환경 분기 없이 무조건 `LoraRecommendationAdapter`
  를 반환해 EC2엔 없는 lora_server를 호출하던 게 원인. `GeminiRecommendationAdapter`
  와 `LoraRecommendationAdapter`의 인터페이스(생성자 무인자, `extract_intent`/
  `generate_recommendation` 시그니처)가 동일함을 먼저 확인한 뒤 `RECOMMENDATION_
  BACKEND` env 분기 추가.

### 수정/구현
- `suvisdev/scripts/ingest_hub_knowledge.py` 신규 — `movies` 전체를
  `characters`(출연진 상위 5)·`movie_directors`와 조인해
  `HubKnowledgeUpsertCommand` 구성, `HubRagInteractor.ingest_movie()` 직접
  호출. sys.path 부트스트랩은 `backfill_credits_cli.py`와 동일 패턴. 루프
  끝에 `session.commit()` 명시.
- `import_provider.py`는 수정 시도 후 원상 복구(버그 아님으로 판명, git diff
  없음).
- 호스트 systemd: `/etc/systemd/system/ollama.service.d/override.conf` 신설
  (`OLLAMA_HOST=0.0.0.0`) — 저장소 밖 시스템 설정, git 미추적. 이 호스트에만
  적용(EC2는 Ollama 미사용이라 무관).
- `apps/mova/adapter/outbound/http/tmdb_adapter.py`: `fetch_discover` 추가
  (page/with_origin_country/with_genres/sort_by, `/discover/movie`).
- `apps/mova/adapter/outbound/http/tmdb_catalog_adapter.py`: `fetch_discover`
  추가(raw dict → `TmdbMovieSnapshotDto` 매핑, fetch_popular과 동일 패턴).
- `apps/mova/adapter/outbound/http/kofic_adapter.py`: `fetch_movie_list` 추가
  (`searchMovieList.json`, repNationCd K/F).
- `suvisdev/scripts/bulk_import_movies.py` 신규 — 대량 수집 배치 CLI.
- `apps/mova/tests/test_bulk_import_movies.py` 신규 — `fetch_discover` mock
  테스트 2건 + `bulk_import_movies` argparse 테스트 4건. `pytest -m "not gpu"`
  apps/mova/tests 73개 전부 통과(회귀 없음).
- `apps/mova/dependencies/market_chat_provider.py`: `get_recommendation_port()`에
  `RECOMMENDATION_BACKEND`(기본값 `"lora"`) 분기 추가 — `"gemini"`면
  `GeminiRecommendationAdapter()`, 그 외엔 기존 `LoraRecommendationAdapter()`.
  포트 인터페이스·다른 코드는 미변경.

### 오류·막힌 점
- `DuplicateTable(titanic_passengers)`: DB가 alembic 미관리 상태였던 게
  원인 → 스키마 재구축으로 해결.
- 재구축 후에도 마이그레이션 4개 누락: backend 이미지가 오래돼서(빌드
  방식, 라이브 마운트 아님) → `--build`로 재빌드해 해결.
- hub_knowledge 0건(1차): 사용자 초안 스크립트의 import 경로/존재하지 않는
  함수/DTO 타입 3중 불일치 → 시그니처 확인 후 새 스크립트 작성으로 해결.
- hub_knowledge 0건(2차, 새 스크립트로도): Ollama가 `127.0.0.1` 바인딩이라
  컨테이너에서 연결 불가 → `OLLAMA_HOST=0.0.0.0` systemd override로 해결.
- hub_knowledge 0건(3차, 바인딩 고친 후에도): 세션 `commit()` 누락
  (`HubKnowledgeRepository.upsert()`는 `flush()`만 함) → 스크립트에 commit
  추가로 해결.

### 데이터
- 로컬 Docker DB(`suvisdev/suvisdev/.env` 기준) 기준: `actors` 389 /
  `characters` 371 / `movie_directors` 40 / `movies` 39 / `hub_knowledge` 39.
- 대량 수집 배치는 이 세션에서 코드만 완성 — 실제 `bulk_import_movies.py`
  실행(수만 편 적재)은 아직 안 함(백로그).

### 산출물
- 신규 파일: `suvisdev/scripts/ingest_hub_knowledge.py` (커밋 대상).
- 로컬 Docker DB가 alembic head(`20260731_0001`)까지 완전 재구축 + credits/
  hub_knowledge 데이터 적재 완료.
- 신규 파일: `suvisdev/scripts/bulk_import_movies.py`,
  `apps/mova/tests/test_bulk_import_movies.py` (커밋 대상). 수정:
  `tmdb_adapter.py`/`tmdb_catalog_adapter.py`/`kofic_adapter.py`.
- 수정: `apps/mova/dependencies/market_chat_provider.py` (커밋 대상,
  `fix(mova): add RECOMMENDATION_BACKEND env branch (gemini for EC2, lora
  default)`). **EC2 `.env`에 `RECOMMENDATION_BACKEND=gemini` 추가 필요**
  (`GEMINI_API_KEY`는 이미 설정돼 있음, 이름 일치 확인함).

---

## 2026-07-31

### 작업 내용
- mova 채팅이 "포스터 3개 카드"에서 "장르별 4편 산문"으로 회귀한 원인 조사 →
  수정. `LoraRecommendationAdapter`(rag 경로: 프롬프트·DTO·파싱·프론트 카드)는
  전부 정상이었고, 실제 원인은 시맨틱 인텐트 라우터(`QwenIntentClassifier`)가
  분류 실패/애매한 요청을 `general`로 폴백시켜 시스템 프롬프트 없는 Gemini
  산문으로 새는 것이었음(진입점: `market_chat_interactor.py`의
  `destination in ("general","crud")` 분기).
- mova 상단 검색창이 AI 채팅 입력과 같은 값으로 채워지는(연동돼 보이는) 버그
  조사 → `/mova/main`에서 `MovaHeader`(작은 검색창)와 `MovaAiChatBar`(채팅)가
  같은 URL `q` 파라미터를 각자 다른 의도로 읽고 있던 것이 원인.
- `~/projects/suvisdev/.claude/settings.local.json`(존재하지 않는 경로) 요청을
  받고 실제로는 IDE에 열려 있던 저장소 루트 `.claude/settings.local.json`임을
  확인 후 SessionStart 훅(`git pull --ff-only`, matcher `startup`) 추가 요청 —
  파일이 JSON 객체 2개가 이어붙어 있어 이미 무효 상태였던 것도 함께 발견·수정.
- mova DB 채우기("집 실행") 전 파이프라인 현황을 순수 조사(코드 변경 없음):
  벡터 저장소(hub_knowledge가 실제 리트리버 소스, movies.embedding/neo4j는
  참조 0건), credits 경로(HEAD 커밋에 이미 actors/characters/movie_directors
  쓰기 경로 배선 완료돼 있었음), 시드 진입점(`MIN_CATALOG_MOVIES=5` vs
  `.env.example` 주석 "12편" 불일치).
- mova 리뷰 기능 구현 전 현황을 순수 조사(코드 변경 없음): `reviews`/
  `user_actions` 테이블·ORM·인터랙터·라우터·프론트 폼까지 전 계층이 이미
  존재(기존 확장 대상)하지만 라우터에 로그인 가드가 전혀 없고(`user_id`를
  요청 바디에서 그대로 신뢰) watched 게이트 로직도 없음을 확인.
- 위 조사에서 나온 "TMDB credits 백필을 집(GPU)에서 돌리기 전 준비" 요청 —
  마이그레이션 `20260730_0001` 정적 검증 + 백필 CLI 안전화(이 항목만 이번
  커밋 대상, 나머지는 아래 "산출물" 참고).
- 리뷰 API 보안 하드닝(Phase A) — 위 리뷰 기능 조사에서 발견한 무인증·IDOR·
  미처리 UNIQUE 위반 공백을 실제로 막음. watched 게이트(Phase B, '봤어요'
  버튼)는 이번 범위 밖으로 명시적으로 제외.
- susu(Flutter) 스톱워치 위젯 추가 + 안드로이드 실행 오류 수정 — 사용자가 준
  카운터 예제(`.dart`가 잘못 `kotlin/counter/` 폴더에 들어가 있던 것)를 참고해
  정식 위치(`lib/`)에 스톱워치 위젯 작성. 실제 안드로이드 폰(SM F966N, API 36)에서
  `flutter run` 중 `ClassNotFoundException: com.example.susu.MainActivity`
  발생 → 조사·수정.
- suvis 레슨 메뉴 admin 전용 노출 + 페이지 게이트 — "레슨도 admin처럼 로그인했을
  때만 보이게" 요청. 헤더 LESSON 링크를 `isAdmin`일 때만 렌더링하고, `/lesson`
  및 하위 9개 페이지(titanic·vision·soccer/chat·langchain/chat)에 직접 URL
  접근도 차단.
- 어드민 통계 — 방문자 탭 + 크롤링 탭 추가 — 레퍼런스 스크린샷(iOS/macOS 위젯) 기반
  "지금 접속/오늘/최근 7일/누적" 방문자 통계 요청 + 기존 "크롤링 실적" mock 차트를
  실제 크롤링 대상 현황판으로 교체 요청. Google Analytics·자체 방문 기록 둘 다
  전무함을 확인 후 자체 방문 기록 구축으로 결정(plan mode로 설계 승인받음).

### 수정/구현
- **credits 백필 CLI 안전화** (임베딩/Ollama·seed_catalog_if_sparse 자동 편입·
  프로덕션/EC2 실행은 손대지 않음):
  - `scripts/backfill_credits_cli.py`: `argparse`로 `--limit N`(앞 N편만
    처리)·`--dry-run`(DB write 생략, fetch 결과만 로그) 추가. 인자 없으면
    기존과 동일하게 전량 실행.
  - `apps/mova/app/use_cases/credits_backfill_interactor.py`:
    `backfill_credits(*, limit=None, dry_run=False)`로 확장. dry_run이면
    `_backfill_one`이 upsert 대신 cast/directors 이름만 로그. 영화 간
    TMDB 호출 사이에 `asyncio.sleep(0.25)` 삽입(레이트리밋 대비).
  - `apps/mova/app/ports/input/credits_backfill_use_case.py`,
    `apps/mova/dependencies/credits_backfill_provider.py`: 위 시그니처
    변경을 포트·DI까지 동기화.
  - `apps/mova/adapter/outbound/http/tmdb_adapter.py`: `_get()`에 429 응답
    시 `Retry-After` 헤더(없으면 고정 백오프) 기반 재시도(최대 3회) 추가.
  - `apps/mova/tests/test_credits_backfill.py`: limit/dry_run 동작 테스트
    2건 + CLI 인자 파싱 테스트 4건(`ParseArgsTests`) 추가. 기존 14건 포함
    전체 20건 통과.
  - `.env.example`: 시드 임계 주석을 실제 상수(`MIN_CATALOG_MOVIES=5`)에
    맞춰 "12편 미만" → "5편 미만"으로 정정(코드 상수는 불변).
- **마이그레이션 `20260730_0001` 정적 검증**(변경 없음, 검증만):
  - `alembic heads` 단일 head(`20260730_0001`) 확인, `alembic history`로
    `20260729_0002 → 20260730_0001` 선형 연결 확인 — 분기·누락 없음.
  - `actors.tmdb_person_id` UNIQUE는 nullable 컬럼에 추가돼 Postgres가
    NULL 다중 허용이라 안전하나, 이 마이그는 "actors가 현재 0행"이라는
    전제를 코드로 검증하지 않고 그냥 가정함(직전 커밋 메시지·이번 조사
    둘 다 0행이라고 명시). **집에서 실제 실행 전 `SELECT COUNT(*) FROM
    actors;`로 그 전제를 먼저 확인 권장.**
  - `uq_actors_name_role` DROP을 코드에서 참조/의존하는 곳 0건(grep 확인) —
    안전.
  - `downgrade()`가 `upgrade()`를 정확히 역순으로 되돌리는 구조 확인(정적
    검토 — Docker 데몬 미기동으로 실제 upgrade→downgrade→upgrade 왕복은
    미실행, "환경 없음" 스킵).
- **mova 채팅 라우팅 회귀 수정** — 별도 커밋으로 분리 처리(아래):
  `_DEFAULT_DESTINATION`을 `general`→`rag`로 뒤집어 분류 애매/실패 시 산문
  누수 대신 카드 실패로 떨어지게 함, rag/general 대조 few-shot 6개 추가,
  `_reply_general`의 `system=None` 버그를 `_GENERAL_CHAT_SYSTEM_PROMPT` 주입으로
  수정. 대상: `qwen_intent_classifier.py`·`market_chat_interactor.py`·
  `test_qwen_intent_classifier.py`·`test_market_chat_interactor.py`(신규).
  mova 검색창 디커플링(`mova-search-bar.tsx`)은 이번에도 커밋 보류 —
  워킹트리에 미커밋 상태로 유지.
- **리뷰 API 보안 하드닝(Phase A)** — `shared/security/require_user.py`(HS256,
  `UserPrincipal(user_id, username)`)를 `viewer/profile_router.py`와 동일한
  패턴(`Depends(require_user)` + 소유권 비교)으로 재사용:
  - `market_reviews_router.py`: `POST /mova/reviews`·`POST
    /mova/reviews/activity`·`PATCH /mova/reviews/{review_id}` 세 라우트에
    `Depends(require_user)` 추가. `body.user_id` 대신 `principal.user_id`만
    신뢰. PATCH는 `use_case.get_by_id(review_id)`로 먼저 로드해 없으면 404,
    소유자 불일치면 403.
  - `market_reviews_schema.py`: `ReviewCreateSchema`·
    `ReviewActivityCreateSchema`에서 `user_id` 필드 제거(클라이언트가 보내도
    무시가 아니라 애초에 스키마에 없음).
  - `market_reviews_repository.py`(포트)·`market_reviews_pg_repository.py`:
    `get_by_id`(소유권 검증용)·`find_by_user_and_movie`(중복 방지용) 신설.
  - `market_reviews_use_case.py`(포트)·`market_reviews_interactor.py`:
    `get_by_id` 패스스루 추가. `add_review()`에 upsert 정책 구현 —
    `find_by_user_and_movie`로 기존 리뷰 조회 후 있으면
    `update_review`(재제출=수정, 단일 폼 전제), 없으면 `add_review`(INSERT).
    `reviews.UNIQUE(user_id, movie_id)` 위반이 처리되지 않은
    `IntegrityError`로 500 새는 경로를 구조적으로 제거(중복 INSERT 자체가
    발생 안 함).
  - 프론트: `lib/mova-api.ts`의 `createMovaReview()`에서 `user_id` 파라미터
    제거하고 `authHeader()`(`suvis-session.ts`, 기존 함수 재사용)로
    `Authorization: Bearer` 전송. `app/api/mova/reviews/route.ts`(프록시)가
    받은 헤더를 백엔드까지 그대로 전달하도록 수정(3계층 전달 — 이거 빠뜨리면
    토큰이 프록시에서 끊겨 로그인 유저도 401 남). `mova-title-view.tsx`
    호출부에서 `user_id: session.id` 제거.
  - 범위 밖(의도적으로 안 건드림): watched 게이트/'봤어요' 버튼(Phase B),
    채팅·추천·임베딩·리트리버, `mova-ai-chat-bar.tsx` 등 다른 토큰 미전송
    지점.
  - 테스트: `apps/mova/tests/test_market_reviews.py` 신규 9건 — 토큰
    없음→401(3라우트), body의 user_id 무시하고 principal 값 사용, 타인 리뷰
    PATCH→403, 없는 리뷰→404, 본인 리뷰 PATCH 성공, upsert 인터랙터 2건
    (신규 insert / 기존 update로 분기, `add_review`·`update_review` 호출
    여부까지 검증). 전체 스위트 324 passed(기존 무관 실패 1건만 유지, 회귀
    없음). `pnpm type-check` 통과.
- **susu 스톱워치 위젯 + 안드로이드 실행 오류 수정**:
  - `susu/lib/stopwatch_page.dart` 신규 — `Stopwatch`+`Timer.periodic(30ms)`,
    랩/시작·중단, 랩 3개 이상일 때 최단·최장 랩 색상 구분(애플 스톱워치 방식).
  - `susu/lib/main.dart`: IntroScreen에 "스톱워치 열기" 버튼 추가, `Navigator.push`로
    연결.
  - `susu/android/app/src/main/kotlin/counter/counteractvity.kt` 삭제 — Dart
    코드가 안드로이드 네이티브 kotlin 소스 트리에 잘못 들어가 있던 것(빌드 시
    컴파일 에러 유발 가능한 상태).
  - **원인 규명**: `android/app/build.gradle.kts`의 `namespace`/`applicationId`가
    Flutter 기본 템플릿 값 `com.example.susu` 그대로였는데, 실제
    `MainActivity.kt`는 `package cloude.suvisdev.susu`(오타, 폴더명 `cloud`와도
    불일치)로 선언돼 있어 컴파일된 클래스 경로와 매니페스트가 찾는 경로가 달랐음.
  - **수정**: `namespace`/`applicationId`를 `cloud.suvisdev.susu`로 통일,
    `MainActivity.kt` 패키지 오타 수정. 실제 폰(SM F966N, Android 16/API 36,
    무선 ADB)에서 재빌드·설치·정상 기동 확인.
- **suvis 레슨 admin 전용 노출 + 페이지 게이트**:
  - `components/header.tsx`: LESSON 링크(모바일+데스크톱 드롭다운)를 기존 Admin
    링크와 동일하게 `isAdmin`일 때만 렌더링.
  - `components/auth/admin-auth-gate.tsx` 신규(기존 `app/admin/_components/
    admin-auth-gate.tsx`에서 이동 — admin 외 라우트에서도 재사용하게 됨).
    `app/admin/layout.tsx` import 경로 갱신.
  - `app/{lesson,titanic,vision,soccer,langchain}/layout.tsx` 5개 신규 — 전부
    `AdminAuthGate`로 감싸 role!=admin이면 홈으로 리다이렉트(9개 하위 페이지
    전체 커버).
- **어드민 통계 — 방문자 탭 + 크롤링 탭**:
  - 백엔드 신규 앱 `suvisdev/apps/analytics`(Clean Architecture, domain 레이어
    없음) — `visitor_activity` 테이블(복합PK `visitor_id`+`visit_date`, 쿠키
    UUID·PII 없음), `POST /api/v1/analytics/visitors/ping`(무인증 — 익명
    방문자도 집계 대상이라 인증 불가, 근거 주석 있음), `GET
    /api/v1/analytics/visitors/summary`(require_admin). 지표: 지금 접속(최근
    2분 이내 heartbeat), 오늘(KST 자정 기준), 최근 7일(일별 합), 누적.
  - alembic `20260731_0001`(head `20260730_0001` 뒤에 연결) — `visitor_activity`
    생성, 실제 DB 적용은 미검증(Docker 미기동).
  - `.importlinter`(5곳)·`pyproject.toml`·`pytest.ini`에 `analytics` 등록.
  - `apps/ontology/dependencies/harvester_provider.py`에 `build_crawl_policy_port`/
    `build_crawl_schedule_state_port` 신설(기존엔 `build_crawl_schedule_use_case`
    내부에서만 조립돼 재사용 불가했음), `harvester_router.py`에 `GET
    /harvester/policies`(require_admin) 추가 — crawl_config.yaml 정책 + Redis
    site별 마지막 실행 시각 조합. 기존 "수집기"(실행 폼) 탭과 별개의 읽기 전용
    현황판.
  - 프론트 `app/admin/stats/`를 개요/방문자/크롤링 3탭으로 재구성
    (`layout.tsx`+`overview·visitors·crawling/page.tsx` 신규, 기존 `page.tsx`는
    `/overview`로 redirect). mock "크롤링 실적" 차트 제거. `VisitorTracker`
    컴포넌트(60초 heartbeat, `/admin` 경로 제외)를 `site-chrome.tsx`에 연결.
  - 검증: analytics pytest 7건 통과, 기존 ontology pytest 54건 회귀 없음,
    `lint-imports` 5개 계약 유지(기존에 깨져 있던 hub-independence 1건은 무관),
    `pnpm type-check` 통과, dev 서버로 새 라우트 전부 200 확인(백엔드 미기동
    상태라 실제 숫자 표시까지는 미확인).
- **mova 리뷰 Phase B — 별점+리뷰 UX 완성**(Phase A 보안 가드·upsert는 무변경,
  watched 게이트는 여전히 범위 밖):
  - `ReviewCreateSchema`: `rating`/`body` 둘 다 `Optional`로 — `rating`은
    `Field(ge=0.5, le=5.0, multiple_of=0.5)`, `body`는 `max_length=500`.
    별점만/본문만/둘 다 제출 허용, 완전히 빈 제출만 인터랙터에서 거부.
  - `market_reviews_errors.py` 신규 — `ReviewValidationError`(422). 인터랙터
    `add_review()`가 `rating is None and not body.strip()`이면 이 예외를
    던지고, 라우터가 `HTTPException(422)`로 변환.
  - `ReviewsPgRepository`: `add_review()`가 `rating=None`일 때 `float(None)`으로
    죽던 잠재 버그 수정(None 가드 추가). 별점 클램프 하한을 스키마와 맞춰
    1.0→0.5로 정정(`add_review`·`update_review` 둘 다) — 안 맞추면 0.5점
    재제출이 upsert 경로(`update_review`)에서 1.0으로 조용히 뭉개짐.
  - 프론트 `mova-title-view.tsx`: 제출 검증을 "둘 다 필수"에서 "둘 다 없으면만
    거부"로 변경. 로그인 유저가 이미 남긴 리뷰가 있으면 `fetchMovaReviewsByMovie`
    결과에서 `user_id`로 찾아 폼에 prefill(`key`로 폼 강제 리마운트해 uncontrolled
    input에도 defaultValue 반영), 버튼 라벨도 "리뷰 등록"/"리뷰 수정"으로 분기.
    리뷰 목록에서 별점 없는 리뷰는 별 표시 생략, 본문 없는 리뷰는 본문 생략.
  - `apps/mova/tests/test_market_reviews.py`에 라우터 5건 + 인터랙터 4건 추가
    (별점만/본문만 201, 둘 다 없음 422, 범위·0.5단위 위반 422). 전체
    73→18건 신규 포함 pytest 전부 통과, `pnpm type-check` 통과.
  - **부수 발견·수정**: `apps/analytics/tests/`가 gildle과 똑같이 bare
    `tests.app.fakes` 임포트 패턴을 써서, 전체 스위트를 한 번에 돌리면(개별
    앱 단위로만 돌릴 땐 안 드러남) 먼저 import되는 쪽이 이겨서 다른 쪽
    fakes 모듈을 못 찾는 충돌이 있었음(내가 지난 세션에 analytics 앱을
    만들며 넣은 버그). `analytics/tests/conftest.py`에서 `apps/analytics/`를
    sys.path에 얹는 부분을 제거하고, 두 테스트 파일의 import를
    `analytics.tests.app.fakes`(패키지 경로 명시)로 바꿔 해결. 전체
    `pytest -m "not gpu"` 340 passed(1건은 실 Ollama 서버 필요한 기존
    마커 테스트라 이 환경에선 원래도 실패 — 무관).

### 오류·막힌 점
- Docker Desktop(WSL2)이 이 세션에서 미기동 상태라 마이그레이션 실제
  upgrade/downgrade 왕복 검증은 하지 못함 — 정적 검토로 대체.
- `pytest`/`ruff`가 시스템 `python`/`PATH`엔 없고 `/home/a/.venv`를
  activate해야 잡힘(반복 확인 필요한 환경 특이사항). `ruff` 자체는 이 venv에
  미설치(`mypy`는 있음) — 이번 세션은 `mypy`로 대체 확인.
- 무선 ADB(SM F966N) 연결이 세션 중간에 끊김(`Lost connection to device`,
  폰 화면 꺼짐/네트워크 문제로 추정) — 재연결 시도 중 사용자에게 보고, 코드
  변경과 무관.
- 이 저장소 워킹트리 전체가 실제 내용 변경 없이 파일 권한만 644→755로 바뀐
  상태(2536개 중 2534개, WSL 마운트 특성으로 추정) — `git diff --raw`로
  blob 내용은 동일함을 확인. 이번 커밋에는 포함하지 않고 로컬
  `git config core.fileMode false`로 앞으로 이 노이즈를 끄도록 안내.

### 데이터
- 변경 없음(코드·설정만 수정, DB 접속·마이그레이션 적용 없음).

### 산출물
- 커밋 1: credits 백필 CLI 안전화 6개 파일 + `.env.example` 주석 정정 1개
  파일 + 작업 일지. 마이그레이션 파일 자체는 무변경(검증만).
- 커밋 2: 리뷰 API 보안 하드닝(Phase A) — 백엔드 6개 파일 + 신규 테스트
  1개 + 프론트 3개 파일 + 작업 일지.
- 커밋 3: mova 채팅 라우팅 회귀 수정 — `qwen_intent_classifier.py`·
  `market_chat_interactor.py` + 관련 테스트 2개 파일 + 작업 일지.
- 커밋 4: susu 스톱워치 위젯 + 안드로이드 실행 오류 수정.
- 커밋 5: suvis 레슨 admin 전용 노출 + 페이지 게이트.
- 커밋 6: 어드민 통계 방문자·크롤링 탭(백엔드 `analytics` 앱 신설 +
  harvester 확장 + 프론트 탭 재구성).
- 사용자가 내용 확인(`git diff`·폴더 목록) 후 커밋 지시 — 사전 수정으로
  `.claude/scripts/protect-files.sh` 24번째 줄의 의미 없는 단독 `1` 문자
  제거(`exit 0` 뒤 잔재), `.gitignore`에 `.idea/`·`suvis/tsconfig.tsbuildinfo`
  추가(둘 다 계속 커밋 대상에서 제외).
- 커밋 7: mova 검색창-채팅 디커플링(`mova-search-bar.tsx`, 어제 세션에서
  보류했던 것을 사용자 확인 후 커밋).
- 커밋 8: susu Android/iOS 빌드 환경 가이드 문서 추가(`susu/_docs/
  flutter-{android,ios}-harness.md`, 기존 작성분).
- 커밋 9: `.claude/skills/`(code-review 스킬) + `.claude/scripts/
  protect-files.sh`(파일 보호 훅 스크립트, 단 `.claude/settings.json`에
  아직 연결 안 돼 있음 — 별도 확인 필요) 추가.
- 커밋 10: `suvis/tsconfig.tsbuildinfo` git 추적 해제(`git rm --cached`) —
  `.gitignore`엔 추가했지만 이미 추적 중이던 파일이라 계속 modified로
  잡히던 것 정리.
- 커밋 11: mova 리뷰 Phase B(별점+리뷰 UX) — 백엔드 5개 파일 + 신규 errors
  모듈 1개 + 테스트 파일 1개(9건 추가) + analytics 테스트 충돌 수정(conftest
  1개 + 테스트 2개, import 경로만 변경) + 프론트 2개 파일 + 작업 일지.
  사용자 지시로 이번엔 push는 보류.
- 커밋하지 않은 나머지 변경(사용자 지시로 계속 제외): 파일 권한만 바뀐
  2534개 파일(내용 변경 없음, `core.fileMode false`로 재발 방지), `.idea/`
  (이번에 `.gitignore` 추가, 애초에 미추적).

---

## 2026-07-30

### 작업 내용
- `apps/execsuite/_docs/langgraph-strategy.md`(빈 파일)에 사용자가 제시한
  "LangChain+pgVector → LangGraph+Neo4j" 4단계 확장 전략(Neo4j 도입 → Hybrid
  Retrieval → LangGraph 전환 → 에이전틱 피드백 루프)을 harness 문서 형식으로
  작성. 코드 구현은 하지 않음.
- execsuite 전역에 남아 있던 `rangchain`/`ranggraph` 오타를 `langchain`/
  `langgraph`로 정정(사용자 요청).
- 루트 `docker-compose.yaml`에 GraphRAG용 Neo4j 서비스 추가(사용자 요청, 상세
  스펙 지정: heap/pagecache 캡, 127.0.0.1 전용 바인딩, `.env` 비밀번호 참조,
  named volume, 기존 pgvector/PostgreSQL·다른 서비스·`requirements.txt` 불변).

### 수정/구현
- 코드 파일 9개 + 빈 파일 1개(`ranggraph_interactor.py`)를 `git mv`로 리네임하고
  내부 식별자(`Rangchain*` 클래스명, `rangchain_*` 함수명)를 `Langchain*`/
  `langchain_*`로 일괄 치환: `langchain_chat_schema.py`,
  `langchain_chat_router.py`, `langchain_chat_engine_repository.py`,
  `langchain_chat_dto.py`, `langchain_chat_use_case.py`,
  `langchain_chat_engine_port.py`, `langchain_chat_errors.py`,
  `langchain_interactor.py`, `langgraph_interactor.py`,
  `langchain_chat_provider.py`. `adapter/inbound/api/__init__.py`의 import·
  라우터 등록도 갱신.
- 위 리네임을 반영해 `langgraph-harness.md`·`neo4j-strategy.md`·
  `langchain-elastic-strategy.md`·`langchain-ncl-strategy.md`·
  `langchain-monigstar-strategy.md`가 언급하던 옛 파일명(`rangchain_*.py`,
  `ranggraph_interactor.py`, `ranggraph-harness.md`)도 함께 정정. 제안
  파일명 `rangchain_reasoning_graph.py`는 LangGraph StateGraph 구현체라는
  맥락에 맞춰 `langgraph_reasoning_graph.py`로 수정.
- 리네임된 모듈들의 stale `__pycache__/*.pyc`(옛 모듈 경로) 삭제.
- `docker-compose.yaml`에 `neo4j` 서비스 신설: `image: neo4j:5.26-community`,
  `NEO4J_server_memory_heap_{initial,max}__size=1G`/`NEO4J_server_memory_pagecache_size=512m`로
  캡, `ports`는 `127.0.0.1:7474:7474`/`127.0.0.1:7687:7687`만(0.0.0.0 미노출),
  `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}`, `neo4j_data` named volume,
  `restart: unless-stopped`. 다른 서비스 블록은 미변경.
- `suvisdev/.env`의 `NEO4J_PASSWORD`가 이미 있었으나 값이 약한 기본값 패턴
  (`suvisdev123`)이었음 — 아직 코드 어디서도 참조하지 않아 안전하게 강한
  임의값(hex 48자)으로 교체.

### 오류·막힌 점
- 코드 리네임 관련: 없음. `ast.parse`로 리네임된 10개 파일 구문 검증, 저장소
  전체 `rangchain|ranggraph` grep으로 잔여 참조 없음 확인.
- `docker-compose.yaml` 편집 중 파일 끝에 `1` 한 글자가 단독으로 붙어 있어
  YAML이 깨져 있던 것 발견(이번 세션 이전부터 존재하던 상태, 원인 불명) —
  제거.
- `suvisdev/.env` 76번째 줄에 `TUNNEL_TOKEN suvisdev/.env | cat`이라는 실행되다
  만 셸 명령어 조각이 값 대신 들어가 있어 `.env` 파싱 자체가 실패하던 것 발견
  (역시 이전부터 존재, 바로 다음 줄에 정상 `TUNNEL_TOKEN=...` 있음) — 그
  줄만 제거.
- 이 WSL 세션에서 Docker Desktop 데몬(`npipe:////./pipe/dockerDesktopLinuxEngine`)에
  연결이 안 돼 `docker compose up -d neo4j`/`logs`/`docker ps` 실행 검증은
  못 함. `docker compose config`로 문법·서비스 등록만 확인. 사용자가 Docker가
  붙는 환경에서 직접 기동·검증하기로 함.

### 산출물
- `apps/execsuite/_docs/langgraph-strategy.md` 신규 작성.
- 코드 리네임 10건 + 관련 문서 5건 수정 — 커밋 `bff6d48` → `main` PR #16
  머지(`93ce0c3`).
- `docker-compose.yaml` neo4j 서비스 추가, `suvisdev/.env`(gitignore 대상,
  미추적) `NEO4J_PASSWORD` 교체 + 손상 라인 제거.

### 작업 내용 (이어서 — nginx/certbot 커밋)
- EC2 호스트에서 코드만 고치고 커밋 안 된 상태(`docker-compose.yaml` 수정 +
  `nginx/` 미추적)를 정리해 커밋으로 남김(사용자 요청).

### 수정/구현
- `docker-compose.yaml`(기존 EC2 로컬 수정, 내용은 불변): `nginx`/`certbot`
  서비스 추가, `backend`의 `deploy.resources`(GPU 예약) 블록 주석 처리(EC2엔
  GPU 없음), `cloudflared` command에 `--protocol http2` 추가. neo4j는 이전
  커밋(a112cb5)에서 이미 반영되어 있던 것 유지.
- `nginx/conf.d/app.conf` 신규 추적 시작 — `docker-compose.yaml`의
  `./nginx/conf.d:/etc/nginx/conf.d` 마운트가 실제로 참조하는 리버스 프록시
  설정(`api.suvisdev.cloud` → `backend:8000`).

### 오류·막힌 점
- 루트에 `docker-compose.yaml.ec2-backup`(HEAD보다 오래된 중간 스냅샷)과
  `e.yaml docker-compose.yaml.ec2-backup`(내용이 `git diff` 출력 텍스트인
  실수 파일)가 있어 사용자에게 처리 방법 확인 후 둘 다 삭제(git 미추적
  상태였으므로 히스토리엔 영향 없음).
- 루트의 `nginx.conf`(docker-compose가 참조하지 않는 초안, `proxy_pass`
  대상이 실제 서비스명과 다름)는 사용자 지시로 손대지 않고 미추적 상태 유지.
- 원래 지침(`suvisdev` 작업 → `main` 병합)과 달리 이번엔 EC2가 이미 `main`
  브랜치였고, 사용자가 이번 건은 예외적으로 `main`에 직접 커밋하기로 확인.

### 산출물
- `docker-compose.yaml`, `nginx/conf.d/app.conf` 커밋 `41d56a6`(`main`
  직접 커밋).

### 작업 내용 (이어서 — alembic 마이그레이션 적용 + backend 재배포, 로그인 500 복구)
- `git pull`로 마이그레이션 2개(`20260729_0001_add_vision_upload_soft_flags`,
  `20260729_0002_create_hub_knowledge`)가 들어왔는데 backend 컨테이너는 옛
  이미지로 떠 있어 `user_identities`/`hub_knowledge` 관련 로그인 500 발생 →
  복구(사용자 요청, 순서 지정: DB 백업 → 마이그레이션 → backend 재배포 →
  로그인 검증).

### 수정/구현
- (코드 변경 없음 — 순수 배포/운영 작업)
- DB 백업: `docker compose exec db pg_dump` → `/tmp/suvisdev_backup_20260730_0232.sql`
  (94KB, 0바이트 아님 확인).
- `docker image prune -f`(dangling만, 0B 회수 — 태그 이미지와 레이어 공유) +
  `docker builder prune -f`(빌드 캐시 9GB 회수, 둘 다 사용자 승인) →
  `/` 여유공간 5.0G→14G.
- `docker compose up -d --build backend`로 재빌드(새 마이그레이션 파일
  포함) 후 `alembic upgrade 20260729_0001`(vision_uploads 3컬럼:
  `poster_confidence`/`sharpness_score`/`is_poster_warning`) 적용,
  `alembic stamp 20260729_0002`로 버전만 기록(아래 오류 참고).

### 오류·막힌 점
- **컨테이너 이미지 stale**: `docker compose exec backend alembic heads`가
  재빌드 전엔 옛 head(`20260727_0001`)만 인식 — `docker-compose.yaml`이
  `suvisdev/` 전체를 bind mount하지 않아(코드는 build-time COPY) 새
  마이그레이션 파일이 이미지 밖에 있었음. 지시된 순서(마이그레이션 먼저 →
  재빌드 나중)로는 4번이 no-op이 됐을 것 — 사용자 확인 후 순서를
  재빌드 우선으로 변경.
- **호스트에 alembic 실행 환경 없음**: `pip` 모듈조차 시스템 python3에
  없고 프로젝트 venv도 전무 — 호스트 직접 실행(1안) 대신 컨테이너 재빌드
  경유(2안)로 전환.
- **디스크 공간 부족**: 1차 `docker compose up -d --build backend`가
  `pip install` 중 `OSError: [Errno 28] No space left on device`로 실패
  (`/` 84% 사용, 5.0G 남음, dangling 이미지 18.2GB reclaimable). `docker
  image prune -f`는 태그 이미지와 레이어를 공유해 0B 회수 — 실제로는
  `docker builder prune -f`(빌드 캐시 9GB)가 필요했음(둘 다 사용자 승인
  받고 실행).
- **hub_knowledge DuplicateTable**: `alembic upgrade head`가
  `20260729_0002`(hub_knowledge 생성)에서 `psycopg.errors.DuplicateTable`로
  실패. 트랜잭션 전체가 롤백돼 DB 손상은 없었음(`alembic_version`
  `20260727_0001` 그대로, vision_uploads 컬럼도 안 들어감). 원인은 마이그레이션
  파일 자체 docstring에 있었음 — `HubKnowledgeOrm`이 2026-07-14(cc2c334)에
  추가된 뒤 `ensure_titanic_tables()`의 `create_all()`로만 생성돼 왔고, 이
  DB엔 이미 그 경로로 테이블이 존재. 컬럼·인덱스·유니크제약까지 마이그레이션
  정의와 완전히 일치함을 확인한 뒤, `20260729_0001`만 `upgrade`로 적용하고
  `20260729_0002`는 `stamp`로 버전만 기록(SQL 미실행)하는 우회로 해결(사용자
  승인).
- **백로그**: `create_all()`(`ensure_titanic_tables`)과 alembic이 테이블
  생성을 이중 관리하고 있어 새 테이블이 추가될 때마다 이번과 같은 stamp
  충돌이 반복될 수 있다. 근본 해결은 `create_all()` 경로를 제거하고 alembic을
  테이블 생성의 단일 소스로 삼는 것 — 오늘은 `20260729_0002` stamp로
  우회했을 뿐 근본 원인은 그대로 남아 있음.

### 산출물
- 커밋 없음(순수 배포). DB `alembic_version`: `20260727_0001` →
  `20260729_0002`. backend 이미지 재빌드·재기동. 백업 파일:
  `/tmp/suvisdev_backup_20260730_0232.sql`.

### 작업 내용 (이어서 — 어드민 화면 미노출 수정 + 닉네임 표시/변경 기능)
- 사용자가 `ssuvisdev@gmail.com`으로 로그인해도 어드민 화면이 안 보인다고
  보고 → 원인 조사 후 수정.
- 메인페이지 로그인 표시가 이메일(정확히는 OAuth로 자동 생성된
  `{이메일 로컬파트}_{provider}` 형태의 `username`)로 보여서, OAuth 로그인도
  닉네임을 설정할 수 있고 헤더에 닉네임이 뜨도록 개선(사용자 요청).

### 수정/구현
- **어드민 미노출 원인**: `_resolve_role()`(RBAC)이 `ADMIN_EMAILS` env를
  기준으로 role을 산출하는데, `suvisdev/.env`에 이 항목 자체가 누락돼 있어
  누가 로그인해도 role이 항상 `user`였음. `.env`에
  `ADMIN_EMAILS=ssuvisdev@gmail.com` 추가 후 `docker compose up -d
  --force-recreate backend`로 재기동(이미지 재빌드 불필요, env만 반영).
- **닉네임 표시/변경**: 로그인 응답 체인
  (`LoginResponseDto → SessionPayloadDto → JWT 세션 핸드오프 → 프론트 응답`)
  전체에 `nickname` 필드를 추가해 로그인 시 프론트 세션(localStorage)에
  닉네임이 실리도록 함. 변경 파일: `auth_command_dto.py`,
  `login_pg_repository.py`, `oauth_identity_pg_repository.py`,
  `oauth_dto.py`, `session_store_port.py`,
  `redis_session_store_adapter.py`(handoff 문자열에 nickname 필드 추가),
  `oauth_login_interactor.py`, `oauth_router.py`, `login_router.py`.
  - 신규 `PATCH /viewer/profile/{user_id}`(닉네임 변경) — 본인 확인 가드
    `shared/security/require_user.py`(신규, `require_admin.py`와 동일한
    HS256 검증이되 role 체크 없음) + 요청자 user_id와 경로 user_id 일치
    검증(`.claude/rules/security/auth.md` §5 IDOR 규칙 준수). 포트/유스케이스/
    리포지토리(`profile_repository.py`, `profile_use_case.py`,
    `profile_interactor.py`, `profile_pg_repository.py`,
    `user_orm.py::update_user_nickname`) 계층 전부 관통.
  - 프론트: 헤더(`auth-login-button.tsx`)가 `username` 대신 `nickname`
    표시(`?? username` 폴백). 마이페이지에 닉네임 인라인 편집 UI 추가
    (`profile-api.ts::updateNickname`, `app/api/viewer/profile/route.ts`에
    `PATCH` 프록시 추가, 저장 성공 시 로컬 세션도 즉시 갱신해 재로그인 없이
    헤더 반영). `SuvisSession`/`OAuthSessionResult` 타입에 `nickname` 추가.

### 오류·막힌 점
- 없음. `apps/viewer`에 기존 테스트가 없어(pytest testpaths 미포함) 자동
  회귀 테스트는 못 돌렸고, 대신 backend 컨테이너 안에서 실제 계정
  (`user_id=1`, `ssuvisdev@gmail.com`, 기존 닉네임 "진수택")으로 수동
  검증: `RedisSessionStoreAdapter.issue_session→redeem_handoff_code`
  체인에 nickname/role 정상 전달, `PATCH /viewer/profile/1`을
  토큰 없이(401)·남의 id로(403)·본인 id로 동일 닉네임값(200, 멱등) 호출해
  가드·소유권 검증 확인, `GET`으로 값 보존 재확인(실데이터 훼손 없음),
  `POST /viewer/login/login`(admin 시드 계정) 응답에도 nickname 포함 확인.
  프론트는 이 EC2에 `pnpm`/`node_modules`가 없어 `pnpm type-check` 실행
  불가 — 타입은 수동 검토만 함.

### 산출물
- 코드 변경 파일: 백엔드 16개 + 신규 1개(`shared/security/require_user.py`),
  프론트 7개. `suvisdev/.env`에 `ADMIN_EMAILS` 추가(gitignore 대상, 커밋
  안 됨). backend 재빌드·재기동 완료.

### 작업 내용 (이어서 — Neo4j GraphRAG 스키마(제약+벡터 인덱스) 생성)
- 2026-07-30 앞부분에서 provisioning만 하고 실기동 검증이 미완이던 neo4j
  컨테이너에, pg `movies` 스키마 기준 도메인 제약·인덱스를 실제로 생성
  (사용자 요청, 데이터는 아직 안 넣음 — TMDB/KOFIC import가 나중에 채울 예정).

### 수정/구현
- `docker compose exec neo4j cypher-shell`로 실행: 유니크 제약 4개
  (`movie_slug`→Movie.slug, `genre_name`→Genre.name, `person_slug`→Person.slug,
  `collection_id`→Collection.ext_id, 각각 자동 RANGE 인덱스 동반), 검색용
  `movie_title`(Movie.title, RANGE), 벡터 인덱스 `movie_embedding`
  (Movie.embedding, 768차원, cosine — pg embedding 컬럼과 동일 스펙).

### 오류·막힌 점
- `suvisdev/.env` 소스 시 29번째 줄에 예전(76번째 줄, 2026-07-29 수정분)과
  같은 종류의 손상(단독 `1` 문자, `GEMINI_API_KEY` 바로 다음 줄)이 있어
  `source` 경고가 났음 — `NEO4J_PASSWORD`는 정상 로드돼 이번 작업엔 지장
  없었고, 이번 작업 범위 밖이라 손대지 않음(백로그).

### 산출물
- `SHOW CONSTRAINTS`/`SHOW INDEXES`로 4개 제약 + 6개 인덱스(벡터 포함)
  전부 `state=ONLINE` 확인, `MATCH (n) RETURN count(n)` = 0 확인(데이터
  없음, 그릇만 존재).

### 작업 내용 (이어서 — ADMIN_EMAILS 추가 + mova TMDB credits 백필 조사·설계·구현)
- 로컬 `suvisdev/.env`에 `ADMIN_EMAILS` 항목 자체가 없어(어드민 role 판정이
  전부 "user"로만 나오는 상태) `ADMIN_EMAILS=ssuvisdev@gmail.com` 추가(사용자
  요청). `.env`는 gitignore 대상이라 로컬 전용 — EC2 `.env`는 별도로 채워야
  함을 안내.
- mova의 TMDB/KOFIC import 경로 코드 조사(사용자 요청, 코드 수정 없이 조사만):
  actors/characters 테이블이 스키마·ORM·읽기 API는 있지만 **쓰기 경로가
  0건**이라 pg `actors` 0행인 것을 확인. TMDB credits(cast/crew) 조회도
  `fetch_movie_detail()`(단일 상세)에만 있고 시드가 쓰는 `fetch_popular`
  등에는 없어 cast가 늘 빈 값. `movies.embedding` 컬럼도 스키마 주석은
  Gemini를 가리키지만 실제로는 아무 코드도 안 채움 — 임베딩은 별도로
  `_ingest_to_hub()`가 ontology `hub_knowledge` 테이블에만 씀. 결과를 표로
  보고(구현됨/정의만 되고 안 도는 것/없는 것 3단 구분).
- 위 조사를 바탕으로 "TMDB credits 배선" 2단계 작업 Phase A(조사·설계, 코드
  변경 금지) 진행: actors/characters 스키마 전체, Port·DTO 현재 인터페이스,
  `.importlinter` 레이어 제약, TMDB credits 응답 필드, 설계안 검토, 변경
  파일 목록, TDD 테스트 목록을 보고. 사용자가 세 가지 결정 확정: ① 마이그레이션
  4건 진행(`actors.tmdb_person_id`, `characters.billing_order`,
  `movie_directors` 조인 테이블, `uq_actors_name_role` DROP — 사용자가 이
  네 번째 항목을 직접 지적함, 안 빼면 동명이인 upsert가 기존 제약에 막혀
  실패), ② 감독 관계는 movie_directors 조인 테이블(공동 감독 지원, characters와
  대칭), ③ 실행은 수동 스크립트 전용(어드민 엔드포인트·스케줄러 배선 금지).
- Phase B로 TDD 구현 진행(사용자 승인, "커밋은 하되 push는 확인 후" 조건).

### 수정/구현
- `alembic/versions/20260730_0001_add_tmdb_credits_columns.py` 신규
  (`down_revision=20260729_0002`, 현재 head): `actors.tmdb_person_id`
  INTEGER UNIQUE NULL 추가 + 인덱스, `characters.billing_order` INTEGER
  NULL 추가, `movie_directors(movie_id, actor_id)` 테이블 신설(FK CASCADE,
  UNIQUE), `uq_actors_name_role` DROP(+downgrade에서 복원).
- ORM: `studio_actors_orm.py`(`tmdb_person_id` 컬럼, UNIQUE 제약을
  name+role_type에서 tmdb_person_id로 교체), `studio_characters_orm.py`
  (`billing_order` 컬럼), 신규 `studio_movie_directors_orm.py`
  (`MovaMovieDirector`, characters와 대칭 구조) — `adapter/outbound/orm/__init__.py`에
  등록해 `core.matrix.grid_oracle_database_manager`의 `import
  mova.adapter.outbound.orm`으로 메타데이터에 잡히게 함.
- DTO: `studio_import_dto.py`에 `TmdbCastMemberDto`/`TmdbDirectorDto`/
  `TmdbCreditsDto`/`CreditsBackfillResultDto`(succeeded/failed/skipped +
  실패 slug 목록, `_ingest_to_hub`처럼 조용히 삼키지 않음), `studio_actors_dto.py`에
  `ActorUpsertCommand`, `studio_characters_dto.py`에 `CharacterUpsertCommand`,
  신규 `studio_movie_directors_dto.py`에 `MovieDirectorUpsertCommand`.
- 매퍼: `tmdb_mapper.py`에 `map_credits()` 신규(person id/character/order/
  crew 보존, 기존 `map_cast_names`(hub_rag용, 이름만)는 불변). `tmdb_adapter.py`의
  `poster_url()` 내부 로직을 모듈 함수 `build_image_url()`로 추출해
  profile_path에도 재사용(동작 동일, 순수 리팩터).
- Port 확장: `ActorsRepositoryPort.upsert_actor`, `CharactersRepositoryPort.upsert_character`,
  신규 `MovieDirectorsRepositoryPort.upsert_director`, `MoviesRepositoryPort.list_all_slugs`
  (배치 순회 전용, 기존 필터·페이지네이션용 `list_movies`와 분리),
  `TmdbCatalogPort.fetch_credits`(기존 `fetch_by_id`는 불변 — seed/import
  경로 안 건드림).
- PgRepository 구현: `ActorsPgRepository.upsert_actor`(tmdb_person_id
  기준 select-then-insert/update, 기존 `upsert_movie` 패턴과 동일),
  `CharactersPgRepository.upsert_character`, 신규
  `MovieDirectorsPgRepository`(movie_id+actor_id 기준, 필드가 없어 이미
  있으면 그대로 반환하는 순수 멱등 insert), `MoviesPgRepository.list_all_slugs`,
  `TmdbCatalogAdapter.fetch_credits`(`fetch_movie_detail` 재사용 + `map_credits`).
- 유스케이스: 신규 `credits_backfill_use_case.py`(입력 포트) +
  `credits_backfill_interactor.py` — `list_all_slugs()` 순회, `slug`가
  `tmdb-{id}` 형식이 아니면 skipped 집계 후 계속(이 파싱 전제를 코드 주석에
  명시), 영화 1편의 credits 조회·upsert가 실패해도 예외를 잡아 failed 집계
  후 다음 영화로 진행(전체 중단 안 함).
- DI: 신규 `dependencies/credits_backfill_provider.py` — FastAPI 요청
  컨텍스트 없이 `get_mova_session_factory()`로 직접 세션을 여는
  `seed_catalog_if_sparse`와 동일 패턴(어드민 엔드포인트 없음).
- 실행 진입점: 신규 `scripts/backfill_credits_cli.py` — 기존
  `scripts/harvester_cli.py`와 동일하게 `sys.path` 수동 부트스트랩 후 직접
  실행(`docker compose exec backend python scripts/backfill_credits_cli.py`).
  사용자가 예시로 든 `python -m ...`은 이 저장소에 PYTHONPATH 설정이 없어
  그대로는 안 돼 기존 컨벤션에 맞춰 조정했음을 보고에 명시.
- 테스트: 신규 `apps/mova/tests/test_credits_backfill.py` 14건 —
  `map_credits`(credits 없음/cast만/crew job 필터/공동 감독 2명/cast person
  id 중복 제거/cast_limit/profile_path→URL), `_parse_tmdb_id`(정상/비-TMDB
  slug/파싱 실패), `CreditsBackfillInteractor`(AsyncMock 포트 — 비-TMDB
  slug skip, cast+감독 upsert 오케스트레이션, 한 편 실패해도 나머지 진행,
  전부 실패 시 집계).

### 오류·막힌 점
- repository upsert의 실제 멱등성·동명이인 분리(같은 tmdb_person_id 재upsert
  시 행 1개 유지, 다른 tmdb_person_id+같은 이름은 별도 행)는 Postgres 없이는
  검증 불가 — 로컬 Docker 데몬 미연결이라 마이그레이션 적용·backfill 실행·
  이 검증은 EC2에서 사용자가 직접 진행하기로 함(사전 합의).
- `apps/mova/tests/` 전체 47개 + 신규 14개 = 61개 전부 통과, `import-linter`
  결과 "Spokes must not import each other directly"·"Mova domain must not
  import app or adapter" 둘 다 KEPT(이번 변경으로 깨진 계약 없음). 남은
  broken contract 1건(Hub-independence, ontology→core.matrix→spoke 전이
  경로)은 이번 세션 파일과 무관한 기존 이슈.

### 산출물
- 마이그레이션 1건 + ORM 3개 파일 + DTO 4개 파일 + Port 5개(4개 확장,
  1개 신규) + PgRepository 4개 파일 + 유스케이스 2개 파일(신규) + DI
  프로바이더 1개(신규) + CLI 스크립트 1개(신규) + 테스트 1개 파일(14건) —
  총 16개 수정 + 10개 신규, 로컬 커밋만 하고 push는 보류(사용자 확인 후).
  마이그레이션 실제 적용(`alembic upgrade head`)과 backfill 실행은 EC2에서
  사용자가 별도 진행.

---

## 2026-07-29

### 작업 내용
- `origin/main`의 lora-server 베이스 모델 폴백 커밋(4703232)을 `suvisdev`
  브랜치로 cherry-pick.
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 백로그 중 "06 Sentinel 소프트
  플래그 저장 지속화 + 어드민 오버라이드 엔드포인트" 착수(사용자 선택).
  사전 조사 결과 저장 계층이 S3(자격증명 미연결로 사실상 미동작)/DB
  (`VisionRepository`, 실제 구현이나 DI 미배선) 둘로 쪼개져 있던 것을 확인,
  DB로 일원화하기로 결정(S3는 `.env`에 AWS 키가 전혀 없어 당장 못 씀).
- 같은 백로그의 "CLIP 모델 다운로드 hang" 착수 — 재현·원인 규명 후 최소 수정.
- `.claude/rules/` 경로별 코딩 규칙 4종 신규 작성 + 루트 `CLAUDE.md` 보강
  (하네스 설정·명령어·환경변수·브랜치·테스트 섹션이 아예 없던 것을 추가).
- `.claude/projects/memory/` 팀 공유용 주제별 메모 신설.
- 메인 페이지 우측 히어로 자리를 정지 이미지에서 영상으로 교체 요청.
- 전역 `Suvisdev AI` 채팅 버블을 LESSON `/langchain/chat`과 같은 백엔드
  설정으로 전환 요청.
- 완전히 빈 DB에서 `alembic upgrade head`가 성공하는지 실제 검증(사용자
  요청) — 이 날 앞선 세션이 "로컬 Postgres 미기동"으로 미뤄뒀던 검증을
  도커 임시 컨테이너로 이어서 수행하고, 검증 중 발견된 누락 마이그레이션 보완.

### 수정/구현
- **DB 스키마**: `alembic/versions/20260729_0001_add_vision_upload_soft_flags.py`
  신규 — `vision_uploads`에 `poster_confidence`/`sharpness_score`/
  `is_poster_warning` 컬럼 추가(`down_revision=20260727_0001`, 단일 head 체인
  유지). `VisionUploadOrm`에 동일 컬럼 추가.
- **DTO/포트**: `vision_dto.py`에 `VisionImageCommand`·`VisionUploadResponse`
  플래그 필드 + `upload_id`, 신규 `VisionPosterFlagOverrideDto` 추가.
  `VisionPort`/`VisionUseCase`에 `update_poster_flag`/`override_poster_flag`
  추상 메서드 신설.
- **리포지토리**: `VisionRepository.save_image`가 플래그를 실제 persist,
  신규 `update_poster_flag`(select→갱신→commit, id 없으면 `updated=False`)
  구현. `VisionS3Repository`는 인터페이스 계약만 맞추도록
  `update_poster_flag`에서 `NotImplementedError`(메타데이터 row가 없어 오버라이드
  불가) — 나머지 S3 코드는 손 안 댐.
- **DI 전환**: `vision_provider.py`의 `get_vision_repository`를
  `VisionS3Repository` → `VisionRepository`(DB)로 교체.
- **어드민 엔드포인트**: `PATCH /vision/{upload_id}/poster-flag` 신설
  (`vision_router.py` + 신규 `vision_schema.py`), `require_admin` 가드 적용
  (mova `market_picks_router.py`의 PATCH 패턴을 그대로 따름).
- **테스트**: `test_vision_upload_sentinel_gate.py` — 새 추상 메서드로 깨질
  뻔한 `_FakeVisionRepository`에 `update_poster_flag` 구현 추가, GPU 불필요한
  `override_poster_flag` 위임 테스트 1개 신설.
- **CLIP hang 수정**: `apps/ontology/test/conftest.py` 신규 — `HF_HUB_OFFLINE`·
  `TRANSFORMERS_OFFLINE`을 세션 시작 시 설정해 GPU 테스트가 네트워크를 타지 않고
  로컬 캐시만 쓰게 강제. Sentinel 판별 로직·임계값은 건드리지 않음.
- **`.claude/rules/`**: `typescript.md`(strict·any 금지·type 별칭·enum 금지·
  단언 경계 — `suvis/` 실측: type 167 : interface 4, any 0, enum 0, React.FC 0),
  `api-standards.md`(제네릭 fetch 래퍼·Bearer 3계층·`safeApiErrorMessage`·
  라우트 핸들러 상태코드), `testing.md`(마커·conftest 격리·포트 fake),
  `security/pci.md`(결제 코드가 생길 때 발동하는 게이트로 작성),
  `security/auth.md`(`require_admin` 단일 가드·role은 서버 산출 JWT claim만 신뢰·
  토큰 3계층 전달·무인증 지점은 근거 주석·IDOR·엔드포인트 체크리스트 5항목.
  이 저장소에서 무인증 취약점이 실제로 두 번 나온 영역이라 규칙으로 굳힘).
- **루트 `CLAUDE.md`**: 기존 내용 수정 없이 섹션 추가 — 명령어(3스택별)·테스트·
  환경 변수·브랜치 전략·주의사항·하네스 설정(`.claude/` 구조, 메모리 두 곳의
  차이, 훅 동작).
- **`.claude/projects/-home-a-projects-suvis/memory/`**: `MEMORY.md`(인덱스)·
  `debugging.md`(lint-imports baseline red, CLIP hang, DB 미기동, 기존 실패
  테스트)·`patterns.md`(백엔드 계층·어드민 엔드포인트·마이그레이션·테스트 패턴).
  처음엔 `projects/memory/`로 만들었다가, 하네스 관례인 `<프로젝트 경로>` 인코딩
  (`-home-a-projects-suvis`, 절대경로의 `/`→`-`)을 넣어 `git mv`로 이동(이력 보존).
  단, **홈(`~/.claude/...`)이 아니라 저장소 안이라 자동 로드되지 않는다** — 두
  경로가 `~/` 유무만 달라 혼동 위험이 커서 양쪽 문서에 구분을 명시했다.
- **`memory/auto-memory.md` 신규**: 자동 메모리 동작 방식(`MEMORY.md` 첫 200줄만
  세션 시작 시 로드, 초과분·주제 파일은 필요할 때만, 200줄 제한은 `MEMORY.md`
  전용, `CLAUDE.md`는 길이 무관 전체 로드) + 활성화/비활성화 방법
  (`CLAUDE_CODE_DISABLE_AUTO_MEMORY`, `autoMemoryEnabled`, `/memory` 토글).
  기존 문서와 겹치는 "두 위치 차이"는 링크로만 처리.
- **`.mcp.json` 정리 + 내부 MCP 서버 2종 등록·검증**: 예시로 있던 `postgres`·
  `notion`을 지우고 `github` 유지 + `gmail` 추가. gmail은 공식 서버가 없어
  (`@modelcontextprotocol/server-gmail` 부재를 npm으로 확인) 사용자 선택으로
  `@gongrzhe/server-gmail-autoauth-mcp` 채택. 저장소 내부 FastMCP 서버 중
  `suvis-vision-sentinel`·`suvis-vision-genre`를 상대경로 + `PYTHONPATH=
  suvisdev:suvisdev/apps`로 등록(팀 공유 고려해 절대경로 회피).
  `.claude.json`은 0바이트 로컬 상태 파일이라 등록 위치로 쓰지 않고 `.gitignore`에 추가.
- **`${VAR:-default}` 문법 지원 여부 실측 확정**: `claude mcp list` A/B 대조로
  판정 — `${SUVIS_PYTHON:-python}`일 때는 변수 미설정에도 경고가 없고,
  `${SUVIS_PYTHON}`으로 바꾸면 "Missing environment variables: SUVIS_PYTHON"
  경고가 뜬다(기본값 없는 `${GITHUB_TOKEN}`과 동일 거동). 즉 **`:-` 문법은
  지원된다.** 그럼에도 **기본값을 제거**했는데, 이 머신엔 `python`이 없고
  (`/usr/bin/python3`뿐, 그마저 `mcp` 미설치) 기본값이 있으면 검증을 통과한 뒤
  기동 단계에서 조용히 실패하기 때문이다. 기본값을 빼면 Claude Code가 명확한
  누락 경고를 준다.
- **`/code-review` 실행 결과 검증 후 사고 2건 되돌림** — 서브에이전트 리뷰가
  세션 밖에서 생긴 작업트리 변경(마지막 커밋 이후, 내가 만든 게 아님)을
  잡아냄: (1) `suvis/.env.production`(공개 API URL 한 줄, 비밀 아님) 삭제가
  스테이징돼 있었는데 이 값을 공급하는 다른 경로가 전혀 없어 그대로 배포하면
  프로덕션 로그인·OAuth·관리자·비전 요청이 방문자 로컬호스트로 조용히
  나갈 뻔함 — 사용자 확인 후 스테이징 해제+원복. (2) `.gitignore`에
  `.mcp.json`을 추가했는데 이미 git이 추적 중인 파일이라 효과가 없고
  바로 위 주석과도 모순 — 그 줄과 중복된 `.claude.json` 줄 제거.
  `.mcp.json`의 `github` 서버 삭제는 사용자 확인 후 그대로 유지.
- **`.claude/agents`·`scripts`·`skills/deploy` 검토 — 채우지 않고 삭제 결정**:
  `/code-review` 실행 중 로컬에 새로 생긴 4개 파일이 이 저장소 것이 아니라
  Claude Code 공식 문서 예시 템플릿임을 확인(설명 주석 스타일, 존재하지 않는
  스킬 참조, 빈 본문). 어디에도 연결 안 돼 비활성 상태였음. 처음엔 실제로
  채워 넣는 방향으로 시작했으나(`protect-files.sh`를 이 저장소 `.env*` 현황에
  맞게 재작성 중 `jq` 미설치 버그까지 발견), 사용자가 방향 전환 — "프로덕션
  배포" 스킬과 auto-invoke 가능한 에이전트를 지금 활성화하는 게 오히려 위험
  하다는 판단으로 `skills/deploy/SKILL.md`·`agents/code-reviewer.md`(기존
  `/code-review`와 중복)·`agents/data-analyzer.md`(존재하지 않는 스킬 참조로
  호출 시 깨짐) 3개 삭제. `scripts/protect-files.sh`는 원본 템플릿 상태로
  되돌리고 등록하지 않은 채 보류(추후 별도 작업으로 제대로 엮기로 함).
- **공개 개발로그 `/devlog` 신설**: 내부 작업 일지를 도메인 메인 사이트에
  공개용으로 옮김. **자동 변환하지 않고** WORK_LOG 전체(1252줄·15개 작업)를
  읽어 "공개 가능 / 추상화 / 완전 제외" 3분류한 뒤, 공개 안전 항목만 골라
  12개로 다시 썼다. 각 항목은 "제목 + 설계 의도 한 줄"이며 파일 경로·클래스명·
  수치·인프라 세부는 넣지 않았다. `lib/devlog.ts`(`apps-catalog.ts` 패턴의
  타입 있는 데이터 파일, `highlighted` 필드로 강조 제어) + `app/devlog/page.tsx`
  (서버 컴포넌트) + `components/header.tsx`(Devlog 링크). 메인 페이지
  레이아웃은 건드리지 않았다.
- **루트 `CLAUDE.md`에 커밋 메시지 규칙 추가**: Conventional Commits·제목 50자
  이내·한국어. 실측 대조 결과 최근 14건 중 11건이 50자를 넘지만(중앙값 60자대),
  사용자 결정으로 **소급 없이 앞으로 지킬 목표**로 둔다.
- **메인 페이지 우측 히어로를 정지 이미지 → 영상으로 교체**: 사용자가 준
  mp4(H.264, 1280×720, 8초, ~2MB)를 `suvis/public/hero-holographic-mask.mp4`로
  파일명 정리해 추가(원본 경로에 특수문자 포함, URL 문제 방지). `hero-image-panel.tsx`의
  `next/image` `<Image>`를 `<video autoPlay loop muted playsInline>`로 교체,
  기존 정지 이미지는 `poster`(로딩 중 표시)로 재활용. 실제 dev 서버 + 헤드리스
  브라우저로 데스크톱(1440px)·모바일(390px) 두 폭 모두에서 `paused: false`·
  `currentTime` 증가까지 확인해 재생 중임을 실측 검증(정적 스크린샷만으로는
  autoplay 성공 여부를 알 수 없어서).
- **전역 `Suvisdev AI` 채팅 버블을 LESSON `/langchain/chat`과 같은 백엔드로
  전환**: 기존엔 `/api/chat`(Next 로컬 라우트, Gemini SDK 직접 호출 +
  모델 선택 드롭다운)을 썼는데, `/api/v1/langchain/chat`(semantic_router가
  의도 판단 → LangChain 체인이 답변, 레슨 페이지와 완전히 동일한 백엔드)으로
  교체. 요청 형식도 `{message, model}` → `{messages: [...]}`(대화 이력 전체,
  레슨 페이지와 동일)로 변경. 모델 선택 드롭다운은 제거 — 백엔드 스키마에
  `model` 필드가 있지만 라우터가 실제로 안 씀(`use_case.chat()`에 미전달)을
  코드로 확인, 남겨두면 선택이 무시되는데도 되는 것처럼 보여 오해를 만듦.
  백엔드 직접 `curl` 확인 + 헤드리스 브라우저로 버블 열기→입력→전송→응답
  전 과정 재현, 네트워크 로그로 실제 호출 엔드포인트·페이로드까지 확인.
- **버그 발견·수정(범위 밖, 검증 중 발견)**: 전송 흐름을 실제로 클릭 테스트하다
  `pageerror: Cannot read properties of null (reading 'reset')` 발생 —
  `handleSubmit`이 `await sendMessage(...)` **이후**에 `e.currentTarget.reset()`을
  호출하는데, React `SyntheticEvent.currentTarget`은 동기 디스패치가 끝나면
  null이 되는 구조적 함정. `git diff`로 이 코드가 이번 변경 이전부터 있던
  것임을 확인(이번에 처음 실제 인터랙션 테스트를 돌리며 드러남). `await` 전에
  폼 참조를 변수로 미리 잡아두는 방식으로 수정, 재검증 결과 에러 사라짐.
- **메인 페이지 헤더-콘텐츠 간격 조정**: 헤더 알약(pill)과 카드 모서리가
  거의 맞닿아 답답해 보인다는 사용자 지적으로 `app/page.tsx`의 `pt-0`을
  `pt-3 md:pt-4`(12~16px)로 변경. 뷰포트 높이 계산식(`min-h-[calc(...)]`,
  outer/inner 둘 다)도 늘린 padding만큼 같이 줄여 불필요한 스크롤이 새로
  생기지 않게 맞춤. 짧은 화면(700px)·모바일에서 스크롤이 생기긴 하는데,
  원본 코드로 되돌려 대조한 결과 **이 스크롤은 원래도 있던 것**임을 확인
  (콘텐츠 자체가 이미 뷰포트보다 김) — 이번 변경은 정확히 padding만큼만
  늘렸을 뿐 새로 만든 문제가 아님.
- **다크 모드에서 로그인 카드 입력창이 검게 변하는 버그 수정**: 로그인 모달
  (`auth-dialog.tsx`)은 다크 모드에서도 항상 흰 배경으로 고정되도록 만들어져
  있는데, `Input`·`Tabs` shadcn 베이스 컴포넌트가 `dark:bg-input/30` 등을 갖고
  있어(색상 변수 `--input: oklch(0.22 0.01 260)`, 거의 검정) `.dark` 스코프에서
  `bg-white`보다 CSS 명시도가 높아 이겨버리는 게 원인 — `bg-white`(무조건 적용)와
  `dark:bg-input/30`(다크 전용)은 Tailwind `twMerge`가 서로 다른 modifier로 보고
  충돌 처리를 안 해서 둘 다 남는데, `.dark .dark\:bg-input\/30` compound selector가
  더 구체적이라 이긴다. `app/login/auth-forms.tsx`의 `inputClass`(입력창·셀렉트)·
  `tabTriggerClass`(로그인/회원가입 탭)에 `dark:...!`(Tailwind v4 important 문법)를
  추가해 라이트 스타일을 명시적으로 강제 — `components/ui/input.tsx` 같은 공용
  베이스는 사이트 전역 다크 모드가 정상 동작해야 해서 건드리지 않음. 실제로
  다크 모드를 켜고 모달을 열어 계산된 스타일(`background-color: rgb(255,255,255)`)
  까지 확인해 검증. mova 쪽은 `mova-login-button.tsx` 주석으로 이미 예전에
  자체 다크 테마(`--mova-*` CSS 변수, shadcn Input 미사용)로 교체돼 이 버그의
  영향을 받지 않음을 확인 — 별도 수정 없음.
- **위 버그 수정 배포 확인 중 mova 다크모드 구조 재발견 + 방향 전환**: 배포
  사이트에서 여전히 회색으로 보인다는 사용자 피드백에 git 상태(`main`이
  최신 커밋을 포함하는지, 머지 누락 없는지)를 재확인했으나 이상 없었음 —
  실제 원인은 Vercel 캐시/배포 지연으로 추정된 상태였으나, 사용자가 문제를
  이 시점에서 근본적으로 우회하기로 결정: **"메인 사이트는 다크모드 자체를
  없애고 mova만 유지"**. 조사 중 `mova-theme-setter.tsx`를 확인해 기존에
  가졌던 이해("mova는 독립된 always-dark 테마")가 틀렸음을 확인 — 실제로는
  `MovaThemeSetter`가 `/mova` 진입 시 전역 next-themes 상태를 `setTheme("dark")`로
  강제하고 나갈 때 이전 값으로 복원하는 구조였고, mova 자체 헤더에도 별도
  `ThemeToggle`이 있어 mova 안에서 라이트("Warm Cinema")로 전환 가능함
  (`mova.css`의 `html:not(.dark) .mova-app`). 즉 메인 사이트와 mova가 같은
  전역 토글 상태를 공유하고 있었던 것.
- **다크 모드를 mova 전용으로 한정**: `components/header.tsx`에서
  `<ThemeToggle />` 제거(메인 사이트에서 다크 진입 경로 원천 차단).
  `components/site-chrome.tsx`에 `useEffect`로 `pathname`이 `/mova`가
  아니면 매번 `setTheme("light")`를 강제하는 로직 추가 — 토글 UI를 없애는
  것만으로는 next-themes가 localStorage에 저장해 둔 예전 `dark` 값이 계속
  복원되는 문제(이번 세션 내내 다크로 테스트해 온 사용자가 실제로 이 상태였음)
  까지는 못 막아서 필요했음. `admin`도 같은 조건으로 라이트 고정(별도
  다크 스타일이 없어 원래도 영향 없었지만 범위를 명확히 함).
  **검증**: 헤드리스 브라우저로 (1) `localStorage.theme="dark"`를 미리 심어
  기존 다크 사용자 상태를 재현한 뒤 홈 진입 → `html.dark` 없음·헤더에 토글
  흔적 없음·로그인 입력창 `rgb(255,255,255)` 확인, (2) `/mova` 진입 → `html.dark`
  있음(시네마 테마 그대로) 확인, (3) mova→홈 복귀 → 다시 라이트로 강제되는
  것까지 3단계 전부 스크린샷과 함께 확인.
- **DB 스키마**: `alembic/versions/20260729_0002_create_hub_knowledge.py`
  신규 — `HubKnowledgeOrm`(2026-07-14, cc2c334에서 추가)이 마이그레이션 체인에
  한 번도 CREATE된 적 없이 `ensure_titanic_tables()`의 `create_all()`로만
  존재해 온 것을 확인하고 보완(`down_revision=20260729_0001`, pgvector
  `CREATE EXTENSION IF NOT EXISTS vector` 포함). 이 리비전 이후 alembic
  체인만으로 앱이 실제로 쓰는 모든 테이블(contents/gildle/mova/titanic/
  dispatch/ontology/execsuite/viewer 전 앱)이 생성됨을 확인.
- **`main.py`의 `create_tables()`(→`ensure_titanic_tables()`) 재확인**: 이미
  이전 세션(a42e667)에서 mova/viewer 테이블은 "Alembic이 전담, create_all
  우회 생성 금지"로 정리돼 있었음. 남은 건 `grid_neo_theone_base.Base`
  소유 테이블(titanic/dispatch_adress/vision_uploads/hub_knowledge) —
  주석상 "삭제 후 업로드 복구용" 의도적 fallback이고 `create_all`은
  `checkfirst=True`라 이미 있는 테이블은 건드리지 않아 충돌은 아님. 다만
  `ensure_titanic_tables()`가 `dispatch.receive_orm`(dispatch_inbox)·
  `execsuite.pdf_loader_orm`은 import하지 않아 그 두 테이블은 create_all
  대상이 아님 — 지금은 두 테이블 다 알렘빅 마이그레이션이 있어 문제 없지만,
  "복구용" 의도라면 어떤 테이블까지가 대상인지 import 목록과 주석이
  불일치함. 코드 변경은 하지 않고 다음 정리로 제안만 남김: (1) 복구
  대상을 정말 titanic 전용으로 좁히려면 hub_knowledge/vision_uploads/
  dispatch_adress import를 이 함수에서 빼거나, (2) 지금처럼 유지한다면
  주석을 "NeoTheOneBase 전체 복구용"으로 정정해 목록과 의도를 맞출 것.

### 오류·막힌 점
- **로컬 Postgres 미기동(세션 초반)** — DB 프로세스가 안 떠 있어
  `alembic upgrade head`로 신규 마이그레이션을 실제 DB에 적용해보는 검증은
  당장 못 함(문법·체인 유효성만 `alembic history`로 확인). → 아래 "완전히
  빈 DB 검증 성공"에서 도커 임시 컨테이너로 이어서 검증.
- **리비전 ID 충돌** — `hub_knowledge` 마이그레이션을 처음엔
  `20260729_0001`로 만들었는데, 같은 시점에 `git pull`로 받아온
  `20260729_0001_add_vision_upload_soft_flags.py`와 리비전 ID·
  `down_revision`이 완전히 겹침(두 세션이 같은 날짜로 각자 새 리비전을
  만든 것). `20260729_0002`로 재번호 + `down_revision`을
  `20260729_0001`로 체인해 단일 head 유지.
- **검증 중 실수로 실제 로컬 dev DB에 접속**(중요, 재발 방지용 기록) —
  임시 도커 컨테이너(포트 55432)를 만들어 `DATABASE_URL`만 그 컨테이너로
  export했는데, `alembic/env.py`의 `_database_url()`이
  `MOVA_DATABASE_URL`을 `DATABASE_URL`보다 먼저 확인하고, `suvisdev/.env`가
  이미 `MOVA_DATABASE_URL=localhost:5432`(docker-compose `suvisdev-db-1`,
  실제 로컬 개발 DB)를 정의하고 있어 그쪽으로 연결됨. 그 DB는 실제
  백엔드가 상시 기동 중이라(`suvisdev-backend-1`) `create_all()`로 이미
  `titanic_passengers`/`dispatch_adress`/`vision_uploads`/`hub_knowledge`가
  떠 있는 상태였고, 알렘빅은 한 번도 안 돈 상태(alembic_version 없음) —
  결과적으로 사용자가 신고한 버그의 실물 사례를 우연히 재현(`20260604_0000`이
  이미 있는 `titanic_passengers`를 CREATE하려다 `DuplicateTable`). 각
  마이그레이션은 트랜잭션으로 묶여 있어 실패 시 롤백 확인(`\dt`로 실 DB에
  변경 없음 확인) — 실제 데이터 손상 없음. 원인 규명 후 `DATABASE_URL`·
  `MOVA_DATABASE_URL` 둘 다 임시 컨테이너로 export하도록 고쳐서 재검증.
- **완전히 빈 DB 검증 성공** — 위 실수를 바로잡은 뒤 순수 도커
  `pgvector/pgvector:pg16` 컨테이너(빈 DB, `create_all` 전혀 안 거침)에
  `alembic upgrade head`를 처음부터 끝까지 실행, 에러 없이 34개 테이블
  전부(`hub_knowledge` 포함) 생성 확인. `alembic/env.py`는 무거운
  ML/ORM import(torch·transformers 등, 이 머신엔 미설치) 없이 순수 SQL
  DDL만 검증하려고 임시로 target_metadata를 비웠다가 검증 후 원본으로
  완전히 복원(`git diff` 무변경 확인).
- import-linter가 `vision_repository.py`(hub-independence 위반, ontology→
  core.matrix.grid_oracle_database_manager→titanic/mova/viewer/dispatch)를
  잡아내는데, `git stash` 비교로 이번 변경 이전부터 있던 기존 위반임을
  확인(파일 자체는 이전에도 있었고 DI만 안 됐을 뿐이라 정적 분석엔 그때도
  걸렸음) — 이번 작업이 새로 만든 문제 아님.

- **CLIP hang은 이번 세션에서 재현되지 않았다** — 네트워크가 정상이라
  `from_pretrained()`가 17초에 성공. 대신 캐시에서 결정적 증거를 찾았다:
  `~/.cache/huggingface/hub/models--openai--clip-vit-base-patch32/blobs/*.incomplete`
  (490MB, 07-28 16:09 생성 후 정체). hang 단계는 collection이 아니라 **테스트 실행
  중 `from_pretrained()`의 네트워크 왕복**으로 특정(어댑터가 함수 본문 안에서
  import되고 모델 로드도 `detect()` 시점이라 collection은 영향 없음). 근본 원인은
  코드가 아니라 "캐시가 있어도 매번 HF Hub etag 확인 → 멈추면 무한 대기" 구조.
  `HF_HUB_OFFLINE` 적용 후 캐시 누락 시 hang 대신 4.5초 만에 `OSError`로 즉시
  실패하는 것까지 실측 확인.
- **공개 개발로그에서 인증 관련 항목을 통째로 뺐다** — 초안에서는 취약점 수정
  이력을 "권한 검증 설계 개선"으로 추상화해 넣으려 했으나, 추상화해도 "인증
  관련 작업을 했다"는 신호 자체가 과거 취약점의 존재를 암시하고 공격 힌트가
  된다는 판단으로 사용자와 함께 제외 결정. 미해결 IDOR은 언급조차 하지 않았다.
  최종 노출 스캔에서 데이터 파일 주석에 내부 문서 경로가 하나 남아 있던 것을
  발견해 제거(화면에 렌더링되진 않지만 기준 적용). 재스캔 클린.
- **genre MCP 도구는 500 — 설정이 아니라 학습 산출물 부재** —
  `suvis-vision-sentinel`의 `detect_anomaly`는 백엔드까지 왕복해 정상 응답
  (`is_poster=true`, `poster_confidence=0.699`, `sharpness=2587.96`). 반면
  `suvis-vision-genre`의 `list_supported_classes`는 백엔드 500이고 원인은
  `apps/ontology/runs/genre_classify/classes.json` 부재였다. `runs/`는
  `.gitignore` 대상(`suvisdev/.gitignore:70`)이고 디렉터리 자체가 없다 —
  echo 어댑터 테스트가 실패하는 것과 같은 기존 조건이며 MCP 설정 문제가 아니다.
  등록·연결·`tools/list`는 두 서버 모두 정상.
- **세션 내에서는 connected 상태를 확인할 수 없다** — `.mcp.json`은 세션 시작 시
  로드되고, `claude mcp list`상 두 서버는 `⏸ Pending approval` 상태다. 프로젝트
  스코프 서버는 사용자 승인이 필요하므로 최종 connected 확인은 사용자 몫이다.
  대신 Claude Code와 동일한 방식(stdio JSON-RPC)으로 직접 띄워 `initialize`~
  `tools/call`까지 왕복시켜 검증했다.
- **루트 `CLAUDE.md`가 권장 길이를 넘겼다** — 자동 메모리 문서를 쓰며 확인:
  `CLAUDE.md`는 길이와 무관하게 전체 로드되지만 200줄 이내가 지시 준수에 유리한데,
  이번 세션의 추가분으로 216줄이 됐다. 더 늘릴 내용은 `.claude/rules/`나 `_docs/`로
  빼는 게 낫다는 메모를 `auto-memory.md`에 남겼다(정리 자체는 미착수).
- **붙여넣은 규칙 템플릿이 다른 프로젝트 것이었다** — 루트 `CLAUDE.md`에 추가하라고
  받은 내용이 "Node.js REST API / npm test / Jest+Supertest / `AppError`(`src/errors/`)
  / `src/legacy/` / payments PCI / `.env.local` / develop 브랜치"였는데, 실제로는
  백엔드가 Python·FastAPI, 프론트는 pnpm(테스트 0건), `src/`·`AppError`·`payments`·
  `develop` 전부 부재, env는 `suvisdev/.env` 하나. 대조표로 보고하고 카테고리만
  살려 실측 값으로 채웠다. 미리 만들어져 있던 빈 규칙 파일 `testing.md`·
  `security/pci.md`도 같은 출처 — `testing.md`는 백엔드 pytest 기준으로 다시 쓰고,
  `pci.md`는 결제 코드가 없다는 배너를 달아 "생기면 발동하는 게이트"로 작성.

### 산출물
- 코드: 위 "수정/구현" 파일 전체.
- 문서: 이 항목 + `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(완료분 이동),
  루트 `CLAUDE.md`, `.claude/rules/` 4종, `.claude/projects/memory/` 3종.
- `alembic/versions/20260729_0002_create_hub_knowledge.py` 신규 —
  빈 DB에서 `alembic upgrade head` 성공까지 확인 후 커밋.

## 2026-07-28

### 작업 내용
- suvis 프론트 LESSON 사이트에 LangChain 채팅 탭 신설 요청 — 처음엔 UI 틀만
  (SOCCER 섹션 아래 LANGCHAIN 섹션 추가, `/langchain/chat`), 이후 실제 파이프라인
  연결까지 확장 요청.
- silicon_valley 백엔드에 semantic_router(ontology) → LangChain 챗봇 엔진 파이프라인을
  클린 아키텍처(라우터→유스케이스→포트→리포지토리)로 구현.
- pnpm 로컬 개발환경 트러블슈팅(susu에 pnpm 잘못 로컬 설치, suvis `pnpm install`
  sharp 빌드 스크립트 차단) 지원.
- LangChain 활용 사례 문서 2건 추가(NCL, Elastic) + 기존 Morningstar 문서 접점
  섹션을 같은 형식으로 보강.

### 수정/구현
- **프론트(`suvis/`)**: `app/langchain/chat/page.tsx` 신규(soccer 채팅과 동일
  레이아웃, 인디고 테마, 실제 `/api/v1/langchain/chat` fetch). 사이드바에 LANGCHAIN
  섹션(채팅 링크)을 11개 페이지에 동일 추가(이 저장소가 사이드바 nav를 페이지마다
  복사하는 기존 관례를 따름). `pnpm-workspace.yaml`의 `allowBuilds.sharp`를
  자리표시자 텍스트에서 `true`로 수정. `susu/`에 잘못 로컬 설치됐던
  `node_modules`/`package.json`/`package-lock.json`/`pnpm-lock.yaml` 정리(삭제).
- **백엔드(`suvisdev/apps/silicon_valley/`)**: 신규 —
  `app/ports/output/rangchain_chat_engine_port.py`(`RangchainChatEnginePort`),
  `adapter/outbound/repositories/rangchain_chat_engine_repository.py`
  (`ChatPromptTemplate`+`MessagesPlaceholder`+`ChatOllama` LCEL 체인, destination별
  시스템 프롬프트 분기, `OLLAMA_BASE_URL` 반영), `app/dtos/rangchain_chat_dto.py`,
  `app/ports/input/rangchain_chat_use_case.py`, `app/ports/output/rangchain_chat_errors.py`,
  `adapter/inbound/api/schemas/rangchain_chat_schema.py`,
  `adapter/inbound/api/v1/rangchain_chat_router.py`(`POST /api/v1/langchain/chat`),
  `dependencies/rangchain_chat_provider.py`(ontology의 `get_semantic_router_use_case`를
  그대로 DI 재사용 — mova가 ontology를 참조하는 기존 cross-app 관례를 따름).
  `app/use_case/rangchain_interactor.py` — `semantic_router.route()` 호출 후 결과
  (destination/entities/answer)를 LangChain 엔진에 전달하도록 작성. `silicon_valley_router`에
  라우터 등록.
- **문서**: `apps/silicon_valley/_docs/ranchain-ncl-strategy.md`,
  `rangchain-elastic-strategy.md` 신규, `rangchain-monigstar-strategy.md` 접점
  섹션 보강 — 전부 "이 저장소엔 해당 데이터 소스 없음, 문서화만" 결론(실제
  데이터·구현은 보류).

### 오류·막힌 점
- **500 plain-text 파싱 오류**(`"Unexpected token 'I', "Internal S"... is not
  valid JSON"`): 원인은 `SemanticRouterInteractor.route()`(ontology)의
  general(잡담) 분기가 `HubRagError`를 잡지 않고 그대로 던지는데,
  `rangchain_chat_router.py`는 `RangchainChatError`만 캐치해서 미처리 예외가
  FastAPI 기본 500(plain text)으로 나간 것. `rangchain_interactor.py`에서
  `semantic_router.route()` 호출을 `HubRagError` 캐치 → `RangchainChatError`
  변환으로 고침. `GEMINI_API_KEY`는 `.env`에 설정돼 있어 정확한 실패 원인
  (quota/네트워크 등)은 재현 시 에러 메시지로 추가 확인 필요 — 이번 세션에서는
  백엔드 서버가 환경에 안 떠 있어 재기동 후 실제 검증은 못 함(코드 리뷰로만
  원인 특정).
- `[ERR_PNPM_IGNORED_BUILDS] sharp` — `pnpm-workspace.yaml`의 `allowBuilds.sharp`
  값이 `true` 대신 자리표시자 텍스트였던 게 원인.
- `[ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL] Command "dev" not found` — `susu`
  (Flutter, `package.json` 없음)에서 `pnpm dev`를 실행해 발생. `suvis`(Next.js)가
  맞는 위치.

### 데이터
- 해당 없음.

### 산출물
- 프론트: `suvis/app/langchain/chat/page.tsx`(신규) + 사이드바 11개 파일,
  `suvis/pnpm-workspace.yaml`.
- 백엔드: `apps/silicon_valley/` 내 `rangchain_chat_*`/`rangchain_interactor.py`
  8개 파일 신규, `adapter/inbound/api/__init__.py` 라우터 등록.
- 문서: `ranchain-ncl-strategy.md`, `rangchain-elastic-strategy.md`(신규),
  `rangchain-monigstar-strategy.md`(수정).
- 커밋 해시: 이번 커밋 참고.

---

### [2] PROGRESS 백로그 점검 — 진행 가능한 항목 처리

**배경**: 사용자가 `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 "다음/남은 작업"을
확인 후 지금 바로 진행 가능한 부분을 진행해달라고 요청. 비전 02·05(제품 결정
대기), 06 저장 지속화·S3(AWS 미연결), 시크릿(a)(단독 실행 금지 명시)는 외부
의존/결정 때문에 스킵하고, 실제 진행 가능한 두 항목만 처리.

**수정/구현**:
1. **`apps/mova/tests/test_import_interactor.py` 실패 2건 수정** — 원인은
   `ImportInteractor.__init__`에 `box_office`/`hub_rag` 파라미터가 추가됐는데
   테스트는 예전 3-인자 시그니처로 호출하던 것. 두 테스트 모두 이 두 의존성을
   실제로 쓰지 않는 경로라(`box_office` 미참조, `hub_rag.ingest_movie`는
   예외를 삼키는 try/except 안) `AsyncMock()` 2개만 추가해 해결. 8개 전부
   통과 확인(`/home/a/.venv/bin/python -m pytest apps/mova/tests/...`).
   `test_llm_error_handling.py`는 이미 통과 상태였음(PROGRESS 기록이 stale).
2. **dispatch `watcher/judge/spam/adress` 인증 공백 감사** — watcher·judge는
   `/myself` 스캐폴딩 스텁뿐이라 위험 없음. spam은 프론트·백엔드 어디서도
   호출하는 곳이 없는 미사용 코드라 위험 낮음. **adress는 실제 취약점**:
   `search`/`upload` 둘 다 인증이 전혀 없었는데, 어드민 UI
   (`admin/dispatch/contacts/page.tsx`)뿐 아니라 LESSON 공개 데모
   (`suvis/app/mail/contacts/page.tsx`, 로그인 개념 없음)도 같은 백엔드
   엔드포인트를 호출 — 2026-07-27 인증 공백 대응 당시 "어드민 UI 미사용"으로
   보고 범위에서 뺐던 판단이 틀렸음이 이번에 드러남. 사용자 확인 후(어드민만
   가드, 레슨 데모는 막기로 결정) 2026-07-27과 동일 패턴으로 수정:
   - BE: `adress_router.py`의 `search`/`upload`에
     `Depends(require_admin)` 추가.
   - FE 프록시: `suvis/app/api/dispatch/adress/{search,upload}/route.ts`가
     들어온 `Authorization` 헤더를 `backendFetch`로 전달하도록 수정(search는
     raw `fetch`에서 `backendFetch`로 교체).
   - FE 클라: `admin/dispatch/contacts/page.tsx` 업로드 호출에
     `suvis-session.ts`의 `authHeader()` 첨부.
   - `suvis/app/mail/contacts/page.tsx`(공개 레슨 데모)는 코드 변경 없음 —
     이제 업로드 시 401을 받게 됨(의도된 동작). 이 페이지 자체를 어떻게 할지는
     별도 결정 필요(PROGRESS 백로그에 남김).

**검증**: `python3 -m ast` 문법 검증 통과, `pnpm exec tsc --noEmit` 통과,
`pytest apps/mova/tests apps/dispatch`(jwt 미설치로 `test_whoami_router.py`
제외) 41 passed / 2 failed — 실패 2건은 `test_send_email_interactor.py`
(orchestrator 프롬프트 포맷 불일치, 이번 작업과 무관하게 기존에 깨져 있던
것을 우연히 발견 — 수정 안 함, PROGRESS 백로그에 신규 등록).

**오류·막힌 점**:
- `/home/a/.venv`에 `requirements.txt`엔 있는 `PyJWT[crypto]`가 실제로
  설치돼 있지 않아 `shared.security.require_admin`을 import하는 모든 모듈
  (email/telegram/discord/receive/harvester/adress 라우터,
  `test_whoami_router.py`)이 이 venv에서 import 실패함 — 내 변경으로 생긴
  문제가 아니라 기존 email_router.py로도 재현 확인. venv에
  `pip install -r requirements.txt` 재실행 필요(이번 세션에선 미설치 상태로
  둠, 별도 사용자 확인 필요해 임의 설치 안 함).

### 산출물 (2)
- `apps/mova/tests/test_import_interactor.py`(수정),
  `apps/dispatch/adapter/inbound/api/v1/adress_router.py`(수정),
  `suvis/app/api/dispatch/adress/search/route.ts`,
  `suvis/app/api/dispatch/adress/upload/route.ts`,
  `suvis/app/admin/dispatch/contacts/page.tsx`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신(완료 항목 반영 + 신규 백로그 3건:
  mail/contacts 공개 데모 처리, test_send_email_interactor 실패, PyJWT 미설치).

---

### [3] 프론트 프로덕션 API URL 설정 + LangChain 모델을 Gemini로 교체

**배경**: 강사가 `suvisdev/.cursorrules`에 `NEXT_PUBLIC_BASE_URL=https://api.suvisdev.cloud`를
넣으라고 지시했다는데, 이유를 물어와 확인해보니 지시 자체가 틀렸음. `.cursorrules`는
Cursor 에디터용 AI 코딩 규칙 문서일 뿐 어떤 코드도 환경변수로 읽지 않고,
`NEXT_PUBLIC_BASE_URL`이라는 이름도 이 저장소 어디에도 없음(실제 코드가 읽는
이름은 `NEXT_PUBLIC_API_URL`, `suvis/lib/backend-client.ts` 등 7곳). 게다가
`NEXT_PUBLIC_*`는 프론트(`suvis/`) 관례라 백엔드(`suvisdev/`) 쪽에 있을 이유도
없음. 올바른 위치·이름으로 바로잡아 설정.

이어서 랭체인 모델을 Gemini로 바꿀 수 있는지 요청받아 진행.

**수정/구현**:
1. `suvis/.env.production`(신규) — `NEXT_PUBLIC_API_URL=https://api.suvisdev.cloud`.
   `.gitignore`엔 `.env.local`만 있어 커밋 가능(NEXT_PUBLIC 값은 어차피 브라우저에
   노출되는 값이라 커밋해도 안전).
2. `rangchain_chat_engine_repository.py` — `ChatOllama(exaone3.5:2.4b)` →
   `ChatGoogleGenerativeAI`(langchain-google-genai)로 교체. 모델 ID는 새로 만들지
   않고 `core.matrix.vauly_keymaker_secret_manager.GEMINI_MODEL_MAP["flash15"]`
   (`gemini-3.1-flash-lite`)를 재사용, API 키도 `get_keymaker().gemini_api_key`
   재사용 — ontology `GeminiLlmAdapter` 등 다른 Gemini 사용처와 키·모델 관리
   일원화. LCEL 체인 구조(`ChatPromptTemplate`+`MessagesPlaceholder`+
   `StrOutputParser`)·destination별 프롬프트 분기·에러 래핑은 그대로 유지, LLM
   provider만 교체.
3. `requirements.txt` — `langchain-google-genai==4.3.2` 추가, `langchain-core`
   (1.4.8→1.5.1)·`langsmith`(0.9.3→0.10.10)는 설치 과정에서 자동으로 딸려 올라간
   실제 버전에 맞춰 갱신. `/home/a/.venv`에 실제 설치 완료.

**검증**: `RangchainChatEngineRepository().generate(...)`를 직접 호출해 실제
Gemini 응답("안녕하세요! 저는 SUVIS의 한국어 어시스턴트입니다...") 받는 것까지
확인.

**오류·막힌 점**: `langchain-ollama`도 `/home/a/.venv`에 실제로는 설치돼 있지
않았음(PyJWT와 같은 종류의 기존 venv-requirements.txt 드리프트) — 이번 작업으로
ChatOllama를 걷어내서 문제되진 않았지만, venv 전체가 `requirements.txt`와
계속 어긋나 있다는 신호라 언젠가 `pip install -r requirements.txt` 재실행 필요.

### 산출물 (3)
- `suvis/.env.production`(신규), `suvisdev/apps/silicon_valley/adapter/outbound/repositories/rangchain_chat_engine_repository.py`(수정),
  `suvisdev/requirements.txt`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 LangChain 파이프라인 항목에 Gemini
  교체 내용 반영.

---

### [4] CLAUDE.md 응답 언어 지침 + PROGRESS 백로그 추가 처리

**배경**: 사용자가 CLAUDE.md에 "한국어로만 답변, 다른 언어 금지" 지침 추가 요청.
이어서 PROGRESS.md를 다시 확인하고 진행 가능한 나머지 항목(테스트 실패, venv
드리프트) 처리 요청.

**수정/구현**:
1. `CLAUDE.md`에 "## 응답 언어" 섹션 추가 — 항상 한국어로만 답변, 다른 언어
   사용 금지.
2. **`test_send_email_interactor.py` 실패 2건 수정** — `SendEmailInteractor.send()`가
   이메일 품질 개선을 위해 `orchestrator.generate()` 호출에 `system=` 키워드
   인자를 추가한 게 실제 기능인데(수신자 정보 포함 프롬프트 + 이메일 작성
   전문가 시스템 프롬프트), 테스트 2건이 예전 시그니처(위치 인자 하나만)를
   가정하고 있어 깨졌던 것. `test_hub_record_called_before_orchestrator`의
   `mock_orc.generate.side_effect` 람다가 `system=` 키워드를 못 받아 TypeError,
   `test_orchestrator_generates_body`는 호출 인자 자체를 잘못 assert. 둘 다
   실제 호출 형태에 맞게 테스트 수정. 14개 전부 통과.
3. **PyJWT/langchain-ollama 미설치 해소** — `pip install -r requirements.txt`
   전체 실행을 시도했으나 두 단계로 실패:
   - 1차: `/tmp`가 WSL2 tmpfs(3.9G)라 torch(843MB) 등 받다가
     `[Errno 28] No space left on device` — `TMPDIR`을 디스크 쪽
     (`/home/a/.cache/pip-tmp`, `/`는 898G 여유)으로 돌려 재시도.
   - 2차: `catboost==1.2.8`이 Python 3.14에서 빌드 실패
     (`AttributeError: 'Distribution' object has no attribute 'dry_run'` —
     distutils가 Python 3.12+에서 빠지면서 구식 setup.py가 깨짐). titanic 앱이
     실제로 쓰는 패키지라 requirements.txt에서 못 뺌 — 전체 동기화는 별도
     결정(catboost 버전 업/Python 버전 조정) 필요해 백로그로 남김.
   - 실제 목적(PyJWT 미설치)은 전체 동기화 대신 `PyJWT[crypto]==2.10.1`,
     `langchain-ollama==1.1.0`만 개별 설치로 해결. `require_admin`을 쓰는
     `email_router`·`rangchain_chat_router` import 확인, `apps/mova/tests`+
     `apps/dispatch` 47개 전부 통과(이전엔 jwt 없어 수집 실패하던
     `test_whoami_router.py`도 포함).

### 산출물 (4)
- `CLAUDE.md`(수정), `suvisdev/apps/dispatch/test/test_send_email_interactor.py`(수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신 — 완료 항목 반영(테스트 수정,
  PyJWT/langchain-ollama 설치), catboost 빌드 실패를 신규 백로그로 등록.

---

### [5] catboost/Python 3.14 빌드 문제 해소 + 캐시 정리

**배경**: [4]에서 남긴 백로그(`catboost` 빌드 실패로 `pip install -r
requirements.txt` 전체 불가)를 이어서 처리. 이후 사용자가 `suvisdev/`의
`.import_linter_cache`/`.mypy_cache`/`.pytest_cache`/`.ruff_cache`가 필요한지
질문.

**수정/구현**:
1. `catboost==1.2.8`→`1.2.10` 버전 업 — PyPI에 Python 3.14용 사전빌드 wheel
   (`catboost-1.2.10-cp314-cp314-manylinux2014_x86_64.whl`)이 존재함을
   `pip download`로 먼저 확인 후 진행. titanic 앱의 실제 사용(`CatBoostClassifier(
   iterations=200, verbose=False, random_state=42)`)은 단순 API라 호환 문제
   없음.
2. `pip install -r requirements.txt` 재실행 — 이번엔 빌드 에러 없이 끝까지
   성공(torch-2.12.1+cu126 등 전체 설치). `catboost`/`jwt` import 확인.
3. `apps/mova/tests`+`apps/dispatch`+`apps/titanic` 전체 재실행 —
   mova/dispatch는 계속 통과. **`apps/titanic/tests` 4개가 새로 눈에 띔**
   (패키지 설치와 무관, 지금 코드에 없는 이름 import: `JackTrainerMapper`,
   `titanic.adapter.outbound.llm`, `PassengerEntity`,
   `passenger_jack_trainer_vo` 모듈) — 원인 조사·수정 안 함, 백로그 등록.
4. `.import_linter_cache`/`.mypy_cache`(18M)/`.pytest_cache`/`.ruff_cache`
   삭제 — 전부 재생성 가능한 도구 캐시. `.mypy_cache`/`.pytest_cache`/
   `.ruff_cache`는 `.gitignore`에 이미 명시, `.import_linter_cache`는 자체
   `.gitignore`(`*`)로 커밋 제외돼 있어 git 추적에는 영향 없음.

**오류·막힌 점**: `pip install` 1차 시도 시 `/tmp`가 WSL2 tmpfs(3.9G)라
torch(843MB) 받다가 공간 부족 — `TMPDIR`을 디스크 쪽(`/home/a/.cache/pip-tmp`)
으로 돌려 재시도. 이후 catboost 문제로 2차 실패, 버전 업으로 최종 해결.

### 산출물 (5)
- `suvisdev/requirements.txt`(catboost 버전만 수정).
- `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신 — catboost 백로그 완료 처리,
  titanic 테스트 4건 신규 백로그 등록.

---

### [6] silicon_valley → execsuite 앱 이름 변경 + labs/ 04·08 독립 실습 데모

**배경**: 사용자가 `apps/silicon_valley`를 `admin`으로 바꿔달라고 요청 —
이미 `suvis/app/admin/*`(어드민 대시보드)·`viewer`(RBAC)가 "admin"이라는
이름을 다른 의미로 쓰고 있어 충돌 우려를 짚고 대안을 물으니 `execsuite`로
확정. 이어서 "04·08은 mova/gildle에 안 쓰더라도 만들어둘 수 있냐"는 질문에,
`00_COMMON_conventions.md` §8의 "기법 먼저·용도 나중" 실패 사례를 짚고
독립 실습 영역으로 분리할 것을 확인받아 진행.

**수정/구현**:
1. **이름 변경**: `git mv apps/silicon_valley apps/execsuite`(102개 파일
   rename). 앱 내부 46개 `.py` 파일 + 외부 3곳(`main.py`, `alembic/env.py`,
   `.importlinter`)의 `silicon_valley`/`silicon-valley` 참조를 전부
   `execsuite`로 치환. `apps/ontology/_docs/star-craft-pipeline.md`의 앱
   목록, `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`의 완료 항목 라벨도 "구
   silicon_valley" 표기로 갱신(WORK_LOG 과거 기록은 당시 이름 그대로 유지).
   검증: `execsuite_router` 단독 import, `main.py` 전체 import 모두 성공,
   라우트(`/pdf/summarize`, `/langchain/chat` 등) 정상 확인.
2. **`suvisdev/labs/` 신설** — `apps/`의 어떤 앱과도 엮이지 않는 완전 고립
   영역(`main.py` 미등록, `.importlinter` 미포함). README에 명시한 원칙:
   Port(`ports.py`)는 참조 구현일 뿐 실제 편입 시 그 앱 컨벤션에 맞춰
   재배치, DTO는 도메인 중립이라 그대로 재사용 가능. GPU 없는 환경
   (m7i-flex.large)이라 학습 없이 사전학습 모델 추론만.
   - `pose_estimation/`(04·Atlas): YOLOv8n-pose(ultralytics, 3.3M 파라미터).
     `yolov8n-pose.pt`는 최초 실행 시 자동 다운로드(`*.pt`는 `.gitignore`에
     이미 있어 커밋 걱정 없음). 샘플은 ultralytics 기본 내장 `zidane.jpg`
     복사. 실행 검증 완료 — 샘플에서 사람 2명, 각 17개 COCO keypoint 정상
     출력.
   - `video_classification/`(08·Chronos): torchvision.models.video 중 실제
     파라미터 수 비교(s3d 8.3M < mc3_18 11.7M < r3d_18 33.4M)로 가장 가벼운
     `s3d`(Kinetics-400, 400개 레이블) 선택. 가중치는 torch hub가
     `~/.cache/torch/hub/checkpoints/`에 자동 캐시. 이 저장소엔 실제 동영상
     샘플이 없어 `samples/source.jpg`(ultralytics 기본 내장 `bus.jpg`)를
     확대하며 프레임을 늘린 합성 클립을 매 실행 즉석 생성(디스크 미저장)해
     분류 — 진짜 동작이 없으니 결과 자체보다 파이프라인이 CPU에서 학습 없이
     끝까지 도는지 확인용임을 demo 출력·README에 명시.

**검증**: 두 데모(`python -m labs.pose_estimation.demo`,
`python -m labs.video_classification.demo`) 실제 실행해 결과 확인.
`labs/` 전체 `ast.parse` 문법 검증 통과.

**오류·막힌 점**: 없음(이름 변경·labs 구현 모두 실행 검증까지 완료).
다만 이름 변경 후 회귀 확인용으로 돌린 `mova+dispatch+ontology` 전체
테스트는 ontology 쪽 비전 모델 로딩이 무거워 커밋 시점까지 계속 실행 중이었음
— `execsuite_router`/`main.py` 자체는 별도로 직접 import 검증을 마쳐 이름
변경 자체의 정합성은 확인됨.

### 산출물 (6)
- `apps/execsuite/`(구 `apps/silicon_valley/`, rename), `main.py`,
  `alembic/env.py`, `.importlinter`(수정).
- `suvisdev/labs/`(신규): `README.md`, `pose_estimation/`(`dto.py`,
  `ports.py`, `adapters/yolov8_pose_adapter.py`, `demo.py`,
  `samples/sample.jpg`), `video_classification/`(`dto.py`, `ports.py`,
  `adapters/s3d_adapter.py`, `demo.py`, `samples/source.jpg`).
- `apps/ontology/_docs/star-craft-pipeline.md`,
  `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(execsuite 라벨 갱신).

---

### [7] labs/ 03(시맨틱 분할) 추가 + mova 부팅 작업 ENABLE_MOVA_STARTUP 플래그

**배경**: [6]에 이어 "03도 04·08처럼 labs에 만들 수 있냐"는 질문에, 03은
04·08과 제외 사유가 다름을 짚었다 — 04·08은 순수 "용도 없음"이지만 03은
"용도(서울 보도 검출)는 있었는데 검증 데이터(OSM sidewalk 태그)가 없어서"
막힌 케이스. 사용자 확인 후 04·08과 동일 패턴으로 labs에 추가.

이어서 별개 요청: 이 프로젝트가 집(GPU/EXAONE)·AWS EC2(GPU 없음, Gemini)
두 환경에 배포되는데, mova의 부팅 자동 작업(TMDB 시드·랭킹/KOFIC 스케줄러 —
전부 Ollama 의존)이 EC2에서 연결 실패 WARNING을 계속 뿜는 문제를 코드
제거·브랜치 분리 없이 환경변수 플래그로 해결.

**수정/구현**:
1. **`suvisdev/labs/semantic_segmentation/`**(03·Loom) — 04·08과 동일 구조
   (`dto.py`/`ports.py`/`adapters/`/`demo.py`/`samples/`). 모델은
   torchvision.models.segmentation 4종 실측 비교(lraspp_mobilenet_v3_large
   3.2M < deeplabv3_mobilenet_v3_large 11.0M < fcn_resnet50 35.3M <
   deeplabv3_resnet50 42.0M) 후 가장 가벼운 `lraspp_mobilenet_v3_large`
   선택. Pascal VOC 21클래스 사전학습(도로/보도 클래스 없음 — 그래서 이
   데모가 막힌 용도인 "서울 보도 검출"과 구조적으로 무관함을 README에 명시).
   전처리가 짧은 변을 520px로 리사이즈해 마스크 크기가 원본과 달라짐을
   실측으로 확인 → DTO의 width/height는 원본이 아니라 실제 마스크 크기로
   정확히 반영. 가중치(~12.5MB)는 torch hub가 `~/.cache/torch/hub/checkpoints/`
   에 자동 캐시(리포에 안 남음, gitignore 불필요 확인). `samples/sample.jpg`
   (ultralytics 기본 내장 `bus.jpg`)로 실행 검증 완료(bus 31.0%, person
   12.2%, 배경 56.8% 정상 검출).
2. **`main.py`에 `ENABLE_MOVA_STARTUP` 플래그 추가** — `lifespan()` 안
   TMDB 카탈로그 시드·chat_trend 랭킹 스케줄러·KOFIC 박스오피스 스케줄러
   3개 try 블록을 `if _ENABLE_MOVA_STARTUP:`로 감싸고 `else:`에 "비활성화됨"
   info 로그 추가. 기본값 `true`(안 넣으면 기존 집 환경 동작 그대로).
   "HubRagInteractor 임베딩 ingest"는 별도 호출이 아니라 TMDB 시드
   (`ImportInteractor._persist_snapshots` → `_ingest_to_hub`) 안에 이미
   포함돼 있어 TMDB 시드 하나만 감싸면 같이 꺼짐 — 별도 지점 불필요.
   `seed_viewer_if_empty()`, Ollama 워밍업, 다른 앱(dispatch/execsuite/
   vision 등)의 부팅 작업은 건드리지 않음.

**부수 발견(건드리지 않음, 백로그 등록)**: `main.py`의 `seed_assistants_if_empty`
import(`mova.adapter.outbound.pg.assistants_pg_repository`)가 실제로
존재하지 않는 모듈 — 실제 파일명은 `platform_assistants_pg_repository.py`고
`seed_assistants_if_empty` 함수 자체가 코드베이스 어디에도 없음. 매 부팅마다
`ModuleNotFoundError`가 나서 기존 try/except로 조용히 삼켜지고 있던 기존 버그.

**검증**: 실제 DB/Ollama 없이 `verify_connection`/`create_tables`/
mova 시드·스케줄러 함수를 전부 mock으로 대체해 `lifespan()`의 분기만
격리 검증.
- `ENABLE_MOVA_STARTUP=false` → "비활성화됨" info 로그만, 3개 함수
  (`seed_catalog_if_sparse`/`run_chat_trend_scheduler`/
  `run_kofic_import_scheduler`) 전부 `called=False` 확인.
- 미설정(기본값) → 3개 함수 전부 `called=True`, 기존 로그(랭킹/KOFIC
  스케줄러 시작) 정상 출력 확인.

**오류·막힌 점**: [6]에서 백그라운드로 남겨둔 `mova+dispatch+ontology`
전체 회귀 테스트가 `openai/clip-vit-base-patch32`(Sentinel 이상탐지가
쓰는 CLIP 모델) Hugging Face Hub 다운로드에서 1시간 넘게 멈춰 있는 걸
발견해 프로세스 종료 — execsuite 이름 변경 자체는 별도 직접 import
검증으로 이미 확인이 끝난 상태라 이 hang은 이번 작업과 무관.

### 산출물 (7)
- `suvisdev/labs/semantic_segmentation/`(신규): `dto.py`, `ports.py`,
  `adapters/lraspp_adapter.py`, `demo.py`, `samples/sample.jpg`.
- `suvisdev/labs/README.md`(03 절 추가, §03 특수 사정 명시).
- `suvisdev/main.py`(`ENABLE_MOVA_STARTUP` 플래그 추가).

---

### [8] PROGRESS 백로그 마저 처리 — titanic 도메인 테스트 재작성 + seed_assistants 죽은 코드 제거

**배경**: [7]에서 남긴 백로그 중 진행 가능한 2건(titanic 테스트 4개 수집
실패, `seed_assistants_if_empty` import 버그) 처리.

**수정/구현**:
1. **titanic 테스트 4개** — 조사해보니 단순 이름 변경 드리프트가 아니라
   도메인이 재설계된 상태였음(관련 VO·엔티티·깨진 테스트 4개가 전부 같은
   커밋 `251ae61`(2026-07-08, "하위 파일 구조 통째로 업로드 성공")에서
   한꺼번에 들어옴 — 시간이 지나며 리팩터링된 게 아니라 애초부터 서로 안
   맞는 버전이 같이 업로드된 것). mova(`platform_users_vo.py` 등)·gildle
   (`route_edge.py` 등) 둘 다 "필드 하나당 VO 하나"가 아니라 "개념당 VO
   하나"로 묶는 방식을 쓰고 있어, 지금 titanic의 `PassengerIdentity`/
   `Survived` 방식이 이 프로젝트의 실제 컨벤션과 일치함을 확인(titanic은
   `.cursorrules`상 "기준선"). 사용자 확인 후:
   - `test_korean_ai_adapter.py` 삭제 — `titanic.adapter.outbound.llm.
     korean_ai_adapter`는 한 번도 만들어진 적 없고, 실제 구현은
     `tests/korean_ai.py`(프로토타입 스크립트)에 있으며 이미 통과 중인
     `test_korean_ai.py`가 커버 중인 중복 고아 테스트였음.
   - 나머지 3개(vo/entity/mapper) 삭제 후, 현재 도메인
     (`PassengerIdentity`/`Survived`/`Title`/`Gender`/`PassengerJackTrainer`/
     `PassengerJackTrainerMapper`) 기준으로 41개 테스트 새로 작성 — frozen
     불변성, 팩토리 검증(from_raw/from_name 성공·실패), DDD 동등성 규칙
     (passenger_id만으로 동등성 판단), DIP 어댑터 스왑(`SimpleNamespace`로
     실제 SQLAlchemy ORM 대신 같은 모양의 가짜를 넣어도 매퍼 결과가 같음을
     검증) 포함 — titanic이 기준선이라 mova/gildle이 참고할 모범 형태로
     작성.
   - **작성 중 실제 버그 발견**: `PassengerJackTrainer.summary()`와
     `PassengerJackTrainerMapper.to_orm_fields()` 둘 다 존재하지 않는
     `entity.identity.age`를 참조해 `AttributeError`(`PassengerIdentity`는
     title+gender만 갖고 age는 의도적으로 안 가짐 — docstring에 명시).
     `identity.age` 참조가 이 두 곳뿐임을 grep으로 확인 후 두 메서드 모두
     age 참조 제거로 수정.
   - 검증: `apps/titanic/tests` 44개 전부 통과(1개 ollama 마커 skip).
2. **`seed_assistants_if_empty` 죽은 코드 제거** — `AssistantsPgRepository`
   (실제 파일 `platform_assistants_pg_repository.py`)엔 `list_active`/
   `get_by_slug`만 있고 count/insert 메서드 자체가 없으며, 기본 시드
   데이터도 어디에도 없음 — 즉 이 시드 기능은 리네임된 게 아니라 애초에
   구현된 적이 없는 죽은 코드로 확인됨. 사용자 확인 후 `main.py`의 해당
   try/except 블록 통째로 제거. `ENABLE_MOVA_STARTUP=false`/미설정 두
   시나리오 mock 하네스로 재검증 — `assistants` WARNING이 완전히 사라지고
   플래그 동작은 그대로 정상임을 확인.

**검증**: `apps/mova/tests`+`apps/dispatch`+`apps/titanic/tests` 전체
91 passed, 1 skipped. `main.py` import 정상.

### 산출물 (8)
- `apps/titanic/domain/entities/passenger_jack_trainer_entity.py`,
  `apps/titanic/adapter/outbound/mappers/passenger_jack_trainer_mapper.py`
  (버그 수정).
- `apps/titanic/tests/domain/value_objects/test_passenger_jack_trainer_vo.py`,
  `apps/titanic/tests/domain/etitites/test_passenger_jack_trainer_entity.py`,
  `apps/titanic/tests/adapter/outbound/mappers/test_passenger_jack_trainer_mapper.py`
  (새로 작성), `test_korean_ai_adapter.py`(삭제).
- `suvisdev/main.py`(`seed_assistants_if_empty` 블록 제거).

---

### [9] LangGraph 하네스 문서 작성

**배경**: 사용자가 LangChain 선형 체인의 한계(분기·루프·상태관리 불가)와
LangGraph 도입 근거, Neo4j 기반 GraphRAG(지식그래프 구축·Text-to-Cypher·
하이브리드 검색) 자료를 제공하며, 시멘틱 라우터가 reasoning이 필요한
질문을 받았을 때 LangGraph를 활용하는 하네스 문서 작성을 요청. 이번엔
문서만 요청받아 코드는 건드리지 않음.

**작성**: `apps/execsuite/_docs/ranggraph-harness.md` — LangGraph 도입
근거, GraphRAG/Neo4j 활용법, 장단점, "이 프로젝트와의 접점" 절 작성.
접점 절은 실제 코드 기준으로 현재 상태를 짚음: `semantic_router_interactor`
(ontology)는 아직 `crud`/`rag`/`general` 3갈래뿐 "reasoning" 신호 없음,
`rangchain_chat_engine_repository.py`는 단일 선형 LCEL 체인, `langgraph`/
`neo4j-graphrag`는 `requirements.txt`에 설치만 돼 있고 코드베이스 어디서도
미사용, Neo4j 서버 자체가 `.env`에 `NEO4J_URI`/`NEO4J_USER` 없이 미배포
상태(`neo4j-hanress.md` 기존 확인 내용과 일치). 그 위에 제안 흐름(semantic_router
"reasoning 필요" 신호 추가 → LangGraph StateGraph의 retrieve→generate→
verify→재시도/종료 루프 → Neo4j 배포 후 GraphRAG로 retrieve 노드 보강)을
다이어그램과 단계적 도입 순서로 남김 — 실제 구현은 보류.

### 산출물 (9)
- `apps/execsuite/_docs/ranggraph-harness.md`(신규 작성).

---

### [10] Neo4j Docker 설치 전략 문서 작성

**배경**: [9] ranggraph-harness.md가 제안한 GraphRAG retrieve 노드를 실제로
쓰려면 Neo4j 서버가 먼저 떠 있어야 함 — 그 서버를 이 프로젝트 기존
방식(docker-compose)대로 띄우는 전략 문서 작성 요청. 문서만 요청받아
`docker-compose.yaml`/`.env` 실제 수정은 하지 않음.

**작성**: `apps/execsuite/_docs/neo4j-strategy.md` — 현재 상태(neo4j 서비스
없음, `.env`엔 비밀번호만, `star-craft-pipeline.md`에 예전 계획 스니펫
존재) 재확인 후, `docker-compose.yaml`에 추가할 `neo4j` 서비스 정의안
(`neo4j:5.26-community`, `NEO4J_AUTH`/`NEO4J_PLUGINS=apoc`, 포트
7474/7687, `neo4j_data`/`neo4j_logs` 네임드 볼륨, healthcheck — 기존
db/redis 서비스와 같은 패턴), `.env` 추가안(`NEO4J_URI`/`NEO4J_USER`,
`neo4j-hanress.md`가 이미 예정해둔 값), backend 컨테이너가 실제로 연결할
때 `DATABASE_URL`/`REDIS_URL`과 같은 "호스트용 vs 컨테이너용 URI 분리"
패턴 적용 방법, 기동·검증 절차(기존 `neo4j-hanress.md`의 확인 코드 재사용)
를 정리. 남은 결정 사항(버전 태그 재확인, EC2 리소스, APOC 필요 여부)도
명시.

### 산출물 (10)
- `apps/execsuite/_docs/neo4j-strategy.md`(신규 작성).

---

### [11] EXAONE-3.5-2.4B-Instruct-AWQ 기반 lora-server 초기 세팅 (RTX 4060 8GB, 추론 전용)

**배경**: 초기화된 노트북에 lora-server(mova RAG 답변 생성용)를 새로 세팅.
원래 계획은 EXAONE AWQ였는데, `EXAONE_LOCAL_AI_SETUP.md` 8-1엔 8GB GPU에서
EXAONE-AWQ **학습**이 OOM나서 현재 운영은 Qwen2.5-1.5B(plain)로 돼 있다는
점을 먼저 확인시킴. 사용자는 "추론 전용"이 목적이라 학습 OOM은 무관하다며
EXAONE-3.5-**2.4B**-Instruct-AWQ(원래 계획이던 7.8B가 아니라 2.4B)로 진행
결정. 학습된 LoRA 어댑터(`~/lora_adapters/LATEST`)는 이 노트북에도 백업에도
없어서, 재학습·복사 없이 `serve.py`에 "어댑터 없으면 베이스만" 폴백을 최소
수정으로 추가하기로 함.

**환경 구성**: `cmake`/`nvidia-cuda-toolkit` sudo 설치(사용자 직접 실행) →
`uv` 설치 → `~/.venv-exaone`(python 3.12) 생성 → `torch==2.13.0+cu126`,
`transformers==5.13.1`, `gptqmodel==7.1.0`(소스 빌드), `peft`, `torchvision`
(gptqmodel 내부 import에 필요 — 기존 문서엔 없던 의존성), `optimum>=1.24.0`
(peft가 gptqmodel 백엔드를 인식하는 데 필요) 설치. `LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct-AWQ`
다운로드(2.1GB, repo root).

**실측 확인**:
- VRAM: 베이스 단독 로드 2455MiB, generate 후 2477MiB, 미학습 더미 LoRA까지
  얹어도 2533MiB — 8GB 카드에서 여유 충분(~5.6GB 남음).
- `BACKEND.EXLLAMA_V2` 커널 정상 동작(7.8B에서 겪었다는 Marlin 행 현상 없음,
  JIT 컴파일 2~16초).
- `get_peft_model()`이 7.8B 문서의 wte 패치(`_input_embed_layer="wte"`) 없이도
  정상 동작 — 이 2.4B 체크포인트·현재 transformers/peft/optimum 조합에선
  해당 패치가 불필요함을 확인.

**오류·막힌 점**:
- 다운로드된 `modeling_exaone.py`의 `create_causal_mask()` 호출이
  `transformers==5.13.1`과 호환 안 됨(`input_embeds`→`inputs_embeds` 이름
  변경, `cache_position` 인자 제거로 `TypeError`). 로컬 체크포인트 파일의
  해당 호출부만 최소 수정 — 7.8B 문서의 "wte 패치"와 같은 성격(체크포인트
  remote code가 설치된 transformers 버전보다 오래됨).

**수정/구현**: `model_servers/lora_server/serve.py` — `_read_latest()`가
`LATEST` 파일이 없으면 `None`(어댑터 없음) + `LORA_FALLBACK_BASE_MODEL`/
`LORA_FALLBACK_BACKEND`(기본값 EXAONE-3.5-2.4B-Instruct-AWQ/awq_gptqmodel)를
반환하도록 수정, `_load()`는 `adapter_dir`가 없으면 `PeftModel` 래핑을
생략하도록 수정. 실제 `uvicorn model_servers.lora_server.serve:app --port 8200`으로
기동해 `/health`(`adapter_dir: null` 확인)·`/generate` 실호출까지 검증함.

### 산출물 (11)
- `model_servers/lora_server/serve.py`(수정, 어댑터 없을 때 베이스 전용 폴백).
- `EXAONE-3.5-2.4B-Instruct-AWQ/modeling_exaone.py`(패치, 다운로드된 체크포인트 파일 — 리포 추적 대상 아님).
- `~/.venv-exaone`(신규 venv, 리포 밖).

---

## 2026-07-27

### [5] pdf_summary → pdf_loader 네이밍 환원 + LangChain 문서 2건

**배경**: 사용자가 [4]에서 만든 `pdf_summary_*` 네이밍을 원래 자신이 만들었던
파일명 `pdf_loader_interactor.py` 기준으로 되돌려달라고 요청.

**수정**: 13개 파일 `git mv`로 `pdf_summary_*` → `pdf_loader_*` 리네임,
클래스명도 동반 변경(`PdfSummaryUseCase`→`PdfLoaderUseCase`,
`PdfSummaryInteractor`→`PdfLoaderInteractor`, `PdfSummaryPort`→`PdfLoaderPort`,
`PdfSummaryRepository`→`PdfLoaderRepository`, `PdfSummaryOrm`→`PdfLoaderDocumentOrm`).
DB 테이블명 `pdf_summaries`→`pdf_loader_documents`(아직 실 DB 미적용 마이그레이션이라
새 리비전 없이 기존 파일 내용만 수정). 사용되지 않던 `PdfSummaryCommand` 죽은
코드 제거. `alembic/env.py` import, `adapter/inbound/api/__init__.py` 라우터
등록도 함께 갱신. import + 라우터 등록(`/pdf/summarize`) 재검증 완료.

**추가**: `apps/silicon_valley/_docs/rangchain-monigstar-strategy.md` —
LangChain 활용 사례(Morningstar 금융 인사이트 엔진) 문서화. 사용자가 실제
코드 구현은 원치 않아(이 저장소에 금융/시장 데이터 소스가 없음) 문서만 작성.

### 산출물 (5)
- 리네임된 13개 파일(경로는 위 커밋 diff 참고), `alembic/env.py`,
  `apps/silicon_valley/adapter/inbound/api/__init__.py`,
  `apps/silicon_valley/_docs/rangchain-monigstar-strategy.md`(신규).

---

### 작업 내용
- **03(Loom, 시맨틱 분할) 관문0 실측 조사** — "OSM 서울 walk가 보도를
  별도 way/태그로 갖는가(있으면 CV 불필요, 폐기)"를 Overpass API로 실측.
  용도 재정의 "보도 유무/폭" 기준으로 판정.
- 조사 중 사용자 지시로 **스코프 재조정**('폭' 폐기 → '유무'만, OSM
  `footway=sidewalk` 부분 데이터로 갈 수 있는지 재검토)까지 진행.

### 데이터 (Overpass API 실측, overpass-api.de)
- 서울 3개 지역 `sidewalk=*` 도로 속성 밀도:
  - 강남(37.495,127.025,37.515,127.050): 도로 903 / sidewalk 태그 11 (**1.2%**)
  - 성북 주거(37.585,127.010,37.605,127.035): 도로 1127 / sidewalk 태그 5 (**0.4%**),
    `footway=sidewalk` way 131, footway 전체 545, `width` 태그 5
  - 종로: footway 전체 922 (레이트리밋으로 일부 셀만)
- **커버리지 실측**(성북 소구역 37.590,127.010,37.605,127.030):
  도로 643 way/**96.85km** vs `footway=sidewalk` 25 way/**3.47km**
  → **보도길이/도로길이 = 0.04** (완전 양방향=2.0, 편측 완전=1.0 기준).
  도로 길이의 ~96%에 매핑된 보도 없음.

### 결론
- **관문0: "폐기(CV 불필요)" 불성립** — `sidewalk=*` 도로 속성은 사실상
  전무(0.4~1.2%), `width` 태그도 전무(재정의 용도 '폭'은 OSM에서 못 얻음).
- **스코프 재조정('유무'만)도 불가** — 두 각도 수렴: (1) 개념: OSM open-world라
  "매핑 없음 ≠ 보도 없음", "보도 없음→페널티" 규칙의 *부재* 신뢰 불가.
  (2) 실측: 커버리지 4% → 페널티가 도로 ~96%에 발화 = 노이즈.
- **최종: 03(Loom)을 04·08과 동급의 정식 '폐기/제외'로 확정(사용자 승인).**
  보도 신호 자체가 서울 OSM에 존재하지 않음이 실측 확인됨. 관문1(스트리트뷰+CV)은
  소비처 walk 그래프가 데모(4간선)이고 CV는 전 간선 이미지 필요 → 관문1
  이미지 비용 문제로 회귀.

### 오류·막힌 점
- Overpass 공개 서버(overpass-api.de) 과부하로 다수 쿼리 timeout/406/empty.
  미러(kumi.systems, private.coffee)도 무응답. curl+User-Agent로 서버 여유
  시점에만 성공 → 강남·종로 일부 셀 미수집(결론엔 영향 없음).

### 산출물
- 본 로그, `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(03 제외 확정 반영 —
  완료 목록 이동 + 진행 중 비움 + 감사표 갱신),
  `apps/ontology/_docs/03_semantic_segmentation_agent.md`(⛔ 제외 배너 + §5.4
  최종 확정) 갱신.

---

### [2] 어드민 dispatch/harvester 백엔드 인증 공백 차단

**배경**: PROGRESS 백로그 "어드민 백엔드 인증 공백" — `/api/v1/dispatch/*`·
`/api/ontology/harvester/*` 라우터에 `require_admin`이 없어 프론트 `AdminAuthGate`
우회 직접 호출 시 무인증 통과. `_ApiAuthMiddleware`는 `/docs`류만 막고 API
경로는 미들웨어 레벨 상시 공개임을 확인(인증은 라우터별 Depends로만).

**조사에서 드러난 것(구현 전 확인)**:
- 인증 스킴 2종 — auth 게이트웨이(RS256/roles/aud, `shared/security/token_verifier.py`)
  vs viewer 세션(HS256/role, `require_admin`). 어드민 UI가 실제로 보내는 건
  후자라 dispatch/harvester도 `require_admin`을 써야 일관.
- 어드민 UI의 dispatch/harvester 호출은 Next 프록시(`backendFetch`, Basic
  서비스 자격증명)를 거쳐 **사용자 세션 Bearer가 백엔드까지 안 감** → 백엔드
  가드만 추가하면 정상 호출도 401. 3계층 동시 수정 필요.
- import-linter: `require_admin`을 `core`가 아니라 "cross-app 토큰 검증 전용"
  리프 패키지 `shared`로 이동하는 게 계약(shared-independence)·구조에 맞음.
  실측 검증 결과 shared/spoke/auth 계약 모두 KEPT, 내 변경으로 인한 신규 위반
  0건(hub-independence BROKEN은 `core→viewer.orm` 기존 커플링, baseline 동일).

**수정·구현 (3계층)**:
1. 가드 이동: `viewer/dependencies/require_admin.py` → `shared/security/require_admin.py`
   (viewer 두 어드민 라우터 import 재지정, 원본 삭제).
2. 백엔드 가드 추가(어드민 UI 구동분만): dispatch `email/telegram/discord` POST(발송),
   `receive` GET·DELETE(수신함), ontology harvester `scrape/crawl/sites`. **`receive`
   POST(외부 인입)는 제외**.
3. 프론트 프록시 7개(`suvis/app/api/{dispatch,harvester}/*`)가 들어온 `Authorization`을
   `backendFetch`로 전달.
4. 프론트 클라 4개(mail/telegram/receive 페이지 + harvester-command-form)가 세션
   Bearer 첨부. `suvis/lib/suvis-session.ts`에 `authHeader()` 헬퍼 추가.

**검증**:
- import-linter(uv 일시 설치, PYTHONPATH=apps:.): 5 kept / 1 broken(기존) — baseline 동일.
- 백엔드 변경 파일 `py_compile` OK, 잔여 `viewer.dependencies.require_admin` 참조 0.
- 프론트 `npm run type-check` exit 0.
- 가드 런타임 실측: no-auth→401, 무효서명→401, 비관리자 role→403, 관리자→AdminPrincipal.

**남긴 것(후속 백로그)**: dispatch `watcher/judge/spam/adress` 라우터는 어드민 UI
미사용이라 이번 범위 밖. 각 엔드포인트가 외부 인입인지 개별 확인 후 보호 판단할 것
(검증 없이 가드 씌우지 말 것).

### 산출물 (2)
- BE: `shared/security/require_admin.py`(신규·이동), dispatch
  `email/telegram/discord/receive_router.py`, ontology `harvester_router.py`,
  viewer `admin_agents_router.py`·`admin_users_router.py`(import 재지정).
- FE: `suvis/app/api/{dispatch/email,dispatch/telegram,dispatch/discord,dispatch/receive,harvester/scrape,harvester/crawl,harvester/sites}/route.ts`,
  `suvis/app/admin/dispatch/{mail,telegram,receive}/page.tsx`,
  `suvis/app/admin/harvester/_components/harvester-command-form.tsx`,
  `suvis/lib/suvis-session.ts`.

---

### [3] alembic 마이그레이션 체인 누락 테이블 수정 + neo4j-graphrag 설치

**배경**: 사용자 보고 — 완전히 빈 DB에서 `alembic upgrade head`를 실행하면
`20260701_0001`에서 `relation "dispatch_adress" does not exist`로 실패.
지금까지는 backend startup의 `create_all()`이 테이블을 만들어줘서 드러나지
않았음. Google 로그인 500(새 DB에 `users`/`user_identities` 없음)도 같은
원인 의심.

**원인 조사**: `alembic/env.py`의 `target_metadata`(6개 Base) 대비 마이그레이션
체인의 `create_table` 호출을 전수 비교. `dispatch_adress`뿐 아니라 `users`,
`groups`, `admins`, mova 앱의 `movies`/`actors`/`characters`/`assistants`/
`collections`/`tags`/`chat`/`rankings`/`reviews`/`picks`/`watchlist`,
`titanic_passengers`, `vision_uploads`까지 전부 마이그레이션 체인에 CREATE가
없이 `create_all()`로만 존재해온 테이블이었음(alembic을 프로젝트 중간에
도입하면서 베이스라인 마이그레이션을 만든 적이 없었던 게 근본 원인).

**수정·구현**: 체인 맨 앞(20260604_0001보다 앞)에 베이스라인 마이그레이션
`20260604_0000_create_baseline_v1_tables.py` 신설, `20260604_0001`의
`down_revision`을 여기로 변경. 각 테이블은 뒤따르는 `41f584bfcb4e`(mova v2
스키마) 등이 적용되기 **직전 상태**로 생성하도록 설계(예: `movies.release_year`는
VARCHAR(8), `genres` 컬럼 존재, `characters.character_name` 없음,
`users.age_group` 있음) — 이후 리비전이 그 위에 그대로 ALTER 적용돼야 최종
스키마가 현재 ORM과 일치하기 때문. FK 의존 순서(groups→users→collections→
movies→actors→characters→assistants→tags→chat→rankings→reviews→picks→
watchlist) 고려해 테이블 순서 배치.

**검증**: 로컬엔 Docker/Postgres가 없어 EC2의 실제 `pgvector/pgvector:pg16`
이미지로 별도 테스트용 컨테이너(`suvisdev_migration_test_db`, 포트 15432,
기존 운영 DB 컨테이너와 별개)를 띄우고 SSH 터널로 연결. 백엔드 최소 venv
(`.venv_migration_test`, gitignore됨, sqlalchemy/alembic/psycopg/pgvector/
fastapi만 설치)로 완전히 빈 DB에 `alembic upgrade head` 실행 → 전체 10개
리비전 끝까지 성공, `alembic current`가 단일 head(`f3a7c9e21b6d`)로 확인.
`movies`/`users`/`characters`/`reviews` 최종 스키마를 `\d`로 대조해 현재
ORM과 일치 확인. 시행착오: `movies.release_year` VARCHAR→INTEGER 타입 변경
시 서버 디폴트(`''`)가 자동 캐스팅되지 않아 실패 → 베이스라인에서 해당
컬럼 디폴트를 제거해 해결.

**설계 의도(기존 배포 DB 영향 없음)**: 새 베이스라인은 체인의 새 루트로
삽입되므로, 이미 `alembic_version`이 어떤 리비전에든 스탬프돼 있는 기존
DB(운영 DB 포함)에는 적용되지 않음 — `None`에서 시작하는 완전히 빈 DB에만
적용된다.

**추가**: `requirements.txt`에 `neo4j-graphrag==1.18.0` 추가, 실제 백엔드
venv(`~/.venv`)에 설치·import 확인. `apps/silicon_valley/_docs/neo4j-hanress.md`에
그래프 데이터 모델 개념 + 연결 확인 절차(Python 드라이버/cypher-shell/브라우저)
문서화 — 실제 Neo4j 인스턴스는 아직 미배포(`.env`에 `NEO4J_PASSWORD`만 있고
`NEO4J_URI`/`NEO4J_USER` 없음, docker-compose에도 서비스 없음 확인).

### 산출물 (3)
- `suvisdev/alembic/versions/20260604_0000_create_baseline_v1_tables.py`(신규),
  `suvisdev/alembic/versions/20260604_0001_create_titanic_person_booking.py`(down_revision 변경),
  `suvisdev/requirements.txt`(neo4j-graphrag 추가),
  `suvisdev/apps/silicon_valley/_docs/neo4j-hanress.md`(신규).

---

---

### [4] PDF 업로드→추출→요약 파이프라인 (silicon_valley, **완료**)

**배경**: 사용자가 `neo4j-graphrag`의 `PdfLoader` 예시를 참조해 PDF 업로드→텍스트
추출→요약 파이프라인을 inbound router~outbound repository까지 완성형으로
요청. 헥사고날 컨벤션은 ontology `vision` 슬라이스(`vision_router.py` 등)를
그대로 참고.

**설계**: `pdf_summary_*` 네이밍. 포트 3개 — 추출(`PdfExtractorPort`, neo4j-graphrag
`PdfLoader` 어댑터), 요약(`PdfSummarizerPort`, 기존 `T1MidFakerOrchestrator`/exaone
Ollama 재사용), 저장(`PdfSummaryPort`, `NeoTheOneBase` + `get_mova_session_factory()`
— vision_uploads와 동일 패턴). `ensure_titanic_tables()` 같은 create_all() 폴백은
**의도적으로 안 씀**(오늘 [3]에서 고친 문제 재발 방지) — 대신 정식 alembic
마이그레이션(`20260727_0001_create_pdf_summaries`, head `f3a7c9e21b6d` 뒤에 추가)로
테이블 생성, `alembic/env.py`에 ORM import 등록 완료.

**완료된 파일**:
- `alembic/env.py`(pdf_summary_orm import 추가)
- `alembic/versions/20260727_0001_create_pdf_summaries.py`(신규 — 아직 미검증)
- `apps/silicon_valley/adapter/outbound/orm/pdf_summary_orm.py`
- `apps/silicon_valley/app/dtos/pdf_summary_dto.py`
- `apps/silicon_valley/app/ports/input/pdf_summary_use_case.py`
- `apps/silicon_valley/app/ports/output/pdf_summary_extractor_port.py`

**추가 완료된 파일**: `pdf_summary_summarizer_port.py`, `pdf_summary_repository_port.py`,
`app/use_case/pdf_summary_interactor.py`(자리표시자 `pdf_loader_interactor.py`는
삭제), `adapter/outbound/extractor/pdf_summary_pdfloader_extractor.py`(temp file로
`PdfLoader.run(filepath=Path)`에 전달), `adapter/outbound/llm/pdf_summary_ollama_summarizer.py`
(T1MidFakerOrchestrator 재사용, 입력 12000자 상한), `adapter/outbound/repositories/pdf_summary_repository.py`,
`adapter/inbound/api/v1/pdf_summary_router.py`(`POST /pdf/summarize`), `dependencies/pdf_summary_provider.py`,
`adapter/inbound/api/__init__.py`에 등록(최종 경로 `/api/v1/pdf/summarize`).

**검증**: `~/.venv`(neo4j-graphrag 포함)에서 라우터 import + `/pdf/summarize`
등록 확인, 마이그레이션 파일 `py_compile` OK, ORM 테이블 컬럼 확인. **미검증**:
실제 빈 DB에 `alembic upgrade head`(간단한 단일 create_table이라 위험 낮음,
필요시 EC2 임시 컨테이너로 재검증 가능), Ollama 서버 연동 실사용 테스트.

### 산출물 (4)
- 위 파일 전체. 커밋 전.

---

## 2026-07-24

### 작업 내용
- 06(Sentinel, 이상 탐지) **H4(추론 어댑터) + H5(HTTP API + MCP tool) 구현**
  — H3까지의 방향 전환(CLIP 제로샷 + Laplacian variance)을 실제 코드로
  반영하고 MCP tool까지 노출.
- **[1순위 백로그 해결] vision app→adapter DIP 위반 + 순환 import 근본 수정**
  — H6에서 드러난 순환(테스트만 우회 중)을 제거.
- **[2순위 (c)+(d)] S3 경로 Tank 단일화 + boto3 기본 자격증명 체인 전환.**
- **03(Loom, 분할) 이미지 수집 경로 조사 — 종료조건 합의(읽기 전용 분석).**
- 커밋 워크플로우 훅 설정 — 커밋 요청 시 두 추적 문서를 먼저 갱신하도록
  리마인더(공유용 `.claude/settings.json`, 커밋됨).

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

**3) 06 Sentinel H6 — `/vision/upload` 업로드 게이트 통합**
- 용도 확정(소거법): harvester=텍스트만 수집, TMDB=poster_url 참조(항상 포스터),
  lora-server=텍스트 생성기, Prisma(05)=미구현 → 이미지 입력이 불확실한 유일한
  경로가 `POST /vision/upload`라 여기에 게이트로 붙임(근거 추적은 이 세션 대화).
- `app/dtos/vision_dto.py`: `VisionUploadResponse`에 `poster_confidence`/
  `sharpness_score`/`is_poster_warning` 추가(기본값 있어 repo 무변경).
- `app/use_cases/vision_interactor.py`: `AnomalyDetectionPort` 주입,
  `upload_image`가 `to_thread`로 detect → 블러 하드 게이트(임계값 345.77 미달
  `ValueError`→400) + 포스터 소프트 플래그(`poster_confidence`<0.5 경고, 차단 안
  함). 임계값을 interactor가 raw 값으로 소유(어댑터 부울은 /sentinel·MCP용).
- `dependencies/vision_provider.py`: `get_anomaly_detection_port` 재사용 주입.
- 검증: `test/test_vision_upload_sentinel_gate.py`(gpu, fake VisionPort+실제
  Sentinel) 3경로 PASSED — good(통과+저장), blur(하드 반려+미저장),
  cast_0001(소프트 플래그+저장). 앱 import 무결성(`main` 7 vision routes) 확인,
  VRAM 3034→3034 안정.
- 동기 지연(~20s CLIP 로드)·VRAM 경합은 감수(어드민 간헐 경로, to_thread, CLIP
  경량) — 근거 `06 §6.9`.

**4) AWS S3 매니저(Tank) 신설** — 향후 AWS 이전(이미지/객체를 S3 URL로
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

**5) [1순위 백로그] vision app→adapter DIP 위반 + 순환 import 근본 수정**
- 위반: `app/ports/input/vision_use_case.py`·`app/use_cases/vision_interactor.py`가
  어댑터 pydantic 스키마 `VisionIntroduceSchema`를 인자 타입으로 임포트 →
  `vision_use_case→vision_schema→api/__init__→vision_router→vision_use_case` 순환.
- 수정: 포트·interactor를 앱 DTO `VisionIntroduceQuery`(이미 존재, repository 포트도
  이걸 받음)로 바꾸고, schema→query 변환을 어댑터 계층(`vision_router`)으로 올림.
  interactor는 query를 repository로 직행(변환 제거). dead가 된 `vision_schema.py`
  삭제(`schemas/__init__` 빔, 다른 참조 없음 확인).
- H6 테스트에서 넣었던 우회(`import ontology.adapter.inbound.api` 선로드) 제거 —
  이게 통과한다는 게 근본 해결의 증거(테스트 로드 경로 = 프로덕션 경로).
- 검증: 이전에 순환으로 실패하던 `import ontology.dependencies.vision_provider`가
  성공, `from main import app` 부팅(vision routes 7), H6 게이트 3/3 PASSED(우회 없이).
- semantic_router_dto도 어댑터 스키마 참조하나 `TYPE_CHECKING`/지역 임포트라 런타임
  순환 없음 → 이번 범위 밖(DIP 냄새만, 위험 아님).

**6) [2순위 백로그 (c)+(d)] S3 경로 Tank로 단일화 + 기본 자격증명 체인 전환**
- 배경: `VisionS3Repository`가 자체 `boto3.client`(기본 체인), Tank는 명시적 키
  전달 — S3 경로가 둘로 갈리고 자격증명 전략도 반대. 사용자 결정: (c)+(d) 함께,
  기본 체인으로 통일.
- Tank(d): `_access_key`/`_secret_key`/`ready`/키 전달 제거 →
  `boto3.client("s3", region_name=...)`만 사용(기본 체인). region/bucket은 계속
  Keymaker에서. boto3 기본 체인이 로컬은 `.env`가 os.environ에 실은 AWS_* env를,
  EC2는 인스턴스 IAM Role을 집는다 → 단일 경로.
- VisionS3Repository(c): 자체 boto3/os 제거, `get_tank()` 위임. 키 네이밍·
  content_type만 도메인 로직으로 남기고 put은 `tank.upload_bytes`(to_thread).
- Keymaker: `aws_access_key_id`/`secret` 속성은 vestigial(아무도 안 읽음, 기본
  체인이 env 직접 집음)로 남김 + 주석 정정. `.env.example`에 EC2 IAM Role이면
  키 비워도 된다는 노트 추가.
- 검증: `tank.client`가 명시적 키 없이 S3 클라이언트 빌드(전엔 ready=False로
  raise), `VisionS3Repository`가 Tank 싱글턴에 위임(save_image→Tank 버킷 체크
  RuntimeError 도달로 위임 경로 증명), `from main import app` 부팅 OK. 실 업로드는
  AWS 연결(버킷+키) 후 확인.

**7) 03(Loom, 분할) 이미지 수집 경로 조사 — 종료조건 합의(코드 변경 없음, 읽기 전용)**
착수 전 종료조건부터 합의하기로 하고 03 문서(§5)·gildle 라우팅 코드
(`route_weight_calculator.py`)를 읽어 3가지를 정리:
- **용도/소비처**: 재정의 스코프는 "보도 유무/폭"(계절 무관 구조 신호, 결빙은
  §5.1에서 기각). 소비처는 실재 — `RouteWeightCalculator.calculate_edge_weight`가
  `_near_hazard`(20m 근접→6배 페널티) 패턴처럼 "보도 없음/좁음"을 상시 페널티로
  얹으면 됨. **단 구멍 2개**: (a) 소비 그래프가 데모(`sample_walk_graph.json` 4간선),
  OSM 운영 미구현(코드에 osmnx 없음 확인). (b) OSM walk 태그가 보도를 이미 주면
  CV 불필요(중복). → "용도 없음"이 아니라 "CV가 필수 수단이 아닐 수 있음".
- **이미지 최소 조건**: 지상 스트리트뷰(항공 아님 — 가로수 canopy 폐색), 유효크롭
  ≥512px, 지오태그 정밀도 ≤~10~20m(간선 매칭 반경), 주간·비폐색(구조라 계절 무관,
  단 적설 배제), **커버리지=라우팅 그래프 전 간선(킬러 조건)**. 실질 판정 기준은
  해상도가 아니라 커버리지×합법성×비용.
- **폐기 수용**: 04·08 제외 선례와 동급으로 '폐기'를 정식 결론으로 수용하기로 제안
  (쓸 소스 없음 / OSM으로 충분함 둘 다 유효 종료).
- **합의한 관문 순서**: 관문0(OSM 보도 태깅으로 CV 불필요한지, 가장 쌈, 먼저) →
  관문1(스트리트뷰 소스 ToS/과금/커버리지) → GO는 둘 다 통과+최소조건 만족 시만.
- **상태**: 사용자 종료조건 합의 대기 → 합의되면 관문0부터 착수(아직 소스 조사 미착수).

**8) 커밋 워크플로우 훅 설정**
- 규칙 확정: 커밋 **요청 시** WORK_LOG(오늘 작업)·PROGRESS(완료 삭제·남은 작업)를
  **먼저 갱신 후** 문서+코드 함께 커밋(커밋 후 갱신은 순서가 거꾸로라 폐기).
- `.claude/settings.json`(공유용, 커밋됨)에 `UserPromptSubmit` 훅 — 프롬프트에
  `commit|커밋` 있으면 문서 먼저 갱신 리마인더 주입. grep 기반(호스트에 jq 없음).
  개인 permissions는 `.claude/settings.local.json`(전역 gitignore)에 유지.
- 검증: python3로 두 파일 JSON 유효성·훅 매칭/비매칭 재현, 이번 세션에서 실제
  발화 확인(이 프롬프트에 리마인더 주입됨).

### 오류·막힌 점
- **로컬 `.venv`/`.venv-exaone`에 pytest/opencv 없음** — 이 프로젝트의 실제
  런타임 의존성(`transformers==4.47.1`, `opencv-python`, `pytest`)은
  `requirements.txt` 기반으로 `suvisdev-backend-1` 도커 이미지에만 있고,
  compose에는 코드 전체가 아니라 `datasets`·`resources/crawled`만 바인드
  마운트돼 있어 새 파일이 컨테이너에 자동 반영 안 됨 → `docker cp`로
  변경/신규 파일 6개를 컨테이너에 직접 복사해 그 안에서 pytest 실행,
  둘 다 PASSED. VRAM은 호출 전후 2879MB로 동일(로드-언로드 정상 확인),
  lora-server(`:8200/health`) 정상 유지.
- **기존 순환 임포트 노출(H6 테스트)** — `app/ports/input/vision_use_case.py`가
  어댑터 계층 `adapter/inbound/api/schemas/vision_schema.py`를 임포트(app→adapter
  DIP 위반)해서, `vision_interactor`를 `api/__init__` 애그리게이터보다 먼저
  임포트하면 `vision_use_case → vision_schema → api/__init__ → vision_router →
  vision_use_case(partial)` 순환이 터진다. 프로덕션은 `main.py` 임포트 순서
  덕에 회피 중(앱 import 무결성 확인함). H6 테스트는 `api` 애그리게이터를 선
  로드해 우회. **근본 수정(포트가 어댑터 스키마를 안 보게)은 백로그 — 아래.**

### 산출물
- 문서 갱신: `apps/ontology/_docs/06_anomaly_detection_agent.md` §6.7(H4)·
  §6.8(H5)·§6.9(H6) 신규, `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 06을 H0~H6
  완료로 갱신(완료 목록 이동, 감사표·우선순위 반영).
- 백엔드 이미지 리빌드(H5 코드 반영) — `suvisdev-backend-1` 재기동됨.
- 커밋/푸시/머지(모두 main 반영): Sentinel H4·H5 `df5a56b`, S3 매니저(Tank)
  `53bd4de`, Sentinel H6 `2da0762`, 블러 상수 주석+백로그 `e91d9c7`, Keymaker
  계약+시크릿 감사 `9994ed7`, vision DIP 순환 수정 `6098955`, S3 Tank 단일화+
  기본 체인 `dc9afbd`, 03 조사 기록+진행 메모 프루닝 `b8628bb`, 커밋 워크플로우
  훅(.claude/settings.json)+WORK_LOG(이 커밋).

### 백로그 (우선순위 조정 — 2026-07-24)

**[1순위] app→adapter DIP 위반 + 순환 import — ✅ 해결(2026-07-24, 위 수정/구현 5)**
- `vision_use_case`/`vision_interactor`가 어댑터 스키마 `VisionIntroduceSchema`를
  받던 것을 앱 DTO `VisionIntroduceQuery`로 교체, 변환을 `vision_router`로 올림,
  dead `vision_schema.py` 삭제. 테스트 우회 제거 후에도 통과 = 근본 해결.

**[2순위] 시크릿·S3 접근 경로 정리 (묶음)**

시크릿 관리 현황 감사 결과, Keymaker(`vauly_keymaker`)는 단일 관문이 아니라
여러 시크릿 접근 경로 중 하나였다(GEMINI/TMDB/KOFIC/AWS/DATABASE_URL만 관리,
나머지 JWT·OAuth·API_USERNAME 등은 각 app이 `os.getenv`로 직접 읽음).

**방향 결정 — Keymaker 전면 통합은 채택 안 함.** core/matrix가 TMDB_API_KEY·
JWT 키 같은 앱별 시크릿을 알게 되면 core → apps 역방향 의존이 생겨 헥사고날
원칙에 어긋난다. 나중에 정리한다면 core는 `SecretProvider` 인터페이스(메커니즘)
만 갖고, 키 목록은 각 app의 Settings가 소유하는 방향으로 간다.

- (a) TMDB/KOFIC 코드 중복(ontology `api_keys.py` / mova `keymaker.tmdb_api_key`):
  둘 다 같은 env 이름을 읽어 **값 divergence 위험 없음(상태 중복 아니라 코드
  중복)**, 앱별로 하나씩 가진 건 "app이 자기 키를 소유" 목표 방향과 오히려 일치.
  지금 mova에 accessor를 신설하면 pydantic-settings 이관 때 또 뜯게 됨 →
  **app별 Settings(pydantic-settings) 도입 시 mova·ontology 키 접근을 함께 이관.
  현재는 무해. 단독 실행 금지.**
- (b) `load_dotenv` 3곳 감사 완료(2026-07-24): **세 곳 모두 같은 파일**
  (`suvisdev/.env`) 로드 — vauly_keymaker·grid_oracle는 `override=True`,
  alembic/env.py는 `override=False`. 파일이 같아 값 분기는 없으나 override
  플래그가 불일치. **단일화 안 함** — Keymaker의 임포트 시 self-load는 scripts/를
  떠받치는 **기능(계약)**이라 제거 대상 아님(Keymaker docstring에 계약 명시함).
  override 불일치는 인지만 하고 현행 유지.
- (c)+(d) **✅ 해결(2026-07-24, 위 수정/구현 6)**: S3 경로를 Tank로 단일화 +
  Tank를 boto3 기본 자격증명 체인으로 전환. `VisionS3Repository`가 자체
  `boto3.client`를 버리고 Tank에 위임, Tank는 명시적 키 전달을 제거하고
  `region_name`만 지정 → 로컬(.env 키)·EC2(IAM Role)가 단일 경로로 처리됨.

**[유지] 하위 우선순위**
- 블러 임계값(345.77)은 포스터 분포 보정값이라 저디테일 비포스터(backdrop 등)가
  미달해 하드 반려될 수 있음 — 업로드 게이트 용도상 허용(현행 유지).
- Sentinel 소프트 플래그의 **저장 지속화 + 어드민 오버라이드 엔드포인트** — 저장
  계층(S3 배선인데 AWS 미연결, DB 폴백 미배선) 정리 후 처리(현행 유지).

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
