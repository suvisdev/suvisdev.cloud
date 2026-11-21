import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'help.dart';
import 'l10n/app_localizations.dart';
import 'level.dart';
import 'settings.dart';
import 'tile.dart';

const _ink = Color(0xFF42384C);
const _felt = Color(0xFFE6F0DC);
const _sideW = 76.0; // 양옆 봇 자리 폭

/// 게임 화면. 사람은 0번 자리(아래), 봇은 시계 방향으로 1번 왼쪽 · 2번 맞은편 · 3번 오른쪽.
/// 판정은 서버가 하고 여기서는 그리기만 한다.
class TableScreen extends StatefulWidget {
  final Api? api;

  /// 봇 난이도(메인 화면에서 고름). 없으면 지난번에 고른 것
  final String? level;

  /// 처음 들어온 사람에게 설명 카드를 띄울지(테스트에서는 끔)
  final bool showHelpOnFirstVisit;
  const TableScreen({super.key, this.api, this.level, this.showHelpOnFirstVisit = true});

  @override
  State<TableScreen> createState() => _TableScreenState();
}

class _TableScreenState extends State<TableScreen> {
  late final Api api = widget.api ?? Api();
  GameState? s;
  Play? flash; // 방금 누가 무엇을 냈는지 잠깐 보여 줌
  final picked = <String>{};
  final gone = <String>{}; // 방금 낸 패 — 봇 장면이 다 끝나기 전에도 손패에서 바로 뺀다
  Set<int> passed = {}; // 지금 바퀴에서 패스한 자리(봇 장면을 넘기는 동안에도 갱신)
  List<List<String>?> plays = List.filled(4, null); // 자리마다 이번 바퀴에 낸 패
  int? lead; // 지금 바닥에서 가장 센 패를 낸 자리
  String level = 'normal'; // 봇 난이도 — 마지막으로 고른 것을 기억
  bool busy = true; // 첫 판 전(난이도 읽기·패 그림 받기)부터 잠근다 — 그 사이 새 게임을 누르면 판 요청이 두 번 나간다
  List<int> shown = List.filled(4, 13); // 자리마다 보여 주는 남은 장수(봇 장면을 넘기며 줄인다)
  int? intro; // 새 판 시작 카드를 보이는 동안 선(솜사탕 1을 가진 자리)
  int? dealt; // 패를 나눠 주는 동안 내 손에 보인 장수(나눠 주기가 끝나면 null)

  @override
  void initState() {
    super.initState();
    _startSaved();
    if (widget.showHelpOnFirstVisit) _helpOnce();
  }

