# 작업 일지 — GILDLE 워크로드

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

## 2026-09-28

### 작업 내용
- 사용자 스크린샷: 웹 지도(`/gildle/map`)의 배경 타일이 전부 "API KEY REQUIRED carto.com/basemaps/apikey"
  워터마크로 나옴. 원인은 코드가 아니라 **CARTO basemaps 정책 변경** — `basemaps.cartocdn.com/dark_all`
  타일이 API 키 없는 요청에 워터마크 타일을 돌려준다(08-27 도입 당시엔 무료·무키). 보행 그래프 간선
  (초록)은 우리 API라 정상.

- 이어서 사용자 결정 **"네이버 SDK로 재작성 + 웹도 앱과 동일하게"**(장소 검색은 유지, 레이어 토글·
  여름 출발 시각·경유 도로 목록은 삭제, 산책 추적도 웹에 구현). Explore 에이전트로 Flutter 지도 화면
  (`gildle_map_screen.dart`·`map_controller.dart`)과 웹을 대조한 뒤 앱 구성을 기준으로 다시 썼다.

### 수정/구현
- (오전) `gildle-map.tsx` TileLayer를 OSM 표준 타일로 임시 교체 — 아래 재작성으로 대체됨.
- **`app/gildle/map/_components/gildle-map.tsx` 전면 재작성(네이버 지도 JS v3, `next/script`로
  `maps.js?ncpKeyId=…` 로드)**: 서울시청 중심·zoom 13·minZoom 10·로고 오른쪽 위(앱과 동일) · 지도 탭
  1번째 출발→2번째 도착(`POST /api/gildle/routes`, 좌표를 그대로 보내 서버가 스냅)→3번째 다시 출발 ·
  계절 모드 3종(봄·가을/여름 그늘/겨울 안전, 바꾸면 루프 비우고 재계산) · FAB 3개(현재 위치→출발지
  +zoom 16, 루프 시트 0.5~8 km 슬라이더→`POST /loops` 후보 칩 "거리·8방위", 지우기) · 하단 카드(안내
  문구·거리·예상(1.2 m/s)·여름 그늘 %·"밤이라 그늘 계산 없이 최단 경로") · 폴리라인은 흰 외곽선 위에
  여름+`edge_shades`면 구간별 햇빛(warm)→그늘(accent) lerp, 그 외 accent 단색(앱 `_pathOverlay`와 같은
  규칙, 앞뒤 연결 구간은 이웃 간선 그늘) · 경로 바뀌면 fitBounds(60/60/200/60).
- **산책 추적(웹)**: "이 길로 산책 시작" → 로그인 세션 없으면 안내, 있으면 `watchPosition`(5 m 미만
  이동은 버림, 앱 distanceFilter와 동일)으로 걸은 길을 accent 실선, 계획 경로를 회색 점선으로 그리고
  거리·시간 타이머 표시 → "산책 끝내기" → `POST /api/gildle/walks`(path 5,000점 이하로 솎음, 여름이면
  `avg_shade_score`=경로 그늘 비율) → "기록 #id 저장됨". 웹엔 기록 목록 화면이 아직 없다(후속).
- `lib/gildle-api.ts` 신설(`calculateRoute`·`findLoops`·`createWalk`, 세션 Bearer, `safeApiErrorMessage`)
  — 종전 컴포넌트가 `fetch`를 직접 부르던 것을 CLAUDE.md C.2 규칙대로 정리. 장소 검색(Nominatim)은
  컴포넌트 안 그대로(외부 공개 API).
- 삭제: Next 프록시 `app/api/gildle/graph-edges`·`navigate`(웹 전용 기능과 함께 불필요), 의존성
  `leaflet`·`react-leaflet`·`@types/leaflet`. 추가: `@types/navermaps`(dev).
- 환경변수 `NEXT_PUBLIC_NAVER_MAP_CLIENT_ID`(앱 `NAVER_MAP_CLIENT_ID`와 같은 값). 로컬은 `suvis/.env.local`
  (gitignore), 프로덕션은 **사용자가 Vercel 환경변수로 등록**. NCP 콘솔 Application `gildle`의 Web
  서비스 URL에 `https://suvisdev.cloud` 등록 확인(스크린샷), `http://localhost:3000` 추가 권고. 인증 실패
  시 `navermap_authFailure` 훅으로 상단 안내.

