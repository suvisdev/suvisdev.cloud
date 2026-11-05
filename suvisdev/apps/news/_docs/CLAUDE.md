# news 앱 — news.suvisdev.cloud (2026-11-05)

뉴스를 모아 **검색어 탭**과 **최신 뉴스 탭**으로 보여 주고, AI가 만든 기사에는 **숨기지 않고 배지**를 단다.
판정 기준의 원천은 하네스 저장소 밖 폴더(`Desktop\뉴스\newsdesk`)의 `news-ai-filter` 스킬 `references/rubric.md` 다.

## 원칙

- **원문 페이지는 가져오지 않는다.** 검색 API·RSS 가 직접 준 것(제목·요약·링크·날짜·작성자, 일부 매체의 `content:encoded` 본문)만 쓴다.
  저장소의 기존 저작권 원칙(`ontology/.../google_news_scraper.py`, `mova/.../editor_reviews_scheduler.py`)과 같다.
- **화면·API 에 본문을 내보내지 않는다.** `ArticleSchema` 에는 제목·요약·원문 링크·배지만 있다.
- **배지는 신호로만 말한다.** `ai_disclosed`(매체가 AI 작성을 밝힘) → "AI 작성", `ai_suspected`(규칙·2차 판정 추정) → "AI 생성 의심",
  누르면 `reasons_ko`. "가짜·허위" 같은 단정은 쓰지 않는다. 사실 여부는 판정하지 않는다.
- **`domain/ai_filter/` 는 newsdesk 하네스 `scripts/ai_filter/` 와 같은 파일이다.** 표준 라이브러리만 쓴다(`.importlinter` news-domain-purity).
  기준을 바꾸면 rubric → `thresholds.json` → `signals.py` 순서로 고치고 `harness_version` 을 올린다. 버전이 바뀌면 다음 수집 주기에 그 주기 기사부터 다시 판정된다.
- **수집 스케줄러는 노트북에서만** (`ENABLE_NEWS_SCHEDULER=true`, 기본 꺼짐). 꺼져 있어도 `POST /api/v1/news/admin/collect` 로 한 주기를 돌릴 수 있다.

## 흐름

```text
스케줄러(30분) 또는 POST /admin/collect
 → NewsCollectInteractor
     ├ 검색어 탭: NaverNewsSearchClient(키 없으면 건너뜀) → domain.relevance 로 관련 기사만
     ├ 최신 뉴스: RssFeedReader × latest_feeds.json(13곳)
     ├ canonical_url 로 중복 제거(검색·RSS 둘 다 걸리면 RSS 쪽을 남김)
     ├ NewsPgRepository.save_articles / link_topic_articles
     └ 현재 하네스 버전 rules 판정이 없는 기사만 classify(mode C, 스레드) → save_verdicts
GET /topics · /topics/{id}/articles · /latest → 배지 = llm 판정이 있으면 llm, 없으면 rules
```

## ERD (alembic `20261105_0001`)

| 테이블 | 열 | 비고 |
|---|---|---|
| `news_topics` | id · query(UQ) · label · is_public · active · created_at | 운영자 검색어 = 탭 |
| `news_articles` | id · canonical_url(UQ) · link · source_domain · source_name · title · summary · body · author · origin(search/feed) · published_at · sort_at · fetched_at | body 는 RSS 가 준 본문만, 내보내지 않음 |
| `news_topic_articles` | topic_id(FK, PK) · article_id(FK, PK) · relevance · matched_at | |
| `news_verdicts` | id · article_id(FK) · layer(rules/llm) · harness_version · verdict(normal/pending/ai) · badge · reasons_ko(JSONB) · signals(JSONB) · created_at | UQ(article_id, layer) |

## API (`/api/v1/news`)

| 메서드 | 경로 | 인증 |
|---|---|---|
| GET | `/topics` | 없음 |
| GET | `/topics/{id}/articles?limit=&before=` | 없음 (비공개·꺼진 탭은 404) |
| GET | `/latest?limit=&before=` | 없음 |
| GET·POST | `/admin/topics` | require_admin |
| PATCH·DELETE | `/admin/topics/{id}` | require_admin |
| POST | `/admin/collect` | require_admin |

## 환경 변수

`ENABLE_NEWS_SCHEDULER` · `NEWS_COLLECT_INTERVAL_SECONDS`(최소 300) · `NAVER_SEARCH_CLIENT_ID` · `NAVER_SEARCH_CLIENT_SECRET` ·
`NAVER_SEARCH_API_URL`(비우면 개발자센터, `apigw.ntruss.com` 이면 API HUB 헤더). 키가 없으면 RSS 만 모은다.

## 남은 단계 (newsdesk `docs/구현가이드.md` §7)

2 화면(suvis `app/news` + 호스트 rewrite) · 3 방문자 검색 · 4 올라마 2차 판정(llm 층) · 5 아침 메일 · 6 정답셋·평가.
본문 30일 보관 정리, 같은 소식 묶음 표시도 아직이다.
