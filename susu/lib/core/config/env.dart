/// 백엔드(main FastAPI, mova 등) base URL — 환경별로 --dart-define으로 전환한다.
///
/// 예: 로컬 백엔드 → `flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000`
///     집 GPU 백엔드 → `flutter run --dart-define=API_BASE_URL=http://<집서버IP>:8000`
///     (기본값은 EC2 프로덕션 — nginx가 api.suvisdev.cloud를 backend:8000으로 프록시)
class AppConfig {
  AppConfig._();

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.suvisdev.cloud',
  );

  /// 네이버 클라우드 플랫폼 Maps Client ID(gildle 지도 배경). 소스에 넣지 않고
  /// `dart_defines.json`(gitignore) → `--dart-define-from-file`로 주입한다.
  /// 비어 있으면 지도 SDK 초기화를 건너뛴다(로그인·mova 등 나머지는 그대로 동작).
  static const String naverMapClientId = String.fromEnvironment('NAVER_MAP_CLIENT_ID');
}
