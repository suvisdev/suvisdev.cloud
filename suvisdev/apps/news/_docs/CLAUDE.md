# news 앱 — news.suvisdev.cloud (2026-11-05)

**목적: 새 AI 기술·아키텍처 변화를 바로 알아 공부하는 것**(2026-11-05 사용자 결정).
메인은 **AI 섹션**(연구소 블로그·논문·릴리스·해설·커뮤니티·국내 AI 매체), **경제 섹션은 부록**(경제 언론 RSS + 검색).
국내 뉴스 기사에서 AI가 만든 기사에는 **숨기지 않고 배지**를 단다.
판정 기준의 원천은 하네스 저장소 밖 폴더(`Desktop\뉴스\newsdesk`)의 `news-ai-filter` 스킬 `references/rubric.md` 다.

## 원칙

- **원문 페이지는 가져오지 않는다.** RSS·검색 API 가 직접 준 것(제목·요약·링크·날짜·작성자, 일부 피드의 본문)만 쓴다.
  저장소의 기존 저작권 원칙(`ontology/.../google_news_scraper.py`, `mova/.../editor_reviews_scheduler.py`)과 같다.
- **화면·API 에 본문을 내보내지 않는다.** `ArticleSchema` 에는 제목·요약·원문 링크·섹션·묶음·배지만 있다.
- **AI 배지 판정은 한국어 뉴스 기사 묶음만**(`domain/sections.py` `JUDGED_GROUPS` = 국내 AI 매체·경제 언론·뉴스 검색).
  기사체 신호(기자명, '-다'체, 인용 표기)를 보는 규칙이라 영어 글·1차 출처에는 맞지 않는다 — 11-05 실측:
  국내 AI 매체를 뺀 AI 피드 3,321건에 돌리면 'AI 생성 의심' 13건(OpenAI·AWS·Microsoft Research 공식 블로그 포함), 보류 208건.
  판정하지 않는 묶음은 **본문도 저장하지 않는다**(본문은 판정에만 쓰므로).
- **배지는 신호로만 말한다.** `ai_disclosed`(매체가 AI 작성을 밝힘) → "AI 작성", `ai_suspected`(규칙·2차 판정 추정) → "AI 생성 의심",
  누르면 `reasons_ko`. "가짜·허위" 같은 단정은 쓰지 않는다. 사실 여부는 판정하지 않는다.
- **`domain/ai_filter/` 는 newsdesk 하네스 `scripts/ai_filter/` 와 같은 파일이다.** 표준 라이브러리만 쓴다(`.importlinter` news-domain-purity).
  기준을 바꾸면 rubric → `thresholds.json` → `signals.py` 순서로 고치고 `harness_version` 을 올린다. 버전이 바뀌면 다음 수집 주기에 그 주기 기사부터 다시 판정된다.
- **수집 스케줄러는 노트북에서만** (`ENABLE_NEWS_SCHEDULER=true`, 기본 꺼짐). 꺼져 있어도 `POST /api/v1/news/admin/collect` 로 한 주기를 돌릴 수 있다.
- **방문자 검색은 모아 둔 기사에서만** 찾는다(`/search`). 외부 검색 API 를 부르지 않아 할당량을 쓰지 않는다.

## 섹션·묶음 (`domain/sections.py`, 피드 목록 `adapter/outbound/http/latest_feeds.json`)

| 섹션 | 묶음 | 피드 (11-05 응답 확인) | 판정 |
|---|---|---|---|
| ai | lab 연구소·기업 블로그 | OpenAI, Google DeepMind, Google Research, Hugging Face, NVIDIA 개발자, Microsoft Research, AWS ML | 안 함 |
| ai | paper 논문 | arXiv cs.CL·cs.LG (새 논문만, 개정 공지 `replace` 건너뜀, 피드당 300건) | 안 함 |
| ai | release 오픈소스 릴리스 | GitHub `releases.atom` — vLLM, Ollama, Transformers | 안 함 |
| ai | commentary 해설·뉴스레터 | Simon Willison, Latent Space, Interconnects, Import AI, Lilian Weng | 안 함 |
| ai | community 커뮤니티 | GeekNews, Hacker News(LLM·50점 이상), r/LocalLLaMA | 안 함 |
| ai | ko_media 국내 AI 매체 | AI타임스, 인공지능신문 | **함** |
| economy | outlet 경제 언론 | 연합(경제·마켓+), 매경(경제·증권), 한경(경제·증권), 조선비즈, 머니투데이, 서울경제, 뉴시스·동아·경향·JTBC 경제 (13곳) | **함** |
| economy | search 뉴스 검색 | 경제 검색어 탭의 네이버 뉴스 검색 결과(키 있을 때) | **함** |

