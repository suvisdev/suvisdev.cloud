# SUVIS 어드민 대시보드 + 멀티에이전트 진행 상황

컨텍스트가 끊길 경우를 대비한 재개용 메모. 완료된 작업은 상세 로그 대신
**위치만** 남긴다(중복 기록 방지). 관련 상세 지시서:
- `suvisdev/_docs/RBAC_agent_dashboard.md` (RBAC + 어드민 대시보드 H0~H4)
- `suvisdev/apps/ontology/_docs/00_COMMON_conventions.md` + `01~08_*.md` (에이전트별 지시서)

2026-09-03 정리: 완료 항목의 상세 서술은 전부 삭제하고 워크로그 포인터만
남김(중복 제거). 상세는 `WORK_LOG_MOVA.md` / `WORK_LOG_MAINPAGE.md` /
`WORK_LOG_GILDLE.md`의 해당 날짜 참고.

---

## 완료됨 (워크로그 날짜 인덱스 — 상세는 재기록 안 함)

날짜 앞 표기: `[M]` = WORK_LOG_MOVA, `[P]` = WORK_LOG_MAINPAGE, `[G]` = WORK_LOG_GILDLE.

- `[P]` 09-09 노트북 프로덕션 컷오버 후 실사용 검증(API 전수 — backend·gildle 경로계산·auth·웹 카카오 OAuth 302 · 터널 530=WSL 미부팅 진단 · auth 게이트웨이 `AUTH_*_REDIRECT_URI` env drift 발견)
- `[M]` 09-09 "정치 스릴러" 무관 픽 종결(교집합 메커니즘 규명 · 프로덕션 실측 2회 남산의 부장들·야당으로 교정 확인)
- `[M]`·`[P]` 09-09 LoRA 재학습 배치 큐 소진 + 노트북 lora-server AWQ→GGUF 이전(교사 92→94건 재생성 · 3에폭 loss 0.52 `mova_20260909_025528` · GGUF Q5_K_M · 노트북 소스 CUDA 빌드 sm_89 · drop-in override 전환 · RTX 4060 256tok 2.38s · hook 캡 120→80 · evaluate 줄거리+리뷰 종합)
- `[P]` 09-07 데스크톱 인프라 compose→k3s 전환 완주(`k8s/` 매니페스트 9종·deploy.sh · Docker Desktop `/Docker/host` 마운트發 kubelet 크래시 해결(systemd drop-in) · 구 compose 볼륨 DB 이전·검증)
- `[P]` 09-07 노트북 프로덕션 k3s 1단계 컷오버(backend·auth·cloudflared 파드 · db·redis 도커 외부 연결 `external-db-redis.yaml` · `nginx-alias.yaml`로 502 복구 · 도커 backend·auth·nginx stop 보존)
- `[M]` 09-03 무관 픽 '식객' RAG 연도 재검증 · 회귀 하네스 신설 · 키워드 사전 11엔트리 백필 · 분류기 추천 확정 가드 · general 429→200 강등
- `[M]` 09-02 RAG∪태그 합집합 + `_FILLER` 정규식 수정 · booking 탐색형 질의 · 다중 장르 AND · "최신영화" booking 오분류 · 교사 데이터셋 92건 재학습 · llama.cpp GGUF 전환 · 전체 점검 + DB 정비 · lora-nb 터널
- `[M]` 09-01 데스크톱 lora-server 재구축 + LoRA 재학습 · 컬렉션 v3 · 키워드 태그 백필 완주 · vote_count 베이지안 가중 정렬 · 터널 토큰 잠금 · 감정분석 프로덕션 백필
- `[M]` 08-31 리뷰 유용성 투표 + 감정분석 스케줄러 · 감정분석 통합/자동별점/감정요약/신뢰도 배지 · 오타 허용 제목 검색 · booking Phase 2 롯데시네마 시간표
- `[P]` 08-31 mypy 재활성화(415→0) · `google.genai` 마이그레이션 · 챗바 useCallback 리팩터링
- `[M]` 08-28 채팅 응답 트랙 재설계 Phase 1(분류기 5종·evaluate·booking) · 클래식 시대 어휘 연도 매핑 · 폴백 정직 문구 · Gemini 백필 키 분리
- `[G]` 08-27 여름 그늘 경로
- `[P]` 08-27 LLM 챗 3종 require_admin 잠금 · EC2 auto-deploy 재작성(nginx reload) · `/mail` 관리자 전용 전환
- `[M]` 08-26 zero-rec 실측 + 언어 허용목록 · RAG 부활(EMBEDDING_BACKEND=gemini, 재임베딩) · 불만 발화 general 라우팅 · dedup 소진 대안 · Gemini 자동 폴백 DI · 헤더 통합 · 검증 파이프라인 복구 · 지킬 블로그
- `[M]` 08-25 대규모 정비(LoRA 재학습 등) · EC2 lora 복구 · EC2 이미지 통합 · Jekyll 배포 · 에디터 리뷰 배치 + 24h 스케줄러
- `[G]` 08-25 서울 전역 확장 + OSM 나무/공원 점수 · 08-21 CSV→PostgreSQL + Leaflet · 08-20 소개 페이지 + 보행 그래프
- `[M]` 08-19 멀티턴 필터 오염 수정 · 초성게임 외국 영화 혼입 수정
- `[M]` 08-18 취향 벡터 재정렬 · 배우 인식 옵션 A · 컬렉션 배정 API/CLI · 컬렉션 v2 · 레거시 12편 정리 · 개봉예정 과거 필터 · cloudflared 24h 관찰 종결
- `[M]` 08-14 채팅 3건 후속 · 푸터 + TMDB attribution + 약관/개인정보 · TMDB KR 356편 수집 + 성인물 130편 purge
- `[M]` 08-13 사이클 A~J(초성 게임 정답·무제한 모드·랭킹·개봉예정·auth TTL·카탈로그 대량 확장)
- `[M]` 08-12 만료 세션 fix · 대화 스레드 저장 v1 · 사용자 리포트 C~R
- `[M]` 08-11 로그인 장애 · nginx stale DNS · HNSW 인덱스 + planner 힌트 · reviews.embedding · 취향 벡터 γ · movies.embedding 크론 백필 · 정식 이미지 재빌드
- `[M]` 08-10 Gemini 호출 2→1회 + 429 재시도 · `.env` 단독 `1` 제거 + drift 탐지
- `[M]` 08-07 하네스·문서 정비 · 마이페이지 3종 · 선호 장르 온보딩 · 무인증·IDOR 5건 수정 · `original_language`
- `[M]` 08-06 카탈로그 확장 종결 · 홈 피드 배선 · 챗 502 수정 · synopsis · 필터 UI · `search_tag_catalog` 개선 · 랜딩 네비 · 컬렉션 시드 · hub_knowledge Phase 2 백필
- `[M]` 08-05 수집 첫 실전 배치 · Tunnel 연동 · `character_name` truncation · 품질 검증 Phase 1 · 오귀속 수정 · UI 감사
- `[P]` 08-04 EC2 S3 실연결 + OCR · 방문자 alembic 재확인 · Neo4j 노드 재확인 · credits 백필 재확인 · 리뷰 watched 게이트
- `[P]` 08-03 susu 카카오 로그인 + JWT · 추천 챗 화면 · 네비게이션/로그아웃 · 폰 카메라→S3 · 원격 GPU 하드닝
- `[P]` 08-02 로컬 개발 DB 세팅 · 수집 파이프라인 코드
- `[P]` 07-31 리뷰 보안 Phase A · 리뷰 UX · 어드민 통계 방문자/크롤링 탭 · 레슨 메뉴 admin 전용
- `[P]` 07-30 Neo4j provisioning + 스키마 · EC2 alembic 로그인 500 복구 · 어드민 미노출 + OAuth 닉네임 · TMDB credits 배선 · Sentinel 소프트 플래그 · execsuite 네이밍 정정
- `[P]` 07-28~29 execsuite 이름 변경 + LangChain 채팅 · 테스트 수정 다수 · 인증 공백 감사 · `ENABLE_MOVA_STARTUP` · labs 03·04·08 · CLIP hang · lora-server 노트북 재세팅
- `[P]` 07-27 alembic 베이스라인 · PDF 파이프라인 · 03 Loom 제외 확정
- `[P]` ~07-27 어드민 대시보드 전 화면 · 01 이미지 분류 · 06 Sentinel · 07 Echo (H0~H6) · 02~08 H0 스캐폴딩

