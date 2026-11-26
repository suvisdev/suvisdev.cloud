import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'help.dart';
import 'l10n/app_localizations.dart';
import 'level.dart';
import 'practice.dart';
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
  // 지금 화면에 맞춘 나온 패(연습만) — 봇 수 재생에 맞춰 하나씩 늘고, 열려 있는 '나온 패' 시트도 이걸 따라간다
  final _out = ValueNotifier<List<String>?>(null);

  @override
  void dispose() {
    _out.dispose();
    super.dispose();
  }

  Play? flash; // 방금 누가 무엇을 냈는지 잠깐 보여 줌
  final picked = <String>{};
  final gone = <String>{}; // 방금 낸 패 — 봇 장면이 다 끝나기 전에도 손패에서 바로 뺀다
  Set<int> passed = {}; // 지금 바퀴에서 패스한 자리(봇 장면을 넘기는 동안에도 갱신)
  List<List<String>?> plays = List.filled(4, null); // 자리마다 이번 바퀴에 낸 패
  int? lead; // 지금 바닥에서 가장 센 패를 낸 자리
  List<int> order = []; // 최근 세 수를 낸 자리(같은 자리가 두 번일 수 있음), 오래된 수 → 최근 수
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
      for (var i = 0; i < next.events.length; i++) {
        final e = next.events[i];
        if (!mounted) return;
        if (e.auto) {
          // 아무도 못 이김 → 남은 자리 패스를 한 명씩이 아니라 한꺼번에 띄우고 한 번만 멈춘다(11-25 사용자)
          final run = [for (var k = i; k < next.events.length && next.events[k].auto; k++) next.events[k]];
          setState(() {
            passed.addAll(run.map((p) => p.seat));
            flash = run.last;
          });
          await Future.delayed(const Duration(milliseconds: 1000));
          if (!mounted) return;
          if (passed.length == 3) setState(() => _clearRound());
          i += run.length - 1;
          continue;
        }
        setState(() {
          if (e.tiles == null) {
            passed.add(e.seat);
          } else {
            shown[e.seat] -= e.tiles!.length;
            passed.clear();
            _record(e.seat, e.tiles!);
            final out = _out.value;
            if (out != null) _out.value = {...out, ...e.tiles!}.toList();
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
    final ahead = {for (final e in next.events) ...?e.tiles}; // 아직 재생하지 않은 봇 수
    setState(() {
      s = next;
      _out.value = next.out?.where((c) => !ahead.contains(c)).toList();
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
    _out.value = g.out;
    shown = [...g.counts];
    gone.clear();
    passed = g.passed.toSet();
    plays = [...g.plays];
    lead = g.table.isEmpty ? null : g.last;
    // 차례는 자리 번호 순으로 돌므로, 최근 수를 낸 자리(lead)에서 거꾸로 세면 오래된 순서가 된다
    order = lead == null
        ? []
        : [
            for (var k = 3; k >= 0; k--)
              if (plays[(lead! - k) % 4] != null) (lead! - k) % 4,
          ];
  }

  /// 판에는 최근 세 수만 남긴다 — 네 번째 전 수는 지운다(보통 내 차례에 보이던 내 첫 패).
  void _record(int seat, List<String> tiles) {
    // 한 바퀴 안에서 같은 자리가 연달아 낼 수는 없다 → 같은 자리가 또 오면 같은 수(내가 낸 수를 바로 그린 뒤 서버 응답에 다시 옴)
    if (order.isNotEmpty && order.last == seat) {
      plays[seat] = tiles;
      return;
    }
    order.add(seat);
    plays[seat] = tiles;
    lead = seat;
    if (order.length > 3) {
      final old = order.removeAt(0);
      if (!order.contains(old)) plays[old] = null; // 그 자리가 최근 세 수 안에서 또 냈으면 남긴다
    }
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
      _record(0, tiles);
      flash = Play(0, tiles); // 응답이 올 때까지 내 차례 버튼을 잠근다
    });
    _apply(api.move(g.id, tiles));
  }

  void _clearRound() {
    passed.clear();
    plays = List.filled(4, null);
    lead = null;
    order = [];
  }

  String _name(AppLocalizations t, int seat) => seat == 0 ? t.you : t.bot(seat);

  void _showResult(GameState g) {
    // 재생 중 열어 둔 연습 시트(나온 패·족보)는 닫는다 — 결과 창 뒤에 남으면 다시 시작한 판을 가린다(리뷰 3차)
    Navigator.of(context).popUntil((r) => r is! ModalBottomSheetRoute);
    final t = AppLocalizations.of(context)!;
    final winner = g.winner!;
    final order = [0, 1, 2, 3]
      ..sort((a, b) {
        final byScore = g.settlement![b].compareTo(g.settlement![a]);
        if (byScore != 0) return byScore;
        return (a == winner ? -1 : a).compareTo(b == winner ? -1 : b);
      });
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (c) => AlertDialog(
        scrollable: true, // 낮은 창에서도 정산표를 끝까지 볼 수 있게
        titlePadding: const EdgeInsets.fromLTRB(24, 12, 8, 0),
        title: Row(
          children: [
            Expanded(child: Text(t.winner(_name(t, winner)))),
            IconButton(
              tooltip: MaterialLocalizations.of(c).closeButtonTooltip,
              icon: const Icon(Icons.close),
              onPressed: () => Navigator.pop(c), // 판을 그대로 보며 닫기 — 새 판은 아래·위 '새 게임'
            ),
          ],
        ),
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
          OutlinedButton.icon(
            key: const ValueKey('result-restart'),
            onPressed: () {
              Navigator.pop(c);
              level = g.level;
              _apply(api.newGame(g.level)); // 끝난 판과 같은 난이도로 바로(바꾸려면 위 '새 게임')
            },
            icon: const Icon(Icons.replay),
            label: Text(t.restart),
          ),
          FilledButton.icon(
            key: const ValueKey('result-home'),
            onPressed: () {
              Navigator.pop(c);
              Navigator.of(context).popUntil((r) => r.isFirst); // 끝난 판이라 나갈지 묻지 않는다
            },
            icon: const Icon(Icons.home),
            label: Text(t.home),
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
    // 위 줄이 좁다: 폭을 글자 배율로 나눠 본다(글자 200%면 800 미만) — 배지 설명을 빼고 새 게임은 아이콘으로
    final size = MediaQuery.sizeOf(context);
    final low = size.height < 560 && size.width > size.height; // 낮은 '가로' 창만 — 세로 창은 예전 배치(리뷰 1차)
    // 낮은 가로 창은 제목 자리에 무늬 순서가 들어가므로 더 일찍 줄인다(리뷰 2차, 400×300)
    final narrowBar = size.width < MediaQuery.textScalerOf(context).scale(low ? 560 : 400);
    // 낮은 가로 화면(휴대폰 가로, 앱 기본 — 11-25 사용자): 무늬 순서는 위 막대로, 맞은편 자리는 한 줄,
    // 패스·내기는 손패 오른쪽. 세로로 쌓으면 판·버튼이 화면 아래로 밀린다.
    return PopScope(
      canPop: g == null || g.finished,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _leave();
      },
      child: Backdrop(
        kind: 'table',
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(
            toolbarHeight: low ? 44 : null,
            title: low && g != null
                // 아주 좁은 창에서도 넘치지 않게 통째로 줄인다(리뷰 2차)
                ? FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _SuitOrder(suits: g.suits, label: t.suitOrder),
                        PracticeButtons(out: _out.value, live: _out, suits: g.suits),
                      ],
                    ),
                  )
                : Text(g == null ? t.title : '${t.title} · ${levelName(t, g.level)}'),
            backgroundColor: Colors.transparent,
            actions: [
              if (g != null) _TodayBadge(suit: g.today, label: narrowBar ? '' : t.today, doubles: g.doubles),
              const MuteButton(),
              IconButton(tooltip: t.help, icon: const Icon(Icons.help_outline), onPressed: () => showHelp(context)),
              if (narrowBar)
                IconButton(
                  key: const ValueKey('new-game'),
                  tooltip: t.newGame,
                  icon: const Icon(Icons.add_circle_outline),
                  onPressed: busy ? null : _newGame,
                )
              else
                TextButton(key: const ValueKey('new-game'), onPressed: busy ? null : _newGame, child: Text(t.newGame)),
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
                      child: PracticeFrame(
                        out: _out.value,
                        suits: g.suits,
                        child: LayoutBuilder(
                          builder: (context, box) {
                            final tileW = _handTileW(box.maxWidth, box.maxHeight);
                            final myTurn = active == 0 && !busy;
                            final you = _Seat(
                              name: t.you,
                              g: g,
                              seat: 0,
                              count: shown[0],
                              active: active == 0,
                              turnLabel: t.turn,
                              compact: true,
                              passed: passed.contains(0),
                              passLabel: t.pass,
                            );
                            Widget handOf(double tileW) => AnimatedContainer(
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
                                                  () => picked.contains(code) ? picked.remove(code) : picked.add(code),
                                                ),
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                            );
                            final buttons = Row(
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
                            );
                            // 낼 패가 없어도 자동으로 넘기지 않는다(남에게 손패가 드러남) — 직접 패스
                            final onlyPass = myTurn && g.table.isNotEmpty && g.playable.isEmpty
                                ? Padding(
                                    padding: const EdgeInsets.only(top: 6),
                                    child: Text(t.onlyPass, style: const TextStyle(color: _ink, fontSize: 13)),
                                  )
                                : null;
                            return Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 12),
                              child: Column(
                                children: [
                                  if (!low) ...[
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Flexible(
                                          child: _SuitOrder(suits: g.suits, label: t.suitOrder),
                                        ),
                                        if (!PracticeFrame.wide(context))
                                          PracticeButtons(out: _out.value, live: _out, suits: g.suits),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                  ],
                                  _Seat(
                                    name: t.bot(2),
                                    g: g,
                                    seat: 2,
                                    count: shown[2],
                                    active: active == 2,
                                    turnLabel: t.turn,
                                    fan: Axis.horizontal,
                                    inline: low,
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
                                            // 2.5D: 판을 뒤로 눕혀 원근을 주고, 아래에 판 두께와 그림자를 깐다.
                                            // 원근을 판 크기에 비례시켜 폰·PC가 같은 모양, 앞 가장자리가 넓어지는 만큼(약 1.1배) 줄여 자리 안에 둔다
                                            Transform(
                                              alignment: Alignment.center,
                                              transform: Matrix4.identity()
                                                ..setEntry(3, 2, .5 / max(side, 1)) // 창이 아주 낮으면 side가 0
                                                ..rotateX(-.42) // 위(먼 쪽)가 뒤로 → 가까운 아래 가장자리가 넓게
                                                ..scaleByDouble(.9, .9, 1, 1),
                                              child: Container(
                                                width: side,
                                                height: side,
                                                decoration: BoxDecoration(
                                                  color: _felt,
                                                  borderRadius: BorderRadius.circular(24),
                                                  border: Border.all(color: const Color(0xFFCFDDBF), width: 2),
                                                  // 두께·그림자도 판 크기에 비례(고정 px면 아주 작은 판에서 원근 분모가 0을 지난다)
                                                  boxShadow: [
                                                    BoxShadow(
                                                      color: const Color(0xFFB7CA9F),
                                                      offset: Offset(0, side * .022),
                                                    ),
                                                    BoxShadow(
                                                      color: const Color(0x30000000),
                                                      blurRadius: side * .036,
                                                      offset: Offset(0, side * .04),
                                                    ),
                                                  ],
                                                ),
                                                child: Center(
                                                  child: Padding(
                                                    padding: const EdgeInsets.all(6),
                                                    child: _felt4(t, g, side),
                                                  ),
                                                ),
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
                                  if (low)
                                    Row(
                                      crossAxisAlignment: CrossAxisAlignment.end,
                                      children: [
                                        Expanded(
                                          // 손패 한 줄 13장이 버튼 칸을 뺀 실제 폭에 들어가게, 높이는 화면의 약 18%
                                          child: LayoutBuilder(
                                            builder: (_, b) => handOf(
                                              max(
                                                6.0,
                                                min(52.0, min((b.maxWidth - 12) / 13 - 4, box.maxHeight * .135)),
                                              ), // 아주 좁아도 한 줄,
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        ConstrainedBox(
                                          // 버튼 칸이 손패 자리를 먹지 않게 — 긴 안내문·큰 글자는 이 폭 안에서 줄바꿈하고,
                                          // 그래도 높이가 넘치면(큰 글자 200%) 칸째 줄인다. 아니면 판이 아래로 넘쳤다(리뷰 9차).
                                          constraints: BoxConstraints(
                                            maxWidth: min(240, box.maxWidth * .32),
                                            maxHeight: box.maxHeight * .32,
                                          ),
                                          child: FittedBox(
                                            fit: BoxFit.scaleDown,
                                            child: ConstrainedBox(
                                              constraints: BoxConstraints(maxWidth: min(240, box.maxWidth * .32)),
                                              child: Column(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  FittedBox(fit: BoxFit.scaleDown, child: you),
                                                  const SizedBox(height: 6),
                                                  FittedBox(fit: BoxFit.scaleDown, child: buttons),
                                                  ?onlyPass,
                                                ],
                                              ),
                                            ),
                                          ),
                                        ),
                                      ],
                                    )
                                  else ...[
                                    you,
                                    const SizedBox(height: 8),
                                    handOf(tileW),
                                    const SizedBox(height: 10),
                                    buttons,
                                    ?onlyPass,
                                  ],
                                  const SizedBox(height: 12),
                                ],
                              ),
                            );
                          },
                        ),
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
                          // 같은 수면 키가 같아 다시 그려도 모션이 반복되지 않는다
                          child: _DropIn(
                            key: ValueKey('drop-$seat-${m.join()}-$c'),
                            index: m.indexOf(c),
                            from: _from[seat],
                            child: TileView(code: c, width: 44),
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

  /// 낮은 가로 화면의 맞은편 자리: 이름·뒷면·장수·점수를 한 줄로(세로 자리를 아낀다)
  final bool inline;

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
    this.inline = false,
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
    final column = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // 좁은 옆자리에서도 이름·차례 배지가 넘치지 않게
        FittedBox(fit: BoxFit.scaleDown, child: label),
        const SizedBox(height: 4),
        _Backs(
          count: count,
          turns: seat, // 1 왼쪽·2 맞은편·3 오른쪽 — 부채 손잡이가 그 사람 쪽
          // 세로: 이름·장수·점수 줄과 여백(약 110)을 뺀 높이에 13장이 들어가게
          length: fan == Axis.vertical ? max(32.0, room - 110) : 170, // 32 = 뒷면 한 장 높이(낮은 가로 창)
        ),
        Text('×$count', style: const TextStyle(color: _ink, fontSize: 12)),
        const SizedBox(height: 2),
        stats,
      ],
    );
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
          : inline
          ? FittedBox(
              fit: BoxFit.scaleDown, // 아주 좁은 창은 한 줄째 줄인다
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  label,
                  const SizedBox(width: 10),
                  _Backs(count: count, turns: seat, length: 140),
                  const SizedBox(width: 6),
                  Text('×$count', style: const TextStyle(color: _ink, fontSize: 12)),
                  const SizedBox(width: 10),
                  stats,
                ],
              ),
            )
          : fan == Axis.vertical
          // 옆자리: 글자가 커서(200%) 110px 어림을 넘으면 폭은 그대로 두고 높이에 맞춰 자리째 줄인다(리뷰 9차)
          ? LayoutBuilder(
              builder: (_, c) => FittedBox(
                fit: BoxFit.scaleDown,
                child: SizedBox(width: c.maxWidth, child: column),
              ),
            )
          : column,
    );
    // 패스하면 그 자리가 말하듯 말풍선을 띄워 둔다(누가 새로 내거나 바퀴가 넘어가면 사라짐)
    return Stack(
      clipBehavior: Clip.none,
      children: [
        box,
        // 봇 자리는 자리 안 위쪽(이름 줄)에 띄우고 자리보다 크면 줄인다 — 자리 밖에 두면 화면 폭·장수·글자 크기에 따라
        // 화면 끝에서 잘리거나 무늬 순서 띠를 가렸다. 이름은 자리 위치로 알 수 있으니 덮고, 아래 남은 장수(×N)는
        // 가리지 않는다(가운데에 두면 1장일 때 ×1을 덮었다). 꼬리는 뺀다.
        // 내 자리(한 줄로 낮음)만 자리 위에. 한 줄 자리(낮은 가로 창 맞은편)는 ×N이 같은 줄이라 왼쪽(이름 위)에(리뷰 8차).
        if (passed && !compact)
          Positioned.fill(
            child: Align(
              alignment: inline ? Alignment.centerLeft : Alignment.topCenter,
              child: Padding(
                padding: const EdgeInsets.only(top: 2),
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: _Bubble(key: ValueKey('passed-$seat'), text: passLabel, tail: false),
                ),
              ),
            ),
          )
        else if (passed)
          Positioned(
            top: -40,
            right: -12,
            child: _Bubble(key: ValueKey('passed-$seat'), text: passLabel),
          ),
      ],
    );
  }
}

/// 말풍선: 둥근 상자 + 왼쪽 아래 꼬리(tail).
class _Bubble extends StatelessWidget {
  final String text;
  final bool tail;
  const _Bubble({super.key, required this.text, this.tail = true});

  // 크게·굵게, 뜰 때 톡 튀어나온다(11-24 사용자: "패스가 더 크게 잘 보였으면")
  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
    tween: Tween(begin: 0, end: 1),
    duration: const Duration(milliseconds: 260),
    curve: Curves.easeOutBack,
    builder: (_, k, c) => Transform.scale(scale: k, alignment: Alignment.bottomLeft, child: c),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: _ink, width: 2.5),
            boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 6, offset: Offset(0, 3))],
          ),
          child: Text(
            text,
            style: const TextStyle(color: _ink, fontSize: 18, fontWeight: FontWeight.w900),
          ),
        ),
        if (tail)
          Padding(
            padding: const EdgeInsets.only(left: 14),
            child: CustomPaint(size: const Size(14, 10), painter: _Tail()),
          ),
      ],
    ),
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
        ..strokeWidth = 2.5,
    );
  }

  @override
  bool shouldRepaint(_Tail old) => false;
}

