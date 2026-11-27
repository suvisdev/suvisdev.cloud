import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';

import 'api.dart';
import 'auth.dart';
import 'l10n/app_localizations.dart';

/// 서버 지갑 응답(/api/wallet). 숫자 규칙은 서버(wallet/money.py)가 정한다.
class WalletState {
  WalletState(this.j) : got = DateTime.now().millisecondsSinceEpoch;
  final Map<String, dynamic> j;

  /// 받은 순간의 기기 시각(밀리초)
  final int got;

  /// 서버 시각 − 기기 시각(밀리초). 하루·하트 시각은 서버 시계로 정해지니 예약도 서버 시각으로(리뷰 8차)
  int get skew => t == 0 ? 0 : (t * 1000).round() - got;

  /// 서버의 실제 시각(초) — 충전·자정·날짜 계산용. v는 응답 순서용 번호라 따로(리뷰 26차)
  double get t => (j['now'] as num?)?.toDouble() ?? 0;

  /// 서버가 지갑 행을 잠근 채 DB 시퀀스에서 받은 순서 번호 — 같은 계정이면 나중에 처리된 것이 크다(시계와 무관)
  double get v => (j['v'] as num?)?.toDouble() ?? 0;
  int get coins => j['coins'] as int;
  int get gems => j['gems'] as int;
  int get hearts => j['hearts'] as int;

  /// 다음 하트가 차는 시각(초, 꽉 찼으면 null)
  double? get nextHeart => (j['next_heart'] as num?)?.toDouble();
  bool get attended => (j['attend'] as Map)['claimed'] as bool;

  /// 지금 출석하면 7의 배수 날(판돈 500 + 보석 10)
  bool get seventhNext => ((j['attend'] as Map)['next'] as int? ?? 1) % 7 == 0;

  /// 스냅숏의 하루(서버 KST)가 그 스냅숏을 찍은 시각(v)의 하루보다 이르면 — 자정 직전 요청이 잠금을 기다리다 자정을
  /// 넘긴 것. 새날 상태를 곧 다시 받아야 한다(리뷰 9·11차)
  bool get staleDay => t != 0 && (j['attend'] as Map)['day'] != kstDay((t * 1000).round());
  int get streak => (j['attend'] as Map)['streak'] as int;
  List<String> get all => List<String>.from((j['missions'] as Map)['all'] as List);
  List<String> get done => List<String>.from((j['missions'] as Map)['done'] as List);
  Map<String, int> get counts => Map<String, int>.from((j['missions'] as Map)['counts'] as Map);
}

/// 미션마다 세는 값과 목표 — 서버 wallet/missions.py NEED와 같게(완료 판정은 서버가 한다, 여기는 진행 표시만).
const missionNeed = {
  'games5': ('games', 5),
  'games10': ('games', 10),
  'wins2': ('wins', 2),
  'low3': ('low3', 1),
  'five3': ('five', 3),
  'triple2': ('triple', 2),
  'today': ('today', 1),
  'score30': ('score', 30),
  'oddeven': ('oddeven', 1),
  'fullhouse': ('fullhouse', 1),
};

/// 상점 상품: (id, 보석 값) — 서버 money.SHOP과 같게
/// 상점 상품(서버 money.SHOP과 같아야 함): (id, 무지개 조각 값, 얻는 것, 양). 많이 살수록 덤(11-27 사용자)
const shopItems = [
  ('coins1000', 10, 'coins', 1000),
  ('coins5500', 50, 'coins', 5500),
  ('coins12000', 100, 'coins', 12000),
  ('coins40000', 300, 'coins', 40000),
  ('hearts5', 10, 'hearts', 5),
  ('hearts15', 25, 'hearts', 15),
];

/// 무지개 조각 묶음(원, 개수) — 화면만, 결제는 게임위 문의 뒤(11-27 사용자). 기준 100원에 1개, 큰 묶음일수록 덤
const gemPacks = [(1200, 12), (5900, 62), (12000, 132), (33000, 380), (59000, 708), (119000, 1488)];

/// 상점 탭 순서
const shopTabs = ['gems', 'coins', 'hearts'];

