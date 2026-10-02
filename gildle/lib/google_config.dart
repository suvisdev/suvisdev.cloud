/// 구글 로그인 serverClientId — 웹 OAuth 클라이언트 ID(suvisdev/.env의 GOOGLE_CLIENT_ID와 동일).
/// 앱이 받는 id token의 aud가 이 값이 되고, auth 게이트웨이가 같은 값으로 검증한다.
/// 클라이언트 ID는 공개값이다(비밀은 CLIENT_SECRET). Android OAuth 클라이언트(패키지명 + SHA-1)는
/// 같은 GCP 프로젝트에 따로 등록해야 로그인 창이 뜬다.
const String googleServerClientId =
    '226054818742-5vqbit71e4o41g9oujlgjvmjugistifo.apps.googleusercontent.com';
