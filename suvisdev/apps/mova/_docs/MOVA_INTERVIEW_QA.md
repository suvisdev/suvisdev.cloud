# MOVA — 면접 예상 질문 & 답변 노트

---

## Q1. 왜 hexagonal 아키텍처를 선택했나?

**Situation:** 영화 추천 서비스를 처음 설계할 때, LLM 어댑터(Gemini/EXAONE/Ollama)와 DB 어댑터를 자주 교체해야 할 것이 예상됐다.

**Task:** 어댑터가 바뀌어도 비즈니스 로직(Use Case)이 영향받지 않는 구조가 필요했다.

**Action:** Titanic 앱을 기준선으로 Ports & Adapters 패턴을 먼저 구현하고, 동일한 레이어 규칙(Router → Input Port → Interactor → Output Port → PgRepository)을 Mova·Viewer 등 12개 앱에 적용했다. import-linter로 스포크 간 직접 import를 커밋 시점에 차단하는 Star Topology도 강제했다.

**Result:** 실제로 EC2(Gemini)↔노트북(LoRA) 전환 시 `RECOMMENDATION_BACKEND` 환경변수 하나만 바꾸면 됐다. 새 앱(Gildle)을 추가할 때도 기존 패턴을 그대로 복제해 빠르게 확장할 수 있었다.

---

## Q2. 가장 어려웠던 기술적 문제는?

**Situation:** 추천 실패 6건을 해결하기 위해 카탈로그를 1055→2014편으로 2배 확장했다.

**Task:** 확장 후 골든셋 15개를 재검증해야 했다.

**Action:** 재검증 결과 실패 6건이 단 1건도 안 풀렸다. 원인을 추적하니 `search_tag_catalog()`가 배우 이름을 전혀 검색하지 않고 장르/무드 태그만 조회하며, top-12 rating 컷까지 있어 카탈로그 크기와 무관하게 구조적으로 차단돼 있었다. "카탈로그가 부족해서"라는 가설을 데이터로 기각한 뒤, 배우 매칭 신설 + 3단계 후보 완화 + Grounded Prompting으로 방향을 전환했다.

**Result:** 골든셋 통과 6→9건, 실사용 신고 버그도 해소. "직감이 아니라 데이터로 가설을 검증하고 방향을 바꾸는 것"이 가장 어렵고 중요한 판단이었다.

---

## Q3. 코드 품질은 어떻게 관리했나?

정적 분석 3종(ruff lint/format, mypy strict, import-linter)을 pre-commit 훅으로 커밋 시점에 강제한다. pytest 547개로 정책·로직을 검증하고, GPU/Ollama 의존 테스트는 마커로 분리해 CI 환경에서도 깨지지 않게 했다. 추천 품질은 골든셋 15개를 수동 구축해 코드 변경마다 "문제→원인→해결→결과" 구조로 판정하고 문서에 비교표를 남겼다.

---

## Q4. 추천 알고리즘을 설명해달라

4단계 파이프라인이다. (1) Intent Extraction — 사용자 질의에서 장르·배우·무드 키워드를 결정론적 정규식으로 먼저 추출하고, 부족하면 Gemini에 폴백. (2) 후보 생성 — `search_tag_catalog()`가 태그+배우 교집합 → 합집합 완화 → 인기작 폴백 3단계로 후보 16편을 추린다. (3) Grounded Prompting — 후보 movie_id를 프롬프트에 넣어 Gemini가 카탈로그에 있는 영화만 추천하게 강제. (4) Taste Vector 재정렬 — 사용자 리뷰 별점 가중 평균 임베딩(768d)과 영화 임베딩의 코사인 유사도로 최종 순위를 조정.

---

## Q5. 보안 이슈를 어떻게 발견/해결했나?

**Situation:** 리뷰 API 보안 하드닝 중 `user_id`를 요청 바디에서 그대로 신뢰하는 패턴이 반복되는 걸 발견했다.

