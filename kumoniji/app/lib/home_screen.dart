import 'package:flutter/material.dart';

import 'api.dart';
import 'help.dart';
import 'l10n/app_localizations.dart';
import 'level.dart';
import 'settings.dart';
import 'table_screen.dart';
import 'tile.dart';
import 'wallet.dart';

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
    return Backdrop(
      kind: 'home',
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          automaticallyImplyLeading: false,
          // 왼쪽 위에도 이름 — 글씨가 아니라 만든 제목 로고로(11-26 사용자)
          // 이름은 Semantics로 — Image의 semanticLabel은 따로 노드를 만들어 앱바의 화면 제목(namesRoute)에 안 붙는다(리뷰 1차)
          title: const Row(
            children: [
              // 좁은 창에선 로고도 잔고와 함께 줄어든다(280px에서 넘침)
              Flexible(child: TitleLogo()),
              SizedBox(width: 12),
              Flexible(child: WalletBar()),
            ],
          ),
          centerTitle: false,
          actions: [
            IconButton(
              key: const ValueKey('open-missions'),
              tooltip: t.missions,
              icon: const Icon(Icons.event_available),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const MissionsScreen())),
            ),
            IconButton(
              key: const ValueKey('open-shop'),
              tooltip: t.shop,
              icon: const Icon(Icons.storefront),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ShopScreen())),
            ),
            const MuteButton(),
            const SizedBox(width: 4),
          ],
        ),
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 320),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // 제목 로고가 위, 패 넷이 아래(11-26 사용자)
                    // 제목 로고(Codex 그림, 원본 kumoniji/_docs/brand/title_jade_original.png). 글자는 한국어 하나 — 화면 읽기는 언어별 제목
                    Image.asset('assets/brand/title_jade.png', semanticLabel: t.title),
                    const SizedBox(height: 16),
                    FittedBox(
                      fit: BoxFit.scaleDown, // 아주 좁은 창에선 네 장을 함께 줄인다
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // 무늬 넷 하나씩 — 산·벚꽃은 해(13), 잎사귀는 무지개(12), 솜사탕은 구름(11)(11-25 사용자)
                          for (final c in ['m13', 's13', 'l12', 'c11']) TileView(code: c, width: 64),
                        ],
                      ),
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
                      onPressed: () =>
                          Navigator.push(context, MaterialPageRoute(builder: (_) => const OptionsScreen())),
                      icon: const Icon(Icons.settings),
                      label: Text(t.options),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