- **시간·거리로 돌아오는 산책 추천 + mova식 오케스트레이터**(사용자 "출발지 선택하면 몇 분 동안 몇 키로 산책하고
  싶다고 지정 → 편한 길·언덕길 골라 제한 시간 안에 키로수 맞춰 집까지"): ① **고도**: SRTM1 타일 N37E126·N37E127
  (AWS `elevation-tiles-prod/skadi`)을 쌍선형 보간해 `apps/gildle/data/node_elevation.json`(16.5만 노드, -11~711m,
  남산 268m·여의도 18m 검증, gitignore·hostPath) — `scripts/compute_node_elevation.py`. ② `walk_preference`
  도메인 서비스: fast·shade·green·flat(경사 페널티 ×(1+10·경사))·hilly(경사 할인 최대 60%) 가중치 + 휴리스틱
  하한, 누적 오르막 `climb_m`. 경로 유스케이스에 `execute_weighted`·`execute_shortest`, 루프 유스케이스에
  `weight_fn`·`heuristic_scale` 주입. ③ `RouteOptionsInteractor`가 모든 후보를 선호 가중치로 계산(고도 있으면
  편한 길 후보 추가, 요청 시 언덕길), `loops()`로 선호 루프 → 제한 시간 넘는 루프 제외 → 들를 곳 종류를 지나는
  루프 우선 → 선호가 가장 뚜렷한 순. 설명문에 "목표 N km에 맞춰 출발지로 돌아오는 …"·오르막 문장.
  ④ **이해**: `ExaoneWalkUnderstandingAdapter`(Ollama exaone3.5:7.8b JSON 모드, 슬롯 kind·minutes·distance_km·
  preference·stops) → `walk_request.verify`(문장에 근거 있는 숫자·키워드는 규칙 우선, 모델은 규칙이 못 잡은
  표현만 채움, 목록 밖 값 버림, 범위 클램프) → 폼 값 최우선. 모델 장애 시 규칙 이해로 폴백
  (`GILDLE_UNDERSTANDING=rules`로 끌 수 있음). 시간→거리는 1.2 m/s, 시간만 주면 목표=95%·상한=100%.
  ⑤ `POST /api/gildle/walk/plan`(응답 understood·source·target_m·max_m·options), `/routes/options`·`/routes/via`
  에도 고도 전달(일반 경로에도 편한 길 후보). ⑥ 웹 루프 시트를 "시간·거리로 돌아오는 산책 추천"으로 교체
  (자연어 입력·분·km·길 성격 칩·들를 곳 칩), 이해 요약 줄("40분 안에 · 2km · 편한 길 (AI가 이해)"), 편한 길
  하늘색·언덕길 주황, 구 `/loops` 칩 UI·`findLoops` 제거. ⑦ **"여름 그늘" → "그늘 모드"** 명칭 변경(웹 지도·
  산책 기록, Flutter 라벨 2곳; API 값 `summer_shade` 유지). ⑧ 경로 후보 아래 안내 문구 "업데이트가 안된 경우에는
  길이 조금 다를 수 있는 점 양해 부탁드리겠습니다." 운영 실측: "40분 2키로 편하게"→편한 길 2.08km 오르막 41m,
  "오르막 한 시간 반, 사료도"→언덕길 6.3km 오르막 434m·용품점, "사십 분쯤 나무 많은 데로"→규칙이 못 읽는
  "사십 분"을 모델이 40분으로 이해(첫 호출 7s는 모델 로드, 이후 2~3s). 테스트 gildle 237·전체 941.

- **Play 출시 준비(인증 완료 후, 사용자 "변경해야 하는 사항 다 변경 + 개인 회원가입, 필수 항목만")**:
  ① **버그 발견·수정 — 앱 토큰이 산책 API에서 전부 401**: `shared/security/require_user`가 aud `suvis-mova`만
  받아, 앱(aud `suvis-susu`)의 산책 저장·기록·푸시 토큰 등록이 운영에서 불가능했다. 두 aud를 모두 받게 수정.
  ② 인증 게이트웨이: `POST /auth/mobile/signup`·`/auth/mobile/login`(이메일·비밀번호만, 이메일 정규화, 8자↑,
  username은 UNIQUE라 `이메일앞_난수6`), `DELETE /auth/mobile/account`(모바일 토큰으로 본인 확인 → users 삭제,
  FK CASCADE → 모바일 세션 폐기, 웹 토큰은 401). ③ gildle `DELETE /api/gildle/me/data`(산책 기록·기기 토큰 —
  walks에 users FK가 없어 CASCADE로 안 지워짐). ④ 앱: 게스트 모드(스플래시가 항상 지도로, 기록·내 정보는
  로그인 안내, 산책 시작 시 로그인 요구), 로그인 화면에 이메일 로그인·가입(필수 동의 체크 + 약관·방침 링크,
  `url_launcher` 추가), 내 정보에 회원 탈퇴(확인 창)·정책 링크. ⑤ 웹: 개인정보처리방침 개정(산책 기록 저장,
  이메일 가입, 포그라운드 기록, 네이버·카카오 장소 검색·Firebase 반영, 09-28 시행), 계정 삭제 안내 페이지.
  ⑥ **노트북에서 AAB 빌드**: Flutter 3.47.5를 스크래치에, JDK 17·Android SDK를 `~/.cache/gildle-build`에 설치,
  `key.properties` 경로만 임시로 `/mnt/c/...`로 바꿔 빌드 후 원복 → `길들/gildle-release-20260928.aab`
  (targetSdk 36, 업로드 키 서명 확인). `flutter analyze` 0건·`flutter test` 통과. 도구가 바꾼
  `analysis_options.yaml`은 되돌림. ⑦ 스토어 아이콘 512·그래픽 1024×500 생성, 심사용 이메일 계정 생성(비밀번호는
  바탕화면 파일), 입력 가이드 `gildle/_docs/GILDLE_PLAY_CONSOLE_GUIDE.md`. 운영 E2E: 가입 201·중복 409·로그인
  200/401·앱 토큰 산책 저장 201·데이터 삭제 {walks:1}·탈퇴 204·탈퇴 후 로그인 401. **정정**: 처음에 "위치
  포그라운드 서비스 권한은 안 쓴다"고 답했으나 산책 중 화면 꺼짐 기록에 실제로 쓴다 — 권한 유지, Play 선언·
  시연 영상 필요로 정정. 파이썬 기본 UA는 Cloudflare 1010으로 막힌다(테스트 시 UA 지정).

### 오류·막힌 점
- 노트북 `node_modules`는 pnpm 11.21.0으로 설치돼 있어 `npx pnpm@10`이 스토어 불일치로 실패 —
  `npx -y pnpm@11.21.0`으로 add/remove.
- 삭제한 라우트를 `.next/types/validator.ts`가 계속 참조해 tsc가 실패 → `.next` 캐시 삭제 후 통과.
- 브라우저 실검증은 못 했다(노트북 하네스에 브라우저 없음) — `tsc`·eslint·`next build`까지만. **사용자가
  Vercel 변수 등록 후 실제 화면에서 탭→경로·루프·현재 위치·산책 추적을 확인해야 한다.**

- **프로덕션 첫 로드에서 지도 빈 화면**: Playwright 실측으로 지도 컨테이너 높이 0 — 네이버 SDK가 컨테이너에
  `position:relative` 등 인라인 스타일을 덮어써 `absolute inset-0`이 무효. `h-full w-full`로 고쳐 재배포,
  789px·타일 36장·두 번 클릭 경로(2.4 km) 확인. Client ID는 `.env.production`에 커밋(사용자 "알아서 작성").

- **웹 산책 기록 화면** `/gildle/walks`(앱의 기록·상세와 같은 내용): 누적 통계(횟수·거리·시간), 목록(날짜·거리·
  시간·계절·그늘 %, 20개씩 더 보기), 선택한 산책 경로를 네이버 지도에 그림. 비로그인은 로그인 안내. 지도 헤더
  "내 산책 기록"·저장 후 "기록 보기" 링크. `lib/gildle-api.ts`에 listWalks·getWalk·walkStats. 운영 walks 0건이라
  로그인 상태 목록은 실데이터로 미확인(빌드·비로그인 화면·API 401만 확인).

- **경로 후보 + 고를 이유 + 반려동물 장소**(사용자 "이쪽은 이런 장점, 저쪽은 이런 장점 — 골라서 산책", "펫샵·
  동물병원·용품점 들르면서"): 먼저 실측으로 봄가을·겨울이 사실상 최단거리임을 확인 — 가중치가 샘플 CSV
  (가로수 3건·위험구역 1건)만 보고 23만 간선의 tree_score(19.3% 유효)를 안 썼다. ① 봄가을 규칙에 수관 점수
  비례 감면(최대 60%, 휴리스틱 하한 0.28) + `/routes` 봄가을 기본 상한 최단×1.5. ② `POST /routes/options`:
  빠른 길(순수 거리)·그늘 많은 길(여름 가중·출발 슬롯)·푸른 길(수관 감면)을 최단×1.5 상한으로 나란히, 간선
  겹침 80%↑는 제거(추천 종류 우선 보존), 수치만으로 이유 문장(`route_option_describer`: 추가 거리·그늘·나무
  %·주요 도로 2개·장소 수, 을/를 조사), 모드별 추천 표시. ③ `KakaoPetPlaceAdapter`(gildle 전용, 키워드 4개·
  10분 캐시·반려동물 카테고리만 — 테스트로 "강아지떡볶이"가 동물병원으로 통과하던 버그 발견·수정)로 경로
  150m 안 동물병원·펫샵·용품점·애견카페. ④ `POST /routes/via`: 출발→장소→도착을 같은 성격으로.
  ⑤ 웹: 후보 색깔 선(선택 굵게·나머지 옅게, 선 클릭 선택), 후보 카드(라벨·추천·수치·이유), 🐾 장소 마커·
  칩(누르면 들렀다 가기 후보 추가). 운영 E2E: 사직동→종로 빠른 4.0km/푸른 4.5km(나무 71%)/그늘 5.2km(87%),
  장소 칩 → "빵댕잇 들렀다 가기" 4.8km. 응답 첫 요청 6s(그늘 데이터 적재)·이후 0.6s. gildle 테스트 225.
  앱(Flutter)은 이 노트북에 flutter가 없어 미적용 — 같은 API로 후속.

### 산출물
- 커밋: 오전 타일 교체(프론트 2차 묶음) + 오후 네이버 SDK 재작성 + 컨테이너 높이 수정 + env + 산책 기록 화면
  + 경로 후보·반려동물 장소.

---

## 2026-09-27

### 작업 내용 (밤 — 아키텍처 감사 후속: 인터랙터의 HTTPException 제거)
- 저장소 전체 헥사고날 감사(사용자 요청, `[P]` 09-27)에서 `WalkInteractor`·`PushTokenInteractor`가
  `HTTPException`을 직접 던지는 것(suvisdev/CLAUDE.md §K 금지)이 잡혔다 — 둘 다 09-22·09-27에 내가 쓴 코드.
  `apps/gildle/app/errors.py`(`WalkValidationError`·`WalkNotFoundError`·`PushTokenValidationError`)로 바꾸고
  라우터가 400/404로 변환. 테스트는 앱 예외를 기대하도록 수정, gildle 225 passed. 남은 위반은 mova
  `games_interactor`(HTTPException 7곳)·`whoami_router`(viewer ORM 직접 import) — 기록만.

 · 아이콘·스플래시 · graph-edges 메모리 · 릴리스 AAB)
- 사용자: "앱 이름도 susu 말고 gildle로", 그리고 목록 2번(`scored_edges.json` DB 이전)부터 콘솔 등록
  전까지 완성도 올리기. **DB 이전은 실측 뒤 보류 판단**: 경로 탐색(A*)은 어차피 메모리 그래프가
  필요해 DB로 옮겨도 RSS가 줄지 않고, uvicorn 워커도 1개라 "워커 수만큼 복제" 우려는 해당 없음.
  대신 실제 낭비였던 **graph-edges용 원본 dict 23만 건 이중 캐시**를 없앴다(아래).

### 수정/구현 (저녁)
- **개명** `susu/` → `gildle/`(`git mv`), pubspec `name: gildle`·설명, 테스트 import, web manifest,
  README, 루트 CLAUDE.md(구조·명령·워크로그 표)·`suvisdev/CLAUDE.md`·`_docs/README.md`·ponytail 스킬,
  `gildle/_docs/*`의 경로. 과거 워크로그·하네스 문서 본문의 "susu"는 역사라 그대로 둠. Windows 빌드
  복사본도 `C:\Users\suteagy\gildle-build\gildle`로 교체(구 `susu` 폴더 삭제).
- **런처 아이콘**: `assets/icon/{icon,icon_fg}.png`를 Pillow로 생성(초록 `#16A34A` 라운드 배경 + 흰
  산책길 곡선·출발점·warm 도착점·나무). 첫 버전은 `ImageDraw.line(joint=)`가 촘촘한 점열에서 털처럼
  갈라져 원판(디스크) 연속으로 그리는 방식으로 교체. `flutter_launcher_icons` 0.14.4로 mipmap 5종 +
  adaptive(`mipmap-anydpi-v26`, 전경은 안전영역 66% 축소본) 생성. 기본 Flutter 아이콘은 Play 심사
  전에 반드시 바꿔야 했던 항목.
- **스플래시**: Suvisdev 인트로 영상(4~5초 대기) 제거 → 세션 확인 후 즉시 전환하는 초록 정적 화면.
  `video_player` 의존성·`assets/videos/intro.mp4` 삭제. 네이티브 스플래시 `launch_background.xml`
  (drawable·v21)을 `@color/gildle_launch`로.
- **graph-edges 이중 캐시 제거**(`route_router.py`): `_get_scored_edges_raw`(원본 dict 23만)와
  `_load_scored_edges`(RouteEdge 23만)를 둘 다 들고 있었다. bbox 필터·격자 솎기를 RouteEdge로 하고
  응답 최대 2만 건만 `_edge_to_dict`로 직렬화. 로컬 TestClient 실측(ru_maxrss): graph-edges+routes
  호출 뒤 **716MB → 497MB**. 프로덕션 파드는 예열 후 VmRSS 1.73GB였음(gildle 몫 ≈590MB).
- `.env`·`.env.example`에 `GILDLE_APP_MIN_VERSION`·`_LATEST_VERSION`·`_STORE_URL`(기본 1.0.0).
- **릴리스 AAB**: `flutter build appbundle --release --dart-define-from-file`(key.properties 서명,
  Gradle 104초) → **75.6MB** `바탕화면/길들/gildle-release-20260927.aab`. 디버그 APK도 개명·아이콘·
  스플래시 반영본으로 재빌드해 `gildle-debug-20260927.apk` 교체.
- **배포**: graph-edges 캐시 제거 롤아웃 후 프로덕션 예열 VmRSS **1.73GB → 1.51GB**, graph-edges·
  routes·app/version 정상. flutter analyze 0 issues.

### 작업 내용 (오후 — 산책 중 · 기록 · 내 정보 화면 · 토큰 갱신 · push-tokens · app/version · APK)
- 오전 작업 배포·커밋(`0457d0d`) 뒤 사용자 지시로 "산책 중 화면부터 쭈욱": ① 산책 중 → ② 기록·상세·
  내 정보 탭 → ④ 실기기용 디버그 APK → ⑤ `app/version` → ③ FCM 토큰 등록(백엔드 테이블·API 포함).
  ⑥ `scored_edges.json` DB 이전은 착수하지 않았다(별도 세션 분량).

### 수정/구현 (오후)
- **access 토큰 자동 갱신** — 산책은 10분(access TTL)을 넘기므로 필수였다. `AuthSession.refresh()`
  (`POST /auth/mobile/refresh`, 로테이션된 두 토큰 저장, 동시 401은 한 번만 재발급, 401이면 세션
  삭제·네트워크 오류면 보존) + dio 인터셉터가 401에서 refresh 후 같은 요청을 **1회** 재시도
  (`extra['retried']` 가드). 09-22 auth.dart 주석의 "refresh 미구현" 해소.
- **산책 중** `walk_session_controller.dart`·`walk_screen.dart`: geolocator `AndroidSettings`
  (best, distanceFilter 5m, **포그라운드 서비스 알림** — 화면이 꺼져도 추적, 백그라운드 위치 권한은
  불필요) 스트림, 정확도 30m 초과 점 폐기·2m 미만 이동 무시, 1초 타이머로 경과. 지도에 계획 경로(회색
  점선)·걸은 길(초록) 오버레이, 거리·시간·페이스 카드. 종료 확인 → 점 2개 미만이면 "버리기/그래도
  저장" → `POST /walks`(5,000점 초과는 등간격 솎기, `season_mode`=계획 모드, `avg_shade_score`=계획
  경로 그늘 비율) → 상세 화면으로 교체. `PopScope`로 추적 중 뒤로가기는 종료 확인으로.
