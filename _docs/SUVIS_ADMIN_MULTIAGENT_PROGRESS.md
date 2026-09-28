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

- `[M]` 09-22 멀티턴 학습 데이터셋 구축(교사 470행이 전부 단일턴인데 서빙은 6턴 히스토리 주입 — 학습·서빙 불일치 규명 · `build_multiturn_dataset.py` 4패턴 231행 · 최종 607행 하드 체크 전 행 통과 · 코랩 노트북 평가셋에 멀티턴 포함 + `nopick_ok` 체크 추가 · 09-17 어댑터 폐기 결정 · 바탕화면 `colab/mova-colab-20260922/` 배치, **코랩 실행은 사용자 대기**)
- `[M]`·`[P]` 09-17 f745447 노트북 프로덕션 배포(빌드 6m10s) + RAG 임베딩 bge-m3 컷오버 완주(`EMBEDDING_BACKEND` gemini→ollama 정정 · alembic `20260911_0001` · 파드 안 재색인 2,965건 실패 0 · 회귀 23/23 PASS · vector_search 1024 히트 실측)
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
- **⛔ 09-28 사용자 지시: Arda는 해커톤이 끝날 때까지 손대지 않는다**(조회 포함). 아래는 종료 후 재개용.
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
원인 → 결정론 가드+테스트 패턴으로 진행. 회귀 하네스 두 개를 상시 사용:
`scripts/eval_chat_queries.py`(23질의, 단일턴)·`scripts/eval_chat_multiturn.py`(6장면,
history 포함 — 09-22 밤 신설, 실대화 로그 기반). 노트북에선 `--base-url
http://127.0.0.1:31386`.

### 저장소 정리 (2026-09-27 저녁, `[P]` 09-27)
- Qwen 명칭 제거(실체 EXAONE), 데드 코드 백엔드 94파일·프론트 64파일·의존성 35 삭제, `route_requests/
  route_results` 드롭(`20260927_0002`). 남은 후보: 프론트 shadcn `button/card/dialog` 하위 export(라이브러리
  성격이라 보류), `eslint-config-next`(knip 오탐 — flat config compat이 씀).

### 메인페이지 (2026-09-28 갱신)
- **09-28 2차 개편(`[P]` 09-28)**: 심플 중앙 구조 유지 + 07월 컨셉 포인트만(콘덴스드 헤드라인·노란 악센트).
  대화 패널은 입력창 위, 타일에 개인/팀 프로젝트 라벨. 우하단 플로팅 채팅 버튼(`gemini-chat-panel`) 삭제.
- **홈 개편 배포 완료(`adef914`, Vercel 반영 확인, `[P]` 09-27)** — 이후 같은 날 입력창을 AI 채팅으로 전환(아래): 로고 → 검색창 → mova·gildle·arda 3타일. 데이터는 `apps-catalog.ts`.
- **홈 AI 채팅 배포 완료(09-27 새벽, `[P]` 09-27)**: `POST /portfolio/chat` — ontology에 유스케이스·라우터 추가,
  `hub_knowledge(source='portfolio_doc')` 124청크(프로필 + 지킬), EXAONE 7.8B(ollama, num_ctx 8192)→Gemini 폴백,
  IP 20회/60s. 운영 스모크 4종 정상·mova 23/23 유지. 계획서 `suvisdev/_docs/plans/2026-09-27-portfolio-chat.md`.
- 09-28: 프로필에 "Gildle(길들)" 별칭·유래 추가 후 파드에서 프로필만 재색인(리셋 없이 upsert). **테마는 경로 고정**(사용자 결정):
  `/mova/**` 다크·그 외 라이트를 `forcedTheme`로, 토글·`setTheme` 코드 전부 삭제(탭 간 storage 동기화로
  라이트 뒤집히던 버그도 함께 해소).
