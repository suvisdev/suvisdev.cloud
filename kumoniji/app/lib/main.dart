import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'l10n/app_localizations.dart';
import 'auth_screens.dart';
import 'music.dart';
import 'settings.dart';
import 'tile.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // 앱은 가로 고정(11-25 사용자). 안드로이드·iOS 설정(매니페스트·Info.plist)과 같게.
  // 웹은 부르지 않는다 — 웹 엔진이 브라우저 화면 잠금으로 넘겨 설치형 웹 앱을 가로로 돌려 버린다(리뷰 1차)
  if (!kIsWeb) {
    await SystemChrome.setPreferredOrientations([DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]);
  }
  await Settings.load();
  precacheTiles(); // 기다리지 않는다 — 첫 판을 시작할 때 끝나 있는지 확인
  runApp(const KumonijiApp());
  Music.start(); // 기다리지 않는다 — 소리가 늦게 나와도 화면은 먼저
}

class KumonijiApp extends StatelessWidget {
  const KumonijiApp({super.key});

  @override
  Widget build(BuildContext context) => ValueListenableBuilder(
    valueListenable: Settings.locale,
    builder: (_, locale, _) => MaterialApp(
      locale: locale,
      onGenerateTitle: (c) => AppLocalizations.of(c)!.title,
      debugShowCheckedModeBanner: false,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFF2A7C3)),
        scaffoldBackgroundColor: const Color(0xFFFFF9EC),
      ),
      // 웹은 브라우저가 방향을 잠그게 두지 않으니(설치형 웹 앱은 manifest가 가로로 잠금) 세로 창이면 돌려 달라고 가린다.
      // 세로 배치는 쓰지 않는다 — 가로 고정(11-26 사용자 "세로버전 x")
      builder: kIsWeb ? (context, child) => RotateGate(child: child!) : null,
      home: const AuthGate(),
    ),
  );
}

/// 웹에서 창이 세로(폭 < 높이)면 내용 대신 '가로로 돌려 주세요'를 보여 준다. 내용은 그대로 살려 둬 돌리면 이어진다.
class RotateGate extends StatelessWidget {
  final Widget child;
  const RotateGate({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    final portrait = size.width < size.height;
    return Stack(
      children: [
        // Offstage는 키보드 포커스·입력을 막지 않는다 — 가려진 입력란에 타이핑되지 않게 포커스도 뺀다
        Offstage(
          offstage: portrait,
          child: ExcludeFocus(
            excluding: portrait,
            child: TickerMode(enabled: !portrait, child: child),
          ),
        ),
        if (portrait)
          Positioned.fill(
            child: ColoredBox(
              key: const ValueKey('rotate'),
              color: Theme.of(context).scaffoldBackgroundColor,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.screen_rotation, size: 64, color: Color(0xFF8A4A63)),
                    const SizedBox(height: 16),
                    Text(
                      AppLocalizations.of(context)!.rotateDevice,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}
