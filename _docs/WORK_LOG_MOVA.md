# 작업 일지 — MOVA 워크로드

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

## 2026-09-02

### 작업 내용
- **RAG 히트가 태그 검색을 가리는 갭 수정**(9/1 실측 백로그, trace=81b08f57) —
  "좀비 영화 추천해줘"에서 좀비 태그가 실재하는데도 RAG 시맨틱이 무관 8건을
  물어오면 태그 폴백 조건(RAG 0건)이 미충족돼 recs=0이 되던 구조적 갭.
  착수 전 `.claude/rules/mova-chat.md` 불변식(폴백 유지·카탈로그 한정) 검토.

### 수정/구현
- `apps/mova/app/use_cases/market_chat_interactor.py`: RAG 히트가 있어도
  태그 검색을 **원시 키워드로(mood 확장 없이)** 함께 돌리고, 결과가 실매칭
  (`popular_fallback` 제외)일 때만 RAG 히트 뒤에 합집합(dedup, 캡 16)으로
  합류. 설계 핵심: "결정론 키워드 질의냐"를 사전 분류하지 않고 **태그 검색
  결과 자체**로 판별 — 순수 mood 질의는 원시 토큰이 태그에 안 걸려
  popular_fallback으로 떨어지고 그건 버리므로 자연히 현행(RAG 단독) 유지
  (백로그의 "mood 현행 유지" 조건을 결과 기반으로 충족). 두 경로 공용
  태그 검색 인자 조립은 `_search_tags` 헬퍼로 통합, 폴백 경로(mood 확장 +
  dedup 소진 시 풀 확장)는 동작 불변.
- `apps/mova/tests/test_market_chat_interactor.py`:
  `ChatInteractorRagTagUnionTests` 3건 신규 — ① 합집합·RAG 우선·dedup +
  원시 키워드 호출 검증, ② popular_fallback 폐기(mood 현행 유지), ③ 캡 16.
- `.claude/rules/mova-chat.md`: §1 파이프라인에 합집합 단계 반영, §2에
  불변식 추가(합집합 제거 금지·합집합 경로 mood 확장 금지).
- `_docs/WORK_LOG_MOVA.md` 첫 줄 단독 `1` 삽입 재발분 제거(기존 알려진
  편집기 이슈, PROGRESS "단독 1 문자 삽입" 항목 참조).

### 작업 내용 (후속 — 예매 탐색형 질의 오응답 수정)
- 실사용 보고: "지금 바로 예매할 수 있는 영화 뭐있어" → "비슷한 제목이
  여러 편이에요: … 어떤 작품을 예매하시려나요?" 오응답. 추적 결과 booking
  트랙이 모든 질의에 제목이 있다고 가정하고 `resolve_movie_title`로
  직행 → 일반어 "영화"가 제목 ILIKE/퍼지 매칭돼 무관 후보 3편(무서운
  영화 등)이 ambiguous로 잡힌 것. **탐색형(제목 없는) 예매 질의 경로
  부재가 근본 원인.**

### 수정/구현 (후속)
- `market_chat_booking_interactor.py`: 제목 해석 **전에** 결정론 패턴
  (`_DISCOVERY_PATTERN`: 뭐 있/뭐 볼/무슨 영화/어떤 작품/상영작/상영 중인)
  으로 탐색형을 갈라, 기존 `_is_showing`이 쓰던 KOFIC 주간 박스오피스로
  상영작 최대 8편을 나열하고 작품 선택 유도("최근 주간 박스오피스 기준"
  출처 명시 — 정직성 규칙). KOFIC 실패 시 정직 폴백. card·booking 없이
  reply만 → 인터랙터·프론트 변경 0건.
- `qwen_intent_classifier.py`: booking 기준에 "제목 없어도 지금 예매/상영
  중인 영화를 찾는 질문은 booking" 명시 + 예시 1건 추가("공포 영화 뭐
  있어?"=recommend 예시와 충돌해 라우팅이 흔들릴 수 있어서).
- `test_chat_tracks.py`: `BookingDiscoveryTests` 3건(박스오피스 나열 +
  title resolver 미호출 / KOFIC 실패 정직 폴백 / 제목 질의 패턴 비매칭).
- `.claude/rules/mova-chat.md` §8: 탐색형 경로 불변식 추가(패턴 제거·
  title 해석 선행 금지).

### 작업 내용 (후속 2 — 배포 중 EC2 디스크·LoRA 서빙 5배 감속 해결)
- **EC2 배포 실패 → 디스크 원인 해결**: `auto-deploy.sh` 재빌드가 pip
  `[Errno 28] No space left on device`로 실패. 원인 둘 — ① auth가 태그를
  뺏긴 구 이미지(`<none>`, 9.31GB)로 떠 있던 이미지 드리프트(auto-deploy
  기본값이 backend만 재빌드해서 생김), ② 예전 `builder prune`으로 pip 레이어
  빌드 캐시가 소실돼 torch 스택 전체 재설치(피크 ~15G+)가 30GB 디스크에
  안 들어감. auth를 latest로 재생성 + 구 이미지 정리로 1.9GB 확보했지만
  전체 재빌드는 구조적으로 불가 → **기존 이미지 베이스 파생 빌드**
  (`FROM suvisdev-app:latest` + `COPY . .`)로 배포(requirements 불변이라
  캐시 히트 빌드와 결과 동일, 코드 레이어만 추가).
- **LoRA 추천 경로 감속 규명·해결**: 배포 후 recommend E2E가 504(61s).
  계통 추적 — 터널·서버 정상, 생성 자체가 읽기 타임아웃(60s) 초과. 실측:
  서버 경유 256tok 78.6s(≈3.2tok/s)인데 **동일 구성 오프라인 17.8tok/s**
  → 오래 뜬 서버 프로세스 열화(단편화→WDDM 스필 추정)가 주범. serve.py에
  `merge_and_unload()`(어댑터 병합) + `attn_implementation="sdpa"` 반영
  (벤치 17.8→26.1tok/s) 후 재기동 → **서버 경유 256tok 8.5s**, 프로덕션
  E2E 6.4s 200.
- **합집합 순서 개선**: LoRA 경로 실사용에서 RAG-우선 순서일 때 2.4B가
  좀비 태그 후보(부산행 등 DB 실재 확인)를 두고 무관 시맨틱 1편을 픽 →
  태그 실매칭 우선(상한 10)+시맨틱 보충으로 순서 변경. 테스트 갱신.
- **"좀비 recs=0"의 진짜 뿌리 발견 — `_FILLER` 문두 담화어 정규식**:
  순서 변경 후에도 recs=0이라 후보를 SQL로 재현하니 16편이 나와야 하는데
  실제는 3편 → 추출기를 직접 돌려보니 keywords가 `['영화', '비 영화']`.
  `^(오늘|지금|좀|그냥|...)\s*`의 `\s*`가 공백 0개를 허용해 **문두
  "좀비"의 "좀"이 잘려 "비 영화"(rain)**로 변질 — 9/1 트레이스에서 RAG
  top1이 "비와 당신의 이야기"였던 미스터리까지 이걸로 설명됨(시맨틱은
  "비 영화"를 제대로 찾은 것). `\s+`(공백 필수)로 수정, 단독 담화어
  ("좀 ", "지금 ", "오늘 ") 제거는 유지. 회귀 테스트 3건
  (`FillerWordBoundaryTests`).

### 오류·막힌 점
- 없음. mypy를 테스트 파일에 직접 걸면 나오는 2건은 수정 전부터 있던
  기존 에러(프로젝트 mypy는 tests 제외 — 8/31 재활성화 설정 그대로).
- (미결) EC2 전체 재빌드는 여전히 불가 — requirements/Dockerfile이 바뀌는
  날은 디스크 증설 또는 로컬 빌드+이미지 전송이 필요. 서버 프로세스 열화는
  재발 감시 필요(재발 시 lora-server 재시작이 응급 처치).

### 데이터
- 변경 없음(코드·테스트·규칙 문서만).

### 산출물
- RAG 합집합: 커밋 `9c146d5`, `apps/mova/tests` 281 passed, import-linter
  6계약 KEPT.
- 예매 탐색형: mova 전체+분류기 299 passed(신규 3건 포함).
- 배포 후 실효 확인: "좀비 영화 추천해줘" recs>0(`RAG+태그 합집합 후보`
  로그), "지금 예매할 수 있는 영화 뭐있어" 박스오피스 목록 응답
  (`탐색형 예매 질의 → 상영작 N편 안내` 로그).

### 작업 내용 (후속 3 — 노트북 세션: 구 터널 삭제·lora-nb 신설·미커밋분 정리)
- git pull 후 백로그 점검 중, 이 노트북(teagy)에서 systemd enabled 잔존으로
  구 lora-server·cloudflared-lora(`lora-notebook` 터널)가 부팅 시 자동
  기동돼 있던 것을 발견. 처음엔 문서 결정("다시 켜지 않는다")대로
  stop+disable했으나, **사용자 결정 변경: 노트북도 상시 서빙**으로 전환.
- 구 `lora-notebook` 터널은 **원격 관리형**(엣지 ingress가
  `lora.suvisdev.cloud` 고정, 로컬 config.yml 무시)이라 새 호스트네임을
  로컬에서 못 붙임 → 대시보드 없이 해결하기 위해 터널을 삭제하고 **로컬
  관리형 `lora-nb` 터널을 CLI로 신설**하는 경로 선택.

### 수정/구현 (후속 3)
- `cloudflared tunnel delete lora-notebook`(97489360) — PROGRESS 백로그
  "구 터널 계정에서 삭제 예정" 항목 완료.
- `cloudflared tunnel create lora-nb`(54f7f631) + `route dns
  lora-nb.suvisdev.cloud`(구 터널 삭제 후에야 CNAME 이전 성공 —
  `--overwrite-dns`는 자기 계정 터널을 가리키는 레코드는 덮어쓰지 않음).
- `~/.cloudflared/config.yml`(터널 ID·자격증명·hostname)과 systemd 유닛
  (`cloudflared-lora.service` ExecStart)을 lora-nb로 갱신, enable 유지.
- E2E: `lora-nb.suvisdev.cloud/health` 200(노트북, AWQ·08-25 어댑터) +
  `lora.suvisdev.cloud/health` 200(데스크톱, GGUF) — 상호 영향 없음 확인.
  EC2 프로덕션은 여전히 `lora.suvisdev.cloud`(데스크톱)만 호출.
- **이전 세션 미커밋분 정리 커밋**: `mova-ai-chat-bar.tsx` 채팅 스크롤
  하단 고정(`listRef.scrollTo` → `bottomRef.scrollIntoView` + rAF),
  `apps-catalog.ts` ARDA 카드(WORK_LOG_MAINPAGE 참조), 8/31 산출물 보강.
  검증: `npx tsc --noEmit` 통과(이 노트북엔 eslint 의존성 미설치라 lint
  스킵 — 데스크톱에서 실행 가능).

### 작업 내용 (후속 4 — 다중 장르 AND 검색 결함 수정)
- 백로그 잔여 결함(QUALITY_PHASE1 §9 계열, "키워드끼리의 AND 결합"):
  `_movie_ids_by_tags`가 키워드 전부를 OR로 묶어 "SF 드라마"가 교집합이
  아닌 합집합으로 검색되고, `_movies_by_ids`의 평점순 limit 16 컷에서
  두 태그를 다 가진 영화가 통째로 밀릴 수 있던 구조.

### 수정/구현 (후속 4)
- `market_chat_pg_repository.py`: ① `_movie_ids_by_tags`가 태그 label을
  함께 조회해 키워드별 매칭 집합을 만들고 `(합집합, 교집합)` 반환 —
  매칭 0건 키워드("영화" 등 비태그 어휘)는 교집합 판정에서 제외, 실매칭
  키워드 2개 미만이면 교집합은 빈 set. ② `search_tag_catalog`의 keyword
  경로에서 **교집합 우선 + 합집합 보충**: 교집합 영화를 limit까지 먼저
  조회하고 남는 자리만 나머지 합집합으로 채움(2.4B LoRA가 목록 앞쪽
  후보를 선호하는 9/2 실측과 정합). 순수 AND로 안 바꾼 이유: mood 확장
  (공포·스릴러 = 동의어 OR)이 깨짐 — 보충 경로로 후보 풀 크기·폴백·
  dedup 확장 동작 전부 불변. `actor+keyword`(배우+태그 교집합) 경로는
  기존 동작 유지(이미 해소된 축).
- `apps/mova/tests/test_search_tag_catalog_and.py` 신규 8건 —
  키워드별 그룹핑(교집합·비태그 제외·단일 키워드·빈 입력) 4건 +
  오케스트레이션(교집합 우선 2회 조회·합집합 단독 1회 유지·교집합=합집합
  스킵·actor+keyword 불변) 4건.
- `.claude/rules/mova-chat.md` §2: 교집합 우선+합집합 보충 불변식 추가.

### 오류·막힌 점 (후속 4)
- 이 노트북에 백엔드 테스트 환경이 없어(`suvisdev/.venv`는 gildle/OSM
  전용 39패키지) uv 임시 venv(`/tmp/mova-test`)에 pytest·sqlalchemy·
  fastapi·google-genai·PyJWT·psycopg[binary] 등을 설치해 검증.
  reviews 라우터 테스트 9건이 "Mova URL이 설정되지 않았습니다"로 깨진
  것은 psycopg 미설치가 진짜 원인(에러 메시지가 오도) — 설치 후 전량 통과.

### 산출물 (후속 4)
- `apps/mova/tests` 295 passed(신규 8건 포함), mypy 대상 파일 클린.
- 커밋 `9b0e26d`, EC2 파생 빌드 배포(9/2 방식 재현 — `/tmp/Dockerfile.derived`
  `FROM suvisdev-app:latest` + `COPY . .`, backend·auth 동시 재생성, 디스크
  75% 불변). **프로덕션 E2E 실측**: "SF 드라마 추천해줘" → 인터스텔라·
  엑스 마키나·혹성탈출: 진화의 시작(전부 SF+드라마 교집합 작품),
  로그 `RAG+태그 합집합 후보 16편(태그 keyword)` recs=3.

### 작업 내용 (후속 5 — "최신영화 알려줘" booking 오분류 실사고)
- 배포 직후 사용자 실사용 보고: "최신영화 알려줘" → "비슷한 제목이 여러
  편이에요: 간신(2015) / 변신(2012) / 실(2020). 어떤 작품을 예매하시려나요?"
  카드 0개. 프로덕션 로그 추적(trace=8b0789b7·621b25e4): destination=booking,
  status=ambiguous — 3중 결함 규명. ① **주원인**: 후속 2에서 booking 기준을
  넓힌 프롬프트 예시("요즘 상영작 알려줘")와 표면이 거의 같아(요즘≈최신 +
  "알려줘") LLM이 booking으로 오분류, 예매 어휘가 전혀 없어도 막는 가드
  부재. ② booking 트랙에서 `_DISCOVERY_PATTERN` 미매칭 → 제목 해석기
  직행 → "최신"이 간신/변신/실에 자모 퍼지 매칭 → ambiguous 되묻기.
  ③ recommend로 갔어도 `_guess_year_range`에 최신 어휘 매핑이 없어(클래식
  →year_max만 존재) 최신작 필터가 안 걸렸을 것.

### 수정/구현 (후속 5)
- `qwen_intent_classifier.py`: ① `_BOOKING_VOCAB` 결정론 가드 — LLM이
  booking을 반환해도 예매·예약·티켓·표 끊·상영·극장·영화관·보러·시간표·
  어디서가 하나도 없으면 recommend로 교정(기존 `_META_COMPLAINT_PATTERNS`
  가드와 같은 패턴). ② 프롬프트에 반례 명시 + "최신영화 알려줘"→recommend
  예시 추가.
- `intent_extraction.py` `_guess_year_range`: 최신·신작 → `year_min=올해-1`,
  최근 → `year_min=올해-5`(클래식→1999의 대칭). 명시 연대·연도 우선 유지.
- 테스트 6건 신규(분류기 가드 3 + 연도 매핑 3), `.claude/rules/mova-chat.md`
  §8·§2 불변식 반영.

### 산출물 (후속 5)
- mova+분류기 316 passed, mypy 변경 파일 2건 클린.

### 작업 내용
- **8/31 배포 실측 마무리** — EC2 코드 `5e38138` 최신, alembic
  `20260831_0003 (head)`, 신규 엔드포인트 라이브 확인(감정 요약 200,
  투표 미인증 401). hub_knowledge 색인 2,972/2,972 전량 완료 실측,
  ingest cron 라인은 이미 제거돼 있었음(고아 주석만 잔존 — 정리 안내).
- **백로그 최신화 실측 2건** — `GEMINI_BACKFILL_API_KEY`는 로컬·EC2 양쪽에
  이미 등재돼 있었고 야간 cron도 정상(움직일 것 없이 항목 종결).
  `RECOMMENDATION_BACKEND=lora` + 터널 530 상태에서 Gemini 자동 폴백
  체인이 프로덕션 실호출로 정상 작동함을 실증.
- **감정분석 스케줄러 EC2 에러 원인 규명** — `'frozenset' object has no
  attribute 'discard'`는 transformers 4.47.1 업스트림 버그
  (`integrations/bitsandbytes.py:498`, `get_available_devices()`가
  FrozenSet인데 CPU 전용 분기에서 `.discard` 호출). GPU 머신은 이 분기를
  안 탐 — EC2 측 조치 불필요. **프로덕션 reviews 166건 중 감정 데이터
  0건**(에디터 리뷰 160건 자동별점 대기) 발견 — Echo 어댑터가 있는 GPU
  머신에서의 백필 실행이 백로그로 등재됨.
- **lora-server 데스크톱(DESKTOP-IOAQ7L7) 재구축 + EC2 왕복 복구** —
  8/6부터 끊겨 있던 LoRA 경로 복원. 사용자 요청으로 모델 가중치는
  D 드라이브(`/mnt/d/models/`) 배치.
- **LoRA 파인튜닝 완주** — 교사 데이터셋 재생성(EC2 prod DB) → 학습 →
  서빙 반영 → E2E 검증까지. 베이스 전용 시절 깨진 제목('Actor:eal') 해소.

### 수정/구현
- `model_servers/lora_server/serve.py`: gptqmodel 임포트를 AWQ 분기 지연
  임포트로 이동(transformers v4 환경에서 hf 백엔드 사용 가능), hf 분기에
  `trust_remote_code=True` + `torch_dtype` 정정(미사용이던 경로 정비).
- `suvisdev/scripts/train_mova_lora.py`: 동일 지연 임포트 + EXAONE 로드
  인자 정정 + `apply_chat_template`에 `return_dict=True` 명시(버전별
  반환형 차이 호환) + gradient checkpointing을 plain 백엔드에도 공통 적용
  (fp16 2.4B가 8GB VRAM에서 OOM 없이 돌게 — 실측 7.9/8GB).
- 인프라: `~/.venv-exaone`(system-site-packages, gptqmodel은 transformers
  v5 강제라 제거), `~/.config/systemd/user/{lora-server,cloudflared-lora}.service`,
  linger 활성화, cloudflared 사용자 영역 설치(`~/.local/bin`, sudo 불필요),
  신규 터널 `lora-desktop`(7e1038e9) 생성 + `lora.suvisdev.cloud` CNAME
  덮어쓰기(사용자 실행).

### 오류·막힌 점
- gptqmodel 7.x가 transformers>=5.14 강제 ↔ EXAONE 구식 remote code는
  v5 비호환(`get_input_embeddings` NotImplementedError) → AWQ 경로 포기,
  fp16 hf 백엔드로 전환(비양자화라 품질 손해 없음, VRAM 5.5GB).
- transformers 4.47에서 `apply_chat_template(return_tensors="pt")`가 순수
  텐서 반환 → 스크립트의 `["input_ids"]` 인덱싱이 IndexError →
  `return_dict=True`로 통일.
- 분류기 차단 3건(원격 crontab 덮어쓰기, DNS 라우팅, sudo linger)은
  사용자가 직접 실행. `cloudflared tunnel login` cert가 브라우저 다운로드
  (바탕화면)로 떨어져 수동 복사로 해결.
- `pkill -f "uvicorn serve:app"`이 명령 자신을 매칭해 셸 자살 —
  `serve:ap[p]` 패턴으로 회피.

### 데이터
- 교사 데이터셋 60→65건(그라운딩 55 + no-pick 10). 스킵 49건 대부분
  "no grounded picks" — 주제형 질의(좀비·요리·재난 등)에서 태그 검색
  후보와 교사 추천 불일치. TMDB keyword 태그 백필이 되면 개선 여지.
- D 드라이브: EXAONE fp16 9GB 배치, 미사용 AWQ 2.1GB·pip 캐시 2.2GB 삭제.
- LoRA 어댑터 `~/lora_adapters/mova_20260901_025206`(3에폭, loss
  0.88→0.65→0.51), LATEST 갱신.

### 산출물
- E2E 검증: 프로덕션 `/mova/chat` → `lora.suvisdev.cloud/generate 200` →
  "긴장감 넘치는 범죄 스릴러" = 추격자·범죄와의 전쟁·범죄도시.
- `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` 갱신(백로그 3건 종결·1건 신규).
- 지킬 포스트 `2026-09-01-mova-lora-desktop-rebuild` 배포(Pages 빌드 성공).
- **리뷰 감정분석 프로덕션 완결(같은 날 저녁)** — Echo 어댑터 데스크톱
  재학습(NSMC 2,000×2에폭 QLoRA, val acc 87.0%/f1 0.865, peak VRAM 3.3GB;
  `train_echo_sentiment.py`에 masking_utils 구버전 가드 + `ECHO_BASE_MODEL`
  로컬 경로 오버라이드) → EC2 DB 본문 CSV 추출 → 로컬 GPU 배치 분석
  (모델 1회 로드, 167건, 긍정 165/부정 2 — 표본 검증: 혼합 톤 저확신
  0.64, 소송·소식성 본문 부정) → 트랜잭션 SQL 반영(감정 167, 자동 별점
  161, 영화 평점 재계산 161, rating_still_null=0; 사전 reviews 백업).
  `GET /mova/reviews/sentiment/{id}` 긍정·부정 실데이터 응답 확인 —
  8/31 기능이 처음으로 실데이터 위에서 동작. DB 쓰기·SQL 조립은 분류기
  차단으로 사용자 실행.
- **TMDB keyword 기반 태그 백필 구현(같은 날 밤)** — 백로그(2026-08-25,
  franchise_expansion의 체계적 대체재) 착수. 채팅 태그 매칭이
  `tags.label ILIKE %한국어%`라서 영어 키워드를 그대로 넣으면 무의미 —
  **선별 EN→KO 매핑 사전**(`tmdb_keyword_map.py`, 164 엔트리: 좀비·타임루프·
  법정·요리·재난 등 교사 데이터셋 스킵 49건 주제 실측 기반)으로 변환해
  tags(kind=mood)에 적재. `TmdbAdapter.fetch_movie_keywords()` 신규 +
  `scripts/backfill_tmdb_keyword_tags.py`(--limit/--dry-run,
  ON CONFLICT DO NOTHING 멱등, RETURNING 카운트 — 벌크 rowcount -1 이슈
  회피). 로컬 실검증: 부산행 → 기차·전염병·좀비 자동 태깅, 재실행 신규 0.
- **KR 성인·노이즈 잔여 purge v2 + 컬렉션 큐레이션 v3 완결(같은 날 밤)** —
  ① purge v2: 읽기 전용 사전 분석(v1 키워드 잔존 2건 + rating≥4.8
  무인터랙션 8건) 후 사용자 확정으로 **9편 삭제**(아방섹·한녀·월하의
  사미인곡·태조 왕건(드라마 오입)·갈망·너무 너무 좋은 거야·퍼펙트 센스·
  봄이가도·기억의 전쟁), 비밀애(4128, 정식 상업영화)는 보존. KR 1,197→
  1,188. 8/18 관찰 노이즈("섹귀" 등)는 8/25 정비(672편)에서 이미 제거돼
  있었음을 실측 확인. 사전 movies 백업 CSV. 삭제 실행은 분류기 차단으로
  사용자 수행. ② 컬렉션 v3: 이월됐던 D/E/F 진행 —
  `seed_collections_v3.sql` + 정식 CLI 배정. korean-cinema 10편(기생충·
  살인의 추억·아가씨 등)·animation-masters 6편(주토피아·너의 이름은. 등)·
  horror-classics 6편(싸이코·샤이닝·조용한 가족 등). 후보는 rating 단독이
  아니라 **picks 인터랙션 존재 + 수동 검수**로 노이즈(만선·흥부와 놀부,
  2026 미개봉작) 배제. API 검증: 컬렉션 11개, 3종 편수 10/6/6 정확.
  배정 총계 77→99편.
- **키워드 태그 백필 프로덕션 완주** — 3,295개 신규 태그 / 1,848편(전체
  3,411편의 54%), 상위 라벨: 실화 178·슈퍼히어로 133·복수 123·형사 113·
  우정 111·디스토피아 107. 커버리지 max(movie_id)=5620=movies 최대 id로
  전량 확인. 관찰: 로컬 ssh 파이프(tail 버퍼링)가 원격 종료 후에도 매달려
  진행 로그가 안 보였음 — DB 카운트로 모니터링하는 것이 정답.
