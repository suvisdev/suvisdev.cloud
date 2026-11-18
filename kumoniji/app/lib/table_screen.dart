import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'help.dart';
import 'l10n/app_localizations.dart';
import 'tile.dart';

const _ink = Color(0xFF42384C);
const _gold = Color(0xFFC9A24A);
const _felt = Color(0xFFE6F0DC);

/// 게임 화면. 사람은 0번 자리(아래), 봇은 시계 방향으로 1번 왼쪽 · 2번 맞은편 · 3번 오른쪽.
/// 판정은 서버가 하고 여기서는 그리기만 한다.
class TableScreen extends StatefulWidget {
  final Api? api;

  /// 처음 들어온 사람에게 설명 카드를 띄울지(테스트에서는 끔)
  final bool showHelpOnFirstVisit;
  const TableScreen({super.key, this.api, this.showHelpOnFirstVisit = true});

  @override
  State<TableScreen> createState() => _TableScreenState();
}

class _TableScreenState extends State<TableScreen> {
  late final Api api = widget.api ?? Api();
  GameState? s;
  Play? flash; // 방금 누가 무엇을 냈는지 잠깐 보여 줌
  final picked = <String>{};
  bool busy = false;

  @override
  void initState() {
    super.initState();
    _apply(api.newGame());
    if (widget.showHelpOnFirstVisit) _helpOnce();
  }

