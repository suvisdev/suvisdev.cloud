import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'l10n/app_localizations.dart';
import 'tile.dart';

const _ink = Color(0xFF4A3B47);

/// 조합 예시(서버 규칙 classify·beats로 확인한 것만) — 게임 방법과 조합표가 같이 쓴다. 약한 것 → 센 것.
List<(String, List<String>)> fiveCombos(AppLocalizations t) => [
  (t.comboStraight, ['c3', 'l4', 's5', 'm6', 'c7']),
  (t.comboFullHouse, ['c9', 'l9', 's9', 'm4', 'c4']),
  (t.comboOddEven, ['c1', 'l3', 's5', 'm7', 'c9']),
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

/// 나온 패 크게 보기 창의 이름 — 결과를 띄울 때 이것과 연습 시트만 닫는다.
const outBigRoute = 'out-big';

/// 조합표: 5장 조합 8가지(센 것이 위)와 한 장·페어·트리플. 싱글·멀티 모두.
/// 이름 아래에 패를 크게(11-25 사용자 "좀 더 크게, 보기 편하게"), 넓으면(시트) 두 칸으로.
class ComboChart extends StatelessWidget {
  const ComboChart({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return LayoutBuilder(
      builder: (context, box) {
        final cols = box.maxWidth >= 560 ? 2 : 1;
        final colW = (box.maxWidth - 16 * (cols - 1)) / cols;
        final tileW = min(36.0, (colW - 4) / 5 - 1);
        Widget item(String name, List<String> codes) => SizedBox(
          width: colW,
          child: Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: _ink),
                ),
                const SizedBox(height: 3),
                _tiles(codes, tileW),
              ],
            ),
          ),
        );
        return Column(
          key: const ValueKey('combo-chart'),
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            _title(t.comboChart),
            Wrap(
              spacing: 16,
              children: [
                for (final (name, codes) in fiveCombos(t).reversed) item(name, codes),
                item(t.comboTriple, ['c9', 'l9', 's9']),
                item(t.comboPair, ['c5', 'l5']),
                item(t.comboSingle, ['c7']),
              ],
            ),
            Text(t.comboChartNote, style: const TextStyle(fontSize: 12, color: _ink)),
          ],
        );
      },
    );
  }
}

/// 나온 패(싱글 연습 전용): 무늬마다 1~13을 실제 패 그림으로(11-25 사용자), 이미 나온 패는 또렷하게·아직은 흐리게.
/// 폭이 되면 한 줄에 13장, 아니면 7장씩. 멀티는 서버가 out을 주지 않아 안 보인다.
class OutTracker extends StatelessWidget {
  final List<String> out;
  final List<String> suits;

