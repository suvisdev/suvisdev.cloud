import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
          // 배경 그림 위에서 잔고·아이콘이 묻혀 상단 바를 깐다(11-28 사용자) — 메인 버튼 판(Codex B안)과 같은
          // 크림 바탕·비취 테두리. 그림이 아니라 코드로 그려 창 폭이 달라도 늘어나지 않는다
          // 바가 상태 표시줄 칸까지 크림색이라 시계·배터리는 어두운 아이콘으로(리뷰 1차)
          systemOverlayStyle: SystemUiOverlayStyle.dark,
          flexibleSpace: const DecoratedBox(
            key: ValueKey('home-top-bar'),
            decoration: BoxDecoration(
              color: Color(0xD9FBF1DE),
              borderRadius: BorderRadius.vertical(bottom: Radius.circular(22)),
              border: Border(bottom: BorderSide(color: Color(0xFF8DB7A6), width: 3)),
              boxShadow: [BoxShadow(color: Color(0x334A3426), blurRadius: 10, offset: Offset(0, 3))],
            ),
            child: SizedBox.expand(), // 앱바는 flexibleSpace에 느슨한 제약을 줘서, 비워 두면 높이 0으로 줄어든다
          ),
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
          // 순서: 미션·출석 / 상점 / 프로필(11-28 사용자, 옵션은 아래 큰 버튼). 음소거는 빼고(음량은 옵션), 홈 배경은 옵션 안으로.
          actions: [
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
            // 간단한 프로필 — 닉네임 첫 글자. 누르면 계정 화면(닉네임·비밀번호 바꾸기, 11-27 사용자)
            ValueListenableBuilder(
              valueListenable: Auth.me,
              // 아주 좁은 창(360px 아래)에선 뺀다 — 아이콘들이 제목 줄을 밀어 잔고가 안 보인다(리뷰 9차). 계정은 옵션 → 계정
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
            const SizedBox(width: 4),
          ],
        ),
        body: SafeArea(
          // 앱은 가로 고정이라 폰에선 높이가 낮다(844×390이면 본문 ~330) — 세로로 쌓으면 버튼이 화면 밖으로 밀려
          // 싱글만 반쯤 보인다. 낮으면 왼쪽 로고·패 | 오른쪽 버튼 두 칸으로(11-27 사용자 '전체 앱에 맞춰')
          child: LayoutBuilder(
            builder: (context, box) {
              final low = box.maxHeight < 560;
              // 낮은 폰 가로(740×360 등)에서도 넷이 한 화면에 들게 버튼 높이를 남은 높이에 맞춘다(최대 66, 최소 48).
              // 위아래 여백 12+12, 간격 14×3
              final h = low ? ((box.maxHeight - 24 - 42) / 4).clamp(48.0, 66.0) : 66.0;
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
              // 메인 버튼: 1.5배(높이 78·글자 21)에서 살짝 줄임(11-28 사용자) — 높이 66·글자 19·간격 14. 폰 가로에서 넷이 한 화면에 든다(사용자 '이렇게 고정').
              // 판은 Codex 그림 B안(크림 도자기·비취 테두리, 11-28 사용자) — 아이콘은 판 그림 왼쪽에 있어 글자만 쓴다
              final label = Theme.of(context).textTheme.labelLarge?.copyWith(fontSize: 19, fontWeight: FontWeight.w700);
              final buttons = Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  FilledButton(
                    style: _plate('single', label, h),
                    onPressed: () => _single(context),
                    child: _label(t.singleMode),
                  ),
                  const SizedBox(height: 14),
                  OutlinedButton(
                    style: _plate('multi', label, h),
                    onPressed: null, // 2단계(4인 멀티)에서 연결 — 준비 중이라 판째 흐리게
                    child: _label('${t.multiMode} · ${t.comingSoon}'),
                  ),
                  const SizedBox(height: 14),
                  OutlinedButton(style: _plate('help', label, h), onPressed: () => showHelp(context), child: _label(t.help)),
                  const SizedBox(height: 14),
                  OutlinedButton(
                    key: const ValueKey('open-options'),
                    style: _plate('options', label, h),
                    onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const OptionsScreen())),
                    child: _label(t.options),
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

/// 메인 버튼 글자 — 한 줄로, 넘치면 줄여서 판 높이 안에 둔다(큰 글자 설정·긴 언어에서 두 줄로 판을 넘지 않게)
Widget _label(String text) => FittedBox(fit: BoxFit.scaleDown, child: Text(text, maxLines: 1));

/// 홈 버튼 아이콘(Codex 그림 b안, 11-27 사용자). 원본 512px는 바탕화면 `타일게임_기획/홈버튼아이콘_Codex`
Widget _icon(String name) => Image.asset('assets/icons/home/$name.png', width: 28, height: 28);

/// 메인 버튼 판 그림(Codex B안, 원본 1200×280은 바탕화면 `타일게임_기획/메인버튼_Codex`). 왼쪽 약 22%가 아이콘 자리라
/// 글자는 그 오른쪽에. 누를 수 없으면(준비 중) 판째 흐리게
ButtonStyle _plate(String name, TextStyle? label, double height) => ButtonStyle(
  minimumSize: WidgetStatePropertyAll(Size.fromHeight(height)),
  // 높이도 막아야 _label(FittedBox)이 짧은 글자(Options 등)를 큰 글자 설정에서 높이에 맞춰 줄인다(가로만 보면 안 줄어든다)
  maximumSize: WidgetStatePropertyAll(Size(double.infinity, height)),
  padding: const WidgetStatePropertyAll(EdgeInsets.only(left: 76, right: 16)),
  textStyle: WidgetStatePropertyAll(label),
  foregroundColor: const WidgetStatePropertyAll(Color(0xFF4A3426)),
  backgroundColor: const WidgetStatePropertyAll(Colors.transparent),
  overlayColor: WidgetStatePropertyAll(const Color(0xFF4A3426).withValues(alpha: .08)),
  elevation: const WidgetStatePropertyAll(0),
  side: const WidgetStatePropertyAll(BorderSide.none),
  shape: const WidgetStatePropertyAll(StadiumBorder()),
  backgroundBuilder: (_, states, child) {
    final dim = states.contains(WidgetState.disabled) ? .5 : 1.0;
    // Ink로 그려야 포커스·눌림 효과가 그림 위에 보인다(DecoratedBox면 가려짐, 리뷰 1차). Ink는 위쪽 Material에 그려져
    // 바깥 Opacity가 안 먹으므로 흐리게 하기는 그림과 글자에 따로 건다(리뷰 2차)
    return Ink(
      decoration: BoxDecoration(
        image: DecorationImage(image: AssetImage('assets/buttons/$name.png'), fit: BoxFit.fill, opacity: dim),
      ),
      child: Opacity(opacity: dim, child: child),
    );
  },
);