---

## 진행 중 (현재 액티브)

### 개인 백엔드 EC2 → 노트북 이전 — 컷오버 완료(2026-09-03 밤)
- `api.`/`auth.suvisdev.cloud`는 **노트북(teagy)**이 서빙 — 09-07 k3s 1단계
  컷오버로 backend·auth·cloudflared는 파드, db·redis는 도커 컨테이너
  (`deploy.sh --external-db`). 터널 `suvisdev.cloud`의 커넥터는 노트북 단독.
  프로덕션 DB는 EC2 덤프(09-03) 복원본.
- ~~EC2 개인 스택 down·Elastic IP·t3.small 축소~~ — **09-04 결정 변경으로
  폐기**: Arda는 신규 `arda-api`를 생성했고, 개인 EC2는 **중지 보관**
  (EBS 월 ~$3, 필요 없다고 확정되면 종료. ARDA_AWS_DEPLOY_GUIDE 표 참고).
- **남은 것**: ~~① 노트북 lora-server 어댑터 동기화~~ **(09-09 완료)** —
  노트북을 AWQ(serve.py)→GGUF(serve_gguf) 스택으로 이전하고 재학습 어댑터
  `mova_20260909_025528`(loss 0.52) 반영. 소스 CUDA 빌드(sm_89)+drop-in
  override, RTX 4060 256tok 2.38s. 상세 `[P]`·`[M]` 09-09.
  ~~브라우저 실사용 검증~~(09-09 API 레벨 전수
  완료 — 채팅·gildle 경로계산·auth·웹 카카오 OAuth 302까지 실측, `[P]` 09-09.
  카카오 동의 화면부터의 브라우저 클릭만 사용자 확인 잔여). ~~루트 CLAUDE.md
  낡은 EC2 서술 갱신~~(09-08 완료 — 노트북 k3s·EC2 중지 보관 기준으로 교체).
  상세: SUBDOMAIN_MIGRATION_PLAN.md.