  /// 메인 화면에서 고른 난이도로, 없으면 지난번에 고른 난이도로 바로 시작한다(처음이면 중급).
  Future<void> _startSaved() async {
    level = widget.level ?? await savedLevel();
    await precacheTiles(); // 패 그림을 다 받아 둔 뒤 시작(봇 패가 끊겨 뜨지 않게)
    if (mounted) _apply(api.newGame(level));
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
      if (s?.id != next.id) await _intro(next);
      for (final e in next.events) {
        if (!mounted) return;
        setState(() {
          if (e.tiles == null) {
            passed.add(e.seat);
          } else {
            shown[e.seat] -= e.tiles!.length;
            passed.clear();
            plays[e.seat] = e.tiles;
            lead = e.seat;
          }
          // 패스는 내 것도 보여 준다 — 아무도 바닥을 이길 수 없으면 서버가 내 차례를 자동으로 패스하기 때문
          if (e.seat != 0 || e.tiles == null) flash = e;
        });
        // 봇 한 수·모든 패스마다 잠깐 멈춰 누가 무엇을 했는지 보이게
        if (e.seat != 0 || e.tiles == null) {
          await Future.delayed(Duration(milliseconds: e.tiles == null ? 1000 : 1200));
        }
        // 셋이 패스하면 바퀴가 끝난다 → 판을 비운다
        if (passed.length == 3) {
          if (e.seat == 0) await Future.delayed(const Duration(milliseconds: 600));
          if (!mounted) return;
          setState(() => _clearRound());
        }
      }
      if (!mounted) return;
      setState(() {
        _sync(next);
        s = next;
        picked.clear();
        flash = null;
      });
      if (next.finished) _showResult(next);
      // 봇이 돌고 내 차례가 돌아왔으면 짧게 진동(옵션에서 끌 수 있음)
      if (!next.finished && next.turn == 0 && next.events.any((e) => e.seat != 0)) Settings.buzz();
    } on ApiError catch (e) {
      if (!mounted) return;
      final t = AppLocalizations.of(context)!;
      _toast(e.status == 422 ? _reason(t, e.code) : t.serverError);
      _rollback();
      if (e.status != 422) await _resync();
    } catch (_) {
      if (!mounted) return;
      _toast(AppLocalizations.of(context)!.serverError);
      _rollback();
      await _resync();
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  /// 실패하면 미리 뺀 패를 마지막 서버 상태로 되돌린다(재조회가 실패해도 패가 사라진 채 남지 않게).
  void _rollback() {
    final g = s;
    if (g == null) return;
    setState(() {
      _sync(g);
      flash = null;
    });
  }

  void _toast(String msg) => ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg)));

  String _reason(AppLocalizations t, String? code) => switch (code) {
    'suit' => t.reasonSuit,
    'weaker' => t.reasonWeaker,
    'count' => t.reasonCount,
    'not_combo' => t.reasonNotCombo,
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
        _sync(now);
        s = now;
        picked.clear();
        flash = null;
      });
      if (now.finished && !g.finished) _showResult(now);
    } catch (_) {}
  }

  /// 난이도를 골라 새 판을 시작한다. 진행 중인 판이 있으면 그만둘지도 같은 창에서 묻는다.
  Future<void> _newGame() async {
    final g = s;
    final t = AppLocalizations.of(context)!;
    final choice = await pickLevel(context, current: level, title: g != null && !g.finished ? t.newGameConfirm : null);
    if (choice == null) return;
    level = choice;
    _apply(api.newGame(choice));
  }

  /// 진행 중인 판에서 뒤로 가면 그만둘지 묻는다(실수로 판을 잃지 않게).
  Future<void> _leave() async {
    final t = AppLocalizations.of(context)!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        content: Text(t.leaveConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(t.cancel)),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(t.leave)),
        ],
      ),
    );
    if (ok == true && mounted) Navigator.pop(context);
  }

  /// 새 판: 서버는 사람 차례까지 봇 수를 미리 두고 보내므로, 그 수를 되돌린 시작 상태(13장씩·빈 바닥)를 먼저 그리고
  /// "게임 시작" 카드를 보인 뒤 봇 수를 하나씩 보여 준다(이전엔 로딩 뒤나 이전 판 위에서 지나가 패가 미리 나가 있었다).
  Future<void> _intro(GameState next) async {
    final start = [...next.counts];
    for (final e in next.events) {
      start[e.seat] += e.tiles?.length ?? 0;
    }
    setState(() {
      s = next;
      gone.clear();
      picked.clear();
      flash = null;
      _clearRound();
      shown = List.filled(4, 0);
      dealt = 0;
    });
    // 나눠 주기: 네 자리에 한 장씩 13바퀴
    for (var k = 1; k <= 13; k++) {
      await Future.delayed(const Duration(milliseconds: 70));
      if (!mounted) return;
      setState(() {
        shown = [for (final n in start) min(k, n)];
        dealt = k;
      });
    }
    setState(() {
      dealt = null;
      intro = next.events.isEmpty ? next.turn : next.events.first.seat;
    });
    await Future.delayed(const Duration(milliseconds: 1400));
    if (mounted) setState(() => intro = null);
  }

  void _sync(GameState g) {
    shown = [...g.counts];
    gone.clear();
    passed = g.passed.toSet();
    plays = [...g.plays];
    lead = g.table.isEmpty ? null : g.last;
  }

  /// 내기를 누르면 서버 응답·봇 장면을 기다리지 않고 바로 손에서 빼서 내 자리 앞에 놓는다.
  void _play(GameState g) {
    final tiles = [
      for (final c in g.hand)
        if (picked.contains(c)) c,
    ];
    setState(() {
      gone.addAll(tiles);
      picked.clear();
      passed.clear();
      plays[0] = tiles;
      lead = 0;
      flash = Play(0, tiles); // 응답이 올 때까지 내 차례 버튼을 잠근다
    });
    _apply(api.move(g.id, tiles));
  }

  void _clearRound() {
    passed.clear();
    plays = List.filled(4, null);
    lead = null;
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
                  style: TextStyle(fontWeight: FontWeight.bold, color: r == 0 ? gold : _ink),
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
              _newGame();
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
    // 나눠 주는 동안엔 아무도 차례가 아니고, 시작 카드 동안엔 선이 차례다
    final active = dealt != null ? null : intro ?? flash?.seat ?? (g == null || g.finished ? null : g.turn);
    return PopScope(
      canPop: g == null || g.finished,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _leave();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(g == null ? t.title : '${t.title} · ${levelName(t, g.level)}'),
          backgroundColor: Colors.transparent,
          actions: [
            if (g != null)
              _TodayBadge(
                suit: g.today,
                label: MediaQuery.sizeOf(context).width < 400 ? '' : t.today,
                doubles: g.doubles,
              ),
            IconButton(tooltip: t.help, icon: const Icon(Icons.help_outline), onPressed: () => showHelp(context)),
            TextButton(onPressed: busy ? null : _newGame, child: Text(t.newGame)),
            const SizedBox(width: 4),
          ],
        ),
        body: g == null
            ? Center(
                child: busy
                    ? const CircularProgressIndicator()
                    : FilledButton(onPressed: () => _apply(api.newGame(level)), child: Text(t.newGame)),
              )
            : Stack(
                children: [
                  SafeArea(
                    child: LayoutBuilder(
                      builder: (context, box) {
                        final tileW = min(56.0, (box.maxWidth - 32) / 7 - 4);
                        final myTurn = active == 0 && !busy;
                        return Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          child: Column(
                            children: [
                              _SuitOrder(suits: g.suits, label: t.suitOrder),
                              const SizedBox(height: 6),
                              _Seat(
                                name: t.bot(2),
                                g: g,
                                seat: 2,
                                count: shown[2],
                                active: active == 2,
                                turnLabel: t.turn,
                                fan: Axis.horizontal,
                                passed: passed.contains(2),
                                passLabel: t.pass,
                              ),
                              const SizedBox(height: 6),
                              Expanded(
                                // 가운데 판은 정사각형. 양옆 자리 폭(_sideW)을 빼고 남은 폭과 높이 중 작은 쪽이 한 변
                                child: LayoutBuilder(
                                  builder: (context, mid) {
                                    final side = min(mid.maxWidth - 2 * _sideW - 12, mid.maxHeight);
                                    return Row(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        _Seat(
                                          name: t.bot(1),
                                          g: g,
                                          seat: 1,
                                          count: shown[1],
                                          passed: passed.contains(1),
                                          passLabel: t.pass,
                                          active: active == 1,
                                          turnLabel: t.turn,
                                          fan: Axis.vertical,
                                          room: mid.maxHeight,
                                        ),
                                        const SizedBox(width: 6),
                                        Container(
                                          width: side,
                                          height: side,
                                          decoration: BoxDecoration(
                                            color: _felt,
                                            borderRadius: BorderRadius.circular(24),
                                            border: Border.all(color: const Color(0xFFCFDDBF), width: 2),
                                          ),
                                          child: Center(
                                            child: Padding(padding: const EdgeInsets.all(6), child: _felt4(t, g, side)),
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        _Seat(
                                          name: t.bot(3),
                                          g: g,
                                          seat: 3,
                                          count: shown[3],
                                          passed: passed.contains(3),
                                          passLabel: t.pass,
                                          active: active == 3,
                                          turnLabel: t.turn,
                                          fan: Axis.vertical,
                                          room: mid.maxHeight,
                                        ),
                                      ],
                                    );
                                  },
                                ),
                              ),
                              const SizedBox(height: 8),
                              _Seat(
                                name: t.you,
                                g: g,
                                seat: 0,
                                count: shown[0],
                                active: active == 0,
                                turnLabel: t.turn,
                                compact: true,
                                passed: passed.contains(0),
                                passLabel: t.pass,
                              ),
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
                                    for (final code in g.hand.where((c) => !gone.contains(c)).take(dealt ?? 13))
                                      Opacity(
                                        // 내 차례에 낼 수 없는 패는 흐리게(낼 수 있는 패 목록은 서버가 준다)
                                        opacity: myTurn && !g.playable.contains(code) ? 0.35 : 1,
                                        child: _DealIn(
                                          key: ValueKey('deal-$code'),
                                          child: TileView(
                                            key: ValueKey('hand-$code'),
                                            code: code,
                                            width: tileW,
                                            selected: picked.contains(code),
                                            onTap: !myTurn || !g.playable.contains(code)
                                                ? null
                                                : () => setState(
                                                    () =>
                                                        picked.contains(code) ? picked.remove(code) : picked.add(code),
                                                  ),
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
                                    onPressed: !myTurn ? null : () => _apply(api.move(g.id, [])),
                                    child: Text(t.pass),
                                  ),
                                  const SizedBox(width: 16),
                                  FilledButton(
                                    onPressed: !myTurn || !g.isLegal(picked) ? null : () => _play(g),
                                    child: Text(t.play),
                                  ),
                                ],
                              ),
                              // 낼 패가 없어도 자동으로 넘기지 않는다(남에게 손패가 드러남) — 직접 패스
                              if (myTurn && g.table.isNotEmpty && g.playable.isEmpty)
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
                  if (intro != null)
                    Positioned.fill(
                      child: IgnorePointer(
                        child: _StartCard(
                          title: t.gameStart,
                          first: t.goesFirst(_name(t, intro!)),
                          today: g.today,
                          todayLabel: t.today,
                        ),
                      ),
                    ),
                ],
              ),
      ),
    );
  }

  /// 정사각형 판: 자리마다 자기 앞(판 가장자리)에 이번 바퀴에 낸 패를 놓는다. 지금 가장 센 패만 진하게.
  Widget _felt4(AppLocalizations t, GameState g, double side) {
    Widget area(int seat, double w, double h, int perRow) {
      final m = plays[seat];
      if (m == null) return SizedBox(width: w, height: h);
      final top = seat == lead;
      final rows = [for (var i = 0; i < m.length; i += perRow) m.sublist(i, min(i + perRow, m.length))];
      return SizedBox(
        width: w,
        height: h,
        child: Opacity(
          opacity: top ? 1 : .45,
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Column(
              key: ValueKey('play-$seat'),
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final r in rows)
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      for (final c in r)
                        Padding(
                          padding: const EdgeInsets.all(2),
                          child: TileView(code: c, width: 44),
                        ),
                    ],
                  ),
              ],
            ),
          ),
        ),
      );
    }

    final myTurn = dealt == null && intro == null && flash == null && !g.finished && g.turn == 0;
    return Padding(
      padding: const EdgeInsets.all(6),
      child: Stack(
        children: [
          Align(alignment: Alignment.topCenter, child: area(2, side * .8, side * .26, 5)),
          Align(alignment: Alignment.centerLeft, child: area(1, side * .3, side * .42, 3)),
          Align(alignment: Alignment.centerRight, child: area(3, side * .3, side * .42, 3)),
          Align(alignment: Alignment.bottomCenter, child: area(0, side * .8, side * .26, 5)),
          if (myTurn)
            Center(
              child: Text(
                t.yourTurn,
                style: const TextStyle(color: _ink, fontSize: 15, fontWeight: FontWeight.w600),
              ),
            ),
        ],
      ),
    );
  }
}