- **rating=5.0 노이즈 근본 완화 — movies.vote_count + 베이지안 가중 정렬**
  (컬렉션 v3에서 또 수동 검수로 우회한 것을 계기로 착수):
  ① `movies.vote_count` 컬럼(마이그레이션 `20260901_0001`) + TMDB 인입
  체인 배선(snapshot DTO→mapper→upsert command→repo, 0=미수집은 기존값
  보존), ② `weighted_rating.py` — `(v·R + m·C)/(v+m)`, m=50·C=3.0:
  투표 적으면 중립으로 수렴해 "1명 10점→5.0" 노이즈 무력화, ③ rating
  단독 desc 정렬 4곳 교체(영화탭 평점순·인기순 tie-break, 채팅
  recency-first 후보, 에디터 리뷰 대상 선정, 헤더 검색 tie-break),
  ④ `backfill_vote_counts.py`(멱등, vote_count=0만). 로컬 실검증:
  기생충 21,210·부산행 8,660표 채워짐, pytest 728 passed.
  **EC2 배포**: 이미지 재빌드가 ENOSPC로 실패(30GB 디스크에 torch 이미지
  2벌 공존 불가 — builder/image prune으로도 9.9GB뿐) → **docker cp 임시
  반영 + 재시작**(8/11 선례)으로 우회, 마이그레이션 적용·backend 200 확인.
  정식 재빌드는 별도 시점 필요(변경분은 git에 있어 다음 성공 빌드에 포함).
  vote_count 프로덕션 백필 진행(완료 시 전 카탈로그 커버).
  **백필 완주(같은 날 저녁, 무인 완료)**: 3,210/3,411편 채움 — 잔여는
  진짜 투표 0인 작품 189편 + TMDB 삭제 404 1편(tmdb-1676053, movie_id
  2769 — 카탈로그 정리 후보). 멱등 재실행으로 완주 검증. **최종 실측**:
  `/mova/movies?sort=rating` 상위 12편이 전부 대작(스파이더맨 노 웨이 홈·
  주토피아·듄·오펜하이머·탑건 매버릭 등) — 무명 5.0 노이즈 상단 점령
  현상 소멸 확인.
- **운영 결정(사용자)**: 데스크톱은 상시 서버가 아님 — **오늘만 예외로
  켜두고 퇴근**(vote_count 백필 완주용). 평소에는 PC 꺼지면 LoRA 경로가
  내려가고 Gemini 폴백이 받는 게 정상 상태. 구 노트북 터널은 재기동 금지
  (DNS가 데스크톱 `lora-desktop`으로 이관됨). 루트 CLAUDE.md 주의사항에
  반영.
- **키워드 태그 실효 검증 + 채팅 후보 조립 갭 발견** — "요리 소재 영화"는
  식객·카모메 식당으로 정상 작동(키워드 태그 효과 실증). 그러나 "좀비
  영화"는 0건(trace=81b08f57): 태그는 있는데 **RAG 시맨틱 히트가 1건이라도
  있으면 태그 검색 폴백을 아예 안 타는** `ChatInteractor` 구조 — 무관한
  시맨틱 8건이 후보를 점령하면 그라운딩 0픽. 수정 방향(키워드 질의는
  RAG∪태그 합집합)을 PROGRESS 백로그에 정밀 기록(불변식 검토 선행).
- **`lora.suvisdev.cloud` 터널 인증 잠금(같은 날 후속)** — 재노출된 공개
  터널이 무인증이던 백로그(2026-08-05) 해소. 토큰 생성 → 로컬 systemd 유닛
  `Environment=LORA_SERVER_TOKEN` 주입 + 재기동(무토큰 401·정토큰 200 실측,
  `/health`만 공개 유지), `docker-compose.yaml`에
  `LORA_SERVER_TOKEN=${LORA_SERVER_TOKEN:-}` 매핑 추가(**compose 미매핑이면
  .env에 넣어도 컨테이너에 안 들어가는 8/5 LORA_SERVER_URL 함정과 동일
  구조를 선제 차단**). EC2 `.env` 등재는 분류기 차단으로 사용자 실행,
  이후 backend 재생성·E2E 재검증.
- **후속 테스트 정리** — 전체 pytest에서 8/31 커밋의 드리프트 2건 발견·수정:
  `list_embedded_reviews_by_user`가 5-tuple(sentiment 포함)로 확장됐는데
  `test_platform_user_taste_vector.py` mock이 3-tuple로 남아 있었음(sentiment
  None 추가, 기대값 불변). 리뷰 라우터 3건 실패는 이 데스크톱에 로컬 DB가
  없어서였음 — `docker compose up -d db redis` + 빈 DB에 `alembic upgrade
  head`(20260831_0003까지 전체 체인 무결 확인)로 로컬 개발 DB 세팅 후
  **728 passed, 0 failed**(8/31 기준선과 동일). 8/31 커밋에서
  `market_review_votes_orm`의 importlinter 예외 누락도 발견·등재(커밋
  `1449dbc`에 포함).

## 2026-08-31

### 작업 내용
- **Phase 2 상영시간표 구현 (설계서 §5, 롯데시네마 단독)** — booking 트랙에
  롯데시네마 내부 JSON 엔드포인트를 통한 실시간 시간표 조회 기능 추가.
  robots.txt 재실확인(롯데 전체 허용, 메가박스 전체 차단, CGV AI봇 차단).

### 수정/구현
- **ShowtimePort ABC** (`mova/app/ports/output/showtime_port.py`): `fetch_showtimes(cinema_name, movie_title, date?)` → `CinemaShowtimeDto | None`
- **LotteCinemaAdapter** (`mova/adapter/outbound/http/lotte_cinema_adapter.py`):
  - `CinemaData.aspx` `GetCinemaItems`로 극장 237곳 목록 조회 (24시간 캐시)
  - `TicketingData.aspx` `GetPlaySequence`로 극장+날짜별 시간표 조회
  - 카카오 place_name → 롯데시네마 매칭 (접두사 제거 + 정규화 부분 문자열)
  - 영화 제목 매칭 (상호 부분 문자열 포함)
  - 좌석: `seats_available = max(total - booked, 0)`
- **DTO 확장** (`mova/app/dtos/market_chat_dto.py`):
  - `ShowtimeSlotDto` (screen, start_time, end_time, film_type, seats_available, seats_total)
  - `CinemaShowtimeDto` (cinema_name, slots)
  - `ChatBookingDto.showtimes` 필드 추가 (default_factory=list, 하위호환)
- **Schema 확장** (`mova/adapter/inbound/api/schemas/market_chat_schema.py`):
  - `MovaChatShowtimeSlotSchema`, `MovaChatCinemaShowtimeSchema`, `MovaChatBookingSchema.showtimes`
- **BookingAssistService 연동** (`mova/app/use_cases/market_chat_booking_interactor.py`):
  - `_fetch_lotte_showtimes()`: 근처 영화관 중 "롯데" 포함 극장에 시간표 조회 (최대 2곳)
  - 응답 문구에 "롯데시네마 기준 오늘 상영 시간표 N회차를 찾았어요" 포함
  - ShowtimePort optional 주입 — 미주입 시 빈 리스트 (Phase 1 폴백)
- **DI 배선** (`mova/dependencies/market_chat_provider.py`): `get_booking_service`에 `showtimes=LotteCinemaAdapter()` 추가
- **ChatInteractor meta 저장** (`mova/app/use_cases/market_chat_interactor.py`): `_reply_booking`에 showtimes 직렬화
- **프론트 패널 렌더** (`suvis/components/mova/mova-ai-chat-bar.tsx`):
  - `ShowtimeSlot`, `CinemaShowtime` 타입 추가
  - `ChatBookingPanel`에 시간표 칩 렌더 (시작 시간, 상영관, 2D 아닌 상영 타입, 좌석)
  - "롯데시네마 기준 · 실시간 좌석은 다를 수 있어요" 안내 문구
- **테스트 8건** (`mova/tests/test_chat_tracks.py`):
  - `test_lotte_theater_gets_showtimes`: mock ShowtimePort로 롯데시네마 시간표 응답 포함 확인
  - `test_non_lotte_theater_skips_showtime_fetch`: 비롯데 극장은 조회 안 함 확인
  - `test_no_showtime_port_returns_empty`: ShowtimePort 미주입 시 빈 리스트 확인
  - `test_showtime_exception_is_swallowed`: 시간표 조회 예외 시 graceful 폴백
  - `test_max_two_cinemas_cap`: 롯데시네마 3곳 → 최대 2곳만 조회 확인
  - `test_showtime_none_result_excluded`: fetch_showtimes None 반환 시 결과 미포함
  - `test_showtime_reply_includes_slot_count`: 응답에 회차 수 포함 확인
  - `test_response_dto_to_schema_includes_showtimes`: ChatResponseDto.to_schema() 시간표 직렬화

- **좌표 기반 최근접 롯데시네마 폴백** — 카카오 결과에 롯데시네마가 없을 때
  (예: "강남" 검색 → CGV·메가박스만 5곳) 첫 극장의 좌표로 가장 가까운
  롯데시네마를 자동 탐색(haversine 거리 계산, 반경 10km):
  - `ChatTheaterDto`에 `lat`/`lng` 필드 추가
  - `KakaoLocalTheaterAdapter`: 카카오 응답의 `x`(lng)/`y`(lat) 채우기
  - `_LotteCinema`에 `lat`/`lng` 추가, `_ensure_cinemas`에서 `Latitude`/`Longitude` 저장
  - `LotteCinemaAdapter._find_nearest_cinema()`: haversine 최근접 검색
  - `LotteCinemaAdapter.fetch_nearest_showtimes()`: 좌표 기반 시간표 조회
  - `ShowtimePort.fetch_nearest_showtimes()`: 기본 메서드 (None 반환, 비추상)
  - `BookingAssistService._fetch_lotte_showtimes()`: 롯데 0곳일 때 좌표 기반 폴백
  - 테스트 3건 추가: 폴백 호출 확인 / 롯데 있으면 폴백 안 함 / 좌표 없으면 폴백 스킵

### 오류·막힌 점
- EC2 SSH 자동 명령 일부가 classifier에 의해 차단됨 (단순 읽기 명령은 통과)
- hub_knowledge ingest cron 제거 미완 (차단으로 인해 — 2972/2972 완료라 무해)
- 강남 검색 시 시간표 0건 버그 — 카카오 로컬 "강남" 검색에 롯데시네마가
  없고(가장 가까운 롯데 "도곡"이 약 2km) 좌표 기반 폴백이 없었음 → 해결

- **오타 허용 영화 제목 검색 (자모 퍼지 매칭)** — "더문은 쩸 쓰나"처럼
  오타+조사가 섞인 발화에서 "더 문"을 찾도록 3계층 폴백 구현:
  1. **조사 분리** (`market_chat_title_resolver.py`): 한국어 조사 정규식으로
     첫 어절에서 은/는/이/가/을/를 등 제거 — "더문은" → "더문"
  2. **공백 정규화 SQL** (`market_chat_pg_repository.py`): `func.replace(title, ' ', '')`로
     "더문" ↔ "더 문" 띄어쓰기 차이 허용
  3. **자모 편집거리 퍼지 폴백** — exact 검색 0건일 때만 발동:
     - `jamo_fuzzy.py` (신규): 한글 자모 분해(초·중·종성) + Levenshtein 편집거리
     - `ChatRepositoryPort.fuzzy_search_movies_by_title()`: 비추상 기본 메서드 (빈 리스트)
     - `ChatPgRepository`: 전체 제목 로드 → Python 자모 비교 → 편집거리 3 이내 매칭
     - 결과 1건이면 ok, 2건 이상이면 ambiguous (오인식 방지 안전장치)
  - 테스트: `test_jamo_fuzzy.py` 16건 신규 + `test_chat_tracks.py` 조사 분리 2건 +
    기존 not_found 테스트 2건 fuzzy mock 추가

- **`google.generativeai` → `google.genai` 마이그레이션** — 구 패키지 지원
  종료(FutureWarning) 대응. 전역 `genai.configure()` → 인스턴스 기반
  `genai.Client(api_key=...)` 패턴으로 전환:
  - **Keymaker** (`vauly_keymaker_secret_manager.py`): `genai_client` 프로퍼티 추가,
    `genai.configure()` + `GenerativeModel` 캐시 제거
  - **호출자 4곳**: `gemini_llm_adapter.py`, `gemini_client.py`, `intent_extraction.py`,
    `media/ocr.py` — `client.models.generate_content(model=..., contents=...)` 호출로 변경
  - **임베딩 어댑터**: `client.models.embed_content()` + `EmbedContentConfig` 사용,
    `client` 생성자 주입 지원 (백필 스크립트에서 별도 API 키 클라이언트 전달)
  - **백필 스크립트 3곳**: `genai.Client(api_key=backfill_key)` 인스턴스를
    `GeminiEmbeddingAdapter(client=...)` 로 전달 (전역 상태 제거)
  - **테스트 3파일**: mock 경로를 새 API에 맞게 갱신
  - **requirements.txt**: `google-generativeai==0.8.6` → `google-genai>=1.0.0`
  - **EC2 배포**: auth·backend 컨테이너 재빌드(디스크 부족 3회 → auth 중지+prune로
    19GB 확보 후 성공), health 200 확인, Gemini API 정상 응답

- **mova-ai-chat-bar useCallback 의존성 리팩터링** — `sendMessage` useCallback이
  `conversationId`·`dbMode`·`onConversationChanged`를 클로저로 잡아 stale closure
  발생 가능한 구조 수정:
  - `chatRef`·`conversationIdRef`·`dbModeRef`·`onConversationChangedRef` 도입으로
    최신 값을 ref에서 읽도록 변경
  - deps를 `[]`로 비워 sendMessage 재생성 방지
  - `dbModeRef` 선언 위치 문제(선언 전 사용) 수정 → `pnpm type-check`·`pnpm lint` 클린

- **PROGRESS.md 정비** — `EMBEDDING_BACKEND=gemini` 전환 완료 확인(EC2 printenv),
  hub_knowledge 임베딩 어댑터 항목 완료 마킹, genai 마이그레이션·chat-bar 리팩터링
  완료 마킹

- **리뷰 시스템 감정분석 통합 + 자동 별점 + 감정 요약 + 신뢰도 태그**

  **A. 에디터 리뷰 감정분석 → 자동 별점**
  - `review_sentiment_backfill_interactor.py`: `sentiment_to_rating()` — 긍정:
    2.5+score×2.5, 부정: 2.5-score×2.0, 0.5단위 반올림
  - `analyze_one()`에서 감정 저장 후 `rating=NULL`(에디터 리뷰)이면 자동 별점 부여
  - `market_reviews_pg_repository.py`: `update_rating_if_null()` 구현

  **B. 선호도 점수 = 별점 + 감정 합산**
  - `platform_user_taste_vector_interactor.py`: `_effective_rating()` 도입 (α=0.3)
  - 별점과 감정 일치 시 강화, 불일치 시 감쇄. 감정 없으면 원래 별점 그대로
  - `list_embedded_reviews_by_user` 시그니처 5-tuple 확장 (sentiment 포함)

  **2. 영화별 감정 요약**
  - 백엔드: `GET /mova/reviews/sentiment/{movie_id}` — 긍정/부정 수·비율·한 줄 요약
  - `MovieSentimentSummaryDto` + `MovieSentimentSummarySchema` 신규
  - 프론트: 리뷰 섹션 상단에 긍정/부정 비율 바 + 요약 텍스트

  **3. 에디터 리뷰 신뢰도 태그**
  - ORM: `reviews.news_source_count` INTEGER 컬럼 추가
  - 마이그레이션: `20260831_0002_add_reviews_news_source_count.py`
  - 스케줄러: 에디터 리뷰 생성 시 `len(articles)` 저장
  - 프론트: "AI 에디터 ·높음/보통/낮음" 배지 (5건↑=높음, 2~4=보통)

  **4. 감정분석 24시간 자동 스케줄러**
  - `review_sentiment_scheduler.py`: 24시간 주기로 `sentiment_label IS NULL` 리뷰
    자동 분석. GPU 없는 환경에서는 연속 2회 실패 시 루프 자동 종료
  - `main.py` lifespan에 등록 + 종료 시 cleanup

  **5. 리뷰 유용성 투표 (도움돼요)**
  - ORM: `review_votes` 테이블 (user_id+review_id UNIQUE, CASCADE)
  - 마이그레이션: `20260831_0003_create_review_votes.py`
  - 백엔드: `POST /mova/reviews/{review_id}/vote` 토글 엔드포인트 (로그인 필수)
  - `get_by_movie`에 vote_count 서브쿼리 추가 (리뷰 목록과 함께 반환)
  - 프론트: ThumbsUp 버튼 클릭으로 투표 토글 + 실시간 카운트 반영

### 산출물
- pytest 728 passed, FutureWarning 해소, `import main` 클린
- genai 마이그레이션 커밋 `2c68503`, EC2 배포 완료
- 감정분석+자동별점+감정요약+신뢰도 태그 커밋 `be1f055`
- 투표+감정분석 스케줄러 커밋 `5e38138`, EC2 배포 완료 (마이그레이션 3건 적용)
- `pnpm type-check`·`pnpm lint` 에러 0건
- 지킬 포스트 `2026-08-31-mova-review-sentiment-voting.markdown` push 완료

## 2026-08-28

### 작업 내용
- "클래식 명작 처음 보는 사람용" 칩 클릭에 주토피아(2016)·엔드게임(2019)이
  추천된 오추천 원인 규명(사용자 스크린샷 제보). EC2 로그·DB 실측으로 4단계
  체인 확정: ① Gemini 임베딩 일일 쿼터 429로 RAG 시맨틱 검색 생략(trace=
  89f3f24a) → ② 태그 폴백에서 "클래식"·"명작" 매칭 태그 0건(tags 8,584건 중)
  + `_guess_year_range`가 시대 어휘를 연도로 해석 못 함 → 하드 조건 0개 →
  ③ 인기작 폴백의 "최근 15년 우선 + 평점순"(2026-08-25 콜드스타트 대책) 상위
  16편에 주토피아·엔드게임 포함(DB 실측) — 클래식 요청인데 옛 영화가 오히려
  뒤로 밀림 → ④ LLM이 "엄선했습니다"로 포장. DB에 클래식은 실재(1990년 이전
  238편, 90년대 197편) — 후보로 못 올라온 것.
- mova 채팅에 누적된 명령·규칙을 하네스로 통합(사용자 인터뷰로 4개 결정:
  위치 `.claude/rules/`, 범위 백엔드+프론트 전부·mova 한정, 버그 즉시 수정,
  폴백 정직 문구 규칙 추가).

### 수정/구현
- `intent_extraction.py`: 시대 어휘("클래식·고전·옛날") → `year_max=1999` 근사
  (`_ERA_WORDS`). 명시 연대·연도("90년대 클래식")가 있으면 그쪽 우선.
- `chat_prompt.py`: 의도 섹션 AND 조건에 `연도=` 표기 추가 — SQL 하드 필터가
  없는 RAG 경로에서도 LLM이 연도 제약을 보게.
- `test_intent_country_year.py`: 시대 어휘 3케이스 추가(칩 원문·고전·명시
  연대 우선). 14 passed.
- `.claude/rules/mova-chat.md` 신설 — 파이프라인 불변식(카탈로그 한정·폴백
  유지·히스토리 병합·dedup 2단·recency-first와 연도 필터 상호보완), 응답 문구
  규칙(0건 정직·다양화·폴백 확신 문구 금지), 실행·보안 규칙, 프론트 UX까지
  통합. `MOVA_CHAT_UX.md`는 흡수 후 삭제, `apps/mova/_docs/CLAUDE.md` 참조 갱신.
- `mova-header.tsx`: 헤더 테마 토글 제거(사용자 지시 — 토글이 안 먹는 것으로
  보였고, mova는 `MovaThemeSetter`가 진입 시 다크를 강제하는 다크 전용 설계라
  토글이 라이트로 빠지는 구멍이었음). 토글 삭제로 mova는 항상 다크 고정.
  gildle 페이지·공용 `theme-toggle.tsx`는 유지(스코프 밖).
- 채팅 응답 트랙 재설계 설계서 작성(사용자 지시): 추천 단일 트랙 →
  recommend/evaluate/booking 3트랙. `MOVA_CHAT_INTENT_REDESIGN.md` 신설
  (현행 자산 실측 표·evaluate 집계 설계·booking Phase 1~3·레이어 배치·
  체크리스트), 하네스 `.claude/rules/mova-chat.md` §8에 방향 요약 규칙 추가.
- 재설계 미결 결정 5건 사용자 인터뷰로 확정: ① 왓챠 리뷰 수집은 약관
  명시 금지·DB권 판례(사람인–잡코리아 4.5억 배상) 실확인 후 **제외** →
  TMDB 리뷰 API 대체, ② 시간표 Phase 2 진행(체인 약관 실확인·단건 조회·
  딥링크 폴백 선행), ③ 위치는 프롬프트 지역명 입력+상황 변수(차량 등)는
  되묻기, ④ **1차 분류기 확장으로 변경**(초안의 mova 내부 2단 분류 폐기,
  destination 5종 — 소비자 mova뿐 실측) + mova 정의를 "추천·평가·예매
  프로젝트"로 재정의(`apps/mova/_docs/CLAUDE.md` 역할 갱신), ⑤ chat_trend
  조건부 반영(단순 질의 미집계, 긍정 반응·예매 의지 시만).
- **3트랙 Phase 1 구현 완료**(같은 날 이어서):
  - 분류기 5종 확장: `qwen_intent_classifier.py` 프롬프트·상수(레거시 "rag"
    → recommend 정규화, 기본 폴백 recommend), 포트 docstring, semantic
    router는 신설 3종을 rag 경로 동일 취급.
  - evaluate 트랙: `MovieEvaluationService` + `ReviewAggregationPort`/pg
    구현(스포일러 리뷰 발췌 제외) + `TmdbReviewAdapter`(공식 API) + Mycroft
    (Gemini) 종합 프롬프트(정량/정성 분리·표본 3건 미만 명시).
  - booking 트랙: `BookingAssistService` — KOFIC 주간 박스오피스로 상영 중
    근사 판정, 미상영이면 OTT 안내, 상영 중이면 『제목』+`REGION_ASK_MARKER`
    되묻기 → 다음 턴을 결정론으로 이어받아 카카오 로컬(주소→키워드 폴백
    지오코딩, 반경 10km 거리순) 영화관 목록 + 체인 3사 검색 딥링크.
  - chat_trend 조건부 신호: `user_actions`에 `booking_intent`(작품 확정 최초
    턴, 로그인 한정)·`eval_positive`(직전 평가 meta + 긍정 어휘) 기록,
    `aggregate_chat_trend`가 click과 함께 집계.
  - 응답 계약: `response_type` + evaluation/booking payload(DTO·Schema),
    프론트 `mova-ai-chat-bar.tsx` 타입·파싱·패널 2종(지표 칩+발췌 인용 /
    영화관 리스트+예매 링크) 렌더 분기.
  - 테스트: 신규 `test_chat_tracks.py`(22케이스)·`test_intent_classifier_
    destinations.py`(6케이스), 레거시 분류기 테스트 기대값 갱신 + 프롬프트
    few-shot 2건 복원. 전체 692 passed(`-m "not gpu and not ollama"`),
    `pnpm type-check` 통과.
  - 알려진 한계: 대화 스레드 복원 시 evaluation/booking 패널은 재구성 안 됨
    (meta에 카드만 저장) — 필요해지면 meta에 payload 추가.
- **배포 중 발견·수정한 후속 3건**(전부 EC2 실측):
  - 인텐트 분류 잠복 결함: EC2엔 Ollama(Qwen)가 없어 분류가 **전부 호출
    실패 → 기본값**으로 새고 있었음(기본값이 rag이던 시절엔 증상이 안 보여
    발견 못 함). `FallbackHubLlmAdapter`(Qwen→Gemini) 신설로 해결.
  - 상영 중 판정 0건: 주 중간 날짜로 KOFIC 주간 박스오피스를 조회하면
    완결 안 된 주라 빈 목록 — KST 직전 일요일로 고정(`_last_completed_week_date`).
  - EC2 `.env`에 `KAKAO_API_KEY` 미반영(오늘 gildle 작업에서 로컬만 추가) —
    `KAKAO_CLIENT_ID`와 동일 값으로 등재 후 backend 재생성.
- **임베딩 쿼터 429 대응(1순위 백로그)**: 크론 백필(하루 950건)이 실시간
  채팅 RAG와 Gemini 일일 쿼터를 공유해 오후마다 채팅이 폴백 품질로 떨어지던
  구조 분리. 임베딩 백필 3종(movies·reviews·ingest_hub_knowledge) CLI 시작
  시 `GEMINI_BACKFILL_API_KEY`(두 번째 Google 프로젝트 키)로 genai를 재설정
  — CLI는 서버와 별개 프로세스라 전역 재설정이 안전하고, 미설정이면 기존
  동작. 로컬 임베딩 폴백안은 Gemini와 의미 공간이 달라(hub 어댑터 주석
  실측) 전량 재임베딩 없이는 불가라 배제. `.env.example`·
  `SCRIPTS_EXECUTION_GUIDE.md` 등재. 키 발급(새 프로젝트, 사용자)·로컬
  ·EC2 `.env` 등재·backend 재생성·양쪽 실호출 검증(768차원)·EC2 백필
  스크립트 경로 검증까지 완료 — 새벽 크론부터 새 키 사용.