**Action:** 라우터 60개를 전수 조사해 동일 유형 IDOR 5건을 찾았다. 가장 심각한 건 `/mova/watchlist/*` — 남의 찜 목록을 읽고 쓰고 삭제할 수 있었다. `/viewer/profile/{user_id}`는 이메일이 노출됐다. 전부 JWT 클레임에서만 신원을 추출하도록 수정하고, `.claude/rules/security/auth.md`에 체크리스트 5항목을 코드화해 이후 엔드포인트 추가 시 사전 점검을 강제했다.

**Result:** 프로덕션에서 401/403 전환 확인. 별도로 dispatch 엔드포인트 감사에서 공개 데모 페이지가 실제 주소록 DB에 쓰기 가능했던 건도 발견·차단했다.

---

## Q6. 팀 협업 경험은?

SEUK 해커톤에서 팀 프로젝트 경험이 있다. MOVA는 1인 풀스택 프로젝트지만, Claude Code를 적극 활용해 체계적으로 진행했다. `.claude/rules/`에 경로별 코딩 규칙을 설정하고, skills(systematic-debugging, verification-before-completion, writing-plans)로 디버깅·검증·계획 수립 프로세스를 표준화했다. 작업마다 WORK_LOG에 "무엇을 왜 했는지, 어디서 막혔는지"를 기록해 컨텍스트 유실 없이 장기 프로젝트를 진행했다.

---

## Q7. 성능 최적화 경험은?

**Situation:** pgvector HNSW 인덱스를 생성했는데 시맨틱 검색에서 자동 선택되지 않았다.

**Task:** PostgreSQL 플래너가 HNSW scan보다 sequential scan의 cost를 낮게 잡는 문제를 해결해야 했다.

**Action:** `EXPLAIN ANALYZE`로 확인한 결과 HNSW cost가 seq보다 높게 잡히고 있었다. 근본 원인은 플래너의 벡터 인덱스 cost 추정이 보수적인 것이었다. 세션 힌트 `SET enable_seqscan = off`로 강제 전환 후 벤치마크를 돌렸다.

**Result:** 6.8배 성능 개선을 실측. 이 결과를 근거로 세션 힌트 적용을 정당화했다.

---

## Q8. 실패에서 배운 것은?

세 가지를 꼽겠다. 첫째, 카탈로그 확장이 답이 아니었던 경험 — 2배로 늘렸는데 추천 실패가 1건도 안 풀려서, 병목이 데이터 양이 아니라 후보 생성 로직임을 데이터로 증명한 뒤 방향을 전환했다. 둘째, 문서 최신성 갭 — PROGRESS.md에 "미완료"로 적힌 3개 항목이 실제로는 이미 완료돼 있었다. 문서와 실제 상태의 괴리를 주기적으로 검증해야 한다는 걸 배웠다. 셋째, `.env` 배포 절차 누락 — `.env.example`에 주석까지 달아놨지만 실제 `.env`(git 미추적)에 반영을 빠뜨려 `RECOMMENDATION_BACKEND`가 EC2에서 한 번도 설정된 적 없었다.

---

## Q9. 왜 로컬 GPU + 클라우드 하이브리드?

**비용:** GPU 인스턴스(g4dn.xlarge) 월 $160+ vs m7i-flex.large 월 $77. 집에 이미 RTX 4060이 있으니 무료 GPU를 쓰고, EC2는 CPU만 돌리는 게 합리적이었다.

**설계:** `RecommendationPort` ABC 뒤에 `LoraServerClient`와 `GeminiRecommendationAdapter`를 둬서, 환경변수 하나로 전환된다. Cloudflare Tunnel이 집 GPU를 EC2에 노출하고, 터널이 끊기면 Gemini로 수동 폴백(8초). 이 구조 자체가 hexagonal의 어댑터 교체를 실증하는 사례다.

