import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gildle/core/network/dio_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// 모든 요청에 401(access token 만료)을 돌려주는 가짜 어댑터.
class _Always401 implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async =>
      ResponseBody.fromString('', 401);

  @override
  void close({bool force = false}) {}
}

const _session = {'suvis_mobile_access_token': 'old', 'suvis_mobile_refresh_token': 'r1'};

/// refresh(POST /auth/mobile/refresh)를 [refresh]로 흉내 내고 API 401을 받았을 때 만료 콜백이 불렸는지.
Future<bool> _expiredAfter401(MockClient refresh) async {
  FlutterSecureStorage.setMockInitialValues(Map.of(_session));
  var expired = false;
  final dio = createDio(onSessionExpired: () => expired = true)..httpClientAdapter = _Always401();
  await http.runWithClient(() async {
    await expectLater(dio.get('/api/gildle/walks'), throwsA(isA<DioException>()));
  }, () => refresh);
  return expired;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('refresh가 401이면 세션이 지워지고 로그인 상태를 내리라고 알린다', () async {
    expect(await _expiredAfter401(MockClient((_) async => http.Response('', 401))), isTrue);
  });

  test('refresh가 네트워크 오류면 세션을 남기고 로그아웃시키지 않는다', () async {
    final expired = await _expiredAfter401(MockClient((_) async => throw http.ClientException('offline')));
    expect(expired, isFalse);
  });
}
