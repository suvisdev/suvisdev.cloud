import 'package:flutter/material.dart';

import 'account_screen.dart';
import 'api.dart';
import 'auth.dart';
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
            // 간단한 프로필 — 닉네임 첫 글자. 누르면 계정 화면(닉네임·비밀번호 바꾸기, 11-27 사용자)
            ValueListenableBuilder(
              valueListenable: Auth.me,
              // 아주 좁은 창(360px 아래)에선 뺀다 — 버튼 다섯이 제목 줄을 밀어 잔고가 안 보인다(리뷰 9차). 계정은 옵션 → 계정
              builder: (context, me, _) => me == null || MediaQuery.sizeOf(context).width < 360
                  ? const SizedBox.shrink()
                  : IconButton(
                      key: const ValueKey('open-profile'),
                      tooltip: '${t.profile}: ${me.nickname}',
                      icon: CircleAvatar(
                        radius: 14,
                        child: Text(me.nickname.isEmpty ? '?' : me.nickname.characters.first),
                      ),
                      onPressed: () =>
                          Navigator.push(context, MaterialPageRoute(builder: (_) => const AccountScreen())),
                    ),
            ),
            // 배경은 옵션이 아니라 이 화면에서 바로(11-27 사용자)
            IconButton(
              key: const ValueKey('home-background'),
              tooltip: t.homeBackground,
              icon: _icon('background'),
              onPressed: () => pickBackground(context, 'home'),
            ),
            IconButton(
              key: const ValueKey('open-missions'),
              tooltip: t.missions,
              icon: _icon('missions'),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const MissionsScreen())),
            ),
            IconButton(
              key: const ValueKey('open-shop'),
              tooltip: t.shop,
              icon: _icon('shop'),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ShopScreen())),
            ),
            const MuteButton(),
            const SizedBox(width: 4),
          ],
        ),
        body: SafeArea(
          // 앱은 가로 고정이라 폰에선 높이가 낮다(844×390이면 본문 ~330) — 세로로 쌓으면 버튼이 화면 밖으로 밀려
          // 싱글만 반쯤 보인다. 낮으면 왼쪽 로고·패 | 오른쪽 버튼 두 칸으로(11-27 사용자 '전체 앱에 맞춰')
          child: LayoutBuilder(
            builder: (context, box) {
              final low = box.maxHeight < 560;
              final title = Column(
                mainAxisSize: MainAxisSize.min,
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
                ],
              );
              // 메인 버튼은 1.5배(11-28 사용자) — 높이 78·아이콘 42·글자 21. 폰 가로에선 버튼 칸이 스크롤된다
              final label = Theme.of(context).textTheme.labelLarge?.copyWith(fontSize: 21);
              final buttons = Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  FilledButton.icon(
                    style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(78), textStyle: label),
                    onPressed: () => _single(context),
                    icon: _icon('single', 42),
                    label: Text(t.singleMode),
                  ),
                  const SizedBox(height: 18),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(78), textStyle: label),
                    onPressed: null, // 2단계(4인 멀티)에서 연결
                    icon: Opacity(opacity: .5, child: _icon('multi', 42)), // 준비 중 — 흐리게
                    label: Text('${t.multiMode} · ${t.comingSoon}'),
                  ),
                  const SizedBox(height: 18),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(78), textStyle: label),
                    onPressed: () => showHelp(context),
                    icon: _icon('help', 42),
                    label: Text(t.help),
                  ),
                  const SizedBox(height: 18),
                  OutlinedButton.icon(
                    key: const ValueKey('open-options'),
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(78), textStyle: label),
                    onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const OptionsScreen())),
                    icon: _icon('options', 42),
                    label: Text(t.options),
                  ),
                ],
              );
              return Center(
                child: SingleChildScrollView(
                  padding: EdgeInsets.symmetric(horizontal: 24, vertical: low ? 12 : 32),
                  child: low
                      ? ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 680),
                          child: Row(
                            children: [
                              Expanded(child: title),
                              const SizedBox(width: 32),
                              Expanded(child: buttons),
                            ],
                          ),
                        )
                      : ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 320),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [title, const SizedBox(height: 40), buttons],
                          ),
                        ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

/// 홈 버튼 아이콘(Codex 그림 b안, 11-27 사용자). 원본 512px는 바탕화면 `타일게임_기획/홈버튼아이콘_Codex`
Widget _icon(String name, [double size = 28]) => Image.asset('assets/icons/home/$name.png', width: size, height: size);
