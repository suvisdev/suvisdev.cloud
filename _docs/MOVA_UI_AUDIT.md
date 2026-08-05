# mova 프론트엔드 UI 완성도 감사

**범위**: `suvis/app/mova/**`·`suvis/components/mova/**`·`suvis/lib/mova-*` 정적
코드 감사 + EC2 실 DB 카운트 대조. **코드 변경 없음 — 현황 파악만.**

---

## 0. 구조 먼저 — 감사 전에 확정해둘 것

- `/mova`(`app/mova/page.tsx`)는 **랜딩**(인트로 애니메이션 + AI 챗바 CTA
  하나짜리 스플래시)이고, 로그인 후에도 계속 쓰는 **"홈 피드"는
  `/mova/main`**(`app/mova/main/page.tsx`)이다. 사용자가 "홈 화면(§2)"로
  물어본 라우트가 실제로는 이 둘로 나뉘어 있어 두 파일 다 감사했다.
- **"검색 결과 페이지"(§3)는 존재하지 않는다.** 검색은 헤더의 자동완성
  드롭다운(`MovaSearchBar`) 하나로 전부이고, 결과를 클릭하면 바로 상세
  페이지로 이동한다 — 필터·정렬·페이지네이션이 있는 별도 "검색 결과"
  라우트 자체가 없다. 가장 가까운 대안은 `/mova/movies`(장르 탭 브라우징
  페이지)인데 이것도 텍스트 검색이 아니라 장르 클릭 기반이다. §3은 이
  전제로 판정했다.

---

## 1. 마이페이지 감사 (`app/mova/mypage/page.tsx`)

| 항목 | 판정 | 근거 |
|---|---|---|
| (a) 온보딩(신규 사용자 `preferred_genres` 등록) | **없음** | 헤더 로그인 드롭다운의 이메일 가입 폼(`mova-login-button.tsx` `handleEmailSubmit`)도, `/mova/login`의 `MovaAuthForms`(`mova-auth-forms.tsx`)도 `preferred_genres`를 전혀 다루지 않는다. 백엔드 `SignupSchema.preferred_genres`(`suvisdev/apps/viewer/adapter/inbound/api/schemas/signup_schema.py:17`) 필드 자체는 있지만 이 UI들이 안 채워 보낸다. |
| (b) 활동 요약(본 영화 수/리뷰 수/별점 분포) | **없음** | `mypage/page.tsx`엔 "AI 추천 기록"·"찜한 영화"·"최근 검색" 3개 섹션뿐. `MypageData` 타입(`lib/mova-api.ts:600-605`)에 통계 필드 자체가 없다 — 스캐폴딩도 아니고 아예 설계에서 빠짐. |
| (c) Watchlist 담기/보기/삭제 | **부분(기능은 완전, mypage 안에서만 일부)** | 담기/삭제(`addToWatchlist`/`removeFromWatchlist`, `lib/mova-api.ts:571-583`)는 title 상세(`mova-title-view.tsx:103-119`)와 AI 채팅 카드(`mova-recommendation-cards.tsx`) 양쪽에 토글 버튼으로 구현돼 있다. **보기는 mypage에 있지만(§ 아래 "찜 목록" 섹션), mypage 화면 자체에는 삭제 버튼이 없다** — 지우려면 상세 페이지로 가서 토글해야 함. |
| (d) 프로필 편집(닉네임/이미지) | **없음(다른 라우트에 있음)** | mypage는 닉네임을 읽기 전용으로만 보여준다(`{data?.nickname ?? session?.username}`, `mypage/page.tsx:76`). 닉네임 편집 UI는 `suvis/CLAUDE.md` 라우트 표 기준 별개의 `/mypage`(mova 아님, 사이트 공용) 쪽에 있다(2026-07-30 작업, `PATCH /viewer/profile/{id}`) — mova mypage와 연결이 안 돼 있다. 이미지 업로드는 어디에도 없음. |
| (e) 내 리뷰 목록 및 관리 | **없음** | mypage 어디에도 "내 리뷰" 섹션이 없다. 리뷰 작성·수정은 각 영화 상세 페이지(`mova-title-view.tsx`)에서만 가능하고, 자기가 쓴 리뷰를 한곳에 모아보거나 삭제하는 화면이 없다(삭제 API 자체 존재 여부도 미확인 — 조사 범위 밖). |
| (f) 취향 재편집(`preferred_genres` 수정) | **없음(백엔드도 없음)** | mypage는 `data.preferred_genres`를 배지로 **표시만** 한다(`mypage/page.tsx:79-90`, 클릭 불가). 백엔드 `profile_router.py`에도 닉네임 `PATCH`(`update_nickname`)만 있고 취향 수정 엔드포인트가 없다(§ 코드 확인) — 프론트뿐 아니라 API 계약 자체가 없는 상태. |