**트레이드오프:** 자동 폴백은 의도적으로 안 넣었다 — 어떤 모델이 답했는지 불투명해지는 것을 방지하기 위해 수동 전환을 유지했다.

---

## Q10. 다음에 개선하고 싶은 것은?

세 가지를 계획하고 있다. (1) 멀티턴 주제 전환 고도화 — 현재는 결정론적 경로로 이전 턴 필터를 차단했지만, 사용자가 의도적으로 이전 맥락을 이어가는 케이스("그 감독의 다른 영화는?")를 구분하는 로직이 없다. (2) Aspect-based 감정분석 — 리뷰를 단일 별점이 아니라 연기·스토리·영상미 축으로 분리해 취향 벡터 정밀도를 높이고 싶다. (3) Auth SSO 완성 — 현재 Google/Kakao/Naver OAuth + 이메일 로그인이 별개 계정으로 생성되는데, 동일 이메일 기준으로 통합하는 작업이 남아 있다.

---

## Q11. 데이터 수집은 어떻게 했나?

TMDB API(`/discover/movie`, `/movie/popular`)와 KOFIC API(`searchMovieList`)를 사용한다. `scripts/bulk_import_movies.py` CLI가 `--source tmdb_popular|tmdb_discover|kofic`, `--pages`, `--start-page` 옵션으로 배치 수집을 지원하고, 영화당 upsert → credits 백필(배우·감독·캐릭터) → hub_knowledge 임베딩 순으로 처리한다. 단계별 실패는 해당 영화만 스킵하고 `session.rollback()`으로 격리한다. 실제 배치에서 `succeeded=1960, failed=0`을 달성했고, credits 백필 실패 13편은 `characters.character_name` VARCHAR(50) truncation 버그가 원인이었는데, TEXT로 마이그레이션 후 재실행해 100% 복구했다.

---

## Q12. 데이터 수집 파이프라인은 어떻게 구성했나?

**Situation:** 추천 품질 향상을 위해 영화 관련 최신 뉴스·정보를 자동으로 수집하고, 이를 기반으로 AI 리뷰를 생성하는 파이프라인이 필요했다.

**Task:** 다양한 소스(박스오피스·뉴스·위키)에서 데이터를 안정적으로 크롤링하고, 영화별로 매칭한 뒤 LLM이 리뷰 톤으로 재작성하는 자동화 구조를 설계해야 했다.

**Action:** harvester가 kobis(박스오피스)·google_news(개봉/넷플릭스 신작 RSS)·kowiki 등 5개 소스를 일일 크롤링하고, `ScrapedRecord`로 정규화한 뒤 DB에 저장한다. 수집된 기사를 영화별로 매칭한 뒤 LLM(Gemini/EXAONE)이 리뷰 톤으로 재작성하는 파이프라인을 구축 중이다. 스케줄러 기반 일일 수집(5개 소스, 주기 1일)으로 운영한다.

**Result:** 크롤링·정규화·DB 저장까지는 동작하며, LLM 리뷰 생성과 감정분석 연계 자동 별점 생성은 구현 진행 중이다.

---

## Q13. 테스트 전략을 설명해달라

3계층으로 나눈다. (1) 도메인 — frozen dataclass 불변성, 동등성, 값 범위를 검증한다. (2) 인터랙터 — Output Port를 구현한 Fake(ABC 상속)로 정책을 검증한다. 임계값 판정, 게이트 통과·반려, 저장 호출 여부가 대상이다. Fake가 실제 포트 ABC를 상속하므로 인터페이스가 바뀌면 테스트가 먼저 깨진다. (3) 어댑터 통합 — 실제 추론이나 실 DB가 필요한 테스트는 `@pytest.mark.gpu`, `@pytest.mark.ollama` 마커로 분리해 마커 없는 테스트는 아무 환경에서나 즉시 통과한다. 현재 547개, mova 단독 218개.
