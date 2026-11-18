import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kumoniji/api.dart';

Map<String, dynamic> view({List<Map<String, dynamic>> events = const []}) => {
  'id': 'a',
  'today': 's',
  'turn': 0,
  'hand': ['m1', 's3'],
  'counts': [2, 13, 13, 13],
  'table': <String>[],
  'last': null,
  'petals': [0, 0, 0, 0],
  'bonus': [0, 0, 0, 0],
  'doubles': 0,
  'winner': null,
  'settlement': null,
  'events': events,
  'playable': ['m1', 's3'],
  'moves': [
    ['m1'],
    ['s3'],
  ],
  'suits': ['m', 's', 'l', 'c'],
  'plays': [null, null, null, null],
  'passed': <int>[],
};

void main() {
  test('GameState parses server view', () {
    final s = GameState.fromJson(
      view(
        events: [
          {'seat': 1, 'tiles': null},
          {
            'seat': 2,
            'tiles': ['c4'],
          },
        ],
      ),
    );
    expect(s.hand, ['m1', 's3']);
    expect(s.events.first.tiles, isNull);
    expect(s.events.last.tiles, ['c4']);
    expect(s.finished, isFalse);
  });

  test('move posts tiles and maps 422 to ApiError', () async {
    late Map<String, dynamic> sent;
    final ok = Api(
      MockClient((r) async {
        sent = jsonDecode(r.body);
        expect(r.url.path, '/api/games/a/moves');
        return http.Response(jsonEncode(view()), 200);
      }),
    );
    await ok.move('a', ['s3']);
    expect(sent, {
      'tiles': ['s3'],
    });

    final bad = Api(MockClient((r) async => http.Response('{}', 422)));
    expect(() => bad.move('a', ['s3']), throwsA(isA<ApiError>().having((e) => e.status, 'status', 422)));
  });
}