**부수 확인**: `preferred_genres`가 실제로 값을 가진 사용자가 EC2 DB에 **0/4명**
(전체 유저 4명 중 0명)이었다 — (a)+(f)가 둘 다 없으니 애초에 채워질 방법이
없었던 것과 정확히 일치.

---

## 2. 홈 화면 감사 (`/mova` 랜딩 + `/mova/main`)

### `/mova`(`app/mova/page.tsx`) — 랜딩

| 항목 | 판정 | 근거 |
|---|---|---|
| (a) 로그인 사용자 개인화 | **없음** | 인트로 애니메이션 → 로고·검색·로그인 버튼 헤더 → AI 챗바 CTA 하나. 세션 유무로 레이아웃이 갈라지는 지점이 없다(로그인 버튼만 세션 있으면 로그아웃 버튼으로 바뀜 — `mova-login-button.tsx:213-236`). |
| (b) 노출 섹션 | 인트로 문구("AI movie concierge") + 챗바 하나뿐. 인기·최신·장르별 리스트는 랜딩엔 없음(§ `/mova/main`에 랭킹만 있음, 아래 참고). |
| (c) AI 챗봇 접근 경로 | **페이지 중앙 전면 CTA** — 플로팅 버튼이나 배너가 아니라 랜딩 자체가 챗 입력창(`MovaLandingChatBar`)이다. |
| (d) 검색창 위치 | 헤더 우상단, `MovaSearchBar`(자동완성 드롭다운). |
| (e) 비로그인 vs 로그인 차이 | 로그인 버튼 텍스트/드롭다운 외 **레이아웃 차이 없음**. |

### `/mova/main`(`app/mova/main/page.tsx`) — 실질적 홈 피드

| 항목 | 판정 | 근거 |
|---|---|---|
| (a) 개인화 섹션 | **부분** | 화면 구성(프로모 배너 + 챗 + 랭킹 사이드바)은 로그인 여부와 무관하게 동일. 다만 `MovaAiChatBar`가 세션이 있으면 `user_id`를 요청에 실어 보내(`mova-ai-chat-bar.tsx:223`) 챗 답변 자체는 서버 쪽에서 `preferred_genres`·최근 의도(과거 대화) 기반으로 조용히 개인화된다(`market_chat_interactor.py`) — **눈에 보이는 섹션 개인화는 없고, 챗 답변 내용만 개인화**. |
| (b) 노출 섹션 | 프로모 배너(`MovaPromoBanner`) + AI 챗바(메인) + HOT 랭킹 사이드바(`MovaRankingSection`, `chat_trend`/`box_office` 소스). 인기·최신·장르별 그리드는 여기 없음 — 그건 `/mova/movies`(§3 근처)에 있음. |
| (c) AI 챗봇 접근 경로 | 페이지 메인 컬럼 전체가 챗바 — 배너·플로팅이 아니라 **1차 콘텐츠**. |
| (d) 검색창 위치 | `MovaHeader`(공통 헤더) 우측, 자동완성. |
| (e) 로그인 vs 비로그인 | 위 (a) 참고 — 구조 차이 없음, 챗 답변만 다름. |

