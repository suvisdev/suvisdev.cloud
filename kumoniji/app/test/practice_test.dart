import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/practice.dart';
import 'package:kumoniji/tile.dart';

Widget _at(double width, {VoidCallback? onOpen}) => MaterialApp(
  locale: const Locale('en'),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: Scaffold(
    body: SingleChildScrollView(
      child: SizedBox(
        width: width,
        child: OutTracker(out: const ['m1'], suits: const ['m', 's', 'l', 'c'], onOpen: onOpen),
      ),
    ),
  ),
);

double _tileW(WidgetTester t) => t.widget<TileView>(find.byType(TileView).first).width;

void main() {
  setUp(markTilesReady);

  testWidgets('390px 시트(크게 보기 버튼 없음)에선 패를 두 줄로 나눠 키운다(로고 PR 리뷰 3차)', (t) async {
    await t.pumpWidget(_at(390));
    expect(_tileW(t), greaterThan(40));
  });

  testWidgets('크게 보기 버튼이 있는 옆 패널은 무늬마다 13장 한 줄', (t) async {
    await t.pumpWidget(_at(390, onOpen: () {}));
    expect(_tileW(t), lessThan(30));
  });
}