### 서브도메인 이사 — seuk(팀 프로젝트)만 (2026-09-03 결정 변경)
- **개인 앱(mova·gildle)은 이사 안 함** — 서빙 실익 없음(세션 분리·OAuth
  복귀 갭·중복 URL). 리라이트 `0bef4f3` 되돌림(저녁 세션, 푸시 대기).
- **팀 인프라 이전 완료(09-04, `[P]` 09-04 상세)**: 개인 AWS에 EC2
  `arda-api`(t3.small, 16.184.62.242) + S3·SQS·SES·IAM 분리 + Caddy HTTPS
  (`api.seuk.suvisdev.cloud`) + CD(2분 폴링) + DB alembic 0008 정합 +
  Vercel `VITE_API_BASE` 전환. Seuk-Team/Arda main 동기화·PR #2 머지,
  서버 remote 전환 완료.
- **남은 것(Arda)**: ① SES 프로덕션 승인 → `MAIL_DRY_RUN=0` + api·worker
  재기동 ② GPU 쿼터 승인 → `arda-gpu`(g4dn.xlarge) 생성 + CloudWatch 자동
  중지(가이드 5단계) ③ 사용자 몫: main 보호 토글 복구·Team-Seuk/Arda 삭제
  (Vercel이 Seuk-Team에 연결된 것 확인 후)·바탕화면 키 csv 삭제 ④ 팀 실데이터
  UI 검증(공고→지원→메일) ⑤ 팀원 admin 계정 발급(`POST /api/v1/auth/signup`)
  ⑥ 10/27 철거 체크리스트(가이드 맨 아래). 실행 기록·Q&A:
  `_docs/ARDA_AWS_DEPLOY_GUIDE.md`.

