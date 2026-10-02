import 'package:flutter/widgets.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// 산책 중 기기 알림 — 경로를 벗어나면 화면이 꺼져 있어도 알려 준다(2026-09-30).
/// 알림을 누르면 앱이 열리고, 산책 화면의 "새 길 찾기" 버튼으로 이어진다.
/// 꺾임·도착은 음성으로 말하고, 앱이 화면 뒤에 있을 때만 진동 알림도 띄운다(2026-10-02).
/// 권한이 없거나 초기화가 실패해도 산책 기록은 그대로 된다(알림만 없음).
class WalkAlerts {
  final _plugin = FlutterLocalNotificationsPlugin();
  final _tts = FlutterTts();
  bool _ready = false;
  bool _ttsReady = false;

  /// 음성 끄기 — 진동 알림은 그대로 둔다.
  bool muted = false;

  static const _offRouteId = 1;
  static const _cueId = 2;
  static const _cueDetails = NotificationDetails(
    android: AndroidNotificationDetails(
      'walk_turn',
      '길 안내 알림',
      channelDescription: '산책 중 꺾을 곳과 도착을 알려 줍니다',
      importance: Importance.high,
      priority: Priority.high,
      timeoutAfter: 15000,
    ),
  );
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
    if (!_ttsReady) {
      try {
        await _tts.setLanguage('ko-KR');
        await _tts.setSpeechRate(0.5);
        _ttsReady = true;
      } catch (e) {
        debugPrint('음성 안내 초기화 건너뜀: $e');
      }
    }
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

  /// 길 안내 한마디 — 말하고, 화면을 안 보고 있으면 진동 알림도 띄운다.
  Future<void> cue(String text) async {
    if (_ttsReady && !muted) {
      try {
        await _tts.speak(text);
      } catch (e) {
        debugPrint('음성 안내 실패: $e');
      }
    }
    if (!_ready || WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed) return;
    try {
      await _plugin.show(id: _cueId, title: '길 안내', body: text, notificationDetails: _cueDetails);
    } catch (e) {
      debugPrint('길 안내 알림 실패: $e');
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
