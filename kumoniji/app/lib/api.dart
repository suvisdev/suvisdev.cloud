import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import 'auth.dart';

/// 한 자리가 낸 패. tiles가 null이면 패스. auto: 아무도 못 이겨 서버가 한꺼번에 넘긴 패스(앱이 묶어서 한 번에 보여 줌).
class Play {
  final int seat;
  final List<String>? tiles;
  final bool auto;
  const Play(this.seat, this.tiles, {this.auto = false});
}

/// 서버가 준 판 상태(사람은 항상 0번 자리). 규칙 판정은 서버가 한다.
class GameState {
  final String id, today;

  /// 봇 난이도(easy·normal·hard)
  final String level;
  final int turn, doubles;
  final int? last, winner;
  final List<String> hand, table, playable, suits;
  final List<int> counts, petals, bonus;

  /// 마지막으로 낸 사람 뒤로 이어서 패스한 자리
  final List<int> passed;
  final List<int>? settlement;

  /// 이미 나온 패(싱글 연습만 — 멀티는 서버가 안 줘서 null)
  final List<String>? out;

  /// 판이 끝나 서버가 기록한 뒤의 지갑(끝난 판 응답에만)
  final Map<String, dynamic>? wallet;

  /// 지금 낼 수 있는 조합 전부(사람 차례일 때만, 서버가 계산)
  final List<List<String>> moves;

  /// 이번 바퀴에 자리마다 마지막으로 낸 패(안 냈으면 null)
  final List<List<String>?> plays;
  final List<Play> events;

  GameState.fromJson(Map<String, dynamic> j)
    : id = j['id'],
      today = j['today'],
      level = j['level'] ?? 'normal',
      turn = j['turn'],
      doubles = j['doubles'],
      last = j['last'],
      winner = j['winner'],
      hand = List<String>.from(j['hand']),
      table = List<String>.from(j['table']),
      playable = List<String>.from(j['playable'] ?? const []),
      moves = [for (final m in j['moves'] ?? const []) List<String>.from(m)],
      passed = List<int>.from(j['passed'] ?? const []),
      plays = [
        for (final m in j['plays'] ?? const [null, null, null, null]) m == null ? null : List<String>.from(m),
      ],
      suits = List<String>.from(j['suits'] ?? const ['m', 's', 'l', 'c']),
      counts = List<int>.from(j['counts']),
      petals = List<int>.from(j['petals']),
      bonus = List<int>.from(j['bonus']),
      settlement = j['settlement'] == null ? null : List<int>.from(j['settlement']),
      out = j['out'] == null ? null : List<String>.from(j['out']),
      wallet = j['wallet'] as Map<String, dynamic>?,
      events = [
        for (final e in j['events'])
          Play(e['seat'], e['tiles'] == null ? null : List<String>.from(e['tiles']), auto: e['auto'] == true),
      ];

  bool get finished => winner != null;

  /// 고른 패가 낼 수 있는 조합 중 하나와 정확히 같은가
  bool isLegal(Set<String> picked) => moves.any((m) => m.length == picked.length && m.every(picked.contains));
}

class ApiError implements Exception {
  final int status;

  /// 422일 때 서버가 준 이유 코드(suit·weaker·count·not_combo·not_in_hand)
  final String? code;
  const ApiError(this.status, [this.code]);
}

class Api {
  /// 웹은 같은 주소(서버가 앱을 냄), 휴대폰 앱은 운영 서버. 개발 때는 --dart-define=API=http://localhost:8300
  static const base = String.fromEnvironment('API', defaultValue: kIsWeb ? '' : 'https://kumoniji.suvisdev.cloud');
  final http.Client client;

  /// 이 화면을 연 계정 — 요청마다 x-kumoniji-account로 보낸다. 화면이 닫히는 사이 계정이 바뀌어도 이 화면의 요청은
  /// 다른 계정의 하트를 쓰지 않고 서버가 409로 거절한다(앱 리뷰 9차)
  final int? account;
  Api([http.Client? client]) : client = client ?? Auth.client, account = Auth.me.value?.id;