---

## 다음 / 남은 작업 (백로그)

### 우선순위 방향 (2026-09-02, 사용자 결정)
**당분간 신규 기능보다 mova 채팅 품질 향상에 주력한다** — 실사용 오답·
오분류·무관 추천 감소가 우선, 새 트랙·새 기능은 보류. 로그 추적 → 근본
원인 → 결정론 가드+테스트 패턴으로 진행. 회귀 하네스
(`scripts/eval_chat_queries.py`, 23질의)는 상시 사용.

### mova 채팅 품질 잔여
- ~~"정치 스릴러 영화" 무관 픽~~ — **09-09 종결**(`[M]` 09-09): 프로덕션
  실측 2회 모두 남산의 부장들·야당으로 정상. 09-03 백필의 정치 태그가
  스릴러 장르 태그와 교집합(`tag_and_ids` prio)을 이뤄 후보 맨 앞에 오는
  구조로 설명됨. 09-03 당일 "미개선" 기록과의 차이(당시 EC2 vs 현 노트북)는
  원인 미상으로 남김 — 재발 시에만 노트북 DB INTERSECT 실측으로 재개.
- ~~의도 추출 Gemini 429 재시도 지연~~ — **09-11 해소(결정론 우선, 배포 대기)**:
  08-19 멀티턴 오염 수정 2건(f59f1d4·5c9c24c)이 Gemini 추출 산출물을 전부
  결정론 결과로 덮은 뒤로 **호출만 남고 결과는 미사용**(순수 지연+쿼터 낭비)
  이었음을 확인하고 호출 자체를 제거. 출력 동일(테스트 8건 재작성으로 고정),
  질의당 0.9~5s 절감 + Gemini 쿼터 1건 절약. 부수 발견: 구 QUALITY_PHASE1 §9
  "Gemini 배우 보강"은 08-19부터 사실상 무력화돼 있었다 — 재도입하려면 현재
  턴만 Gemini에 주고 must.actors만 병합하는 별도 설계 필요(`.claude/rules/
  mova-chat.md` §2 갱신).
- **취향 재정렬 후속(08-18 신규)**: alpha 별점 결합 튜닝(현재 순수 코사인),
  후보 window 확대(taste vector 있는 유저에게 limit 16 이상 — 프롬프트
  토큰·Gemini 요금 트레이드오프).
- **엔티티 매칭(편집거리·초성·수사 변환) — 보류**: 프로덕션 로그 오타 질의
  0건(08-26, 09-03 재확인). 재검토 트리거: ① zero-rec 재실측에서 제목/배우
  오타·음차 질의가 쌓일 때 ② 검색창·초성 게임 판정 등 UX 직접 개선 지점
  ③ 채팅 제목 직접 언급 증가. 도입 시 ATS 순수 Python 구현 복사(의존 금지)
  → `intent_extraction` 결정론 경로.

### RAG 임베딩 bge-m3 전환 — 코드 완료, 노트북 컷오버 대기 (2026-09-11)
- **실측 근거**(`scripts/eval_embedding_models.py`, 60질의·패러프레이즈 포함):
  bge-m3 recall@8 **0.860** vs e5-base 0.765 vs 현행 nomic **0.390**(한국어
  취약). bge-m3 채택 — 접두사 불요·Ollama 공식, 비용은 hub_knowledge 한
  테이블 1024 마이그레이션뿐(movies/reviews/taste·dispatch는 각자 768 공간).