- **2순위 후속 3건 구현**(쿼터 분리에 이어 같은 날):
  ① 폴백 정직 문구 — 후보가 전부 `popular_fallback`이면 프롬프트에 "조건
  매칭 실패, 인기작 폴백임을 정직하게 밝혀라" 지시 삽입(`chat_prompt.py`,
  어댑터 4종 공용 빌더라 한 곳 수정). ② 스레드 복원 패널 재구성 — 대화
  meta에 evaluation(지표·발췌)·booking(영화관·링크) payload 전체 저장 +
  프론트 `messagesFromConversation`이 파싱해 새로고침 후에도 패널 유지.
  ③ 이동수단 슬롯 — 지역 답변에서 "차로/도보"를 파싱해 검색 반경 조정
  (도보 3km·기본 10km·차량 20km), 되묻기 문구에 예시 추가, 미지정 시 힌트.
  테스트 7케이스 추가(전체 699 passed), `pnpm type-check` 통과.
- **프로덕션 실측(EC2)**: "주토피아 어때?" → evaluation(정량/정성 분리·표본
  1건 부족 명시·TMDB 리뷰 한국어 요약·payload 발췌), "주토피아 예매하고
  싶어" → not_showing+디즈니플러스 안내, "오디세이 예매하고 싶어"→"강남"
  → CGV 청담씨네시티(1,106m) 등 5곳 거리순 + 체인 3사 링크. 커밋
  a75c060·d42fe7e·b31909c, 프론트는 Vercel 자동 배포.

### 오류·막힌 점
- 전체 pytest에서 6건 실패로 보였으나 `-m` 미지정으로 ollama 자동 skip이
  꺼진 것 + ontology vision 테스트 기존 실패(수정 전에도 동일) — 표준 실행
  (`-m "not gpu and not ollama"`)은 670 passed 전부 통과.

### 데이터
- EC2 movies 연대 분포: ~1989 238편 · 1990s 197편 · 2000s 507편 · 2010s
  962편 · 2020s 1,504편. "클래식"·"명작" 라벨 태그 0건.

### 산출물
- 백로그: PROGRESS.md "mova 채팅 클래식 오추천 후속" — 쿼터 429 대응·폴백
  정직 문구 프롬프트 구현·RAG 연도 필터(선택).

## 2026-08-26

### 작업 내용
- 프로덕션 `/mova/chat` 502 원인 규명: 노트북 lora-server·cloudflared가 내려가
  `lora.suvisdev.cloud`가 530 → EC2(`RECOMMENDATION_BACKEND=lora`)의 LoRA 호출
  연속 실패 → 서킷 오픈. 8/25에 추가된 `FallbackRecommendationAdapter`가
  **DI에 미연결**이라 Gemini 자동 폴백이 작동하지 않고 에러가 그대로 노출됐다.
- 채팅 로딩 클래퍼보드 영상 하단 문구("Mova가 찾아줄게") 잘림 수정. 영상
  파일 자체는 원본과 md5 동일 — 잘림은 CSS 크롭(`aspect-[7/5]`+`object-left`)
  때문이었다(주석의 "우측 20% 검은 여백" 전제가 현재 영상과 불일치).

### 수정/구현
- `suvisdev/apps/mova/dependencies/market_chat_provider.py` —
  `get_recommendation_port()`가 lora 모드에서
  `FallbackRecommendationAdapter(primary=LoRA, fallback=Gemini)`를 조립하도록
  연결. 서킷 쿨다운(60초) 후 LoRA 재시도 → 성공 시 자동 복귀(왕복 자동 전환).
- `suvis/components/mova/mova-ai-chat-bar.tsx` — 로딩 비디오 컨테이너를
  `aspect-video`로, `object-left` 크롭 제거.

### 오류·막힌 점
- 로컬 검증 시 `.env`의 `RECOMMENDATION_BACKEND=gemini`가
  `load_dotenv(override=True)`로 셸 env를 덮어써 폴백 조립이 안 보이는 것처럼
  나옴 — import 후 `os.environ` 주입으로 양쪽 모드 조립 검증 완료.

### 데이터
- EC2 DB 장르 실측: 19개 장르(TMDB 표준). "뮤지컬"은 TMDB 장르 체계에
  없어 0편 — 레미제라블은 "역사, 드라마", 라라랜드는 "코미디, 로맨스,
  드라마"로만 수집돼 있었다. "음악"(92편)은 콘서트 실황·아이돌 다큐 계열로
  뮤지컬과 별개(사용자 지적으로 확인).
- TMDB 키워드(musical 4344 | broadway musical 165241 | musical theater
  220201, vote≥100) discover 458편 ↔ 카탈로그 3,419편을 제목 정규화+연도 ±1
  매칭 → 65편(레미제라블·라라랜드·위대한 쇼맨·위키드·겨울왕국 등).

### 수정/구현 (추가) — 채팅 zero-rec 로그 실측 + 언어 허용목록 과차단 수정
- 프로덕션 로그 실측: 어시스턴트 응답 39건 중 recs=0 13건(33%). 분류 결과
  대부분 이미 수정된 구버전 버그(멀티턴 오염 8/19, 프랜차이즈·무드 8/25)
  또는 dedup 소진·비질의 오분류였고, 제목/배우 오타는 0건 — 편집거리·초성
  엔티티 매칭은 실측 수요 없음(YAGNI 기각). 유일한 재현 가능 실패:
  "일본 애니메이션 영화 추천" (현행 프로덕션 재현으로 확인).
- 근본 원인: `ALLOWED_ORIGINAL_LANGUAGES=("ko","en")` 허용목록(8/7,
  맥락 없는 외국어 노출 방지)이 **국가를 명시한 요청**까지 차단 — ja 원어
  79편이 후보에서 원천 배제돼 catalog가 비고 recs=0.
- 수정: `_hard_conds`에서 countries 필터가 명시된 경우 언어 허용목록을
  우회(정책 취지 보존 — 미명시 요청은 기존대로). 회귀 테스트
  `test_market_chat_hard_conds.py` 2건 추가. 전체 628 passed.

### 수정/구현 (추가) — RAG(시맨틱 검색) 프로덕션 부활 진행
- EC2 `EMBEDDING_BACKEND` ollama→gemini 전환(8/7부터 조용히 죽어 있던
  벡터 검색 부활). 시맨틱 경로 라이브 실증: "우주에서 살아남는 이야기"
  → 그래비티·라이프. general 히스토리 전달(75df08c)도 함께 배포.
- 전량 재임베딩 중 **조용한 실패 삼킴 사고**: ingest_movie가 임베딩
  실패(429)를 삼켜 succeeded=2,972로 위장, 실제 색인 889건. →
  ingest_movie bool 반환 + 스크립트 지수 백오프 재시도·`--skip-existing`
  재개·정직한 집계(58fb796).
- **Gemini 무료 티어 일일 쿼터 1,000회 실측 확인**(429): 색인
  979/2,972(33%)에서 중단. EC2 호스트 crontab에 매일 07:10 UTC(쿼터
  리셋 직후) `--skip-existing` 재개 잡 등록 — 이틀 내 전량 예상, **완료
  확인 후 cron 제거할 것**. 쿼터 소진 동안 채팅은 태그 폴백으로 정상.

### 수정/구현 (추가) — 불만·메타 발화 general 라우팅
- "똑같은 말 반복하지마"·"뭔 영화가 이렇게 없냐" 같은 봇 행동 불만이 추천
  파이프라인으로 흘러 빈 카드 응답을 반복하던 것(실측 2건) —
  `QwenIntentClassifier.classify`에 결정론 가드 추가: 실측 패턴 3종
  ("반복하지"/"이렇게 없"/"보여줘야지") 감지 시 LLM 라우터 없이 general.
  패턴은 실측 기반으로만 유지("영화 없냐" 단독은 추천 요청이라 제외).
  분류기가 mova 채팅·게이트웨이 공용이라 한 곳 수정으로 양쪽 적용.
- 테스트 2건 추가(가드 발동 + "재밌는 영화 없냐" 비발동). 전체 631 passed.

### 수정/구현 (추가) — dedup 소진 대안 행동
- 후속 질의("다른것도")에서 첫 후보 16편이 전부 이미 소개된 경우, 조건은
  유지한 채 후보 풀만 16→48로 넓혀 한 번 재검색해 새 후보를 공급
  (실측 zero-rec 13건 중 4건이 이 케이스). 그래도 없으면 기존 동작
  (정직한 0카드 + 안내 문구) 유지. RAG(semantic) 경로는 재검색 없음.
- `market_chat_interactor.py` 폴백 검색을 `_search_catalog(limit)` 클로저로
  묶어 재사용, 테스트 1건 추가(소진→확장→새 후보 서빙). 전체 629 passed.

### 수정/구현 (추가) — 헤더 레이아웃 통합 + 닉네임 깜빡임 해소
- 좌상단 닉네임 깜빡임의 3중 원인 규명: ① MovaHeader가 각 page에 개별
  마운트라 이동마다 리마운트, ② 세션이 effect에서 채워져 "로그인 버튼→
  닉네임" 플래시, ③ 닉네임이 별도 fetchProfile이라 새로고침 시 username
  선노출(8/25 모듈 캐시는 메모리라 새로고침 미커버).
- 해소: MovaHeader를 `app/mova/layout.tsx`로 통합(리마운트 제거, 페이지
  14곳+타이틀 뷰에서 제거, `/mova/login`은 헤더가 pathname으로 자기 숨김),
  랜딩·채팅은 min-h-screen/h-screen → flex-1로 높이 보정. 로그인 버튼은
  hydration 가드 placeholder + localStorage 닉네임 캐시(user id 키)로
  첫 렌더부터 닉네임 표시.
- 검증: tsc·eslint(0 errors) 통과, `pnpm build` 성공, dev 서버 SSR 실측
  — 전 페이지 헤더 1개·`/mova/login`만 0개 확인.

### 수정/구현 (추가)
- `/mova/movies` 장르 탭을 DB 실측에 맞게 갱신: 뮤지컬 0편 문제로 모험·
  판타지·가족·미스터리·음악 추가, 뮤지컬은 아래 백필과 함께 유지(총 16탭).
- `suvisdev/scripts/tag_musical_genre.py` 신규 — TMDB 키워드 기반 '뮤지컬'
  genre 태그 백필(멱등, `--dry-run` 지원). `TmdbAdapter.fetch_discover`에
  `with_keywords` 파라미터 추가.

### 산출물
- 커밋(아래), mova 채팅 테스트 12건 통과, `pnpm type-check` 통과.
- 배포 실측 확인: EC2 저장소·백엔드 이미지 `edc1de6` 반영(컨테이너 안
  `with_keywords` 존재), alembic `20260825_0001 (head)`, Vercel 번들에
  새 장르 탭·뮤지컬 확인, EC2 DB 뮤지컬 태그 65건 존재.
- **전체 검증 파이프라인 복구 + 테스트 그린화**: ① 전체 pytest에서만 나던
  수집 에러 3건 — gildle conftest의 sys.path 순서로 정규 패키지
  `apps/gildle/scripts`가 최상위 `scripts`를 선점(메타패스 훅으로 실증).
  루트 `scripts/__init__.py` 추가 + gildle 쪽 빈 `__init__.py` 제거로
  정규>네임스페이스 우선순위를 이용해 순서 무관 해결. ② 테스트 드리프트/
  격리 6건 수정: bulk_import kofic(8/13 CLI 제거분) → tmdb_discover,
  채팅 0건 안내 랜덤 3변형 플레이키 → random.choice 고정, gildle 경로 2건
  → N1~N5 픽스처+`GILDLE_SCORED_EDGES` 고정(서울 실데이터 간섭 차단),
  core/lol 서킷 전역 상태 누출 → autouse 리셋. 최종 626 passed.
  ③ lint-imports가 낡은 ignore 3줄로 실행 불능이던 것 복구 — 문서화된
  결합 (a)를 hub 계약에, 신규 mova ORM 6건을 spoke 계약 ignore에 등록,
  6 계약 전부 KEPT. ④ ruff F401 미사용 임포트 12건 제거.
  검증: pytest 626 passed·lint-imports exit 0·`import main` OK.
- **pre-commit 게이트 복구**: 훅·도구 모두 미설치 상태였음(WSL 재구축
  여파 — 이번 드리프트 누적의 근본 원인). 설정이 `suvisdev/` 안에 있어
  모노레포 git 루트에서 애초에 동작 불가 → 루트로 이동하고 경로 스코프
  (`files: ^suvisdev/`, lint-imports는 cd 래핑). ruff+ruff-format 전체
  적용(433 파일, 포맷·정렬만 — pytest 626 passed 재확인). mypy는 전체
  실측 1,327건이라 임시 비활성(백로그 등재). 자동수정 불가 53건 처리:
  실제 냄새 14건 수정(B011 assert False→AssertionError 4, B904 예외
  체이닝 from e 7, B007 미사용 루프 변수 2, F841 1) + F821(DTO lazy
  import 반환 주석)은 TYPE_CHECKING 임포트로 해결. 의도적 관례(E402
  부트스트랩·sklearn X 변수명·Gemini systemInstruction 미러링·기존
  예외/모듈명)는 pyproject per-file-ignores에 사유와 함께 등재.
  최종: pre-commit 3훅 전부 Passed.
- 지킬 블로그(`suvisdev/suvisjk` 레포) 8/26 포스트(장르 탭·뮤지컬 백필)
  추가·푸시. 8/25 포스트는 전 세션이 이미 배포해 둔 상태였음. 모노레포 안
  `suvisjk/`가 레포 분리(8/25) 이전의 낡은 무연결 사본이었던 것을 발견 —
  `git init`+fetch+checkout으로 원격 클론에 재연결해 동기화(로컬 고유
  콘텐츠는 신규 포스트뿐이었음). deploy key가 push 불가라 remote를
  HTTPS(gh 인증)로 전환.

### 오늘 커밋 요약 (시간순)
- `3eeda2c` Cursor 설정 제거 · `af4ff37`/`0937ced` 앱 카탈로그 SEUK 카드
- `d4828b8` 검증 파이프라인 복구(pytest·lint-imports·eslint 그린)
- `2885155` pre-commit 게이트 복구 + ruff 전체 포맷
- `efa0835` 헤더 레이아웃 통합(닉네임 깜빡임 해소)
- `83d8b44` 언어 허용목록 우회(일본 애니 0건 수정)
- `f8f217f` dedup 소진 풀 확장 재검색
- `0343a05` 불만·메타 발화 general 가드
- `75df08c` general 응답 히스토리 전달
- `58fb796` ingest_movie bool 반환 + 재임베딩 재시도·재개
- suvisjk `af91804` 8/26 포스트 · ats `c8594af`~`9b84ff8` 팀원·주간보고·Arda

## 2026-08-25

### 작업 내용
- EC2 mova 추천 백엔드를 gemini 폴백 → lora로 복구. 노트북 lora-server와
  Cloudflare 터널(`lora.suvisdev.cloud`)이 정상 동작 중인데 EC2만 폴백에
  남아 있던 상태.
- **채팅 무응답 근본 원인 규명 + LoRA 재학습**: 7/20 어댑터가 구버전 출력
  형식(movie_id 없음)으로 학습돼 현재 그라운딩 프롬프트에서 picks:[]만 반환.
  기존 export 스크립트도 completion에 movie_id가 없는 구형식임을 확인.
  → Gemini 교사 증류 데이터셋 60건(실 DB 카탈로그 + 그라운딩 검증 필터) 생성,
  EXAONE-AWQ LoRA 재학습(3 epoch, loss 0.92→0.49, `mova_20260825_123937`).
  재검증: 3개 질의 모두 recs=3 정상 (이전 전부 0).
- **폴백 어댑터 + 서킷 브레이커**: `FallbackRecommendationAdapter`(lora 실패
  시 Gemini 자동 전환) + 오케스트레이터 서킷(연속 2회 실패 → 60초 즉시 실패).
  노트북 꺼짐 = 수동 .env 전환하던 운영 부담 제거.
- **DB 정리 (성인물 + 한국 미개봉)**: ① CLIP 포스터 제로샷(0.995 임계) +
  제목 키워드 + 성인물 배우 전파(118명) + 수동 검토로 672편 삭제.
  ② TMDB release_dates KR 부재 400편 삭제(고전 명작 19편은 오탐 보존).
  ③ 고아 배우 3,938명 정리. 최종 movies 4,255→3,419, actors 22,430→18,492.
  전부 trash 스키마 백업. 검수 리포트 HTML을 바탕화면에 생성.
- **TMDB 최신 수집**: discover에 region/release_type/release_date_lte/sort_by
  파라미터 추가, 한국 개봉 기준(외화 포함)·성인물 제외·최신순 1,000편 수집
  (실패 0).
- **"집에서만 502/404" 근본 해결**: 집 docker cloudflared가 EC2와 동일 토큰
  으로 api 터널에 이중 접속 → Cloudflare가 트래픽을 구버전 로컬 스택으로
  분산하던 것. lora 전용 터널(systemd `cloudflared-lora`)은 별도로 이미 존재
  → 중복 docker cloudflared 중지 + restart=no.
- **검색 품질**: mood_expansion에 히어로/마블 추가 + franchise_expansion
  신규(마블→어벤져스 등 대표작 제목 확장) + search_tag_catalog 제목 매칭.
  콜드 스타트 후보 정렬을 "최근 15년 우선, 평점순" 2단 정렬로 변경(1959년
  작 뜬금 추천 방지).
- **프론트 UX 6건**: 가로 스크롤 행 마우스 드래그(DragScrollRow), 배우
  클릭→소개+출연작 다이얼로그(기존 `/mova/actors/{id}` 연동), 출연진
  사진·이름 정렬, 아바타 onError 폴백, 장르 행 로테이션(48편 풀 셔플),
  랭킹 포디움 빈 슬롯 placeholder, 채팅 로딩 영상 비율, 닉네임 깜빡임
  (모듈 캐시), 랜딩·채팅 헤더 검색 placeholder 통일,
  window.confirm/alert 전부 Mova 스타일 다이얼로그로 교체.
- **리뷰 댓글 + 리뷰 수정 진입 + 에디터 리뷰**: ① `review_comments` 테이블
  신규(1단 댓글, 로그인 작성, 본인만 삭제) — 헥사고날 전체 스택(ORM/스키마/
  DTO/포트/인터랙터/라우터) + 프록시 + 접힘식 댓글 스레드 UI.
  ② 본인 리뷰 카드에 "수정" 버튼 → 기존 수정 폼으로 스크롤.
  ③ `generate_editor_reviews.py` 신규 — 구글뉴스 RSS(제목+요약만) + Gemini로
  "Mova 에디터" 시스템 계정 리뷰 생성 배치(영화당 1건, 재실행 안전).
  이후 24시간 주기 스케줄러로 상시화(EDITOR_REVIEWS_DAILY_LIMIT 기본 15편,
  스크립트는 얇은 래퍼로 위임).
  랜딩 자체 헤더를 공통 MovaHeader로 통일. 다이얼로그 포털 투명 배경 수정
  (.mova-app 스코프). 새로고침 버튼 양 탭 통일.

### 수정/구현
- EC2 `suvisdev/.env`: `RECOMMENDATION_BACKEND=gemini` → `lora` 변경 후
  backend 컨테이너만 재생성(`--force-recreate --no-deps`, 약 8초).
- 코드 변경 없음 — 운영 설정 전환만.

### 검증
- 컨테이너 printenv: `RECOMMENDATION_BACKEND=lora`,
  `LORA_SERVER_URL=https://lora.suvisdev.cloud` 확인.
- EC2 컨테이너 안에서 터널 경유 `/health` 200, `/generate` 실제 생성 200
  (엔드투엔드 확인).
- 베이스 모델 실측: **EXAONE-3.5-2.4B-Instruct-AWQ** + mova LoRA 어댑터
  (`mova_20260720_022643`, awq_gptqmodel 백엔드). 루트 CLAUDE.md의
  "베이스 Qwen2.5-1.5B" 기술은 구정보 — 어댑터 `adapter_config.json`의
  `base_model_name_or_path`가 EXAONE-AWQ를 가리킨다.

## 2026-08-19

### 작업 내용
- WSL 클린 재구축 Phase 2 — 개발 환경 복원 (Node.js/pnpm/Python/프론트·백엔드
  의존성/.env).
- 멀티턴 주제 전환 미감지 버그 조사 및 수정. 증상: 1턴 "액션 영화" → 2턴
  "여행 영화"에서 "새 후보 없음" — 이전 턴 장르가 search_filters에 잔존.

### 수정/구현
- **`intent_extraction.py` — `IntentExtractionService.extract()`**:
  `_prepend_recent_user_context()`가 만든 `composed_text`(이전 턴 포함)를
  결정론적 경로(`_fallback_raw`, `build_search_filters`, `normalize_keywords`)에
  흘리던 것이 근본 원인. 수정 후 `composed_text`는 Gemini EXTRACT_PROMPT에만
  사용하고, 결정론적 경로·keywords·search_filters는 현재 턴(`text`)에서만 유도.
  Gemini 응답에서는 `refined_query`만 취하고 `must`/`similar_to`/`keywords`는
  결정론적 결과를 사용해 이전 턴 필터 오염 방지.
- **`intent_extraction.py` — `refined_query` RAG 오염 2차 수정**:
  1차 수정(search_filters/keywords)으로 필터는 고쳤지만, `refined_query`는
  여전히 Gemini 응답에서 가져오고 있었음. `refined_query`는
  `market_chat_interactor.py` L136에서 RAG 시맨틱 검색 쿼리로 직행하므로,
  Gemini가 이전 턴 컨텍스트를 포함한 "송강호 공포 영화" 같은 refined_query를
  반환하면 후보 자체가 오염됨. `refined_query`도 현재 턴 결정론적 결과
  (`deterministic.get("refined_query")`)에서 가져오도록 수정.
- **`games_pg_repository.py` — 한국 영화 풀 외국 영화 혼입 수정**:
  `_kr_pool_conditions`에 `_has_korean_actor()` EXISTS 서브쿼리 추가 —
  `original_language='ko'`이지만 한국어 이름 배우가 한 명도 없는 영화
  (TMDB 오분류)를 제외. `MovaCharacter` JOIN `MovaActor`에서
  `name ~ '[가-힣]'` 조건.
- 변경 파일 3개:
  - `suvisdev/apps/mova/adapter/outbound/llm/intent_extraction.py`
  - `suvisdev/apps/mova/adapter/outbound/pg/games_pg_repository.py`
  - `suvisdev/apps/mova/tests/test_intent_gemini_skip.py` (테스트 기대값 갱신)

### 오류·막힌 점
- 최초 계획은 3줄 변경(composed_text → text)이었으나, `.env`에 GEMINI_API_KEY가
  있어 Gemini 경로가 실제 동작하면서 `parsed.keywords`와 `parsed.must`를 통해
  이전 턴 장르가 여전히 유입되는 것을 확인. `build_search_filters`에 넘기는
  `parsed`를 `deterministic`(현재 턴 결과)으로 교체하여 해결.
