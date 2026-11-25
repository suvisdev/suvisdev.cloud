import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import 'l10n/app_localizations.dart';
import 'tile.dart';

const _ink = Color(0xFF4A3B47);

/// 조합 예시(서버 규칙 classify·beats로 확인한 것만) — 게임 방법과 조합표가 같이 쓴다. 약한 것 → 센 것.
List<(String, List<String>)> fiveCombos(AppLocalizations t) => [
  (t.comboStraight, ['c3', 'l4', 's5', 'm6', 'c7']),
  (t.comboFullHouse, ['c9', 'l9', 's9', 'm4', 'c4']),
  (t.comboOddEven, ['c1', 'l3', 's5', 'm7', 'c9']),
  (t.comboColorStraight, ['s3', 'c4', 's5', 'c6', 's7']),
  (t.comboColorOddEven, ['l2', 'm4', 'l6', 'm8', 'l10']),
  (t.comboFour, ['c8', 'l8', 's8', 'm8', 'c2']),
  (t.comboStraightFlush, ['s4', 's5', 's6', 's7', 's8']),
  (t.comboSuitOddEven, ['m1', 'm3', 'm5', 'm7', 'm9']),
];

Widget _tiles(List<String> codes, double w) => Row(
  mainAxisSize: MainAxisSize.min,
  children: [
    for (final c in codes)
      Padding(
        padding: const EdgeInsets.only(left: 1),
        child: TileView(code: c, width: w),
      ),
  ],
);

Widget _title(String s) => Padding(
  padding: const EdgeInsets.only(bottom: 6),
  child: Text(
    s,
    style: const TextStyle(fontWeight: FontWeight.bold, color: _ink),
  ),
);

/// 조합표: 한 장·페어·트리플, 그리고 5장 조합 8가지(센 것이 위). 싱글·멀티 모두.
class ComboChart extends StatelessWidget {
  const ComboChart({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    Widget row(String name, List<String> codes) => Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(name, style: const TextStyle(fontSize: 11, color: _ink)),
          ),
          _tiles(codes, 19),
        ],
      ),
    );
    return Column(
      key: const ValueKey('combo-chart'),
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        _title(t.comboChart),
        for (final (name, codes) in fiveCombos(t).reversed) row(name, codes),
        const Divider(height: 12),
        row(t.comboTriple, ['c9', 'l9', 's9']),
        row(t.comboPair, ['c5', 'l5']),
        row(t.comboSingle, ['c7']),
        Text(t.comboChartNote, style: const TextStyle(fontSize: 10, color: _ink)),
      ],
    );
  }
}

/// 나온 패(싱글 연습 전용): 무늬 넷 × 1~13, 이미 낸 패는 채워서. 멀티는 서버가 out을 주지 않아 안 보인다.
class OutTracker extends StatelessWidget {
  final List<String> out;
  final List<String> suits;
  const OutTracker({super.key, required this.out, required this.suits});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final gone = out.toSet();
    return Column(
      key: const ValueKey('out-tracker'),
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        _title('${t.outTiles} ${out.length}/52'),
        for (final s in suits.reversed) // 무늬 순서와 같이 약한 것부터
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(
              children: [
                SvgPicture.asset('assets/icons/suit_$s.svg', width: 16, height: 16),
                const SizedBox(width: 4),
                Expanded(
                  child: Wrap(
                    spacing: 2,
                    runSpacing: 2,
                    children: [
                      for (var n = 1; n <= 13; n++)
                        Container(
                          key: ValueKey('out-$s$n'),
                          width: 18,
                          height: 18,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: gone.contains('$s$n') ? _ink : Colors.white,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: const Color(0xFFE9DFD1)),
                          ),
                          child: Text(
                            '$n',
                            style: TextStyle(fontSize: 9, color: gone.contains('$s$n') ? Colors.white : _ink),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

/// 넓은 화면: 왼쪽 나온 패(싱글만)·오른쪽 조합표를 판 옆에 늘 띄운다. 좁은 화면은 버튼으로 연다(PracticeButtons).
class PracticeFrame extends StatelessWidget {
  static const side = 240.0;
  final List<String>? out;
  final List<String> suits;
  final Widget child;
  const PracticeFrame({super.key, required this.out, required this.suits, required this.child});

  // 넓고 충분히 높을 때만 — 낮은 가로 창에서 양옆을 떼면 손패가 두 줄로 늘어 패스·내기가 밀린다(리뷰 1차)
  static bool wide(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    return size.width >= 1000 && size.height >= 720;
  }

  @override
  Widget build(BuildContext context) {
    if (!wide(context)) return child;
    Widget panel(Widget w) => SizedBox(
      width: side,
      child: SingleChildScrollView(padding: const EdgeInsets.all(10), child: w),
    );
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        panel(out == null ? const SizedBox() : OutTracker(out: out!, suits: suits)),
        Expanded(child: child),
        panel(const ComboChart()),
      ],
    );
  }
}

/// 좁은 화면: 무늬 순서 옆 작은 버튼 — 나온 패(싱글만)·조합표를 아래 시트로.
class PracticeButtons extends StatelessWidget {
  final List<String>? out;

  /// 시트가 열려 있는 동안 바뀌는 나온 패(봇 수 재생이 끝나 상태가 바뀌면 시트도 따라감)
  final ValueListenable<List<String>?> live;
  final List<String> suits;
  const PracticeButtons({super.key, required this.out, required this.live, required this.suits});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    void sheet(Widget w) => showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (_) => SafeArea(
        child: SingleChildScrollView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 16), child: w),
      ),
    );
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (out != null)
          IconButton(
            key: const ValueKey('open-out'),
            tooltip: t.outTiles,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints.tightFor(width: 30, height: 22),
            style: IconButton.styleFrom(
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ), // 48px 터치 여백이 줄을 키우지 않게 // 무늬 순서 줄보다 높아지지 않게
            icon: const Icon(Icons.grid_view, size: 20),
            onPressed: () => sheet(
              ValueListenableBuilder(
                valueListenable: live,
                builder: (_, now, _) => OutTracker(out: now ?? out!, suits: suits),
              ),
            ),
          ),
        IconButton(
          key: const ValueKey('open-combos'),
          tooltip: t.comboChart,
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints.tightFor(width: 30, height: 22),
          style: IconButton.styleFrom(tapTargetSize: MaterialTapTargetSize.shrinkWrap), // 48px 터치 여백이 줄을 키우지 않게
          icon: const Icon(Icons.list_alt, size: 20),
          onPressed: () => sheet(const ComboChart()),
        ),
      ],
    );
  }
}