- 피드는 최신 50건만(`max_items`, 보관본 전체를 주는 피드가 있음 — OpenAI 1,359건·Hugging Face 897건).
- SBS 는 RSS 에 "개인 리더 이용 목적만 허용, 게시 금지" 문구가 있어 넣지 않는다. 안 되는 곳: Anthropic·Meta AI(RSS 404), r/MachineLearning(429).
- 한겨레 경제 RSS 는 글에 날짜가 없어(11-05 화면 확인 때 발견) 뺐다 — 날짜 없는 글은 수집 시각으로 정렬돼 첫 수집분 30건이 경제 첫 화면을 다 차지했다.
- AI타임스·인공지능신문은 날짜에 시간대가 없다("2026-11-05 17:27:15", 한국 시각). 피드 설정 `"naive_tz": "+09:00"` 로 읽는다 —
  없으면 UTC 로 읽혀 9시간 미래가 된다(11-05 운영 첫 수집에서 AI 메인 맨 위를 차지). 새 피드를 넣을 때 날짜 끝에 시간대가 있는지 본다.
- 목록 정렬·다음 쪽 기준은 `sort_at`(날짜가 없으면 수집 시각) — API 가 내보내고 화면은 마지막 글의 `sort_at` 을 `before` 로 넘긴다.
- 피드를 더하려면 `latest_feeds.json` 에 `{"name", "url", "group"}` 한 줄(묶음 코드는 위 표). 판정 범위는 묶음으로 정해진다.

## 흐름

```text
스케줄러(30분) 또는 POST /admin/collect
 → NewsCollectInteractor
     ├ RSS × latest_feeds.json(35곳) — 섹션·묶음 표시, 피드당 최신 N건, arXiv 개정 공지 건너뜀
     ├ 검색어 탭: 자기 섹션의 이번 주기 RSS 글을 domain.relevance 로 고름
     │    └ 경제 탭은 NaverNewsSearchClient(키 없으면 건너뜀) 결과도 더함
     ├ canonical_url 로 중복 제거(먼저 온 RSS 묶음을 남김, 검색·RSS 둘 다면 RSS)
     ├ 판정 범위 밖 묶음은 본문을 비움 → NewsPgRepository.save_articles / link_topic_articles
     └ 판정 범위 묶음 중 현재 하네스 버전 rules 판정이 없는 기사만 classify(mode C, 스레드) → save_verdicts
GET /sections · /topics · /topics/{id}/articles · /latest · /search → 배지 = llm 판정이 있으면 llm, 없으면 rules
```

## ERD (alembic `20261105_0001` + `20261105_0002`)

| 테이블 | 열 | 비고 |
|---|---|---|
| `news_topics` | id · query(UQ) · label · **section** · is_public · active · created_at | 운영자 검색어 = 탭 |
| `news_articles` | id · canonical_url(UQ) · link · source_domain · source_name · title · summary · body · author · origin(search/feed) · **section · feed_group** · published_at · sort_at · fetched_at | body 는 판정 범위 묶음에서 RSS 가 준 본문만, 내보내지 않음. ix(section, sort_at) |
| `news_topic_articles` | topic_id(FK, PK) · article_id(FK, PK) · relevance · matched_at | |
| `news_verdicts` | id · article_id(FK) · layer(rules/llm) · harness_version · verdict(normal/pending/ai) · badge · reasons_ko(JSONB) · signals(JSONB) · created_at | UQ(article_id, layer) |

## API (`/api/v1/news`)

| 메서드 | 경로 | 인증 |
|---|---|---|
| GET | `/sections` | 없음 — 섹션·묶음·피드 이름 |
| GET | `/topics?section=` | 없음 |
| GET | `/topics/{id}/articles?limit=&before=` | 없음 (비공개·꺼진 탭은 404) |
| GET | `/latest?section=ai&group=&limit=&before=` | 없음 (section 기본 ai, 다른 섹션 묶음은 400) |
| GET | `/search?q=&section=ai&limit=&before=` | 없음 (q 1~50자, 단어 5개까지, 제목·요약에 모두 포함) |
| GET·POST | `/admin/topics` (POST 에 `section`) | require_admin |
| PATCH·DELETE | `/admin/topics/{id}` | require_admin |
| POST | `/admin/collect` | require_admin |