String thousands(int n) => n.toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');

/// 재화 그림(골드·햇살·무지개 조각 — Codex 시안 B, 11-27 사용자)
Widget currencyIcon(String kind, double size, {bool empty = false}) => Image.asset(
  'assets/currency/${switch (kind) {
    'coins' => 'gold',
    'hearts' => empty ? 'sun_empty' : 'sun',
    _ => 'gem',
  }}.png',
  width: size,
  height: size,
  filterQuality: FilterQuality.medium,
);

/// 잔고 숫자 — 통통한 입체 숫자 그림(시안 B). 0-9·콤마·더하기만
class Digits extends StatelessWidget {
  const Digits(this.text, {super.key, this.height = 18});
  final String text;
  final double height;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      for (final c in text.split(''))
        Image.asset(
          'assets/currency/digits/${c == ',' ? 'comma' : (c == '+' ? 'plus' : c)}.png',
          height: height,
          filterQuality: FilterQuality.medium,
        ),
    ],
  );
}

class Wallet {
  /// 지금 로그인한 계정의 지갑. 계정이 바뀌거나 로그아웃하면 비운다 — 앞 사람 잔고가 남지 않게(리뷰 1차)
  static final current = _watchAccount(ValueNotifier<WalletState?>(null));
  static int? _owner;

  static ValueNotifier<WalletState?> _watchAccount(ValueNotifier<WalletState?> v) {
    Auth.me.addListener(() {
      if (Auth.me.value?.id != _owner) {
        v.value = null;
        _owner = null; // 결과를 모르는 구매 id(buyRids)는 계정별이라 남긴다 — 다시 로그인해 그 구매를 확인하게(리뷰 7차)
      }
    });
    return v;
  }

  /// owner: 요청을 보낼 때의 계정 — 그사이 계정이 바뀌었으면 버린다(앞 사람 잔고가 다음 사람에게, 리뷰 3차).
  /// 서버 시각(v)이 지금 것보다 옛 응답도 버린다 — 응답이 도착한 순서로는 서버가 처리한 순서를 알 수 없다(리뷰 2~4차).
  /// 반영했으면 true — 다른 계정 것이거나 이미 보인 것보다 옛 스냅숏(v는 서버 DB 시퀀스, 처리 순서)이면 버리고 false
  static bool set(Map<String, dynamic> j, {required int? owner}) {
    if (owner != Auth.me.value?.id) return false;
    final next = WalletState(j);
    final now = current.value;
    if (now != null && next.v < now.v) return false;
    _owner = owner;
    current.value = next;
    return true;
  }

  /// (계정, 상품)마다 결과를 모르는 구매 id — 상점을 닫거나 로그아웃했다 돌아와도 같은 id로 다시 보내 두 번 사지 않게(리뷰 1·7차)
  static Map<(int?, String), String> get buyRids => PendingIds.buy;
  static bool pendingBuy(String item) => buyRids.containsKey((Auth.me.value?.id, item));