**부수 발견 — 죽은 컴포넌트 4개**: `MovaFeaturedRow`·`MovaGenreCatalog`·
`MovaHeroBanner`·`MovaQuickActions`(전부 `components/mova/`)가 **어떤
`app/` 페이지에서도 import되지 않는다**(grep 확인, 자기 파일 밖 참조 0건).
"인기/최신/장르별 노출 섹션"이 왜 없는지의 답이 여기 있다 — 만들다 만 게
아니라 **완성된 컴포넌트가 있는데 어느 페이지에도 안 꽂혀 있는 상태**다.

---

## 3. 검색 UX 감사 (§0 참고 — 별도 "검색 결과 페이지" 없음)

| 항목 | 판정 | 근거 |
|---|---|---|
| (a) 필터 UI(장르/연도/평점/플랫폼/배우) | **부분** | 자동완성 드롭다운엔 필터가 아예 없다. `/mova/movies`엔 **장르 탭만** 있음(`GENRES` 하드코딩 12종, `movies/page.tsx:19-32`). `fetchMovaMovies()`(`lib/mova-api.ts:341-376`)는 `release_year`·`min_rating`·`age_rating`·`platform`·`sort`까지 이미 받게 돼 있는데 **이 페이지 UI가 장르 말고는 아무것도 안 넘긴다** — API는 준비돼 있고 UI만 안 씀. |
| (b) 정렬 옵션 | **없음** | 위와 동일한 이유 — `sort` 파라미터가 함수엔 있지만 어느 화면에도 정렬 버튼/셀렉트가 없다. |
| (c) 페이지네이션 | **부분** | `/mova/movies`는 "더 보기" 버튼(오프셋 누적 로드) 방식(`movies/page.tsx:249-266`) — 번호 페이지네이션은 아님. 자동완성엔 해당 개념 없음(드롭다운 목록일 뿐). |
| (d) 자동완성 | **있음** | `MovaSearchBar`(`components/mova/mova-search-bar.tsx`) — 입력 280ms 디바운스 후 `fetchMovaSearch()` 호출, `title`/`person`/`keyword`/`synopsis` 매치 타입 라벨까지 표시(`movaMatchLabel`). API 실패 시 로컬 목업 데이터로 폴백까지 구현돼 있음(51-77행). |
| (e) 결과 없을 때 대안 | **부분** | 자동완성: "검색 결과가 없습니다" 문구만(대안 추천 없음, 168행). `/mova/movies`: "등록된 영화가 없습니다"/"{장르} 장르 영화가 없습니다" 문구만(239-241행) — 둘 다 대체 검색어·인접 장르 제안 같은 건 없음. |

---

## 4. 영화 상세 페이지 감사 (`components/mova/title/mova-title-view.tsx`)

전수 목록(파일 순서대로):