- **기록·상세·내 정보** `walks_screen.dart`(통계 카드 + 목록, 당겨서 새로고침, autoDispose
  FutureProvider라 탭 진입마다 재조회)·`walk_detail_screen.dart`(폴리라인 fitBounds + 수치 + 삭제
  확인)·`profile_screen.dart`(누적 통계·로그아웃). `main.dart` `HomeScreen`을 3탭 `NavigationBar` +
  `IndexedStack`(탭 전환에도 지도 상태 유지)으로. 지도 하단 카드에 "산책 시작/이 길로 산책 시작".
  공용 `format.dart`(StatTile·km·시간·날짜·모드 라벨).
- **매니페스트**: `FOREGROUND_SERVICE`·`FOREGROUND_SERVICE_LOCATION`(Android 14 필수)·
  `POST_NOTIFICATIONS`.
- **백엔드 `push_tokens`**(`20260927_0001`, token 유일키, users FK 없음) — 엔티티(platform
  android|ios 검증)·출력 포트(upsert/delete)·인터랙터·PG 저장소·`POST/DELETE /api/gildle/push-tokens`
  (`require_user`, 204). 남의 토큰 삭제는 조용히 무시(멱등). **발송 코드는 없다** — 보낼 알림이 정해지면
  출력 포트를 더한다(서비스 계정 키 `~/secrets/gildle-fcm.json`).
- **`GET /api/gildle/app/version?platform=android`** — `GILDLE_APP_MIN_VERSION`·`_LATEST_VERSION`·
  `_STORE_URL` 환경변수(기본 1.0.0). 앱은 `package_info_plus`로 자기 버전을 읽어 min 미만이면 닫을 수
  없는 안내(스토어 링크는 등록 후 `store_url`로). 확인 실패는 막지 않는다.
- **앱 FCM** `app_services.dart`: 홈 진입 시 `Firebase.initializeApp` → 권한 → `getToken` → 등록,
  `onTokenRefresh` 재등록, 로그아웃 때 해제(best-effort). 초기화 실패는 로그만(푸시 없이 동작).
- 테스트: 인터랙터 3건(asyncio)·라우터 3건 → gildle **239 passed**, ruff·mypy·lint-imports 통과.
  Flutter analyze 0 issues, 테스트 3/3(Windows 복사본).
- **배포·마이그레이션(오후)**: `deploy.sh --external-db --build` 롤아웃 → 파드에서 `alembic upgrade head`
  (`20260922_0002 → 20260927_0001`, `push_tokens` 생성). 프로덕션 `app/version` 200(1.0.0), `push-tokens`
  무인증 401 확인. 디버그 APK 241MB → 바탕화면 `길들/gildle-debug-20260927.apk`(Gradle 55초, Windows 복사본).
  **실기기 확인은 아직** — 폰에 설치해 지도 인증·위치 권한·산책 저장까지 봐야 한다.

### 작업 내용 (앱 지도 화면 · susu 정리 · `/routes` 점검 · 수관 데이터 · A* 모드별 배율)
- 사용자 지시 순서대로 ①Flutter 지도 화면 → ②susu를 gildle 앱으로 정리 → ③`/routes`
  점검 → ④나무 데이터 보강 → ⑥모드별 A* 휴리스틱. ⑤그늘 실측(사진)은 앱이 나온 뒤로 미룸.
- 이 세션까지 gildle 앱 화면은 0개였고(09-22 기준), 백엔드는 출시 준비가 끝난 상태였다.

### 수정/구현
- **① 지도 화면** `susu/lib/features/gildle/` — `domain/{season_mode,geo_point}.dart`,
  `data/{gildle_route_api,models/route_result,models/loop_candidate}.dart`,
  `presentation/{map_controller,gildle_map_screen}.dart`. 네이버 지도(flutter_naver_map 1.4.4,
  Windows pub 캐시 소스에서 시그니처 확인) 위에 탭 2번으로 출발·도착 → `POST /api/gildle/routes`,
  계절 모드 SegmentedButton, 여름은 구간별 그늘을 warm(햇빛)↔accent(그늘)로 색 보간한
  `NMultipartPathOverlay`, 루프 버튼(거리 슬라이더 → `POST /api/gildle/loops`, 후보 칩),
  현재 위치 버튼(geolocator → 출발지), 하단 카드(거리·예상 분·그늘%·밤 안내·OSM 저작자 표시).
  riverpod `StateNotifier`는 기존 mova 컨트롤러와 같은 꼴, 에러 문구는 auth.md §6대로 짧게.
- **② susu 정리(A안)** — `features/mova`·`features/media`·`stopwatch_page.dart`·
  `naver_config.dart`(미사용, Client ID는 dart_defines) 삭제, `main.dart`를 `GildleApp` +
  `HomeScreen`(지도 + 로그아웃)으로 재작성, `gildleLightTheme/DarkTheme` 적용, 로그인 화면
  문구 '길들'. `image_picker` 의존성 제거, 매니페스트 CAMERA 권한 삭제·`ACCESS_FINE/COARSE_LOCATION`
  추가(백그라운드 위치는 Play 정당화가 필요해 안 넣음). 인트로 영상 스플래시는 그대로 둠.
  낡은 테스트 2개(`MyApp` 참조 오류·스톱워치) 삭제 → `test/geo_point_test.dart` 3건.
- **③ `/routes` 점검 — 결함 2개 수정** (`route_router.py`)
  - 여름 모드가 `/routes`에선 그늘 조회 없이(나무 점수 폴백) 돌았고 응답에 `shade_ratio`
    등이 없었다 — 앱은 좌표만 알기 때문에 이 엔드포인트가 `/navigate`와 같아야 한다.
    `_plan_route()`로 공통화(④ 제약·③ 시간 의존·기본 분기 전부), `RouteRequestSchema`에
    `departure_time`·`max_detour_ratio` 추가, 두 엔드포인트 모두 `length_m` 응답.
  - **좌표 응답이 간선 저장 방향을 무시했다**: 간선을 양방향으로 색인하면서 항상 `from_coord`를
    써서 역방향 간선에선 상대편 끝점이 나갔다(경로 a→b→c가 (a,b)·(c,b)로 저장돼 있으면 좌표가
    a,c,b). `_path_coordinates()`가 진행 방향 끝점을 고르게 수정, `/loops`도 공용(마지막
    도착 좌표까지 넣어 루프가 닫힘). 실데이터 표본 2경로에서 역방향 간선 54개 — 웹 지도의
    폴리라인이 그동안 국소적으로 되돌아가고 있었다는 뜻.
- **④ 나무 데이터 보강** — `scripts/fetch_osm_canopy.py`(Overpass: wood·forest·park 폴리곤
  `out geom`, tree_row 선; 미러 순환·백오프는 buildings 수집과 동일, UA 없으면 406) +
  `scripts/enrich_tree_scores.py`(간선을 **선분**으로 보고 shapely STRtree로 숲 1.0 · 공원 0.6 ·
  나무열 15m 0.9 · 나무 점 25m 밀도(12m 간격=만점), 기존 값을 하한으로 max → 멱등, 원본은
  `graph_cache/`에 백업 후 임시 파일→`os.replace`). 테스트 `test_enrich_tree_scores.py` 4건.
- **가중치 규칙 변경** `RouteWeightCalculator` 여름: `shade = max(건물 그늘, tree_score)`.
  이유: `shade_scores.json`이 전 간선(233,945)을 0%로라도 덮고 있어 tree_score 폴백이 **한 번도
  안 걸렸고**, 건물 없는 산길·공원길이 "완전 햇빛"으로 계산됐다. 라우터·루프의 그늘 통계도 같은 정의.
- **⑥ 모드별 A* 배율** — `RouteWeightCalculator.min_multiplier(mode)`(봄가을 0.7, 여름·겨울
  1.0)를 포트 `find_shortest_path(..., heuristic_scale=)`로 넘긴다(networkx·PG·Fake는 받고
  무시). `execute_bounded`의 순수 거리 탐색은 1.0, `scaled(t)`는 모드 하한, 루프 되밟기 페널티도
  하한 그대로. `verify_routing_equivalence.py`를 모드별 측정으로 확장(`astar` 기본 0.7 vs
  `astar_mode`).

