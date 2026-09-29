# MOVA — 프로젝트 요약

## 한줄 소개

MOVA는 AI 기반 영화 추천 채팅 + 리뷰·랭킹·미니게임을 제공하는 풀스택 웹 서비스다.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 | FastAPI, SQLAlchemy 2.0 (async), PostgreSQL + pgvector, Alembic |
| AI/ML | Gemini API (추천·임베딩·OCR), EXAONE LoRA (로컬 GPU 추론), Ollama |
| 검색 | pgvector HNSW 인덱스, 코사인 유사도 기반 시맨틱 검색 |
| 프론트엔드 | Next.js 15 (App Router, Server Components), Tailwind CSS v4 |
| 모바일 | Flutter (Dio + Riverpod + go_router) |
| 인프라 | AWS EC2 (m7i-flex.large), Docker Compose, Cloudflare Tunnel, S3 |
| 코드 품질 | ruff, mypy (strict), import-linter, pytest |

---

## 아키텍처 하이라이트

### Hexagonal Clean Architecture + 모듈러 모놀리식

Titanic 앱을 기준선(baseline)으로 Ports & Adapters 패턴을 확립하고, 동일한 레이어 규칙을 Mova·Viewer·Gildle 등 12개 앱으로 확장했다. 스타 토폴로지(Hub-and-Spoke)로 앱 간 직접 import를 차단하고, import-linter가 커밋 시점에 위반을 자동 검출한다. 새로운 DB나 LLM 어댑터가 필요할 때 Outbound Adapter만 교체하면 Use Case 코드 변경 없이 환경을 전환할 수 있다.

### 하이브리드 GPU 아키텍처

로컬 노트북(RTX 4060, EXAONE-2.4B AWQ LoRA)과 AWS EC2(GPU 없음, Gemini API)를 동일한 `RecommendationPort` 인터페이스 뒤에 배치했다. EC2는 Cloudflare Tunnel로 노트북의 LoRA 서버를 호출하고, 터널 장애 시 `RECOMMENDATION_BACKEND=gemini`로 전환해 수동 폴백한다(전환 왕복 8초 실측). GPU 인스턴스 없이 월 $77(m7i-flex.large) 비용으로 LLM 추천을 운영하는 구조다.

### 리뷰 기반 개인화 추천

사용자 리뷰의 별점 가중 평균 임베딩으로 취향 벡터(taste vector)를 생성하고, 추천 후보의 `movies.embedding`과 코사인 유사도로 재정렬한다. Gemini `text-embedding-004` 768d 공간에서 movies·reviews·taste vectors 세 벡터가 정합하는 것을 사전 진단으로 확인한 뒤 구현했다. 이 기능으로 MOVA는 "TMDB 데이터를 보여주는 카탈로그 브라우저"에서 "개인화 추천 엔진"으로 전환됐다.

---

## 핵심 문제 해결 사례

### 1. 카탈로그 확장이 답이 아니었던 경험

**문제:** 추천 실패 6건(골든셋 15개 중)을 카탈로그 부족으로 가정하고, 1055→2014편으로 2배 확장.

**원인:** 재검증 결과 실패 6건이 단 1건도 안 풀림. `search_tag_catalog()`가 배우 이름을 전혀 검색하지 않고 장르/무드 태그만 조회하며, top-12 rating 컷까지 적용해 후보 자체가 구조적으로 차단돼 있었다.

**해결:** 데이터로 증명한 뒤 방향을 전환. 배우 이름 매칭 신설, 태그+배우 교집합 우선 + 합집합 완화 + 인기작 폴백 3단계 후보 생성으로 근본 수정. 동시에 Grounded Prompting(프롬프트가 카탈로그 movie_id를 강제 응답)으로 LLM 환각을 차단.

**결과:** 골든셋 통과 6→9건. "키아누 리브스 액션"·"송강호 스릴러"가 배우 매칭으로 정당하게 통과. 실사용 신고 버그("reply는 있는데 카드 0개")도 인기작 폴백으로 해소.

### 2. IDOR 5건 전수 조사·수정

**문제:** mova 리뷰 API 보안 하드닝 중 `user_id`를 요청 바디에서 그대로 신뢰하는 패턴이 반복되는 걸 발견.

