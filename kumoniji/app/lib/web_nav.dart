// 웹 전용 동작(페이지 이동·주소 정리·Turnstile). 휴대폰 앱에서는 아무 일도 하지 않는 판으로 바뀐다.
export 'web_nav_stub.dart' if (dart.library.js_interop) 'web_nav_web.dart';
