import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/auth_screens.dart';
import 'package:kumoniji/legal.dart';

Widget _app(String lang) => MaterialApp(
  locale: Locale(lang),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: const Scaffold(body: LegalLinks()),
);

void main() {
  testWidgets('korean sign-in links open the korean privacy policy with the contact address', (t) async {
    await t.pumpWidget(_app('ko'));
    await t.tap(find.byKey(const ValueKey('legal-privacy')));
    await t.pumpAndSettle();
    expect(find.text('개인정보처리방침'), findsWidgets);
    expect(find.textContaining('ssuvisdev@gmail.com'), findsOneWidget);
  });

  testWidgets('other languages get the english terms', (t) async {
    await t.pumpWidget(_app('ja'));
    await t.tap(find.byKey(const ValueKey('legal-terms')));
    await t.pumpAndSettle();
    expect(find.textContaining('Operator: suvisdev'), findsOneWidget);
  });

  testWidgets('a failed load shows an error with retry instead of spinning forever', (t) async {
    var fail = true;
    t.binding.defaultBinaryMessenger.setMockMessageHandler('flutter/assets', (msg) async {
      final key = utf8.decode(msg!.buffer.asUint8List());
      if (!key.startsWith('assets/legal/')) return null;
      return fail ? null : ByteData.sublistView(utf8.encode('# Terms\nOperator: suvisdev'));
    });
    addTearDown(() => t.binding.defaultBinaryMessenger.setMockMessageHandler('flutter/assets', null));
    await t.pumpWidget(_app('en'));
    await t.tap(find.byKey(const ValueKey('legal-terms')));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('legal-retry')), findsOneWidget);
    fail = false; // 연결이 돌아옴
    await t.tap(find.byKey(const ValueKey('legal-retry')));
    await t.pumpAndSettle();
    expect(find.textContaining('Operator: suvisdev'), findsOneWidget);
  });

  testWidgets('changing the app language while the policy is open reloads the body in the new language', (t) async {
    t.binding.defaultBinaryMessenger.setMockMessageHandler('flutter/assets', (msg) async {
      final key = utf8.decode(msg!.buffer.asUint8List());
      if (!key.startsWith('assets/legal/')) return null;
      return ByteData.sublistView(utf8.encode(key.contains('_ko') ? '한국어 본문' : 'English body'));
    });
    addTearDown(() => t.binding.defaultBinaryMessenger.setMockMessageHandler('flutter/assets', null));
    final lang = ValueNotifier('en');
    await t.pumpWidget(
      ValueListenableBuilder<String>(
        valueListenable: lang,
        builder: (_, l, _) => MaterialApp(
          locale: Locale(l),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: const LegalScreen(doc: Legal.privacy),
        ),
      ),
    );
    await t.pumpAndSettle();
    expect(find.textContaining('English body'), findsOneWidget);
    lang.value = 'ko';
    await t.pumpAndSettle();
    expect(find.textContaining('한국어 본문'), findsOneWidget);
  });

  testWidgets('the sign-up consent notice sits above the sign-up button', (t) async {
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
        home: const SignupScreen(),
      ),
    );
    await t.pumpAndSettle();
    final notice = t.getTopLeft(find.byKey(const ValueKey('legal-terms'))).dy;
    final button = t.getTopLeft(find.byKey(const ValueKey('signup'))).dy;
    expect(notice, lessThan(button));
  });
}