/// 자리 하나: 이름, 남은 장수, 꽃잎(가져간 바퀴 수), 보너스. 차례면 금색 테두리와 "차례" 표시.
class _Seat extends StatelessWidget {
  final String name, turnLabel;
  final GameState g;
  final int seat;

  /// 보여 줄 남은 장수(봇 장면 중에는 서버 값보다 늦게 줄어든다)
  final int count;
  final bool active, compact;

  /// 남은 패 뒷면을 겹쳐 펼치는 방향(봇만). 세로면 [room] 높이 안에 맞춘다.
  final Axis? fan;
  final double room;

  /// 이번 바퀴에 패스했으면 이름 옆에 "패스" 표시
  final bool passed;
  final String passLabel;
  const _Seat({
    this.passed = false,
    this.passLabel = '',
    this.fan,
    this.room = 400,
    required this.name,
    required this.g,
    required this.seat,
    required this.count,
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
            decoration: BoxDecoration(color: gold, borderRadius: BorderRadius.circular(8)),
            child: Text(
              turnLabel,
              style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ],
    );
    final stats = Text('🌸${g.petals[seat]}  ✦${g.bonus[seat]}', style: const TextStyle(fontSize: 12, color: _ink));
    final box = AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
      decoration: BoxDecoration(
        color: active ? const Color(0xFFFFF7E0) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: active ? gold : const Color(0xFFE9DFD1), width: active ? 3 : 1),
        boxShadow: active ? [BoxShadow(color: gold.withValues(alpha: .35), blurRadius: 10)] : null,
      ),
      width: fan == Axis.vertical ? _sideW : null,
      child: compact
          ? Row(mainAxisSize: MainAxisSize.min, children: [label, const SizedBox(width: 12), stats])
          : Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // 좁은 옆자리에서도 이름·차례 배지가 넘치지 않게
                FittedBox(fit: BoxFit.scaleDown, child: label),
                const SizedBox(height: 4),
                _Backs(
                  count: count,
                  axis: fan ?? Axis.horizontal,
                  // 세로: 이름·장수·점수 줄과 여백(약 110)을 뺀 높이에 13장이 들어가게
                  length: fan == Axis.vertical ? max(48.0, room - 110) : 170,
                ),
                Text('×$count', style: const TextStyle(color: _ink, fontSize: 12)),
                const SizedBox(height: 2),
                stats,
              ],
            ),
    );
    // 패스하면 그 자리가 말하듯 말풍선을 띄워 둔다(누가 새로 내거나 바퀴가 넘어가면 사라짐)
    return Stack(
      clipBehavior: Clip.none,
      children: [
        box,
        if (passed)
          Positioned(
            top: -24,
            right: -10,
            child: _Bubble(key: ValueKey('passed-$seat'), text: passLabel),
          ),
      ],
    );
  }
}