### 오류·막힌 점
- `flutter test`는 `\\wsl.localhost` 경로에서 09-23과 같은 잠금 대기로 실패 →
  `C:\Users\suteagy\gildle-build\susu`로 rsync 후 실행(3/3 통과). `flutter analyze`는 WSL
  경로에서도 된다(0 issues). `pub get`이 Windows 데스크톱 플러그인 심볼릭 링크 오류로 exit≠0이지만
  Android와 무관, `analysis_options.yaml` 자동 수정은 되돌림.
- 노트북엔 pytest가 없어 스크래치 `uv venv`(requirements에서 torch 계열 제외 + shapely·lightgbm)로
  gildle 233 passed. `ruff format apps/gildle`이 안 건드린 파일 4개(walk_orm 등)까지 재포맷해
  `git checkout`으로 되돌림 — 포맷은 편집한 파일에만 걸 것.
- Overpass `out count;`는 406/빈 응답 — UA 헤더 + `out ids;`로 대체. 공원 조회는 연속 호출 시
  일시 실패(레이트리밋)했고 수집 스크립트의 5초 간격·백오프로는 문제 없었다.

### 데이터
- 수관: wood 1,982 · forest 906 · park 3,124 폴리곤 + tree_row 445 선(열린 고리 168 건너뜀) →
  `seoul_canopy_osm.json` 4.8MB(커밋 대상, trees·parks와 같은 취급).
- `scored_edges.json` 보강(12:40 KST, 18초): tree_score>0 **10,355(4.43%) → 45,256(19.34%)**,
  ≥0.5 42,869, dog_friendly>0.3 74,843 → 128,085(공원 150m 판정을 중심점→폴리곤 거리로 바꾼 효과),
  변경 75,009. 표본: 남산 0.2→1.0, 서울숲 0→1.0, 북한산 0→1.0, 여의도공원 0.2→0.6, 강남역 0 유지,
  광화문(기존 1.0) 유지. 백업 `graph_cache/scored_edges.before-tree-enrich-20260927.json`.
  **파드 hostPath라 즉시 서빙** — 프로덕션 `graph-edges` 남산 구역 19간선 전부 1.0 확인.
- A* 모드별(실데이터 60쌍, seed 3, 보강 **전** 데이터, 불일치 0):
  | 모드 | 배율 | 방문 비율(다익스트라=1) 0.7 → 모드 | 질의당 초 다익/0.7/모드 |
  |---|---|---|---|
  | 봄가을 | 0.7 | 0.415 → 0.415 | 0.284 / 0.156 / 0.157 |
  | 겨울 | 1.0 | 0.415 → **0.191** | 0.271 / 0.150 / **0.070** |
  | 여름 | 1.0 | 0.861 → 0.803 | 0.392 / 0.424 / 0.390 |
  여름이 여전히 약한 이유는 가중치가 거리의 1~5배라 직선거리 하한이 느슨해서다(09-22 진단과 같음).
  **보강 후 재측정**(같은 60쌍): 여름 방문 비율 0.7 배율 0.787 → 모드 배율 **0.696**(질의당 0.385→0.342s),
  봄가을·겨울은 동일 — 그늘 간선이 늘어 가중치가 거리에 가까워진 만큼 휴리스틱이 조여진 것.

### 산출물
- susu: 위 신규·삭제 파일, `pubspec.yaml`·`AndroidManifest.xml`·`auth.dart`·`main.dart`.
- suvisdev: `route_router.py`·`route_schema.py`·`route_graph_port.py`·다익스트라/networkx/PG
  어댑터·`calculate_route_interactor.py`·`plan_loop_interactor.py`·`route_weight_calculator.py`·
  `verify_routing_equivalence.py`·신규 스크립트 2·테스트(navigate 2건·다익스트라 2건·가중치 5건·
  enrich 4건). ruff·mypy·lint-imports 통과.
- **배포 완료(오후, 사용자 지시)**: `./k8s/deploy.sh --external-db --build` — backend·auth 롤아웃
  성공, 프로덕션 `/routes` 여름 모드가 `length_m`·`shade_ratio`·`edge_shades`·`night`를 반환하는 것 확인.
- 남은 것: 산책 중(위치 추적·기록 저장 `POST /walks`)·기록 목록·FCM 토큰 화면, 실기기 APK 확인,
  ⑤ 그늘 실측(앱 이후).

## 2026-09-22

### 작업 내용 (앱 출시 준비 — walks API · 건물 그늘 파이프라인 복구)
- 앱 출시를 **gildle만** 하기로 결정(mova는 TMDB 약관의 AI 학습 조항이 별도 서면
  계약을 요구 — gildle은 OSM/공공데이터 기반이라 그 리스크가 없다).
- gildle이 **stateless 경로 계산기**라 사용자가 다시 열 이유가 없다는 문제를
  `walks` API로 해결하고, 코드만 있고 한 번도 돌지 않았던 **건물 그늘 계산**을
  복구했다.

### 수정/구현
- **`walks` API 신규** (`/api/gildle/walks`) — 저장·목록·상세·삭제·통계 5종.
  전부 `require_user`이고, **남의 기록은 403이 아니라 404**로 막는다(id 존재
  여부를 흘리지 않기 위해 — 08-07 mova 마이페이지 IDOR 수정과 같은 기준).
  레이어: ORM·엔티티·DTO·포트 2종·PgRepository·Interactor·스키마·라우터·provider.
  alembic `20260922_0001`(테이블 `walks` + 복합 인덱스). **gildle 197 passed.**
  - `user_id`에 FK를 걸지 않았다 — `users`는 다른 앱 테이블이고 참조하면 앱 경계를
    넘는 결합이 생긴다. 소유권 검사는 유스케이스가 한다.
  - 경로 좌표는 상한 5,000점에서 **거부가 아니라 절단** — 기록을 통째로 잃는 편이
    더 나쁘다.
- **건물 데이터 출처를 OSM → 브이월드로 교체**. `scripts/fetch_vworld_buildings.py`
  신규(`fetch_osm_buildings.py`와 **같은 형식**으로 저장해 하위 파이프라인 무수정).

### 오류·막힌 점
- **건물 그늘이 한 번도 계산된 적이 없었다**: `compute_shade_scores.py`는 08-27
  커밋인데 서빙 데이터 `scored_edges.json`은 **08-25 생성**이라 `shade_score` 필드
  자체가 0건이었다. 건물 데이터 파일(`seoul_buildings_osm.json`)도 없었다. 즉
  "그늘 우선 경로"가 `tree_score` 폴백으로만 돌고 있었다. 라우터
  (`_load_shade_scores`)는 mtime 캐시까지 갖춘 채 파일만 기다리고 있었다.
- **JSONB가 sqlite에서 안 돼 gildle 테스트 31건이 깨졌다** — 기존 테스트가
  sqlite in-memory로 `create_all`을 한다. `JSON().with_variant(JSONB, "postgresql")`로 수정.
- `slots=True` dataclass에 `__dict__`를 써서 테스트 2건 실패 → `dataclasses.replace`로 수정.

### 데이터
- **건물 높이 출처 비교(실측)**:
  | 출처 | 높이/층수 보유율 |
  |------|------------------|
  | OSM `height` 태그 | **10.6%** (테스트 영역 1,147동) |
  | 브이월드 `LT_C_SPBD.gro_flo_co` | **83.6%** (표본 5,000동, 서울 5개 지역) |
  - 지역별: 관악 100% · 강남 96.9% · 여의도 93.8% · 종로 89.6% · 노원 37.8%
    (노원은 아파트 단지 부속 건물이 0으로 들어간 것으로 보인다)
- **높이는 `heit`가 아니라 층수를 써야 한다** — 건축HUB 건축물대장 공식 가이드
  (HWP 원문 확인)의 응답 예시조차 `<heit>0</heit>`이고 `<grndFlrCnt>2</grndFlrCnt>`만
  채워져 있다. 층당 3.0m 환산(OSM `building:levels`와 같은 계수).
- 브이월드 API: `size` 상한 **1,000**(1,001 이상 오류), `geomFilter=BOX(minx,miny,maxx,maxy)`,
  `domain` 파라미터 필수(인증키 발급 시 등록한 도메인).

### 산출물
- 신규: `apps/gildle/adapter/outbound/orm/walk_orm.py` · `domain/entities/walk_entity.py`
  · `app/dtos/walk_dto.py` · `app/ports/{output/walk_repository,input/walk_use_case}.py`
  · `adapter/outbound/pg/walk_pg_repository.py` · `app/use_cases/walk_interactor.py`
  · `adapter/inbound/api/{schemas/walk_schema,v1/walk_router}.py` · `dependencies/walk_provider.py`
  · `scripts/fetch_vworld_buildings.py` · `tests/app/test_walk_interactor.py`
  · `alembic/versions/20260922_0001_create_gildle_walks.py`
- 문서: `apps/gildle/_docs/GILDLE_APP_API_PLAN.md` · `susu/_docs/GILDLE_APP_RELEASE_PLAN.md`
  · `susu/_docs/GILDLE_APP_SETUP_GUIDE.md`
- 프론트: `suvis/app/gildle/privacy/page.tsx`(위치정보 처리 고지 — Play 필수 제출물)
- **완료(저녁)**: 브이월드 건물 약 80만 동 수집 → 그늘 13슬롯 계산 완료, 그늘 구간
  4.4%→39.9%. 마이그레이션 `20260922_0001` **노트북 프로덕션 적용**(`walks` 테이블
  확인), walks API 401 가드 실측. `test_compute_shade_scores.py`는 서빙 이미지에
  shapely가 없어 `importorskip`으로 파드에서 스킵.
- **남은 것**: Flutter 지도 화면(네이버 Client ID 적용됨), `/routes` `summer_shade`
  모드·좌표 응답, Firebase `google-services.json`, 나무 데이터 보강(`tree_score` 4.4%).