  Map<String, String> get _headers => {
    'content-type': 'application/json',
    if (account != null) 'x-kumoniji-account': '$account',
  };

  /// 새 판(하트 1개). 요청 id를 붙여, 응답을 못 받았거나(5xx·연결 끊김) 같은 요청이 아직 만드는 중(409)이면
  /// 같은 id로 두 번까지 다시 보낸다 — 서버가 원장으로 확인해 하트를 두 번 쓰지 않고 그 판을 돌려준다.
  /// 세 번 다 결과를 모르면 id를 남겨 두고, 다음 새 판도 그 id로 보낸다 — 새 id면 이미 낸 하트로 만든 판을 두고
  /// 하트를 또 쓴다(리뷰 1차). 그 판이 다른 난이도로 만들어졌으면 그 판을 받는다(하트는 그 판 몫).
  /// 다시 보내기 전에 계정이 바뀌었으면 그만둔다 — 서버의 rid는 계정마다라 다음 사람 하트를 쓰게 된다(리뷰 3차).
  Future<GameState> newGame([String level = 'normal']) async {
    final who = account;
    final kept = pendingNewGame[who];
    final rid = pendingNewGame[who] ??= newRid();
    // 앞선 시도(앞 호출 포함)가 결과를 모르고 끝났나 — 그 뒤의 401·429 같은 거절은 이 id의 판을 부정하지 않는다(리뷰 6·7차)
    var unknown = kept != null;
    _inFlight[rid] = (_inFlight[rid] ?? 0) + 1;
    try {
      return await _newGameWith(level, who, rid, unknown);
    } finally {
      if ((_inFlight[rid] = _inFlight[rid]! - 1) == 0) _inFlight.remove(rid);
    }
  }

  /// 새 판 응답을 받을 화면이 아직 있나 — 판 화면이 자기 mounted로 바꿔 끼운다
  bool Function() wanted = () => true;

  /// 받았지만 아직 화면에 보이지 않은 새 판의 (계정, 요청 id)
  (int?, String)? unsettled;

  /// 판 화면이 새 판을 다 보였다 — 이제 다음 새 판은 새 id로
  void settle() {
    final u = unsettled;
    unsettled = null;
    if (u != null) _forget(u.$1, u.$2);
  }

  /// 같은 id로 지금 나가 있는 새 판 요청 수 — 다른 화면이 같은 id로 기다리는 중이면 이 호출의 거절로 id를 지우지 않는다(리뷰 18차)
  static final _inFlight = <String, int>{};

  Future<GameState> _newGameWith(String level, int? who, String rid, bool unknown) async {
    for (var i = 0; ; i++) {
      if (Auth.me.value?.id != who) throw const ApiError(401); // 이 화면을 연 계정이 아니면 보내지 않는다
      // 보내기 전에 화면이 닫혔으면(닫히는 애니메이션 중 포함) 보내지 않는다 — id는 남겨 다음 진입이 이어 쓴다(리뷰 31·32차)
      if (!wanted()) throw const ApiError(0);
      try {
        // 응답이 멈추면 AuthClient.timeout이 예외로 — 결과 모름으로 쳐 같은 id로 다시(리뷰 19차).
        // 세션 갱신 뒤 AuthClient가 다시 보낼 때도 화면이 있는지 본다(리뷰 34차)
        final req = GuardedRequest('POST', _uri('/api/games'), wanted)
          ..headers.addAll(_headers)
          ..body = jsonEncode({'level': level, 'rid': rid});
        final g = await _send(client.send(req).then(http.Response.fromStream));
        // id는 여기서 지우지 않는다 — 판 화면이 나눠 주기 연출을 마치고 판을 보인 뒤 settle()로 지운다. 그 전에 닫으면
        // 남아 다음 진입이 같은 id로 그 판(하트를 이미 쓴)을 받는다(리뷰 28·34차)
        unsettled = (who, rid);
        return g;
      } on ApiError catch (e) {
        final unsure = e.status >= 500 || (e.status == 409 && e.code == null); // 409 code 없음 = 같은 요청이 만드는 중
        unknown |= unsure;
        // 다음은 새 id: 이 id로 낸 하트가 없다고 서버가 확인한 402, 판이 밀려난 410, 처음부터 거절된 경우만.
        // 결과를 모르는 시도 뒤의 401(세션 만료)·429면 남겨 둔다 — 다시 로그인해도 같은 id로 그 판을 찾게(리뷰 6차)
        final settled = e.status == 402 || e.status == 410 || !unknown;
        if (!unsure && settled && _inFlight[rid] == 1) _forget(who, rid);
        if (i >= 2 || !unsure) rethrow;
      } catch (_) {
        unknown = true;
        if (i >= 2) rethrow;
      }
      await Future.delayed(Duration(milliseconds: 500 * (i + 1)));
    }
  }