  /// 성공하면 null, 실패하면 HTTP 상태(네트워크 오류는 0)와 서버 코드. 401은 로그인 화면으로.
  /// account: 이 요청을 시작한 계정(구매) — 없으면 지금 계정. 그 번호를 보내 서버가 다른 계정이면 409로 거절한다
  static Future<(int, String?)?> _call(String path, [Map<String, dynamic>? body, int? account]) async {
    final who = account ?? Auth.me.value?.id;
    final session = Auth.me.value; // 같은 계정으로 다시 로그인해도 로그인마다 새 객체 — 옛 세션의 늦은 401로 새 로그인을 끊지 않게(리뷰 21차)
    final headers = {'content-type': 'application/json', if (who != null) 'x-kumoniji-account': '$who'};
    try {
      final uri = Uri.parse('${Api.base}$path');
      final r = body == null
          ? await Auth.client.get(uri, headers: headers)
          : await Auth.client.post(uri, headers: headers, body: jsonEncode(body));
      if (r.statusCode == 200) {
        final j = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
        final applied = set(j, owner: who);
        // 접속만으로 오늘 출석됨 — 잔고 막대가 알린다. 스냅숏 반영과 따로: 연달아 조회해 뒤 응답이 먼저 오면 이 응답은
        // 옛 스냅숏이라 버려져도 출석은 이 응답이 했다(리뷰 2차). 지금 계정의 응답일 때만
        if (j['attended_now'] == true && who == Auth.me.value?.id) attendedNow.value++;
        // 조회가 옛 스냅숏이라 버려짐(서버 재시작과 시계 되감기가 겹침 등) — 실패(0)로 알려 잔고 막대가 30초 뒤 다시(리뷰 25차)
        if (!applied && body == null && who == Auth.me.value?.id) return (0, 'stale');
        return null;
      }
      // 401: 앞 계정 요청의 늦은 401은 무시(리뷰 4차). 곧바로 로그아웃하지 않고 세션을 다시 확인 — 다른 탭이 방금
      // 갱신해 새 쿠키가 늦게 오는 중일 수 있다(리뷰 55차)
      if (r.statusCode == 401 && session != null && identical(Auth.me.value, session)) Auth.reloadIfStill(session);
      String? code;
      try {
        final d = jsonDecode(utf8.decode(r.bodyBytes))['detail'];
        if (d is Map) code = d['code'] as String?;
      } catch (_) {}
      return (r.statusCode, code);
    } catch (_) {
      return (0, null);
    }
  }

  /// 성공하면 null, 아니면 (상태, 코드) — 상태 0은 연결 실패
  static Future<(int, String?)?> refresh() => _call('/api/wallet');

  /// 잔고를 읽다 서버가 오늘 출석을 처리함(접속만 해도 출석, 11-27 사용자)
  static final attendedNow = ValueNotifier<int>(0);

  /// 막대 밖(판 화면 등)에서 받다 실패했을 때 — 홈의 잔고 막대가 다시 시도하게 알린다(리뷰 12차)
  static final retry = ValueNotifier<int>(0);

  /// 끝난 판의 기록을 서버가 뒤에서 다시 시도 중(api.py RECORD_RETRY 2·10·60초 간격 = 2·12·72·132…초 뒤) —
  /// 잔고 막대가 각 시도 조금 뒤에 다시 받는다(리뷰 19·20차). 타이머는 막대가 맡아 화면이 닫히면 함께 취소된다.
  /// ponytail: 4번째 서버 시도(132초)까지만 따라간다 — 그 뒤 성공은 다음 하트·자정·화면 재진입 때 보인다
  static final recheck = ValueNotifier<int>(0);
  static Future<void> refreshOrRetry() async {
    final err = await refresh();
    // 401도 — 세션 재확인 결과 살아 있으면 잔고 막대가 다시 받아야 한다(리뷰 64차)
    if (err != null && (err.$1 == 0 || err.$1 == 401 || err.$1 >= 500)) retry.value++;
  }

  /// account: 화면을 연 계정 — 지금 계정이 다르면(비었거나 바뀜) 보내지 않는다. 보낼 땐 그 번호를 붙여 서버가 다른
  /// 세션이면 409로 거절한다(리뷰 18차)
  static Future<(int, String?)?> attend({required int? account}) async =>
      Auth.me.value?.id != account ? (401, null) : _call('/api/wallet/attend', {}, account);

  /// 상품마다 결과를 모르는 구매 id를 이어 써서, 응답이 끊겨 다시 눌러도 한 번만 산다(서버 원장).
  static final _buying = <String, int>{}; // 구매 id마다 응답을 기다리는 호출 수
  static final _bought = <String>{}; // 겹친 호출 중 하나가 성공한 구매 id

