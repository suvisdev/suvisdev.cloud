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
          Row(
            children: [
              Column(
                children: [
                  const TileView(code: 'c1', width: 34),
                  _small(t.weak),
                ],
              ),
              const Expanded(
                child: Center(
                  child: Text('→', style: TextStyle(fontSize: 20, color: _ink)),
                ),
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
          Row(
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
          Row(
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
          Row(
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
          Row(
            children: [
              _tiles(['c3', 'l9', 'm11', 's13'], w: 30),
              const SizedBox(width: 8),
              const Text('🌸×1', style: TextStyle(color: _ink)),
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
        constraints: const BoxConstraints(maxWidth: 420, maxHeight: 560),
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
                    for (final (title, visual, body) in cards)
                      SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                            const SizedBox(height: 12),
                            visual,
                            const SizedBox(height: 12),
                            Text(body, style: const TextStyle(fontSize: 14, height: 1.5)),
                          ],
                        ),
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