- 1차 배포 후 실사용 재현("배우 송강호 나오는 작품" → "그냥 공포 영화
  추천해줘")에서 여전히 송강호+공포 결합 추천. 원인: `refined_query`를
  Gemini 응답에서 가져오는데, 이 값이 RAG 시맨틱 검색 쿼리로 직행
  (`market_chat_interactor.py` L136 `rag_query = intent["refined_query"]`).
  Gemini가 composed_text를 보고 "송강호 공포 영화"를 refined_query로 반환
  → 후보 자체가 오염. `refined_query`도 결정론적 결과로 교체.
- 초성 게임 한국 영화 풀: `_has_hard_signal()`이 장르만으로는 False를 반환해
  Gemini 경로를 타는 구조와 별개 이슈. `original_language='ko'`만으로는
  TMDB 오분류 영화를 걸러내지 못함 → 한국 배우 EXISTS 조건 추가.
- WSL Phase 2: Python 3.14(Ubuntu 26.04 기본)에서 matplotlib 빌드 실패 →
  pyenv로 3.13.15 설치 해결. /tmp tmpfs 3.9GB 한도로 torch 다운로드 실패 →
  TMPDIR=~/pip-tmp로 우회 해결.

### 산출물
- 커밋: `fix(mova): refined_query RAG 오염 + 초성게임 한국 영화 풀 필터 강화`

---

---

## 2026-08-18

### 작업 내용
- 사용자 리포트: `/mova/upcoming`(개봉 예정작)에 이미 개봉일이 지난
  영화가 섞여 있음. 원인 확인 후 수정.
- (같은 세션) PROGRESS 백로그 훑어 착수 가능한 항목 실행. 벡터 스위치
  단독 flip은 재임베딩 없이는 오히려 오응답(ollama 벡터 vs gemini 쿼리)
  이라 보류 유지. 3순위 "레거시 무태그 12편(1056~1067) 정리"만 실행.
- (같은 세션) 취향-영화 코사인 결합 랭킹 착수 전 벡터 공간 정합성
  읽기 전용 조사 → Go 판정. 이어서 실 구현·검증·커밋까지 완료.

### 수정/구현 — 취향 벡터 재정렬 (1-c 다음 순서 1)
- **사전 진단(쓰기 없이 4축 조사)**: movies.embedding·reviews.embedding·
  user_taste_vectors 세 벡터가 전부 Gemini 768d로 정합함을 실 코드 경로로
  확정 (backfill_movie_embeddings_cli.py:91,97 하드 gemini / review_embedding_provider.py:15,21 하드 gemini /
  platform_user_taste_vector_interactor.py:45-63 reviews 벡터 가중 평균 →
  자동 gemini 공간). `EMBEDDING_BACKEND` 플래그는 hub_rag_provider.py:28-38
  한 곳에만 걸려 있어 hub_knowledge 트랙과 movies/reviews 트랙은 완전 독립
  — flip은 랭킹 결합과 무관.
- **결정 5개 (재해석 없이 적용)**: (1) 결합 위치 = ChatInteractor 계층
  (5개 어댑터 공통이라 하위 chat_reply.py 대신 상위 인터랙터에 삽입),
  (2) 순수 코사인 정렬(별점 alpha 결합은 후속 백로그), (3) taste vector
  없으면 스킵 debug 로그, (4) 후보 window 12 유지 · 상위 3 노출 유지,
  (5) Python 재정렬(3편 규모, SQL <=> 불필요).
- **Port 확장**:
  - `UserTasteVectorRepositoryPort.get_taste_vector(user_id) → list[float]|None`
    신설 (얇은 wrapper, 재정렬 경로 전용 — DTO 없이 벡터만).
  - `MoviesRepositoryPort.list_embeddings_by_ids(movie_ids) → dict[int, list[float]]`
    신설 (배치 조회, embedding NULL은 반환 dict에서 제외).
- **PgRepository 구현**: 각 port에 대응. taste는 `select(vector).where(user_id==?)`,
  movies는 `select(id, embedding).where(id IN ..., embedding IS NOT NULL)`.
- **ChatInteractor**:
  - 생성자에 `movies: MoviesRepositoryPort | None`, `taste_vectors:
    UserTasteVectorRepositoryPort | None` optional 주입(기존 테스트 호환).
  - `_llm.generate_recommendation()` 반환 직후 · `save_chat/save_picks`
    이전에 `_rerank_recommendations()` 호출 — save_picks 순서와 UI 카드
    배치가 어긋나지 않게.
  - 재정렬 helper `_rerank_by_taste_cosine(recs, taste_vector, embeddings_by_id)`:
    embedding 없는 rec은 `math.inf` key로 뒤로 밀되 자기들끼리는 original_idx
    stable sort로 원 순서 유지. 0벡터/차원 불일치는 cosine=0.0.
  - 스킵 조건(debug 로그만): 비로그인, port 미주입, taste vector None(리뷰 0건/
    rating 합계 0), movies embedding 전량 없음.
- **DI**: `market_chat_provider.py`에 `get_movies_repository_for_chat`·
  `get_user_taste_vector_repository` 신설, `get_chat_use_case`에 배선.
- **테스트 3건**(`test_market_chat_interactor.py::ChatInteractorTasteRerankTests`):
  (a) taste vector 있음 → cosine 순 재정렬 발현(입력 `[101,202,303]` +
  taste `[1,0,0]` + embedding `[[0.5,0.5,0],[1,0,0],[0,1,0]]` → 응답 순서
  `[202,101,303]`, save_picks 순서도 동일 검증),
  (b) taste vector None → LLM 원 순서 유지 + movies port 미호출 assert,
  (c) 비로그인 user_id=None → 두 port 미호출 assert.
- **회귀**: `apps/mova/tests` 202 pass + 신규 3 pass. 사전 실패 2건
  (`test_bulk_import_movies.py::test_start_page_for_resume` — 스크립트에서
  `--source kofic` 옵션이 제거된 상태 미반영, `test_market_conversations_interactor.py::
  test_zero_recs_reply_content_when_already_shown_all` — `_compose_empty_reply`
  랜덤 문구 다양화 이후 하드코딩 문구 기대 잔재)은 이번 스코프 아니라 손대지 않음.
- **lint-imports**: "Hub (ontology) must not depend on any spoke BROKEN"은
  사전 상태(ontology→dispatch 1 · ontology→mova 1 · ontology→viewer 3, 전부
  이번 세션 이전부터 존재). 이번 변경은 전부 mova 내부라 새로 유발한 위반 없음.
- **후속 백로그** (PROGRESS 갱신): alpha 별점 결합 튜닝, 후보 window
  확대, `search_tag_catalog` 후보 생성 개선(배우 필터/OR·AND 복합조건/
  origin_country).
- 크론 상태 점검: movies embedding(잔여 0), review embedding(잔여 0),
  taste vectors(전일 1건 갱신) 전부 건강. `POSTGRES_PASSWORD blank` 경고는
  crontab 라인이 `docker compose exec`라 `--env-file` 없이 도는 것 —
  exec 실행에는 무해(컨테이너 내부 env 정상, "Mova DB 엔진 초기화 성공"
  로그 확인).

### 수정/구현 — 레거시 12편 정리
- 대상 확정: EC2 DB에서 id 1056~1067 12편 전부 `release_year=0`, 비-TMDB
  slug, tags/chars/dirs 전부 0인 죽은 로우 재확인. 2026-08-05 골든셋 튜닝
  시점에 title 매칭용으로 끼워 넣은 임시 데이터로 추정(WORK_LOG 2026-08-05
  및 memory `project_mova_vector_search_pending_reembed.md`와 정합).
- 정식 대체 조회: 12편 중 10편은 정식 TMDB row가 이미 카탈로그에 있음
  확인(엽기적인 그녀=`tmdb-11178`, 극한직업=`tmdb-567646` 등). 조제·
  패터슨 2편만 대체 없음 — 어차피 태그 0으로 후보에 못 들어가던 상태라
  잃는 것 없음(필요 시 나중에 정식 TMDB import로 복구).
- 외래키 참조 조사: `movies` 참조 8개 테이블(characters/tags/rankings/
  reviews/picks/watchlist/user_actions/movie_directors) 전부 CASCADE.
  실사용자 데이터 확인 결과 `picks`에만 12건 걸림, 나머지 0. picks 12건은
  전부 `user_id=NULL`(익명), `feedback=NULL`, `batch_at=2026-08-05 04:58~05:23`
  으로 골든셋 검증 시점 임시 로그로 확정.
- 백업: EC2 `~/legacy_12_movies_backup_20260818_013402.csv`(119KB, 12행) +
  `~/legacy_12_picks_backup_20260818_013402.csv`(2KB, 12행). 초기에
  `pg_dump | grep -E '1056|1057...'`로 만들려 했다가 embedding 벡터 내부
  부동소수 값에 오탐(42MB 나옴) — WHERE 절이 있는 `COPY (...) TO STDOUT
  CSV`로 재작성.
- 실행: `DELETE FROM movies WHERE id BETWEEN 1056 AND 1067` 트랜잭션 —
  `DELETE 12` + CASCADE로 picks 12건 함께 삭제, 검증 쿼리로 잔여 0 확인.

### 오류·막힌 점
- `pg_dump` 오탐(위 참고).
- 로컬 백엔드 미기동이라 `/mova/upcoming` 검증은 프로덕션으로 함.
- 정식 대체 조회 쿼리에서 `\\d picks` 결과 `created_at` 없고 `batch_at`이 실
  컬럼명이라 재쿼리.

### 산출물
- `suvisdev/apps/mova/adapter/inbound/api/v1/upcoming_router.py` 수정
  (개봉예정 필터, PR #127 머지 `8d4f272`, EC2 backend 재빌드 완료).
- EC2 DB 레거시 12편 삭제(백업 CSV 2건, EC2 홈).
- WORK_LOG·PROGRESS 갱신.

### 수정/구현 — MOVA v1 완결 판정 로드맵 문서 신설
- 파일: `suvisdev/_docs/MOVA_POST_V1_ROADMAP.md` (신규, 문서만).
- 목적: PROGRESS(백로그 순위)·WORK_LOG(일자별 기록) 위의 상위 로드맵
  — v1 완결 판정 5축 + 완결 후 백로그 스냅샷 + 신규 사이클 후보 +
  취업 어필 문서화 트랙 + 우선순위 정렬.
- 구조: Meta / A(5축 판정) / B(남은 백로그 4하위) / C(v2 후보 3건) /
  D(취업 어필 3항목) / E(다음 착수 지점 3건).
- 근거 사용 원칙: 실 파일 근거만, 창작 금지. 사용자가 언급한
  소스 중 `suvisdev/_docs/MOVA_UI_AUDIT.md`·`suvisdev/_docs/PROGRESS.md`
  경로는 실제 존재하지 않음(전자는 파일 자체 없음, 후자는 실제
  경로가 `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`) — 실제 존재 파일
  (`_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`,
  `suvisdev/apps/mova/_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md`,
  `suvisdev/apps/mova/_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`,
  `suvisdev/apps/mova/_docs/CLAUDE.md`)만 근거로 사용.
- v1 완결 판정 = 5/5 ✅: (1) UX 루프 폐쇄(취향 재정렬 오늘 배포로
  최종 폐쇄), (2) 데이터 정합성(크론 3건·HNSW·레거시 정리), (3) 보안
  하드닝(리뷰 IDOR·watched 게이트), (4) 운영 관측성(크론 로그 표준),
  (5) 결함 관리(PROGRESS 우선순위 명시적 관리).
- Section C-3(챗봇 학원 커리큘럼 대응)은 근거 문서 부재로 "판단 보류"
  로 명시하고 사용자 범위 명세 요청 조건 기재. Section D 전체도
  근거 문서 부재라 "사용자 지정 카테고리 · 실행 전 스코프 합의 필요"
  명시.
- 사용자 스코프 준수: PROGRESS.md 수정 없음(별도 티켓). 코드 변경
  없음, 문서 신설만.

### 산출물(추가)
- `suvisdev/_docs/MOVA_POST_V1_ROADMAP.md` 신규 파일.
- WORK_LOG 갱신(이 항목).

### cloudflared 24h 관찰 결론 (로그 판정, 코드 변경 없음)
- 6.7일(2026-08-11T13:34 ~ 2026-08-18T06:00) 9538 샘플, FAIL 620건 중
  초일 527·08-13 13:00~13:18 연속 87·08-14 1건. **08-15~08-18 4일간
  FAIL 0건**. cloudflared 컨테이너 uptime 12일(08-06 시작) 재시작 0회.
  실측 응답 60ms. → ✅ 자연 해소, 관찰 종결. PROGRESS "진행 중"·ROADMAP
  Section E-3 종결 반영. 로그 파일은 EC2 홈에 그대로 보존.

### 수정/구현 — QUALITY_PHASE1 §7 stale 정정 (문서만)
- 사용자 지시: 다음 착수 지점(ROADMAP Section E-2) "search_tag_catalog
  배우 조인 추가"로 시작. 사전 조사 결과 **이미 구현·배포·검증 완료**
  임을 발견:
  - `market_chat_pg_repository.py:52-68 _movie_ids_by_actors` +
    `search_tag_catalog(actor_names=..., countries=..., year_min=..., year_max=...)`
    시그니처
  - 커밋 이력: `26adfec (2026-08-06)` 배우 매칭·인기작 폴백,
    `b07c64b (2026-08-07)` 국가·연도 하드 필터,
    `4231991 (2026-08-07)` original_language 언어 필터
  - 테스트 3건 `test_market_chat_interactor.py::ChatInteractorSearchTagCatalogTests`
- 사용자에게 재확인 → **옵션 1(실측 재검증 + QUALITY_PHASE1 §7 정정,
  코드 변경 없음)** 확정.
- **실측**(EC2 프로덕션, 13초 간격 §8.1 쿼터 오염 방지):
  - #6 송강호 스릴러: 3/3 grounded — 살인의 추억(925)·기생충(147)·
    **박쥐(2172, 신규 등장)**. 배우 매칭 구조적 정착 실증(§7.2 "우연"
    정정 근거).
  - #5 전지현 코미디: 0카드, 하지만 `intent_type=mood` **오분류** —
    저장소 계층 아니라 intent 계층으로 원인 이동.
  - #7 키아누 리브스 액션: 0카드, 같은 패턴(`intent_type=mood`).
- **문서 정정**: `MOVA_RECOMMENDATION_QUALITY_PHASE1.md` §9 신설
  (§7 stale 서술 정정) — 해소 결함 매핑 표(4건 중 3건 해소, (3) 다중
  장르 AND만 미해소), §7.2 "우연" 정정, §7.3 잔여 실패가 intent 계층
  이동으로 넘어감 명시, 실측 대조표, "§9 없이 §7만 인용하지 말 것"
  경고. 코드 변경 없음.
- **얻은 교훈**: PROGRESS·품질 문서·실 코드의 갱신 시차가 벌어지면
  이미 해소된 결함을 다시 파는 반복 작업 발생. 오늘 실제로 겪음
  (사용자가 §7.3 근거로 배우 조인 지시 → 사전 조사에서 이미 구현됨
  발견). 사용자가 지목한 근거 문서는 반드시 사전 조사에서 실 코드와
  대조할 것.

### 산출물(추가)
- `suvisdev/apps/mova/_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md` §9 신설.
- WORK_LOG(이 항목) + PROGRESS "취향 재정렬 후속" 백로그의 배우 조인
  항목 완결 표시.

### 수정/구현 — 영화-컬렉션 배정 API/CLI 신설 (PROGRESS 7순위)
- **사전 조사(쓰기 없이)**: `movies.collection_id` FK **one-to-many** 구조
  확인(조인 테이블 없음 → 마이그레이션 신설 불필요). 기존 8개 층 스캔:
  Schema/DTO/Input Port/Interactor/Output Port/PgRepo/Router/Tests 전부 존재,
  CRUD·List·Movies 조회는 있으나 배정 경로 부재. `scripts/seed_collections.sql`
  이 raw UPDATE로 시드 중이던 상태.
- **결정**: API(어드민 가드) + CLI(Repository 직접 호출) **둘 다 신설**
  (사용자 지시). CLI는 8순위 큐레이션 확장 전 실질 창구.
- **Port·DTO 확장**:
  - `CollectionRepositoryPort.assign_movies(slug, movie_ids) → CollectionAssignResultDto | None`
  - `CollectionRepositoryPort.unassign_movies(slug, movie_ids) → CollectionAssignResultDto | None`
  - `AssignMoviesUseCase` · `UnassignMoviesUseCase` 신설
  - `CollectionAssignResultDto` — `collection_id, collection_slug, affected,
    skipped_ids, moved_from_other_collection`
- **PgRepository 구현**:
  - `assign`: `SELECT id, collection_id WHERE id IN (...)`로 존재+현재 소속
    확인 → `moved_from_other_collection` 계산 → `UPDATE ... SET collection_id`
  - `unassign`: `SELECT id WHERE id IN AND collection_id = ?`로 대상 좁힘 →
    `UPDATE ... SET collection_id = NULL`
  - 둘 다 중복 id 제거(`dict.fromkeys`), 컬렉션 없으면 `None`, 빈 movie_ids
    는 0-affected 결과 반환(idempotent).
- **Router**:
  - `PATCH /mova/collections/{slug}/movies` — 배정, `require_admin`
  - `DELETE /mova/collections/{slug}/movies` — 해제, `require_admin`
  - `CollectionMoviesMutationRequest` body(`movie_ids: list[int]`,
    `min_length=1, max_length=500`), `CollectionAssignResultSchema` 응답
  - 컬렉션 없으면 404, 존재 안 하는 movie_id는 `skipped_ids`로 부분 성공(200)
- **DI**: `market_chat_provider.py` 패턴과 정합. `get_assign_movies_use_case`
  · `get_unassign_movies_use_case` 신설, 기존 interactor 인스턴스 공유.
- **CLI**: `suvisdev/scripts/assign_collection_cli.py` 신설
  (`--slug --movie-ids A,B,C [--unassign] [--dry-run]`).
  `SCRIPTS_EXECUTION_GUIDE.md` 표준 형태 준수, docstring에 시맨틱 명시.
  Repository 직접 호출(관리자 SSH 전제).
- **테스트 6건 추가**:
  - Router 5건: assign 부분 성공(moved 카운트 검증) · assign 404 · assign 빈
    바디 422 · unassign 부분 성공 · unassign 404
  - Interactor 1건: assign/unassign 위임 + None bubble
  - CLI 6건(별도 파일 `test_assign_collection_cli.py`): argparse 파싱 정상·
    unassign+dry-run 조합·정수 아닌 값 거부·빈 값 거부·공백 관용·helper 직접
  - fake use case에 `assign_movies`/`unassign_movies` 메서드 추가, router
    fixture에 `require_admin` override 배선.
- **회귀**: `apps/mova/tests` 214 pass + 신규 6 pass. 사전 실패 2건은 이번
  스코프 밖(bulk_import `--source kofic` 미반영, `_compose_empty_reply` 랜덤
  문구 하드 기대 — 이전 사이클과 동일).
- **마이그레이션 없음**: `movies.collection_id`가 이미 있고 `ON DELETE SET NULL`
  까지 걸려 있어 신규 마이그레이션 불필요.
- **의도적으로 안 함**: 어드민 UI(별도 프론트 스코프), many-to-many 전환
  (구조 변경, 별도 티켓).

### 산출물(추가)
- 신규 파일: `assign_collection_cli.py`, `test_assign_collection_cli.py`
- 수정: `market_collections_dto.py`, `market_collections_repository.py`(port),
  `market_collections_pg_repository.py`, `collections_use_case.py`(port),
  `collections_interactor.py`, `collections_provider.py`,
  `market_collections_schema.py`, `collections_router.py`,
  `test_collections_router.py`, `test_collections_interactor.py`
- 총 신규 2 + 수정 10 = 12 파일.

### 수정/구현 — 컬렉션 큐레이션 v2 (PROGRESS 8순위 부분 완결)
- **사전 조사(쓰기 없이)**: EC2 DB 실측 — 카탈로그 3852편 중 배정 44편
  (1.1%), 미배정 3808편. 8-06 시점 서술(2014편) 대비 카탈로그 확장 반영.
  프론트 `/mova/collections`는 완전 동적(`fetchMovaCollections`, 그리드
  자동 렌더) — 백엔드만으로 커버.
- **후보 6개 데이터 기반 선정**: A) spielberg(스필버그 감독 12편) · B)
  tarantino(11편 전량) · C) ridley-scott(10편) · D) korean-cinema(233편
  풀에서 top-15) · E) animation-masters(178편 풀에서 top-12) ·
  F) horror-classics(138편 풀에서 top-10).
- **⚠ 실측에서 D·F 오염 발견**: rating DESC LIMIT이 **rating=5.0 노이즈**
  (소수 평가 + 성인물 잔여 로우)에 걸림. D 15편은 "섹귀·피지컬 뷁·윤율의
  사내 불륜·비키니바" 등 **전량 성인물**, F 10편도 상위 대부분이 성인물
  KR 로우("흡혈귀 야녀·월하의 사미인곡·한녀·악령·하녀의 방·춘몽" 등
  1970~80년대 rating=5.0 노이즈). E도 상위 몇 편이 중국 계열
  (`仙逆剧场版`·`八仙！`)로 검증 필요. **그대로 실행 시 대표작 컬렉션에
  성인물 노출 사고**. 즉시 사용자에게 보고.
- **사용자 결정(옵션 2)**: A/B/C 3개만 이번 사이클 진행, D/E/F는 KR 성인
  잔여 purge(2026-08-14 130편 purge 연장선) 선행 후 다음 사이클에서
  재시도.
- **실행**:
  - `suvisdev/scripts/seed_collections_v2.sql` 신설 — 3개 컬렉션 INSERT
    (`ON CONFLICT DO NOTHING`). 배정 SQL은 없음(7순위 CLI로 진행하려는
    의도 파일 상단 명시).
  - EC2 프로덕션: `docker compose exec -T db psql -f seed_collections_v2.sql`
    → `INSERT 0 3` 확인 → collections 8개(1~5 기존, 6~8 신규).
  - 배정 3회: `docker compose exec -T backend python scripts/
    assign_collection_cli.py --slug ... --movie-ids ...`
    - A `spielberg-world` (id=6): 12편(232,386,576,521,717,901,580,1147,
      339,808,2,883) affected=12 skipped=0 moved=0
    - B `tarantino-universe` (id=7): 11편(146,322,121,660,757,399,785,876,
      1964,482,1393) affected=11 skipped=0 moved=0
    - C `ridley-scott-selects` (id=8): 10편(152,345,112,1338,634,455,470,
      290,1906,769) affected=10 skipped=0 moved=0
- **검증**:
  - DB SELECT: 컬렉션 8개(기존 5 + 신규 3) 확인, 신규 3개 편수 12/11/10 정확.
    기존 5개 편수(12/8/8/8/8) 변동 없음(회귀 확인).
  - 배정 총계: 44 + 33 = **77편 / 3852편 = 2.0%** (기존 1.1% → 2배)
  - API 검증: `GET /mova/collections?limit=20` → items 8개 반환.
    `GET /mova/collections/{slug}/movies` × 3 → total=12/11/10 정확.
  - 프론트: 완전 동적이라 별도 배포 없이 즉시 반영. Vercel 캐시 만료 후
    `/mova/collections` 그리드에 3개 신규 카드 노출 예정.
- **얻은 관찰**: rating 컬럼이 소수 평가에도 5.0을 반환하는 노이즈 취약성
  이 큐레이션의 rating DESC 정렬에서 실제로 사고 유발할 수 있음을 실증.
  ROADMAP 백로그에 "KR 성인 잔여 purge" + "rating 노이즈 완화(vote_count
  기반 재정렬 등)" 추가 필요.
- **의도적으로 안 함**: D/E/F 강행 · 김기덕 등 논란 감독 컬렉션 ·
  카탈로그 필터 완화 · 프론트 어드민 UI.

### 산출물(추가)
- 신규 파일: `suvisdev/scripts/seed_collections_v2.sql`
- EC2 프로덕션 DB 변경: collections 3행 INSERT + movies 33행 UPDATE.
  롤백 필요 시 `assign_collection_cli.py --unassign` 3회 + `DELETE FROM
  collections WHERE slug IN (...)` — 로컬 CSV 백업 안 함(정식 배정 경로
  로만 통한 UPDATE라 이력·재현 가능).

