import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import 'auth.dart';

/// 한 자리가 낸 패. tiles가 null이면 패스.
class Play {
  final int seat;
  final List<String>? tiles;
  const Play(this.seat, this.tiles);
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
      events = [
        for (final e in j['events']) Play(e['seat'], e['tiles'] == null ? null : List<String>.from(e['tiles'])),
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
  Api([http.Client? client]) : client = client ?? Auth.client;

  Future<GameState> newGame([String level = 'normal']) => _send(
    client.post(_uri('/api/games'), headers: {'content-type': 'application/json'}, body: jsonEncode({'level': level})),
  );
  Future<GameState> get(String id) => _send(client.get(_uri('/api/games/$id')));
  Future<GameState> move(String id, List<String> tiles) => _send(
    client.post(
      _uri('/api/games/$id/moves'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({'tiles': tiles}),
    ),
  );

  Uri _uri(String path) => Uri.parse('$base$path');

  Future<GameState> _send(Future<http.Response> req) async {
    final r = await req;
    if (r.statusCode == 401) Auth.me.value = null; // 세션이 끝남(리프레시도 실패) → 로그인 화면으로
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