- **완료**: `EMBEDDING_DIM` 1024, Ollama 어댑터 기본 bge-m3, alembic
  `20260911_0001`, ingest 호스트 실행 지원. 데스크톱 검증(alter+gemini 10편
  색인+1024 벡터 검색 히트) 완료.
- **남은 것(노트북, 절차 엄수)**: `ollama pull bge-m3` → pull·deploy →
  `alembic upgrade head` → `ingest_hub_knowledge.py --reset
  --embedding-backend ollama`(859편) → eval_chat_queries 회귀. 상세:
  `suvisdev/_docs/RS_TEACHER_LOOP.md` §2.

### RS 교사 루프(엑사온 데이터셋 v2) — 파이프라인 완성 (2026-09-11)
- 학생(EXAONE) 온도 4종 후보 생성 → 그라운딩 하드 필터 → Gemini 루브릭
  심판(7점 미만은 교사 작성 폴백) 구조. `rs_mine_queries.py`(실질의 채굴) +
  `rs_generate_and_judge.py`(생성·심판·감사로그, 재개 지원).
- 데스크톱 스모크 E2E 통과 — 단 로컬 카탈로그(205편·장르만)라 심판 6점으로
  전건 교사 폴백. **본 실행은 노트북 호스트에서**(프로덕션 카탈로그 + 내부
  llama-server 8201 온도 샘플링). 학습은 기존 배치 큐 원칙: v2가 300건+
  모이면 stop→train→GGUF→reload→eval 한 번에. 상세: RS_TEACHER_LOOP.md §1.

### LoRA 재학습 배치 큐 (2026-09-03 사용자 결정 — 매 변경마다 학습 금지)
- **원칙**: 상류 변경(태그 사전·후보 조립·프롬프트 입력)은 계속 쌓되,
  재학습은 진짜 트리거(출력 계약 변경 / 생성 단계 체계적 실패 / 데이터셋
  유의미 증분)가 모였을 때 **한 번에**: 데이터셋 재생성 → 학습 → GGUF
  변환(`export_mova_gguf.py`) → /reload.
- ~~현재 큐 ①②~~ **(09-09 소진)**: 교사 데이터셋 92→94건 재생성(09-03 태그로
  뉴욕·유럽·프랑스 부활) → 3에폭 재학습(loss 0.52, `mova_20260909_025528`)
  → GGUF → 노트북 배포까지 완주. **hook 다이어트(②)는 재학습 불요로 판명**
  (교사 hook 16~35자·프롬프트 이미 40자 이내 → 120→80은 방어 캡만 조인 것),
  캡 변경만 코드 반영. 상세 `[M]` 09-09.
- **현재 큐(잔여)**: 이후 태그 사전 확장분. 잔여 교사 스킵 15건(배우명·형사물·
  정치 스릴러 등)은 실서비스 정상이라 태그 사전 확장 여지로만 남김. hook
  프롬프트 목표를 40자 미만으로 낮추려면 그때는 교사 completion 재생성 필요.

### ~~EC2 전체 재빌드 불가~~ — 폐기(개인 백엔드 노트북 이전으로 무의미)
- 09-03 노트북 이전 + 09-04 개인 EC2 중지 보관 확정으로 30GB 디스크·
  파생 빌드 누적·auto-deploy 드리프트 이슈 전부 소멸. 노트북은 전체
  재빌드 가능(09-03 pip 레이어 재설치 14.6GB 실증). "EBS 증설 vs 로컬 빌드
  전송" 결정 건도 함께 폐기.

### lora-server 운영 수칙·감시 (2026-09-02)
- 학습 직후 바로 start하면 VRAM 지연 반환과 겹쳐 5배 열화(31~34s) 재현 —
  **stop → `nvidia-smi` VRAM 하강 확인 → start** 순서 고정. 재발 시 응급
  처치 `systemctl --user restart lora-server`.