- 홈 채팅 잔여: ① 문서 갱신 시 `ingest_portfolio_docs.py --reset` 재실행(수동; 파일 하나만 바뀌면 파드에서
  리셋 없이 그 디렉터리만 넘겨도 됨 — `datasets/`는 hostPath) ② 7.8B 상주로 VRAM 7.8/8.2GB —
  mova 지연 실측되면 `PORTFOLIO_LLM_MODEL=exaone3.5:2.4b` 또는 `PORTFOLIO_LLM_BACKEND=gemini` ③ 후속 질문의
  검색어에 이전 턴 결합 ④ 스트리밍 ⑤ ontology `api/__init__.py` lazy import(테스트가 torch를 끌어옴).

### mova 리뷰 배치 (2026-09-27 조사)
- 에디터 리뷰 생성 스케줄러 정상(일 1~20건, 주기당 대상 15편 — 미생성 3,209편 남음, 속도 상향 여부 결정 필요).
- ~~감성 분석 스케줄러 전량 실패~~ → **09-27 밤 수정**: 파드에 GPU가 없는데 4bit(bitsandbytes) 로드를 하드코딩한
  것이 원인, CPU bf16 경로 추가 + 호스트 HF 캐시 마운트(`[M]` 09-27). 백로그 430/430 완료, 이후 24h 스케줄.

### mova 채팅 품질 잔여
- **오케스트레이터 층 도입(09-27 저녁, `[M]` 09-27)**: EXAONE 7.8B 이해 → 카탈로그 검증 → 트랙 실행.
  기존 결정론 경로는 폴백으로 유지. core/lol은 `suvisdev_orchestrator.py`(`SuvisdevOrchestrator`,
  `understand_json`)·`lora_server_client.py`로 개명. **다음**: 프로덕션 한 주 관찰 후 폴백 선분기 4단·트랙 정규식
  제거, 『제목』 마커 파싱 → 구조화 슬롯. 설계 `apps/mova/_docs/MOVA_CHAT_ORCHESTRATOR.md`.
- **09-28 오후(`[M]` 09-28)**: 롯데시네마 회차 예매 딥링크(`link_channelCode=naver` 계열)·극장 시간표 링크,
  CGV·메가박스 극장은 네이버 상영시간표 검색 링크,
  평가 응답 mova 리뷰 기준(TMDB 평점 제거)·2~4문장 요약, "봤어요" 영화 추천 제외(종전엔 미구현).
- **09-27 오후 예매 대화 할루시네이션 수정·배포**(`[M]` 09-27 오후): 시간표 발화 general 오분류 →
  결정론 booking 선분기, general 프롬프트 실시간 사실 금지, 제목 해석기 1자 어간('파과'→'파') 제거.
  이어서 '몇 시' 어휘·어절 정확 일치 추가, 멀티턴 하네스 6→10장면(프로덕션 10/10). LoRA 학습 대상
  아님(예매·잡담 트랙은 LoRA 미사용). 잔여: 분류기 entities 품질 관찰(로그에 추가됨).
- ~~히스토리 코드 4건 수정~~ **09-22 밤 배포·검증 완료**(멀티턴 하네스 2/6→6/6, 단일턴
  21/23 유지, `[M]` ㉒). "기억 못한다"는 LoRA가 아니라 이 코드 문제였음(예매 트랙은 LLM
  미사용). 잔여: 분류기가 "줄거리 알려줘"를 evaluate 아닌 recommend로 보냄.
- **v5 데이터 준비 완료(09-23 새벽, `[M]` ㉓)** — 856행(honest_genre 제거·연도/장르 27행 Haiku
  교사), 노트북 `ref_pick_ok`. 바탕화면 `mova/FT/mova-colab-v5/`. **코랩 실행은 사용자** — 09-27
  드라이브 마운트 실패로 중단 → 노트북에 드라이브 폴백 추가 후 **사용자 완주 → v5
  `mova_20260926_161748` 로컬 GGUF 변환·운영 서빙(09-27 새벽). 운영 회귀 23/23(Gemini 동률)·
  멀티턴 6/6(1건은 Gemini 503 재실행 PASS). v4 유지/v3 롤백 결정은 v5로 해소**(`[M]` 09-27).
  목표: 한 달 코랩 결제 기간(~10-22) 안에 Gemini 능가. 교사 비교(10행): 픽 정확도 동일,
  차이는 형식·안정성 → 기본 Gemini(막히면 유료 $0.9/1,000행), Claude Haiku는 비상구.
