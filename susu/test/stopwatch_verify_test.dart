import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:susu/main.dart';
import 'package:susu/stopwatch_page.dart';

void main() {
  testWidgets('IntroScreen에서 스톱워치 열기 버튼으로 진입', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const SuvisApp());

    await tester.tap(find.text('스톱워치 열기'));
    await tester.pumpAndSettle();

    expect(find.byType(StopwatchPage), findsOneWidget);
    expect(find.text('00:00.00'), findsOneWidget);
  });

  testWidgets('스톱워치: 시작 -> 랩 -> 중단 -> 리셋', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(home: StopwatchPage()));

    expect(find.text('00:00.00'), findsOneWidget);
    expect(find.text('시작'), findsOneWidget);

    await tester.tap(find.text('시작'));
    await tester.pump();
    expect(find.text('중단'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 500));
    await tester.tap(find.text('랩'));
    await tester.pump();
    expect(find.text('랩 1'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 500));
    await tester.tap(find.text('랩'));
    await tester.pump();
    expect(find.text('랩 2'), findsOneWidget);
    expect(find.text('랩 1'), findsOneWidget);

    await tester.tap(find.text('중단'));
    await tester.pump();
    expect(find.text('시작'), findsOneWidget);
    expect(find.text('재설정'), findsOneWidget);

    await tester.tap(find.text('재설정'));
    await tester.pump();
    expect(find.text('00:00.00'), findsOneWidget);
    expect(find.text('랩 1'), findsNothing);
  });
}