/// 남은 패 뒷면을 한 장씩 겹쳐 펼친다. [length] 안에 다 들어가게 겹침 간격을 정한다(최대 반 장).
class _Backs extends StatelessWidget {
  final int count;
  final double length;

  /// 시계 방향 90° 회전 수 — 0 기본(손이 아래), 1 왼쪽 자리, 2 맞은편, 3 오른쪽 자리. 부채의 손잡이가 늘 그 사람 쪽.
  final int turns;
  const _Backs({required this.count, required this.length, this.turns = 0});

  @override
  Widget build(BuildContext context) {
    // 실제로 패를 쥔 것처럼 뒷면을 부채꼴로 편다(11-25 사용자, 2.5D로 네 명이 둘러앉은 느낌).
    const w = 24.0, h = w * 4 / 3;
    final gaps = max(count - 1, 1);
    if (MediaQuery.sizeOf(context).height < 600) {
      // 낮은 창: 부채 대신 예전처럼 겹쳐 쌓기 — 부채가 높아지면 판·패스 버튼 자리를 먹는다(리뷰 2차)
      final along = turns.isOdd ? h : w;
      final step = count < 2 ? 0.0 : min(along / 2, (length - along) / (count - 1));
      final total = count == 0 ? 0.0 : along + step * (count - 1);
      return SizedBox(
        width: turns.isOdd ? w : total,
        height: turns.isOdd ? total : h,
        child: Stack(
          children: [
            for (var i = 0; i < count; i++)
              Positioned(
                left: turns.isOdd ? 0 : step * i,
                top: turns.isOdd ? step * i : 0,
                child: const TileView(code: 'back', width: w),
              ),
          ],
        ),
      );
    }
    final spread = min(70.0, 6.0 * gaps) * pi / 180; // 부채 전체 각도
    // 반지름: 자리 길이 안에 들어가고, 이웃 패가 너무 벌어지지 않게(패 폭의 절반 남짓)
    final r = min((length - w) / (2 * max(sin(spread / 2), .01)), .55 * w * gaps / max(spread, .01)).clamp(0.0, 400.0);
    final width = count == 0 ? 0.0 : w + 2 * r * sin(spread / 2);
    final height = count == 0 ? 0.0 : h + r * (1 - cos(spread / 2));
    final fan = SizedBox(
      width: width,
      height: height,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          for (var i = 0; i < count; i++)
            Builder(
              builder: (_) {
                final a = count < 2 ? 0.0 : -spread / 2 + spread * i / gaps;
                return Positioned(
                  left: width / 2 + r * sin(a) - w / 2,
                  top: r * (1 - cos(a)),
                  child: Transform.rotate(
                    angle: a,
                    child: const TileView(code: 'back', width: w),
                  ),
                );
              },
            ),
        ],
      ),
    );
    return RotatedBox(quarterTurns: turns, child: fan);
  }
}