- ~~② "후보 N편 이상이면 0편 금지" 서빙 가드~~ **09-27 밤 완료**(폴백 어댑터가 빈 픽도 Gemini 재시도). "법정
  드라마 영화"는 Gemini도 0편 → 카탈로그 갭으로 재분류(단일턴 22/23의 1건).
  ~~③ v5 결과 반영~~(09-27 완료) ~~④ 분류기 "줄거리" 오라우팅 결정론 분기~~ **09-28 완료**(제목 있는
  줄거리 요청→evaluate, 폴백 경로용) ~~⑤ Gemini 503이 `HubRagError`→500으로 새는 경로~~ **09-28 완료**
  (평가 트랙 `_compose_reply`가 정량 요약으로 강등, `[M]` 09-28).
- **오케스트레이터 관찰 전제(09-28)**: `chat`은 `hit_count` 합산이라 `last_used_at`으로 봐야 하고, 최근
  7일 545건이 전부 하네스(user_id NULL) — **실사용 트래픽 0**. "한 주 관찰"은 하네스 재실행으로 대신하고
  실사용이 생기면 재개.
- 다음 지표 목표: 코랩 심판(v5 6.93 vs 8.86)과 운영 하네스가 두 회차 연속 반대로 갈림 — 내보내기 판단은
  운영 하네스 우선, 코랩 평가셋은 심판 루브릭·홀드아웃 구성 재검토 후보.
- ~~멀티턴 재학습 — 코랩 실행 대기~~ — **09-22 v2·v3 학습 완료, v3 운영 반영**
  (아래 "EXAONE 재학습" 절). 09-17 어댑터는 폐기.
- **학습 스크립트 미반영(의도적)**: `train_mova_lora.py`의 target_modules가 Llama식
  이라 EXAONE에선 q/k/v만 걸린다. 베이스 기본값 Qwen2.5-1.5B·구 데이터셋 경로·
  토큰 경계 수정도 미반영 — 코랩으로 학습하기로 해 손대지 않았다. 로컬 학습으로
  돌아가려면 먼저 고칠 것.
- ~~`rs_mine_queries.py:63` 테이블명 버그~~ — 09-22 수정(`chat`).
- ~~운영 `serve_gguf.py` `--cache-ram` 상한~~ — **09-22 `--cache-ram 1024` 적용·배포**
  (RSS 5.4GB→0.51GB). 테스트 서버는 `--cache-ram 0`으로 띄울 것.
- ~~배우 질의 picks 0 회귀(v3)~~ → **v4(09-22 밤) 서빙으로 회복**. 대신 `2000년대 초반
  한국 영화`·`법정 드라마 영화`가 후보 있는데 0편(같은 유형, 결정적). 21/23 동률.
  **v4 유지 vs v3 롤백은 사용자 결정 대기**. 근본 대책은 재학습 반복이 아니라 "후보 N편
  이상이면 0편 금지" 서빙 가드/하드 체크(`[M]` 09-22 ㉑).
- ~~응답 `intro` 미저장~~ — **09-22 밤 `chat.reply` 칼럼 구현**(alembic `20260922_0002`,
  LLM 원문 저장). **배포·검증 완료** — 운영 chat 609부터 reply 저장 실측(`[M]` 09-22 ⑲).
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

### EXAONE 재학습 — v3 운영 반영 완료, v4 데이터 준비 (2026-09-22)
- **v3(`mova_20260922_064437`) 운영 서빙 중** — 로컬 변환 GGUF
  `~/lora_adapters/gguf/mova_20260922_064437-Q5_K_M.gguf`, `RECOMMENDATION_BACKEND=lora`,
  lora 실패 시 Gemini 자동 폴백. 회귀 **21/23**(Gemini 23/23) — FAIL은 배우 질의 2건이
  카탈로그가 있는데도 picks 0(`v3_honest` 과잉 일반화). 상세 WORK_LOG_MOVA 09-22 ⑮.
