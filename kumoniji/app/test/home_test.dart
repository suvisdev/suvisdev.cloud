import 'dart:convert';
import 'dart:ui' show SemanticsAction, Tristate;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show RenderParagraph;
import 'package:flutter/services.dart';

import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/api.dart';
import 'package:kumoniji/auth.dart';
import 'package:kumoniji/home_screen.dart';
import 'package:kumoniji/l10n/app_localizations.dart';
import 'package:kumoniji/main.dart';
import 'package:kumoniji/settings.dart';
import 'package:kumoniji/table_screen.dart';
import 'package:kumoniji/tile.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_test.dart' show view;
import 'table_screen_test.dart' show noRid, settle;

Widget _home(Api api) => MaterialApp(
  locale: const Locale('en'),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: HomeScreen(api: api, showHelpOnFirstVisit: false),
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    markTilesReady();
    Settings.locale.value = null;
    Settings.vibration.value = true;
    Settings.muted.value = false;
    Settings.homeBg.value = 0;
    Settings.tableBg.value = 0;
  });

  testWidgets('home has single, multi (disabled), how to play, options — no quit', (t) async {
    await t.pumpWidget(_home(Api(MockClient((_) async => http.Response('', 500)))));
    await settle(t);
    expect(find.text('Single player'), findsOneWidget);
    final multi = find.ancestor(of: find.text('Multiplayer · Coming soon'), matching: find.byType(OutlinedButton));
    expect(t.widget<OutlinedButton>(multi).onPressed, isNull);
    expect(find.text('How to play'), findsOneWidget);
    expect(find.text('Options'), findsOneWidget);
    // 왼쪽 위에 이름(글씨가 아니라 제목 로고), 가운데 제목 로고가 패 넷보다 위(11-26 사용자)
    final name = find.descendant(of: find.byType(AppBar), matching: find.bySemanticsLabel('Kumoniji'));
    expect(name, findsOneWidget);
    expect(find.descendant(of: find.byType(AppBar), matching: find.text('Kumoniji')), findsNothing);
    expect(t.getTopLeft(name).dx, lessThan(100));
    expect(t.getSemantics(name).flagsCollection.namesRoute, isTrue); // 화면 제목으로 읽힌다
    final logo = find.descendant(of: find.byType(Column), matching: find.byType(Image)).first;
    expect(t.getTopLeft(logo).dy, lessThan(t.getTopLeft(find.byType(TileView).first).dy));
  });

  testWidgets('single → pick level → game; back mid-game asks before leaving', (t) async {
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        bodies.add(noRid(r.body));
        return http.Response(jsonEncode({...view(), 'level': 'hard'}), 200);
      }),
    );
    await t.pumpWidget(_home(api));
    await settle(t);
    await t.tap(find.text('Single player'));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('level-hard')));
    await t.pump();
    expect(bodies, isEmpty); // 고르기만 해서는 시작하지 않는다
    await t.tap(find.byKey(const ValueKey('level-start')));
    for (var i = 0; i < 50 && find.text('Your turn').evaluate().isEmpty; i++) {
      await t.pump(const Duration(milliseconds: 100)); // 나눠 주기·시작 카드가 끝날 때까지
    }
    expect(bodies, [
      {'level': 'hard'},
    ]);
    expect(find.text('Your turn'), findsOneWidget);
    await t.tap(find.byType(BackButton));
    await settle(t);
    expect(find.text('Quit this game and leave?'), findsOneWidget);
    await t.tap(find.text('Cancel'));
    await settle(t);
    expect(find.text('Your turn'), findsOneWidget); // 그대로 남음
    await t.tap(find.byType(BackButton));
    await settle(t);
    await t.tap(find.text('Leave'));
    await settle(t);
    expect(find.text('Single player'), findsOneWidget); // 메인으로 돌아옴
  });

  testWidgets('level dialog scrolls on a short landscape screen', (t) async {
    t.view.physicalSize = const Size(640, 300);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final bodies = <Object?>[];
    final api = Api(
      MockClient((r) async {
        bodies.add(noRid(r.body));
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await t.pumpWidget(_home(api));
    await settle(t);
    await t.ensureVisible(find.text('Single player')); // 낮은 화면이라 홈도 스크롤된다
    await t.pump();
    await t.tap(find.text('Single player'));
    await settle(t);
    expect(t.takeException(), isNull); // 넘침 없음
    await t.dragUntilVisible(
      find.byKey(const ValueKey('level-hard')),
      find.byType(SingleChildScrollView).last,
      const Offset(0, -50),
    );
    await t.tap(find.byKey(const ValueKey('level-hard')));
    await t.pump();
    final old = FlutterError.onError;
    FlutterError.onError = (_) {}; // 판 화면은 높이 300에서 원래부터 넘친다(범위 밖) — 여기서는 난이도 창만 본다
    await t.tap(find.byKey(const ValueKey('level-start')));
    await t.pump();
    expect(bodies, [
      {'level': 'hard'},
    ]);
    for (var i = 0; i < 50; i++) {
      await t.pump(const Duration(milliseconds: 100)); // 나눠 주기 애니메이션 타이머를 끝낸다
    }
    FlutterError.onError = old;
  });

  testWidgets('finished game result Home goes back to the home screen', (t) async {
    final done = {
      ...view(),
      'winner': 3,
      'settlement': [-9, -17, 3, 23],
      'moves': [],
      'playable': [],
    };
    final api = Api(MockClient((r) async => http.Response(jsonEncode(done), 200)));
    await t.pumpWidget(_home(api));
    await settle(t);
    await t.tap(find.text('Single player'));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('level-start')));
    for (var i = 0; i < 50 && find.byKey(const ValueKey('result-home')).evaluate().isEmpty; i++) {
      await t.pump(const Duration(milliseconds: 100));
    }
    await t.tap(find.byKey(const ValueKey('result-home')));
    await settle(t);
    expect(find.text('Single player'), findsOneWidget);
    expect(find.byKey(const ValueKey('result-home')), findsNothing);
  });

  testWidgets('four suit tiles shrink together in a 280px window', (t) async {
    t.view.physicalSize = const Size(280, 700);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    Auth.me.value = Me.fromJson({'id': 1, 'nickname': 'me'}); // 로그인 상태 — 프로필 버튼까지 있어도 넘치지 않게(리뷰 9차)
    addTearDown(() => Auth.me.value = null);
    await t.pumpWidget(_home(Api(MockClient((r) async => http.Response('{}', 200)))));
    await settle(t);
    expect(t.takeException(), isNull);
    expect(find.byKey(const ValueKey('open-profile')), findsNothing); // 좁은 창에선 옵션 → 계정으로
    expect(t.getRect(find.byWidgetPredicate((w) => w is TileView && w.code == 'c11')).right <= 280, isTrue);
  });

  testWidgets('home shows one tile of each suit; top bar is missions, shop, profile (no options icon, no mute, no background)', (t) async {
    Auth.me.value = Me.fromJson({'id': 1, 'email': 'me@x.com', 'nickname': 'me'});
    addTearDown(() => Auth.me.value = null);
    await t.pumpWidget(_home(Api(MockClient((r) async => http.Response('{}', 200)))));
    await settle(t);
    for (final c in ['m13', 's13', 'l12', 'c11']) {
      expect(find.byWidgetPredicate((w) => w is TileView && w.code == c), findsOneWidget);
    }
    // 순서(11-28 사용자): 미션·출석 / 상점 / 프로필. 옵션은 큰 버튼, 음소거·배경 버튼은 홈 상단에서 뺐다
    final xs = [
      for (final k in ['open-missions', 'open-shop', 'open-profile']) t.getCenter(find.byKey(ValueKey(k))).dx,
    ];
    final bar = find.byType(AppBar);
    expect(find.descendant(of: bar, matching: find.byKey(const ValueKey('open-options'))), findsNothing);
    expect(xs, [...xs]..sort());
    expect(find.byKey(const ValueKey('mute')), findsNothing);
    expect(find.byKey(const ValueKey('home-background')), findsNothing);
  });

  testWidgets('mute button (game screen) silences music and effects and restores volumes', (t) async {
    await t.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        home: Scaffold(appBar: AppBar(actions: const [MuteButton()])),
      ),
    );
    Settings.music.value = 0.6;
    Settings.sfx.value = 0.8;
    await t.tap(find.byKey(const ValueKey('mute')));
    await t.pump();
    expect((Settings.musicVolume, Settings.sfxVolume), (0.0, 0.0));
    expect(find.byIcon(Icons.volume_off), findsOneWidget);
    expect((await SharedPreferences.getInstance()).getBool('muted'), true);
    await t.tap(find.byKey(const ValueKey('mute')));
    await t.pump();
    expect((Settings.musicVolume, Settings.sfxVolume), (0.6, 0.8)); // 음량 값은 그대로 돌아온다
  });

  testWidgets('options: language switches the whole app and is remembered; vibration and volume saved', (t) async {
    // 로그인된 계정으로 시작(쿠키·토큰이 살아 있는 상태)
    Auth.client = AuthClient(
      MockClient(
        (r) async => r.url.path == '/api/auth/me'
            ? http.Response(jsonEncode({'id': 1, 'email': 'me@x.com', 'nickname': 'me'}), 200)
            : http.Response('{}', 404),
      ),
    );
    await t.pumpWidget(const KumonijiApp());
    await settle(t);
    await t.tap(find.byKey(const ValueKey('open-options')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('language')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('locale-ja')));
    await settle(t);
    expect(find.text('オプション'), findsOneWidget); // 화면이 바로 일본어로
    // 게임판·세트 줄이 늘어 아래 항목은 내려야 보인다
    await t.scrollUntilVisible(find.byKey(const ValueKey('vibration')), 200, scrollable: find.byType(Scrollable).last);
    await t.tap(find.byKey(const ValueKey('vibration')));
    await settle(t);
    Settings.muted.value = true; // 게임 화면에서 음소거하고 왔다
    addTearDown(() => Settings.muted.value = false);
    await t.drag(find.byKey(const ValueKey('music')), const Offset(-500, 0));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('mute-option'))); // 홈엔 음소거 버튼이 없어 옵션에서 푼다
    await settle(t);
    final p = await SharedPreferences.getInstance();
    expect((Settings.muted.value, p.getBool('muted')), (false, false));
    expect(p.getString('locale'), 'ja');
    expect(p.getBool('vibration'), false);
    expect(p.getDouble('music'), 0);
    await t.tap(find.byType(BackButton));
    await settle(t);
    expect(find.text('シングルモード'), findsOneWidget);
  });

  testWidgets('시작 화면 배경은 옵션 안에서, 게임 화면은 꾸미기 버튼에서(배경·게임판·세트) — 고르면 바로 깔리고 기억된다', (t) async {
    Auth.client = AuthClient(
      MockClient(
        (r) async => r.url.path == '/api/auth/me'
            ? http.Response(jsonEncode({'id': 1, 'email': 'me@x.com', 'nickname': 'me'}), 200)
            : http.Response('{}', 404),
      ),
    );
    await t.pumpWidget(const KumonijiApp());
    await settle(t);
    expect(find.byKey(const ValueKey('backdrop-home-0')), findsOneWidget); // setUp에서 없음
    await t.tap(find.byKey(const ValueKey('open-options')));
    await settle(t);
    Future<void> choose(String kind, int n) async {
      for (var i = 0; i <= (kind == 'home' ? homeBackgrounds : tableBackgrounds); i++) {
        expect(find.byKey(ValueKey('bg-$kind-$i')), findsOneWidget); // 없음 + 홈 15장(6~10 세트 배경·11~15 시작 화면) / 게임 화면 10장
      }
      final title = kind == 'home' ? 'Home background' : 'Table background';
      expect(find.bySemanticsLabel('$title 2'), findsOneWidget); // 화면 읽기가 구분할 이름
      expect(
        t.getSemantics(find.bySemanticsLabel('$title 2')).getSemanticsData().hasAction(SemanticsAction.tap),
        isTrue,
      );
      await t.tap(find.byKey(ValueKey('bg-$kind-$n')));
      await settle(t);
    }

    await t.tap(find.byKey(const ValueKey('home-background'))); // 옵션 안(11-28 사용자 '우선 숨겨 두자')
    await settle(t);
    expect(t.getSemantics(find.bySemanticsLabel('None')).flagsCollection.isSelected, Tristate.isTrue); // 지금 고른 것
    await choose('home', 3);
    await t.tap(find.byType(BackButton)); // 옵션 → 시작 화면
    await settle(t);
    final box = t.widget<DecoratedBox>(find.byKey(const ValueKey('backdrop-home-3')));
    expect(((box.decoration as BoxDecoration).image!.image as AssetImage).assetName, 'assets/backgrounds/home_3.jpg');
    // 게임 화면: 꾸미기 버튼 → 배경·게임판·세트
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
        home: TableScreen(
          api: Api(MockClient((r) async => http.Response(jsonEncode(view()), 200))),
          showHelpOnFirstVisit: false,
        ),
      ),
    );
    await settle(t);
    Future<void> menu(String item) async {
      await t.tap(find.byKey(const ValueKey('table-look')));
      await settle(t);
      await t.tap(find.byKey(ValueKey(item)));
      await settle(t);
    }

    await menu('table-background');
    await choose('table', 5);
    final p = await SharedPreferences.getInstance();
    expect(p.getInt('homeBg'), 3);
    expect(p.getInt('tableBg'), 5);
    // 게임판: 기본 + 10장, 하나를 고르면 기억(11-26 사용자)
    await menu('board');
    for (var i = 0; i <= boards; i++) {
      expect(find.byKey(ValueKey('board-$i')), findsOneWidget);
    }
    await t.tap(find.byKey(const ValueKey('board-4')));
    await settle(t);
    expect(p.getInt('board'), 4);
    // 세트: 배경과 판을 한 번에(세트 3 = 배경 8 · 판 8)
    await menu('board-set');
    expect(find.byKey(const ValueKey('set-0')), findsNothing); // 세트엔 '없음'이 없다
    await t.tap(find.byKey(const ValueKey('set-3')));
    await settle(t);
    expect((p.getInt('tableBg'), p.getInt('board')), (8, 8));
    expect((Settings.tableBg.value, Settings.board.value), (8, 8));
    expect(backgroundAsset('home', 7), 'assets/backgrounds/table_7.jpg'); // 홈의 세트 배경은 같은 파일
    expect(backgroundAsset('home', 12), 'assets/backgrounds/home_12.jpg'); // 11~15는 시작 화면 전용
    for (var i = 1; i <= homeBackgrounds; i++) {
      await rootBundle.load(backgroundAsset('home', i)); // 고를 수 있는 그림 파일이 다 있다
    }
  });

  testWidgets('낮은 폰 가로(740×360)에서도 메인 버튼 넷이 판째 한 화면에 든다', (t) async {
    t.view.physicalSize = const Size(740, 360);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    await t.pumpWidget(_home(Api(MockClient((_) async => http.Response('', 500)))));
    await settle(t);
    final options = find.ancestor(of: find.text('Options'), matching: find.byType(OutlinedButton));
    expect(t.getRect(options).bottom, lessThanOrEqualTo(360));
    expect(t.getSize(options).height, greaterThanOrEqualTo(48));
  });

  testWidgets('좁은 가로 창(568×320)·글자 2배에선 버튼 글자가 줄바꿈되고 판이 늘어나 잘리지 않는다', (t) async {
    t.view.physicalSize = const Size(568, 320);
    t.view.devicePixelRatio = 1;
    t.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(t.view.reset);
    addTearDown(t.platformDispatcher.clearTextScaleFactorTestValue);
    await t.pumpWidget(_home(Api(MockClient((_) async => http.Response('', 500)))));
    await settle(t);
    for (final label in ['Multiplayer · Coming soon', 'How to play']) {
      // 글자 상자가 글자가 실제로 필요한 높이만큼 받았는지(상한에 눌리면 상자는 작고 글자는 넘쳐 잘린다)
      final p = t.renderObject<RenderParagraph>(find.text(label));
      expect(p.size.height, greaterThanOrEqualTo(p.getMaxIntrinsicHeight(p.size.width) - .5), reason: label);
    }
  });

  testWidgets('시스템 글자를 키우면(3배, 740×360) 버튼 글자를 줄이지 않고 줄바꿈해 판이 늘어난다', (t) async {
    t.view.physicalSize = const Size(740, 360);
    t.view.devicePixelRatio = 1;
    t.platformDispatcher.textScaleFactorTestValue = 3;
    addTearDown(t.view.reset);
    addTearDown(t.platformDispatcher.clearTextScaleFactorTestValue);
    await t.pumpWidget(_home(Api(MockClient((_) async => http.Response('', 500)))));
    await settle(t);
    for (final label in ['Multiplayer · Coming soon', 'Options']) {
      expect(find.ancestor(of: find.text(label), matching: find.byType(FittedBox)), findsNothing, reason: label);
      final p = t.renderObject<RenderParagraph>(find.text(label));
      expect(p.size.height, greaterThanOrEqualTo(p.getMaxIntrinsicHeight(p.size.width) - .5), reason: label);
    }
  });

  testWidgets('폰 가로(844×390): 메인 버튼(높이 66) 넷이 스크롤 없이 한 화면에 든다', (t) async {
    t.view.physicalSize = const Size(844, 390);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    await t.pumpWidget(_home(Api(MockClient((_) async => http.Response('', 500)))));
    await settle(t);
    expect(t.getRect(find.text('Single player')).bottom, lessThan(390));
    expect(t.getSize(find.ancestor(of: find.text('Single player'), matching: find.byType(FilledButton))).height, 66);
    // 상단 바(11-28): 앱바 높이만큼 깔린다 — 비우면 높이 0으로 줄어 안 보였다
    expect(t.getSize(find.byKey(const ValueKey('home-top-bar'))).height, t.getSize(find.byType(AppBar)).height);
    // 사용자 '이렇게 고정' — 옵션 버튼까지 통째로 보인다(글자만이 아니라 판 전체)
    expect(t.getRect(find.ancestor(of: find.text('Options'), matching: find.byType(OutlinedButton))).bottom, lessThanOrEqualTo(390));
    await t.tap(find.text('Options'));
    await settle(t);
    expect(find.byType(OptionsScreen), findsOneWidget);
  });

  test('기본 배경은 게임판 종이 구름(2)·시작 화면 찻집 창가(15), 없음을 골랐으면 그대로 없음', () async {
    SharedPreferences.setMockInitialValues({});
    await Settings.load();
    expect(Settings.tableBg.value, 2);
    expect(Settings.homeBg.value, 15);
    SharedPreferences.setMockInitialValues({'tableBg': 0, 'homeBg': 0});
    await Settings.load();
    expect((Settings.tableBg.value, Settings.homeBg.value), (0, 0));
  });

  testWidgets('웹 세로 창은 가로로 돌려 달라고 가리고, 돌리면 같은 화면이 이어진다', (t) async {
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final focus = FocusNode();
    addTearDown(focus.dispose);
    Widget app() => MaterialApp(
      locale: const Locale('ko'),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      builder: (context, child) => RotateGate(child: child!),
      home: Scaffold(body: TextField(focusNode: focus)),
    );
    t.view.physicalSize = const Size(844, 390);
    await t.pumpWidget(app());
    focus.requestFocus();
    await t.pump();
    expect(focus.hasFocus, isTrue);
    t.view.physicalSize = const Size(390, 844);
    await t.pump();
    expect(find.text('화면을 가로로 돌려 주세요'), findsOneWidget);
    expect(find.byType(TextField), findsNothing); // 가려짐(Offstage)
    expect(focus.hasFocus, isFalse); // 가려진 입력란에 타이핑되지 않게
    t.view.physicalSize = const Size(844, 390);
    await t.pump();
    expect(find.byKey(const ValueKey('rotate')), findsNothing);
    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('옵션에서 중국어(간체)를 고르면 화면이 바로 중국어로', (t) async {
    SharedPreferences.setMockInitialValues({});
    await Settings.load();
    Auth.client = AuthClient(
      MockClient(
        (r) async => r.url.path == '/api/auth/me'
            ? http.Response(jsonEncode({'id': 1, 'email': 'me@x.com', 'nickname': 'me'}), 200)
            : http.Response('{}', 404),
      ),
    );
    await t.pumpWidget(const KumonijiApp());
    await settle(t);
    await t.tap(find.byKey(const ValueKey('open-options')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('language')));
    await settle(t);
    await t.tap(find.byKey(const ValueKey('locale-zh')));
    await settle(t);
    expect(find.text('设置'), findsOneWidget);
    expect((await SharedPreferences.getInstance()).getString('locale'), 'zh');
    await t.tap(find.byType(BackButton));
    await settle(t);
    expect(find.text('单人模式'), findsOneWidget);
    Settings.locale.value = null;
  });
}