/// 말풍선: 둥근 상자 + 왼쪽 아래 꼬리.
class _Bubble extends StatelessWidget {
  final String text;
  const _Bubble({super.key, required this.text});

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: _ink, width: 1.5),
          boxShadow: const [BoxShadow(color: Color(0x22000000), blurRadius: 4, offset: Offset(0, 2))],
        ),
        child: Text(
          text,
          style: const TextStyle(color: _ink, fontSize: 12, fontWeight: FontWeight.bold),
        ),
      ),
      Padding(
        padding: const EdgeInsets.only(left: 10),
        child: CustomPaint(size: const Size(10, 7), painter: _Tail()),
      ),
    ],
  );
}

class _Tail extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    // 상자 테두리와 겹쳐 이어지도록 위로 2px 올려 그린다
    final path = Path()
      ..moveTo(0, -2)
      ..lineTo(size.width, -2)
      ..lineTo(1, size.height)
      ..close();
    canvas.drawPath(path, Paint()..color = Colors.white);
    canvas.drawPath(
      Path()
        ..moveTo(0, -1)
        ..lineTo(1, size.height)
        ..lineTo(size.width, -1),
      Paint()
        ..color = _ink
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5,
    );
  }

  @override
  bool shouldRepaint(_Tail old) => false;
}

