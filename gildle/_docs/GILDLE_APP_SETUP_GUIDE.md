# gildle 앱 — 외부 서비스 설정 가이드 (2026-09-22)

Firebase(FCM 푸시)와 네이버 지도를 붙이기 위해 **콘솔에서 발급받아야 하는 것**과
**코드에 넣어야 하는 것**을 순서대로 정리한다. 콘솔 UI 명칭은 바뀔 수 있으니
메뉴가 안 보이면 비슷한 이름을 찾으면 된다.

전제: 앱은 `gildle/`를 gildle 앱으로 전환하는 A안 기준이다
(`GILDLE_APP_RELEASE_PLAN.md` 단계 1). 패키지명은 `cloud.suvisdev.gildle`로 가정한다.

---

## 1. 네이버 지도 (Maps)

### 1-1. 콘솔에서 할 일

1. **네이버 클라우드 플랫폼** 가입 — `ncloud.com`
   - 결제수단 등록이 필요하다. 무료 한도 안에서는 청구되지 않지만 카드 등록은 요구된다.
2. 콘솔 → **Services** → **Application Services** → **Maps** 이용 신청
3. **Application 등록**
   - Application 이름: `gildle`
   - 서비스 선택: **Mobile Dynamic Map** 체크 (앱 안에 지도를 그리는 용도)
     - 웹도 네이버로 바꾸려면 **Web Dynamic Map**도 함께 체크
   - Android 패키지 이름: `cloud.suvisdev.gildle`
   - **iOS는 등록하지 않는다** — 안드로이드(Play)만 출시하기로 했다(2026-09-22 결정)
4. 등록 후 **Client ID**(`X-NCP-APIGW-API-KEY-ID`)를 받는다. 이게 앱에 넣는 값이다.

### 1-2. 무료 한도

Mobile Dynamic Map은 월 단위 무료 호출량이 있다(구간별 종량 과금). 개인 앱
규모에서는 무료 범위를 넘기기 어렵다. 콘솔의 **요금 계산기**에서 현재 단가를
확인할 수 있다.

### 1-3. 코드에 넣는 것 — **적용 완료(2026-09-22 밤)**

Client ID는 발급받아 `gildle/dart_defines.json`(gitignore)에 넣었다. 소스·매니페스트에는
값이 없고, 실행 때 파일로 주입한다:

```bash
flutter run --dart-define-from-file=dart_defines.json
flutter build apk --dart-define-from-file=dart_defines.json
```
Android Studio 실행 버튼을 쓰면 Run/Debug Configurations → **Additional run args**에
`--dart-define-from-file=dart_defines.json`을 한 번 넣어 둔다.

- `lib/core/config/env.dart` — `AppConfig.naverMapClientId`(`String.fromEnvironment`).
- `lib/main.dart` — `runApp` 전에 `FlutterNaverMap().init(clientId: …, onAuthFailed: …)`.
  값이 비어 있으면 초기화를 건너뛰어 지도 없는 실행도 깨지지 않는다.
- `AndroidManifest.xml`의 `com.naver.maps.map.CLIENT_ID` meta-data는 **넣지 않았다** —
  flutter_naver_map 1.x는 `init()`으로 충분하고, 매니페스트에 넣으면 값이 소스에 박힌다.
- 인증 실패(`onAuthFailed`)가 찍히면 NCP 콘솔의 Android 패키지명이 `applicationId`와
  같은지부터 본다.

### 1-4. 중요 — 바뀌는 건 "배경 지도"뿐이다

gildle의 경로는 OSM 보행 그래프에 그늘·위험 점수를 얹어 **백엔드가 계산**한다.
네이버로 바꾸는 것은 그 경로를 그리는 **바탕 지도**일 뿐이다. 네이버 길찾기 API로
경로까지 바꾸면 그늘 점수를 못 쓰므로 gildle의 핵심이 사라진다.
좌표계는 양쪽 다 WGS84라 변환 없이 폴리라인을 그대로 올릴 수 있다.

---

## 2. Firebase — FCM 푸시

### 2-1. 푸시가 동작하는 구조

```
① 앱 최초 실행  → FCM이 그 기기에 "토큰"(기기 주소) 발급
② 앱            → 우리 백엔드에 토큰 전송·저장
③ 보낼 때       → 백엔드가 FCM에 "이 토큰으로 이 메시지" 요청
④ FCM           → 해당 기기에 알림 표시
```
안드로이드는 구글 서버(FCM)를 거치지 않으면 앱이 꺼진 상태에서 알림을 띄울 수 없다.

### 2-2. 콘솔에서 할 일

1. `console.firebase.google.com` → **프로젝트 만들기** (이름: `gildle`)
   - Google 애널리틱스는 꺼도 된다(푸시와 무관).
