import 'dart:ui' show PlatformDispatcher;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'account_screen.dart';
import 'l10n/app_localizations.dart';
import 'legal.dart';
import 'level.dart';

/// 옵션 값(앱 전체, 기기에 기억). 저장소를 못 쓰면 기본값으로 동작한다.
/// 배경음악은 music.dart가 music을 음량으로 쓴다. 효과음은 아직 값만 저장한다(시안 고르는 중).
class Settings {
  static final locale = ValueNotifier<Locale?>(null); // null = 기기 언어

  /// 지금 화면 언어 코드 — 서버가 메일 언어로 쓴다. 고른 언어가 없으면 기기 언어.
  static String get lang => langFor(PlatformDispatcher.instance.locales);

  /// MaterialApp과 같은 방식으로 기기 선호 언어 목록에서 앱이 지원하는 첫 언어(프랑스어·중국어 순이면 중국어).
  static String langFor(List<Locale> device) =>
      (locale.value ?? basicLocaleListResolution(device, AppLocalizations.supportedLocales)).languageCode;
  static final music = ValueNotifier<double>(0.6);
  static final sfx = ValueNotifier<double>(0.8);
  static final vibration = ValueNotifier<bool>(true);
  static final muted = ValueNotifier<bool>(false); // 배경음악·효과음을 한 번에 끔(음량 값은 그대로 둔다)
  // 배경(Codex 시안, 사용자가 고름 — 0 = 없음). 상점 판매는 화폐 뒤에 붙인다(11-26 사용자)
  static const defaultHomeBg = 15; // 시작 화면 기본은 찻집 창가(home_15, 11-27 사용자). '없음'을 고르면 0으로 기억
  static final homeBg = ValueNotifier<int>(defaultHomeBg);
  static const defaultTableBg = 2; // 게임판 기본은 종이 구름(wide-02-paper, 11-26 사용자). '없음'을 고르면 0으로 기억
  static final tableBg = ValueNotifier<int>(defaultTableBg);
  static final board = ValueNotifier<int>(0); // 게임판 윗면 그림(0 = 기본 초록 펠트, 11-26 사용자)

  /// 실제로 쓸 음량 — 음소거면 0.
  static double get musicVolume => muted.value ? 0 : music.value;
  static double get sfxVolume => muted.value ? 0 : sfx.value;

  static void toggleMute() {
    muted.value = !muted.value;
    _save((p) => p.setBool('muted', muted.value));
  }

  static Future<void> load() async {
    try {
      final p = await SharedPreferences.getInstance();
      final code = p.getString('locale') ?? '';
      locale.value = code.isEmpty ? null : Locale(code);
      music.value = p.getDouble('music') ?? music.value;
      sfx.value = p.getDouble('sfx') ?? sfx.value;
      vibration.value = p.getBool('vibration') ?? vibration.value;
      muted.value = p.getBool('muted') ?? muted.value;
      homeBg.value = (p.getInt('homeBg') ?? defaultHomeBg).clamp(0, homeBackgrounds);
      tableBg.value = (p.getInt('tableBg') ?? defaultTableBg).clamp(0, tableBackgrounds);
      board.value = (p.getInt('board') ?? 0).clamp(0, boards);
    } catch (_) {}
  }

  static Future<void> _save(void Function(SharedPreferences p) write) async {
    try {
      write(await SharedPreferences.getInstance());
    } catch (_) {}
  }

  /// 내 차례가 왔을 때 짧게 진동(휴대폰만 — 웹에서는 아무 일도 없다).
  static void buzz() {
    if (vibration.value) HapticFeedback.mediumImpact();
  }
}

// assets/backgrounds/<home|table>_N.jpg — 6~10은 세트 배경(세트 N = 배경 5+N · 판 5+N)
const homeBackgrounds = 15, tableBackgrounds = 10, boards = 10, boardSets = 5;

// 홈 6~10은 세트 배경을 같이 쓴다(11-26 사용자: 시작 화면 배경은 있는 배경으로) — 같은 파일이라 앱 크기가 늘지 않는다
// 홈 11~15는 시작 화면 전용(Codex, 11-26 사용자 요청)
String backgroundAsset(String kind, int n) =>
    kind == 'home' && n > 5 && n <= 10 ? 'assets/backgrounds/table_$n.jpg' : 'assets/backgrounds/${kind}_$n.jpg';
String boardAsset(int n) => 'assets/boards/board_$n.jpg';

/// 판 두께색 — 그림 가장자리 평균색을 어둡게(변환할 때 뽑음). 0 = 기본 펠트
const boardEdges = [
  Color(0xFFB7CA9F),
  Color(0xFF929E8E),
  Color(0xFFBD9B92),
  Color(0xFFBEA39F),
  Color(0xFFA2A5BC),
  Color(0xFFBCB1C5),
  Color(0xFFB6BDB9),
  Color(0xFFC59886),
  Color(0xFF9FB8AE),
  Color(0xFFA890A5),
  Color(0xFFC4AD90),
];

