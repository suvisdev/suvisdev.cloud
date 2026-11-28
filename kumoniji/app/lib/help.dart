import 'package:flutter/material.dart';

import 'l10n/app_localizations.dart';
import 'practice.dart';
import 'tile.dart';

const _ink = Color(0xFF42384C);

/// 처음 하는 사람을 위한 설명 카드(넘겨 보는 5장). 글보다 실제 패 그림으로 보여 준다.
/// 예시 조합은 서버 규칙(classify·beats)으로 확인한 것만 쓴다.
Future<void> showHelp(BuildContext context) => showDialog(context: context, builder: (_) => const _HelpCards());

Widget _tiles(List<String> codes, {double w = 34}) => Wrap(
  spacing: 3,
  runSpacing: 3,
  children: [for (final c in codes) TileView(code: c, width: w)],
);

/// 설명을 줄마다 글머리 한 줄로(문구의 \n이 줄 나눔) — 긴 한 덩어리 글을 읽기 쉽게(11-26 사용자)
Widget _points(String body) => Column(
  crossAxisAlignment: CrossAxisAlignment.start,
  spacing: 8,
  children: [
    for (final line in body.split('\n'))
      Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 8, right: 8),
            child: CircleAvatar(radius: 3, backgroundColor: Color(0xFFC9A24A)),
          ),
          Expanded(
            child: Text(line, style: const TextStyle(fontSize: 15, height: 1.45, color: _ink)),
          ),
        ],
      ),
  ],
);

Widget _small(String s) => Text(s, style: const TextStyle(fontSize: 12, color: _ink));

Widget _mark(bool ok) => Text(
  ok ? '✓' : '✗',
  style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: ok ? Colors.green.shade700 : Colors.red.shade700),
);

class _HelpCards extends StatefulWidget {
  const _HelpCards();

  @override
  State<_HelpCards> createState() => _HelpCardsState();
}

class _HelpCardsState extends State<_HelpCards> {
  final pc = PageController();
  int page = 0;

  @override
  void dispose() {
    pc.dispose();
    super.dispose();
  }