- ~~v4 코랩 실행 대기~~ — **09-22 밤 v4 `mova_20260922_124254` 로컬 GGUF 변환·서빙**
  (21/23, 배우 회복·연도/법정 2건 회귀, `[M]` ㉑). 아래는 당시 준비 기록:
- **v4 데이터 완성(09-22 저녁)**: `chat_teacher_dataset_v4.jsonl`
  **895행**(rebuild 753 + 신규 142) 바탕화면 `mova/FT/mova-colab-v4/`, 노트북
  `VERSION_TAG="v4"`, 산출물 드라이브 `out/v4/`. 학습 후: GGUF 다운로드 →
  `LATEST_GGUF` 교체·`/reload` → `eval_chat_queries.py`(기준선 v3 21/23 · Gemini 23/23)
  — **배우 질의 2건(송강호·마동석)이 살아나는지**가 합격 기준.
- **후속(코드)**: ~~①~③~~ 09-22 저녁 완료 — `export_mova_gguf.py`가 `convert_exaone_gguf.py`
  경유 + peft 우회 내장 + 실경로 기본값, 격리 실행으로 운영 GGUF와 md5 동일 확인;
  venv 핀은 `_docs/lora-remote-gpu-ops.md` §1. ~~④ `chat`에 `intro` 저장 칼럼~~ — 09-22 밤
  `chat.reply`로 구현·배포·실측 완료(chat 609부터 저장).
- 페르소나 부여는 보류(v3 패배 사유에 톤 0건). GPU: lora-server 단독 2,652MB 실측 —
  4GB 데스크톱 서빙 가능하나 ollama 동거·학습·병합 불가.

#### (이전 기록 — 2026-09-17 준비 단계)
- 94건 → **376건 증강**(`datasets/augment_teacher_dataset.py`: 카탈로그 셔플 +
  Gemini 말투 패러프레이즈 2종, 개수 표현 필터). 정답 픽은 원본 유지.
- 코랩 노트북 `suvisdev/scripts/mova_exaone_colab.ipynb`(바탕화면
  `mova-colab/`에 데이터와 함께): 원본 단위 14건 홀드아웃 → 에폭별 평가 손실로
  최적 에폭 → 하드 체크 + Gemini 블라인드 심판(학생 vs Gemini·베이스) →
  전체 재학습 → 병합 → llama.cpp `304665f`로 GGUF Q5_K_M → 드라이브 저장.
  CPU 초소형 모델로 셀 로직 스모크 통과(EXAONE 실학습은 미검증).
- **09-17 저녁 코랩 결과 GGUF 변환·A/B 완료, 운영 미적용**:
  `~/lora_adapters/gguf/mova_20260917_124713-Q5_K_M.gguf`. 학습행 pass 85→92·80→92지만
  처음 보는 인사("ㅎㅇ"·"고마워요")에 영화 3편 추천하는 퇴행 → 적용 전 미학습 질의
  평가(`eval_chat_queries.py`) 필요. 상세 WORK_LOG_MOVA 09-17.
- **llama-server `--cache-ram` 기본 8GB**(09-17 RAM 고갈 원인): 운영 `serve_gguf.py`
  인자에 상한 추가 여부 결정 대기.
- **남은 것(원래 계획)**: 사용자가 코랩 실행 → GGUF 내려받기 → 노트북 `LATEST_GGUF`
  교체·`/reload` → `eval_chat_queries.py` 비교(**09-17 기준선 23/23 PASS**,
  09-09 어댑터). 절차는 노트북 8번 셀.

### gildle 앱 출시·경로 알고리즘 (2026-09-27 갱신)
- 완료(09-22): walks API·브이월드 건물 그늘 13슬롯(모델 B 적용)·합성 검증 하네스·자체 다익스트라/A*·
  시간 의존 그늘·제약 최단경로·루프 `/gildle/loops`. 발급 3종(네이버 지도·google-services·FCM 키)·
  릴리스 서명 키·디버그 APK. 설계 `apps/gildle/_docs/GILDLE_ROUTING_ALGORITHM.md`.
