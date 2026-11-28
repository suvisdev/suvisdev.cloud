import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'auth.dart';
import 'help.dart';
import 'home_screen.dart' show plateStyle;
import 'l10n/app_localizations.dart';
import 'level.dart';
import 'practice.dart';
import 'settings.dart';
import 'sfx.dart';
import 'table3d_data.dart';
import 'tile.dart';
import 'wallet.dart';

const _ink = Color(0xFF42384C);
const _plateText = TextStyle(fontSize: 17, fontWeight: FontWeight.w700);
const _felt = Color(0xFFE6F0DC);
const _sideW = 76.0; // 양옆 봇 자리 폭
// 배경 위에 띄운 글자가 잘 읽히게 두르는 흰 테
const _halo = [Shadow(color: Colors.white, blurRadius: 3), Shadow(color: Colors.white, blurRadius: 6)];

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
  late final Api api; // 화면을 연 순간의 계정에 묶는다(initState) — 늦게 만들면 그사이 바뀐 계정을 잡는다(리뷰 10차)
  GameState? s;
  // 지금 화면에 맞춘 나온 패(연습만) — 봇 수 재생에 맞춰 하나씩 늘고, 열려 있는 '나온 패' 시트도 이걸 따라간다
  final _out = ValueNotifier<List<String>?>(null);

  @override
  void dispose() {
    _out.dispose();
    super.dispose();
  }

  // 새 판을 다 보였는데 웹 세로 안내(RotateGate)에 가려 있었으면 — 가로로 돌려 판이 실제로 보인 뒤에 요청 id를 지운다.
  // 가려진 채 닫으면 다음 진입이 같은 id로 그 판을 받는다(새 판·하트를 또 쓰지 않게, 화폐 재리뷰)
  bool _settleWhenVisible = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_settleWhenVisible && TickerMode.valuesOf(context).enabled) {
      _settleWhenVisible = false;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_alive) api.settle();
      });
    }
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
    // 닫히는 애니메이션 중에도 mounted라 경로가 아직 활성인지도 본다(리뷰 29차)
    api = (widget.api ?? Api())..wanted = (() => mounted && (ModalRoute.of(context)?.isActive ?? true));
    _startSaved();
    if (widget.showHelpOnFirstVisit) _helpOnce();
  }

  /// 메인 화면에서 고른 난이도로, 없으면 지난번에 고른 난이도로 바로 시작한다(처음이면 중급).
  Future<void> _startSaved() async {
    level = widget.level ?? await savedLevel();
    await precacheTiles(); // 패 그림을 다 받아 둔 뒤 시작(봇 패가 끊겨 뜨지 않게)
    // 그동안 busy가 true라 새 게임 버튼은 꺼져 있다. 그래도 이미 판이 열렸으면 다시 시작하지 않는다 — 새 id로
    // 하트를 또 쓰고 하던 판을 바꾸지 않게(리뷰 37차)
    if (mounted && s == null) _apply(api.newGame(level));
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

  /// 아직 보이는 판 화면인가 — 닫히는 애니메이션 중에도 mounted라 경로가 활성인지도 본다
  bool get _alive => mounted && (ModalRoute.of(context)?.isActive ?? true);

  Future<void> _apply(Future<GameState> call) async {
    final who = Auth.me.value?.id; // 응답이 오기 전에 계정이 바뀌면 그 지갑은 버린다
    setState(() => busy = true);
    try {
      final next = await call;
      if (next.wallet != null) {
        Wallet.set(next.wallet!, owner: who); // 끝난 판 — 미션이 반영된 지갑
      } else if (next.finished && (s?.id != next.id || s?.finished != true)) {
        // 앞 판이 끝났어도 새 판이 끝났으면 — 판 id로 본다(리뷰 48차)
        // 끝났는데 지갑이 없음 = 서버가 기록에 실패해 뒤에서 다시 시도 중(2·10·60초). 그 뒤에 잔고를 다시 받는다(리뷰 19차)
        Wallet.recheck.value++;
      } else if (s?.id != next.id) {
        Wallet.refreshOrRetry(); // 새 판에 하트 1개를 썼다(실패하면 홈의 잔고 막대가 다시 받는다)
      }
      final fresh = s?.id != next.id;
      if (fresh) await _intro(next);
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
          _sound(Sfx.pass);
          await Future.delayed(const Duration(milliseconds: 1000));
          if (!mounted) return;
          if (passed.length == 3) _sweep();
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
        if (e.tiles == null) {
          _sound(Sfx.pass);
        } else if (e.seat != 0) {
          _sound(Sfx.play); // 내 수는 누를 때 이미 냈다
        }
        // 봇 한 수·모든 패스마다 잠깐 멈춰 누가 무엇을 했는지 보이게
        if (e.tiles == null) {
          await Future.delayed(const Duration(milliseconds: 1000));
        } else if (e.seat != 0) {
          // 앞에 놓이고 가운데에 떠오른 조합을 읽을 시간까지(Codex 1·2차)
          await Future.delayed(Duration(milliseconds: max(1200, _readMs(e.tiles!.length))));
        } else if (i + 1 < next.events.length || next.finished) {
          // 내 수: 봇 수나 결과 창이 바로 이어지면 — 누른 뒤 이미 흐른 시간을 빼고 남은 만큼만(Codex 3차)
          final spent = _playedAt == null ? 0 : DateTime.now().difference(_playedAt!).inMilliseconds;
          await Future.delayed(Duration(milliseconds: max(0, _readMs(e.tiles!.length) - spent)));
        }
        // 셋이 패스하면 바퀴가 끝난다 → 판을 비운다
        if (passed.length == 3) {
          if (e.seat == 0) await Future.delayed(const Duration(milliseconds: 600));
          if (!mounted) return;
          _sweep();
        }
      }
      // 닫히는 중(뒤로·다른 탭 계정 바뀜으로 걷힘)이면 결과 창을 띄우지 않는다 — 새 화면 위에 옛 판 결과가 뜨지 않게(리뷰 44차)
      if (!_alive) return;
      setState(() {
        _sync(next);
        s = next;
        picked.clear();
        flash = null;
      });
      // 새 판을 끝까지(나눠 주기·봇 수 재생) 보였고 닫히는 중이 아니면 — 새 판 요청 id를 지운다. 그 전에 닫으면
      // 다음 진입이 같은 id로 그 판을 받는다(리뷰 34·36차)
      if (fresh) {
        await WidgetsBinding.instance.endOfFrame; // setState는 다음 프레임 예약일 뿐 — 실제로 그려진 뒤에(리뷰 48차)
        if (mounted && _alive) {
          if (TickerMode.valuesOf(context).enabled) {
            api.settle();
          } else {
            _settleWhenVisible = true;
          }
        }
      }
      // 프레임을 기다리는 사이 닫혔으면(계정 전환 등) 결과 창을 띄우지 않는다 — 새 화면 위에 옛 판 결과가 뜨지 않게(리뷰 57차)
      if (!_alive) return;
      if (next.finished) _showResult(next);
      // 봇이 돌고 내 차례가 돌아왔으면 짧게 진동(옵션에서 끌 수 있음)
      if (!next.finished && next.turn == 0 && next.events.any((e) => e.seat != 0)) Settings.buzz();
    } on ApiError catch (e) {
      // 결과를 모르면(새 판이었다면 하트를 썼는지 모름) 화면이 닫혔어도 잔고는 다시 — 잔고 막대는 홈에 있다(리뷰 17·33차)
      final unsure = e.status != 422 && e.code != 'no_heart';
      if (unsure) Wallet.refreshOrRetry();
      // 하트 부족 — 다음 하트까지 남은 시간을 받는다(실패하면 잔고 막대가 30초 뒤, 리뷰 37차)
      if (e.code == 'no_heart') await Wallet.refreshOrRetry();
      if (!mounted) return;
      final t = AppLocalizations.of(context)!;
      if (e.code == 'no_heart') {
        _toast(t.noHeart(minutesToHeart(Wallet.current.value) ?? 10));
        return; // 판은 그대로(새 판을 안 열었다)
      }
      _toast(e.status == 422 ? _reason(t, e.code) : t.serverError);
      _rollback();
      if (unsure) await _resync();
    } catch (_) {
      Wallet.refreshOrRetry();
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
      final who = Auth.me.value?.id;
      final now = await api.get(g.id);
      if (now.wallet != null) {
        Wallet.set(now.wallet!, owner: who); // 끝난 판 응답이 유실됐어도 다시 받은 판의 지갑으로(리뷰 1차)
      } else if (now.finished && !g.finished) {
        Wallet.recheck.value++; // 끝났는데 지갑이 없음 — 서버가 기록을 다시 시도 중(리뷰 20차)
      }
      if (!_alive) return;
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

  /// 손패 칸·게임판의 위치를 재려고 그 BuildContext를 둔다(내 패가 고른 자리에서 나오게, Codex 2차)
  final _handCtx = <String, BuildContext>{};
  BuildContext? _arenaCtx;

  /// 방금 낸 내 패마다 있던 화면 위치(게임판 영역 좌표) — 판 좌표로는 원근을 거꾸로 풀어 옮긴다(가로·세로 둘 다, Codex 8~11차)
  final _myFrom = <String, Offset>{};

  /// 내기를 누른 때 — 응답이 빨리 와도 내 패가 앞에 놓이고 가운데에 뜰 시간을 채운다(이긴 수 포함)
  DateTime? _playedAt;

  /// 내기를 누르면 서버 응답·봇 장면을 기다리지 않고 바로 손에서 빼서 내 자리 앞에 놓는다.
  void _play(GameState g) {
    final tiles = [
      for (final c in g.hand)
        if (picked.contains(c)) c,
    ];
    final arena = _arenaCtx?.mounted == true ? _arenaCtx!.findRenderObject() as RenderBox? : null;
    _myFrom.clear();
    for (final c in tiles) {
      final box = _handCtx[c]?.mounted == true ? _handCtx[c]!.findRenderObject() as RenderBox? : null;
      if (box != null && arena != null) {
        _myFrom[c] = arena.globalToLocal(box.localToGlobal(box.size.center(Offset.zero)));
      }
    }
    _playedAt = DateTime.now();
    setState(() {
      gone.addAll(tiles);
      picked.clear();
      passed.clear();
      _record(0, tiles);
      flash = Play(0, tiles); // 응답이 올 때까지 내 차례 버튼을 잠근다
    });
    Sfx.play();
    _apply(api.move(g.id, tiles));
  }

  /// 셋이 패스해 바퀴가 끝남 — 바닥을 비우며 쓸어 담는 소리
  void _sweep() {
    setState(_clearRound);
    _sound(Sfx.sweep);
  }

  /// 판 장면의 효과음 — 나가기로 닫히는 중이면 옛 판 소리를 내지 않는다(리뷰 3차)
  void _sound(Sfx f) {
    if (_alive) f();
  }

  void _clearRound() {
    passed.clear();
    plays = List.filled(4, null);
    lead = null;
    order = [];
  }

  String _name(AppLocalizations t, int seat) => seat == 0 ? t.you : t.bot(seat);

  void _showResult(GameState g) {
    // 재생 중 열어 둔 연습 시트·나온 패 크게 보기 창은 닫는다 — 결과 창 뒤에 남으면 다시 시작한 판을 가린다(리뷰 3차·로고 3차).
    // 도움말·나가기 확인은 사용자가 보던 것이니 두고(로고 4차), 그 위에 결과를 띄운다
    Navigator.of(
      context,
    ).popUntil((r) => r is! ModalBottomSheetRoute && r.settings.name != outBigRoute && r.settings.name != combosRoute);
    final t = AppLocalizations.of(context)!;
    final winner = g.winner!;
    (winner == 0 ? Sfx.win : Sfx.lose)();
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

  // 봇이 내는 장면을 보여 주는 동안에는 그 봇이 차례다
  // 나눠 주는 동안엔 아무도 차례가 아니고, 시작 카드 동안엔 선이 차례다
  int? get _active => dealt != null ? null : intro ?? flash?.seat ?? (s == null || s!.finished ? null : s!.turn);

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final g = s;
    final active = _active;
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
            // 뒤로 가기 화살표는 두지 않는다(11-28 사용자) — 나가기는 제목 로고·기기 뒤로 가기
            automaticallyImplyLeading: false,
            // 제목(로고·난이도)을 누르면 홈으로 — 뒤로 가기와 같다(판 중이면 나갈지 묻는다, 11-27 사용자)
            // 낮은 가로 창은 제목 자리에 무늬 순서가 들어가니 앞에 작은 로고를 두어 거기서도 누를 수 있게(리뷰 19차)
            title: FittedBox(
              // 아주 좁은 창에서도 넘치지 않게 통째로 줄인다(리뷰 2차)
              fit: BoxFit.scaleDown,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // 키보드(Tab·Enter)로도 닿는 버튼으로 — 화살표를 뺀 뒤 홈으로 가는 유일한 화면 안 조작(Codex 21차)
                  Semantics(
                    button: true,
                    label: t.home,
                    child: InkWell(
                      key: const ValueKey('title-home'),
                      onTap: () => Navigator.maybePop(context),
                      borderRadius: BorderRadius.circular(8),
                      // 이름은 글씨가 아니라 제목 로고로(홈과 같게, 11-26 사용자) — 판이 오면 옆에 난이도
                      child: low && g != null
                          ? const Padding(padding: EdgeInsets.only(right: 8), child: TitleLogo(height: 24))
                          : Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const TitleLogo(height: 32),
                                if (g != null) Text('  ·  ${levelName(t, g.level)}'),
                              ],
                            ),
                    ),
                  ),
                  // 무늬 순서·나온 패·조합표는 둥근 바 위에(11-28 사용자 '상단에 바 하나 만들어서 바 위로') — 폰 가로는 위 막대 안
                  if (low && g != null) _practiceBar(t, g),
                ],
              ),
            ),
            backgroundColor: Colors.transparent,
            actions: [
              if (g != null) _TodayBadge(suit: g.today, label: narrowBar ? '' : t.today, doubles: g.doubles),
              const MuteButton(),
              // 꾸미기(배경·게임판·세트)는 옵션이 아니라 게임 화면에서 바로(11-27 사용자). 좁은 줄에선 게임 방법도 이 메뉴로 —
              // 버튼이 하나 늘어 새 게임·오늘의 무늬가 밀리지 않게
              PopupMenuButton<Future<void> Function(BuildContext)>(
                key: const ValueKey('table-look'),
                tooltip: t.tableBackground,
                icon: const Icon(Icons.palette_outlined),
                onSelected: (pick) => pick(context),
                itemBuilder: (_) => [
                  for (final (key, label, pick) in [
                    ('table-background', t.tableBackground, (BuildContext c) => pickBackground(c, 'table')),
                    ('board', t.board, pickBoard),
                    ('board-set', t.boardSet, pickBoardSet),
                    if (narrowBar) ('help', t.help, showHelp),
                  ])
                    PopupMenuItem(key: ValueKey(key), value: pick, child: Text(label)),
                ],
              ),
              if (!narrowBar)
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
                        live: _out,
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
                                        child: Builder(
                                          builder: (c) {
                                            _handCtx[code] = c;
                                            return TileView(
                                              key: ValueKey('hand-$code'),
                                              code: code,
                                              width: tileW,
                                              selected: picked.contains(code),
                                              onTap: !myTurn || !g.playable.contains(code)
                                                  ? null
                                                  : () {
                                                      Sfx.select();
                                                      setState(
                                                        () => picked.contains(code)
                                                            ? picked.remove(code)
                                                            : picked.add(code),
                                                      );
                                                    },
                                            );
                                          },
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                            );
                            // 좁은 세로 창·큰 글자에선 둘째 버튼이 다음 줄로(한 줄이면 274px 미만에서 넘침, Codex 18차)
                            final buttons = Wrap(
                              alignment: WrapAlignment.center,
                              runSpacing: 6,
                              children: [
                                // Codex 그림 판 B안(연보라 패스·코랄 내기, 11-28 사용자). 왼쪽 28%가 아이콘 자리
                                OutlinedButton(
                                  style: plateStyle('pass', _plateText, 48, true, left: 44, minWidth: 120),
                                  onPressed: !myTurn ? null : () => _apply(api.move(g.id, [])),
                                  child: Text(t.pass),
                                ),
                                const SizedBox(width: 10),
                                FilledButton(
                                  style: plateStyle('play', _plateText, 48, true, left: 44, minWidth: 120),
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
                            final body = Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 12),
                              child: Column(
                                children: [
                                  // 낮은 가로 창(폰 가로, 앱 기본): 폭을 거의 다 쓰는 3D 탁자와 가장자리에 세운 상대 패 벽(11-28 사용자)
                                  // 세로·큰 창은 같은 바를 본문 맨 위에(위 막대에 넣으면 좁은 폭에서 글자가 너무 작아진다)
                                  if (!low) ...[_practiceBar(t, g), const SizedBox(height: 6)],
                                  if (low)
                                    const Spacer() // 탁자는 뒤에 화면 전체로 깔린다(아래 Stack)
                                  else ...[
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
                                      // 가운데 판: 높이(side)는 남은 높이와 폭 중 작은 쪽, 폭(wide)은 남는 가로를 1.8배까지 쓴다 —
                                      // 정사각형이면 폰 가로에서 한 변 ~165px라 낸 패가 작았다(11-26 '낸 패 크게')
                                      child: LayoutBuilder(
                                        builder: (context, mid) {
                                          final room = mid.maxWidth - 2 * _sideW - 12;
                                          final side = max(0.0, min(room, mid.maxHeight));
                                          final wide = max(side, min(room, side * 1.8));
                                          // 넓은 판은 덜 눕힌다 — 같은 각이면 먼 쪽 자리의 패가 더 작아 보인다
                                          final tilt = wide > side * 1.3 ? -.32 : -.42;
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
                                                  ..rotateX(tilt) // 위(먼 쪽)가 뒤로 → 가까운 아래 가장자리가 넓게
                                                  ..scaleByDouble(.9, .9, 1, 1),
                                                child: ValueListenableBuilder(
                                                  valueListenable: Settings.board,
                                                  builder: (_, b, child) => Container(
                                                    width: wide,
                                                    height: side,
                                                    decoration: BoxDecoration(
                                                      color: _felt,
                                                      // 고른 판 그림(0 = 기본 펠트) — 모서리 둥글기대로 잘린다
                                                      image: b == 0
                                                          ? null
                                                          : DecorationImage(
                                                              image: AssetImage(boardAsset(b)),
                                                              fit: BoxFit.cover,
                                                            ),
                                                      borderRadius: BorderRadius.circular(24),
                                                      border: Border.all(
                                                        color: b == 0
                                                            ? const Color(0xFFCFDDBF)
                                                            : boardEdges[b].withValues(alpha: .5),
                                                        width: 2,
                                                      ),
                                                      // 두께·그림자도 판 크기에 비례(고정 px면 아주 작은 판에서 원근 분모가 0을 지난다)
                                                      boxShadow: [
                                                        BoxShadow(color: boardEdges[b], offset: Offset(0, side * .022)),
                                                        BoxShadow(
                                                          color: const Color(0x30000000),
                                                          blurRadius: side * .036,
                                                          offset: Offset(0, side * .04),
                                                        ),
                                                      ],
                                                    ),
                                                    child: child,
                                                  ),
                                                  child: Center(
                                                    child: Padding(
                                                      padding: const EdgeInsets.all(6),
                                                      child: _felt4(t, g),
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
                                  ],
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
                            // 낮은 가로 창(폰 가로, 앱 기본): 블렌더로 렌더한 3D 탁자를 화면 폭 가득 손패 뒤까지 깔고, 손패는 그 앞에
                            // 원근 없이 일자로(11-28 사용자 '내 패만 일자로 앞에 깔고 2D 느낌')
                            return low
                                ? Stack(
                                    children: [
                                      Positioned.fill(child: _arena(t, g)),
                                      body,
                                    ],
                                  )
                                : body;
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

  /// 무늬 순서(약한 것부터) + 나온 패·조합표 버튼을 올린 둥근 바
  Widget _practiceBar(AppLocalizations t, GameState g) => Container(
    key: const ValueKey('top-bar'),
    margin: const EdgeInsets.only(left: 8),
    padding: const EdgeInsets.fromLTRB(4, 3, 6, 3),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .72),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: _ink.withValues(alpha: .15)),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Flexible(
          child: _SuitOrder(suits: g.suits, label: t.suitOrder),
        ),
        const SizedBox(width: 6),
        PracticeButtons(live: _out, suits: g.suits),
      ],
    ),
  );

  /// 낮은 가로 창의 3D 탁자(11-28 사용자): 화면 폭을 거의 다 쓰는 판을 뒤로 눕히고, 판 위의 모든 것 — 낸 패와 상대가 세워 든
  /// 패 — 을 같은 판 좌표에 놓아 한 카메라(같은 원근)로 그린다. 낸 패는 낸 사람 쪽을 향해 눕고, 상대 패는 판 가장자리에 선다.
  Widget _arena(AppLocalizations t, GameState g) => LayoutBuilder(
    builder: (context, box) {
      _arenaCtx = context;
      final (w, h) = (box.maxWidth, box.maxHeight);
      // 판을 그릴 높이가 거의 없으면(웹 창을 아주 낮게 줄임) 그리지 않는다 — 깊이가 0·음수가 되면 배치가 깨진다(Codex 4차)
      // 대신 지금 가장 센 조합과 내 차례만 납작하게 보여 준다 — 상대가 뭘 냈는지 모른 채 두지 않게(Codex 6차)
      // 손패 줄 윗선 — 탁자 판 위의 것은 이보다 위에 있어야 손패에 덮이지 않는다(build의 손패 크기 식과 같게)
      // 손패 패 폭은 build의 식 그대로(본문 여백 24·간격 8·버튼 칸을 뺀 폭에 13장, 높이의 13.5%까지). 고른 패는 패 높이의
      // 18%만큼 들린다(TileView.selected) — 그만큼 더 위가 윗선(Codex 17·18차)
      final handW = w - 24 - 8 - min(240.0, w * .32);
      final handTile = max(6.0, min(52.0, min((handW - 12) / 13 - 4, h * .135))) * 4 / 3;
      final handTop = h - (handTile * 1.18 + 28);
      Widget flat() {
        String who(int s) => s == 0 ? t.you : t.bot(s);
        final status = [
          if (_active != null) _active == 0 ? t.yourTurn : '${who(_active!)} ${t.turn}',
          for (final p in passed) '${who(p)} ${t.pass}',
          // 3D 판이 없으니 상대 남은 장수도 글자로(Codex 18차)
          for (final s in [1, 2, 3]) '${who(s)} ${shown[s]}',
        ].join(' · ');
        // 손패 위 남은 칸 안에만(손패가 판 위에 겹쳐 그려진다, Codex 16차)
        return Align(
          alignment: Alignment.topCenter,
          child: SizedBox(
            height: max(24.0, handTop - 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (lead != null && plays[lead!] != null) Flexible(child: _center(lead!, plays[lead!]!, Offset.zero)),
                Flexible(
                  child: Text(
                    status,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: _ink, fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
        );
      }

      if (h < 60 || w < 120) return flat();
      // 렌더 그림은 화면 폭에 맞춘다(양옆이 끊기지 않게). 위는 맞은편 이름 자리를 남기고, 화면보다 길면 앞 가장자리가 손패
      // 아래로 들어가고, 짧으면 바닥에 붙인다
      // 폰 가로는 폭이 먼저 닿는다. 아주 낮고 넓은 창(웹)은 높이로 줄여 가운데에 — 판 앞쪽(내 자리)이 화면 밖으로
      // 나가지 않게(Codex 12차). 그림 아래 15%는 손패 밑으로 들어가도 되는 판 앞 가장자리
      // 내가 낸 패(판 깊이 .66, 패 높이 절반만큼 아래까지)가 손패 윗선 위에 오게 — 손패 줄 높이는 build의 손패 크기 식과
      // 같게(패 높이 + 위아래 여백). 폰 가로는 그대로이고 아주 낮은 창만 줄어든다(Codex 13차)
      // 그림 맨 위를 화면 맨 위에 둘 때의 낸 패 아래 끝(세로 위치는 아래 top에서 정한다)
      double spotBottom(double k) {
        const oy = 0.0;
        final ox = (w - t3Size.width * k) / 2;
        final q = [for (final p in t3Felt) Offset(p.dx * k + ox, p.dy * k + oy)];
        final bw = (q[2].dx - q[3].dx), d = bw * t3FeltAspect;
        // 내 자리 + 놓인 패 높이 절반 + 두께(_laid의 laidW 식) — 낸 패의 실제 아래쪽 끝
        final lw = min(5.5 * bw / 100, d * .3 / (2 / 3 + .11));
        return MatrixUtils.transformPoint(_quad(bw, d, q), Offset(bw / 2, _spots(bw, d)[0].dy + lw * (2 / 3 + .11))).dy;
      }

      var k = min(w / t3Size.width, h / (t3Size.height * .85));
      for (var i = 0; i < 12 && spotBottom(k) > handTop; i++) {
        k *= .93;
      }
      // 줄여도 손패에 덮이면(본문이 아주 낮은 창) 3D 판 대신 납작한 줄로(Codex 15차)
      if (spotBottom(k) > handTop) return flat();
      // 그림이 본문보다 짧으면 바닥에 붙이되, 낸 패가 손패 윗선을 넘지 않는 데까지만 내린다 — 줄인 그림을 바닥에 붙여
      // 낸 패가 도로 손패 밑으로 들어가던 것(Codex 19차, 844×190)
      final ox = (w - t3Size.width * k) / 2, oy = max(0.0, min(h - t3Size.height * k, handTop - spotBottom(k)));
      Offset px(Offset p) => Offset(p.dx * k + ox, p.dy * k + oy);
      // 판 좌표: 펠트 앞 가장자리의 화면 폭을 판 폭으로 — 가까운 쪽 배율이 1쯤이라 패 크기 감이 화면과 같다
      final bw = (t3Felt[2].dx - t3Felt[3].dx) * k, depth = bw * t3FeltAspect, u = bw / 100;
      final m = _quad(bw, depth, [for (final p in t3Felt) px(p)]);
      final back = Matrix4.tryInvert(m) ?? Matrix4.identity();
      Offset at(double x, double y) => MatrixUtils.transformPoint(m, Offset(x, y));
      Offset onBoard(Offset screen) => MatrixUtils.transformPoint(back, screen); // 판 위 점(바닥)의 화면 → 판 좌표
      // 남은 패가 서는 칸: 맞은편은 가운데로 모으고, 양옆은 먼 쪽부터
      int first(int s, int n) => s == 2 ? (13 - n) ~/ 2 : 0;
      Offset handOf(int seat, int i, String c) {
        if (seat == 0) return _myFrom[c] != null ? onBoard(_myFrom[c]!) : Offset(bw * .42, depth * 1.1);
        // 봇이 낸 패는 내기 전 벽의 끝쪽 칸에서 나온다고 본다(낸 장수만큼이 벽 끝에서 빠짐, Codex 2·3차)
        final n0 = shown[seat] + (plays[seat]?.length ?? 0);
        return onBoard(px(t3Walls[seat - 1][min(12, first(seat, n0) + shown[seat] + i)].foot));
      }

      Widget seat(int s, String name, {bool stacked = false}) => FittedBox(
        fit: BoxFit.scaleDown,
        child: _Seat(
          stacked: stacked,
          name: name,
          g: g,
          seat: s,
          count: shown[s],
          active: _active == s,
          turnLabel: t.turn,
          compact: true,
          passed: passed.contains(s),
          passLabel: t.pass,
        ),
      );
      return Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            left: ox,
            top: oy,
            width: t3Size.width * k,
            height: t3Size.height * k,
            child: Image.asset('assets/table3d/table.png', fit: BoxFit.fill),
          ),
          // 판 위의 것은 펠트 네 모서리로 만든 원근 변환 안에 그린다 — 렌더와 같은 카메라로 보인다
          Positioned(
            left: 0,
            top: 0,
            width: bw,
            height: depth,
            child: IgnorePointer(
              child: Transform(
                transform: m,
                child: ValueListenableBuilder(
                  valueListenable: Settings.board,
                  builder: (_, b, _) => Stack(
                    clipBehavior: Clip.none,
                    children: [
                      if (b != 0)
                        Positioned.fill(
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(depth * .03),
                              image: DecorationImage(image: AssetImage(boardAsset(b)), fit: BoxFit.cover),
                            ),
                          ),
                        ),
                      Center(
                        child: Opacity(
                          opacity: .13,
                          child: SvgPicture.asset(
                            'assets/icons/suit_${g.today}.svg',
                            width: depth * .3,
                            height: depth * .3,
                          ),
                        ),
                      ),
                      for (final s in [0, 1, 2, 3]) _TurnGlow(seat: s, on: _active == s),
                      ..._laid(bw, depth, u, handOf),
                    ],
                  ),
                ),
              ),
            ),
          ),
          // 상대가 세워 든 패: 칸마다 렌더한 그림을 남은 장수만큼(먼 것부터 그려 가까운 것이 위에)
          for (final s in [2, 1, 3])
            for (var i = first(s, shown[s]); i < first(s, shown[s]) + shown[s]; i++)
              Positioned.fromRect(
                rect: Rect.fromLTWH(
                  t3Walls[s - 1][i].rect.left * k + ox,
                  t3Walls[s - 1][i].rect.top * k + oy,
                  t3Walls[s - 1][i].rect.width * k,
                  t3Walls[s - 1][i].rect.height * k,
                ),
                child: IgnorePointer(
                  child: Image.asset('assets/table3d/wall_${s}_$i.png', key: ValueKey('wall-$s-$i'), fit: BoxFit.fill),
                ),
              ),
          // 무슨 패가 나왔는지 가운데에 똑바로 크게 따로 보인다(11-28 사용자 '앞에도 생기고 가운데에서도 확인 — 둘 다 따로').
          // 앞에 놓이는 모션이 끝날 즈음 톡 떠오른다
          if (lead != null && plays[lead!] != null)
            Builder(
              builder: (_) {
                final mid = at(bw / 2, depth * .45);
                return Positioned(
                  left: mid.dx - w * .22,
                  width: w * .44,
                  top: mid.dy - h * .13,
                  height: h * .26,
                  child: IgnorePointer(child: _center(lead!, plays[lead!]!, Offset.zero)),
                );
              },
            ),
          if ((lead == null || plays[lead!] == null) &&
              dealt == null &&
              intro == null &&
              flash == null &&
              !g.finished &&
              g.turn == 0)
            Positioned(
              left: 0,
              right: 0,
              top: at(bw / 2, depth * .45).dy - 12,
              child: Center(
                child: Text(
                  t.yourTurn,
                  style: const TextStyle(color: _ink, fontSize: 15, fontWeight: FontWeight.w600),
                ),
              ),
            ),
          // 봇 이름: 각자 패 벽 가운데 칸(13칸 중 7번째)의 윗변 바로 위에 똑바로 — 패 뒤에 앉은 사람처럼(11-28 사용자).
          // 남은 장수를 따라 움직이지 않고(낼 때마다 옮겨 다녔다), 화면 위로는 넘지 않는다(Codex 12차)
          for (final s in [1, 2, 3])
            Builder(
              builder: (_) {
                final top = px(t3Walls[s - 1][6].top);
                final (cw, ch) = s == 2 ? (w * .4, 34.0) : (96.0, 64.0);
                return Positioned(
                  left: top.dx - cw / 2,
                  top: max(0.0, top.dy - ch - 2),
                  width: cw,
                  height: ch,
                  child: Align(
                    alignment: Alignment.bottomCenter,
                    child: seat(s, t.bot(s), stacked: s != 2),
                  ),
                );
              },
            ),
        ],
      );
    },
  );

  /// 판 좌표 직사각형(0,0)~(bw,d)을 화면의 네 점 [q](먼 왼쪽·먼 오른쪽·가까운 오른쪽·가까운 왼쪽)으로 옮기는 원근 변환
  /// (정사각형 → 사각형 호모그래피, Heckbert). z는 그대로 둔다
  static Matrix4 _quad(double bw, double d, List<Offset> q) {
    final [p0, p1, p2, p3] = q;
    final dx1 = p1.dx - p2.dx, dx2 = p3.dx - p2.dx, dx3 = p0.dx - p1.dx + p2.dx - p3.dx;
    final dy1 = p1.dy - p2.dy, dy2 = p3.dy - p2.dy, dy3 = p0.dy - p1.dy + p2.dy - p3.dy;
    final den = dx1 * dy2 - dx2 * dy1;
    final g = (dx3 * dy2 - dx2 * dy3) / den, hh = (dx1 * dy3 - dx3 * dy1) / den;
    final a = p1.dx - p0.dx + g * p1.dx, b = p3.dx - p0.dx + hh * p3.dx;
    final dd = p1.dy - p0.dy + g * p1.dy, e = p3.dy - p0.dy + hh * p3.dy;
    // 열 우선: x' = (a·u + b·v + x0) / (g·u + h·v + 1), u = x/bw, v = y/d
    return Matrix4(a, dd, 0, g, b, e, 0, hh, 0, 0, 1, 0, p0.dx, p0.dy, 0, 1)
      ..multiply(Matrix4.diagonal3Values(1 / bw, 1 / d, 1));
  }

  /// 각자 낸 패가 놓이는 자기 앞 자리(판 좌표): 나·왼쪽·맞은편·오른쪽
  /// 내 자리는 판 앞쪽이 손패에 덮여서(3D 탁자가 손패 뒤까지 깔린다) 조금 안쪽에, 맞은편은 가운데 조합과 겹치지 않게 벽 가까이
  List<Offset> _spots(double bw, double depth) => [
    Offset(bw / 2, depth * .66),
    Offset(bw * .22, depth * .45),
    Offset(bw / 2, depth * .2),
    Offset(bw * .78, depth * .45),
  ];

  /// 판 위에 눕힌 밀려난 패(판 좌표): 각자 자기 앞에 자기 쪽을 향해 놓는다(옆 사람 패는 옆으로 누움, 11-28 사용자).
  /// 지금 가장 센 패는 여기 말고 [_center]가 판 가운데에 똑바로 세워 그린다.
  List<Widget> _laid(double bw, double depth, double u, Offset Function(int seat, int k, String c) handOf) {
    const turnsOf = [0, 1, 2, 3]; // 시계 방향 90° 회전 수: 패 아래쪽이 낸 사람을 향한다
    final spots = _spots(bw, depth);
    // 패마다 출발점(판 좌표)은 [handOf]: 내 패는 고른 패가 있던 자리, 봇 패는 내기 전 패 벽의 칸

    // 지금 가장 센 패는 자기 앞에 진하게, 손에서 앞으로 내는 모션으로 놓인다(11-28 사용자 '앞에 내는 것처럼') — 키는 laid-
    // (같은 패를 가운데에도 따로 크게 보이므로 play-·drop- 키는 가운데 것). 밀려난 패는 흐리게 그대로
    Widget row(int seat, List<String> m, double tw, {required bool top}) => RotatedBox(
      quarterTurns: turnsOf[seat],
      child: Row(
        key: ValueKey('${top ? 'laid' : 'play'}-$seat'),
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final c in m)
            Padding(
              padding: EdgeInsets.all(tw * .04),
              child: top
                  ? _DropIn(
                      key: ValueKey('laid-$seat-${m.join()}-$c'),
                      index: m.indexOf(c),
                      // 그 패의 출발점에서 놓일 칸까지 — 돌린 좌표(RotatedBox)로 바꾸고 줄 안 제 칸 위치를 뺀다
                      from:
                          _unturn(handOf(seat, m.indexOf(c), c) - spots[seat], turnsOf[seat]) -
                          Offset((m.indexOf(c) - (m.length - 1) / 2) * tw * 1.08, 0),
                      flip: seat != 0,
                      child: TileView(code: c, width: tw, edge: _unturn(const Offset(0, 1), turnsOf[seat])),
                    )
                  : TileView(
                      key: ValueKey('drop-$seat-${m.join()}-$c'),
                      code: c,
                      width: tw,
                      edge: _unturn(const Offset(0, 1), turnsOf[seat]), // 돌아간 패도 두께는 판 앞쪽으로
                    ),
            ),
        ],
      ),
    );

    // 옆자리 줄은 판 깊이 방향으로 눕는다 — 장수가 많으면 판 깊이 안에 들도록 줄인다(Codex 5차)
    // 내 자리(.66d, 손패에 덮이기 전까지 .34d)·맞은편(.2d)은 남은 깊이 안에 패 높이 절반 + 두께(.11)가 들게(Codex 6차)
    double laidW(int s) => switch (s) {
      1 || 3 => min(5.5 * u, depth * .42 / (plays[s]!.length * 1.08)),
      0 => min(5.5 * u, depth * .3 / (2 / 3 + .11)),
      _ => min(5.5 * u, depth * .19 / (2 / 3 + .11)),
    };

    Widget place(Offset c, Widget child) => Positioned(
      left: c.dx - bw,
      top: c.dy - bw,
      width: 2 * bw,
      height: 2 * bw,
      child: Center(child: child),
    );
    return [
      for (final s in [0, 1, 2, 3])
        if (plays[s] != null)
          place(
            spots[s],
            s == lead
                ? row(s, plays[s]!, laidW(s), top: true)
                : Opacity(opacity: .5, child: row(s, plays[s]!, laidW(s), top: false)),
          ),
    ];
  }

  /// 화면(판) 좌표의 벡터를 시계 방향 [q]번 90° 돌린 RotatedBox 안 좌표로
  static Offset _unturn(Offset v, int q) => switch (q % 4) {
    0 => v,
    1 => Offset(v.dy, -v.dx),
    2 => -v,
    _ => Offset(-v.dy, v.dx),
  };

  /// n장을 낸 뒤 앞에 다 놓이고(_laid) 가운데 조합이 다 떠올라(_center) 잠깐 읽을 때까지(ms)
  static int _readMs(int n) => _DropIn.gap * (n + 3) + _DropIn.fall + 500;

  /// 판 가운데에 똑바로 보이는 가장 센 패(무슨 패인지 확인용). 칸에 맞춰 줄어든다. [from]이 0이면 제자리에서 떠오른다
  Widget _center(int seat, List<String> m, Offset from) => FittedBox(
    fit: BoxFit.scaleDown,
    child: Row(
      key: ValueKey('play-$seat'),
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final c in m)
          Padding(
            padding: const EdgeInsets.all(2),
            child: _DropIn(
              key: ValueKey('drop-$seat-${m.join()}-$c'),
              // 앞에 놓이는 패가 다 앉은 뒤 조합 전체가 한 번에 떠오른다 — 누가 냈는지 먼저, 무슨 패인지 다음(Codex 1·2차)
              index: m.length + 3,
              from: from,
              flip: false,
              child: TileView(code: c, width: 46),
            ),
          ),
      ],
    ),
  );

  /// 정사각형 판: 지금 가장 센 패(이길 패)는 판 가운데에 진하게, 나머지 자리는 자기 앞(판 가장자리)에 흐리게.
  /// 가운데 패는 낸 자리 쪽에서 날아와 누가 냈는지 보인다(11-27 사용자 '가운데 내 차례 자리에 패가 오게').
  /// 칸은 판 크기에 비례 — 가로가 넓으면 위·아래 자리 칸이 넓어진다.
  Widget _felt4(AppLocalizations t, GameState g) {
    Widget area(int seat, double w, double h, int perRow, {bool center = false}) {
      final m = plays[seat];
      final top = seat == lead;
      if (m == null || top != center) return SizedBox(width: w, height: h); // 가장 센 패는 가장자리가 아니라 가운데에
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
                          // 같은 수면 키가 같아 다시 그려도 모션이 반복되지 않는다. 가장자리 패는 날아오지 않는다 — 새로 낸
                          // 패는 늘 이길 패라 가운데에 놓이고, 가장자리는 밀려난 옛 이길 패뿐이다(이미 끝난 수가 다시
                          // 날아오는 것처럼 보였다, 리뷰 3차)
                          child: center
                              ? _DropIn(
                                  key: ValueKey('drop-$seat-${m.join()}-$c'),
                                  index: m.indexOf(c),
                                  from: _from[seat],
                                  child: TileView(code: c, width: 108), // 가운데 패는 크게 — 화면에선 칸에 맞춰 줄어 약 1.25배(11-28 사용자)
                                )
                              : TileView(key: ValueKey('drop-$seat-${m.join()}-$c'), code: c, width: 54),
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
      // 칸은 실제 판 안쪽 크기로 나눈다 — 바깥 패딩까지 짐작해 빼면 칸끼리 겹칠 수 있다
      child: LayoutBuilder(
        builder: (_, box) {
          final (iw, ih) = (box.maxWidth, box.maxHeight);
          return Stack(
            children: [
              // 차례인 사람 앞 판 가장자리를 금빛으로 — 자리 칸만으로는 누가 차례인지 잘 안 보였다(11-28 사용자)
              for (final seat in [0, 1, 2, 3]) _TurnGlow(seat: seat, on: _active == seat),
              // 칸 나누기: 위·아래 24%, 양옆 15.5%, 가운데 66%×50%(사이 여유는 원근으로 벌어지는 몫) — 가운데 패(약 1.25배)가 커도 가장자리의
              // 밀려난 패를 가리지 않는다(리뷰 1차)
              Align(alignment: Alignment.topCenter, child: area(2, iw * .8, ih * .24, 5)),
              // 양옆 칸은 좁고 길어 한 줄 장 수를 칸 모양에 맞춰 고른다(리뷰 2차: 한 줄 세 장 고정이면 10px)
              for (final (seat, at) in [(1, Alignment.centerLeft), (3, Alignment.centerRight)])
                Align(
                  alignment: at,
                  child: area(seat, iw * .155, ih * .5, _perRow(plays[seat]?.length ?? 0, iw * .155, ih * .5)),
                ),
              Align(alignment: Alignment.bottomCenter, child: area(0, iw * .8, ih * .24, 5)),
              Center(
                // 아주 작은 판(글자 크게)에선 가운데 패와 '내 차례'를 함께 줄인다
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (lead != null && plays[lead!] != null) area(lead!, iw * .66, ih * .5, 5, center: true),
                      // 가운데 패가 있으면 그 자리를 패에 준다 — 작은 판에선 글자와 겹쳤다. 차례는 내 자리 '차례' 표시가 알린다
                      if (myTurn && (lead == null || plays[lead!] == null))
                        Text(
                          t.yourTurn,
                          style: const TextStyle(color: _ink, fontSize: 15, fontWeight: FontWeight.w600),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

/// [n]장을 [w]×[h] 칸에 놓을 때 패가 가장 크게 보이는 한 줄 장 수(패 한 칸은 여백 포함 58×76)
int _perRow(int n, double w, double h) {
  double scale(int c) => min(w / (c * 58), h / ((n / c).ceil() * 76));
  var best = 1;
  for (var c = 2; c <= n; c++) {
    if (scale(c) > scale(best)) best = c;
  }
  return best;
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

  /// 3D 탁자 옆자리 이름 칩: 이름 / 장수 / 점수를 세로로(판 바깥 좁은 자리에 맞게)
  final bool stacked;

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
    this.stacked = false,
  });

  /// 3D 탁자 봇 자리: 상자 없이 이름만(compact는 3D 탁자 봇과 내 자리에만 쓴다)
  bool get bare => compact && seat != 0;

  @override
  Widget build(BuildContext context) {
    // 3D 탁자 봇: 둥근 프로필(무늬 캐릭터) + 이름 — 프로필 그림 기능이 생기면(상점 캐릭터) 그 그림으로 바꾼다
    final avatar = AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: 30,
      height: 30,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white,
        border: Border.all(color: active ? gold : const Color(0xFFE9DFD1), width: active ? 3 : 1.5),
        boxShadow: [BoxShadow(color: active ? gold.withValues(alpha: .5) : const Color(0x22000000), blurRadius: 6)],
      ),
      child: SvgPicture.asset('assets/icons/suit_${const ['m', 'c', 'l', 's'][seat]}.svg'),
    );
    final label = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (bare && !stacked) ...[avatar, const SizedBox(width: 6)],
        Text(
          name,
          style: bare
              ? const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 16, shadows: _halo)
              : const TextStyle(fontWeight: FontWeight.bold, color: _ink),
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
    // 꽃잎·보너스는 그림 아이콘(이모지는 기기마다 모양이 달라 깨졌다, Codex 그림 11-28)
    // 화면 낭독기는 그림 대신 '꽃잎 3, 보너스 2'로 읽는다(Codex 22차)
    final stats = Text.rich(
      semanticsLabel: AppLocalizations.of(context)!.scoreStats(g.petals[seat], g.bonus[seat]),
      TextSpan(
        children: [
          WidgetSpan(alignment: PlaceholderAlignment.middle, child: scoreIcon('petal')),
          TextSpan(text: '${g.petals[seat]}  '),
          WidgetSpan(alignment: PlaceholderAlignment.middle, child: scoreIcon('bonus')),
          TextSpan(text: '${g.bonus[seat]}'),
        ],
      ),
      style: TextStyle(fontSize: 12, color: _ink, shadows: bare ? _halo : null),
    );
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
      // 3D 탁자의 봇 이름은 상자 없이 글자만 띄운다(11-28 사용자 '네모 박스 말고 유저처럼 닉네임만') — 차례는 '차례' 배지가 알린다
      decoration: bare
          ? null
          : BoxDecoration(
              color: active ? const Color(0xFFFFF7E0) : Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: active ? gold : const Color(0xFFE9DFD1), width: active ? 3 : 1),
              boxShadow: active ? [BoxShadow(color: gold.withValues(alpha: .35), blurRadius: 10)] : null,
            ),
      width: fan == Axis.vertical ? _sideW : null,
      child: compact && stacked
          ? Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                avatar,
                const SizedBox(height: 2),
                label,
                Text(
                  '×$count',
                  style: TextStyle(color: _ink, fontSize: 12, shadows: bare ? _halo : null),
                ),
                stats,
              ],
            )
          : compact
          ? Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                label,
                if (seat != 0) ...[
                  const SizedBox(width: 8),
                  Text('×$count', style: const TextStyle(color: _ink, fontSize: 12)),
                ],
                const SizedBox(width: 12),
                stats,
              ],
            )
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
        _Pulse(on: active, child: box),
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
            // 내 칩은 위로, 탁자 위쪽 봇 칩(화면 맨 위)은 아래로 띄운다 — 위로 띄우면 화면 밖으로 잘린다
            top: seat == 0 ? -40 : null,
            bottom: seat == 0 ? null : -40,
            right: -12,
            child: _Bubble(key: ValueKey('passed-$seat'), text: passLabel, tail: seat == 0),
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
      return _tilt(
        SizedBox(
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
    return _tilt(RotatedBox(quarterTurns: turns, child: fan));
  }

  /// 상대 패를 원근으로 기울인다 — 판을 사이에 두고 마주 앉아 패를 세워 든 걸 내 자리에서 보는 느낌(11-27 사용자 '같이 게임을
  /// 하고 있는 느낌, 2.5D·3D'). 맞은편은 위가 멀어지게, 양옆은 판 바깥쪽이 멀어지게. 자리 칸 크기는 그대로(그리기만 기울임)
  Widget _tilt(Widget child) => Transform(
    // 내 쪽 가장자리를 축으로 — 먼 쪽이 줄어들어 사다리꼴로 보인다(가운데 축이면 납작해지기만 했다)
    alignment: switch (turns) {
      1 => Alignment.centerRight,
      3 => Alignment.centerLeft,
      _ => Alignment.bottomCenter,
    },
    transform: Matrix4.identity()
      ..setEntry(3, 2, 0.005)
      ..rotateX(turns == 2 ? 0.6 : 0)
      ..rotateY(switch (turns) {
        1 => 0.7,
        3 => -0.7,
        _ => 0.0,
      }),
    child: child,
  );
}

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

  /// 뒷면에서 앞면으로 뒤집히며 앉는다(남의 패). 내 패는 이미 앞면이라 뒤집지 않는다
  final bool flip;
  const _DropIn({super.key, required this.index, required this.from, required this.child, this.flip = true});

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
        final turn = flip ? pi * (1 - Curves.easeInOut.transform(t)) : 0.0; // 뒷면(π) → 앞면(0)
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

/// 차례인 자리 앞 판 가장자리에서 번지는 노란빛 — 그 사람 쪽 가장자리 가운데가 가장 밝고 둥글게 흐려진다.
/// 금색 띠로 칠하면 초록 판 위에서 칙칙한 막대로 보였다
class _TurnGlow extends StatelessWidget {
  final int seat; // 0 아래(나)·1 왼쪽·2 위·3 오른쪽
  final bool on;
  const _TurnGlow({required this.seat, required this.on});

  @override
  Widget build(BuildContext context) => Positioned.fill(
    child: IgnorePointer(
      child: AnimatedOpacity(
        key: ValueKey('turn-glow-$seat'),
        opacity: on ? 1 : 0,
        duration: const Duration(milliseconds: 250),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: RadialGradient(
              center: switch (seat) {
                0 => Alignment.bottomCenter,
                1 => Alignment.centerLeft,
                2 => Alignment.topCenter,
                _ => Alignment.centerRight,
              },
              radius: .75, // 판 짧은 변의 비율
              colors: const [Color(0xCCFFE27A), Color(0x00FFE27A)],
            ),
          ),
        ),
      ),
    ),
  );
}

