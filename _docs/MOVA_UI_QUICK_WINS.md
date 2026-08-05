# mova UI 저수확(low-hanging fruit) 사이클

`_docs/MOVA_UI_AUDIT.md`(§4·§5·§6)에서 발견한 "데이터는 있는데 표시 계층이
끊긴" 항목들을 처리한 기록. **오늘 아침 `characters.character_name`
VARCHAR(50)→TEXT 마이그레이션(`20260805_0001_widen_character_name_to_text`)의
완결편**이기도 하다 — 그 마이그레이션은 "데이터가 안 잘리게" 만들었을 뿐,
그 값이 API 응답에 실려서 화면까지 도달하는 경로는 그날 안 고쳐졌었다. 이
사이클이 데이터 계층부터 표시 계층까지 관통시켜 하루를 완결한다.

---

## 1. character_name — 데이터 계층 → 화면 관통

### 1a. 백엔드 스키마 노출

- `ActorInMovieSchema`(`suvisdev/apps/mova/adapter/inbound/api/schemas/studio_movies_schema.py`)에
  `character_name: str | None = None` 추가.
- `get_by_slug()`(`movies_pg_repository.py`)의 `characters` JOIN `actors` 쿼리는
  이미 `MovaCharacter` 전체 ORM 객체를 SELECT하고 있어서 — **JOIN·SELECT 필드
  추가는 필요 없었다.** DTO(`ActorInMovieDto`)·스키마 계층에만 필드를 관통시키면
  끝나는 작업이었다.
- `MovieDetailDto.from_orm()`/`to_schema()`(`studio_movies_dto.py`)에
  `character_name` 필드 추가·전달.
- EC2 실 배포 후 curl 검증: `curl https://api.suvisdev.cloud/mova/movies/tmdb-1368337`
  응답에 `character_name` 필드와 실값이 실려 나오는지 확인(배포 단계 참고).

### 1b·1c. 프론트 매핑 + 표시 — 예상보다 작은 diff로 끝남

- 지시서는 `mova-title-view.tsx`의 캐스트 리스트 JSX를 직접 고쳐 "이름 — 배역명
  역" 형식을 새로 만드는 걸 전제했지만, 실제로 그 컴포넌트는 이미 `member.role`
  **문자열 하나**를 그대로 렌더링하는 구조였다(`{member.role}` 한 줄).
- 게다가 `lib/mova-movies.ts`의 **목업 데이터**가 이미 `"출연 | 은채니"` 식
  구분자 표기 관례를 쓰고 있었다 — 새 포맷을 발명하지 않고 이 기존 관례를
  그대로 따랐다.
- 결과: `lib/mova-api.ts`의 `fetchMovaTitle()` 매핑 한 곳만 고치면 됐다.
  ```ts
  role:
    a.role_type === "director"
      ? "감독"
      : a.character_name
        ? `출연 | ${a.character_name}`
        : "출연",
  ```
  → **`mova-title-view.tsx`는 변경 없음.** (원 지시서의 1c 항목은 1b로 흡수됨)

### 1d. 회귀 테스트

- `suvisdev/apps/mova/tests/test_studio_movies_dto.py`(신규) — 실 Postgres 없이
  `MovieDetailDto.from_orm()`/`to_schema()`가 cast의 `character_name`을
  보존하는지, 감독 항목이 `character_name=None`으로 병합되는지 검증(3건).
  `testing.md` 원칙(포트/DTO 레벨 fake 우선, 실 DB 의존 최소화)에 맞춰 실
  DB 대신 `SimpleNamespace` 목 객체로 구성.

### 1e. (사이클 도중 발견) movie_directors 미노출 버그 — 같이 고침