  List<(String, Widget, String)> _cards(AppLocalizations t) => [
    (t.help1t, Center(child: _tiles(List.filled(13, 'back'), w: 19)), t.help1b),
    (
      t.help2t,
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            runSpacing: 4,
            children: [
              Column(
                children: [
                  const TileView(code: 'c1', width: 34),
                  _small(t.weak),
                ],
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12),
                child: Text('→', style: TextStyle(fontSize: 20, color: _ink)),
              ),
              for (final (c, n) in [('m11', t.cloud), ('m12', t.rainbow), ('m13', t.sun)])
                Padding(
                  padding: const EdgeInsets.only(left: 4),
                  child: Column(
                    children: [
                      TileView(code: c, width: 34),
                      _small(n),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          // 나란히 놓는 좁은 칸에서도 넘치지 않게 줄바꿈(Wrap)
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            runSpacing: 4,
            children: [
              for (final (i, s) in ['m', 's', 'l', 'c'].indexed) ...[
                if (i > 0)
                  const Text(
                    ' > ',
                    style: TextStyle(fontWeight: FontWeight.bold, color: _ink),
                  ),
                Column(children: [TileView(code: '${s}7', width: 30)]),
              ],
              const SizedBox(width: 8),
              _small(t.strong),
            ],
          ),
        ],
      ),
      t.help2b,
    ),
    (
      t.help3t,
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 좁은 그림 칸·큰 글자에서도 잘리지 않게 줄바꿈(Wrap, 로고 PR 리뷰 1차)
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            runSpacing: 4,
            children: [
              Column(
                children: [
                  _small(t.tableLabel),
                  const TileView(code: 'l7', width: 34),
                ],
              ),
              const SizedBox(width: 12),
              const Text('→', style: TextStyle(fontSize: 20, color: _ink)),
              const SizedBox(width: 12),
              const TileView(code: 's7', width: 34),
              _mark(true),
              const SizedBox(width: 10),
              const TileView(code: 'c7', width: 34),
              _mark(false),
            ],
          ),
          const SizedBox(height: 8),
          // 좁은 그림 칸·큰 글자에서도 잘리지 않게 줄바꿈(Wrap, 로고 PR 리뷰 1차)
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            runSpacing: 4,
            children: [
              _tiles(['c5', 'l5'], w: 30),
              const SizedBox(width: 12),
              const Text('→', style: TextStyle(fontSize: 20, color: _ink)),
              const SizedBox(width: 12),
              _tiles(['s5', 'c5'], w: 30),
              _mark(true),
            ],
          ),
        ],
      ),
      t.help3b,
    ),
    (
      t.help4t,
      Column(
        children: [
          for (final (name, codes) in fiveCombos(t))
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                children: [
                  Expanded(child: _small(name)),
                  _tiles(codes, w: 22),
                ],
              ),
            ),
        ],
      ),
      t.help4b,
    ),
    (
      t.help5t,
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _small(t.exampleLeft),
          const SizedBox(height: 4),
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            runSpacing: 4,
            children: [
              // 패마다 몇 점인지 아래에 — 글로 읽지 않아도 1·2·4·5점이 보이게(11-26 사용자: 가독성)
              for (final (c, p) in [('c3', 1), ('l9', 2), ('m11', 4), ('s13', 5)])
                Padding(
                  padding: const EdgeInsets.only(right: 3),
                  child: Column(
                    children: [
                      TileView(code: c, width: 30),
                      _small('+$p'),
                    ],
                  ),
                ),
              const SizedBox(width: 8),
              scoreIcon('petal', size: 18),
              const Text('×1', style: TextStyle(color: _ink)),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            t.scoreExample,
            style: const TextStyle(fontWeight: FontWeight.bold, color: _ink),
          ),
        ],
      ),
      t.help5b,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final cards = _cards(t);
    final last = page == cards.length - 1;
    return Dialog(
      insetPadding: const EdgeInsets.all(16),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 680, maxHeight: 560),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
          child: Column(
            children: [
              Row(
                children: [
                  const SizedBox(width: 40), // 오른쪽 X와 균형 — 제목이 가운데 오게
                  Expanded(
                    child: Text(t.help, textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleMedium),
                  ),
                  IconButton(
                    tooltip: MaterialLocalizations.of(context).closeButtonTooltip,
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              Expanded(
                child: PageView(
                  controller: pc,
                  onPageChanged: (i) => setState(() => page = i),
                  children: [
                    for (final (i, (title, visual, body)) in cards.indexed)
                      // 가로 화면(앱 기본)에선 그림 | 설명을 나란히 — 위아래로 쌓으면 낮은 화면에서 설명이 스크롤 밑으로 밀린다
                      LayoutBuilder(
                        builder: (_, box) {
                          final head = Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold));
                          final text = _points(body);
                          // 낮은 창(가로 분할 화면 등)이면 제목까지 함께 스크롤되게 한 칸으로(로고 PR 리뷰 2차)
                          if (box.maxWidth < 520 || box.maxHeight < 160) {
                            return SingleChildScrollView(
                              primary: i == page,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [head, const SizedBox(height: 12), visual, const SizedBox(height: 12), text],
                              ),
                            );
                          }
                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              head,
                              const SizedBox(height: 12),
                              // 그림과 설명을 한 스크롤로 — 키보드 Page Down이 긴 설명도, 왼쪽 아래 조합 예시도 함께 내린다.
                              // 칸마다 따로 스크롤하면 기본 컨트롤러가 한쪽에만 붙어 다른 쪽은 키보드로 못 내린다(리뷰 2~4차)
                              Expanded(
                                child: SingleChildScrollView(
                                  // 데스크톱은 기본값이 false — 버튼에 포커스가 있어도 Page Down이 내리게. 지금 카드만 —
                                  // 넘기는 중 두 카드가 함께 붙으면 Page Down이 예외를 낸다(리뷰 5차)
                                  primary: i == page,
                                  child: Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Expanded(flex: 5, child: visual),
                                      const SizedBox(width: 20),
                                      Expanded(flex: 6, child: text),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          );
                        },
                      ),
                  ],
                ),
              ),
              Row(
                children: [
                  for (var i = 0; i < cards.length; i++)
                    Container(
                      margin: const EdgeInsets.only(right: 6),
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: i == page ? const Color(0xFFC9A24A) : const Color(0xFFE9DFD1),
                      ),
                    ),
                  const SizedBox(width: 8),
                  Expanded(
                    // 좁은 화면·큰 글자에선 버튼 줄을 한 줄 그대로 줄인다 — 밖으로 밀리거나 줄이 늘어 본문을 줄이지 않게
                    child: Align(
                      alignment: Alignment.centerRight,
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          spacing: 8,
                          children: [
                            if (page > 0)
                              TextButton(
                                onPressed: () =>
                                    pc.previousPage(duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
                                child: Text(t.helpPrev),
                              ),
                            FilledButton(
                              onPressed: () => last
                                  ? Navigator.pop(context)
                                  : pc.nextPage(duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
                              child: Text(last ? t.helpDone : t.helpNext),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
