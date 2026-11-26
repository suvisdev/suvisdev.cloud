import 'dart:ui' show PlatformDispatcher;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'account_screen.dart';
import 'l10n/app_localizations.dart';
import 'level.dart';

/// 옵션 값(앱 전체, 기기에 기억). 저장소를 못 쓰면 기본값으로 동작한다.
/// ponytail: 배경음악·효과음은 값만 저장한다 — 소리 파일·재생기가 생기면 music/sfx를 음량으로 쓴다.
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
  // 배경(Codex 시안 5장씩, 사용자가 고름 — 기본 배경 없음, 0 = 없음). 상점 판매는 화폐 뒤에 붙인다(11-26 사용자)
  static final homeBg = ValueNotifier<int>(0);
  static final tableBg = ValueNotifier<int>(0);

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
      homeBg.value = (p.getInt('homeBg') ?? 0).clamp(0, backgrounds);
      tableBg.value = (p.getInt('tableBg') ?? 0).clamp(0, backgrounds);
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

const backgrounds = 5; // 종류마다 assets/backgrounds/<home|table>_1..5.jpg

String backgroundAsset(String kind, int n) => 'assets/backgrounds/${kind}_$n.jpg';

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

  Future<void> _background(BuildContext context, String kind, String title) async {
    final t = AppLocalizations.of(context)!;
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
            for (var i = 0; i <= backgrounds; i++)
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
                      border: Border.all(
                        color: i == pick.value ? gold : Colors.black12,
                        width: i == pick.value ? 3 : 1,
                      ),
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
              for (final (kind, title, icon) in [
                ('home', t.homeBackground, Icons.wallpaper),
                ('table', t.tableBackground, Icons.grid_view),
              ])
                ValueListenableBuilder(
                  valueListenable: kind == 'home' ? Settings.homeBg : Settings.tableBg,
                  builder: (_, n, _) => ListTile(
                    key: ValueKey('$kind-background'),
                    leading: Icon(icon),
                    title: Text(title),
                    trailing: Text(n == 0 ? t.noBackground : '$n'),
                    onTap: () => _background(context, kind, title),
                  ),
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
            ],
          ),
        ),
      ),
    );
  }
}