- **완료(09-27, `[G]` 09-27)**: ① Flutter **지도 화면**(susu `features/gildle/` — 출발·도착 탭,
  계절 모드, 그늘 색 폴리라인, 루프, 현재 위치) ② susu를 gildle 앱으로 정리(mova·media·스톱워치 삭제,
  gildle 테마, 위치 권한) ③ `/routes`가 `/navigate`와 같은 여름 그늘 탐색·응답(`length_m` 포함) +
  **좌표 방향 버그 수정** ④ 수관 데이터(숲·공원·나무열 OSM 6,457 피처)로 tree_score>0 **4.4%→19.3%**,
  프로덕션 hostPath에 적용됨 ⑥ 모드별 A* 배율(겨울 방문 노드 41%→19%). 여름 가중치는
  `max(건물 그늘, 수관)`으로 변경.
- 09-27 백엔드 코드(③·가중치 규칙·⑥) **프로덕션 배포 완료**(같은 날 오후).
- **완료(09-27 오후, `[G]` 09-27)**: 산책 중(포그라운드 추적·저장)·기록·상세·내 정보 3탭, access
  토큰 자동 갱신(401→refresh→재시도), `push_tokens` 테이블·API(`20260927_0001`), `app/version`, 앱 FCM
  토큰 등록, 디버그 APK(`바탕화면/길들/gildle-debug-20260927.apk`).
- **완료(09-27 저녁)**: `susu`→`gildle` 개명(폴더·패키지·문서), 런처 아이콘(adaptive)·정적 스플래시,
  graph-edges 이중 캐시 제거(파드 RSS −220MB), 릴리스 AAB `길들/gildle-release-20260927.aab`.
  `scored_edges` DB 이전은 **보류**(RSS 안 줄고 워커 1개 — 근거 `[G]` 09-27 저녁).
- **09-28 웹 지도를 네이버 SDK로 재작성, 앱 지도 화면과 동일 구성**(`[G]` 09-28): 탭 경로·계절 모드·
  현재 위치·루프·산책 추적 저장. 웹 전용 그래프 시각화(레이어 토글·화면 간선)는 삭제, 장소 검색만 유지.
  **사용자 몫: Vercel에 `NEXT_PUBLIC_NAVER_MAP_CLIENT_ID` 등록 + 재배포 후 실화면 검증.** 후속: 웹 산책
  기록 목록 화면(API `GET /walks`는 있음).
- 남은 것: **실기기에서 APK 설치·확인**(지도 인증·위치 권한·산책 저장·아이콘) → 콘솔 인증 후 스토어
  등록정보(스크린샷·설명에 서울 한정·콘텐츠 등급·데이터 보안 양식) + `GILDLE_APP_STORE_URL` →
  FCM 발송(보낼 알림 결정 후) → ⑤ 그늘 실측(사진 5곳) → 모델 A(walks 쌓인 뒤) · 모델 D(DEM).
  **사용자 몫은 Play Console 인증 대기 — 09-28 기준 미승인, 최소 한 달 예상(그동안 출시 항목 보류).** 준비 상태 표: `gildle/_docs/GILDLE_APP_RELEASE_PLAN.md`.

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
- ~~🟡 mova `POST /import/tmdb·/kofic` 무인증 쓰기~~ **완료(09-11 수정, 09-28 파드
  안 `require_admin` 부착 확인)**: `require_admin` 부착 + 401/200 테스트 4건
  (`test_import_router_auth.py`). 프론트 호출처 없음(수동/스케줄러 전용)이라
  토큰 전달 배선 불요. ~~🟡 media 오류 원문 노출·크기검사 전 전체 적재~~
  **완료(09-11 수정, 09-17 f745447 빌드에 포함)**: 502 detail 일반 문구화(원문은 로그),
  업로드는 상한+1바이트까지만 read.
- **🟡(잔여)**: access TTL 7일+웹 리프레시 미사용 · 토큰 localStorage(httpOnly
  쿠키 부재) — 인증 구조 변경이라 별도 설계 필요 · pgadmin admin/admin(replicas:0).
