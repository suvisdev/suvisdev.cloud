import 'package:flutter/material.dart';

import 'api.dart';
import 'help.dart';
import 'l10n/app_localizations.dart';
import 'level.dart';
import 'settings.dart';
import 'table_screen.dart';
import 'tile.dart';

const _ink = Color(0xFF42384C);

/// 첫 화면: 싱글 · 멀티(준비 중) · 게임 방법 · 옵션.
/// 종료 버튼은 두지 않는다 — 웹은 탭을 스스로 닫을 수 없고, iOS는 앱 안 종료 버튼을 권하지 않는다.
class HomeScreen extends StatelessWidget {
  final Api? api;
  final bool showHelpOnFirstVisit;
  const HomeScreen({super.key, this.api, this.showHelpOnFirstVisit = true});

  Future<void> _single(BuildContext context) async {
    final last = await savedLevel();
    if (!context.mounted) return;
    final level = await pickLevel(context, current: last);
    if (level == null || !context.mounted) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => TableScreen(api: api, level: level, showHelpOnFirstVisit: showHelpOnFirstVisit),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final big = Theme.of(context).textTheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 320),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      for (final c in ['c11', 's12', 'm13']) TileView(code: c, width: 64),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    t.title,
                    textAlign: TextAlign.center,
                    style: big.headlineLarge?.copyWith(fontWeight: FontWeight.bold, color: _ink),
                  ),
                  const SizedBox(height: 40),
                  FilledButton.icon(
                    style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                    onPressed: () => _single(context),
                    icon: const Icon(Icons.person),
                    label: Text(t.singleMode),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                    onPressed: null, // 2단계(4인 멀티)에서 연결
                    icon: const Icon(Icons.groups),
                    label: Text('${t.multiMode} · ${t.comingSoon}'),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                    onPressed: () => showHelp(context),
                    icon: const Icon(Icons.help_outline),
                    label: Text(t.help),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                    onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const OptionsScreen())),
                    icon: const Icon(Icons.settings),
                    label: Text(t.options),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