  /// 있으면 제목 옆에 '크게 보기' 버튼(좁은 옆 패널에선 한 줄 13장이 작다, 11-26 사용자)
  final VoidCallback? onOpen;
  const OutTracker({super.key, required this.out, required this.suits, this.onOpen});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final gone = out.toSet();
    return LayoutBuilder(
      builder: (context, box) {
        // 무늬마다 한 줄(13장, 11-26 사용자) — 폭에 맞춰 패를 줄인다. 좁은 패널에서 작으면 제목 옆 버튼으로 크게 연다
        const left = 10.0; // 패가 패널 왼쪽 끝에 붙지 않게(11-26 사용자)
        const gap = 3.0;
        // 크게 보기 버튼이 있는 옆 패널만 13장 한 줄로 줄인다. 버튼 없는 곳(좁은 화면의 시트·크게 본 창)은 좁으면 두 줄로
        // 나눠 패를 키운다 — 390px 시트에서 24px로 줄어 무늬가 안 보이던 문제(리뷰 3차)
        final per = onOpen != null || box.maxWidth - left >= 13 * 32 ? 13 : 7;
        final tileW = min(44.0, (box.maxWidth - left) / per - gap);
        return Column(
          key: const ValueKey('out-tracker'),
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Expanded(child: _title('${t.outTiles} ${out.length}/52')),
                if (onOpen != null)
                  IconButton(
                    key: const ValueKey('out-big'),
                    tooltip: t.outTiles,
                    visualDensity: VisualDensity.compact,
                    icon: const Icon(Icons.open_in_full, size: 18),
                    onPressed: onOpen,
                  ),
              ],
            ),
            for (final s in suits.reversed) // 무늬 순서와 같이 약한 것부터
              Padding(
                padding: const EdgeInsets.only(left: left, bottom: 14), // 무늬끼리는 더 띄워 묶음이 보이게
                child: Wrap(
                  // 패 옆면(2.5D)이 아래로 폭의 11% 나온다 — 그만큼 더 띄워 윗줄 옆면이 아랫줄 패에 붙지 않게(11-26 사용자)
                  spacing: gap,
                  runSpacing: tileW * .11 + 6,
                  children: [
                    for (var n = 1; n <= 13; n++)
                      Semantics(
                        label: '$n', // 그림만이면 스크린 리더가 번호를 못 읽는다(전엔 숫자 칸, 리뷰 10차)
                        excludeSemantics: true,
                        child: Opacity(
                          key: ValueKey('out-$s$n'),
                          opacity: gone.contains('$s$n') ? 1 : .3, // 종이 판 위에서도 아직인 패가 보이되 나온 패와 구분되게
                          child: TileView(code: '$s$n', width: tileW),
                        ),
                      ),
                  ],
                ),
              ),
          ],
        );
      },
    );
  }
}

/// 넓은 화면: 왼쪽 나온 패(싱글만)·오른쪽 조합표를 판 옆에 늘 띄운다. 좁은 화면은 버튼으로 연다(PracticeButtons).
class PracticeFrame extends StatelessWidget {
  static const side = 280.0;
  final List<String>? out;
  final List<String> suits;
  final Widget child;

  /// 크게 본 창이 열려 있는 동안에도 따라 바뀌는 나온 패
  final ValueListenable<List<String>?> live;
  const PracticeFrame({super.key, required this.out, required this.live, required this.suits, required this.child});

  /// 옆 패널 보기·숨기기 — 무늬 순서 옆 버튼으로 켜고 끈다(11-27 사용자 '보기 숨기기가 쉽게')
  static final showOut = ValueNotifier<bool>(true), showCombos = ValueNotifier<bool>(true);

  // 넓고 충분히 높을 때만 — 낮은 가로 창에서 양옆을 떼면 손패가 두 줄로 늘어 패스·내기가 밀린다(리뷰 1차)
  static bool wide(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    return size.width >= 1000 && size.height >= 720;
  }

  /// 좁은 화면(폰)의 떠 있는 창 켜기·끄기 — 판 위에 떠 있고 게임은 그대로 이어진다(11-27 사용자 '게임 도중 창을 껐다
  /// 켤 수 있게'). 아래에서 올라오는 시트는 판을 막아 매번 닫아야 했다
  static final floatOut = ValueNotifier<bool>(false), floatCombos = ValueNotifier<bool>(false);

