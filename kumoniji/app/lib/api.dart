import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

/// 한 자리가 낸 패. tiles가 null이면 패스.
class Play {
  final int seat;
  final List<String>? tiles;
  const Play(this.seat, this.tiles);
}

/// 서버가 준 판 상태(사람은 항상 0번 자리). 규칙 판정은 서버가 한다.
class GameState {
  final String id, today;
  final int turn, doubles;
  final int? last, winner;
  final List<String> hand, table;
  final List<int> counts, petals, bonus;
  final List<int>? settlement;
  final List<Play> events;

  GameState.fromJson(Map<String, dynamic> j)
    : id = j['id'],
      today = j['today'],
      turn = j['turn'],
      doubles = j['doubles'],
      last = j['last'],
      winner = j['winner'],
      hand = List<String>.from(j['hand']),
      table = List<String>.from(j['table']),
      counts = List<int>.from(j['counts']),
      petals = List<int>.from(j['petals']),
      bonus = List<int>.from(j['bonus']),
      settlement = j['settlement'] == null ? null : List<int>.from(j['settlement']),
      events = [
        for (final e in j['events']) Play(e['seat'], e['tiles'] == null ? null : List<String>.from(e['tiles'])),
      ];

  bool get finished => winner != null;
}

class ApiError implements Exception {
  final int status;
  const ApiError(this.status);
}

class Api {
  /// 웹은 같은 주소(서버가 앱을 냄), 휴대폰 앱은 운영 서버. 개발 때는 --dart-define=API=http://localhost:8300
  static const base = String.fromEnvironment('API', defaultValue: kIsWeb ? '' : 'https://kumoniji.suvisdev.cloud');
  final http.Client client;
  Api([http.Client? client]) : client = client ?? http.Client();

  Future<GameState> newGame() => _send(client.post(_uri('/api/games')));
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
    if (r.statusCode != 200) throw ApiError(r.statusCode);
    return GameState.fromJson(jsonDecode(utf8.decode(r.bodyBytes)));
  }
}