**원인:** 라우터 60개를 전수 조사한 결과 동일 유형 5건 발견 — `/mova/mypage/{user_id}`, `/viewer/profile/{user_id}`(이메일 노출), `/mova/watchlist/*`(읽기+쓰기), `PATCH /mova/picks/{pick_id}/feedback`, `POST /mova/chat`(바디 user_id).

**해결:** 모든 엔드포인트에서 `user_id`를 JWT 클레임에서만 추출하도록 수정. 비로그인이 의도된 챗은 `optional_user` 가드를 신설해 기능 유지. `.claude/rules/security/auth.md`에 참고 구현 2종과 점검 체크리스트 5항목을 코드화.

**결과:** 프로덕션에서 401/403 전환 확인. 이후 신규 엔드포인트는 auth.md 규칙으로 사전 방지.

### 3. 멀티턴 대화 필터 오염

**문제:** 1턴 "액션 영화" → 2턴 "여행 영화"에서 "새 후보 없음" 반환.

**원인:** `IntentExtractionService.extract()`에서 이전 턴을 포함한 `composed_text`를 결정론적 경로(search_filters, keywords)와 `refined_query` RAG 검색 쿼리에 모두 흘려 이전 턴 장르가 잔존.

**해결:** 2단계 수정 — ① search_filters/keywords를 현재 턴(`text`)에서만 유도, ② `refined_query`도 결정론적 결과에서 가져오도록 변경. `composed_text`는 Gemini 프롬프트에만 사용.

**결과:** 주제 전환 시 이전 턴 필터 완전 분리. 회귀 테스트 추가.

### 4. intent extraction 결합 결함

**문제:** "봉준호 감독 영화 추천해줘" 같은 쿼리에서 감독/배우 인식 실패.

**원인:** 골든셋 15개 체계적 검증으로 두 가지가 결합된 결함 발견 — ① 정규식이 배우/감독 이름을 인식 못 함, ② `_has_hard_signal()`이 장르 단독으로 True를 반환해 Gemini 폴백을 스킵. Gemini 프롬프트에 배우 인식 예시가 학습돼 있어 폴백만 태우면 해결되는 구조.

**해결:** `_has_hard_signal()`을 완화해 장르 단독으론 Gemini 스킵하지 않도록 수정. 트레이드오프(무료 티어 분당 15요청 소모 증가)를 명시한 뒤 적용.

**결과:** 테스트 4→7건, 골든셋 해당 케이스 통과 전환.

---

## 진행 중 / v2 파이프라인

### 뉴스 기사 기반 AI 리뷰 자동 생성

harvester가 kobis(박스오피스)·google_news(개봉/넷플릭스 신작 RSS)·kowiki 등 5개 소스를 일일 크롤링하고, `ScrapedRecord`로 정규화한 뒤 DB에 저장한다. 수집된 기사를 영화별로 매칭한 뒤 LLM(Gemini/EXAONE)이 리뷰 톤으로 재작성하는 파이프라인을 구축 중이다. 스케줄러 기반 일일 수집(5개 소스, 주기 1일)으로 운영하며, 향후 감정분석 연계로 자동 별점 생성까지 확장할 계획이다.

### 멀티턴 주제 전환 감지

현재 결정론적 경로로 이전 턴 필터를 차단했지만, 사용자가 의도적으로 이전 맥락을 이어가는 케이스("그 감독의 다른 영화는?")를 구분하는 로직이 없다.

### Aspect-based 감정분석 → 취향 매칭

리뷰를 단일 별점이 아니라 연기·스토리·영상미 축으로 분리해 취향 벡터 정밀도를 높이고, 추천 재정렬에 축별 가중치를 반영할 계획이다.

### Auth 게이트웨이 SSO 완성

Google/Kakao/Naver OAuth + 이메일 로그인이 현재 별개 계정으로 생성되는데, 동일 이메일 기준으로 통합하는 작업이 남아 있다.

---

## 수치 요약

| 지표 | 수치 |
|------|------|
| 영화 카탈로그 | 2,014편 (TMDB + KOFIC) |
| 배우/캐릭터 | 11,945 / 19,348 |
| 백엔드 앱 | 12개 (모듈러 모놀리식) |
| Interactor (Use Case) | 24개 (mova 단독) |
| 테스트 | 547개 (88 파일, mova 218개) |
| Alembic 마이그레이션 | 28개 |
| ORM 테이블 | 36개 |
| 커밋 | 504+ |
