import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'l10n/app_localizations.dart';
import 'level.dart';

/// 옵션 값(앱 전체, 기기에 기억). 저장소를 못 쓰면 기본값으로 동작한다.
/// ponytail: 배경음악·효과음은 값만 저장한다 — 소리 파일·재생기가 생기면 music/sfx를 음량으로 쓴다.
class Settings {
  static final locale = ValueNotifier<Locale?>(null); // null = 기기 언어
  static final music = ValueNotifier<double>(0.6);
  static final sfx = ValueNotifier<double>(0.8);
  static final vibration = ValueNotifier<bool>(true);

  static Future<void> load() async {
    try {
      final p = await SharedPreferences.getInstance();
      final code = p.getString('locale') ?? '';
      locale.value = code.isEmpty ? null : Locale(code);
      music.value = p.getDouble('music') ?? music.value;
      sfx.value = p.getDouble('sfx') ?? sfx.value;
      vibration.value = p.getBool('vibration') ?? vibration.value;
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
          for (final (code, name) in [('', t.systemLanguage), ('en', 'English'), ('ja', '日本語'), ('ko', '한국어')])
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
            ],
          ),
        ),
      ),
    );
  }
}
