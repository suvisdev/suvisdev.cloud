import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

  testWidgets('가로 두 칸(600px)·큰 글자에서도 카드 그림이 넘치지 않는다(로고 PR 리뷰 1차)', (t) async {
    t.view.physicalSize = const Size(600, 400);
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
      expect(t.takeException(), isNull, reason: 'card ${i + 1}');
      await t.tap(find.text('Next'));
      await t.pumpAndSettle();
    }
    expect(t.takeException(), isNull, reason: 'card 5');
  });

  testWidgets('낮은 가로 창(600×300)·큰 글자에선 한 칸으로 제목까지 스크롤된다(로고 PR 리뷰 2차)', (t) async {
    t.view.physicalSize = const Size(600, 300);
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
    expect(t.takeException(), isNull);
    // 제목이 스크롤 안에 있다 — 낮은 창에서도 끌어 올려 그림·설명을 읽을 수 있다
    expect(find.ancestor(of: find.text('Goal'), matching: find.byType(SingleChildScrollView)), findsOneWidget);
  });

  testWidgets('폰 가로(844×390)는 그림 | 설명 두 칸', (t) async {
    t.view.physicalSize = const Size(844, 390);
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
        home: Builder(
          builder: (c) => TextButton(onPressed: () => showHelp(c), child: const Text('open')),
        ),
      ),
    );
    await t.tap(find.text('open'));
    await t.pumpAndSettle();
    expect(find.ancestor(of: find.text('Goal'), matching: find.byType(SingleChildScrollView)), findsNothing);
  });

  testWidgets('가로 두 칸에서 Page Down이 긴 설명을 내린다(로고 PR 리뷰 3차)', (t) async {
    t.view.physicalSize = const Size(844, 390);
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
    // 그림|설명 두 칸을 함께 내리는 스크롤
    final text = find.descendant(of: find.byType(SingleChildScrollView).last, matching: find.byType(Scrollable)).first;
    expect(t.state<ScrollableState>(text).position.maxScrollExtent, greaterThan(0)); // 설명이 넘친다
    await t.sendKeyEvent(LogicalKeyboardKey.tab); // 키보드 사용자: 버튼(닫기·다음)에 포커스
    await t.pump();
    await t.sendKeyEvent(LogicalKeyboardKey.pageDown);
    await t.pumpAndSettle();
    expect(t.state<ScrollableState>(text).position.pixels, greaterThan(0));
    // 데스크톱(웹 포함)은 스크롤이 기본 컨트롤러에 저절로 붙지 않는다 — 그쪽에서도 확인(리뷰 4차)
  }, variant: TargetPlatformVariant.only(TargetPlatform.linux));

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
