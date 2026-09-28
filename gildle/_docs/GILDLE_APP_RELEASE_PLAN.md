# gildle 앱 출시 계획 (2026-09-22)

앱 출시는 **gildle만** 한다(2026-09-22 결정). mova를 제외한 이유는 TMDB 약관의
AI 학습 조항이 별도 서면 계약을 요구하기 때문이고, gildle은 OSM 기반이라 그
문제가 없다. 백엔드 쪽 작업은 `suvisdev/apps/gildle/_docs/GILDLE_APP_API_PLAN.md`.

## 현황 실측 (2026-09-22)

| 항목 | 상태 |
|------|------|
| Flutter 프로젝트 | `gildle/` 하나(09-27 `susu`에서 개명) — `applicationId = cloud.suvisdev.gildle` |
| 화면 | ~~mova 채팅 · 사진 업로드 · 스톱워치~~ → **09-27 삭제**, gildle 지도 화면 1개 |
| 구조 | `Splash → Auth → HomeScreen(지도)`, `go_router`는 `/` 하나만 등록 |
| 릴리스 서명 | ~~없음~~ → 09-23 `key.properties` 있으면 release 키, 없으면 debug 폴백 |
| gildle 화면 | ~~0개~~ → **지도 1개(09-27)** — 산책 중·기록·마이페이지는 미구현 |
| iOS | **하지 않음** (2026-09-22 결정, Android만 출시) |
| 지도 패키지 | 없음 (웹은 Leaflet 사용) |
| 인프라 | 카카오 OAuth·dio·flutter_secure_storage·riverpod **있음** (재사용 가치) |

---

## 단계 1. 프로젝트 형태 정하기 — **A안으로 진행함(2026-09-27)**

**A. susu를 gildle 앱으로 전환** (권장)
- 카카오 OAuth·네트워크·보안 저장소가 이미 붙어 있어 그대로 쓴다.
- `applicationId`를 `cloud.suvisdev.gildle`로, 앱 이름·아이콘을 교체한다.
- mova 채팅·사진 업로드 화면은 제거하거나 숨긴다 — **mova 화면이 남아 있으면
  TMDB 포스터를 표시하게 되어 attribution 의무가 되살아난다.**

**B. 새 Flutter 프로젝트 생성**
- 깨끗하지만 OAuth·네트워크 계층을 다시 만든다. susu는 실험용으로 남는다.

A를 고르면 susu의 기존 화면 정리가 첫 작업이 된다.

## 단계 2. 릴리스 서명 (스토어 업로드의 첫 관문)

```bash
keytool -genkey -v -keystore ~/gildle-release.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias gildle
```
- `android/key.properties` 생성(`storeFile`·`storePassword`·`keyAlias`·`keyPassword`)
- `android/app/build.gradle`의 `buildTypes.release.signingConfig`를 릴리스 설정으로 교체
- **`key.properties`와 `.jks`는 절대 커밋하지 않는다** — `.gitignore` 확인
- 분실하면 같은 앱으로 업데이트가 불가능하다. 안전한 곳에 백업할 것

## 단계 3. UI 구성

색은 mova 토큰 체계(`suvis/app/mova/mova.css`)를 그대로 쓰지 않는다 — mova는
"어두운 영화관 + 핑크 액센트"라 산책 앱과 맞지 않는다. gildle 웹 화면
(`suvis/app/gildle/`)의 톤을 기준으로 Flutter `ThemeData`를 만든다.

화면 구성(최소):
1. **지도** — 출발·도착 선택, 계산된 경로 폴리라인, 그늘 점수 표시
2. **산책 중** — 현재 위치 추적, 거리·시간, 종료 시 기록 저장
3. **기록** — 지난 산책 목록·상세
4. **마이페이지** — 로그인, 즐겨찾기, 통계

지도 패키지는 **flutter_map(OSM 타일)** 이 웹(Leaflet)과 데이터 출처가 같아
일관된다. `google_maps_flutter`는 API 키 발급·과금 관리가 추가로 필요하다.

## 단계 4. 권한·정책