/// 무늬 순서 띠: 약한 것부터 차례로, 그림 아래 이름(기호 없이 — 11-25 사용자).
class _SuitOrder extends StatelessWidget {
  final List<String> suits; // 서버는 센 것 → 약한 것
  final String label;
  const _SuitOrder({required this.suits, required this.label});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final names = {'m': t.suitM, 's': t.suitS, 'l': t.suitL, 'c': t.suitC};
    final short = MediaQuery.sizeOf(context).height < 600; // 낮은 창은 이름을 빼 한 줄 높이를 아낀다
    return FittedBox(
      fit: BoxFit.scaleDown,
      child: Row(
        key: const ValueKey('suit-order'),
        mainAxisSize: MainAxisSize.min,
        children: [
          if (!short) Text(label, style: const TextStyle(fontSize: 12, color: _ink)),
          for (final s in suits.reversed)
            Padding(
              padding: const EdgeInsets.only(left: 10),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SvgPicture.asset('assets/icons/suit_$s.svg', width: 22, height: 22),
                  if (!short) Text(names[s] ?? s, style: const TextStyle(fontSize: 10, color: _ink)),
                ],
              ),
            ),
        ],
      ),
    );
  }
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
          // 위 줄은 폭이 정해져 있어 글자 크기 200%에서도 1.3배까지만(음소거·도움말·새 게임이 밀려나지 않게)
          textScaler: MediaQuery.textScalerOf(context).clamp(maxScaleFactor: 1.3),
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

