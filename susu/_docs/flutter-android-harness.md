# Flutter Android 개발 하네스

`susu` Flutter 앱을 Android 에뮬레이터·실기기에서 빌드·실행하기 위한 로컬
개발 환경 구축 가이드다. 오래된 튜토리얼(구버전 Android Studio 마법사,
API 레벨별 분기표 등) 대신 이 저장소의 실제 `android/` 설정 파일 기준으로
작성했다 — 아래 버전은 `susu/android/*.gradle.kts`·`susu/pubspec.yaml`에서
직접 읽은 값이다.

## 0. 이 프로젝트가 실제로 쓰는 버전

| 항목 | 값 | 근거 |
|---|---|---|
| Dart SDK | `^3.12.2` | `pubspec.yaml` |
| Gradle | `9.1.0` | `android/gradle/wrapper/gradle-wrapper.properties` |
| Android Gradle Plugin | `9.0.1` | `android/settings.gradle.kts` |
| Kotlin | `2.3.20` | `android/settings.gradle.kts` |
| Java | 17 (source/target compatibility) | `android/app/build.gradle.kts` |
| compileSdk/minSdk/targetSdk | Flutter SDK가 자동 결정(`flutter.compileSdkVersion` 등) | `android/app/build.gradle.kts` |

마지막 행이 핵심 변화다. 예전엔 `build.gradle`에 `compileSdkVersion 33`처럼
API 레벨을 직접 박아뒀지만, 지금 템플릿(`dev.flutter.flutter-gradle-plugin`
+ Kotlin DSL)은 `flutter.compileSdkVersion`/`flutter.minSdkVersion`/
`flutter.targetSdkVersion`으로 **설치된 Flutter SDK가 알아서 최신값을
채운다.** 즉 API 레벨을 손으로 맞출 일이 없다 — Flutter SDK만 최신으로
유지하면 된다.

## 1. 사전 설치

1. **Flutter SDK** — [공식 사이트](https://docs.flutter.dev/get-started/install)에서
   최신 stable 채널 설치. 이 프로젝트는 `.metadata`에 `channel: "stable"`로
   고정돼 있다.
2. **Android Studio** — 최신 stable 버전 설치 후 최초 실행 시 뜨는 Setup
   Wizard에서 Android SDK·Android SDK Platform-Tools·Android Virtual
   Device를 함께 설치한다.
3. **Flutter/Dart 플러그인** — Android Studio [Settings] → [Plugins]에서
   `Flutter`를 검색해 설치(`Dart` 플러그인은 종속성으로 자동 설치됨).
4. **JDK 17** — Android Studio에 내장된 JBR(JetBrains Runtime)을 그대로
   쓰는 걸 권장한다. 별도 JDK를 설치했다면 `android/app/build.gradle.kts`의
   `JavaVersion.VERSION_17`과 맞아야 한다.

설치가 끝나면 터미널에서 확인한다.

```bash
flutter doctor -v
```

`[✓] Android toolchain`, `[✓] Android Studio` 항목이 전부 체크돼야 한다.
라이선스 미동의 경고가 뜨면:

```bash
flutter doctor --android-licenses
```

## 2. 프로젝트 열기·의존성 설치

`susu`는 이미 생성된 프로젝트이므로 `flutter create`는 필요 없다. 저장소
루트의 `susu/` 폴더를 Android Studio의 [Open]으로 열거나, 터미널에서:

```bash
cd susu
flutter pub get
```

Android Studio에서 처음 열면 `android/local.properties`가 자동
생성된다(`flutter.sdk=<Flutter SDK 경로>`). 이 파일은 `.gitignore` 대상이라
사람마다 다른 값이 들어가며, 저장소에는 없다.

## 3. 에뮬레이터로 실행

1. Android Studio 오른쪽 툴바의 **Device Manager** 아이콘을 연다.
2. [Create Device] → 원하는 기기 프로필(Pixel 계열 권장) 선택.
3. System Image는 **최신 API 레벨(Play Store 지원 이미지)** 을 선택한다.
   과거 튜토리얼처럼 특정 API 30~33 사이로 제한할 필요 없다 — 위 0번
   표에서 봤듯 compileSdk/targetSdk는 Flutter SDK가 자동으로 맞춰준다.
4. [Show Advanced Settings]에서 **Internal Storage를 8GB 이상**으로
   늘린다(기본값이 낮으면 앱 설치 중 용량 부족 에러가 난다).
5. 에뮬레이터를 실행한 뒤 터미널에서:

```bash
flutter devices     # 에뮬레이터가 목록에 잡히는지 확인
flutter run          # 또는 Android Studio 상단 실행 버튼
```

## 4. 실제 Android 기기로 실행 (USB 디버깅)

과거 자료는 Android 버전별로 절차가 갈리는 표를 썼지만, 현재 실사용되는
Android 버전(9 이상, 사실상 전부)은 절차가 동일하다.

1. **개발자 옵션 활성화**: [설정] → [휴대전화 정보] → [빌드 번호]를
   연속으로 7번 탭. ("개발자 모드가 활성화되었습니다" 토스트가 뜬다.)
   기기 제조사에 따라 [설정] → [정보 표시] → [소프트웨어 정보] → [빌드
   번호] 등으로 경로가 조금 다를 수 있다(빌드 번호 항목만 찾으면 된다).
2. **USB 디버깅 켜기**: [설정] → [시스템] → [개발자 옵션] → [USB
   디버깅] 토글 ON. (일부 제조사는 [개발자 옵션]이 [설정] 최상위 메뉴에
   바로 노출된다.)
3. 기기를 USB로 컴퓨터에 연결한다(USB는 개발 PC와 폰을 잇는 데이터
   케이블을 뜻한다 — 충전 전용 케이블은 데이터 전송이 안 돼 인식되지
   않는다). 기기 화면에 "USB 디버깅을 허용하시겠습니까?" 팝업이 뜨면
   [허용]을 누른다("이 컴퓨터에서 항상 허용"을 체크하면 매번 안 물어봄).
4. **Windows에서만**: Google USB Driver가 필요할 수 있다. Android
   Studio [Tools] → [SDK Manager] → [SDK Tools] 탭 → [Google USB
   Driver] 체크 → [Apply]. macOS·Linux는 별도 드라이버 설치가 필요 없다.
5. 확인:

```bash
flutter devices
```

목록에 기기가 보이면 준비 완료. `adb devices`로도 확인 가능하다(기기
쪽에 `unauthorized`로 뜨면 USB 디버깅 허용 팝업을 다시 확인).

## 5. 트러블슈팅

- **`flutter devices`에 기기가 안 보임**: USB 케이블이 데이터 전송을
  지원하는지 확인(충전 전용 케이블이면 인식 안 됨). `adb kill-server &&
  adb start-server`로 ADB 재시작.
- **Gradle 동기화 실패**: `flutter clean` 후 재시도. 그래도 안 되면
  Android Studio의 `File > Invalidate Caches / Restart`.
- **라이선스 미동의(`Some licenses have not been accepted`)**: `flutter
  doctor --android-licenses` 실행 후 전부 `y`.
- **저장 공간 부족(에뮬레이터)**: Device Manager에서 해당 AVD를 Edit →
  Internal Storage를 늘리거나, 기존 AVD를 지우고 8GB 이상으로 재생성.