### 작업 내용 (저녁 — 경로 탐색 자체 구현 · 검증 하네스 · 알고리즘 설계)
- 사용자 지적 "길들은 API로만 돼 있다"에 대한 답으로, 실제로 남의 것인 부분(networkx
  최단경로)을 걷어내고 산책 앱에 필요한 탐색을 직접 구현했다. 설계·모델 삽입 지점·
  하네스 자리는 `apps/gildle/_docs/GILDLE_ROUTING_ALGORITHM.md`.
- 사용자 결정: 경로 탐색 ①~⑤ 전부, 모델은 B(건물 높이 보간)→A(간선 선호 학습)→D(결빙 예측).

### 수정/구현
- **합성 검증 하네스** `scripts/verify_pipeline_synthetic.py` + pytest: 정답을 아는 3×5
  격자 세계(특정 거리 남쪽에만 40m 건물)로 태양→그림자→그늘→가중치→경로를 실제 코드로
  끝까지 돌린다. 7/7(로컬), 파드는 shapely가 없어 기하 2건 스킵·규칙 5/5.
  케이스 2 실측: 같은 세로 거리가 09시 0.93 → 15시 0.06 — 시간 의존(③)의 근거.
- **자체 다익스트라·A\*** `dijkstra_route_graph_adapter.py`: 포트 시그니처 유지, 방문
  간선만 가중치 평가(현 설계), A\* 휴리스틱 0.7×직선거리(봄가을 감면 때문에 0.7 이하여야
  admissible). 실데이터 23만 간선 200쌍 `verify_routing_equivalence.py`: **불일치 0**.
- **③ 시간 의존 그늘**: 포트에 `find_shortest_path_time_dependent`(기본은 시각 무시)
  추가, 다익스트라가 노드별 누적 거리를 동반. `/navigate` 여름 낮은 걸은 거리→슬롯(1.2m/s,
  30분 반올림)으로 간선마다 그 시각의 그늘.
- **④ 제약 최단경로** `execute_bounded`: 가중치 `거리 + t·(모드가중치−거리)`의 t를
  이분탐색(8회)해 길이 ≤ (1+비율)·최단. `/navigate max_detour_ratio`.
- **⑤ 루프** `plan_loop_interactor.py` + `POST /gildle/loops`: 방위각 12방향 × 정삼각
  경유점(D/3), 되밟기 ×3 페널티, 목표 ±35%·되밟기·그늘로 점수. 최근접 노드는 라우터의
  그리드 색인을 콜백으로 주입(중복 구현 안 함).
- DI csv 모드 `AStarRouteGraphAdapter`로 교체. gildle **212 passed**(파드).

### 오류·막힌 점
- A\* 방문 수 테스트가 격자 반대편 모서리에선 다익스트라와 같았다(둘 다 전 노드) —
  안쪽 목적지로 바꿔야 차이가 난다. 모듈 캐시를 어댑터 인스턴스가 공유해 `last_visited`는
  탐색 직후 읽어야 한다.
- 시간 의존 테스트 첫 시나리오는 시간 의존 경로가 직행보다 비싸게 설계돼 실패 — 코드가
  아니라 시나리오 오류. "출발 슬롯엔 직행이 그늘, 뒤 슬롯엔 나머지가 그늘"로 바꿔 통과.
- 실측: 순수 Python 다익스트라는 networkx보다 느리고(0.39→0.53s/질의) A\*의 가지치기는
  13%뿐. 교체 근거는 표현력(③④⑤)이지 속도가 아님을 문서에 남김.
- 파드에 `kubectl cp`한 코드는 uvicorn에 반영되지 않는다(테스트만 가능) — 배포는 `--build`.

### 작업 내용 (밤 — 모델 B·A·D, 루프 길이 보정, 배포)
- 사용자 결정: 모델 B→A→D 전부 진행, 경로 탐색 ①~⑤ 전부. B는 "둘 중 정확한 쪽,
  앙상블이 낫다면 앙상블".
- **모델 B(건물 높이 보간) 채택 — kNN+LightGBM 앙상블**: 홀드아웃 143,008동 MAE
  **3.41m**(현행 격자 중앙값 4.60m), ±1층 적중 78.2%(71.1%). 후보 6종 비교표는
  `GILDLE_ROUTING_ALGORITHM.md` §2.1. 가장 단순한 kNN(3.46m)이 11특징 GBM(3.62m)을 이긴 게
  핵심 발견 — 높이는 동네가 결정한다. 결측 84,665동 예측 `height_model_pred.json` 생성,
  `compute_shade_scores.py`가 사이드카로 적용. **그늘 재계산은 미실행**(집에서).
- **모델 A(간선 선호)**: `train_edge_preference.py` 파이프라인 + 합성 검증(가상 사용자
  40건 → 그늘 계수 +0.93). 실데이터 0건이라 학습은 대기.
- **모델 D(결빙)**: 사고 CSV 12행·DEM 없음 → 보류, 착수 조건 문서화.
- **루프 길이 보정**: 운영 실측에서 목표 1,500m에 1,899~2,000m(정삼각 경유점이 도로
  굴곡을 무시). 1차 후보 중앙 길이로 변 길이를 한 번 보정하는 2패스 → 1,427~1,455m /
  3,000m 목표 2,974~3,003m, 되밟기 ≤4%.
- 운영 실호출(`/api/gildle/loops`·`/navigate max_detour_ratio`) 정상. gildle **214 passed**.

### 오류·막힌 점
- `/gildle/loops`가 404 — 라우터가 `/api` 접두사 아래 마운트돼 있었다(main.py).
- 모델 스크립트가 `compute_shade_scores`의 `project_to_meters`를 import하면 그 모듈 상단의
  shapely까지 딸려와 파드에서 죽는다 → 두 줄짜리 투영 함수를 스크립트에 직접 둠.
- L1 GBM은 MAE는 좋지만 "정확히 그 층" 적중률은 중앙값에 졌다(64.5% vs 70.7%) — 층 단위
  반올림을 붙이니 76.6%로 역전. 정답이 이산(층수×3m)이면 예측도 이산화해야 한다.

---

### 작업 내용 (늦은 밤 — 그늘 13슬롯 재계산, 모델 B 반영)
- 밤 세션이 남긴 배치(`compute_shade_scores.py`)를 노트북 `.venv`(shapely 있음)로 실행.
  로그 `높이 모델 예측 적용 84665동 · 격자 중앙값 보간 0동` — 모델 B 사이드카가 결측
  전량을 덮어 격자 중앙값 폴백은 한 동도 안 탔다. 233,945간선 × 13슬롯, **약 18분**
  (20:34→20:52, 단일 코어 100%, RSS 2.3GB).
- 파드는 `apps/gildle/data`를 hostPath로 마운트(`k8s/backend.yaml`)하므로 새 파일이
  그대로 보인다(파드에서 `ls -la` 실측 mtime 일치). 라우터 mtime 캐시가 다음 요청에
  다시 읽는다 — **재배포 없음**. 운영 `/api/gildle/navigate`(summer_shade, 15:00) 실호출
  정상(13노드 경로, shade_ratio 0.54, edge_shades 12).

### 데이터 (전후 비교 — 격자 중앙값 보간 vs 모델 B 예측)
- 비교 대상: 16:28 산출물(결측 높이 = 250m 격자 중앙값) vs 20:52 산출물(결측 높이 =
  kNN+LightGBM 예측). 간선 집합 동일(233,945).
- **값이 바뀐 간선 31,647 / 233,945 (13.5%)**. 슬롯별 평균 그늘은 전 슬롯에서
  +0.1~0.4%p, 그늘 0% 간선 비율은 −0.1~0.3%p, 100% 간선은 +0.1~0.5%p — 방향은
  일관되게 "조금 더 그늘"이다(모델 B가 격자 중앙값보다 결측 건물을 약간 높게 본다는
  뜻). 대표 슬롯: 12시 0% 60.1→60.0 · 평균 20.4→20.5, 15시 0% 49.9→49.7 · 평균
  29.2→29.4, 18시 0% 24.3→24.0 · 평균 65.7→66.1.
- 해석: 두 방식 다 "결측 건물의 높이 추정"이라 **분포 차이는 작은 게 정상**이다.
  모델 B의 효과는 전역 통계가 아니라 저층·고층 혼재 격자에서 동 단위로 갈리는
  13.5% 간선에 있고, 그게 실제로 맞는지는 전역 지표로는 알 수 없다 → 남은 검증은
  여전히 **실측(사진 5곳)**이다(NEXT_STEPS 내일 1번).
- 이전 산출물은 세션 스크래치에만 백업했고(`shade_scores.before.json`, 휘발) 저장소엔
  넣지 않았다 — 필요하면 `--height-model-pred /nonexistent`로 재생성 가능.

## 2026-09-11

### 작업 내용 (전체 리뷰 후속 — gildle 몫: DoS 상한 + 요청당 재구축 제거)
상세는 `suvisdev/_docs/CODE_REVIEW_2026-09-11.md` 처리 현황 참고.
- **`GET /graph-edges` 상한**: bbox 없는 호출이 23.4만 간선(80MB급) 전체를
  무인증 반환하던 것 → bbox 4개 필수화(지도는 항상 보냄) + 응답 20,000건
  절대 상한.
- **요청당 재구축 제거**: ① nx 그래프를 edges 리스트 동일성 키로 캐시
  ② 최단경로 weight를 전 간선 사전 대입(233k회) 대신 nx 콜러블로 — 방문한
  간선만 평가되고, 캐시된 공유 그래프를 변이하는 동시성 문제도 함께 해소
  ③ 최근접 노드 전수 스캔 → 0.005° 그리드 인덱스(+2링 여유 탐색)
  ④ edge_lookup·그늘 슬롯별 lookup 캐시 ⑤ 가로수·결빙 CSV find_all mtime 캐시.
- 레거시 `session.query(...).delete()` → 2.0 `delete()` 문. 미사용 프로바이더
  3종(get_walk_graph_source/port·get_import_tree_segment_use_case) 제거.

