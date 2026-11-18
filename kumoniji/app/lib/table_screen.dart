import 'dart:math';

import 'package:flutter/material.dart';

import 'api.dart';
import 'l10n/app_localizations.dart';
import 'tile.dart';

const _ink = Color(0xFF42384C);

/// 게임 화면. 사람은 0번 자리, 1~3번은 봇. 판정은 서버가 하고 여기서는 그리기만 한다.
class TableScreen extends StatefulWidget {
  final Api? api;
  const TableScreen({super.key, this.api});

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
  }

  Future<void> _apply(Future<GameState> call) async {
    setState(() => busy = true);
    try {
      final next = await call;
      for (final e in next.events.where((e) => e.seat != 0)) {
        if (!mounted) return;
        setState(() => flash = e);
        await Future.delayed(const Duration(milliseconds: 600));
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
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.status == 422 ? t.illegal : t.serverError)));
      if (e.status != 422) await _resync();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.serverError)));
      await _resync();
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

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

  String _name(AppLocalizations t, int seat) => seat == 0 ? t.you : t.bot(seat);

  void _showResult(GameState g) {
    final t = AppLocalizations.of(context)!;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (c) => AlertDialog(
        title: Text(t.winner(_name(t, g.winner!))),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (var i = 0; i < 4; i++)
              ListTile(
                dense: true,
                title: Text(_name(t, i)),
                trailing: Text(
                  t.points(g.settlement![i]),
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: g.settlement![i] >= 0 ? Colors.green.shade700 : Colors.red.shade700,
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
    return Scaffold(
      appBar: AppBar(
        title: Text(t.title),
        backgroundColor: Colors.transparent,
        actions: [
          if (g != null) _TodayBadge(suit: g.today, label: t.today, doubles: g.doubles),
          IconButton(
            tooltip: t.newGame,
            icon: const Icon(Icons.refresh),
            onPressed: busy ? null : () => _apply(api.newGame()),
          ),
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
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            for (var seat = 1; seat < 4; seat++)
                              Expanded(
                                child: _Seat(name: t.bot(seat), g: g, seat: seat),
                              ),
                          ],
                        ),
                        Expanded(child: Center(child: _center(t, g, tileW))),
                        _Seat(name: t.you, g: g, seat: 0, compact: true),
                        const SizedBox(height: 8),
                        Wrap(
                          alignment: WrapAlignment.center,
                          spacing: 4,
                          runSpacing: 10,
                          children: [
                            for (final code in g.hand)
                              TileView(
                                key: ValueKey('hand-$code'),
                                code: code,
                                width: tileW,
                                selected: picked.contains(code),
                                onTap: busy || g.finished
                                    ? null
                                    : () => setState(
                                        () => picked.contains(code) ? picked.remove(code) : picked.add(code),
                                      ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            OutlinedButton(
                              onPressed: busy || g.finished || g.table.isEmpty
                                  ? null
                                  : () => _apply(api.move(g.id, [])),
                              child: Text(t.pass),
                            ),
                            const SizedBox(width: 16),
                            FilledButton(
                              onPressed: busy || g.finished || picked.isEmpty
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
                        const SizedBox(height: 16),
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
    if (f != null) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            _name(t, f.seat),
            style: const TextStyle(color: _ink, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          f.tiles == null
              ? Text(t.passed, style: const TextStyle(fontSize: 20, color: _ink))
              : Wrap(
                  spacing: 4,
                  children: [for (final c in f.tiles!) TileView(code: c, width: tileW)],
                ),
        ],
      );
    }
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (g.table.isNotEmpty && g.last != null)
          Text(
            _name(t, g.last!),
            style: const TextStyle(color: _ink, fontWeight: FontWeight.bold),
          ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 4,
          children: [for (final c in g.table) TileView(code: c, width: tileW)],
        ),
        const SizedBox(height: 12),
        if (!g.finished && g.turn == 0)
          Text(
            t.yourTurn,
            style: const TextStyle(color: _ink, fontSize: 16, fontWeight: FontWeight.w600),
          ),
      ],
    );
  }
}

/// 자리 하나: 이름, 남은 장수, 꽃잎(가져간 바퀴 수), 보너스. 차례면 테두리 강조.
class _Seat extends StatelessWidget {
  final String name;
  final GameState g;
  final int seat;
  final bool compact;
  const _Seat({required this.name, required this.g, required this.seat, this.compact = false});

  @override
  Widget build(BuildContext context) {
    final active = !g.finished && g.turn == seat;
    return Container(
      margin: const EdgeInsets.all(4),
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: active ? const Color(0xFFC9A24A) : const Color(0xFFE9DFD1), width: active ? 2.5 : 1),
      ),
      child: compact
          ? Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  name,
                  style: const TextStyle(fontWeight: FontWeight.bold, color: _ink),
                ),
                const SizedBox(width: 12),
                _stats(),
              ],
            )
          : Column(
              children: [
                Text(
                  name,
                  style: const TextStyle(fontWeight: FontWeight.bold, color: _ink),
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const TileView(code: 'back', width: 22),
                    const SizedBox(width: 4),
                    Text('×${g.counts[seat]}', style: const TextStyle(color: _ink)),
                  ],
                ),
                const SizedBox(height: 2),
                _stats(),
              ],
            ),
    );
  }

  Widget _stats() => Text('🌸${g.petals[seat]}  ✦${g.bonus[seat]}', style: const TextStyle(fontSize: 12, color: _ink));
}

/// 오늘의 무늬 배지. 오늘의 무늬로만 된 5장이 나오면 ×5가 붙는다.
class _TodayBadge extends StatelessWidget {
  final String suit, label;
  final int doubles;
  const _TodayBadge({required this.suit, required this.label, required this.doubles});

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Text(label, style: const TextStyle(fontSize: 12, color: _ink)),
      const SizedBox(width: 6),
      TileView(code: '${suit}1', width: 26),
      if (doubles > 0) ...[
        const SizedBox(width: 6),
        Text(
          '×${pow(5, doubles)}',
          style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFFC9A24A)),
        ),
      ],
    ],
  );
}