  @override
  Widget build(BuildContext context) {
    if (!wide(context)) {
      return LayoutBuilder(
        builder: (context, box) {
          final w = min(320.0, box.maxWidth * .48);
          Widget window(String key, ValueNotifier<bool> open, Widget body) => Material(
            key: ValueKey(key),
            color: Theme.of(context).scaffoldBackgroundColor.withValues(alpha: .94),
            elevation: 6,
            borderRadius: BorderRadius.circular(12),
            clipBehavior: Clip.antiAlias,
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: w, minWidth: w, maxHeight: box.maxHeight * .72),
              child: Stack(
                children: [
                  SingleChildScrollView(padding: const EdgeInsets.fromLTRB(10, 10, 30, 10), child: body),
                  Positioned(
                    top: 0,
                    right: 0,
                    child: IconButton(
                      key: ValueKey('$key-close'),
                      visualDensity: VisualDensity.compact,
                      icon: const Icon(Icons.close, size: 18),
                      onPressed: () => open.value = false,
                    ),
                  ),
                ],
              ),
            ),
          );
          return ListenableBuilder(
            listenable: Listenable.merge([floatOut, floatCombos]),
            builder: (context, _) => Stack(
              children: [
                child,
                if (out != null && floatOut.value)
                  Positioned(
                    left: 6,
                    top: 6,
                    child: window(
                      'float-out',
                      floatOut,
                      ValueListenableBuilder(
                        valueListenable: live,
                        builder: (_, now, _) => OutTracker(out: now ?? out!, suits: suits),
                      ),
                    ),
                  ),
                if (floatCombos.value)
                  Positioned(right: 6, top: 6, child: window('float-combos', floatCombos, const ComboChart())),
              ],
            ),
          );
        },
      );
    }
    // 옆 패널은 반투명 종이 판 위에 — 그림 배경(나무·꽃) 위에선 아직 안 나온 흐린 패와 제목이 묻혀 안 보였다(11-27 사용자 캡처)
    Widget panel(Widget w) => Container(
      width: side,
      margin: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor.withValues(alpha: .88),
        borderRadius: BorderRadius.circular(12),
      ),
      child: SingleChildScrollView(padding: const EdgeInsets.all(10), child: w),
    );
    return ListenableBuilder(
      listenable: Listenable.merge([showOut, showCombos]),
      builder: (context, _) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (out != null && showOut.value)
            panel(
              OutTracker(
                out: out!,
                suits: suits,
                onOpen: () => showDialog<void>(
                  context: context,
                  routeSettings: const RouteSettings(name: outBigRoute), // 판이 끝나면 결과 창이 닫는다
                  builder: (_) => Dialog(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 680),
                      child: SingleChildScrollView(
                        primary: true, // 데스크톱에서도 Page Down이 내리게(창 안에 포커스 받을 것이 없다)
                        padding: const EdgeInsets.all(16),
                        child: ValueListenableBuilder(
                          valueListenable: live,
                          builder: (_, now, _) => OutTracker(out: now ?? out!, suits: suits),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          Expanded(child: child),
          if (showCombos.value) panel(const ComboChart()),
        ],
      ),
    );
  }
}

/// 무늬 순서 옆 작은 버튼 — 나온 패(싱글만)·조합표 창을 켜고 끈다(넓으면 옆 패널, 좁으면 판 위에 뜬 창).
class PracticeButtons extends StatelessWidget {
  final List<String>? out;

  final List<String> suits;
  const PracticeButtons({super.key, required this.out, required this.suits});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    // 넓은 화면은 판 옆 패널, 좁은 화면은 판 위에 뜬 창을 켜고 끈다(눌린 표시)
    final wide = PracticeFrame.wide(context);
    final out$ = wide ? PracticeFrame.showOut : PracticeFrame.floatOut;
    final combos = wide ? PracticeFrame.showCombos : PracticeFrame.floatCombos;
    return ListenableBuilder(
      listenable: Listenable.merge([out$, combos]),
      builder: (context, _) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (out != null)
            IconButton(
              key: const ValueKey('open-out'),
              isSelected: out$.value,
              tooltip: t.outTiles,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints.tightFor(width: 30, height: 22),
              style: IconButton.styleFrom(
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ), // 48px 터치 여백이 줄을 키우지 않게 // 무늬 순서 줄보다 높아지지 않게
              icon: const Icon(Icons.grid_view, size: 20),
              onPressed: () => out$.value = !out$.value,
            ),
          IconButton(
            key: const ValueKey('open-combos'),
            isSelected: combos.value,
            tooltip: t.comboChart,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints.tightFor(width: 30, height: 22),
            style: IconButton.styleFrom(tapTargetSize: MaterialTapTargetSize.shrinkWrap), // 48px 터치 여백이 줄을 키우지 않게
            icon: const Icon(Icons.list_alt, size: 20),
            onPressed: () => combos.value = !combos.value,
          ),
        ],
      ),
    );
  }
}