### 오류·막힌 점
- 없음. 검증: gildle 테스트 198 passed(전 스위트 784의 일부), ruff·mypy 청정.
- postgres 모드(요청당 create_engine·세션 미close 누수)는 현재 csv 모드라
  잠복 — 리뷰 잔여 목록에 남김.

### 산출물
- 당일 저녁 일괄 커밋·배포(커밋 해시는 WORK_LOG_MAINPAGE 09-11 참고).
  리뷰 문서 처리 현황에 통합 기록.

---

## 2026-08-28

### 작업 내용
- gildle에 필요한 외부 API 키 전수 조사 — 키가 필요한 건 지오코딩용
  `KAKAO_API_KEY`(카카오 로컬 API) 하나뿐임을 확인. Overpass·Nominatim·
  OSM 타일·태양 위치(자체 수식)는 전부 무키. 지오코딩은 가로수 CSV
  임포트의 좌표 결측 보완 fallback에만 쓰이고, 미설정 시 경고 로그 후
  스킵이라 경로 탐색·지도에는 무영향(기존 방어 확인).
- 카카오 개발자 콘솔에서 기존 앱(카카오 로그인용)의 카카오맵 사용 설정
  ON(사용자 수행) 후 실호출 검증.

### 수정/구현
- `suvisdev/.env.example`: `KAKAO_API_KEY` 등재 + 용도·카카오맵 활성화
  조건·미설정 영향 주석.
- `suvisdev/.env`(커밋 대상 아님): 같은 키 추가(REST API 키 —
  `KAKAO_CLIENT_ID`와 동일 값), 카카오 키 5종 블록을 "콘솔 어디서 발급·
  어느 앱이 쓰는지" 주석으로 재정리. EC2 `.env`에는 아직 미반영(선택).

### 오류·막힌 점
- 없음.

### 데이터
- 실호출 검증: 로컬 API 주소 검색("여의도동") HTTP 200 + 좌표
  (126.9301, 37.5267) 반환 확인. `check_env_drift.py` 신규 드리프트 없음.

### 산출물
- 이 항목과 함께 커밋(`chore(gildle)`).

## 2026-08-27

### 작업 내용
- **여름 그늘 경로(`summer_shade`) 신규** — 뚜벅(ttubeok.com) 방식: 출발
  시각의 태양 위치 + 건물 그림자 + 가로수를 결합해 그늘 위주 경로 안내.
  사용자 결정: 정밀도 C(그림자 폴리곤 사전 계산) + 그늘 강력 우선(햇빛
  구간 최대 5배 페널티, 경로는 항상 반환). 계획서:
  `suvisdev/_docs/plans/2026-08-27-gildle-summer-shade.md` (Task 1~8 완료).
- 밤 처리(사용자 요청 반영): 고정 시간 경계가 아니라 **요청 시각의 실제
  태양 고도**(자체 수식, 외부 API 불필요)로 판정 — 고도 ≤ 0°면 그늘 계산
  제외하고 최단 경로 + `night: true`. 일출·일몰이 계절 따라 자동 연동.
- 정확도 개선(사용자 질문 "그림자 계산 모델" 논의 반영): 서울 전역 실측
  에서 건물 높이 태그 결측 75.7% 발견 → `height_known` 플래그 재수집 +
  **250m 격자 중앙값 imputation**(실측 66,273동 학습, 결측 179,612동 추정,
  상한 150m). 음수 높이(-6.0) 오염값도 수집 단계 방어. 딥러닝 세그멘테이션은
  "촬영 시각 그림자만 학습 가능"이라 시간대별 예측 목적과 안 맞아 기각.

### 수정/구현
- 도메인: `sun_position.py`(NOAA 근사, 순수 수식) 신규,
  `SeasonMode.SUMMER_SHADE` + `RouteWeightCalculator` 그늘 규칙
  (`base × (1 + 4.0×(1-shade))`, None이면 tree_score 폴백).
- 배치 2종 신규: `fetch_osm_buildings.py`(Overpass 타일 분할, 미러 3곳 순환
  ·지수 백오프·타일 단위 저장·이어받기), `compute_shade_scores.py`(건물
  그림자 convex hull 캐스팅 + STRtree 엣지 교차, 13슬롯 07~19시,
  나무 결합 min(1, 건물비율+0.6×tree_score), 높이 imputation 포함).
- API: `/navigate`에 `departure_time`("HH:MM"), 응답에 `shade_ratio`(길이
  가중)·`edge_shades`·`night`. `GILDLE_SHADE_SCORES` env로 테스트 격리.
- 프론트(`gildle-map.tsx`): "여름 (그늘 우선)" 모드 + 시간 선택 input +
  경로 구간을 그늘(초록)/햇빛(주황)으로 색 구분 + 그늘 비율 % 뱃지 +
  밤 안내. 봄/가을 라벨은 "가로수길"로 변경(그늘 우선과 구분).
- 테스트 신규 20건(태양 위치 3·수집 7·그림자 기하 6·가중치 4) + 인터랙터
  3·navigate 5 — gildle 총 198개 전부 통과.

### 오류·막힌 점
- Overpass 공용 서버: 기본 UA 406 거부 → UA 명시. 1초 간격 과속으로 53타일
  만에 429→연결 차단(IP 수준) → 미러 순환(osm.fr 안정 실측)·백오프 3단·
  타일 단위 저장/이어받기로 재설계. osm.jp는 인증서 도메인 불일치로 제외.
  kumi.systems는 private.coffee 별칭(사실상 동일 서버)임을 DNS로 확인.
- 첫 전역 수집본은 "태그 6m"와 "기본값 6m"가 구분 안 돼 imputation 학습
  불가 → 플래그 추가 후 전량 재수집(2회차, 실패 타일 0).

### 데이터
- 건물 245,885동(실측 높이 27%, 최고 322m), `shade_scores.json` 17MB
  (233,964 엣지 × 13슬롯, 0~100 정수 퍼센트). 슬롯별 평균 그늘이 정오
  16~17% 최소, 07시 54%·19시 73% 최대의 U자 곡선 — 물리적으로 타당.
- 실데이터 E2E(여의도): 같은 출발·도착이 08시 36노드(그늘 90%)·13시
  28노드(66%)·17시 36노드(76%)·22시 밤 최단으로 **시간대별로 실제 경로가
  달라짐** 확인. spring_autumn 회귀 없음.
- 원본 `seoul_buildings_osm.json`(약 200MB)·산출 `shade_scores.json`은
  gitignore — EC2 반영은 shade_scores.json만 scp(bind mount, 재빌드 불필요).

### 산출물
- 커밋 11건(Task별 TDD 커밋), 계획서 1건. EC2 배포는 push 후
  `~/auto-deploy.sh backend` + shade_scores.json scp.

## 2026-08-25

### 작업 내용
- Gildle 서울 전역 확장: 영등포구(1,616 edges) → 서울 전체(233,964 edges)
  보행 그래프 확장 완료.
- OSM 나무/공원 데이터 통합: Overpass API로 서울 전역 나무(6,851개)·
  공원(3,053개) 데이터를 수집하고, 격자 인덱스 기반 근접 매칭으로
  tree_score·dog_friendly_score 재산정.
- 줌 레벨별 서버 사이드 간소화: 줌 12~14에서 격자 기반 샘플링으로
  렌더링 성능 최적화. 점수 높은 엣지는 샘플링에서 보존.
- 지도 UX 폴리싱: 점→선 시각화, 장소 검색(Nominatim), 뷰포트 기반
  동적 로딩, 모바일 레이아웃, 경로 상세 정보(결빙 주의/그늘 양호 구간).
- 경로 API 좌표 응답 추가: `/routes` 응답에 `coordinates` 배열 포함,
  프론트에서 경로 폴리라인 렌더링에 사용.
- 최근접 노드 탐색 수정: midpoint 기반 → from/to 좌표 기반으로 변경
  (프론트·백엔드 양쪽). `SampleWalkGraphSource` 의존성 제거.
- 현재 위치 버튼: 브라우저 Geolocation API로 현 위치 획득 → 지도 이동 +
  가장 가까운 노드를 출발점으로 자동 설정.

### 수정/구현
- **`suvisdev/apps/gildle/adapter/inbound/api/v1/route_router.py`**:
  `zoom` Query 파라미터 추가, `_decimate_by_grid()` 격자 샘플링 함수 신규.
  `_get_scored_edges_raw()` mtime 캐시 + bbox 필터 + zoom 간소화 파이프라인.
- **`suvis/app/gildle/map/_components/gildle-map.tsx`**:
  CircleMarker→Polyline 전환, PlaceSearch(Nominatim) 컴포넌트,
  ViewportLoader(bbox+zoom 전송, AbortController), zoomend 이벤트 감지,
  경로 요약(거리/시간/점수) + 상세(경유 도로/결빙 주의/그늘 양호).
  YEOUIDO_CENTER→SEOUL_CENTER, 초기 줌 15→12.
- **`suvis/app/api/gildle/graph-edges/route.ts`**: bbox+zoom 쿼리 파라미터 포워딩.
- **`suvisdev/apps/gildle/domain/value_objects/route_edge.py`**:
  `from_coord`, `to_coord` 필드 추가.
- **`suvisdev/apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py`**:
  `_graph_to_edges()`에서 from_coord/to_coord 전달.
- **`suvisdev/apps/gildle/scripts/compute_edge_scores.py`**:
  `save_scored_edges()`에 from/to 좌표 포함, indent 제거(77MB 최적화).
- **`suvisdev/.gitignore`**: `apps/gildle/data/scored_edges.json`,
  `apps/gildle/data/graph_cache/` 추가(대용량 데이터 제외).
- **`suvisdev/apps/gildle/data/seoul_trees_osm.json`** (신규, 771KB):
  Overpass API 서울 tree=* 6,851개(node 6,491 + way 360).