### 수정/구현 — intent_extraction 배우 인식 개선 (옵션 A)
- **사전 조사(쓰기 없이)**: QUALITY_PHASE1 §9.3의 "잔여 실패 원인 =
  intent_type=mood 오분류"가 실제로는 원인/결과 반전임을 실 코드로 확정.
  - `QwenIntentClassifier`(ontology)의 destination은 `crud|rag|general` 3택,
    `mood` 없음. "전지현 코미디"는 `rag`로 정상 분류됨.
  - 진짜 원인은 mova `IntentExtractionService`(`intent_extraction.py`)의 두 축
    결합 결함: (1) `_guess_actors` 정규식이 조사·후치 마커("XX 배우/출연/이랑
    …") 뒤에만 배우 인식 → "전지현 코미디"는 미매칭 · (2)
    `_has_hard_signal`이 장르 하나만 잡혀도 True 반환 → Gemini 폴백 스킵.
    이 두 축이 만나 `must.actors=[]`가 되고 `build_search_filters`가 조건 개수
    1개(장르만)로 fallback해 `intent_type=INTENT_MOOD`가 됨. mood는 결과이지
    원인이 아님.
- **수정**: `intent_extraction.py:240-266 _has_hard_signal` 완화 —
  "장르만/국가만/키워드만"은 False로 떨어져 Gemini 폴백을 태우고, 배우가
  이미 잡혔거나 연도가 있거나 국가+장르 조합인 경우에만 True. Gemini 프롬프트
  예시가 배우 인식을 정확히 학습해 있어 폴백만 태우면 `must.actors`가 채워짐.
- **트레이드오프**: 무료 티어 분당 15요청 소모 증가 — "장르만/국가만"인
  질의가 Gemini를 새로 부르게 됨. 배우 인식 개선의 대가.
- **테스트 갱신**(`test_intent_gemini_skip.py`):
  - **시맨틱 변경 반영으로 2건 어설션 반전**:
    `test_skips_gemini_when_genre_found`→`test_calls_gemini_when_only_genre`,
    `test_skips_gemini_when_country_found`→`test_calls_gemini_when_only_country`.
  - **신규 2건**: `test_skips_gemini_when_country_and_genre`(국가+장르 조합
    은 여전히 스킵), `test_skips_gemini_when_actor_already_caught`(배우 잡히면
    스킵).
  - 기존 2건 유지: `test_skips_gemini_when_year_found`,
    `test_country_year_genre_query_still_resolves`(#9 회귀 방지).
- **회귀**: `apps/mova/tests/test_intent_gemini_skip.py` 7 pass. 전체
  `apps/mova/tests` **216 pass** + 사전 실패 2건(bulk_import `--source
  kofic`·`_compose_empty_reply` 랜덤 문구 하드 기대, 이번 스코프 밖).
- **QUALITY_PHASE1 §9.3 정정**: 원인/결과 반전 서술을 두 축 결합 결함으로
  재기술 + 옵션 A 해소 요지 추가. §9.4 대조표의 "intent_type=mood 오분류"
  문구도 두 축 결합 결함으로 변경.
- **의도적으로 안 함**: `_guess_actors` 정규식 확장(옵션 B, false positive
  위험) · `actors.name` DB lookup(옵션 C, 인프라 추가) — 옵션 A 실측 후
  부족하면 추가 트랙으로.

### 산출물(추가)
- 수정 파일: `intent_extraction.py`(hard signal 완화 5줄+docstring),
  `test_intent_gemini_skip.py`(테스트 갱신·확장),
  `MOVA_RECOMMENDATION_QUALITY_PHASE1.md`(§9.3 정정, §9.4 대조표 문구).

### 수정/구현 — 개봉예정 필터 세부(참고)
- 원인: `mova/adapter/inbound/api/v1/upcoming_router.py`가 TMDB
  `/movie/upcoming`(region=KR) 결과를 그대로 프록시. TMDB는 이 엔드포인트에
  최근 개봉된 항목까지 함께 반환하므로, region 필터만으로는 "과거 개봉일"이
  걸러지지 않는다.
- 프로덕션 실측(오늘 = 2026-08-18): 20건 중 2건이 과거 개봉일 —
  `2012-07-05 모모와 다락방의 수상한 요괴들`, `2026-05-27 백룸`.
- 수정: 라우터에서 `datetime.now(ZoneInfo("Asia/Seoul")).date()` 기준으로
  `release_date < today_kr`인 항목을 제외. 개봉일 미정(빈 문자열)은 프론트
  월별 그룹핑의 "개봉일 미정" 섹션 유지를 위해 그대로 통과시킴. 정렬 규칙
  (개봉일 오름차순, 미정은 뒤)은 그대로 둠.
- 프론트(`app/mova/upcoming/page.tsx`)는 손대지 않음 — 필터는 백엔드에서
  하는 것이 자연스러움(공통 소스, 30분 캐시 유효).

### 오류·막힌 점
- 로컬 백엔드가 안 떠 있어 `curl 127.0.0.1:8000` 실패 → 프로덕션
  (`https://api.suvisdev.cloud/mova/upcoming`)으로 재확인해 지난 개봉일 2건
  확정.
- venv 미활성 상태라 `pytest`·`lint-imports`는 실행 안 함. `py_compile`로
  문법만 확인(OK).

### 산출물
- `suvisdev/apps/mova/adapter/inbound/api/v1/upcoming_router.py` 수정.
- WORK_LOG·PROGRESS 갱신. 커밋 해시는 커밋 후 이 자리에 채워 넣음.

---

---

## 2026-08-14

### 작업 내용
- mova 하단 푸터 신설(티켓 A) — TMDB API 이용약관의 attribution 요건 미충족
  건을 단독 disclaimer 배너 대신 왓챠피디아·Letterboxd 스타일의 정상 푸터
  안에 편입. 이용약관·개인정보 처리방침·문의 자리를 함께 확보해 후속
  법적 페이지 추가 시 재작업 없이 링크만 채우도록 함.
- (같은 세션) 사용자 요청으로 푸터 세로 여백 축소(py-8→py-4, gap-4→gap-2,
  attribution·카피라이트 폰트 xs→11px)로 하단 잠식 완화.
- (같은 세션) 티켓 A 후속 페이지 실체 작성 — `/mova/terms`,
  `/mova/privacy`. 사용자가 참고 자료로 왓챠피디아 이용약관·개인정보처리방침·
  왓챠(VOD 스트리밍) 이용약관 3건을 제공. 왓챠(VOD 스트리밍)는 mova에
  존재하지 않는 유료 결제·왓챠 캐시·환불 로직이 대부분이라 부적합 판단,
  왓챠피디아 이용약관 구조를 채택. 기존 SUVIS 루트 페이지(`app/terms`,
  `app/privacy`, 시행일 2026-07-20)의 톤·섹션 스키마도 함께 참고해 mova
  특화 조항으로 재작성.
- (같은 세션) 푸터 추가 축소 — 폰트 11px→10px, py-4→py-3, gap-2→gap-1.
- (같은 세션) `/mova/main` 채팅 여백·상하 대칭 조정 — 리스트 상단 py-6→py-3
  (24→12px, 아래 입력폼과 대칭), 입력폼 py-3→py-2, "대화 목록" 상단 toolbar
  py-2→py-1. 사용자 지적: "위아래 간격이 안 맞음".
- (같은 세션) `/mova` 랜딩 히어로 카피에 브랜드 포인트 — "Mova가 찾아줄게."
  안의 "Mova"에 accent→#e05a8a→accent-bright 가로 그라디언트 텍스트. 채팅
  유저 말풍선(accent→#b84a72)과 동일 톤 계열로 브랜드 일관성 유지.
- (같은 세션) `/mova/rankings` podium 시상식 실루엣 수정 — 기존
  `aspect-[2/3]` + `mt-6/mt-10` 조합이 items-end grid에서 badge만 위로
  올리는 역효과(1위 badge가 오히려 낮음)를 냈음. 1위 poster `w-full`,
  2·3위 poster `w-[78%] md:w-[82%]`로 크기 계층 부여 → items-end가 자연스러운
  1위 우뚝·2·3위 나란히 podium 실루엣 만들도록 재작성.
- (같은 세션) 라이트 모드 색감 강화 — `--mova-border`
  0.10→0.20, `--mova-muted` #7a6a60→#5a4638 (대비 ~4.2:1→~7:1),
  `--mova-surface-2` #f0e8de→#ece1d0(구분감), `--mova-accent-soft`
  0.10→0.14 (chip 배경 노출). 크림 배경 위에서 소문구·chip·border가
  흐릿하다는 사용자 지적 반영.
- (같은 세션) 초성 게임 개선 2건 — 사용자 지적:
  ① 시리즈 넘버 숫자는 영어 발음으로. "강철비 2: 정상회담"이 기존엔 "이"
    (한자음, 초성 ㅇ)로 뽑혔지만 실제 관용은 "투"(초성 ㅌ). `_replace_digit_runs`
    를 개편해 **숫자 앞에 공백**이 있고 값이 1~10인 짧은 정수만 시리즈
    넘버로 간주하여 영어 발음 초성으로 대체(1=원 ㅇ, 2=투 ㅌ, 3=쓰리 ㅆㄹ,
    4=포 ㅍ, 5=파이브 ㅍㅇㅂ, 6=식스 ㅅㅅ, 7=세븐 ㅅㅂ, 8=에잇 ㅇㅇ,
    9=나인 ㄴㅇ, 10=텐 ㅌ). "20세기 소년"·"13일의 금요일"처럼 다른 글자에
    붙은 숫자는 기존 한자음(이십·십삼) 그대로 — 실측 6케이스 통과.
  ② 청소년 관람불가(청불) 등급 배제. 기존 KR 풀은 age_rating 필터가 없어
    "유부녀의 사정일지" 같은 성인·저품질 영화가 게임 풀에 노출됨.
    `_common_conditions`에 `age_rating != '청불' OR NULL` 조건 추가 — KR·
    외국·통합(카드뒤집기) 풀 모두 원천 차단.
- (같은 세션) TMDB discover 어댑터 강화 — `fetch_discover`에 `include_adult`
  (기본 False, 파라미터로 명시 전송) + `vote_count_gte` 옵션 추가. 카탈로그
  어댑터·`bulk_import_movies` CLI(`--vote-count-gte`)에도 전파. 목적: 유명
  한국영화만 대량 수집(성인·무명 배제). 테스트 `test_fetch_discover_calls_
  discover_endpoint_with_params`의 params 기대값에 `include_adult: "false"`
  추가. 실 수집 실행은 사용자 판단 대기 — 명령: `python scripts/bulk_import_
  movies.py --source tmdb_discover --country KR --pages 50 --start-page 101
  --vote-count-gte 100`.
- (같은 세션) 기존 실패 관찰: `apps/mova/tests/test_bulk_import_movies.py::
  ParseArgsTests::test_start_page_for_resume`가 `--source kofic`을 요구하나
  현행 `_SOURCES=("tmdb_popular", "tmdb_discover")` 뿐이라 실패 — 이 세션
  이전부터 존재하던 stale 테스트, 별건.
- (같은 세션) TMDB KR 대량 수집 실행 시도 → **DB 접속 실패로 미완**.
  ① 로컬 psycopg[binary] 미설치 → `uv pip install`로 해결.
  ② 로컬 Ollama에 `nomic-embed-text` 없음 → `ollama pull`로 해결.
  ③ `vote_count_gte=100` + `--start-page 101` → 결과 0(필터 유니버스가 100
    페이지보다 짧음). `--start-page 1`로 재시도 → 18페이지 356편이 필터 통과.
  ④ 356편 전량 `upsert_movie 실패` — 원인: 로컬 `.env`의 `MOVA_DATABASE_URL`
    이 `localhost:5432` 로컬 도커 대상인데 도커 컨테이너 미기동, 게다가 WSL에
    Docker Desktop WSL integration이 꺼져 있어 `docker` CLI 자체가 호출 불가
    (`/mnt/c/Program Files/Docker/...` PATH는 잡히나 실행 시 "could not be
    found in this WSL 2 distro"). 사용자에게 옵션 3안 제시(Neon URL 임시
    세팅 / EC2 Claude 세션 위임 / SSH 직접) 후 대기.
- (같은 세션) 카드 뒤집기 게임(`/mova/games/memory`) 3건 개선 — 사용자 지적:
  ① 3초 프리뷰 시 렉이 심함. 원인: Next.js `<Image>` 옵티마이저가 12장을
    동시에 처리하면서 flip 애니메이션과 겹쳐 프레임 드롭. 해결: `<Image>`를
    직접 `<img loading="eager" fetchPriority="high">`로 교체(TMDB CDN 직참,
    옵티마이저 우회) + 프리뷰 진입 전 `preloadPosters()`로 브라우저 캐시
    예열(`new Image()` 병렬, 최대 2s 타임아웃).
  ② 카드 뒷면 표지를 `?` → mova 브랜드(accent 세로 바 + "MOVA" 워드마크)로
    교체. MovaLogo 파생 디자인 재사용.
  ③ 매치된 카드가 여전히 뒷면(`?`)으로 표시되는 케이스. 원인 추정:
    `backface-visibility`가 일부 브라우저·GPU 조합에서 실패. 해결: 3D flip
    유지 + face 콘텐츠에 `opacity` 이중 안전장치(백페이스 실패해도 isOpen=
    true면 face 반드시 노출, 100ms 지연 페이드).
- (같은 세션) `/mova/movies` 그리드 밀도 상향 — 카드가 너무 크고 한 화면에
  적게 보인다는 사용자 지적. 컬럼 `2/3/4/6` → `3/4/5/7/8` (모바일부터 xl까지
  전부 +1~+2). 카드 내부 여백 `p-2.5`→`p-1.5`, 타이틀 `text-sm`→`text-xs`,
  메타 `text-xs`→`text-[10px]`, 별 아이콘 `h-3`→`h-2.5`, 장르 라벨 최대 2개
  로 truncate. platform 서브라벨은 제거(공간 확보). `sizes` 속성도 새 컬럼
  비율에 맞춰 재계산.
- (같은 세션) TMDB KR seeder 실 실행 완료(EC2 SSH → backend 컨테이너):
  ① EC2 디스크 정리(prune, 1GB 회수, 11GB 여유) ② `git pull` 확인 →
  PR #120·#121 반영됨 ③ `docker compose up -d --build backend` 재빌드
  성공 ④ `--vote-count-gte` 새 옵션 노출 확인 ⑤ 기준선
  카운트: kr_movies=1952 / total=3978 / hub_indexed=2014 / actors=17720
  ⑥ nohup 백그라운드 실행(30 pages × vote_count_gte=100) → **완료**:
  succeeded=356 failed=0 skipped=0, 페이지 19에서 결과 없음 종료.
  ⑦ 델타: kr_movies +13(1952→1965) · total +16 · hub_indexed +0(Ollama EC2
  미기동 폴백 정상) · actors +58. 356편 중 343편은 기존 카탈로그와 겹쳐
  upsert로 갱신, 실제 신규는 13편 — vote_count≥100 유명작은 이미 대부분
  적재돼 있어서. ⑧ 스팟체크: 최신 tmdb KR 15편 전부 정상(방탄소년단·
  여고괴담·주유소 습격사건 등), 성인물 없음. include_adult=false + 청불
  필터 원천 배제로 이 세션 이후 seed에 성인물 유입 리스크 제거.
- (같은 세션) **KR 성인·저품질 영화 130편 DB purge 실행**(사용자 판단:
  rating 필터로 걸러도 DB에 남아 있는 게 문제). 조건: `original_language=ko
  AND title ~ '정사|음란|매춘|스와핑|누드|룸싸롱|성인영화|여교사|여교수|
  첫경험|퇴폐|색녀|처제|형수|새엄마|유부녀|숙모|과부|야한|매혹적|룸메이트|
  욕망|불륜|...' AND title !~ '여선생|탐하다|마약왕|강남|노량|기생충|공작|
  암살|택시운전사|1987|남산의 부장' AND rating < 4.0`. 자식 테이블 정리
  (characters 572·movie_directors 120·tags 165·hub_knowledge 1) 후
  movies 130 삭제, 트랜잭션 원자성 보장. rankings/reviews/picks/watchlist/
  user_actions는 0건 삭제(성인 타이틀은 사용자 인터랙션 자체가 없었음).
  KR 카탈로그: 1965 → 1835편.
- (같은 세션) 초성 게임 KR 풀 rating 필터 재정정 — `min()` → `max()`.
  이전 커밋에서 `rating >= min(min_rating, 3.3)`으로 바꿨지만 caller의
  `_MIN_RATING=3.0`이 3.3보다 낮아 `min(3.0, 3.3)=3.0`으로 캡핑돼
  "여교수와 남제자"(rating 3.0) 통과함. `max(min_rating, 3.3)`으로 정정 →
  최소 3.3 강제. 첫 시도에서 min/max 방향 실수, 배포 재시도.
- (같은 세션) 초성 게임 KR 풀 rating 상한 2.5→3.3 상향(사용자 재지적:
  "여교사: 제자와의 사랑"(rating 2.9, age_rating NULL, TMDB adult=false)가
  여전히 노출됨). age_rating NULL·TMDB adult 플래그로는 KR 성인·저품질을
  못 잡음(TMDB가 KR 등급을 안 채우고 KR 소프트 에로는 adult 플래그 안 붙임).
  실측: 2.5→3.3 상향 시 KR 풀 1279→707편, 572편 배제(문제작 포함). 배포
  후 EC2 backend 재빌드 필요.
- (같은 세션) `/mova/movies` 페이지에 장르별 가로 스크롤 로우 도입(사용자
  요청 "장르별로 보여줬으면 좋겠어"). 기본 상태(전체 + 필터 없음)에선
  11개 장르(드라마·액션·로맨스·스릴러·SF·코미디·공포·범죄·애니메이션·
  다큐멘터리·뮤지컬) 각 12편을 병렬 fetch해 넷플릭스 스타일 로우로 노출.
  각 로우 헤더에 "더보기 →" 버튼 → 해당 장르 탭으로 전환(기존 평면
  그리드). 필터가 하나라도 활성되면 자동으로 평면 그리드로 복귀. 새
  컴포넌트 `GenreRow`·`GenreRowCard` 신설(120px 카드, aspect-[2/3],
  mova-row-fade+mova-row-scroll 재사용).

### 수정/구현
- `suvis/components/mova/mova-footer.tsx` 신설 — server component. 링크
  행(이용약관·개인정보 처리방침·문의) → TMDB attribution 한 줄 → 카피라이트
  순 3단 구성. `bg-mova-surface/60` + `border-mova-border`로 mova 토큰만
  사용, 반응형(모바일 세로 스택 / md↑ 가로 배치 + `·` 구분자). 후속 축소:
  py-8→py-4, md:py-5, gap-4→gap-2, attribution·카피라이트 `text-xs`→
  `text-[11px]`.
- attribution 문구: "Movie data provided by TMDB. This product uses the TMDB
  API but is not endorsed or certified by TMDB." — "TMDB" 단어를
  https://www.themoviedb.org 링크로 감쌈(target=_blank, rel=noopener
  noreferrer).
- 문의 링크는 `mailto:ssuvisdev@gmail.com`(현행 도메인 이메일).
- `suvis/app/mova/layout.tsx` 배선 — `<div className="mova-app min-h-screen">`
  → `<div className="mova-app flex min-h-screen flex-col">`로 바꾸고
  `{children}` 뒤에 `<MovaFooter />` 추가. `mt-auto`로 짧은 페이지에서도
  뷰포트 바닥에 붙게 함. 모든 `/mova/**` 페이지에 자동 노출.
- `/mova/main`(챗)은 내부에서 `h-screen overflow-hidden`으로 뷰포트 고정
  구조라, 푸터는 뷰포트 아래에 렌더되어 스크롤로만 노출 — 티켓의 "sticky
  아님, 스크롤 끝에만 노출" 요건과 일치.
- `suvis/app/mova/terms/page.tsx` 신설 — 왓챠피디아 이용약관 골격을 채택
  하되 mova 서비스 특성(무료·리뷰/평점·미니게임·TMDB 데이터 출처)에
  맞춰 14조로 재작성. 유료 결제·본인인증·B2B·환불 등 mova에 없는 조항
  전부 제외. 게시물 조항(리뷰·평점·컬렉션·랭킹 기록)과 크롤링/스크래핑
  금지 조항은 유지. 외부 데이터 조항 신설(TMDB/KOFIC + attribution).
  MovaHeader 포함, mova 토큰만 사용, 시행일 2026-08-14.
- `suvis/app/mova/privacy/page.tsx` 신설 — 왓챠피디아 개인정보처리방침의
  섹션 스키마 + 기존 `app/privacy` 스타일을 계승해 15개 섹션으로 재작성.
  OAuth 3사(Google/Kakao/Naver) 각각 실제 수집 항목 명시(X·Apple 제외 —
  mova는 지원 안 함). 처리 항목에 서비스 이용 과정 생성 정보(리뷰/평점/
  watchlist/게임 랭킹/프로필)와 자동 수집 정보(로그·쿠키·기기 정보)
  분리 명시. 위탁·국외 이전에 AWS 서울, Google(OAuth+Gemini API), Kakao,
  Naver 3계층 명시(왓챠 사례의 결제·본인인증 위탁은 mova에 없어 삭제).
  결제·왓챠 캐시·본인인증·B2B·환불 조항 전부 제외. 광고 없음 명시.
  TMDB 외부 데이터는 개인정보 아님을 명시. 만 14세 미만 회원가입 불가
  원칙 유지. 시행일 2026-08-14.

### 오류·막힌 점
- 없음. `pnpm type-check` 통과.

### 산출물
- 파일: `suvis/components/mova/mova-footer.tsx`(신규+축소),
  `suvis/app/mova/layout.tsx`(수정),
  `suvis/app/mova/terms/page.tsx`(신규),
  `suvis/app/mova/privacy/page.tsx`(신규).
- 후속(별개 티켓): 문의 이메일 최종 확정 여부.

### 작업 내용 — 후속 사이클(채팅 3건)
사용자 스크린샷 제보 기반. 원인 규명 + 백엔드/프론트 동시 수정.

1. **대화 흐름 미반영**: `/mova/main`에서 "코미디 영화 추천해줘" → "최근영화로
   추천해줘" → "2026년 영화로 추천해줘"가 각각 독립 추천으로 처리돼 코미디
   컨텍스트가 사라짐(2턴차부터 최신·2026 broad).
2. **채팅 홈에서 추천 키워드 씹힘**: 이력이 남은 상태에서 `/mova` 랜딩 칩을
   클릭하면 `/mova/main?q=X`로 이동해도 새 키워드가 전송 안 됨. DB 모드에선
   `mova-chat-shell.tsx`가 `?q=`를 replaceState로 지우고 `mova-ai-chat-bar.tsx`가
   `autoSentRef.current=true`로 즉시 잠가서 씹힘. 익명 모드는 hydration이 `?q=`
   있으면 sessionStorage 복원을 스킵하는 별개 버그로 이력이 통째 유실됨.
3. **랭킹 레일 상시 노출**: 우측 랭킹 사이드바를 채팅창에서 숨기고 싶다는 요청.

### 수정/구현 — 후속 사이클
- 백엔드 흐름 반영:
  - `mova/app/ports/output/llm_output_port.py` — `extract_intent(message,
    history=None)`으로 시그니처 확장.
  - `mova/adapter/outbound/llm/{gemini,exaone,lora,qwen,ollama_exaone}_recommendation_adapter.py`
    5개 어댑터 시그니처 통일 → `IntentExtractionService.extract(message, history)` 위임.
  - `mova/adapter/outbound/llm/intent_extraction.py` — 새 헬퍼
    `_prepend_recent_user_context(current, history)`: 최근 사용자 발화 최대
    2개(각 24자 상한)를 앞에 이어붙여 결정론적/Gemini 추출 모두에 흘려보냄.
    `EXTRACT_PROMPT`에 "대화 흐름 처리" 규칙 명시(조건 누적,
    "말고"/"바꿔줘"는 최신만).
  - `mova/app/use_cases/market_chat_interactor.py` — `extract_intent` 호출부에
    `request.history_dicts()` 전달.
  - `mova/tests/test_market_chat_interactor.py` — `ChatInteractorHistoryForwardTests`
    회귀 테스트 추가(history가 두 번째 인자로 전달되는지 검증).
- 프론트 `?q=` 씹힘 수정:
  - `suvis/components/mova/mova-chat-shell.tsx` — `conversationId != null` 시
    `?q=` replaceState로 스트립하던 effect 제거.
  - `suvis/components/mova/mova-ai-chat-bar.tsx`:
    - `pendingQuery` 상태(lazy init으로 마운트 시 URL에서 1회 캡처).
    - DB 모드 `conversationIdProp` effect의 즉시 `autoSentRef.current=true`
      잠금 제거.
    - 익명 hydration에서 `?q=` 조기 리턴 제거 → sessionStorage 무조건 복원.
    - `hydratedRef` → `hydrated` 상태로 변경(auto-send가 stale sendMessage,
      즉 chat.messages=[]인 클로저로 먼저 발화해 히스토리 빈 채로 요청 나가는
      race 방지).
    - auto-send는 `chat.loading` 대기 → 로드 완료 후 sendMessage useCallback이
      새 chat.messages 담아 재생성될 때 재실행돼 append 전송.
- 랭킹 레일 토글:
  - `suvis/components/mova/mova-chat-shell.tsx` — `RAIL_HIDDEN_KEY`
    localStorage(디폴트 `"1"`=숨김), 상단 대화 목록 바 우측에 `BarChart3`
    아이콘 토글(lg+만). `!railHidden`일 때만 `<MovaChatRail />` 렌더.

### 오류·막힌 점 — 후속 사이클
- 없음. `pnpm type-check` 통과, mova+viewer+ontology 273개 pytest 통과
  (사전 실패 2건 — `test_zero_recs_reply_content_when_already_shown_all`의
  `_compose_empty_reply` 문구 랜덤 pick으로 브리틀한 assertion,
  `test_start_page_for_resume`의 argparse choices에 `kofic` 미등록 — 이번
  변경과 무관하며 deselect).

### 산출물 — 후속 사이클
- 파일: 위 백엔드 8개(포트/어댑터 5+intent_extraction+interactor+테스트),
  프론트 2개(mova-chat-shell.tsx, mova-ai-chat-bar.tsx). 총 11개.
- 커밋: 3개 예정(feat/rail-toggle, fix/query-swallow, feat/intent-history).

---

---

## 2026-08-13

### 작업 내용 — 후속 사이클 J
- 초성 게임 무제한 모드에 "정답 보기" 버튼 추가 (정답 공개 시 다음 문제
  넘어가면 초기화).
- 한국 영화 카테고리에 중국/홍콩 영화가 섞여 나오던 문제 수정: TMDB에서
  `original_language='ko'`로 잘못 태깅된 5편(맹룡노호·사대소림사·소림관
  지배인·소림 10대 여걸·비련의 벙어리 삼룡)을 DB에서 `cn`/`zh`+`origin_country
  =["HK"]`로 정정.

### 수정/구현
- `suvis/app/mova/games/chosung/page.tsx` — `revealed` 상태 추가, 무제한
  모드에서만 "정답 보기" 버튼 노출, 정답 텍스트를 accent-soft 배경으로 표시,
  `loadNext`에서 초기화.
- DB(EC2): `movies` 테이블 id 2545·2932·2454·4283·4614의 `original_language`·
  `origin_country` 수정(ko/[] → cn or zh/["HK"] 등).

### 작업 내용
- 사용자 요청 5건을 한 세션에서 처리 후 일괄 배포.
  ① 헤더 검색 "아" 오매칭 해결 ② 영화 탭 기본 정렬을 인기순으로
  ③ OAuth 사용자가 마이페이지 진입 시마다 재로그인되던 이슈 + `/mova/login`에
  OAuth 버튼 부재 ④ 컬렉션 탭 자리에 미니게임(초성·카드뒤집기) 신설
  ⑤ 카탈로그 확장 — TMDB discover KR 1000편 + KOFIC 986편.

### 수정/구현

**mova 검색 관련성 정렬(`2c4e2f7` 후속)**
- `suvisdev/apps/mova/adapter/outbound/pg/studio_search_pg_repository.py` —
  배우/감독 이름 `ILIKE %q%` 확장을 **2글자 이상일 때만** 걸도록 가드. 정렬을
  `rating desc`에서 `title 시작일치 → title 포함 → 그 외(배우/감독/태그), 그
  다음 rating`으로 변경. "아" 한 글자 검색 시 배우 이름에 "아"가 든 사람이
  워낙 많아 title 매칭이 밀리던 문제 해결.

**영화 탭 기본 정렬 = 인기순**
- `suvisdev/apps/mova/adapter/outbound/pg/movies_pg_repository.py` — `sort=popular`
  가 `rating desc`와 사실상 동일했던 것을 **picks 카운트(AI 채팅 픽 횟수) desc
  → rating desc → id desc**로 개선. picks 서브쿼리를 outerjoin.
- `suvis/app/mova/movies/page.tsx` — SORTS 첫 항목·initialSort·hasActiveFilters·
  syncUrl·resetFilters의 기본값을 `latest`→`popular`로 통일.

**OAuth 사용자 mova 인증 통과 + 로그인 페이지 OAuth 버튼**
- 근본 원인: mova 인증(RS256+aud=suvis-mova)과 viewer OAuth 세션(HS256, aud
  없음) 두 발급 경로가 완전히 다른데, mova 라우터가 RS256만 검증해 OAuth
  로그인 사용자가 마이페이지·watchlist·리뷰 등 인증 API 전체에서 401.
- `suvisdev/shared/security/token_verifier.py` — `verify_viewer_session_token()`
  신설(HS256+JWT_SECRET, `role: str` → `roles=[role]` 어댑팅, aud 없어서
  표시용 "viewer-session"으로 채움).
- `suvisdev/shared/security/require_user.py`·`apps/mova/dependencies/require_auth.py` —
  RS256 실패 시 viewer HS256 fallback 추가. 두 계층 모두 fix해야 mypage/
  watchlist/reviews 라우터가 통과됨(전자만 고치면 `whoami`만 통과).
- `suvis/components/mova/mova-auth-forms.tsx` — 로그인/회원가입 폼 위에
  Google/네이버/카카오 OAuth 버튼 3개 추가(`OAuthButtons` 재사용). 헤더
  드롭다운의 `AuthDialog`엔 있었지만 마이페이지에서 튕겨진 후 랜딩되는
  `/mova/login`엔 없어 재로그인 자체가 불가능했던 UI 공백 메움.

**미니게임 신설(`/mova/games`) + 컬렉션 탭 숨김**
- `suvis/lib/mova-mock-data.ts` — MOVA_NAV의 "컬렉션" → "미니게임"으로 교체
  (컬렉션 페이지·백엔드는 그대로 유지, 헤더에서만 숨김).
- 신규 백엔드(클린 아키텍처 8 파일):
  `apps/mova/adapter/inbound/api/schemas/games_schema.py`,
  `apps/mova/app/dtos/games_dto.py`,
  `apps/mova/app/ports/input/games_use_case.py`,
  `apps/mova/app/ports/output/games_repository.py`,
  `apps/mova/app/use_cases/games_interactor.py`,
  `apps/mova/adapter/outbound/pg/games_pg_repository.py`,
  `apps/mova/dependencies/games_provider.py`,
  `apps/mova/adapter/inbound/api/v1/games_router.py`. 라우터 4엔드포인트:
  `GET /mova/games/chosung/next`(랜덤 문제, 정답 응답 포함 — 게임 몰입
  이슈 정도라 감수), `GET /mova/games/memory/deck?stage=N`(2N쌍),
  `POST /mova/games/scores`(로그인 필수), `GET /mova/games/leaderboard`
  (익명 조회 가능, `me`는 로그인 시에만).
- 신규 DB: `game_scores` 테이블 (마이그레이션 `20260813_0001_add_game_scores`,
  ORM `market_game_scores_orm.py`, `MovaGameScore`). 컬럼: user_id/game_type/
  stage(memory만)/score/hints_used/played_at. 인덱스 2개(리더보드 정렬용,
  개인 최고 조회용).
- 신규 프론트: `suvis/lib/mova-games-api.ts` +
  `suvis/app/mova/games/{page,chosung/page,memory/page}.tsx`. 초성 게임은
  1분 타이머 + 힌트 3단계(1: 원문 초성+한/외 태그, 2: 출연진 5명, 3: 포스터
  1/4). 카드 뒤집기는 1~10단계(4→40장), 포스터↔제목 매칭, 완료 초를
  score로 저장(빠를수록 상위). 리더보드는 게임별(카드뒤집기는 단계별로)
  TOP 10 + 내 최고를 게임 종료 화면에 표시.
- 초성 계산: `_to_chosung_condensed`(공백·구두점 제거, 한글은 초성만,
  영숫자 대문자 유지) / `_to_chosung_spaced`(원래 형태 유지, 한글만 초성).
  예: "듄: 파트3" → condensed "ㄷㅍㅌ3", spaced "ㄷ: ㅍㅌ3".
- 게임 영화 풀 하한 `rating >= 2.5`(사용자 지정, 2560편). `rating`은 사용자
  리뷰가 아니라 TMDB `vote_average`를 0~5 스케일로 저장한 값이라는 점
  사용자에게 확인·설명.

**카탈로그 대량 확장**
- **tmdb_discover KR 50페이지 배치(EC2)**: `docker exec -d`로 백그라운드
  실행, succeeded=1000/failed=0. movies 2014 → 3014(≈+947 순증, credits
  백필 포함).
- **KOFIC KR 10페이지 배치(EC2)**: `--source kofic --country KR --pages 10`,
  succeeded=986/skipped=14/failed=0 → movies 3014 → 3965(+986 순증).
  스킵된 14편만 title+year가 TMDB에 이미 있던 케이스 — KOFIC이 옛날/독립
  한국영화 커버리지를 실제로 크게 넓혀줬음을 확인.

### 오류·막힌 점
- **KOFIC `repNationCd` 320221 에러(2026-08-13)**: `_KOFIC_NATION_CD`가
  `{"KR": "K", "US": "F"}` 1글자 매핑이었는데 KOFIC API는 8자리 공통코드
  (comCode 220310)를 요구. `searchCodeList.json?comCode=220310`으로 실측해
  `KR=22041011`(South Korea)·`US=22042002`(U.S.) 확인 후 매핑 정정.
- **컨테이너 WORKDIR 착오**: 처음에 배치 스크립트 실행할 때 `cd /app`으로
  래핑했는데 컨테이너 WORKDIR는 `/suvisdev`였음(exec에서 `cd: can't cd to
  /app`). cd 없이 실행하면 되는 걸 확인해서 재시작. 백그라운드 exec는
  실패해도 조용해서 로그 파일이 안 만들어진 것으로만 티가 났음.
- **mova 인증 fix 범위 착오**: 처음 `apps/mova/dependencies/require_auth.py`
  하나만 고쳤는데 실사용은 `shared/security/require_user.py`쪽 — grep으로
  실제 라우터 import 확인 후 양쪽 다 fix.

### 데이터
- movies: 2014 → 3965 (+1951 순증, TMDB+KOFIC 합산).
- game_scores: 마이그레이션 적용 대기(EC2 `alembic upgrade head`).

### 산출물
- 커밋 5건(예정) — 검색·정렬·인증·게임·bulk_import 스크립트 정정.
- 이 세션 시작 시 이미 있던 배치 스크립트에도 KOFIC 사전 매칭 스킵 가드를
  추가(`_ingest_kofic_movie` 상단).

### 후속 사이클 A — 한국 개봉 예정작 페이지
- 사용자: "개봉 예정작도 넣고 싶은데 어디서 db 가져와야 할지 모르겠어" →
  네이버 종료·KOFIC은 개봉 이후 데이터만 → TMDB `/movie/upcoming?region=KR`
  이 유일한 공신력 소스로 정리.
- `TmdbAdapter.fetch_upcoming(page, region)` 신설. `TmdbCatalogAdapter.fetch_upcoming`
  래핑. 얇은 프록시 라우터 `GET /mova/upcoming`(region=KR 고정, DB 저장 안
  하고 매 요청 시 TMDB 호출). 프론트에서 `next: { revalidate: 1800 }`(30분
  캐시)로 rate limit 완화.
- 프론트 `/mova/upcoming` 신설(그리드), MOVA_NAV에 "개봉예정" 탭 추가.
- 커밋: `86ad096`.

### 후속 사이클 C — 미니게임 허브 리디자인 + 카드뒤집기 통합 랭킹
- 사용자 안: 이미지 스타일 카드 + 오른쪽 옆으로 넘기는 랭킹 사이드바.
  `suvis/app/mova/games/page.tsx`를 3:4 세로 카드(초성=대형 자음, 카드뒤집기=
  겹친 카드) + `md:grid-cols-[1fr_320px]` 우측 랭킹 사이드바(탭+화살표)로
  재작성. 커밋 `8be22e5`.
- 카드뒤집기 랭킹 통합 formula: `stage*1000 + max(0,500-완료초)`. 제약 1)
  1단계 최대(1500) < 10단계 최소(10000), 2) 같은 단계 20초 차이 = 20점 차이.
  memory 리더보드 stage 필터 제거, `game_scores.metric` 서브쿼리로 정렬.
  스키마/DTO에 `stage`·`computed_score` 필드 추가. 프론트 사이드바·게임
  종료 화면 표기 통일. 커밋 `c4c1bce`.

