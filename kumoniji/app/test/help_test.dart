import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kumoniji/help.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/tile.dart';

void main() {
  setUp(markTilesReady);

  testWidgets('how to play has back from the second card and an X that closes it', (t) async {
    await t.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (c) => TextButton(onPressed: () => showHelp(c), child: const Text('open')),
        ),
      ),
    );
    await t.tap(find.text('open'));
    await t.pumpAndSettle();
    expect(find.text('Back'), findsNothing); // 첫 장엔 이전 없음
    await t.tap(find.text('Next'));
    await t.pumpAndSettle();
    await t.tap(find.text('Back'));
    await t.pumpAndSettle();
    expect(find.text('Back'), findsNothing); // 첫 장으로 돌아옴
    await t.tap(find.byIcon(Icons.close));
    await t.pumpAndSettle();
    expect(find.byType(Dialog), findsNothing);
  });

  testWidgets('narrow screen with big text keeps the buttons inside on the last card', (t) async {
    // 카드 그림 줄은 이 크기에서 원래부터 넘친다(범위 밖) — 그 오류는 모으기만 하고 버튼 위치만 본다
    final old = FlutterError.onError;
    FlutterError.onError = (_) {};
    t.view.physicalSize = const Size(320, 640);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    await t.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        builder: (c, child) => MediaQuery(
          data: MediaQuery.of(c).copyWith(textScaler: const TextScaler.linear(2)),
          child: child!,
        ),
        home: Builder(
          builder: (c) => TextButton(onPressed: () => showHelp(c), child: const Text('open')),
        ),
      ),
    );
    await t.tap(find.text('open'));
    await t.pumpAndSettle();
    for (var i = 0; i < 4; i++) {
      await t.tap(find.text('Next'));
      await t.pumpAndSettle();
    }
    FlutterError.onError = old;
    final dialog = t.getRect(find.byType(Dialog));
    for (final label in ['Back', "Let's play"]) {
      final r = t.getRect(find.text(label));
      expect(r.right <= dialog.right && r.left >= dialog.left, isTrue, reason: label);
    }
  });
}