2. 프로젝트 안에서 **Android 앱 추가**
   - 패키지 이름: `cloud.suvisdev.gildle` — **앱의 applicationId와 정확히 같아야 한다**
   - SHA-1 인증서 지문: 푸시만 쓸 거면 지금은 생략 가능
   - iOS 앱은 추가하지 않는다
3. **`google-services.json` 다운로드** → `gildle/android/app/google-services.json`에 배치
   - **이 파일은 커밋하지 않는다.** `.gitignore`에 추가할 것
4. 백엔드가 발송하려면 **서비스 계정 키**가 필요하다
   - 프로젝트 설정 → **서비스 계정** → **새 비공개 키 생성** → JSON 다운로드
   - 이 JSON은 서버에만 두고 절대 앱·저장소에 넣지 않는다

### 2-3. 코드에 넣는 것 (Flutter)

`pubspec.yaml`
```yaml
dependencies:
  firebase_core: ^3.8.0
  firebase_messaging: ^15.1.5
```

**적용 완료(09-22 밤, Kotlin DSL)** — 이 템플릿은 플러그인 선언이 `settings.gradle.kts`에 있다:
```kotlin
// android/settings.gradle.kts  plugins { … }
id("com.google.gms.google-services") version "4.4.2" apply false
// android/app/build.gradle.kts  plugins { … }
id("com.google.gms.google-services")
```

`android/app/src/main/AndroidManifest.xml` — Android 13+는 알림 권한이 필요하다
```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

`lib/main.dart`
```dart
await Firebase.initializeApp();
await FirebaseMessaging.instance.requestPermission();   // 사용자 동의 팝업
final token = await FirebaseMessaging.instance.getToken();
// token을 백엔드 POST /app/push-tokens 로 전송
```

### 2-4. 백엔드에 필요한 것

| 항목 | 내용 |
|------|------|
| 테이블 | `push_tokens(user_id, token, platform, created_at, updated_at)` — 같은 토큰 재등록은 upsert |
| API | `POST /app/push-tokens` (토큰 등록, `require_user`) · `DELETE`(로그아웃 시 해제) |
| 발송 | 서비스 계정 키로 FCM HTTP v1 API 호출 |
| 패키지 | `firebase-admin` 또는 직접 HTTP 호출 |
| 주의 | 토큰은 **기기 식별자**다. 탈퇴·로그아웃 시 삭제하고, 데이터 보안 양식에 신고한다 |

### 2-5. 비용

FCM 자체는 **무료**이고 발송량 제한도 사실상 없다. Firebase 프로젝트도 무료
플랜(Spark)으로 충분하다.

---

## 3. 발급 순서 요약 (회원님이 하실 일)

1. **Play Console 개발자 계정** — $25, 신분 확인 (진행 중)
2. ~~네이버 클라우드 플랫폼 → Maps → Application 등록 → Client ID~~ **받음·적용됨(09-22)**
3. ~~Firebase → 프로젝트 → Android 앱 추가 → google-services.json~~ **받음·배치됨(09-22 밤)**
   — `gildle/android/app/google-services.json`(gitignore), 프로젝트 `gildle`, 패키지 일치 확인.
   Gradle 플러그인(`settings.gradle.kts` + `app/build.gradle.kts`, Kotlin DSL) 추가됨.
4. ~~Firebase → 서비스 계정 → 비공개 키 JSON~~ **받음(09-22 밤)** — 노트북 `~/secrets/gildle-fcm.json`
   (chmod 600, 저장소 밖). 백엔드 발송 코드가 생기면 `.env`에 경로로 연결한다.

2~4를 받으면 나머지 코드 작업은 바로 진행할 수 있다.

---

## 4. 보안 주의

| 파일/값 | 어디에 두나 | 커밋 |
|---------|-------------|------|
| 네이버 Client ID | `--dart-define` 주입 | ✗ |
| `google-services.json` | `android/app/` | **✗ (.gitignore 추가 필요)** |
| Firebase 서비스 계정 키 | 백엔드 서버 `.env` 경로 참조 | ✗ |
| 릴리스 keystore·`key.properties` | 로컬 + 백업 | ✗ (이미 차단됨) |

`gildle/android/.gitignore`에 `key.properties`·`**/*.jks`는 이미 있으나
**`google-services.json`은 없다** — Firebase 진행 시 추가해야 한다.

---

## 5. iOS는 하지 않는다 (2026-09-22 결정)

안드로이드(Play)만 출시한다. 따라서:

- 카카오 콘솔의 **iOS 앱 정보(번들 ID)** — 등록하지 않음
- 네이버 Maps Application의 **iOS Bundle ID** — 등록하지 않음
- Firebase의 **iOS 앱 추가** — 하지 않음
- `gildle/ios/`의 Bundle ID는 Flutter 기본값(`com.example.susu`) 그대로 둔다

나중에 App Store를 하려면 **macOS 빌드 환경**이 따로 필요하다(현재 개발 환경은
Windows + WSL). 그때 Bundle ID 변경부터 다시 시작하면 된다.
