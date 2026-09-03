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
- `api.`/`auth.suvisdev.cloud`는 이제 **노트북(teagy)** compose(nginx·
  backend·auth·db·redis·cloudflared)가 서빙. 터널 `suvisdev.cloud`의
  커넥터는 노트북 단독. 프로덕션 DB는 EC2 덤프(09-03) 복원본.
- **남은 것**: ① 하루 안정 확인 후 EC2 개인 스택 `down`·prune·Elastic IP·
  `t3.small` 축소 ② 노트북 lora-server 어댑터 동기화(현재 08-25 AWQ) ③
  브라우저 실사용 검증(카카오 로그인·채팅·gildle) ④ 루트 CLAUDE.md의
  "EC2=Gemini 폴백" 서술 갱신 필요. 상세: SUBDOMAIN_MIGRATION_PLAN.md.

### 서브도메인 이사 — seuk(팀 프로젝트)만 (2026-09-03 결정 변경)
- **개인 앱(mova·gildle)은 이사 안 함** — 서빙 실익 없음(세션 분리·OAuth
  복귀 갭·중복 URL). 리라이트 `0bef4f3` 되돌림(저녁 세션, 푸시 대기).
- **GitHub 이전 완료(09-03 저녁)**: 새 조직 `Seuk-Team` + `Seuk-Team/Arda`
  mirror(브랜치 13/13 일치) + main 보호. 남은 것: 팀원 remote 교체·구 저장소
  Archive·Vercel 연결·Secrets·두 번째 owner, 그리고 **팀 인프라 이전**(팀 Vercel
  도메인+CNAME, 새 AWS 계정). **전체 계획·순서·검증 기준:
  `_docs/SUBDOMAIN_MIGRATION_PLAN.md`**, 실행 체크리스트
  `_docs/ARDA_AWS_DEPLOY_GUIDE.md`(09-04 학원 세션용).

---

## 다음 / 남은 작업 (백로그)

### 우선순위 방향 (2026-09-02, 사용자 결정)
**당분간 신규 기능보다 mova 채팅 품질 향상에 주력한다** — 실사용 오답·
오분류·무관 추천 감소가 우선, 새 트랙·새 기능은 보류. 로그 추적 → 근본
원인 → 결정론 가드+테스트 패턴으로 진행. 회귀 하네스
(`scripts/eval_chat_queries.py`, 23질의)는 상시 사용.

### mova 채팅 품질 잔여
- **"정치 스릴러 영화" 무관 픽**(캐시트럭·미션임파서블) — 정치 태그 42건
  실재하는데 '스릴러' 토큰 물량이 압도하는 것으로 추정. 트레이스로 후보
  조립(교집합 우선 발동 여부) 규명 필요. 유럽 로맨스·뉴욕 배경은 09-03
  태그 확장으로 교정 완료.
- **의도 추출 Gemini 429 재시도 지연** — 쿼터 압박 시 SDK 재시도로
  3.7~5s까지 출렁(평시 0.9s). 옵션: 재시도 상한/타임아웃 단축 or 결정론
  우선. E2E 절대값은 쿼터 회복 후 재실측이 공정.
- **취향 재정렬 후속(08-18 신규)**: alpha 별점 결합 튜닝(현재 순수 코사인),
  후보 window 확대(taste vector 있는 유저에게 limit 16 이상 — 프롬프트
  토큰·Gemini 요금 트레이드오프).
- **엔티티 매칭(편집거리·초성·수사 변환) — 보류**: 프로덕션 로그 오타 질의
  0건(08-26, 09-03 재확인). 재검토 트리거: ① zero-rec 재실측에서 제목/배우
  오타·음차 질의가 쌓일 때 ② 검색창·초성 게임 판정 등 UX 직접 개선 지점
  ③ 채팅 제목 직접 언급 증가. 도입 시 ATS 순수 Python 구현 복사(의존 금지)
  → `intent_extraction` 결정론 경로.

### LoRA 재학습 배치 큐 (2026-09-03 사용자 결정 — 매 변경마다 학습 금지)
- **원칙**: 상류 변경(태그 사전·후보 조립·프롬프트 입력)은 계속 쌓되,
  재학습은 진짜 트리거(출력 계약 변경 / 생성 단계 체계적 실패 / 데이터셋
  유의미 증분)가 모였을 때 **한 번에**: 데이터셋 재생성 → 학습 → GGUF
  변환(`export_mova_gguf.py`) → /reload.
- **현재 큐**: ① 09-03 태그 확장(뉴욕·유럽·직장·정치)으로 살아날 교사 예제
  +5~10건 ② hook 길이 다이어트 120→80자(출력 계약 변경이라 재학습 필수,
  단독 실행 수지 안 맞아 대기) ③ 이후 사전 확장분. 잔여 교사 스킵 17건
  (배우명·형사물 등)은 실서비스 정상이라 태그 사전 확장 여지로만 남김.

### EC2 전체 재빌드 불가 (2026-09-02 실측)
- pip 레이어 캐시 소실 상태에서 torch 스택 재설치는 피크 ~15G+라 30GB
  디스크에 구조적으로 안 들어감(`[Errno 28]`). 현재는 requirements 불변일 때
  **파생 빌드**(`FROM suvisdev-app:latest` + `COPY . .`)로만 배포.
- 파생 빌드 COPY 레이어가 배포마다 누적돼 이미지 9.78→10.3GB↑(09-03) —
  결정 압력 증가. 선택지: ① EBS 증설 ② 데스크톱 로컬 빌드 후
  `docker save | ssh docker load`. **결정 필요.**
- auth 이미지 드리프트는 auto-deploy 기본값(backend만)이 원인 — 재빌드
  배포 시 `./auto-deploy.sh backend auth`로 둘 다 지정할 것.

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
- CLI 개선: 건당 모델 로드/해제라 41건 ≈ 30분 — **모델 1회 로드 배치화**하면
  2~3분. 반복 루틴이 되면 우선 처리.

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

### 구조·인프라 백로그 (착수 전, 우선순위 낮음)
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