- GGUF 전환(serve_gguf.py, 256tok 3.2s·VRAM 2.7GB) 후 기준선. 구 serve.py는
  롤백용 보존. 열화 근본 원인(단편화→WDDM 스필 추정)은 미확정.
- `is_ready()` 헬스체크가 코드 어디서도 안 불림(08-05부터 알려진 별개 이슈).

### 에디터 리뷰 감정분석 — 주기 백필 루틴 필요 (2026-09-02)
- 일 15편 자동 에디터 리뷰가 EC2(GPU 없음)에서 sentiment/rating NULL로
  쌓임(이틀 41건). 데스크톱 백필(터널 15432 +
  `backfill_review_sentiment_cli.py`)을 **주 1회쯤 루틴화**할 것. 접속 방법은
  WORK_LOG_MOVA 09-02 후속 5 메모.
- ~~CLI 개선: 건당 모델 로드/해제라 41건 ≈ 30분~~ **배치화 완료(09-11)**:
  `EchoSentimentAdapter.analyze_batch`(로드 1회 순회, 개별 실패는 None으로
  계속) + `analyze_missing` 배치 경로 전환. fake 단위 테스트 4건
  (`test_review_sentiment_backfill_batch.py`). Router BackgroundTasks 단건
  경로(analyze_one)는 종전 그대로. **실제 백필 실행은 노트북 학습 종료 후**
  (프로덕션 DB 접근 경로 필요 — WORK_LOG_MOVA 09-02 후속 5 메모).

### 채팅 응답 트랙 재설계 잔여 (설계: `suvisdev/apps/mova/_docs/MOVA_CHAT_INTENT_REDESIGN.md`)
- **Phase 2 시간표 확장**: 현재 롯데시네마만. 타 체인 추가 시 약관·robots
  실확인 선행(§5).
- **Phase 3 영화관 리뷰**: 수요 보고 결정(보류).

### 뉴스 기반 에디터 리뷰 잔여 (2026-08-25)
- 에디터 리뷰 출처(뉴스) 링크 표시 — 신뢰도 배지는 08-31 완료, 출처 링크는
  미구현. 크롤링은 어드민 harvester 수동 트리거뿐(상시 스케줄 없음).

### mova 법적 페이지 후속 (2026-08-14)
- 문의 이메일 최종 확정 — 푸터·개인정보 처리방침 모두 `ssuvisdev@gmail.com`,
  전용 support 주소로 바꿀지 결정 필요.
- (선택) 시행일 변경 시 `/mova/terms`·`/mova/privacy` 부칙·개정 이력 섹션.

### TMDB KR 카탈로그 확장 잔여 (2026-08-14)
- vote_count≥100 상위는 이미 카탈로그에 대부분 있어 신규 확보량 낮음.
  규모를 진짜 늘리려면 `--vote-count-gte 50` 또는 `20` — 무명작·저평점 유입
  트레이드오프(초성 게임 품질). 베이지안 가중 정렬(09-01)로 노이즈 방어는
  생겼음.

### 보안 백로그 (2026-09-09 전수 조사)
- ~~🔴① vision `/upload` 무인증+무제한+GPU DoS~~ **배포·검증 완료**(`f7703bc`,
  require_user+10MB+MIME, 프론트 토큰 전달 — 프로덕션 무인증 업로드 401 실측).
  ~~🔴③ CORS `["*"]`+credentials~~ **배포·검증 완료**(화이트리스트 — suvisdev.cloud
  허용·evil.com 차단 실측).
- ~~🔴② 노트북 lora-server 무인증~~ **완료**: backend `.env`엔 토큰이 이미
  있었고 serve_gguf 유닛에만 없어 검증을 안 하던 것 → 기존 토큰을 유닛
  드롭인에 추가·재기동. 무인증/오토큰 401·정상 200 실측.