- **09-11 전체 코드 리뷰 + 후속 수정 ①~⑤ 완료(09-17 이후 빌드로 배포됨, 09-28 확인)** — 리뷰 결과·처리
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
- ~~라우터 exaone3.5:2.4b 전환 코드 완료, 배포 대기(09-17)~~ **배포됨(09-28 파드 확인)**: qwen2.5:1.5b 404→Gemini
  폴백 상태를 EXAONE 2.4B(온도 0)로 교체, Gemini 일치 90%. 배포 후 확인: 로그에
  `FallbackHubLlmAdapter` 404 경고 소멸 + eval_chat_queries 23/23. 불일치(제목+어때 →
  recommend)는 라우터 LoRA 학습 후보.
- ~~exaone3.5:7.8b 온디맨드 전환 코드 완료, 배포 대기(09-17 사용자 결정 1안)~~ **배포됨(09-28 파드 확인)**: 7.8B 상주 시
  bge-m3·2.4B가 밀려 재로드(최대 9s) 실측 → 기동 워밍업 제거(`get_faker_orchestrator`·
  `warmup` 함께 삭제), PDF 요약만 `keep_alive="0"`(요약 직후 언로드, 실측 확인). 7.8B
  추가 학습은 불요 판단 — 전용 출력 계약 없는 범용 요약만 담당.
- **`train_mova_lora.py` LoRA 대상층이 EXAONE에서 q/k/v만 매칭**(09-17 발견) — 코랩
  노트북은 수정됨. 로컬 학습 경로를 다시 쓸 일이 있으면 같은 수정 필요.
- **백엔드 이미지 슬림화 — CPU 전용 torch로 전환 — 09-28 착수·배포(`[P]` 09-28, 결과 수치는 워크로그)**.
  Dockerfile에서 requirements를 sed 치환해 설치(requirements.txt는 데스크톱용 cu126 유지). **결과: 14.9GB→6.83GB,
  빌드 6분, 하네스·스모크 전부 정상.** 아래는 계획 기록:
  노트북 backend 파드엔 GPU 런타임이 없어(`k8s/backend.yaml`에 nvidia 설정
  없음) 파드 안 `torch.cuda.is_available()`이 **False로 실측**됐는데, 이미지는
  `torch==2.12.1+cu126`·torchaudio·torchvision cu126 + bitsandbytes로 pip
  레이어만 **9.01GB, 총 14.6GB**. 이 때문에 requirements가 바뀔 때마다 전체
  빌드(pip 4~5분 + 14GB export 3분, dockerd 단일 코어 100%)로 노트북 팬이
  오래 돈다(08-31 12m43s · 09-03 9m14s · 09-11 7m34s 취소). 계획:
  ① `--extra-index-url`을 `whl/cpu`로, torch 3종을 `+cpu` 빌드로 교체
  ② bitsandbytes는 CUDA 전용이라 pod에서 원래 못 쓰던 것 — echo_sentiment
  어댑터(`device_map={"": 0}`, 4bit)가 pod에서 호출되는 경로가 있는지 먼저
  확인해 없으면 requirements에서 제거, 있으면 CPU 폴백 설계
  ③ convnext·sentinel 어댑터는 `cuda→cpu` 자동 폴백이라 영향 없음
  ④ 데스크톱(학습·GPU 테스트)은 `.venv`로 돌리므로 이미지 변경과 무관 —
  단 `pytest -m gpu`가 이미지가 아닌 venv 기준임을 재확인
  ⑤ 효과 예상: 이미지 수 GB대, export 수십 초. 검증: 빌드 시간·`docker
  history` 레이어 크기 · 파드 기동 후 mova chat·gildle·ontology 추론 엔드포인트
  실측. **노트북 상태 좋을 때(학습 없는 날) 착수** — 전체 재빌드가 한 번 더
  필요하므로.
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
  도커 backend·auth·nginx는 stop 상태로 롤백용 보존(`down` 금지). **09-28 발견: nginx가
  `restart=always`라 재부팅마다 되살아나 크래시루프** — `docker update --restart=no nginx && docker stop
  nginx` 사용자 실행 필요(하네스 차단). 배포는
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