  static void _forget(int? who, String rid) {
    if (pendingNewGame[who] != rid) return; // 다른 화면이 같은 id를 이어 받았을 수도 — 내 id일 때만(리뷰 5차)
    pendingNewGame.remove(who);
  }

  /// 계정마다 결과를 모르는 새 판 요청 id — 화면을 새로 열거나 로그아웃했다 같은 계정으로 돌아와도 이어 쓴다
  static Map<int?, String> get pendingNewGame => PendingIds.newGame;
  Future<GameState> get(String id) => _send(client.get(_uri('/api/games/$id'), headers: _headers));
  Future<GameState> move(String id, List<String> tiles) =>
      _send(client.post(_uri('/api/games/$id/moves'), headers: _headers, body: jsonEncode({'tiles': tiles})));

  Uri _uri(String path) => Uri.parse('$base$path');

  Future<GameState> _send(Future<http.Response> req) async {
    final session = Auth.me.value; // 로그인마다 새 객체 — 같은 계정이라도 옛 세션의 늦은 401은 무시(리뷰 4·21차)
    final r = await req;
    // 401 → 세션을 다시 확인해 정말 끝났을 때만 로그인 화면으로 — 다른 탭이 방금 갱신해 새 쿠키가 늦게 오는 중일
    // 수 있다(리뷰 57차). 앞 계정이 보낸 요청의 늦은 401이면 지금 계정은 두고(리뷰 4차)
    if (r.statusCode == 401 && session != null && identical(Auth.me.value, session)) Auth.reloadIfStill(session);
    if (r.statusCode != 200) {
      String? code;
      try {
        final d = jsonDecode(utf8.decode(r.bodyBytes))['detail'];
        if (d is Map) code = d['code'] as String?;
      } catch (_) {}
      throw ApiError(r.statusCode, code);
    }
    return GameState.fromJson(jsonDecode(utf8.decode(r.bodyBytes)));
  }
}

/// 요청 id(서버 패턴 [A-Za-z0-9_-]{8,64})
String newRid() {
  final r = Random.secure();
  const abc = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  return List.generate(20, (_) => abc[r.nextInt(abc.length)]).join();
}

/// 결과를 모르는 요청 id(새 판·구매), 계정마다 — 이 탭·이 실행 안에서만(메모리) 같은 id로 다시 보내 두 번 쓰지 않는다.
/// ponytail: 새로고침·앱 재시작·다른 탭에는 이어지지 않는다 — 기기에 저장해 탭끼리 나눠 보려 했으나(리뷰 12~16차)
/// 브라우저 저장소엔 탭 사이의 원자적 비교·교체가 없어 경합이 끝나지 않았다. 그 경우는 받아들인다: 잔고 막대가 다시 받아
/// 보석·하트가 줄었으면 이미 처리된 것이고, 판은 서버에 남아 있다가 밀려난다. 줄이려면 서버가 '내 진행 중인 판'을 돌려주는 것.
class PendingIds {
  static final newGame = <int?, String>{};
  static final buy = <(int?, String), String>{};
}

/// 다시 보내기 전에 아직 원하는지 물을 수 있는 요청 — AuthClient가 세션 갱신 뒤 다시 보낼 때 본다
class GuardedRequest extends http.Request {
  final bool Function() wanted;
  GuardedRequest(super.method, super.url, this.wanted);
}