- ~~🟡 mova `POST /import/tmdb·/kofic` 무인증 쓰기~~ **코드 수정 완료(09-11,
  배포 대기)**: `require_admin` 부착 + 401/200 테스트 4건
  (`test_import_router_auth.py`). 프론트 호출처 없음(수동/스케줄러 전용)이라
  토큰 전달 배선 불요. ~~🟡 media 오류 원문 노출·크기검사 전 전체 적재~~
  **코드 수정 완료(09-11, 배포 대기)**: 502 detail 일반 문구화(원문은 로그),
  업로드는 상한+1바이트까지만 read.
- **🟡(잔여)**: access TTL 7일+웹 리프레시 미사용 · 토큰 localStorage(httpOnly
  쿠키 부재) — 인증 구조 변경이라 별도 설계 필요 · pgadmin admin/admin(replicas:0).
- **09-11 전체 코드 리뷰 + 후속 수정 ①~⑤ 완료(배포 대기)** — 리뷰 결과·처리
  현황·잔여 목록의 SSOT는 `suvisdev/_docs/CODE_REVIEW_2026-09-11.md`. 요지:
  인증 3건(평문/pass-the-hash·미검증 이메일 admin·admin1234 시드) + 무인증
  엔드포인트 10곳 가드 + gildle DoS 상한 + 중간 1~5 + 성능 캐시 + 데드 코드
  42파일·스크립트 30개 아카이브. **잔여(중간 6~15·낮음 전부)는 문서의
  "처리 현황 → 잔여" 참고.** 배포 시 auth 파드 재배포 필수, viewer
  login/signup은 404가 정상(언마운트). 평문 저장 계정이 있으면 로그인 불가
  (재설정 대상).
- ~~미확인: S3 버킷 실제 공개 여부~~ **비공개 확인(09-11 실측)**: boto3로
  PublicAccessBlock 4항목 전부 True + 버킷 정책 없음(NoSuchBucketPolicy) +
  ACL 소유자 FULL_CONTROL 단독. CLAUDE.md의 private 기술이 맞음.

### mova 채팅 UX 잔여 (2026-09-09)
- ~~evaluate 맥락 이음·정직~~ **배포·검증 완료**(`525dc80` — "어떠냐고"→직전 영화
  역조회 evaluate, 줄거리 선행+리뷰 종합, 프로덕션 response_type=evaluation 실측).