| 컴포넌트/섹션 | 판정 | 근거 |
|---|---|---|
| 포스터 | 있음 | `movie.poster`, 히어로 배경은 `movie.backdrop` 블러 처리(191-221행) |
| 시놉시스 | 있음(조건부) | `movie.synopsis` — 단, `fetchMovaTitle()`이 API 응답을 매핑할 때 **`synopsis: ""`로 항상 빈 문자열 고정**(`lib/mova-api.ts:222`) — 실제 DB 영화는 UI가 있어도 시놉시스가 절대 안 뜬다(목업 10여 편만 `mova-movies.ts`에 하드코딩된 시놉시스로 보임). |
| 개봉연도 | 있음 | `metaParts`에 `movie.year` 포함(180-185행) |
| 감독 | **있음(별도 섹션 아님)** | "출연 · 제작" 리스트 안에 `role_type: "director"`→"감독" 라벨로 배우와 나란히 표시(303-316행, 매핑은 `lib/mova-api.ts:224-228`) — 감독 전용 필드/줄은 없고 캐스트 리스트에 섞여 나옴 |
| 출연진 | 있음 | 위와 같은 리스트, `role_type: "actor"`→"출연" |
| 리뷰 섹션 | **있음(완성도 높음)** | 목록 + 작성/수정 폼, 별점(0.5~5) + 본문 선택 제출, "봤어요" 게이트(`handleMarkWatched`, 121-132행), 본인 리뷰면 수정 모드로 전환(`myReview`) — 이번 조사 대상 중 가장 완성된 기능 |
| 유사 영화 추천 | **없음** | 파일 전체에 관련/유사 작품 섹션 자체가 없다. `MovaMovie` 타입(`lib/mova-movies.ts:18-40`)에도 `similarMovies`류 필드가 없어 데이터 모델 단계부터 빠져 있음 |
| 트레일러/영상 | **없음** | "스틸컷"(`movie.gallery`, 318-332행)은 정적 이미지 배열이다 — 영상 필드(`videoUrl` 등) 자체가 타입에 없음 |
| 스트리밍 플랫폼 링크 | **부분(사실상 미노출)** | `movie.platform`은 문자열 배지로만 표시(280-284행, `<span>`이지 링크 아님). `platforms[].url`은 `fetchMovaTitle()` 매핑에서 아예 안 읽음(`lib/mova-api.ts:213-216` — `provider`만 취급). 게다가 §5에서 확인했듯 **실 DB 1067편 중 platforms 데이터가 있는 영화가 0편**이라 어차피 안 뜸 |
| Watchlist 담기 버튼 | 있음 | "찜하기"/"찜 완료" 토글(236-256행) |
| 별점/리뷰 작성 진입점 | 있음 | 리뷰 섹션과 동일(위 참고), "봤어요" 안 누르면 진입 못 하게 안내 문구까지 있음(384-386행) |

---

## 5. 데이터 활용도 감사 (EC2 실 DB 카운트 대조, `movies` 총 1,067편 기준)

| 필드 | DB 상태 | 프론트 판정 | 근거 |
|---|---|---|---|
| `movies.platforms`(JSONB) | **1,067편 중 0편**이 값 보유(`bulk_import_movies.py`가 애초에 이 필드를 안 채움) | **미노출**(코드는 있지만 데이터가 없어 결과적으로 항상 미노출) | 코드상으론 목록(`movies/page.tsx:58,85-87`)·상세(위 §4)에서 `netflix`/`disney` **딱 2개 provider만** 하드코딩 인식(`platform?: "netflix" \| "disney"`, `mova-movies.ts:28`) — 그 외 provider는 값이 있어도 어차피 버려짐. `url` 필드는 어디서도 안 읽음(링크 기능 자체가 없음) |
| `movies.age_rating` | **1,067편 중 0편**이 값 보유 | **일부 노출**(코드는 정상 동작, 데이터만 없음) | `fetchMovaTitle()`이 `row.age_rating`을 그대로 매핑(`ageRating`)하고 상세 페이지 `metaParts`에 표시(183행) — 채워지면 바로 보임. 목록 페이지 필터 파라미터(`age_rating`)도 API 클라이언트엔 있음(`fetchMovaMovies` 시그니처) |
| `movies.collection_id` | **1,067편 중 0편**, `collections` 테이블도 **0행** | **미노출(타입에도 없음)** | `MovieDetailSchema.collection_id`는 백엔드에 있지만 프론트 `MovieDetailApiRow`/`MovaMovie` 타입 어디에도 `collectionId` 필드가 없다 — 매핑 자체를 안 함. `/mova/collections` 페이지(§ 아래)는 완성돼 있으나 보여줄 데이터가 없음 |
| `users.preferred_genres` | 유저 4명 중 **0명**이 값 보유 | **일부 노출**(mypage에 표시 코드는 있으나 항상 빈 배열이라 안 보임) | §1 (a)/(f) 참고 — 채울 UI 경로가 signup에도 mypage에도 없어서 구조적으로 항상 빈 상태 |
| `characters`/`actors`(10,152 / 7,058행) | **채워짐** | **일부 노출** | 배우 **이름**은 상세 페이지 "출연·제작"에 나온다(§4). 다만 `characters.character_name`(배역명, 오늘 세션에 32자→332자까지 정확히 담기도록 스키마까지 고친 그 필드)는 **API 응답 스키마 자체(`ActorInMovieSchema`, `studio_movies_schema.py:18-23`)에 없다** — `character_id`/`actor_id`/`name`/`role_type`/`profile_photo_url`뿐, `character_name` 필드가 빠져 있어 프론트가 아무리 고쳐도 표시할 수 없는 상태(백엔드 응답 계약의 누락, 프론트 문제 아님). 그래서 "박은빈 — 출연"까지만 나오고 "박은빈 — 은채니 역"처럼 배역명은 절대 안 나옴 |
| `movies.embedding`(vector, 부수 확인) | 채워짐(Gemini 768차원) | **미노출** | 유사 영화 추천(§4에서 "없음")이 바로 이 임베딩을 쓸 법한 자리인데 실제로 쓰는 코드가 없음 — Neo4j 그래프와 같은 처지("데이터는 있는데 읽는 코드가 없음") |

