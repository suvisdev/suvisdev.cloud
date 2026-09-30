import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 산책 중 기기 알림 — 경로를 벗어나면 화면이 꺼져 있어도 알려 준다(2026-09-30).
/// 알림을 누르면 앱이 열리고, 산책 화면의 "새 길 찾기" 버튼으로 이어진다.
/// 권한이 없거나 초기화가 실패해도 산책 기록은 그대로 된다(알림만 없음).
class WalkAlerts {
  final _plugin = FlutterLocalNotificationsPlugin();
  bool _ready = false;

  static const _offRouteId = 1;
  static const _details = NotificationDetails(
    android: AndroidNotificationDetails(
      'walk_off_route',
      '경로 이탈 알림',
      channelDescription: '산책 중 경로를 벗어나면 알려 줍니다',
      importance: Importance.high,
      priority: Priority.high,
    ),
  );

  Future<void> init() async {
    if (_ready) return;
    try {
      await _plugin.initialize(
        settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
      );
      await _plugin
          .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
      _ready = true;
    } catch (e) {
      debugPrint('산책 알림 초기화 건너뜀: $e');
    }
  }

  Future<void> offRoute(double offM) async {
    if (!_ready) return;
    try {
      await _plugin.show(
        id: _offRouteId,
        title: '경로를 벗어났어요',
        body: '경로에서 ${offM.round()}m 떨어졌어요. 눌러서 여기서부터 새 길을 추천받으세요.',
        notificationDetails: _details,
      );
    } catch (e) {
      debugPrint('이탈 알림 실패: $e');
    }
  }

  Future<void> clear() async {
    if (!_ready) return;
    try {
      await _plugin.cancel(id: _offRouteId);
    } catch (_) {}
  }
}

final walkAlertsProvider = Provider<WalkAlerts>((ref) => WalkAlerts());