- **위치 권한**: `ACCESS_FINE_LOCATION`. 백그라운드 추적이 필요하면
  `ACCESS_BACKGROUND_LOCATION`인데, 이건 Play 심사에서 **별도 정당화 양식**을
  요구하므로 가능하면 포그라운드만으로 설계한다.
- **개인정보처리방침 URL 필수** — 위치 수집·보존·삭제를 명시한 gildle 전용
  문서가 필요하다(mova 방침과 별도).
- **데이터 보안 양식** — 위치 수집 여부·암호화·삭제 요청 경로 신고.
- **OSM 저작자 표시** — ODbL 요구사항. 웹 지도에는 이미 있으므로
  (`suvis/app/gildle/map/_components/gildle-map.tsx:765`) 앱 지도 화면에도
  같은 고지를 넣는다.
- 콘텐츠 등급 설문, 타겟 연령층 설정.

## 단계 5. 백엔드 준비 (병행)

`GILDLE_APP_API_PLAN.md`의 1번 항목(선택적 인증 + walks + favorites + nearby)이
없으면 앱은 "경로만 계산하고 아무것도 남지 않는" 상태가 된다. 출시 전 최소한
**산책 기록 저장**은 있어야 한다.

**가용성**: API는 노트북 k3s + Cloudflare 터널이다. 노트북이 꺼지면 앱 전체가
실패하고, 심사 리뷰어가 그때 접속하면 거절된다. 출시 전에 상시 가동 여부를
정할 것.

## 콘솔 등록 전 준비 상태 (2026-09-27 저녁)

| 항목 | 상태 |
|------|------|
| 패키지·폴더명 | `gildle`(09-27 개명), `applicationId cloud.suvisdev.gildle` |
| 런처 아이콘 | ✅ `assets/icon/` + adaptive(09-27) |
| 스플래시 | ✅ 초록 정적 화면(영상 제거) |
| 화면 | 지도·산책 중·기록·상세·내 정보 |
| 릴리스 서명·AAB | ✅ `key.properties` + `flutter build appbundle --release` (바탕화면 `길들/`) |
| 개인정보처리방침 URL | ✅ `https://suvisdev.cloud/gildle/privacy` |
| 최소 버전 API | ✅ `GET /api/gildle/app/version`(`.env` `GILDLE_APP_*`) |
| 실기기 검증 | ❌ **아직** — 디버그 APK 설치 후 지도 인증·위치 권한·산책 저장 확인 필요 |
| 스토어 등록정보 | 🟡 09-28 입력값·설명 초안·아이콘 512·그래픽 1024×500 준비(`GILDLE_PLAY_CONSOLE_GUIDE.md`), 스크린샷은 실기기에서 |
| Play Console | ✅ 09-28 개발자 인증 완료·앱 생성. 남은 것: 내부 테스트 업로드 → 비공개 테스트 12명·14일 → 프로덕션 신청 |
| 로그인 없이 사용 | ✅ 09-28 지도·경로 추천은 게스트, 산책 저장·기록·내 정보만 로그인(심사자 접근) |
| 이메일 가입·탈퇴 | ✅ 09-28 이메일·비밀번호만 받는 가입, 앱 내 회원 탈퇴 + 웹 `/gildle/account-deletion` |
| 릴리스 AAB | ✅ 09-28 `gildle-release-20260928.aab`(노트북에서 빌드, targetSdk 36) |
| FCM 발송 | ❌ 토큰 등록만(보낼 알림 미정) |

## 단계 6. 내부 테스트 → 출시

1. `flutter build appbundle --release` → `.aab`
2. Play Console 앱 생성(`cloud.suvisdev.gildle`)
3. **내부 테스트 트랙**에 먼저 올려 실기기 검증
4. 스토어 등록정보(스크린샷·설명·아이콘) — 설명에 **서울 전역 한정**을 명시할 것
   (2026-08-25 기준 서울만 지원)
5. 프로덕션 심사 제출

---

## 지금 할 수 있는 순서

1. 단계 1 결정 (susu 전환 vs 신규)
2. 백엔드 `walks` API + 선택적 인증
3. 릴리스 서명 설정
4. Flutter 지도·기록 화면
6. 내부 테스트