---

## 6. 우선순위 제안 — "확실히 없어서 추가 가치가 있는 것"

이미 있는 데이터·API를 그대로 살릴 수 있어 상대적으로 공수 대비 효과가 큰
순서로 정리했다(순수 의견, 착수 여부는 별도 결정 필요).

1. **`/mova/movies` 필터 UI 확장(연도·평점·플랫폼)** — API(`fetchMovaMovies`)
   가 이미 다 받는 파라미터를 UI만 안 씀. 새 백엔드 작업 없이 프론트 폼
   추가만으로 §3 (a)(b) 공백을 상당히 메울 수 있음.
2. **죽은 컴포넌트 4개(`MovaFeaturedRow`·`MovaGenreCatalog`·`MovaHeroBanner`·
   `MovaQuickActions`) 정리** — 홈 화면에 실제로 꽂아 넣거나(원래 의도대로
   "인기/최신/장르별" 섹션 완성), 정말 안 쓸 거면 삭제. 지금 상태(완성돼
   있는데 미연결)가 가장 어정쩡함.
3. **`ActorInMovieSchema`에 `character_name` 추가**(백엔드 스키마 1줄) —
   오늘 세션에 고친 `characters.character_name`(TEXT, 최대 332자 실측)
   데이터가 API 응답에 아예 없어서 프론트가 손 쓸 방법이 없는 상태. 이거
   하나만 열어도 "배역명" 노출이 가능해짐.
4. **마이페이지 "내 리뷰 목록"** — 리뷰 작성 API는 이미 완성돼 있음(§4).
   목록 조회만 추가하면 됨(개별 영화 API를 리뷰별로 순회하거나 새 집계
   엔드포인트 하나).
5. **취향 온보딩 + 재편집** — 신규 가입 시 장르 선택 스텝 + mypage에서
   수정 가능하게. 전제 조건: 백엔드에 `PATCH preferred_genres` 엔드포인트
   자체부터 신설 필요(현재 없음, §1 (f) 참고) — 다른 항목보다 백엔드
   작업이 먼저 필요해 순위를 낮게 잡음.
6. **마이페이지 활동 요약(본 영화 수/리뷰 수)** — `user_actions`(watched)·
   `reviews` 테이블 데이터는 이미 있음(mova 리뷰 watched 게이트, 2026-08-04
   완료). 집계 엔드포인트 하나 + mypage 섹션 하나만 있으면 됨.

**의도적으로 낮은 우선순위**: 유사 영화 추천(임베딩 활용 필요, 설계
결정 먼저), 트레일러/영상(원본 데이터 소스 자체가 없음 — TMDB 비디오
API 별도 연동 필요), 컬렉션 실 데이터 채우기(콘텐츠 큐레이션 작업이라
개발 우선순위와 결이 다름).
