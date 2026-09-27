# Flutter iOS 개발 하네스

`gildle` Flutter 앱을 iOS 시뮬레이터·실기기에서 빌드·실행하기 위한 로컬
개발 환경 구축 가이드다. **iOS 빌드는 macOS에서만 가능하다**(Xcode가
macOS 전용이라 Windows·Linux에서는 iOS 시뮬레이터·실기기 빌드 자체가
불가능 — Android 개발은 `flutter-android-harness.md` 참고).

## 0. 이 프로젝트가 실제로 쓰는 버전

| 항목 | 값 | 근거 |
|---|---|---|
| Dart SDK | `^3.12.2` | `gildle/pubspec.yaml` |
| iOS 배포 타겟(최소 지원 iOS 버전) | 13.0 | `ios/Runner.xcodeproj/project.pbxproj`의 `IPHONEOS_DEPLOYMENT_TARGET` |
| 언어 | Swift(기본) | `flutter create`가 iOS는 Swift로만 생성(Objective-C 템플릿은 더 이상 기본 제공 안 됨) |

## 1. 사전 설치

1. **Xcode** — Mac App Store에서 최신 stable 버전 설치. 설치 후 최초 1회
   실행해 추가 컴포넌트 다운로드까지 완료해야 한다.
2. **Command Line Tools** 연결:

   ```bash
   sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
   sudo xcodebuild -runFirstLaunch
   ```

3. **Flutter SDK** — [공식 사이트](https://docs.flutter.dev/get-started/install/macos)에서
   최신 stable 채널 설치(`.metadata`에 `channel: "stable"`로 고정돼 있다).
4. **CocoaPods** — iOS 네이티브 의존성(Flutter 플러그인의 iOS 쪽 구현체)을
   묶어주는 도구. Flutter 공식 권장 방식은 Homebrew다:

   ```bash
   brew install cocoapods
   ```

   Homebrew가 없다면 `sudo gem install cocoapods`도 가능하지만, 시스템
   Ruby와 충돌하는 경우가 있어 Homebrew 설치를 우선 권장한다.

5. (Android Studio에서 iOS 시뮬레이터를 함께 다루고 싶다면) Android
   Studio에도 Flutter/Dart 플러그인을 설치해두면 같은 IDE에서 Android·iOS
   기기를 동시에 선택할 수 있다.

설치가 끝나면 확인한다.

```bash
flutter doctor -v
```

`[✓] Xcode`, `[✓] CocoaPods` 항목이 체크돼야 한다. CocoaPods 관련 경고가
뜨면 `pod --version`으로 설치 여부를 먼저 확인한다.

## 2. 프로젝트 열기·의존성 설치

`gildle`는 이미 생성된 프로젝트이므로 `flutter create`는 필요 없다.

```bash
cd gildle
flutter pub get
```

iOS 네이티브 의존성(Podfile 기반)은 `flutter run`/`flutter build ios`
실행 시 Flutter 툴이 자동으로 `pod install`을 호출한다. 수동으로 하고
싶다면:

```bash
cd ios
pod install
cd ..
```

## 3. iOS 시뮬레이터로 실행

시뮬레이터를 여는 방법은 여러 가지다. 편한 걸 쓰면 된다.

- **Xcode에서**: 메뉴 [Xcode] → [Open Developer Tool] → [Simulator].
- **터미널에서**: `open -a Simulator`
- **Android Studio에서**: 상단 기기 선택 드롭다운에 iOS 시뮬레이터가
  자동으로 나열된다(별도 실행 버튼 없이 목록에서 바로 선택 가능한 버전이
  대부분이지만, 안 보이면 드롭다운의 "Open iOS Simulator" 항목을 먼저
  누른다).

시뮬레이터가 뜨면 상단 메뉴 [File] → [Open Simulator]에서 원하는 기기
모델·iOS 버전을 고를 수 있다(최신 iOS 버전 권장 — 최소 지원 버전은 위 0번
표의 13.0이지 시뮬레이터 자체를 그 버전으로 맞출 필요는 없다).

```bash
flutter devices     # 실행 중인 시뮬레이터가 목록에 잡히는지 확인
flutter run          # 또는 Android Studio/VS Code 실행 버튼
```

## 4. 실제 iPhone으로 실행 (선택)

시뮬레이터와 달리 실기기 빌드는 Apple 코드 서명이 필요하다.

1. iPhone을 USB(Lightning 또는 USB-C)로 Mac에 연결하고, 기기에서 "이
   컴퓨터를 신뢰하시겠습니까?" 팝업에 [신뢰]를 누른다.
2. Xcode에서 `ios/Runner.xcworkspace`를 연다(`.xcodeproj`가 아니라
   CocoaPods가 만든 `.xcworkspace`를 열어야 한다).
3. 프로젝트 네비게이터에서 `Runner` 선택 → [Signing & Capabilities] 탭
   → [Team]에 Apple ID(무료 개인 개발자 계정으로도 충분) 선택.
4. 무료 계정으로 서명한 앱은 실기기에서 최초 실행 시 "신뢰되지 않은
   개발자" 경고가 뜬다 — iPhone에서 [설정] → [일반] → [VPN 및 기기 관리]
   → 해당 개발자 프로필 [신뢰]로 해제한다.
5. 이후엔 터미널에서도 바로 실행 가능:

```bash
flutter devices
flutter run
```

## 5. 트러블슈팅

- **CocoaPods 관련 빌드 실패**: `cd ios && pod deintegrate && pod install`
  로 Pod 캐시를 재구성.
- **`flutter doctor`에서 Xcode 라이선스 미동의**: `sudo xcodebuild
  -license`.
- **시뮬레이터가 `flutter devices`에 안 보임**: 시뮬레이터 앱이 실제로
  기동돼 있는지 확인(닫혀 있으면 목록에 안 뜬다).
- **실기기 서명 오류(`No profiles for … were found`)**: Xcode
  [Signing & Capabilities]에서 [Automatically manage signing] 체크 후
  Team을 다시 선택하면 프로비저닝 프로파일이 자동 생성된다.
