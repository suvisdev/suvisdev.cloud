/// auth 게이트웨이(suvisdev/apps/auth, `uvicorn auth_main:app --port 9000`) base URL.
/// nginx(nginx/conf.d/app.conf)가 `api.suvisdev.cloud`의 `/auth/*`를 auth 컨테이너로
/// 프록시하므로, 폰 실기기는 이 공개 도메인을 통해서만 접근한다(로컬 127.0.0.1은
/// 폰에서 접근 불가).
const String authBaseUrl = 'https://api.suvisdev.cloud';