## 환경 변수

`ENABLE_NEWS_SCHEDULER` · `NEWS_COLLECT_INTERVAL_SECONDS`(최소 300) · `NAVER_SEARCH_CLIENT_ID` · `NAVER_SEARCH_CLIENT_SECRET` ·
`NAVER_SEARCH_API_URL`(비우면 개발자센터, `apigw.ntruss.com` 이면 API HUB 헤더). 키가 없어도 RSS 35곳과 검색어 탭(RSS 매칭)은 돈다 — 키는 경제 탭의 뉴스 검색에만 쓴다.

## 실측 (11-05, 로컬 SQLite, 네이버 키 없음)

- 피드 36곳 전부 응답, 첫 주기 1,564건(AI 947 · 경제 617) 37.8초, 두 번째 주기 새 글 2건. (이 실측 뒤 날짜 없는 한겨레 경제 30건 피드를 빼 지금은 35곳)
- 판정 717건(국내 AI 매체 100 · 경제 언론 617) 전부 normal, 판정 범위 밖 847건. 본문 저장은 경제 언론 49건(조선비즈)뿐.
- 검색어 탭(RSS 매칭): "mixture of experts" 17건 · "agent" 100건 이상 · "금리"(경제) 8건. `/search` "transformer"(ai) 41건 · "환율"(경제) 10건.

## 화면 (2단계, 11-05)

`suvis/app/news` — 서버 컴포넌트(`lib/news-api.ts` 로 이 API 를 부름). 섹션 전환·검색·묶음 탭·주제 탭·배지(누르면 이유)·"AI 배지 글 숨기기"·더 보기(`sort_at`).
`suvis/next.config.mjs` rewrites 가 `news.suvisdev.cloud` 의 `/` 를 `/news` 로 보낸다. `suvisdev.cloud/news` 도 같은 화면. 허브 타일 `AI 소식`(`lib/apps-catalog.ts`, 아이콘 `public/news-icon.svg`).
**도메인 연결은 사용자 콘솔 작업**: Vercel `suvis` 프로젝트 Domains 에 `news.suvisdev.cloud`, Cloudflare DNS `news` CNAME → `cname.vercel-dns.com`(Vercel 안내값 우선).

## 한국어 제목·요약 (11-05, alembic `20261105_0003`)

- 노트북 올라마 **EXAONE 3.5 7.8B**(`adapter/outbound/llm/ollama_ko_summarizer.py`)가 영어 글 제목을 옮기고 모든 글을 2~3문장으로 요약 → `news_articles.title_ko·summary_ko`.
  한국어 글은 원제 그대로(`domain/ko_summary.py`). 출력 검사에 걸리면 `ko_tries` 를 세고 3번이면 그만. 모델 서버가 안 되면 그 주기는 멈춘다(실패로 세지 않음).
- 스케줄러가 수집 뒤 `NEWS_SUMMARY_BATCH`(기본 80)건까지 — **AI 섹션 먼저**, 최신순. 화면은 한국어 제목(작게 원제)·'AI 요약' 표시. `/search` 는 한국어 제목·요약도 찾는다.
- 주소는 노트북 올라마 직접(`NEWS_SUMMARY_OLLAMA_URL` → `PORTFOLIO_LLM_OLLAMA_URL` → `OLLAMA_BASE_URL`). 중계기를 거치면 노트북이 죽었을 때 집컴 CPU 에 7.8B 를 올린다.
- 11-05 실측(RTX 4060): 글당 2.4~3.8초(첫 글 7.5초), 실제 코드 흐름 27건 실패 0. 2.4B 는 영어 제목을 옮기지 않아 쓰지 않음.
  첫 지시문은 "왜 중요한지"를 시켜 원문에 없는 평가("중요한 발전")가 붙어서 "원문에 없는 평가 금지"로 바꿈. 가끔 이름을 옮긴다(PolicyIK → 정책IK).

## 남은 단계 (newsdesk `docs/구현가이드.md` §7)

3 방문자 검색 캐시·상한 · 4 올라마 2차 판정(llm 층) · '오늘의 핫한 소식'(HF Daily Papers 추천 수·HN 점수 + EXAONE 요약) · 5 아침 메일("어제 AI 소식") · 6 정답셋·평가.
본문 30일 보관 정리, 같은 소식 묶음 표시도 아직이다.