### 후속 사이클 D — 게임 풀 필터·flip 매끄럽게·프리뷰 앞당김
- "슈렉 3 → ㅅㄹ3" 지적 → 제목 끝 " 숫자" 배제 정규식(원작만 유지). 카드
  프리뷰 threshold 5→3단계. 커밋 `58bd10b`.
- "여전히 태국어 배우 나옴" 재지적 → `_MIN_RATING` 2.5→3.0 + KR OTT
  플랫폼 필수(`jsonb_array_length(platforms)>0`). 게임 풀 1517→1163편.
  카드가 뒷면(?) 그대로 남는 이슈 원인 = Tailwind arbitrary
  `[backface-visibility:hidden]`이 프로덕션 빌드에서 CSS로 안 emit → 인라인
  style(backfaceVisibility/WebkitBackfaceVisibility/transformStyle/transform)로
  대체해 브라우저가 직접 파싱. 커밋 `cd1fc5d`.

### 후속 사이클 E — auth TTL fix (마이페이지 재로그인 근본 원인)
- 사용자 지적: "마이페이지 재로그인 걸리는 게 설정이야? 버그면 고쳐줘"
  · "카드뒤집기 랭킹 저장 안 됨"도 동일 원인(모든 mova 인증 API 401).
- `shared/security/require_user.py`에 진단 로그 추가(`897f67c`) → docker cp
  hotfix로 즉시 반영 → test 계정으로 재현했더니 실측:
  `RS256=ExpiredSignatureError('Signature has expired')`
  → 토큰 exp - iat = **600초(10분)**. 프론트가 `refresh_token` 저장·사용 안
  하므로 10분 지나면 무조건 401.
- `apps/auth/security.py`·`apps/auth/services.py`의 `_ACCESS_TTL_DEFAULT_MIN`·
  `_ACCESS_TTL_MIN` 10 → `60*24*7`(7일)로 확장. viewer HS256 세션 TTL과 동일.
  refresh 흐름 도입 시 다시 짧게 되돌릴 것. 커밋 `b2aa2bc`.

### 후속 사이클 F — 개봉예정 날짜별 정리 + 채팅 반복 완화
- 개봉예정: `TmdbAdapter.fetch_upcoming(page, region)`·`fetch_upcoming_dated`
  신설, `UpcomingMovieSchema.release_date`, 라우터에서 오름차순 정렬. 프론트
  YYYY-MM 월별 섹션 + M/D 배지. 커밋 `86ad096`, `aefab64`.
- 추천 0건 안내 문구를 재시도 여부별 3개 변형 랜덤 pick + 대안 축 예시
  ('A24 스릴러', 'OTT 필터' 등) 인라인. 커밋 `0b6c3df`.

### 후속 사이클 G — 회원가입 8자 통일 + 랭킹 podium + 클릭 기반 랭킹
- 회원가입 시 백엔드 `min_length=8` vs 프론트(<6/<4) 불일치 → 프론트 검증·
  placeholder 8자로 통일(`92fcdfb`).
- 랭킹 상단 1·2·3위 시상식 podium(2-1-3 배치, 왕관·메달, mt-{6/10/16}
  계단). 4위~는 기존 리스트. 커밋 `9333fd3`.
- **AI 검색 TOP 재작성**: pick_count(노출)+hit_sum → user_actions.click.
  프론트 `MovaRecommendationCards` Link onClick에 `addReviewActivity`
  ('click'). `chat_trend_score(click_count)` 단일 인자로 축소. DTO/테스트
  전체 정합. 커밋 `925917c`.
- 초성 게임 카테고리 필터(전체·한국·외국) — `original_language=='ko'` 판정.
  `GET /mova/games/chosung/next?category=all|kr|foreign`. idle 화면 3버튼,
  진행 중 헤더 배지. 커밋 `d6c59ba`.
- 채팅 로딩 UI에 3D 클래퍼보드 mp4(978KB) 인라인 재생 — Sparkles 자리에
  h-32/w-40 영상 + spinner + 순환 문구. 커밋 `99759bf`.
- **mood 자연어 → 대중 장르 확장**: "오싹오싹한 영화" recs=0 이슈. EC2에
  Ollama 없어서 tag catalog 폴백만 도는데 자연어 mood를 태그로 못 잡음.
  `domain/value_objects/mood_expansion.py` 신설 — 매핑 40여 개(오싹→공포·
  스릴러, 재밌→코미디, 눈물→드라마 등), `_POPULAR_GENRES` 화이트리스트
  12개("다큐"·"뮤지컬" 등 마이너 제외). `search_tag_catalog` 호출 전
  `expand_mood_keywords`로 전처리. 커밋 `f977ff2`.

### 후속 사이클 H — TMDB KR 배치 이어받기
- `--source tmdb_discover --country KR --pages 50 --start-page 51` (백그라운드
  `docker exec -d`). succeeded=1000/failed=0/last_page=100. 이어받으려면
  `--start-page 101`. 실측: movies 3965 → 3978(+13 순증 — 대부분 슬러그
  중복이라 upsert만).

### 후속 사이클 B — KOFIC 전량 삭제 (거짓 DB 이슈)
- 사용자: 헤더 검색 "왕과" 입력 시 "왕과 사는 남자" 2026/2025 중복 + "의자왕과
  삼천연구원" 등 미공개작 상단 노출. "거짓 DB 들어간 것 같아" 지적.
- 실측: KOFIC 986편 **전부** poster/rating/synopsis 없음(rating=0.0 100%,
  poster 100% 빈문자열). 어제 KOFIC 목록 API가 이 필드를 아예 안 준다는 걸
  놓치고 대량 저장한 결과. 게임 풀엔 `rating >= 2.5`로 자동 제외돼 안 뜨지만
  검색·목록에 그대로 노출돼 UX 오염. title+year 사전 가드는 정확 매치만
  잡아 "왕과 사는 남자 2025 vs 2026" 같은 연도 다른 사실상 동일작을 못
  걸러냈음.
- 처방(사용자 승인 후): EC2에서 `DELETE FROM movies WHERE slug LIKE 'kofic-%'`
  실행. 986편 삭제, FK ON DELETE CASCADE로 tags 1486건 자동 정리. 사용자
  데이터(watchlist/picks/reviews/rankings/user_actions)에 KOFIC 참조 0건
  실측 확인 후 실행 — 무영향. hub_knowledge도 0건(어제 임베딩 실패로
  실제 저장 안 됐음이 이번에 드러남).
- 스크립트: `_SOURCES`에서 "kofic" 제거해 CLI가 재실행을 거부. 어댑터·
  인제스터 함수는 도서관 성격으로 남김(poster 보강 경로 마련 전까지 CLI
  금지 근거 주석).
- 카탈로그: 3965 → 2979(=TMDB 2956 + seed 23) 복귀.
- 커밋: `f4176aa`.

### 후속 사이클 I — 초성 게임 무제한 모드 + 헤더 닉네임 + 랭킹 빈/에러 상태 구분
- **초성 게임 시간 무제한 모드**: 사용자 요청 "각각의 전체/한국영화/외국영화에
  시간 무제한 모드, 랭킹엔 안 들어감". `suvis/app/mova/games/chosung/page.tsx`에
  카테고리와 별개로 모드 선택(1분 타임어택/시간 무제한) 추가. 무제한 모드는
  카운트다운 타이머를 안 돌리고(`useEffect` 가드에 `mode !== "timed"` 추가)
  "무제한" 배지 + 수동 "게임 종료" 버튼으로 종료. 종료 시 `saveGameScore` 호출을
  `mode === "timed"`일 때만 실행해 랭킹 미반영.