/// 패가 날아오는 방향(판 위에서 낸 사람 쪽): 0 아래 · 1 왼쪽 · 2 위 · 3 오른쪽
const _from = [Offset(0, 90), Offset(-90, 0), Offset(0, -90), Offset(90, 0)];

/// 낸 패가 한 장씩 차례로 낸 사람 쪽에서 날아와 뒤집히며 "탕" 내려앉는 모션(처음 그려질 때 한 번).
/// 뒷면으로 떠올라 오다가 반쯤 돌면 앞면이 보인다. index번째 패는 그만큼 늦게 출발한다.
class _DropIn extends StatelessWidget {
  static const gap = 90, fall = 320; // ms: 장 사이 간격, 한 장이 날아와 앉는 시간
  final int index;
  final Offset from;
  final TileView child;
  const _DropIn({super.key, required this.index, required this.from, required this.child});

  @override
  Widget build(BuildContext context) {
    final total = fall + gap * index;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: total),
      builder: (_, k, _) {
        final t = ((k * total - gap * index) / fall).clamp(0.0, 1.0); // 이 패의 진행
        final fly = Curves.easeOutCubic.transform(t);
        final land = Curves.easeOutBack.transform(t); // 살짝 튀었다가 앉음
        final turn = pi * (1 - Curves.easeInOut.transform(t)); // 뒷면(π) → 앞면(0)
        return Opacity(
          opacity: (t * 5).clamp(0.0, 1.0),
          child: Transform.translate(
            offset: from * (1 - fly),
            child: Transform.scale(
              scale: 1 + .35 * (1 - land), // 떠 있을수록 크게 → 내려앉으며 제 크기
              child: Transform(
                alignment: Alignment.center,
                transform: Matrix4.identity()
                  ..setEntry(3, 2, .002)
                  ..rotateY(turn),
                child: turn > pi / 2 ? TileView(code: 'back', width: child.width) : child,
              ),
            ),
          ),
        );
      },
    );
  }
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

/// 손패 한 장 폭 — 예전(최대 56, 한 줄 7장)보다 크게(11-25 사용자 "1.5배 정도").
/// 폭 계산은 예전과 같이 w − 32(양옆 여백 12+6, 패 사이 4). 한 줄 5~13장 중 가장 크게 나오는 것을 고르되, 손패 전체가 화면 높이의 34%를 넘지 않게(가운데 판·옆자리 자리를 남김).
/// 손패 높이는 본문의 34%, 그리고 위 자리·옆자리·내 자리·버튼 몫(약 440)을 뺀 나머지 안 — 낮은 창은 예전 크기 그대로.
/// 큰 화면은 최대 84(1.5배), 세로 휴대폰은 높이에 막혀 약 1.2배.
double _handTileW(double w, double h) =>
    [for (var n = 5; n <= 13; n++) n]
        .map((n) => min(84.0, min((w - 32) / n - 4, (min(.34 * h, h - 440) / (13 / n).ceil() - 10) / 1.4)))
        .fold(min(56.0, (w - 32) / 7 - 4), max); // 예전 크기보다 작아지지는 않는다