/// 글씨 대신 만든 제목 로고(11-26 사용자). 이름은 Semantics로 — Image의 semanticLabel은 따로 노드를 만들어
/// 앱바의 화면 제목(namesRoute)에 안 붙는다(로고 PR 리뷰 1차)
class TitleLogo extends StatelessWidget {
  final double height;
  const TitleLogo({super.key, this.height = 36});

  @override
  Widget build(BuildContext context) => Semantics(
    label: AppLocalizations.of(context)!.title,
    child: Image.asset('assets/brand/title_jade.png', height: height, excludeFromSemantics: true),
  );
}

/// 고른 배경을 화면 뒤에 깐다(없음이면 앱 기본 바탕색). 감싼 Scaffold는 바탕을 투명하게 둔다.
class Backdrop extends StatelessWidget {
  final String kind; // home · table
  final Widget child;
  const Backdrop({super.key, required this.kind, required this.child});

  @override
  Widget build(BuildContext context) {
    final pick = kind == 'home' ? Settings.homeBg : Settings.tableBg;
    return ValueListenableBuilder(
      valueListenable: pick,
      builder: (_, n, child) => DecoratedBox(
        key: ValueKey('backdrop-$kind-$n'),
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor,
          image: n == 0 ? null : DecorationImage(image: AssetImage(backgroundAsset(kind, n)), fit: BoxFit.cover),
        ),
        child: child,
      ),
      child: child,
    );
  }
}

/// 음소거 버튼: 배경음악·효과음을 한 번에 끄고 켠다(홈·게임 화면 위).
class MuteButton extends StatelessWidget {
  const MuteButton({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return ValueListenableBuilder(
      valueListenable: Settings.muted,
      builder: (_, muted, _) => IconButton(
        key: const ValueKey('mute'),
        tooltip: muted ? t.unmute : t.mute,
        icon: Icon(muted ? Icons.volume_off : Icons.volume_up),
        onPressed: Settings.toggleMute,
      ),
    );
  }
}

/// 옵션 화면: 언어 · 배경음악 · 효과음 · 진동.
class OptionsScreen extends StatelessWidget {
  const OptionsScreen({super.key});

  Future<void> _language(BuildContext context) async {
    final t = AppLocalizations.of(context)!;
    final current = Settings.locale.value?.languageCode ?? '';
    final code = await showDialog<String>(
      context: context,
      builder: (c) => SimpleDialog(
        title: Text(t.language),
        children: [
          // 언어 이름은 그 언어로 쓴다(잘못 골라도 되돌아올 수 있게)
          for (final (code, name) in [
            ('', t.systemLanguage),
            ('en', 'English'),
            ('ja', '日本語'),
            ('ko', '한국어'),
            ('zh', '简体中文'),
          ])
            ListTile(
              key: ValueKey('locale-$code'),
              title: Text(name, style: TextStyle(fontWeight: code == current ? FontWeight.bold : null)),
              trailing: code == current ? const Icon(Icons.check, color: gold) : null,
              onTap: () => Navigator.pop(c, code),
            ),
        ],
      ),
    );
    if (code == null) return;
    Settings.locale.value = code.isEmpty ? null : Locale(code);
    Settings._save((p) => p.setString('locale', code));
  }

  String _languageName(AppLocalizations t) => switch (Settings.locale.value?.languageCode) {
    'en' => 'English',
    'ja' => '日本語',
    'ko' => '한국어',
    'zh' => '简体中文',
    _ => t.systemLanguage,
  };