  static Future<(int, String?)?> buy(String item, {required int? account}) async {
    if (Auth.me.value?.id != account) return (401, null);
    final key = (account, item);
    final rid = buyRids[key] ??= newRid();
    _buying[rid] = (_buying[rid] ?? 0) + 1;
    final (int, String?)? err;
    try {
      err = await _call('/api/wallet/buy', {'item': item, 'rid': rid}, key.$1);
    } finally {
      _buying[rid] = _buying[rid]! - 1;
    }
    // 같은 id는 같은 구매다 — 겹친 호출(상점을 닫았다 열어 다시 누름) 중 하나라도 성공했으면 서버가 처리한 것이라 모두
    // 성공으로 알린다. 끝났거나 보석 부족(확정 거절)이면 다음 구매는 새 id — 지우는 건 마지막 호출이 끝날 때(다른 쪽 응답이
    // 아직 오는 중일 수 있으니), 그사이 다른 구매가 새 id를 받았으면 그건 둔다(리뷰 5·42·43차)
    if (err == null) _bought.add(rid);
    final ok = _bought.contains(rid);
    if (_buying[rid] == 0) {
      _buying.remove(rid);
      _bought.remove(rid);
      if ((ok || (err!.$1 == 409 && err.$2 == 'gems')) && buyRids[key] == rid) buyRids.remove(key);
    }
    return ok ? null : err;
  }
}

/// 한국 날짜 'YYYY-MM-DD' — 서버 missions.day_of와 같게
String kstDay(int ms) =>
    DateTime.fromMillisecondsSinceEpoch(ms + 9 * 3600000, isUtc: true).toIso8601String().substring(0, 10);

/// 다음 한국 자정(밀리초) — 서버의 하루(wallet/missions.py KST)와 같게
int nextKstMidnight(int nowMs) {
  const day = 86400000, kst = 9 * 3600000;
  return ((nowMs + kst) ~/ day + 1) * day - kst;
}

/// 다음 하트까지 남은 분(올림, 꽉 찼으면 null)
int? minutesToHeart(WalletState? w) {
  final at = w?.nextHeart;
  if (at == null) return null;
  final left = at - (DateTime.now().millisecondsSinceEpoch + w!.skew) / 1000;
  return max(1, (left / 60).ceil());
}

String missionName(AppLocalizations t, String id) => switch (id) {
  'games5' => t.missionGames5,
  'games10' => t.missionGames10,
  'wins2' => t.missionWins2,
  'low3' => t.missionLow3,
  'five3' => t.missionFive3,
  'triple2' => t.missionTriple2,
  'today' => t.missionToday,
  'score30' => t.missionScore30,
  'oddeven' => t.missionOddEven,
  'fullhouse' => t.missionFullHouse,
  _ => id,
};

/// 잔고 막대: 판돈·하트·보석. 처음 그릴 때 서버에서 받아 오고, 다음 하트가 차는 시각과 한국 자정(출석·미션이
/// 새날로 바뀜)에 다시 받는다(리뷰 1·2차).
class WalletBar extends StatefulWidget {
  /// [onPick]: 재화를 누르면 — 기본은 그 탭으로 상점 열기, 상점 안에서는 탭만 바꾼다
  const WalletBar({super.key, this.onPick});
  final void Function(String kind)? onPick;

  @override
  State<WalletBar> createState() => _WalletBarState();
}

class _WalletBarState extends State<WalletBar> {
  Timer? _heart;
  bool _soon = false; // 곧바로 다시 받기를 잡아 둠(아직 안 받음)
  bool _staleTried = false; // 날이 어긋난 스냅숏에 곧바로 다시 받기를 이미 한 번 했나 — 서버 시계가 뒤로 보정돼
  // 계속 어긋나면 1초마다 받지 않고 보통 일정으로(리뷰 24차)
  final _rechecks = <Timer>[];

  void _recheck() {
    for (final sec in const [4, 14, 75, 135]) {
      _rechecks.add(Timer(Duration(seconds: sec), _fetch));
    }
  }

  @override
  void initState() {
    super.initState();
    Wallet.current.addListener(_schedule);
    Wallet.retry.addListener(_fetch);
    Wallet.recheck.addListener(_recheck);
    Wallet.attendedNow.addListener(_attended);
    _schedule();
    _fetch();
  }

