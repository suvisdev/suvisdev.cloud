import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'l10n/app_localizations.dart';
import 'auth_screens.dart';
import 'settings.dart';
import 'tile.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
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