/// 차례가 오면 자리 칸이 세 번 두근거린다. 끝없이 반복하지 않는다(눈이 피곤하고, 화면이 계속 다시 그려진다).
/// 기기에서 움직임 줄이기를 켰으면 두근거리지 않는다
class _Pulse extends StatefulWidget {
  final bool on;
  final Widget child;
  const _Pulse({required this.on, required this.child});

  @override
  State<_Pulse> createState() => _PulseState();
}

class _PulseState extends State<_Pulse> with SingleTickerProviderStateMixin {
  late final _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 320));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.disableAnimationsOf(context)) {
      _c.value = 0; // 두근거리는 도중 움직임 줄이기를 켜도 바로 멈춘다(리뷰 2차)
    } else if (widget.on && !_c.isAnimating && _c.value == 0) {
      _beat();
    }
  }

  @override
  void didUpdateWidget(_Pulse old) {
    super.didUpdateWidget(old);
    if (widget.on && !old.on) _beat();
    // 차례가 넘어가면 바로 멈춘다 — 봇 장면(1.2초)이 두근거림(약 1.9초)보다 짧아 다음 사람과 함께 뛰었다(리뷰 1차)
    if (!widget.on && old.on) _c.value = 0;
  }

  void _beat() {
    if (MediaQuery.disableAnimationsOf(context)) return;
    _c.repeat(reverse: true, count: 6).whenComplete(() => mounted ? _c.value = 0 : null);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _c,
    builder: (_, child) => Transform.scale(scale: 1 + .06 * Curves.easeOut.transform(_c.value), child: child),
    child: widget.child,
  );
}