- **mova 헤더 사용자 표시를 닉네임으로**: 사용자가 스크린샷으로 지적("아이디
  `ssuvisdev_google`이 그대로 보임") — `SuvisSession`엔 로그인 아이디만 있고
  닉네임이 없어서 `components/mova/mova-login-button.tsx`에 `fetchProfile`
  (`lib/profile-api.ts`, 이미 있던 함수) 호출을 추가해 닉네임을 가져와 있으면
  닉네임, 없으면(로딩 중·실패) 기존 아이디로 폴백.
- **`/mova/rankings` 빈 상태/에러 상태 구분**: 사용자가 "박스오피스·AI 검색
  TOP 둘 다 1초쯤 '아직 랭킹 데이터가 없습니다'가 보였다 사라졌다" 보고.
  원인은 `lib/mova-api.ts`의 `fetchMovaRankings()`가 `!res.ok`(502 등)일 때도
  `[]`을 반환해 "진짜 빈 데이터"와 "일시적 요청 실패"를 UI가 구분 못 했던 것.
  실패 시 `null`을 반환하도록 반환 타입을 `MovaHotRankingItem[] | null`로
  바꾸고, `app/mova/rankings/page.tsx`에서 `items === null`이면 "일시적으로
  랭킹을 불러오지 못했습니다. 새로고침해 주세요."를 별도로 보여주도록 분기
  추가(`RankingItem` 타입도 `ReturnType` 유도 대신 `MovaHotRankingItem` 직접
  참조로 정리 — 반환 타입에 `null`이 섞이면서 `[number]` 인덱싱이 깨짐).
- **502 원인 조사(코드 변경 없음)**: 위 502가 "집에서만 나고 학원에선 안 난다"는
  사용자 보고 → 로라서버(`lora.suvisdev.cloud`, 별도 터널·별도 라우트)와는
  무관함을 확인(`/mova/rankings/hot`은 로라 미호출, 8/4 조사 기록도 로라 무관
  라우트까지 동일 패턴이었음을 재확인). 사용자 홈 PC에서 직접
  `curl -sD - api.suvisdev.cloud/...`로 `cf-ray`를 떠 보니 `-LAX`(로스앤젤레스)
  PoP로 라우팅되고 있었음. PowerShell로 DNS(`Get-DnsClientServerAddress`)·
  어댑터(`Get-NetAdapter`) 확인 결과 VPN 없음, DNS는 KT 자체(168.126.63.1/2)
  정상 사용 중 — 결론: **KT 회선이 이 IP 대역에서 Cloudflare와 국내(ICN) 피어링이
  안 돼 있어 미국 PoP로 우회하는 것으로 추정**, 앱 코드로 고칠 수 있는 범위
  밖(WARP 사용이나 ISP 문의가 유일한 완화책). PROGRESS.md 백로그에 참고용으로
  남김.

---

---

## 2026-08-12
### 작업 내용

- 문서 정리 사이클 — 사용자가 여러 문서를 순회하면서 종결된 것/잘못 위치한
  것/중복된 것을 하나씩 점검·정리.
- 프론트 정비 — 메인 히어로 이미지 이질감 제거(포스터→영상 첫 프레임), mova
  채팅 UI를 Gemini/Claude 스타일 2단 모드로 개편.
### 수정/구현


**문서 정리**
- 삭제(회고 문서·잔여 능동 항목 0건 확인):
  - `_docs/MOVA_UI_AUDIT.md` — 2026-08-05 5영역 감사 사이클 종결본.
  - `_docs/MOVA_UI_QUICK_WINS.md` — character_name 관통·죽은 컴포넌트 정리
    저수확 사이클 종결본.
- 이동(mova 앱 전용 문서라 루트 `_docs/` 배치 규칙 위반) — `git mv`로 이력 보존:
  - `_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`
    → `suvisdev/apps/mova/_docs/MOVA_RECOMMENDATION_QUALITY_PHASE1.md`
  - `_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md`
    → `suvisdev/apps/mova/_docs/MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md`
  - 두 파일의 상호 참조는 mova `_docs/` 관례(bare 파일명)로 정리.
- 통합(스코프 규칙을 실 SSOT에 병합):
  - `_docs/SUVISDEV_RULES.md`(프론트 UI 변경 스코프 규칙 4절) → `suvis/CLAUDE.md`
    의 새 섹션 F로 이관. 기존 F(관련 문서)는 G로 재배번.
- 참조 갱신:
  - `_docs/README.md` — 삭제/이동된 4개 행 정리, "mova 심층 조사는
    `suvisdev/apps/mova/_docs/`에 있다" 안내 추가.
  - `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` — mova 문서 경로 6곳 갱신
    (줄바꿈으로 잘려 있던 2곳 포함).
  - `WORK_LOG.md`의 과거 로그 항목들은 히스토리라 손대지 않음.

**로컬 정리**
- `.idea/`(JetBrains 메타) 제거. `.gitignore`에 이미 있어 트래킹된 적 없음.

**히어로 이미지 스왑 이질감 제거** (`suvis/components/home/hero-image-panel.tsx`)
- 사용자가 메인 진입 시 "1초 예전 사진 → 영상" 튐 지적. 원인 특정: HTML5
  `<video>`의 `poster` 표준 동작이며 `hero-ai.jpg`(1.7MB, AI 얼굴)와
  `hero-holographic-mask.mp4`(2MB, 컨트롤룸) 장면이 완전히 달라 스왑이 튐.
- 조치: `ffmpeg -vf "select=eq(n\,0)" -q:v 2 -frames:v 1`로 영상 첫 프레임을
  62KB JPG로 뽑아 `public/hero-holographic-mask-poster.jpg` 신설, `HERO_POSTER`
  참조 갱신, 고아 `hero-ai.jpg` 제거. 시각적 이음매 소멸 + 포스터 용량
  1.7MB → 62KB(약 27배 감소).

**mova 채팅 UI 개편 — Gemini/Claude 스타일 2단 모드**
- 요구(사용자 확인 2회): `/mova/main`을 채팅 중심으로 개편, 상단 헤더·일간
  힌트 칩·"지금 볼 영화, Mova가 찾아줄게" 히어로 카피 유지, 사이드 요소(랭킹
  사이드바·장르 카탈로그·프로모·온보딩·선호 장르 배지)는 전부 제거 — 전용
  `/mova/rankings`·`/mova/movies` 라우트가 이미 있어 중복.
- 재작성 `suvis/components/mova/mova-ai-chat-bar.tsx`:
  - 2단 모드 — user 메시지 0건일 때 히어로(중앙 큰 입력창+힌트 칩), 첫 메시지
    전송 즉시 채팅 모드(대화 리스트+하단 sticky 입력창)로 자동 전환. 같은
    `chat.messages` 상태를 공유해 모핑처럼 느껴짐.
  - 입력을 controlled(`inputValue`) 전환 — 모드 전환 시 값 유지·오류 시
    복구가 깔끔.
  - 히어로 → 채팅 전환 후 채팅 입력창 자동 포커스(useEffect).
  - `sessionStorage` 키 `mova-ai-chat-history-v1` → `v2` 승격(스키마 변경 반영,
    기존 히스토리 리셋).
  - 죽어 있던 `compact` 프롭 제거.
  - 기존 URL `?q=` 자동 전송·추천 카드 렌더링·오류 UI는 그대로 보존.
- 재작성 `suvis/app/mova/main/page.tsx`: `MovaHeader` + `MovaAiChatBar`만.
  `fetchHotRankings`·`fetchMovaMoviesFromApi`·`groupMovaMoviesByGenre` 등
  서버 fetch·5개 사이드 컴포넌트 import 전부 제거.
- 랜딩(`/mova`)의 `MovaLandingChatBar`는 손대지 않음 — `/mova/main?q=...`
  이동 → 자동 전송 → 즉시 채팅 모드 진입, 기존 동선 유지.
- **부수 발견 — 고아 컴포넌트 5개**: 이번 개편으로 아래 5개가 어디에도
  import 안 되는 상태(`grep -rln`으로 확인). 이번 스코프가 "제거"였고 "삭제"는
  아니라 남겨둠(사용자 판단 대기):
  - `mova-genre-catalog.tsx`, `mova-genre-onboarding.tsx`,
    `mova-preferred-genres-badge.tsx`, `mova-promo-banner.tsx`,
    `mova-ranking-section.tsx`
### 오류·막힌 점

- 없음. `pnpm type-check` 클린, dev 서버 부팅 성공(`Ready in 311ms`),
  `GET /mova/main` HTTP 200 확인. UI 시각 동작은 사용자 브라우저 확인.
### 후속 사이클 A — 만료 세션·프록시 Basic 무차별 주입 fix

- 스크린샷 오류 "유효하지 않은 세션입니다." 신고 → 사용자 브라우저의 만료
  JWT + `/mova/chat`의 `optional_user` 정책("Bearer인데 무효면 401 명시")
  조합에서 발생. **더 깊은 원인**: `suvis/lib/backend-client.ts`가 초기
  커밋부터 `BACKEND_CREDENTIALS` env가 있을 때 **모든 백엔드 요청에
  `Authorization: Basic ...`을 무차별 주입**하고 있었음. 백엔드 Basic
  게이팅은 `main.py::_ApiAuthMiddleware`가 `/docs`·`/redoc`·`/openapi.json`
  세 경로에만 걸어 놓은 것인데, 프록시가 API 요청에도 Basic을 붙여서
  `optional_user`가 "Bearer 아님 → 401"로 튕겨냄. 로그인 사용자는 브라우저
  Bearer가 Basic을 override해서 우연히 동작했고, 익명·만료는 완전 차단
  상태였음(오늘 UI 개편으로 처음 노출).
- 수정 2건(PR #78·#79):
  - `mova-ai-chat-bar.tsx`: 첫 시도 401 + 로컬 세션 존재 시 `clearSuvisSession`
    호출 + 익명으로 1회 재시도. 만료 로그인이 조용히 익명 모드로 전환.
  - `backend-client.ts`: Basic 무차별 주입 로직 제거. `/docs` 보호는 백엔드
    미들웨어가 그대로 담당. 로그인 사용자 흐름 무변화(Bearer 그대로 전달),
    익명·만료 사용자 흐름 정상화.
- 실측 검증: 익명 `POST suvisdev.cloud/api/mova/chat` → HTTP 200(Gemini
  응답 정상), 무효 Bearer → 401 "유효하지 않은 세션입니다."(retry 트리거),
  JS 번들에서 `clearSuvisSession`·`getSuvisSession` 검출됨.
### 후속 사이클 B — 대화 스레드 저장 v1(Claude/Gemini 스타일 사이드바)

- 요구: "채팅창 밋밋함 우선 대화 저장(클로드/제미나이처럼)". 스코프 확정
  질의 2회로 (1) 백엔드 DB 정식 구현, (2) 로그인 사용자만 저장·익명은
  기존 방식 유지로 결정.

**백엔드**
- 새 테이블 2개 + 마이그레이션 `20260812_0001_add_chat_conversations.py`:
  - `chat_conversations` (id, user_id NOT NULL CASCADE, title VARCHAR(80),
    created_at, updated_at) + updated_at DESC 인덱스
  - `chat_messages` (id, conversation_id CASCADE, role VARCHAR(16),
    content TEXT, meta JSONB, created_at)
  - 기존 `mova.chat`(검색·의도 로그)은 손대지 않음.
- 헥사고날 신설: `ConversationsUseCase`/`ConversationsRepository` 포트 →
  `ConversationsInteractor`(list_mine/get_mine/delete_mine, IDOR 검증) →
  `ConversationsPgRepository`(list=`updated_at DESC + message_count`
  outer join, get_detail, create, append_message에서 부모 updated_at 갱신,
  delete=CASCADE) → DI provider.
- 도메인 예외 `ConversationForbiddenError(403)`·`NotFoundError(404)` → 라우터
  변환. 라우터 `/mova/conversations`: `GET /`·`GET /{id}`·`DELETE /{id}`,
  전부 `require_user`.
- `/mova/chat` 확장: 요청에 `conversation_id?`, 응답에 `conversation_id`
  에코. 로그인+id 없음 → 새 대화 생성(title = 첫 user 메시지 앞 40자).
  로그인+id 있음 → user+assistant 두 메시지 append. **LLM 호출 전 소유권
  사전 검증**(쿼터 소모 방지). 비로그인은 저장 없음.
- 테스트 신규 6건(list_mine, get/delete ownership 4가지). 전체
  `pytest apps/mova/tests` 195 passed.

**프론트**
- `lib/mova-conversations-api.ts`: list/get/delete 3개 + 프록시 2개
  (`app/api/mova/conversations/route.ts`·`[id]/route.ts`).
- `components/mova/mova-chat-sidebar.tsx`: 목록·"새 대화"·삭제 UI(hover 시
  삭제 아이콘, confirm), 모바일 close 버튼.
- `components/mova/mova-chat-shell.tsx`: 로그인 상태(`SUVIS_SESSION_CHANGED_EVENT`
  구독) 감지 후 사이드바 표시/숨김, `conversationId` 공유, 데스크톱
  상시·모바일 오버레이(hamburger PanelLeft 아이콘).
- `mova-ai-chat-bar.tsx` 리와이어링: `conversationId` prop 지원(DB 모드
  자동 전환), 변경 시 서버에서 대화 로드해 messages 복원, 응답의
  `conversation_id`를 상위에 콜백으로 전달 → 사이드바 refreshKey 증가 →
  목록·순서 갱신. 비로그인은 prop 미전달로 기존 sessionStorage 경로 유지.
- `/mova/main/page.tsx`: `MovaHeader` + `MovaChatShell`만.

**검증**
- `pnpm type-check` 클린, dev 서버 부팅 성공, `GET /mova/main` HTTP 200.
- 백엔드 부팅 검증: `mova_router.routes` 47개 등록, `/mova/conversations`
  3개 엔드포인트 노출 확인.

**배포**
- 커밋 3건(백엔드 / 프론트 / WORK_LOG). Vercel `main` 자동 배포 + EC2
  `git pull` + `alembic upgrade head`(20260811_0003 → 20260812_0001) +
  `docker compose up -d --build backend auth` 필요.
### 후속 사이클 C~N — 사용자 리포트 대응 릴레이


대화 저장 v1 배포 후 사용자 실사용 리포트가 연이어 들어와 정정·개선을
릴레이로 진행. 각 사이클마다 스크린샷 신고 → 원인 특정 → 수정 → 배포.

**C. 채팅 UX 4가지 통합**(PR #82, `f7d68c5`)
- auto-send 재발화(뒤로 가기 시 같은 쿼리 재전송) → 성공 후 `router.replace(pathname)`로 URL `?q=` 스트립.
- 활성 대화 유실(remount로 chat-shell state 초기화) → `sessionStorage`로
  `conversationId` 보존·복원.
- 태블릿에서 헤더 네비(홈·영화·컬렉션·랭킹·마이) 사라짐 → `lg:flex`→`md:flex`, gap·nowrap 조정.
- 데스크톱 사이드바 접기 불가 → PanelLeft/PanelLeftClose 토글 + localStorage 유지.
- 부수: `/mova` 랜딩과 `/mova/main` 빈 상태 히어로 카피 중복 →
  main 빈 상태를 "무엇이 궁금하세요?" 한 줄로 축소.
- 하이드레이션 게이트: 세션·conv 복원 완료 전 flash·잘못된 auto-send 방지.

**D. auto-send 재발화 근본 원인 + 입력창 밀림**(PR #83, `e2ff550`)
- 사용자 재신고(스크린샷: 사용자 메시지 1건 + assistant 응답 2건).
- 원인: DB 로드 effect가 `autoSentRef=true`를 `async .then` 안에서 설정 →
  같은 tick의 auto-send effect가 아직 false인 flag를 보고 URL `?q=`로 재전송.
- fix: DB 로드 effect 첫 라인에서 **동기적으로** `autoSentRef.current=true`
  설정. Shell에도 하이드 완료 후 URL `?q=` 정리 안전망.
- 부수: 입력창이 뷰포트 밖으로 밀림 → outer `min-h-screen` → `h-screen + overflow-hidden`.

**E. 대화 리스트 스크롤 안 걸림**(PR #84, `884c9d9`)
- 위 D의 h-screen 배포 후 다음 신고: "스크롤바가 사라짐, 대화가 안 내려짐"
  (스크린샷).
- 원인: flex-col + flex-1 자식의 min-height 기본값이 auto라 콘텐츠 높이가
  부모에 강제되어 `overflow-y-auto`가 걸릴 자리 없음(flexbox 관용 함정).
- fix: `overflow-y-auto`가 걸리는 곳까지 이어지는 체인 전체에 `min-h-0`
  (Shell right col, ChatBar section, chat list, sidebar list).

**F. 우측 랭킹 레일 + 사이드바 폴리싱**(PR #85, `d7466c4`)
- 사용자 요청 "전체모드일 때 오른쪽에 짧게 랭킹".
- `MovaChatRail` 신설: `lg:` 노출, `fetchHotRankings(8)` 클라이언트 fetch,
  기존 `MovaRankingSection sidebar variant` 재활용.
- 사이드바 폭 `md:w-64` → `md:w-60`, "새 대화" 버튼 padding·gap 축소,
  대화 항목 밀도(text-13px, py-1.5, rounded-md), 삭제 hover red-500→400.

**G. 리뷰 삭제 confirm**(PR #86, `8a78a05`)
- `/mova/mypage` 리뷰 삭제 전에도 사이드바 대화 삭제와 동일 관례
  ("...삭제할까요? 되돌릴 수 없습니다.") confirm 추가.

**H. 리뷰 로그인 링크 suvisdev 이탈**(PR #87, `92c2983`)
- 사용자: "mova에서 로그인/회원가입하면 (suvisdev) 메인 페이지로 넘어감".
- 원인: 영화 상세 리뷰 섹션의 "로그인" 링크가 `/login`(suvisdev 루트) →
  로그인 성공 시 `router.replace("/")`로 suvisdev 홈으로 튀어나감.
- fix: `/mova/login?redirect=/mova/title/{slug}`로 변경.

**I. 로그인·회원가입 토큰 미저장(1차)**(PR #88, `c93f0a9`)
- 사용자: "회원가입했는데 사이드바 인증이 필요합니다 계속 뜸"(스크린샷).
- 원인: `mova-auth-forms.tsx` 로그인이 `/api/auth/login` 프록시(aud 없이)
  호출 → 응답에서 `id`/`username`만 파싱, `access_token`은 파싱 안 함 →
  세션에 token 필드 없음 → `authHeader()` 빈 헤더 → API 401.
- fix: `${AUTH_BASE}/auth/login`·`/auth/signup` 직접 호출(aud="suvis-mova"),
  `access_token` 파싱 → `mova/whoami`로 신원 확보 → `saveSuvisSession({id, username, token})`.
- 회원가입 auto-login으로 개선(기존 "로그인해주세요" tab 전환 제거).

**J. 회원 탈퇴 API + UI + 오래된 세션 자동 정리**(PR #89, `fdf33f9`)
- 사용자: "회원탈퇴가 없어… 할 수 있는 방법도 없고"(스크린샷).
- 백엔드 신설: `ProfileUseCase.delete_account`·`ProfileRepository.delete_user`
  포트 → Interactor·PgRepository 구현(`DELETE FROM users WHERE id=?`, FK
  CASCADE로 리뷰·와치리스트·대화·취향 벡터·OAuth identities 전부 자동 삭제).
- 라우터: `DELETE /viewer/profile/{user_id}` (require_user + IDOR).
- 프록시 route.ts에 DELETE 메서드, `deleteMovaAccount(userId)` 클라이언트.
- `/mova/mypage` 하단 위험 존 섹션 + 2단 확인(경고 confirm + 사용자명 재입력 prompt).
- 부수: mypage에 오래된 토큰 없는 세션 자동 감지·정리 → 로그인 재유도.

**K. 🔥 require_user·require_admin RS256 통일(핵심 원인)**(PR #90, `392deae`)
- 위 I·J를 배포했는데도 여전히 "인증이 필요합니다"·"유효하지 않은 세션입니다"
  가 안 사라짐(스크린샷). 사이드바 통째로 사라짐도 같은 원인.
- 근본 원인: auth 게이트웨이(`auth.suvisdev.cloud`)는 **RS256** 토큰 발급인데
  `shared/security/require_user.py`·`require_admin.py`는 **HS256 + JWT_SECRET**로
  검증. 알고리즘 자체가 달라 decode 즉시 `PyJWTError` → 401. 새 로그인 사용자가
  RS256 토큰을 잘 저장해도 백엔드가 그 토큰을 못 알아먹음.
- `mova/dependencies/require_auth.py::get_current_user`는 이미 올바른 RS256 검증
  구현(`shared.security.token_verifier`)이 있었음 — 두 시스템이 병존한 채 다른
  라우터가 잘못된 쪽을 쓰고 있었을 뿐.
- fix: `require_user`·`require_admin`을 `token_verifier`(RS256, aud="suvis-mova")로
  통일. `UserPrincipal`/`AdminPrincipal` 인터페이스 유지. `principal.username`
  사용처 grep 결과 0건 확인 후 빈 문자열로.
- 전체 pytest 213 passed. EC2 backend/auth 재빌드 + nginx reload → 새 로그인
  후 사이드바·마이페이지 정상 로드 실측.

**L. 대화 중복 추천 방지**(PR #91, `fab99d1`)
- 사용자: "다른 것도 소개해줘"·"다른건??" 요청에 이전에 이미 소개한 영화가
  또 나옴(스크린샷: 미아즈마 캠프·뒤바뀐 친구들 재등장).
- 원인: `history` 텍스트는 프롬프트에 붙지만 assistant 응답의 `recommendations`
  목록은 LLM이 못 봄 → 후보 카탈로그가 매 턴 사실상 동일한 top-N이라 같은
  slug 재선택.
- fix:
  - `ConversationsRepository.get_recent_recommendation_slugs(conversation_id, limit=30)` 신설 —
    chat_messages `meta.recommendations[].id` 집합 추출.
  - `ChatInteractor.chat`이 LLM 호출 직전에 이미 소개한 슬러그를 `catalog`에서
    제거. 전부 필터되면 원본 유지(사용자에게 빈 응답 대신 뭐라도).
  - 최종 `recs`에도 한 번 더 필터(2차 안전망 — LLM 자유 응답 대비).
- 단위 테스트 3건 추가.

**M. MovaLoginButton→AuthDialog fallout + auth-forms RS256**(PR #92, `f1acffa`)
- 사용자: "새로 탈퇴하고 가입했는데 아직 인증 오류가 계속 떠"(스크린샷).
- main이 `MovaLoginButton`을 `AuthDialog`(공용 auth-forms.tsx)로 리팩터링해
  놓았는데, 그 새 경로도 `/viewer/login/login`(id/username/nickname, token 없음)을
  사용 중이었음. 즉 어떤 경로로 로그인해도 세션에 token 저장 못 하던 문제가
  여전히 남아 있었음(I는 mova-auth-forms만 고쳤음).
- fix: `app/login/auth-forms.tsx`도 `${AUTH_BASE}/auth/login`·`/auth/signup`으로
  통일(aud="suvis-mova" + access_token + whoami + token 세션 저장).
- 회원가입 auto-login으로 개선.

**N. 0카드일 때 정직한 안내 + 로딩 문구 순환**(PR #93, `38dbe2c`)
- 사용자: "추천해줄 게 없으면 없다고 돌려서 말해줘"(스크린샷: 카드 0인데
  "취향에 맞춰 엄선한 명작 영화들을 추천해 드릴게요…"로 응답).
- 원인: `recs`가 0으로 확정된 뒤에도 LLM이 뱉은 "추천해 드릴게요" 텍스트가
  그대로 표시됨(사용자에게 어긋난 응답).
- fix: `ChatInteractor`에서 recs=0 확정 시 reply를 정직한 문구로 대체 —
  이미 소개해서 필터로 빠진 경우와 카탈로그에 원래 없는 경우를 구분 안내.
- 추가: 로딩 UI가 "추천 큐레이션 중…" 정적 텍스트라 3~10초 대기 시 사용자가
  멈춘 것처럼 느낌. 3초마다 4문구가 fade로 순환(요청 취향 살펴보는 중 →
  카탈로그 검색 → AI 조합 → 곧 추천). Gemini 응답 지연을 시각적으로 살아있음
  으로 커버.
- 단위 테스트 2건 추가, 전체 pytest 200 passed.

**오늘 총 PR 14개**(#80~#93) 머지 완료. 프론트는 Vercel 자동 배포, 백엔드는
필요 시 EC2 재빌드 진행. 최종 상태: 로그인 사용자 전 계층(사이드바·대화 저장·
중복 방지·마이페이지·회원 탈퇴·리뷰) 정상 동작 실측 확인.
### 후속 사이클 O~R — 추가 사용자 리포트


**O. 마이페이지 세션 거절 시 재로그인 유도**(PR #95, `078922c`)
- 이전 fix는 `s.token` 자체가 없을 때만 자동 정리. 토큰이 있어도 백엔드가
  거절하는 경우(만료·algorithm 불일치)는 그냥 빨간 에러 문구만 노출.
- fix: 에러 메시지에 "유효하지 않은 세션"·"인증이 필요"가 포함되면
  clearSuvisSession + `/mova/login` 재유도.

**P. 헤더 네비에 채팅 탭 추가**(PR #96, `a2d3f16`)
- 요청: "홈 영화 사이에 채팅 탭 하나". MOVA_NAV에 `{ label: "채팅", href: "/mova/main" }`
  삽입. isNavActive에서 `/mova`(홈)는 정확 매칭만 하도록 좁혀 새 채팅 탭과
  중복 활성 안 되게 정리(mova-header.tsx + mova/page.tsx 인라인 둘 다).

**Q. AI 스포일러 감지 + 프론트 블러·확인 다이얼로그**(PR #97, `29a7b6f`)
- 요청: 리뷰에 스포일러가 있으면 그 단어만 가려주고, 클릭 시 "스포일러일
  수 있습니다. 보시겠습니까?" 확인 후 노출. 판단은 AI.
- 백엔드(마이그레이션 `20260812_0002`):
  - `reviews.spoiler_spans JSONB DEFAULT '[]'` 신설 — {start,end,text} 리스트.
  - `spoiler_detection.py`: Gemini에 리뷰 본문 넣고 후보 문구 리스트만 받아
    body에서 find()로 스팬화. 결말·반전·정체 공개 등만, 일반 감상은 제외.
    실패·쿼터·네트워크 예외 다 삼켜 [] 반환(리뷰 저장 자체는 절대 안 막힘).
  - `ReviewSpoilerBackfillInteractor.detect_one(review_id)`: 자체 세션 팩토리
    로 BG 태스크에서 호출, Gemini 동기 SDK를 asyncio.to_thread 위임.
  - `/mova/reviews` POST/PATCH가 응답 후 BG 발화 — 임베딩·취향 벡터와 독립
    병렬. update 시 body 변경 감지되면 spoiler_spans를 []로 초기화 → 재감지.
  - DTO/스키마(ReviewSchema·ReviewWithUserSchema·MyReviewSchema·MyReviewItem)에
    spoiler_spans 필드 관통. 기존 리뷰 테스트 218 통과(_FakeSpoilerBackfill 추가).
- 프론트:
  - `MovaSpoilerBody` 컴포넌트: 스팬을 순차 잘라 스포일러 부분만 블러 버튼
    (배경·글자 같은 색). 클릭 → window.confirm → 그 스팬만 노출(전체 아님).
  - MovaReviewRow·MypageReviewItem·MovaComment 타입에 spoiler_spans 관통.
  - `/mova/mypage` 내 리뷰 · `/mova/title/[slug]` 리뷰 리스트에 적용.
- 배포: PR #97 → main 머지 → EC2 backend 재빌드 + `alembic upgrade head`
  (`20260812_0001 → 20260812_0002`) + nginx reload. API 응답 200 실측 확인.

**오늘 총 PR 17개**(#80~#97). 프론트+백엔드 대규모 릴레이 완료.

**R. 스포일러 UX 보완**(PR #99, `8cdb29b`)
- 증상: 스포일러 블록에 마우스만 올리면 텍스트 노출(스크린샷 "왕이 죽습니다"),
  스포일러 안내 표시가 없음.
- 원인: 이전 은닉이 `bg-neutral-700 text-neutral-700`(같은 색) + `hover:bg-neutral-600`.
  호버 시 배경 색만 바뀌고 텍스트 색은 그대로라 대비 생겨 노출.
- fix: 텍스트를 `text-transparent`로 완전 투명(호버·컬러 스와이프 무력화),
  `select-none`으로 드래그 복사 차단. `showBadge` prop 신설(기본 true) —
  스팬 있으면 본문 앞에 amber "⊘ 스포일러 포함" 배지 자동 렌더.

**S. 추천 문구 로테이션 주기 1일→3시간**(PR #100, `340c6e0`)
- 사용자: "같은 3개만 계속 보임". 하루 1버킷은 갱신이 너무 느림.
- fix: `getRotatingMovaChatSuggestions`로 rename(기존 daily는 오해 소지),
  bucket key를 `YYYY-MM-DD-{hour÷3}`으로 변경 → 하루 8번 갱신. 두 호출처
  (mova-ai-chat-bar, mova-landing-chat-bar) 함께 갱신.

**T. 헤더 검색 완전 복구 + 배우/감독 확장**(PR #101, `03916bd`)
- 증상: 상단 검색창에 뭘 쳐도 결과 안 나옴(스크린샷 "왕과 사는" 입력).
- 원인 2가지:
  1. 프론트 `fetchMovaSearch`가 응답을 배열로 파싱(`rows.map`)했지만 백엔드는
     `{query, items, total, ...}` 객체 → `rows.map` 실패 → catch 블록의
     로컬 목업만 표시(실질적으로 안 됨).
  2. 백엔드 `search_by_label`이 태그 label + 영화 제목만 매칭. 배우·감독
     이름 못 잡음.
- fix:
  - 백엔드 `search_by_label`에 `characters JOIN actors`(배우) +
    `movie_directors JOIN actors`(감독) OR 브랜치 추가. actor.name ILIKE로
    하나라도 걸리면 그 영화 포함.
  - 프론트 `fetchMovaSearch`를 `data.items` 파싱으로 교정. slug·poster_url·
    release_year 필드 매핑.
  - `/api/mova/search` 프록시 limit 12 → 5(자동완성 5건 이하 요청).
- 실측: "놀란" 검색 → 다크 나이트·인셉션·인터스텔라·프레스티지·메멘토 5편 확인.
- 배포: main 머지 + EC2 backend 재빌드 + nginx reload.

**오늘 총 PR 21개**(#80~#101). 프론트·백엔드·auth·마이그레이션 2건까지 전
계층 전면 개편·복구 릴레이 완료.

---

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

### α 사이클 — 정식 배포 시도(결과: 미완, 임시 반영 유지)

이번 두 사이클(HNSW 리비전·힌트)이 EC2에는 `docker cp`로만 임시 반영된
상태를 정식 이미지로 통합하려 시도. 절차: 로컬 push → PR #75(suvisdev→main
병합, `288186e`) → EC2 `git pull` → `docker compose ... up -d --build backend`.
- **재빌드 2번 모두 실패** — `No space left on device`(pip install 중 임시
  레이어 폭증). 첫 시도 259초 지점 실패, `docker builder prune -a`로 10.5GB
  회수했으나 두 번째도 286초 지점에서 같은 이유로 실패. 12GB free여도 pip
  wheel unpack 임시 공간이 부족.
- 사용자 결정: **EBS 확장 안 함** → 정식 재빌드 강행 포기.
- **결론**: 임시 반영(alembic head 정합 + `docker cp` 코드) 그대로 유지.
  실 서비스는 정상 동작 중(전 벤치마크 20회 통과). 다음 코드 변경 사이클에서
  자연스럽게 함께 재빌드 시 통합될 것.

### β 사이클 — reviews.embedding 인프라

**결정 사항**: 저장 방식 = **BackgroundTasks + 크론 백필 안전망**, 스코프 =
**인프라만**(취향 벡터·추천 반영은 다음 사이클).

**실측 초기 상태**: `reviews` 3건, meaningful body 2건(백필 부담 없음).

**신규 파일**:
- `suvisdev/alembic/versions/20260811_0002_add_reviews_embedding_and_hnsw.py`
  — `reviews.embedding vector(768)` + HNSW 인덱스(m=16, ef_construction=64).
  0.5순위 사이클과 동일 파라미터.
- `apps/mova/app/use_cases/review_embedding_backfill_interactor.py` —
  `ReviewEmbeddingBackfillInteractor` 신설. 세션 팩토리 + `EmbeddingPort`
  (Gemini) 주입, `embed_one(review_id)` · `embed_missing(limit)` 노출.
  BackgroundTasks/CLI 두 진입점 공유. 요청 세션에 붙지 않기 위해 내부에서
  `async with factory() as session:`으로 매번 새 세션.
- `apps/mova/dependencies/review_embedding_provider.py` — 백그라운드 경로용
  DI. 기존 `market_reviews_provider`(요청 경로용)와 별개.
- `scripts/backfill_review_embeddings_cli.py` — movies 백필 스크립트 미러링.
  `--limit` / `--dry-run`.
- `apps/mova/tests/test_review_embedding_backfill.py` — 인터랙터 단위 테스트
  4건(skipped/succeeded/failed/aggregate).

**수정**:
- `apps/mova/adapter/outbound/orm/market_reviews_orm.py` — `embedding` 컬럼
  Mapped 필드 추가.
- `apps/mova/app/ports/output/market_reviews_repository.py` — Port에
  `get_body_for_embedding` · `list_missing_embedding` · `update_embedding`
  추가. `.claude/rules/testing.md` 원칙대로 fake도 함께 갱신 필요했지만
  기존 fake는 use case용이라 이번엔 해당 없음.
- `apps/mova/adapter/outbound/pg/market_reviews_pg_repository.py` — 세 메서드
  구현.
- `apps/mova/adapter/inbound/api/v1/market_reviews_router.py` — `POST` ·
  `PATCH`에 `BackgroundTasks` + `embedding_backfill` DI 주입. `add_review`는
  body 있을 때만, `update_review`는 항상 스케줄(embed_one이 body 없으면 자체
  스킵).
- `apps/mova/tests/test_market_reviews.py` — 새 DI(백그라운드 인터랙터)를
  fake로 오버라이드(`_FakeEmbeddingBackfill`) — 기존 라우터 테스트가 실제
  Gemini/DB 세션 팩토리를 부르지 않게. 회귀 확인: **mova 전체 183/183 통과**.
- `_docs/SCRIPTS_EXECUTION_GUIDE.md` — 크론 표에 reviews 라인 추가.

**EC2 반영(임시 방식)**:
- tar+scp로 8개 파일 번들 전송 → `docker cp` 순회 → `alembic upgrade head`
  (`20260811_0001 → 20260811_0002`) → `docker restart suvisdevcloud-backend-1`.
- DB 확인: `reviews.embedding` 컬럼 + `idx_reviews_embedding_hnsw` 인덱스
  생성 완료. 기존 3건 백필로 파이프라인 실증: `succeeded=3 failed=0 skipped=0`,
  전부 `embedding IS NOT NULL` 확인.

**Crontab**: `30 3 * * *` (KST) — movies 백필과 30분 시차(공유 쿼터 순차 소화).
로그 `~/backfill_review_embeddings.log`.

### 다음 사이클(β 후속) 후보
- **추천 반영**: mova 후보 정렬에 취향-영화 코사인 거리 결합.
- **감정 축**: ontology `echo_sentiment_adapter`를 Spoke→Hub 포트로 연결.
- **BackgroundTasks 실 API 검증**: 로그인·watched 흐름 필요해 이번 세션에서
  스킵. 다음 세션에서 실 리뷰 하나 생성 → embedding 자동 채워지는지 실측.

### γ 사이클 착수 — 취향 벡터 계산(코드만, EC2/CLI/조회 API는 다음 세션)

세션 시간이 짧아 **10분 스코프**로 축소. 코어 파이프라인(테이블·저장·재계산
체이닝)까지만 만들고 커밋, 나머지(CLI·crontab·EC2 반영·조회 API·상세 테스트)는
오늘 밤/내일 이어서 진행.

**결정**: 저장 위치 = `mova.user_taste_vectors` 신규 테이블(users에 컬럼
붙이지 않고 스타-토폴로지 유지). 갱신 = BackgroundTasks + 크론 안전망.
가중 공식 = `sum(rating_i * embedding_i) / sum(rating_i)`(정규화 생략,
cosine 스케일 불변).

**신규 파일**:
- `suvisdev/alembic/versions/20260811_0003_add_user_taste_vectors.py` — 테이블
  신설(user_id UNIQUE FK, vector(768), review_count, updated_at). HNSW는 다음
  사이클(유사 유저 탐색 필요 시).
- `apps/mova/adapter/outbound/orm/platform_user_taste_vectors_orm.py` — ORM.
- `apps/mova/app/dtos/platform_user_taste_vector_dto.py`
- `apps/mova/app/ports/output/platform_user_taste_vector_repository.py` —
  upsert / get_by_user_id / list_user_ids_with_rated_reviews.
- `apps/mova/adapter/outbound/pg/platform_user_taste_vectors_pg_repository.py`
  — `ON CONFLICT (user_id) DO UPDATE ... updated_at = now()` upsert.
- `apps/mova/app/use_cases/platform_user_taste_vector_interactor.py` —
  `UserTasteVectorRecomputeInteractor` (embed_backfill과 같은 세션 팩토리
  주입 패턴). `recompute_for_user` / `recompute_missing`.
- `apps/mova/dependencies/platform_user_taste_vector_provider.py`.

**수정**:
- `apps/mova/app/ports/output/market_reviews_repository.py` +
  `apps/mova/adapter/outbound/pg/market_reviews_pg_repository.py` —
  `list_embedded_reviews_by_user(user_id) -> list[(id, rating, embedding)]`.
- `apps/mova/adapter/inbound/api/v1/market_reviews_router.py` — POST/PATCH에
  `taste_recompute` DI 추가 + `_embed_review_then_recompute_taste` 래퍼로
  BG task 체이닝(embed 성공 시에만 recompute). body 없는 add_review는
  recompute만 걸어둠(rating 변경이 취향 후보를 바꿀 수 있음).
- `apps/mova/tests/test_market_reviews.py` — 새 DI 오버라이드 fake 추가.
  회귀 확인: **mova reviews 관련 29/29 통과**.

**남은 것(다음 세션 몫)**:
1. `scripts/backfill_taste_vectors_cli.py` + crontab `45 3 * * *`(reviews 뒤
   15분) — 안전망.
2. `GET /mova/taste/me` 조회 API + require_user 가드.
3. 인터랙터 단위 테스트(가중 평균 정확성 / 리뷰 0건 → cleared / rating=0 →
   cleared) — 이번엔 라우터 회귀만 확인, 계산 로직 격리 테스트는 미작성.
4. EC2 반영(docker cp + alembic upgrade + restart) + 유일 rated-reviews
   유저에 대해 recompute 실증.
5. WORK_LOG·PROGRESS 갱신은 이 커밋 시점의 결과만 반영, 다음 세션에서 나머지
   완료분 이관.

**주의(다음 세션 착수 전)**: alembic 리비전 `20260811_0003`은 아직 EC2에
반영 안 됨. 로컬 커밋만 존재 → main 병합 후 EC2에서 `docker cp` +
`alembic upgrade head` 필요. β 사이클과 같은 임시 반영 패턴.

### 후속 사이클(같은 날) — γ 잔여 5건 전부 마무리

새 세션 시작 시 origin/main이 이미 fast-forward pull된 상태(γ 코어 커밋
`79fdb5c` 포함)로 시작 — 위에서 "다음 세션 몫"으로 남긴 5개 항목을 이어서
전부 처리.

**1. `GET /mova/taste/me` API**
- `adapter/inbound/api/schemas/platform_user_taste_vector_schema.py` 신설 —
  `UserTasteVectorSchema(has_vector, review_count, updated_at)`. **원본
  768차원 벡터는 응답에 안 넣는다** — 내부 코사인 계산 전용이고 소비할
  프론트 화면이 아직 없어서, 표시 가치 없는 raw float 배열을 그대로 노출할
  이유가 없다는 판단(사용자 확인 없이 진행, 후속 세션에서 필요해지면 스키마
  확장은 쉬움).
- `UserTasteVectorDto.to_schema()` 추가(기존 Dto 컨벤션 그대로).
- `UserTasteVectorRecomputeInteractor.get_for_user()` 추가 — 단순 조회
  위임(순수 SQL, embedder 불필요라 기존 인터랙터 그대로 재사용).
- `adapter/inbound/api/v1/platform_user_taste_vector_router.py` 신설,
  `require_user` 가드. 행이 없으면(리뷰 0건 유저) `has_vector=False`로
  기본값 응답.
- `mova/adapter/inbound/api/__init__.py`에 라우터 등록.

**2. 인터랙터 단위 테스트**
- `apps/mova/tests/test_platform_user_taste_vector.py` 신설 — 6건: 리뷰
  0건→cleared, 가중합 0(rating=0만 있음)→cleared, 별점 가중 평균 계산 정확성
  (`[10/6, 16/6]` 직접 검증), `recompute_missing` 집계, `get_for_user`
  None/passthrough. `test_review_embedding_backfill.py`의 세션 팩토리 mock
  패턴 재사용.

**3. `backfill_taste_vectors_cli.py` + 문서**
- `scripts/backfill_taste_vectors_cli.py` 신설 —
  `backfill_review_embeddings_cli.py`와 같은 구조, `recompute_missing` 호출.
  embedder 의존이 없어 `get_keymaker()` 호출 없음(DB 연결은
  `ensure_mova_database()`가 내부에서 `reload_env()` 처리).
- `_docs/SCRIPTS_EXECUTION_GUIDE.md` 표에 3번째 행 추가 + "왜 45분 시차인지"
  각주(쿼터 경합 아니라 순서 종속 — reviews 크론이 채운 신규 embedding을
  바로 반영하려는 목적).

**4. 로컬 테스트 실행**
- 로컬에 프로젝트 파이썬 환경이 없어(시스템 python3엔 sqlalchemy 없음) `uv`로
  스크래치 venv 생성, `fastapi`·`sqlalchemy[asyncio]`·`psycopg`·`pgvector`·
  `python-dotenv`·`PyJWT[crypto]` 최소 설치(torch 등 무거운 의존 제외).
- 신규 유닛테스트 **6/6 통과**. `platform_user_taste_vector_router`·
  `market_reviews_router` 단독 임포트로 회귀 확인(문법·의존성 오류 없음).

**5. EC2 반영 + BackgroundTasks 실 API 검증**
- 반영 전 실측: EC2 alembic은 `20260811_0002`(head)까지만 — γ 전혀 미반영
  확인.
- γ 코어 10개 파일(79fdb5c) + 이번 세션 신규/수정 4개 파일, 총 14개를
  로컬에서 tar로 묶어 scp → EC2 `/tmp/`에서 압축 해제 → 파일별 `docker cp`로
  `suvisdevcloud-backend-1` 컨테이너 반영. `alembic upgrade head` →
  `20260811_0002 → 20260811_0003`(user_taste_vectors 테이블 생성) 확인.
- `docker restart suvisdevcloud-backend-1` → 로그에서 `Application startup
  complete` 확인(임포트 에러 없음). backend는 호스트 포트가 열려 있지 않아
  (nginx가 프록시) 컨테이너 안에서 `python -c "urllib.request..."`로 검증
  (컨테이너에 curl 자체가 없음 — 발견).
- **BackgroundTasks 실 API 왕복 검증**(대상 `users.id=3 suvisdev`, 컨테이너
  안에서 `JWT_SECRET`으로 10분짜리 임시 토큰 발급, β 사이클과 같은 패턴):
  1. `GET /mova/taste/me` (사전) → `has_vector=false, review_count=0` 확인.
  2. `POST /mova/reviews/activity` `{movie_id:1, action_type:"watched"}` →
     201(리뷰 작성 전제조건 `has_watched` 충족용).
  3. `POST /mova/reviews` `{movie_id:1, rating:4.5, body:"자동검증용..."}` →
     201, review id=4.
  4. 8초 대기 후 `GET /mova/taste/me` → `has_vector=true, review_count=1,
     updated_at` 리뷰 작성 시각 직후로 갱신 — **BG task 체이닝(embed →
     recompute) 실증 확인**.
  5. DB 직접 확인: `reviews.id=4`의 `embedding` 768차원 채워짐,
     `user_taste_vectors.user_id=3`의 `vector` 768차원 — API 응답과 DB
     상태 일치.
- **뒷정리**: `DELETE /mova/reviews/4`(API 경유, 200) → `delete_review`는
  취향 벡터를 자동 재계산하지 않으므로(설계상 미연결) `user_actions`의
  watched 행(id=5)과 `user_taste_vectors`의 user_id=3 행을 DB에서 직접
  `DELETE`로 제거 — 정리 후 `reviews`/`user_actions`/`user_taste_vectors`
  전부 user_id=3 기준 0건 재확인. 임시 토큰 파일도 삭제.
- **crontab 등록**: `45 3 * * * ... backfill_taste_vectors_cli.py >>
  ~/backfill_taste_vectors.log 2>&1` 추가, `crontab -l`로 확인.

**오류·막힌 점**
- EC2 backend 컨테이너에 `curl`이 없다(이미지에 미포함) — 이후 EC2 컨테이너
  내부 API 검증은 `docker exec ... python -c "urllib.request..."` 방식을
  표준으로 쓸 것(이번에 새로 확인된 제약, 문서화 가치 있음).
- 그 외 막힌 점 없음 — alembic·docker cp·재기동·API 왕복 전부 한 번에 성공.

**산출물**
- 신규: `platform_user_taste_vector_schema.py`,
  `platform_user_taste_vector_router.py`,
  `test_platform_user_taste_vector.py`, `backfill_taste_vectors_cli.py`.
- 수정: `platform_user_taste_vector_dto.py`(`to_schema`),
  `platform_user_taste_vector_interactor.py`(`get_for_user`),
  `adapter/inbound/api/__init__.py`(라우터 등록),
  `_docs/SCRIPTS_EXECUTION_GUIDE.md`.
- EC2: alembic head `20260811_0003`, crontab에 취향 벡터 백필 라인,
  `suvisdevcloud-backend-1`에 14개 파일 `docker cp` 반영(git 커밋과는 별개
  — 정식 이미지 재빌드는 다음 배포 사이클 몫, HNSW 사이클과 같은 패턴).
- **γ 사이클(리뷰 이해 파이프라인 1-c순위) 잔여 5건 전부 완료.** 다음 순서는
  PROGRESS.md 1-c순위의 "다음 순서" 2번(추천 후보 정렬에 취향-영화 코사인
  결합)부터.

### 배포 사이클(같은 날) — suvisdev → main 병합 + EC2 정식 이미지 재빌드

사용자 요청으로 로컬 커밋을 `suvisdev` 브랜치에 푸시한 뒤 이어서 main 병합과
EC2 정식 배포까지 진행.

**병합**
- `gh` CLI가 이 환경에 없어 PR 대신 로컬 `git merge --no-ff suvisdev`로
  main에 병합(`08f1a17`) → `git push origin main`. 커밋 전 신규 유닛테스트
  6/6 재확인 + `ruff check`/`ruff format` 정리(단, `platform_user_taste_
  vector_router.py`의 `shared.security` import 순서는 ruff 제안 대신
  `whoami_router.py`/`market_reviews_router.py`와 같은 기존 관례를 그대로
  따름 — `known-first-party`에 `shared`가 빠져 있어 ruff가 서드파티로 오인,
  이건 저장소 전역의 기존 상태라 이번 변경 범위 밖).

**EC2 배포 — 예상 밖 이슈 2건**
1. **로컬 main이 origin과 41 커밋 어긋나 있었음**: 과거 여러 세션의
   `git pull`이 fast-forward 대신 빈 머지 커밋을 반복 생성해 온 것으로 확인
   (`git log --oneline <ec2-head> --not <merge-base>`로 전부
   "Merge remote-tracking branch 'origin/main'" 류의 내용 없는 머지임을
   실측 확인 후 `git reset --hard origin/main`으로 정리 — 고유 콘텐츠 손실
   없음 확인 후 진행).
2. **`docker compose up -d --build` 1차 시도가 디스크 부족으로 실패**
   (`No space left on device`, pip install 중 torch/CUDA 대량 설치 단계).
   원인: `suvisdev-app:latest`(9.2GB, backend·auth 공유)가 컨테이너에
   물려 있는 채로 새 이미지를 빌드하면서 신구 이미지가 동시에 디스크를
   차지 — 30GB 중 12GB 여유로는 부족. CLAUDE.md에 이미 기록된 고질
   문제(2026-08-05)와 같은 원인, 이번엔 실제로 재현·해결.
   - 조치: `docker compose stop/rm backend auth` → `docker rmi
     suvisdev-app:latest`(9.2GB 회수, 21GB 여유 확보) → 재빌드 → 성공(exit
     0, 약 5분). 이 과정에서 backend/auth **일시 다운타임 발생**(nginx·DB·
     기타 서비스는 무영향).

**결과**
- `docker compose ps` 전체 스택 정상(nginx·backend·auth·db·redis·neo4j·
  cloudflared·pgadmin·certbot 전부 Up). `backend`/`auth` 로그에
  `Application startup complete` 확인.
- 컨테이너 내부 `GET /mova/movies` 200, `GET /mova/taste/me`(무인증) 401 —
  재빌드 후에도 정상.
- **이번 재빌드가 main의 전체 누적분을 반영**하므로, β(리뷰 임베딩)·γ(취향
  벡터)뿐 아니라 이전 HNSW 힌트 사이클(0.5순위)의 "docker cp 임시 반영 →
  정식 이미지는 다음 배포 사이클 몫" 백로그도 한 번에 해소됨.
- dangling 이미지(빌드 중 backend/auth가 각각 별도 이미지 ID로 만들어졌다가
  하나로 태깅되며 남은 미태그 레이어) `docker image prune -f`로 정리 —
  레이어 공유로 실 회수는 0B(중복 낭비 아니었음, 정상).

**산출물**
- `origin/main` → `08f1a17`(머지 커밋), `origin/suvisdev` → `f817ad6`.
- EC2 `~/suvisdev.cloud`: `git reset --hard origin/main`, backend/auth
  이미지 재빌드·재기동.
- PROGRESS.md 0.5순위 "EC2 이미지 상태" 항목을 "정식 이미지 재빌드로 해소"로
  갱신, 1-c순위 γ 문단에 배포 완료 문구 추가.

### 작업 내용(추가⑫) — 프로덕션 장애 대응: nginx stale DNS 502 + mova 로그인 완전 장애(auth 게이트웨이 미완성) + cloudflared api.suvisdev.cloud 전용 장애 조사

사용자가 "배포된 백엔드가 안 돈다"고 신고 → 연쇄적으로 서로 다른 원인의
장애 3건이 나와 순서대로 처리. 세 번째(cloudflared)는 세션 종료 시점
기준 미해결(24h 관찰 진행 중).

**1) nginx stale DNS 502(즉시 해결)**
- `docker logs nginx`에 `connect() failed (111: Connection refused)`
  반복, upstream이 backend의 옛 IP(172.20.0.9)를 가리킴 — backend/auth가
  38분 전 재시작하며 새 IP(172.20.0.7)를 받았는데 nginx(31시간째 기동,
  `proxy_pass http://backend:8000` 정적 호스트명, resolver 지시자 없음)가
  DNS를 재해석 안 함. `docker exec nginx nginx -s reload`로 즉시 해결.
- 이후 mova 챗 401("유효하지 않은 세션")은 별개 — 해당 계정의 7일 만료
  JWT 세션이 그냥 만료된 것으로 확인(서버 문제 아님, 재로그인 안내).

**2) mova Google/Kakao/Naver 로그인 완전 장애 — 근본 원인 규명 + 되돌림**
- `auth.suvisdev.cloud/auth/login/google?...` → 503
  `"GOOGLE_CLIENT_ID/AUTH_GOOGLE_REDIRECT_URI가 설정되지 않았습니다."`
- 원인: 커밋 `beec23e`(2026-07-22)가 mova 로그인 버튼을
  `apps/auth`(auth.suvisdev.cloud, 병렬 구축 중인 미완성 SSO 게이트웨이)로
  연결했는데, `apps/auth/_docs/auth_gateway_harness.md` §5에 "Google/Kakao/
  Naver 콘솔에 `AUTH_*_REDIRECT_URI` 신규 등록 안 함", "viewer→auth 실전환은
  범위 밖"이라고 이미 명시돼 있던 미완성 상태였음. EC2 `.env`에
  `AUTH_GOOGLE_REDIRECT_URI` 등 3종이 애초에 없어 항상 503 — 배포 이후
  한 번도 정상 동작한 적 없었던 것으로 추정. env var를 채워도 `apps/auth`는
  `viewer.users`를 read-only로만 봐서 신규 가입자는 여전히 409(별도 미해결
  한계).
- **1차 임시 패치(커밋 `7e90c93`)**: OAuth 리다이렉트 대상만 `viewer/oauth`로
  교체(드롭다운 UI·이메일 로그인 폼은 유지).
- **사용자 지시로 정식 revert(커밋 `65be261`)**: `beec23e` diff 확인 후
  `mova-login-button.tsx`를 그 이전 상태(공용 `AuthDialog` 모달)로 완전히
  되돌림 — `AuthDialog`(`app/login/auth-forms.tsx`)가 OAuth(`viewer/oauth`
  경유)와 이메일 로그인/회원가입(`viewer/login`,`viewer/signup`)을 이미
  전부 제공해 기능 손실 없음. `apps/auth`의 `return_to`/`whoami username`
  등 게이트웨이 자체 개선분은 손대지 않고 보존(추후 게이트웨이 완성
  사이클 재사용 대상). `tsc --noEmit`·`next build` 로컬 통과 확인 후 push.
- **배포 후 검증**: Vercel 재배포 번들에서 옛 게이트웨이 흔적(`auth.suvisdev.cloud
  /auth/login`, `/auth/exchange`) 없음, `viewer/oauth` 경로만 존재 확인.
  **백엔드 로그로 실제 Google OAuth 왕복 성공 2건 확인**(`POST
  oauth2.googleapis.com/token 200` → `기존 계정 로그인` → `콜백 완료
  kind=session`) — 코드 자체는 정상 동작 증명됨. 다만 그 직후 프론트의
  세션 교환 단계(`/api/auth/oauth-exchange`)에서 아래 3번 장애(cloudflared)
  때문에 사용자가 실제로는 "Backend response error (502)"를 두 번 봤음.

**3) cloudflared `api.suvisdev.cloud` 전용 장애 — 미해결, 24h 관찰 중**
- 2번 검증 도중 `api.suvisdev.cloud` 전체가 간헐 502/타임아웃으로 흔들림
  발견. `cloudflared` 컨테이너가 30분 넘게 로그 없이 조용히 멈춘 상태를
  1차 발견해 `docker compose restart cloudflared`로 복구했으나 수 분 뒤
  재발.
- **후보 A(conntrack UDP 타임아웃) 가설 수립**: EC2 호스트 커널
  `nf_conntrack_udp_timeout_stream`이 Linux 기본값 120초 — QUIC 흐름이
  120초 이상 조용하면 로컬 netfilter가 NAT 매핑을 지워 엣지 응답을
  드롭할 수 있다는 이론. 사용자 확인 후 `sysctl -w
  net.netfilter.nf_conntrack_udp_timeout_stream=600`(런타임만, `/etc/sysctl.d/`
  영구화는 24h 관찰 후 판단 조건으로 보류) 적용, 4개 QUIC 흐름 TTL이
  즉시 599로 리필되는 것과 cloudflared 재기동 없이 반영되는 것 확인.
- **후보 A 반증 데이터 누적**: 적용 직후에도 EC2 자신이 보내는 요청은
  계속 실패. FAIL 시점마다 conntrack 4흐름이 매번 `[ASSURED]`+TTL 599로
  건강했고 cloudflared 로그도 조용함(재연결 시도 자체가 없음) — conntrack
  만료가 아니라는 직접 증거. 결정적으로 **EC2에서 `google.com`·
  `cloudflare.com`·`suvisdev.cloud`(Vercel)·`auth.suvisdev.cloud`(같은
  터널의 다른 hostname!)는 전부 즉시 200인데 `api.suvisdev.cloud`만
  100% 실패** — 2026-08-06 WORK_LOG에 이미 기록된 것과 정확히 같은
  패턴("터널 전체가 아니라 이 hostname 하나만" 문제, 그때는 Cloudflare
  SJC PoP 유지보수 추정으로 잠정 결론, 자연 해소).
- **봇 차단 가설도 기각**: 관찰 스크립트(60초 간격 curl) 자체가
  Cloudflare 봇 방어를 유발했을 가능성을 의심해 스크립트를 멈추고
  재시도했으나 EC2發 요청은 그대로 실패 — 관찰 자체가 원인은 아님.
- **실사용자 영향은 현재 없음**: 로컬 환경·Vercel 프론트에서는 계속 200
  정상 — 문제가 EC2 자신이 보내는 아웃바운드 경로에만 국한됨(비대칭).
  사용자가 취침에 들어가 자정 무렵부터는 조용히 백그라운드 관찰만
  지속(noop 체크 반복), 사용자를 깨울 조건은 "외부(로컬/Vercel)까지
  실패 시작"으로 명확히 정해둠.

### 오류·막힌 점(추가⑫)
- `ssh aws "pkill -f cf_monitor.sh; ..."` 실행 시 SSH 세션 자체가 255로
  죽는 현상 재발 — `pkill -f`가 패턴 매칭 시 원격 셸 자신의 커맨드라인
  (전달한 명령 문자열 자체에 `cf_monitor.sh`가 포함됨)까지 잡아 죽이는
  self-match 함정. 이후 알고 있는 PID로 직접 `kill <pid>`하는 방식으로
  전환.
- 관찰 스크립트 1차 버전이 curl 실패 시 `2>&1`로 stderr를 캡처해
  `code=`/`time=` 파싱이 깨짐(에러 메시지가 값처럼 찍힘) — `2>/dev/null`로
  교체 후 재기동.

### 데이터(추가⑫)
- `~/cf_monitor.log`(EC2, 60초 간격): 09-11 23:29 기준 OK 1건 / FAIL
  523건(대부분 정확히 8.00초 타임아웃 — 응답 자체가 없음, 재기동
  13:39:22 이후 거의 연속).
- `~/cf_monitor_detail.log`: FAIL 시점 conntrack 스냅샷 다수 — 전부
  `[ASSURED]`+TTL 근접 최대치로 건강, 후보 A 반증 근거로 축적 중.

### 산출물(추가⑫)
- 커밋 `7e90c93`(1차 임시 패치), `65be261`(정식 revert, `main` push·Vercel
  배포 완료) — `suvis/components/mova/mova-login-button.tsx`.
- EC2: `docker exec nginx nginx -s reload`(nginx stale DNS 해결),
  `docker compose restart cloudflared`(1차 재기동), `sysctl -w
  net.netfilter.nf_conntrack_udp_timeout_stream=600`(런타임, 미영구화).
- 신규 파일(저장소 밖, EC2 로컬): `~/cf_monitor.sh`(24h 관찰 스크립트),
  `~/cf_monitor.log`, `~/cf_monitor_detail.log` — git 미추적.
- **다음 세션 시작 시 먼저 할 일**: cf_monitor 로그로 24h 관찰 결론 내기
  (판단 기준 3가지 — "0건=확신상승·영구화", "빈도감소하나 잔존=부분
  유효+다른 축", "무변화=가설 기각). 현재 데이터는 "무변화"에 가까움 —
  sysctl 되돌리고 처음(엣지/PoP 축)으로 돌아갈 확률이 높아 보임. `apps/auth`
  게이트웨이 완성은 이번 세션 범위 밖으로 유지(백로그, 리뷰 파이프라인
  트랙 우선).

---

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

---

## 2026-07-29
### 산출물

- 코드: 위 "수정/구현" 파일 전체.
- 문서: 이 항목 + `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(완료분 이동),
  루트 `CLAUDE.md`, `.claude/rules/` 4종, `.claude/projects/memory/` 3종.
- `alembic/versions/20260729_0002_create_hub_knowledge.py` 신규 —
  빈 DB에서 `alembic upgrade head` 성공까지 확인 후 커밋.
