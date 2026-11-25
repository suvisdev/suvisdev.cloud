import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'l10n/app_localizations.dart';
import 'auth_screens.dart';
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
      home: const AuthGate(),
    ),
  );
}