  Widget _volume(String label, IconData icon, ValueNotifier<double> v, String key) => ValueListenableBuilder(
    valueListenable: v,
    builder: (_, x, _) => ListTile(
      leading: Icon(x == 0 ? Icons.volume_off : icon),
      title: Text(label),
      subtitle: Slider(
        key: ValueKey(key),
        value: x,
        divisions: 10,
        label: '${(x * 100).round()}',
        onChanged: (n) => v.value = n,
        onChangeEnd: (n) => Settings._save((p) => p.setDouble(key, n)),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(t.options), backgroundColor: Colors.transparent),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: ListView(
            children: [
              ListTile(
                key: const ValueKey('account'),
                leading: const Icon(Icons.account_circle),
                title: Text(t.account),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AccountScreen())),
              ),
              const Divider(),
              ListTile(
                key: const ValueKey('language'),
                leading: const Icon(Icons.language),
                title: Text(t.language),
                trailing: Text(_languageName(t)),
                onTap: () => _language(context),
              ),
              const Divider(),
              _volume(t.music, Icons.music_note, Settings.music, 'music'),
              _volume(t.sfx, Icons.volume_up, Settings.sfx, 'sfx'),
              const Divider(),
              ValueListenableBuilder(
                valueListenable: Settings.vibration,
                builder: (_, on, _) => SwitchListTile(
                  key: const ValueKey('vibration'),
                  secondary: const Icon(Icons.vibration),
                  title: Text(t.vibration),
                  subtitle: Text(t.vibrationDesc),
                  value: on,
                  onChanged: (v) {
                    Settings.vibration.value = v;
                    Settings._save((p) => p.setBool('vibration', v));
                    if (v) Settings.buzz();
                  },
                ),
              ),
              const Divider(),
              ListTile(
                key: const ValueKey('terms'),
                leading: const Icon(Icons.description_outlined),
                title: Text(t.terms),
                onTap: () => openLegal(context, Legal.terms),
              ),
              ListTile(
                key: const ValueKey('privacy'),
                leading: const Icon(Icons.privacy_tip_outlined),
                title: Text(t.privacy),
                onTap: () => openLegal(context, Legal.privacy),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 그림 고르기 창 — 0번은 '없음/기본' 글자 칸. 고른 번호(닫으면 null)
Future<int?> _pickArt(
  BuildContext context,
  String title,
  int count,
  int now,
  String key,
  String none,
  String Function(int) asset,
  double w,
  double h,
) => showDialog<int>(
  context: context,
  builder: (c) => AlertDialog(
    title: Text(title),
    scrollable: true,
    content: Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (var i = 0; i <= count; i++)
          if (i > 0 || none.isNotEmpty)
            Semantics(
              button: true,
              selected: i == now,
              label: i == 0 ? none : '$title $i',
              excludeSemantics: true,
              onTap: () => Navigator.pop(c, i),
              child: InkWell(
                key: ValueKey('$key-$i'),
                onTap: () => Navigator.pop(c, i),
                child: Container(
                  width: w,
                  height: h,
                  decoration: BoxDecoration(
                    color: i == 0 ? const Color(0xFFE6F0DC) : null,
                    image: i == 0 ? null : DecorationImage(image: AssetImage(asset(i)), fit: BoxFit.cover),
                    border: Border.all(color: i == now ? gold : Colors.black12, width: i == now ? 3 : 1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  alignment: Alignment.center,
                  child: i == 0 ? Text(none) : null,
                ),
              ),
            ),
      ],
    ),
  ),
);

/// 게임판 윗면 고르기(게임 화면 꾸미기 버튼)
Future<void> pickBoard(BuildContext context) async {
  final t = AppLocalizations.of(context)!;
  final n = await _pickArt(context, t.board, boards, Settings.board.value, 'board', t.defaultBoard, boardAsset, 72, 72);
  if (n == null) return;
  Settings.board.value = n;
  Settings._save((p) => p.setInt('board', n));
}

/// 세트: 배경과 판을 한 번에(세트 N = 게임 화면 배경 5+N · 판 5+N)
Future<void> pickBoardSet(BuildContext context) async {
  final t = AppLocalizations.of(context)!;
  final now = Settings.board.value > 5 && Settings.tableBg.value == Settings.board.value
      ? Settings.board.value - 5
      : -1;
  final n = await _pickArt(context, t.boardSet, boardSets, now, 'set', '', (i) => 'assets/boards/set_$i.jpg', 128, 72);
  if (n == null) return;
  Settings.tableBg.value = Settings.board.value = 5 + n;
  Settings._save(
    (p) => p
      ..setInt('tableBg', 5 + n)
      ..setInt('board', 5 + n),
  );
}

/// 배경 고르기 — 옵션이 아니라 그 화면의 버튼에서(홈은 시작 화면, table은 게임 화면, 11-27 사용자)
Future<void> pickBackground(BuildContext context, String kind) async {
  final t = AppLocalizations.of(context)!;
  final title = kind == 'home' ? t.homeBackground : t.tableBackground;
  final pick = kind == 'home' ? Settings.homeBg : Settings.tableBg;
  final n = await showDialog<int>(
    context: context,
    builder: (c) => AlertDialog(
      title: Text(title),
      scrollable: true,
      content: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (var i = 0; i <= (kind == 'home' ? homeBackgrounds : tableBackgrounds); i++)
            // 그림·테두리만으론 화면 읽기가 구분 못 한다 — 이름(없음 / 홈 배경 3)과 고른 상태를 알린다
            Semantics(
              button: true,
              selected: i == pick.value,
              label: i == 0 ? t.noBackground : '$title $i',
              excludeSemantics: true, // 안쪽 InkWell의 탭 동작도 빠지므로 여기서 다시 준다
              onTap: () => Navigator.pop(c, i),
              child: InkWell(
                key: ValueKey('bg-$kind-$i'),
                onTap: () => Navigator.pop(c, i),
                child: Container(
                  width: kind == 'home' ? 128 : 72,
                  height: 72,
                  decoration: BoxDecoration(
                    color: Theme.of(c).scaffoldBackgroundColor,
                    image: i == 0
                        ? null
                        : DecorationImage(image: AssetImage(backgroundAsset(kind, i)), fit: BoxFit.cover),
                    border: Border.all(color: i == pick.value ? gold : Colors.black12, width: i == pick.value ? 3 : 1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  alignment: Alignment.center,
                  child: i == 0 ? Text(t.noBackground) : null,
                ),
              ),
            ),
        ],
      ),
    ),
  );
  if (n == null) return;
  pick.value = n;
  Settings._save((p) => p.setInt('${kind}Bg', n));
}