/// 남은 패 뒷면을 한 장씩 겹쳐 펼친다. [length] 안에 다 들어가게 겹침 간격을 정한다(최대 반 장).
class _Backs extends StatelessWidget {
  final int count;
  final Axis axis;
  final double length;
  const _Backs({required this.count, required this.axis, required this.length});

  @override
  Widget build(BuildContext context) {
    const w = 24.0, h = w * 4 / 3;
    final along = axis == Axis.horizontal ? w : h;
    final step = count < 2 ? 0.0 : min(along / 2, (length - along) / (count - 1));
    final total = count == 0 ? 0.0 : along + step * (count - 1);
    return SizedBox(
      width: axis == Axis.horizontal ? total : w,
      height: axis == Axis.horizontal ? h : total,
      child: Stack(
        children: [
          for (var i = 0; i < count; i++)
            Positioned(
              left: axis == Axis.horizontal ? step * i : 0,
              top: axis == Axis.horizontal ? 0 : step * i,
              child: const TileView(code: 'back', width: w),
            ),
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
          style: const TextStyle(fontWeight: FontWeight.bold, color: gold),
        ),
      ],
    ],
  );
}

/// 새 판 시작 카드: "게임 시작!" · 오늘의 무늬 · 솜사탕 1을 가진 선. 잠깐 커지며 나타난다.
class _StartCard extends StatelessWidget {
  final String title, first, today, todayLabel;
  const _StartCard({required this.title, required this.first, required this.today, required this.todayLabel});

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: Colors.black26,
    child: Center(
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: .6, end: 1),
        duration: const Duration(milliseconds: 450),
        curve: Curves.easeOutBack,
        builder: (_, k, child) => Transform.scale(
          scale: k,
          child: Opacity(opacity: k.clamp(0, 1), child: child),
        ),
        child: Card(
          key: const ValueKey('start-card'),
          color: const Color(0xFFFFF9EC),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
            side: const BorderSide(color: gold, width: 3),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: _ink),
                ),
                const SizedBox(height: 14),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(todayLabel, style: const TextStyle(color: _ink)),
                    const SizedBox(width: 8),
                    SvgPicture.asset('assets/icons/suit_$today.svg', width: 30, height: 30),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const TileView(code: 'c1', width: 30),
                    const SizedBox(width: 8),
                    Text(
                      first,
                      style: const TextStyle(color: _ink, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

/// 나눠 받은 패가 판 가운데 쪽에서 날아와 자리 잡는 모션(처음 그려질 때 한 번).
class _DealIn extends StatelessWidget {
  final Widget child;
  const _DealIn({super.key, required this.child});

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
    tween: Tween(begin: 0, end: 1),
    duration: const Duration(milliseconds: 260),
    curve: Curves.easeOut,
    builder: (_, k, c) => Opacity(
      opacity: k,
      child: Transform.translate(offset: Offset(0, -60 * (1 - k)), child: c),
    ),
    child: child,
  );
}
