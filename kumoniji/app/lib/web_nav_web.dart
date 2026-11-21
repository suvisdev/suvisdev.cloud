import 'dart:async';
import 'dart:js_interop';
import 'dart:ui_web' as ui_web;

import 'package:flutter/widgets.dart';
import 'package:web/web.dart' as web;

void goTo(String url) => web.window.location.assign(url);

// Flutter가 기록 항목에 둔 상태 객체는 그대로 두고 주소만 바꾼다(null로 덮으면 Flutter 기록 관리가 오류를 낸다).
void cleanUrl() => web.window.history.replaceState(web.window.history.state, '', '/');

const hasTurnstile = true;

@JS('turnstile.render')
external JSString _render(web.HTMLElement el, JSObject options);

extension type _Options._(JSObject _) implements JSObject {
  external factory _Options({JSString sitekey, JSFunction callback});
}

int _seq = 0;
Future<void>? _script; // 스크립트는 한 번만 싣고, 다 실린 뒤에만 그린다

Future<void> _loadScript() {
  final done = Completer<void>();
  final s = web.HTMLScriptElement()
    ..src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
    ..async = true;
  s.onload = ((web.Event _) => done.complete()).toJS;
  s.onerror = ((web.Event _) {
    _script = null; // 실패하면 다음 시도에 다시 싣는다
    done.completeError('turnstile');
  }).toJS;
  web.document.head!.append(s);
  return done.future;
}

/// Cloudflare Turnstile. 스크립트는 처음 필요할 때만 싣는다(CSP가 challenges.cloudflare.com만 허용).
Widget turnstile(String siteKey, ValueChanged<String> onToken) {
  final type = 'turnstile-${_seq++}';
  ui_web.platformViewRegistry.registerViewFactory(type, (int _) {
    final box = web.HTMLDivElement()
      ..style.width = '100%'
      ..style.height = '72px';
    (_script ??= _loadScript()).then(
      (_) => _render(box, _Options(sitekey: siteKey.toJS, callback: ((JSString t) => onToken(t.toDart)).toJS)),
      onError: (_) {},
    );
    return box;
  });
  return SizedBox(height: 72, child: HtmlElementView(viewType: type));
}
