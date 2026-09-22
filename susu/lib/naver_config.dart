/// 네이버 지도 Client ID — 네이버 클라우드 플랫폼 > Maps > Application에서 발급.
///
/// Client Secret은 여기 두지 않는다. 지도 SDK(Mobile Dynamic Map)는 Client ID만
/// 쓰고, Secret은 서버용이라 앱에 포함하면 안 된다. Client ID는 등록된 패키지명
/// (cloud.suvisdev.gildle)에서만 동작하므로 kakao_config.dart와 같은 방식으로 둔다.
const String naverMapClientId = 'e630p2wr6p';