작업 도중 지시서의 전제("감독은 이미 role_type='감독'으로 표시되고 있음,
character_name null 허용만 하면 됨")가 실제로는 **성립하지 않는다는 걸
발견했다.**

- `get_by_slug()`는 `characters` JOIN `actors`만 조회한다. 감독 크레딧은
  `characters`가 아니라 완전히 별도인 `movie_directors` 테이블에만 저장된다
  (`credits_backfill_interactor.py`가 cast/director를 각각 다른 테이블에
  upsert).
- 실측(EC2 DB): `tmdb-1368337`(오디세이)의 감독 크리스토퍼 놀란은
  `movie_directors`엔 있지만 `characters`엔 없음(`also_in_characters=false`).
  즉 **감독은 실 데이터 기준으로 상세 API 응답에 단 한 번도 실린 적이 없었다**
  — `MOVA_UI_AUDIT.md` §4에 "감독 — 있음"이라고 적은 건 프론트 코드가 그
  분기를 갖고 있다는 것만 확인한 것이었고, 백엔드가 실제로 그 데이터를
  보내는지는 검증하지 않은 상태에서 쓴 오기였다(이 문서에서 정정).
- 사용자 확인 후 이번 사이클에 포함해 수정: `get_by_slug()`에
  `movie_directors LEFT JOIN actors` 쿼리를 추가하고, `MovieDetailDto.from_orm()`
  이 cast 목록과 병합하도록 변경. 감독 항목은 `characters` 행이 없으므로
  `character_id`/`character_name`이 구조적으로 `None`이다(스키마도
  `character_id: int | None`로 완화).
- 회귀 테스트(`test_studio_movies_dto.py`)에 감독 병합 케이스 포함.

---

## 2. synopsis — 조사만 하고 이번 사이클에서는 보류

- `lib/mova-api.ts`의 `synopsis: ""`는 "있는 값을 안 쓰는 하드코딩"이 아니라
  **애초에 매핑할 필드가 없는 상태**였다: `movies` 테이블에 `synopsis` 컬럼
  자체가 없다(EC2 DB `\d movies` 확인). `MovieDetailSchema`/`MovieDetailDto`에도
  없다.
- 원인 추정: git blame으로는 확인 불가. `lib/mova-api.ts:227`은 최초 통짜
  업로드 커밋(`251ae61`, 2026-07-08, "하위 파일 구조 통째로 업로드 성공")에
  이미 이 상태로 들어와 있어 그 이전 이력이 없다. 목업 단계 잔재로 추정되지만
  확정할 근거는 없음.
- 데이터 자체는 죽지 않았다 — TMDB `overview` 필드는 이미 import 시점에
  가져오고 있지만(`tmdb_mapper.py:159`), 지금은 hub_knowledge 임베딩용
  텍스트에만 쓰이고 `movies` 테이블에는 저장되지 않는다.
- 실제로 살리려면 오늘 아침 character_name TEXT 마이그레이션과 같은 급의
  작업(마이그레이션 + ORM 컬럼 + import 시 저장 + 기존 1067편 TMDB 재조회
  백필)이 필요해, "하드코딩 원복" 한 줄로 끝나지 않는다. 사용자 확인 후
  이번 "저수확" 사이클 범위 밖으로 판단 — PROGRESS.md 백로그로 이관.

---

## 3. 죽은 컴포넌트 4개 판정

`components/mova/` 밑에 있었으나 **생성 이후 어떤 페이지에도 import된 적이
없음**(`git log -S<컴포넌트명> --all -- suvis/app` 전부 결과 0건 — 나중에
빠진 게 아니라 처음부터 안 쓰였다).

| 컴포넌트 | 판정 | 근거 |
|---|---|---|
| `MovaHeroBanner` | **(a) 배선** | `featured: MovaHotRankingItem \| null` prop이 `/mova/main`이 이미 `fetchHotRankings(10)`으로 가져오는 데이터와 타입까지 정확히 일치. 새 fetch·매퍼 없이 `rankings[0] ?? null`만 넘기면 됨. |
| `MovaFeaturedRow` | **(b) 삭제** | props 없음, 완전 하드코딩된 가짜 "에디터 픽"(Unsplash 스톡 이미지, "크리스토퍼 놀란, SF를 다시 쓰다" 같은 지어낸 헤드라인). 링크 대상도 목업 전용 slug(`interstellar`/`dune-2`/`oppenheimer`)라 실 DB 영화와 무관. 백엔드에 이런 에디터 큐레이션 데이터 모델 자체가 없음. |
| `MovaGenreCatalog` | **(c) 유보** | 컴포넌트 자체는 `groupMovaMoviesByGenre()`로 그럴듯하게 real-data-ready처럼 보이지만, 그 헬퍼는 **목업 `MovaMovie[]` 전용**이다. 실 DB 응답 타입(`ApiMovieRow`)을 `MovaMovie`로 바꾸는 매퍼가 없어 지금 배선하면 목업 영화가 실 데이터 화면에 섞여 나온다. 이미 백로그에 있는 "카탈로그 커버리지 확장"(PROGRESS.md 다음 세션 후보 🔥1)과 묶어야 의미 있는 작업이라 유보. |
| `MovaQuickActions` | **(b) 삭제** | 버튼에 `onClick` 자체가 없어(순수 장식, 클릭해도 아무 반응 없음) 처음부터 미완성 상태였다. "매거진"·"이벤트"·"취향분석" 액션은 백엔드에 대응 기능이 아예 없다(취향 재편집 UI 부재는 `MOVA_UI_AUDIT.md` §1(f)에서도 확인됨). "연결"이 아니라 "기능을 새로 발명"해야 하는 수준이라 이번 사이클 범위 밖. |

`MovaFeaturedRow`·`MovaQuickActions`는 파일째 삭제했고, `MOVA_QUICK_ACTIONS`
목업 데이터(`lib/mova-mock-data.ts`)도 그 컴포넌트만 참조하던 죽은 데이터라
같이 제거했다. `MovaHeroBanner`는 `/mova/main/page.tsx`의 `MovaPromoBanner`
(얇은 텍스트 CTA 배너)와 `MovaAiChatBar`/`MovaRankingSection` 사이에 삽입 —
`/mova/main`에 그동안 없던 큰 비주얼(포스터) 영역이 생겼다. `rankings`가
비어 있으면 `MovaHeroBanner`가 이미 갖고 있던 자체 empty-state(일반 AI 소개
문구)로 대체된다.

---

## 4. 검증

- 백엔드: `pytest apps/mova/tests -m "not gpu"` → 100 passed(기존 97 + 신규 3).
- `lint-imports` — mova 관련 계약 전부 KEPT(사전에 존재하던 ontology↔mova
  위반 1건은 이번 변경과 무관, 그대로 유지).
- 프론트: `pnpm type-check` 클린. `pnpm lint`는 이 환경에 `eslint` 바이너리가
  없어 실행 불가(사전 환경 문제, 이번 변경과 무관).
- PR #40 → `main` 머지(`64a5876`) → EC2 `git pull` + `docker compose up -d
  --build backend`(디스크 부족 재발 없이 캐시 히트로 빠르게 재빌드 완료)
  → 실 curl 검증(`https://api.suvisdev.cloud/mova/movies/tmdb-1368337`):
  - 크리스토퍼 놀란이 `role_type: "director"`, `character_id: null`,
    `character_name: null`로 목록에 **처음** 등장(수정 전엔 아예 없었음).
  - 캐스트 항목에 실제 `character_name` 값 확인(예: 샤를리즈 테론 →
    `"Calypso"`).

---

## 5. 스코프 밖으로 유지된 백로그 (PROGRESS.md 반영)

- 필터 UI 확장(연도·평점·플랫폼) — 데이터 부재로 미룸
- 마이페이지 리뷰 목록 — 백엔드 집계 엔드포인트 필요
- 온보딩/취향편집 — `PATCH preferred_genres` 엔드포인트 신설 선행
- 활동요약 — 백엔드 집계 필요
- 유사 영화 추천 — `movies.embedding` 활용, 설계 결정 선행
- **synopsis 실값 backfill**(신규) — 마이그레이션 + TMDB overview 재조회 백필
- **MovaGenreCatalog 배선**(신규) — 카탈로그 확장 작업과 함께, `ApiMovieRow → MovaMovie` 매퍼 필요