  void _schedule() {
    // 자정을 넘긴 스냅숏 때문에 곧바로 다시 받기를 잡아 뒀으면, 그 뒤 도착한 스냅숏이 그것을 지우지 않는다(리뷰 44차)
    if (_soon && (_heart?.isActive ?? false)) return;
    _heart?.cancel();
    if (Wallet.current.value == null) return;
    final w = Wallet.current.value!;
    final now = DateTime.now().millisecondsSinceEpoch + w.skew; // 서버 시각
    final at = w.nextHeart;
    final soon = w.staleDay && !_staleTried;
    _staleTried = w.staleDay;
    _soon = soon;
    final ms = soon ? 0 : min(at == null ? nextKstMidnight(now) : (at * 1000).round(), nextKstMidnight(now)) - now;
    _heart = Timer(Duration(milliseconds: max(ms + 1000, 1000)), _fetch); // 서버 시각과 조금 어긋나도 지난 뒤에
  }

  static int _shownAttend = 0;

  void _attended() {
    final w = Wallet.current.value;
    // 출석 한 건에 알림 하나 — 먼저 받은 막대만 띄운다. 알림 창(ScaffoldMessenger)은 앱 전체가 함께 써서 어느 화면의
    // 막대가 띄워도 지금 보이는 화면에 나온다. 맨 위 막대만 띄우면 대화창이 열린 사이 온 출석은 알림이 사라졌다(리뷰 8·10차)
    if (!mounted || w == null || _shownAttend == Wallet.attendedNow.value) return;
    _shownAttend = Wallet.attendedNow.value;
    ScaffoldMessenger.maybeOf(context)
        ?.showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.attended(w.streak))));
  }

  /// 조회가 연결 끊김·5xx로 실패하면 30초 뒤 다시 — 첫 조회도(미션·상점이 빈 채 멈추지 않게, 리뷰 3·4차).
  /// 401도 — 세션 재확인 결과 살아 있으면(다른 탭 갱신 쿠키가 늦게 옴) 다시 받아야 하고, 정말 끝났으면 로그인 화면으로
  /// 가며 이 막대가 사라져 타이머도 꺼진다(리뷰 59차). 그 밖의 4xx는 다시 해도 같아 그만둔다.
  Future<void> _fetch() async {
    _soon = false;
    final err = await Wallet.refresh();
    if (err != null && (err.$1 == 0 || err.$1 == 401 || err.$1 >= 500) && mounted) {
      _heart?.cancel();
      _heart = Timer(const Duration(seconds: 30), _fetch);
    }
  }

  @override
  void dispose() {
    _heart?.cancel();
    for (final t in _rechecks) {
      t.cancel();
    }
    Wallet.current.removeListener(_schedule);
    Wallet.retry.removeListener(_fetch);
    Wallet.attendedNow.removeListener(_attended);
    Wallet.recheck.removeListener(_recheck);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    void pick(String kind) => widget.onPick != null
        ? widget.onPick!(kind)
        : Navigator.push(context, MaterialPageRoute(builder: (_) => ShopScreen(tab: kind)));
    Widget item(String kind, String label, int n, Widget body) => Semantics(
      label: '$label $n',
      button: true,
      excludeSemantics: true,
      onTap: () => pick(kind),
      child: InkWell(
        key: ValueKey('wallet-$kind'),
        borderRadius: BorderRadius.circular(12),
        onTap: () => pick(kind),
        child: Padding(padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2), child: body),
      ),
    );
    return ValueListenableBuilder(
      valueListenable: Wallet.current,
      builder: (_, w, _) => w == null
          ? const SizedBox.shrink()
          : FittedBox(
              fit: BoxFit.scaleDown,
              child: Row(
                key: const ValueKey('wallet-bar'),
                mainAxisSize: MainAxisSize.min,
                children: [
                  // 골드 · 햇살(서버 이름 hearts) · 무지개 조각(gems) — 11-27 사용자가 이름을 정함, 서버 키는 그대로
                  item(
                    'coins',
                    t.coins,
                    w.coins,
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [currencyIcon('coins', 20), const SizedBox(width: 3), Digits(thousands(w.coins))],
                    ),
                  ),
                  const SizedBox(width: 8),
                  // 햇살은 보통 게임처럼 5칸 — 가진 만큼 채우고 넘친 몫은 +N(11-27 사용자)
                  item(
                    'hearts',
                    t.hearts,
                    w.hearts,
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        for (var i = 0; i < 5; i++) currencyIcon('hearts', 18, empty: i >= w.hearts),
                        if (w.hearts > 5) ...[const SizedBox(width: 2), Digits('+${w.hearts - 5}')],
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  item(
                    'gems',
                    t.gems,
                    w.gems,
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [currencyIcon('gems', 20), const SizedBox(width: 3), Digits(thousands(w.gems))],
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

void _toast(BuildContext context, String msg) => ScaffoldMessenger.of(context)
  ..hideCurrentSnackBar()
  ..showSnackBar(SnackBar(content: Text(msg)));

/// 출석 + 일일 미션 10개(5개 완료하면 보너스)
class MissionsScreen extends StatefulWidget {
  const MissionsScreen({super.key});

  @override
  State<MissionsScreen> createState() => _MissionsScreenState();
}

class _MissionsScreenState extends State<MissionsScreen> {
  late final int? account; // 화면을 연 계정 — 출석은 이 계정으로만

  @override
  void initState() {
    super.initState();
    account = Auth.me.value?.id;
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(t.missions), actions: const [WalletBar(), SizedBox(width: 12)]),
      body: ValueListenableBuilder(
        valueListenable: Wallet.current,
        builder: (context, w, _) {
          if (w == null) return const Center(child: CircularProgressIndicator());
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              FilledButton.icon(
                key: const ValueKey('attend'),
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                onPressed: w.attended
                    ? null
                    : () async {
                        final err = await Wallet.attend(account: account);
                        // 이미 받음(409)·결과 모름(0·5xx) — 미션 화면을 닫았어도 잔고를 다시, 실패하면 잔고 막대가 30초 뒤
                        // (리뷰 27·34·36차)
                        if (err != null && (err.$1 == 409 || err.$1 == 0 || err.$1 >= 500)) Wallet.refreshOrRetry();
                        if (err != null && err.$1 != 409 && context.mounted) _toast(context, t.serverError);
                      },
                icon: const Icon(Icons.event_available),
                label: Text(w.attended ? t.attended(w.streak) : (w.seventhNext ? t.attend7 : t.attend)),
              ),
              const SizedBox(height: 16),
              Text(t.missionsDone(w.done.length), style: const TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              for (final id in w.all)
                ListTile(
                  key: ValueKey('mission-$id'),
                  dense: true,
                  leading: Icon(
                    w.done.contains(id) ? Icons.check_circle : Icons.radio_button_unchecked,
                    color: w.done.contains(id) ? Colors.green : null,
                  ),
                  title: Text(missionName(t, id)),
                  trailing: missionNeed[id] == null
                      ? null
                      : Text('${min(w.counts[missionNeed[id]!.$1] ?? 0, missionNeed[id]!.$2)}/${missionNeed[id]!.$2}'),
                ),
            ],
          );
        },
      ),
    );
  }
}

/// 상점: 무지개 조각(현금 — 결제는 준비 중) · 골드 · 햇살 탭. 골드·햇살은 무지개 조각으로 산다
class ShopScreen extends StatefulWidget {
  const ShopScreen({super.key, this.tab = 'coins'});

  /// 처음 열 탭(gems·coins·hearts) — 잔고 막대에서 누른 재화
  final String tab;

  @override
  State<ShopScreen> createState() => _ShopScreenState();
}

class _ShopScreenState extends State<ShopScreen> with SingleTickerProviderStateMixin {
  bool busy = false;
  late final int? account; // 화면을 연 계정 — 구매는 이 계정으로만(리뷰 18차)
  late final TabController tabs;

  @override
  void initState() {
    super.initState();
    account = Auth.me.value?.id;
    tabs = TabController(length: shopTabs.length, vsync: this, initialIndex: max(shopTabs.indexOf(widget.tab), 0));
  }

  @override
  void dispose() {
    tabs.dispose();
    super.dispose();
  }

  Future<void> _buy(String item) async {
    final t = AppLocalizations.of(context)!;
    setState(() => busy = true);
    final err = await Wallet.buy(item, account: account);
    // 보석 부족·결과 모름(응답 유실·시간 초과) — 상점을 닫았어도 잔고는 다시, 실패하면 잔고 막대가 30초 뒤(리뷰 29·32·33차)
    if (err != null && (err.$2 == 'gems' || err.$1 == 0 || err.$1 >= 500)) Wallet.refreshOrRetry();
    if (!mounted) return;
    setState(() => busy = false);
    if (err == null) {
      _toast(context, t.bought);
    } else {
      _toast(context, err.$2 == 'gems' ? t.notEnoughGems : t.serverError);
    }
  }

  /// 덤 비율(%) — 가장 작은 묶음의 개당 값 대비
  static int _bonus(int amount, int price, int baseAmount, int basePrice) =>
      (amount * basePrice * 100 / (price * baseAmount) - 100).round();

  Widget _pack({required Key key, required String kind, required int amount, required int bonus, required Widget buy}) {
    final t = AppLocalizations.of(context)!;
    return Card(
      child: ListTile(
        key: key,
        leading: currencyIcon(kind, 36),
        title: Text(
          '${switch (kind) {
            'coins' => t.coins,
            'hearts' => t.hearts,
            _ => t.gems,
          }} ${thousands(amount)}',
        ),
        subtitle: bonus > 0 ? Text(t.shopBonus(bonus)) : null,
        trailing: buy,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(
        title: Text(t.shop),
        actions: [
          WalletBar(onPick: (k) => tabs.animateTo(max(shopTabs.indexOf(k), 0))),
          const SizedBox(width: 12),
        ],
        bottom: TabBar(
          controller: tabs,
          tabs: [
            for (final k in shopTabs)
              Tab(
                key: ValueKey('shop-tab-$k'),
                icon: currencyIcon(k, 22),
                text: switch (k) {
                  'coins' => t.coins,
                  'hearts' => t.hearts,
                  _ => t.gems,
                },
              ),
          ],
        ),
      ),
      body: ValueListenableBuilder(
        valueListenable: Wallet.current,
        builder: (context, w, _) => TabBarView(
          controller: tabs,
          children: [
            ListView(
              padding: const EdgeInsets.all(16),
              children: [
                for (final (won, n) in gemPacks)
                  _pack(
                    key: ValueKey('gem-pack-$n'),
                    kind: 'gems',
                    amount: n,
                    bonus: _bonus(n, won, gemPacks.first.$2, gemPacks.first.$1),
                    // 결제는 게임위 문의 뒤에 붙인다 — 지금은 값만 보이고 누를 수 없다
                    buy: OutlinedButton(onPressed: null, child: Text('₩${thousands(won)}')),
                  ),
                const SizedBox(height: 8),
                Text(t.shopSoon, style: const TextStyle(fontSize: 12)),
              ],
            ),
            for (final kind in ['coins', 'hearts'])
              ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final (id, price, k, amount) in shopItems.where((e) => e.$3 == kind))
                    _pack(
                      key: ValueKey('pack-$id'),
                      kind: k,
                      amount: amount,
                      bonus: _bonus(
                        amount,
                        price,
                        shopItems.firstWhere((e) => e.$3 == kind).$4,
                        shopItems.firstWhere((e) => e.$3 == kind).$2,
                      ),
                      buy: FilledButton.icon(
                        key: ValueKey('buy-$id'),
                        // 결과를 모르는 구매는 보석이 줄었어도 다시 보내 확인한다 — 이미 처리됐으면 서버가 그대로 성공(리뷰 2차)
                        onPressed: busy || w == null || (w.gems < price && !Wallet.pendingBuy(id))
                            ? null
                            : () => _buy(id),
                        icon: currencyIcon('gems', 16),
                        label: Text('$price'),
                      ),
                    ),
                  const SizedBox(height: 8),
                  Text(t.shopNote, style: const TextStyle(fontSize: 12)),
                ],
              ),
          ],
        ),
      ),
    );
  }
}