- ~~Issue 2(선택지 칩)~~ **배포·검증 완료**(`cab9edd`): ambiguous 후보를 응답
  스키마 `choices`(제목·연도·slug)로 구조화 + 프론트 클릭 칩(클릭 시 "{제목}
  어때?" 전송). 프로덕션 E2E 실측 — 미션임파서블·해리포터는 choices 3건,
  존윅 등 단일은 choices 없이 바로 evaluation. 제목 해석기 일반 로직
  (스파이더맨 전용 아님).
- **교사 스킵 태그 확장은 무용 판정(09-09)**: 라벨 이미 존재, 원인은 배우 매칭·
  origin_country 백필·카탈로그 커버리지. 실오답 트레이스 시 표적 수정(A안).

### 구조·인프라 백로그 (착수 전, 우선순위 낮음)
- ~~evaluate 개선·hook 캡 backend 코드 미배포(09-09)~~ **배포 완료**: hook 캡
  120→80 · evaluate 프롬프트(줄거리+리뷰 종합)가 e2f8034→e7b3f66 재배포로
  프로덕션 반영·검증됨.
- ~~노트북 lora-server 토큰 미설정(09-09 발견)~~ **09-09 저녁에 이미 해소** —
  보안 백로그 🔴②와 같은 건이었다(같은 날 오후 발견 기록이 정리 안 된 채
  남아 있던 것, 09-11 모순 정리). 기존 토큰을 유닛 드롭인에 추가·재기동,
  무인증 401·정상 200 실측 완료(`[P]` 09-09 저녁).
- **auth 게이트웨이 웹 OAuth env drift(09-09 발견)**: `/auth/login/{provider}`가
  503 — `AUTH_{GOOGLE,KAKAO,NAVER}_REDIRECT_URI`가 `.env.example`엔 있는데
  노트북·데스크톱 `.env` 모두 없음(컷오버 회귀 아님, 원래 미설정).
  현 프론트는 backend viewer OAuth(`/viewer/oauth/...`)를 써서 실사용 영향
  없음 — susu가 게이트웨이 웹 플로우를 쓰게 될 때 프로덕션 도메인 기준
  값 확정해 3키 보충 + Secret 갱신·rollout. `check_env_drift.py`가 잡는 케이스.
- **노트북 k3s 잔여 단계**(1단계는 09-07 완료 — 완료됨 인덱스 참고):
  2단계 redis 이관, 3단계 db(pgvector)는 밖에 둬도 무방(`k8s/README.md`).
  도커 backend·auth·nginx는 stop 상태로 롤백용 보존(`down` 금지). 배포는
  `./k8s/deploy.sh --external-db [--build]`.
- **mova만 백엔드 `/api` prefix 없이 마운트됨(08-04)**: 다른 앱은 전부
  `/api`·`/api/v1`인데 `mova_router`만 `/mova/...`. 통일하려면 susu가
  `/mova/...`를 직접 호출하는 곳까지 같이 바뀌어 블라스트 레이디어스가 큼 —
  별도 계획 필요.
- **Neo4j GraphRAG 활용 코드 부재(08-04)**: 노드 데이터(Movie 40 등)는
  있지만 읽는 코드가 없음. 어느 앱이 어떻게 쓸지 설계부터.
- **susu 실기기 검증 미완(08-03)**: ① 폰 카메라→S3 업로드 실촬영 검증
  + access token 10분 만료 시 refresh 미구현 ② 카카오 로그인 iOS 실빌드
  검증(Android만 E2E 완료) ③ 추천 챗 화면 `flutter run` 검증(adb 끊김,
  `flutter analyze`만 클린).
- **비전 02(Argus)·05(Prisma)**: 02 용도 결정, 05 용도+VRAM 전략 필요 —
  제품 결정 전까지 착수 안 함.
- **시크릿 (a)**: app별 pydantic-settings 도입이 결정될 때만 mova·ontology
  키 접근을 함께 이관(단독 실행 금지, WORK_LOG_MAINPAGE 2026-07-24).

---

## 참고: 02~08 적합성 감사 (2026-07-23, `00_COMMON_conventions.md` §8)

06의 실패(기법 먼저·용도 나중)를 기준으로 재감사한 결과.

| # | 이름 | 상태 |
|---|------|------|
| 02 | Argus(객체 검출) | 보류 — 용도 위험/데이터 불확실, 제품 결정 전까지 착수 안 함 |
| 03 | Loom(분할) | **제외**(2026-07-27) — 관문0 실측: 보도 신호가 서울 OSM에 없음(문서 배너) |
| 04 | Atlas(자세 추정) | **제외** — mova/gildle에 용도 없음(문서 배너) |
| 05 | Prisma(이미지 생성) | 보류 — 용도 불확실 + 하드웨어 위험(SD1.5 LoRA vs lora-server VRAM 겹침) |
| 06 | Sentinel(이상 탐지) | **완료**(H0~H6, `/vision/upload` 게이트) |
| 07 | Echo(감정분석) | **완료**(H0~H6) |
| 08 | Chronos(영상 분류) | **제외** — mova/gildle에 용도 없음(문서 배너) |

## 참고: VRAM 정책 (확정, `00_COMMON_conventions.md` §1.1)

`lora-server`(mova 채팅용 EXAONE-2.4B, 현재 llama.cpp GGUF)가 상시 기동 →
**모든 학습 전 `systemctl --user stop lora-server`**, 학습 후 VRAM 하강
확인 → `start` + `:8200/health` 확인 필수. `nvidia-smi` free 수치만 믿지
말 것(WSL2 계측 불안정, 290MB↔7975MB 편차 사례).