  Future<void> _helpOnce() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (prefs.getBool('seenHelp') ?? false) return;
      await prefs.setBool('seenHelp', true);
    } catch (_) {
      return; // 저장소를 못 쓰면(사생활 보호 모드 등) 자동으로 띄우지 않는다 — ? 버튼은 그대로
    }
    if (mounted) showHelp(context);
  }

  Future<void> _apply(Future<GameState> call) async {
    setState(() => busy = true);
    try {
      final next = await call;
      for (final e in next.events.where((e) => e.seat != 0)) {
        if (!mounted) return;
        setState(() => flash = e);
        await Future.delayed(const Duration(milliseconds: 700));
      }
      if (!mounted) return;
      setState(() {
        s = next;
        picked.clear();
        flash = null;
      });
      if (next.finished) _showResult(next);
    } on ApiError catch (e) {
      if (!mounted) return;
      final t = AppLocalizations.of(context)!;
      _toast(e.status == 422 ? _reason(t, e.code) : t.serverError);
      if (e.status != 422) await _resync();
    } catch (_) {
      if (!mounted) return;
      _toast(AppLocalizations.of(context)!.serverError);
      await _resync();
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void _toast(String msg) => ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg)));

  String _reason(AppLocalizations t, String? code) => switch (code) {
    'suit' => t.reasonSuit,
    'weaker' => t.reasonWeaker,
    'count' => t.reasonCount,
    'not_combo' => t.reasonNotCombo,
    'lead_pass' => t.reasonLeadPass,
    _ => t.illegal,
  };

  /// 요청이 실패해도 서버는 이미 진행했을 수 있다 → 지금 판 상태를 다시 받아 화면을 맞춘다.
  /// (판이 없어졌으면(404) 화면은 그대로 두고, 새 게임 버튼으로 다시 시작한다)
  Future<void> _resync() async {
    final g = s;
    if (g == null) return;
    try {
      final now = await api.get(g.id);
      if (!mounted) return;
      setState(() {
        s = now;
        picked.clear();
        flash = null;
      });
      if (now.finished && !g.finished) _showResult(now);
    } catch (_) {}
  }

  /// 진행 중인 판이 있으면 한 번 묻고 새 판을 시작한다.
  Future<void> _confirmNewGame() async {
    final g = s;
    if (g != null && !g.finished) {
      final t = AppLocalizations.of(context)!;
      final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          content: Text(t.newGameConfirm),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: Text(t.cancel)),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(t.newGame)),
          ],
        ),
      );
      if (ok != true) return;
    }
    _apply(api.newGame());
  }

  String _name(AppLocalizations t, int seat) => seat == 0 ? t.you : t.bot(seat);

  void _showResult(GameState g) {
    final t = AppLocalizations.of(context)!;
    final order = [0, 1, 2, 3]..sort((a, b) => g.settlement![b].compareTo(g.settlement![a]));
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (c) => AlertDialog(
        title: Text(t.winner(_name(t, g.winner!))),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (var r = 0; r < 4; r++)
              ListTile(
                dense: true,
                leading: Text(
                  t.rank(r + 1),
                  style: TextStyle(fontWeight: FontWeight.bold, color: r == 0 ? _gold : _ink),
                ),
                title: Text(_name(t, order[r]), style: TextStyle(fontWeight: order[r] == 0 ? FontWeight.bold : null)),
                trailing: Text(
                  t.points(g.settlement![order[r]]),
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: g.settlement![order[r]] >= 0 ? Colors.green.shade700 : Colors.red.shade700,
                  ),
                ),
              ),
          ],
        ),
        actions: [
          FilledButton(
            onPressed: () {
              Navigator.pop(c);
              _apply(api.newGame());
            },
            child: Text(t.newGame),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final g = s;
    // 봇이 내는 장면을 보여 주는 동안에는 그 봇이 차례다
    final active = flash?.seat ?? (g == null || g.finished ? null : g.turn);
    return Scaffold(
      appBar: AppBar(
        title: Text(t.title),
        backgroundColor: Colors.transparent,
        actions: [
          if (g != null)
            _TodayBadge(
              suit: g.today,
              label: MediaQuery.sizeOf(context).width < 400 ? '' : t.today,
              doubles: g.doubles,
            ),
          IconButton(tooltip: t.help, icon: const Icon(Icons.help_outline), onPressed: () => showHelp(context)),
          TextButton(onPressed: busy ? null : _confirmNewGame, child: Text(t.newGame)),
          const SizedBox(width: 4),
        ],
      ),
      body: g == null
          ? Center(
              child: busy
                  ? const CircularProgressIndicator()
                  : FilledButton(onPressed: () => _apply(api.newGame()), child: Text(t.newGame)),
            )
          : SafeArea(
              child: LayoutBuilder(
                builder: (context, box) {
                  final tileW = min(56.0, (box.maxWidth - 32) / 7 - 4);
                  final myTurn = active == 0 && !busy;
                  final canPlay = g.playable.isNotEmpty;
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Column(
                      children: [
                        _SuitOrder(suits: g.suits, label: t.suitOrder),
                        const SizedBox(height: 6),
                        _Seat(name: t.bot(2), g: g, seat: 2, active: active == 2, turnLabel: t.turn),
                        const SizedBox(height: 6),
                        Expanded(
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              _Seat(name: t.bot(1), g: g, seat: 1, active: active == 1, turnLabel: t.turn),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: _felt,
                                    borderRadius: BorderRadius.circular(24),
                                    border: Border.all(color: const Color(0xFFCFDDBF), width: 2),
                                  ),
                                  child: Center(
                                    child: Padding(
                                      padding: const EdgeInsets.all(6),
                                      child: FittedBox(fit: BoxFit.scaleDown, child: _center(t, g, tileW)),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 6),
                              _Seat(name: t.bot(3), g: g, seat: 3, active: active == 3, turnLabel: t.turn),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                        _Seat(name: t.you, g: g, seat: 0, active: active == 0, turnLabel: t.turn, compact: true),
                        const SizedBox(height: 8),
                        AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          padding: const EdgeInsets.fromLTRB(6, 10, 6, 6),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(16),
                            color: myTurn ? const Color(0xFFFFF1CC) : Colors.transparent,
                          ),
                          child: Wrap(
                            alignment: WrapAlignment.center,
                            spacing: 4,
                            runSpacing: 10,
                            children: [
                              for (final code in g.hand)
                                Opacity(
                                  // 내 차례에 낼 수 없는 패는 흐리게(낼 수 있는 패 목록은 서버가 준다)
                                  opacity: myTurn && !g.playable.contains(code) ? 0.35 : 1,
                                  child: TileView(
                                    key: ValueKey('hand-$code'),
                                    code: code,
                                    width: tileW,
                                    selected: picked.contains(code),
                                    onTap: !myTurn || !g.playable.contains(code)
                                        ? null
                                        : () => setState(
                                            () => picked.contains(code) ? picked.remove(code) : picked.add(code),
                                          ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 10),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            OutlinedButton(
                              onPressed: !myTurn || g.table.isEmpty ? null : () => _apply(api.move(g.id, [])),
                              child: Text(t.pass),
                            ),
                            const SizedBox(width: 16),
                            FilledButton(
                              onPressed: !myTurn || !g.isLegal(picked)
                                  ? null
                                  : () => _apply(
                                      api.move(g.id, [
                                        for (final c in g.hand)
                                          if (picked.contains(c)) c,
                                      ]),
                                    ),
                              child: Text(t.play),
                            ),
                          ],
                        ),
                        if (myTurn && !canPlay)
                          Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: Text(t.onlyPass, style: const TextStyle(color: _ink, fontSize: 13)),
                          ),
                        const SizedBox(height: 12),
                      ],
                    ),
                  );
                },
              ),
            ),
    );
  }

  Widget _center(AppLocalizations t, GameState g, double tileW) {
    final f = flash;
    final who = f?.seat ?? g.last;
    final tiles = f == null ? g.table : f.tiles;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (who != null && (f != null || g.table.isNotEmpty))
          Text(
            _name(t, who),
            style: const TextStyle(color: _ink, fontWeight: FontWeight.bold),
          ),
        const SizedBox(height: 8),
        // 직전 두 수: 흐리게, 작게, 이름과 함께
        if (f == null && g.recent.isNotEmpty) ...[
          for (final r in g.recent)
            Opacity(
              opacity: .55,
              child: Padding(
                padding: const EdgeInsets.only(bottom: 4),
                // 좁은 화면에서 5장 조합이 넘치지 않게 폭에 맞춰 줄인다
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_name(t, r.seat), style: const TextStyle(color: _ink, fontSize: 11)),
                      const SizedBox(width: 6),
                      for (final c in r.tiles ?? const <String>[])
                        Padding(
                          padding: const EdgeInsets.only(right: 2),
                          child: TileView(code: c, width: tileW * .55),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          const SizedBox(height: 4),
        ],
        if (f != null && f.tiles == null)
          Text(t.passed, style: const TextStyle(fontSize: 20, color: _ink))
        else
          Wrap(
            spacing: 4,
            children: [for (final c in tiles ?? const <String>[]) TileView(code: c, width: tileW)],
          ),
        if (f == null && !g.finished && g.turn == 0) ...[
          const SizedBox(height: 12),
          Text(
            t.yourTurn,
            style: const TextStyle(color: _ink, fontSize: 16, fontWeight: FontWeight.w600),
          ),
        ],
      ],
    );
  }
}