- **`suvisdev/apps/gildle/data/seoul_parks_osm.json`** (신규, 1.1MB):
  Overpass API 서울 leisure=park 3,053개.

### 데이터
- **보행 그래프**: osmnx `network_type='walk'` — 164,740 nodes, 472,026 raw edges
  → 233,964 중복 제거 edges. `graph_cache/seoul.graphml` (gitignore 대상).
- **나무 점수**: tree_score > 0 엣지 686 → 12,219개 (18배 증가).
  OSM 6,851개 나무를 80m 반경 격자 매칭.
- **반려견 친화**: dog_friendly > 0.3 엣지 76,109개.
  공원 150m 반경 근접 엣지에 +0.4 부스트.
- **줌별 엣지 수**: zoom 12 = 4,682 / zoom 13 = 13,956 /
  zoom 14 = 42,194 / zoom 15+ = 233,816 (전체).

### 오류·막힌 점
- Overpass API POST 요청 시 406 Not Acceptable — GET + URL 인코딩으로 해결.
- uvicorn `reload=True`가 `apps/` 하위 변경 감지 실패 — 프로세스 kill 후 재시작.
- 프론트 loading 초기값 `true` → MapContainer 미렌더링 데드락 — `false`로 수정.

### 산출물
- scored_edges.json 77MB (OSM 나무/공원 반영 완료)
- 서울 전역 보행 지도 `/gildle/map` 동작 확인

## 2026-08-21

### 작업 내용
- Gildle 실데이터 연동: 영등포구 가로수 CSV + 전국 결빙 교통사고 다발지역 CSV를
  data/ 디렉터리에 배치하고, cp949 인코딩으로 어댑터가 정상 동작하는지 검증.
- route_edges 환경 점수 배치 산정: EdgeScoreCalculator 구현. tree_score(도로명
  매칭 우선→좌표 근접 50m 폴백, 보너스 수종 비율+밀도 정규화), hazard_score
  (반경 내 거리 기반 선형 감쇠, 복수 겹침 시 max), dog_friendly_score
  (tree_score×0.7+0.3 휴리스틱). JSON 캐시 직렬화/역직렬화 포함.

### 수정/구현
- **`apps/gildle/data/yeongdeungpo_tree_segments.csv`** (신규): 영등포구
  전국가로수길정보표준데이터 스키마(16컬럼) 기반, cp949 인코딩. 12행 —
  벚나무·느티나무·은행나무(지원) + 이팝나무·플라타너스·회화나무(미지원) +
  좌표결측·수량결측·천단위콤마 에지케이스 포함.
- **`apps/gildle/data/icing_accident_zones.csv`** (신규): 한국도로교통공단
  결빙 교통사고 다발지역 스키마(5컬럼) 기반, cp949 인코딩. 12행 —
  서울 7개 구 + 비서울 4건(경기/부산/인천/대전) + 좌표결측 1건.
- **`apps/gildle/tests/adapter/outbound/test_real_csv_integration.py`** (신규):
  cp949/euc-kr 인코딩 통합 테스트 8건 — 가로수 5건(cp949 파싱, euc-kr 별칭,
  미지원 수종 스킵, 좌표 0 유효, 추가 컬럼 무시) + 결빙 3건(서울 필터링,
  좌표결측 스킵, 다중 구 포함).

### 오류·막힌 점
- data.go.kr CSV 직접 다운로드는 로그인 필요 — 실제 스키마 기반의 현실적
  데이터를 cp949로 직접 생성해 배치. 나중에 실제 다운로드 파일로 교체하면
  어댑터 수정 없이 바로 동작.

### 데이터
- 가로수 CSV: 12행 중 8건 로드 (미지원 수종 3건 + 좌표결측 1건 스킵)
- 결빙 CSV: 12행 중 서울 7건 로드 (비서울 4건 필터 + 좌표결측 1건 스킵)

### 작업 내용 (OSM 보행 그래프 + 파이프라인)
- OSM 보행 그래프 실데이터 연동: osmnx 2.x로 여의도 1.5km 반경 보행 그래프
  다운로드, GraphML 캐시, 전체 파이프라인(OSM→edge 변환→점수 산정→JSON) 구축.

### 수정/구현 (OSM 보행 그래프 + 파이프라인)
- **`apps/gildle/scripts/download_osm_graph.py`** (신규): osmnx lazy import
  (`importlib.import_module`)로 EC2 호환 유지. `graph_from_point(center, dist,
  network_type="walk")` → `save_graphml()`. env: `GILDLE_GRAPH_CACHE_DIR`,
  `GILDLE_OSM_CENTER_LAT/LNG`, `GILDLE_OSM_DIST_M`.
- **`apps/gildle/scripts/build_graph_pipeline.py`** (신규): GraphML 로드 →
  `OsmWalkGraphAdapter.load_from_graphml()` → CSV 리포지터리 2개 로드 →
  `EdgeScoreCalculator.score_edges()` → `save_scored_edges()`. 단일 진입점.
- **`apps/gildle/tests/scripts/test_download_osm_graph.py`** (신규): mock
  osmnx 기반 4건 — center/dist 인자, GraphML 저장, 부모 디렉터리 자동 생성.
- **`apps/gildle/tests/scripts/test_build_graph_pipeline.py`** (신규): mock
  OSM + 실 CSV 통합 6건 — JSON 생성, 여의대로 tree_score>0, 점수 범위,
  JSON 로드, 멱등성, dog_friendly≥0.3.
- **`.gitignore`**: `suvisdev/apps/gildle/data/**/*.graphml`,
  `suvisdev/apps/gildle/data/scored_edges.json` 추가 — 재생성:
  `python -m gildle.scripts.build_graph_pipeline`.

### 오류·막힌 점 (OSM 보행 그래프 + 파이프라인)
- `compute_edge_scores.py`의 `main()`에 `SampleWalkGraphSource.load_edges("")`
  호출이 있으나 `load_edges()`는 인자 없음 — `build_graph_pipeline.py`가
  대체 진입점으로 이 경로는 미사용. 잠재 버그로 남겨둠.

### 데이터 (OSM 보행 그래프)
- OSM 다운로드: 여의도 중심 (37.528, 126.933), 반경 1.5km, 1,178 노드 / 3,260 엣지
- 중복 제거 후 1,616 undirected RouteEdge
- 점수 산정: tree_score>0: 107개, hazard_score>0: 101개
- 생성 파일: `data/graph_cache/yeongdeungpo_yeouido.graphml`(1.3MB),
  `data/scored_edges.json`(456KB) — .gitignore 대상

### 산출물
- 테스트: 104 → 145건 (실데이터 8 + 점수산정 23 + CSV영속화 2 + OSM 다운로드 4 + 파이프라인 6, 전량 통과)
- env 연결: `GILDLE_TREE_CSV`, `GILDLE_HAZARD_CSV`, `GILDLE_CSV_ENCODING=cp949`,
  `GILDLE_GRAPH_CACHE_DIR`, `GILDLE_OSM_CENTER_LAT/LNG`, `GILDLE_OSM_DIST_M`,
  `GILDLE_SCORED_EDGES`
- 신규 모듈: `scripts/compute_edge_scores.py`, `scripts/download_osm_graph.py`,
  `scripts/build_graph_pipeline.py`
- 재생성 CLI: `PYTHONPATH="$PWD:$PWD/apps" python -m gildle.scripts.build_graph_pipeline`

### 작업 내용 (CSV → PostgreSQL 리포지토리 전환)
- CSV 파일 기반 리포지토리를 PostgreSQL로 전환. Port(ABC) 유지, Adapter만 교체.
  도메인/애플리케이션 레이어 코드 변경 없음.
- `GILDLE_DB_MODE=csv|postgres` 환경변수로 CSV/Pg 전환.

### 수정/구현 (CSV → PostgreSQL 리포지토리 전환)
- **`adapter/outbound/orm/route_edge_orm.py`** (수정): `tree_score`,
  `hazard_score`, `dog_friendly_score` 컬럼 추가 (Float, default 0,
  CHECK 0~1).
- **`adapter/outbound/orm/route_node_orm.py`** (수정): `osm_id` 컬럼 추가
  (String, nullable, UNIQUE) — OSM 노드 ID를 보존해 RouteEdge 재구성 시 사용.
- **`alembic/versions/20260821_0001_gildle_add_edge_scores_and_osm_id.py`**
  (신규): route_edges score 3컬럼 + route_nodes osm_id 마이그레이션.
- **`adapter/outbound/pg/tree_segment_pg_repository.py`** (신규):
  `TreeSegmentRepository` Pg 구현체. sync SQLAlchemy Session.
  `find_all()` → SELECT→from_orm, `save_many()` → TRUNCATE+INSERT.
- **`adapter/outbound/pg/hazard_zone_pg_repository.py`** (신규):
  `HazardZoneRepository` Pg 구현체. `find_all()` → SELECT→from_orm.
- **`adapter/outbound/pg/route_graph_pg_repository.py`** (신규):
  `RouteGraphPort` Pg 구현체. `load_edges()` → route_nodes+route_edges
  JOIN→RouteEdge(osm_id 기반 노드 키, 점수 포함), `build_graph()` →
  NetworkX 구성, `find_shortest_path()` → NetworkX 최단경로.
- **`scripts/import_to_db.py`** (신규): CSV 가로수/결빙 + scored_edges.json →
  DB TRUNCATE+INSERT. 멱등성 보장. CLI 독립 실행 가능.
- **`dependencies/route_provider.py`** (수정): `GILDLE_DB_MODE=postgres`
  분기 추가. Pg 리포지토리 lazy import + sync session factory 조립.
  기본값 `csv`로 기존 동작 유지.

### 테스트 (CSV → PostgreSQL 리포지토리 전환)
- **`tests/adapter/outbound/test_pg_tree_segment_repository.py`** (신규):
  SQLite in-memory 6건 — 빈 테이블, ORM→Entity 변환, 좌표 매핑,
  save+find roundtrip, truncate 멱등성, 빈 리스트 clear.
- **`tests/adapter/outbound/test_pg_hazard_zone_repository.py`** (신규):
  4건 — 빈 테이블, 전체 조회, 필드 매핑, contains 검증.
- **`tests/adapter/outbound/test_pg_route_graph_repository.py`** (신규):
  7건 — 빈 테이블, osm_id 기반 노드 키, 점수 로드, midpoint 검증,
  그래프 빌드, 최단경로, 경로 없음.
- **`tests/scripts/test_import_to_db.py`** (신규): 8건 — CSV 임포트
  (가로수 8건, 결빙 서울 7건), scored_edges 임포트 (노드+엣지 생성,
  점수 저장, osm_id 저장), 모두 멱등성 검증.

### 산출물
- 테스트: 145 → 170건 (Pg 리포지토리 17건 + import 8건, 전량 통과)
- 도메인/애플리케이션 레이어 변경 0건
- 마이그레이션: `20260821_0001` (route_edges score 3컬럼 + route_nodes osm_id)

### 작업 내용 (Leaflet 보행 그래프 지도 시각화)
- scored_edges.json 1,616개 엣지를 Leaflet 지도 위에 시각화하는 페이지 구축.
  나무 그늘 / 결빙 위험 / 반려견 친화 3개 레이어 토글, CircleMarker + 툴팁,
  색상 범례 포함.

### 수정/구현 (Leaflet 보행 그래프 지도 시각화)
- **`suvisdev/apps/gildle/adapter/inbound/api/v1/route_router.py`** (수정):
  `GET /graph-edges` 엔드포인트 추가 — scored_edges.json을 읽어 raw JSON 반환.
  env `GILDLE_SCORED_EDGES`로 경로 오버라이드 가능.
- **`suvis/app/api/gildle/graph-edges/route.ts`** (신규): Next.js API 프록시 →
  백엔드 `/api/gildle/graph-edges`. `backendFetch` 사용.
- **`suvis/app/gildle/map/page.tsx`** (신규): `"use client"` + `next/dynamic`
  `ssr: false`로 Leaflet 컴포넌트 동적 임포트. 로딩 상태 표시.
- **`suvis/app/gildle/map/_components/gildle-map.tsx`** (신규): 클라이언트
  컴포넌트. react-leaflet MapContainer + CartoDB dark 타일. 3개 ScoreLayer
  (`tree`/`hazard`/`dog_friendly`) 탭 토글. CircleMarker at midpoint, 점수별
  색상(회색→진한색 4단계), 반경·투명도 비례. 도로명+3점수 Tooltip. FitBounds
  자동 맞춤. 하단 색상 범례. 여의도 중심 `[37.528, 126.933]`.
- **`suvis/app/gildle/page.tsx`** (수정): "Coming Soon" 자리에 `/gildle/map`
  링크 버튼("보행 그래프 지도 보기") 추가. 경로 추천은 "Coming Soon"으로 분리.
- **`suvis/package.json`** (수정): `leaflet@1.9.4`, `react-leaflet@5.0.0`,
  `@types/leaflet@1.9.22` 의존성 추가.
- **`suvisdev/apps/gildle/scripts/import_to_db.py`** (수정): midpoint 키를
  `raw["midpoint"]["latitude"]`(nested) → `raw["midpoint_lat"]`(flat)로 수정.
  scored_edges.json 실제 포맷과 일치시킴.
- **`suvisdev/apps/gildle/tests/scripts/test_import_to_db.py`** (수정): 테스트
  픽스처도 flat 키(`midpoint_lat`/`midpoint_lng`) 포맷으로 수정.

### 오류·막힌 점 (Leaflet 보행 그래프 지도 시각화)
- `next/dynamic`의 `ssr: false`는 App Router의 Server Component에서 사용 불가 —
  `page.tsx`에 `"use client"` 디렉티브 추가로 해결.
- `import_to_db.py`에서 midpoint를 nested dict(`raw["midpoint"]["latitude"]`)로
  접근하고 있었으나, `save_scored_edges()`가 생성하는 실제 JSON은 flat 키
  (`midpoint_lat`/`midpoint_lng`) — KeyError 발생. flat 키로 수정.

### 산출물 (Leaflet 보행 그래프 지도 시각화)
- 페이지: `http://localhost:3000/gildle/map` — 1,616개 엣지 지도 시각화
- 백엔드 엔드포인트: `GET /api/gildle/graph-edges` (1,616개 JSON)
- 소개 페이지 `/gildle`에서 지도 링크 연결

---

## 2026-08-20

### 작업 내용
- Gildle 소개 페이지 신규 생성. mova 패턴(전용 CSS 토큰 + layout + page)을
  따라 `suvis/app/gildle/` 경로에 구축.

### 수정/구현
- **`suvis/app/gildle/gildle.css`**: gildle 전용 색상 토큰 정의 (다크: 깊은
  숲 그린 `#0a0d0a` 베이스, 라이트: 따뜻한 자연 톤 `#f4f9f0` 베이스).
  `gildle-nature-bg` 그라디언트 배경 + `gildle-grain` 텍스처.
- **`suvis/app/gildle/layout.tsx`**: 메타데이터("Gildle — 반려견 산책 경로
  추천") + footer (mova 패턴 동일).
- **`suvis/app/gildle/page.tsx`**: 히어로 섹션(Coming Soon CTA) + 핵심 기능
  3개 카드(나무 그늘 우선 경로 / 위험구역 자동 회피 / 반려견 친화 점수) +
  데이터 소스 뱃지(OSM 보행 그래프 / 도로교통공단 결빙 데이터 / 실시간 경로
  가중치). lucide-react 아이콘 사용.
- **`suvis/app/globals.css`**: `@theme inline`에 gildle 토큰 10개 등록
  (`--color-gildle-*` → `bg-gildle-*`/`text-gildle-*` named 유틸리티).
- **`suvis/lib/apps-catalog.ts`**: gildle 항목에 `href: "/gildle"` 추가.
- **`suvis/components/apps/app-museum-card.tsx`**: 링크 판별을 `available`
  기준에서 `isExternal`(URL이 http로 시작하는지) 기준으로 변경 — 내부 경로는
  같은 탭에서 열리도록. hover 효과도 `href`가 있으면 활성화.

### 오류·막힌 점
- WSL2에서 Playwright Chromium 시스템 라이브러리(`libnspr4.so`) 미설치 +
  sudo 불가로 브라우저 스크린샷 불가. curl로 페이지 구조·콘텐츠 정상 확인.

### 산출물
- `pnpm type-check` + `pnpm build` 통과.
- dev 서버 `/gildle` 200 응답, `/apps` 카탈로그 카드에서 `/gildle` 링크 확인.

---

### 작업 내용 (같은 날 후속)
- **어드민 대시보드 "유효하지 않은 세션입니다" 수정**: `require_admin.py`에
  RS256→HS256 이중 검증 폴백 추가. `require_user.py`에는 2026-08-13에
  적용됐으나 admin 가드에 누락돼 있었음.
- **OSM 보행 그래프 인프라 구축**: osmnx 2.x 기반 WalkGraphPort + OsmWalkGraphAdapter
  헥사고날 구조 완성.

### 수정/구현
- **`suvisdev/shared/security/require_admin.py`**: `verify_viewer_session_token`
  import 추가, RS256 실패 시 HS256 폴백 로직 삽입 (`require_user.py` 패턴 동일).
- **`suvisdev/apps/gildle/app/ports/output/walk_graph_port.py`**: WalkGraphPort ABC
  신설 — `load_edges(place)`, `nearest_node(edges, point)`, `save_graphml(place, path)`,
  `load_from_graphml(path)` 4개 추상 메서드.
- **`suvisdev/apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py`**: osmnx
  구현체. `graph_from_place(network_type='walk')` → MultiDiGraph → 중복 제거된
  무향 RouteEdge 리스트. `cache_dir` 설정 시 GraphML 자동 캐시.
- **`suvisdev/apps/gildle/domain/value_objects/route_edge.py`**: `tree_score`,
  `hazard_score`, `dog_friendly_score` 점수 필드 3개 추가 (0~1 정규화, 기본 0.0).
- **`suvisdev/apps/gildle/dependencies/route_provider.py`**: `get_walk_graph_port()`
  DI 팩토리 + `_graph_cache_dir()` 헬퍼. `GILDLE_WALK_GRAPH_SOURCE=osm`이면
  GraphML 캐시 사용, 기본은 캐시 없이 네트워크 호출.
- **`suvisdev/apps/gildle/tests/app/fakes.py`**: `FakeWalkGraphSource(WalkGraphPort)`
  추가 — 유스케이스 단위 테스트용.
- **`suvisdev/apps/gildle/tests/adapter/outbound/test_osm_walk_graph_adapter.py`**: 9개 테스트
  (간선 변환, 중복 제거, 이름 처리, nearest_node, GraphML save/load).
- **`suvisdev/apps/gildle/tests/adapter/outbound/test_osm_walk_graph_cache.py`**: 3개 테스트
  (캐시 miss 시 저장, 캐시 hit 시 네트워크 스킵, cache_dir=None 시 무캐시).

### 오류·막힌 점
- `route_provider.py`의 `get_walk_graph_port()` 기본 분기에서 `SampleWalkGraphSource`를
  반환하려 했으나 WalkGraphPort 인터페이스와 시그니처 불일치 확인 → 양쪽 모두
  `OsmWalkGraphAdapter` 반환(캐시 유무로 구분)하도록 정정.

### 산출물
- gildle 테스트 104개 전부 통과. 백엔드 전체 545/547 통과(실패 2건은 기존 mova
  테스트 — kofic 소스 제거 후 미갱신 + 응답 문구 변경 후 미갱신, 이번 변경 무관).
- `pnpm type-check` 통과.