/// 자리 하나: 이름, 남은 장수, 꽃잎(가져간 바퀴 수), 보너스. 차례면 금색 테두리와 "차례" 표시.
class _Seat extends StatelessWidget {
  final String name, turnLabel;
  final GameState g;
  final int seat;
  final bool active, compact;
  const _Seat({
    required this.name,
    required this.g,
    required this.seat,
    required this.active,
    required this.turnLabel,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final label = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          name,
          style: const TextStyle(fontWeight: FontWeight.bold, color: _ink),
        ),
        if (active) ...[
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
            decoration: BoxDecoration(color: _gold, borderRadius: BorderRadius.circular(8)),
            child: Text(
              turnLabel,
              style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ],
    );
    final stats = Text('🌸${g.petals[seat]}  ✦${g.bonus[seat]}', style: const TextStyle(fontSize: 12, color: _ink));
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
      decoration: BoxDecoration(
        color: active ? const Color(0xFFFFF7E0) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: active ? _gold : const Color(0xFFE9DFD1), width: active ? 3 : 1),
        boxShadow: active ? [BoxShadow(color: _gold.withValues(alpha: .35), blurRadius: 10)] : null,
      ),
      child: compact
          ? Row(mainAxisSize: MainAxisSize.min, children: [label, const SizedBox(width: 12), stats])
          : Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                label,
                const SizedBox(height: 4),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const TileView(code: 'back', width: 22),
                    const SizedBox(width: 4),
                    Text('×${g.counts[seat]}', style: const TextStyle(color: _ink)),
                  ],
                ),
                const SizedBox(height: 2),
                stats,
              ],
            ),
    );
  }
}

/// 무늬 순서 띠: 센 것부터.
class _SuitOrder extends StatelessWidget {
  final List<String> suits;
  final String label;
  const _SuitOrder({required this.suits, required this.label});

  @override
  Widget build(BuildContext context) => FittedBox(
    fit: BoxFit.scaleDown,
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label, style: const TextStyle(fontSize: 12, color: _ink)),
        const SizedBox(width: 6),
        for (var i = 0; i < suits.length; i++) ...[
          if (i > 0)
            const Text(
              ' > ',
              style: TextStyle(color: _ink, fontWeight: FontWeight.bold),
            ),
          SvgPicture.asset('assets/icons/suit_${suits[i]}.svg', width: 22, height: 22),
        ],
      ],
    ),
  );
}

/// 오늘의 무늬 배지(무늬 그림만). 오늘의 무늬로만 된 5장이 나오면 ×5가 붙는다.
class _TodayBadge extends StatelessWidget {
  final String suit, label;
  final int doubles;
  const _TodayBadge({required this.suit, required this.label, required this.doubles});

  @override
  Widget build(BuildContext context) => Row(
    children: [
      if (label.isNotEmpty) ...[
        Text(label, style: const TextStyle(fontSize: 12, color: _ink)),
        const SizedBox(width: 6),
      ],
      SvgPicture.asset('assets/icons/suit_$suit.svg', key: const ValueKey('today'), width: 26, height: 26),
      if (doubles > 0) ...[
        const SizedBox(width: 6),
        Text(
          '×${pow(5, doubles)}',
          style: const TextStyle(fontWeight: FontWeight.bold, color: _gold),
        ),
      ],
    ],
  );
}
