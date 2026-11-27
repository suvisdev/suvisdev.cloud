import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import 'settings.dart';

/// 효과음(11-27 사용자: 시안 B로 전부). 파일은 assets/audio/sfx/<이름>.wav — 바꾸려면 파일만 바꾼다.
/// 소리마다 재생기 하나 — 같은 소리를 다시 내면 처음부터. 실패해도(웹의 첫 터치 전 등) 게임은 그대로라 조용히 넘긴다.
enum Sfx {
  select, // 패 고르기
  play, // 패 내기(나·봇)
  pass, // 패스
  sweep, // 셋이 패스해 바닥을 가져감
  win,
  lose;

  static final _players = <Sfx, AudioPlayer>{};
  static AppLifecycleListener? _life;
  static var _visible = true; // 앱이 보이는 중 — 뒤로 가면(홈 버튼) 봇 장면이 이어져도 소리는 내지 않는다(리뷰 4차)

  static double get _volume => _visible ? Settings.sfxVolume : 0; // 음소거·숨김이면 0

  /// 테스트: 실제 재생기 대신 이름만 쌓는다(플러그인이 없다)
  @visibleForTesting
  static List<Sfx>? log;

  void call() {
    if (Settings.sfxVolume <= 0) return;
    if (log != null) {
      log!.add(this);
      return;
    }
    _watch();
    if (_volume <= 0) return;
    final p = _players.putIfAbsent(this, () => _make(this));
    // 같은 소리를 다시 내면 처음부터 — 안드로이드는 같은 파일이 재생 중이면 play를 무시해 연달아 고른 소리가 빠진다(리뷰 1차)
    // 멈추는 사이 음소거·음량이 바뀌었으면 그때 값으로(0이면 틀지 않음, 리뷰 2차), 준비하는 사이 0이 됐으면 바로 멈춘다(리뷰 1차)
    p
        .stop()
        .then((_) {
          final now = _volume;
          return now > 0 ? p.play(AssetSource('audio/sfx/$name.wav'), volume: now) : null;
        })
        .then((_) => _volume > 0 ? null : p.stop())
        .catchError((_) => _drop(this, p));
  }

  /// 오류 난 재생기는 버린다 — 안드로이드는 미디어 오류 뒤 같은 파일을 다시 주면 준비를 건너뛰어 그 소리가 다시 안 난다.
  /// 다음에 새 재생기로(리뷰 4차)
  static void _drop(Sfx f, AudioPlayer p) {
    if (identical(_players[f], p)) _players.remove(f);
    p.dispose().catchError((_) {});
  }

  /// 처음 소리를 낼 때 한 번 — 음소거·음량·앱 숨김을 따른다
  static void _watch() {
    if (_life != null) return;
    final now = WidgetsBinding.instance.lifecycleState;
    _visible = now == null || now == AppLifecycleState.resumed || now == AppLifecycleState.inactive;
    void show(bool v) {
      _visible = v;
      _follow();
    }

    // detached → resumed는 onShow 없이 onResume만 온다(배경음악과 같음)
    _life = AppLifecycleListener(onHide: () => show(false), onShow: () => show(true), onResume: () => show(true));
    Settings.muted.addListener(_follow);
    Settings.sfx.addListener(_follow);
  }

  /// 음소거·효과음 음량이 바뀌면 나고 있는 소리에도 바로 — 승리음 도중 음소거하면 그 자리에서 끊는다(리뷰 1차)
  /// 알고 두는 한계(리뷰 3차): 웹에서 브라우저가 소리를 막아 재생기가 허락을 기다리는 동안 음소거하면, 허락이 난 뒤 그 재생이
  /// 잠깐 들렸다가 끊길 수 있다(멈춤이 기다리는 재생을 취소하지 못함). 웹은 시험 화면이고 출시는 앱만이라(ADR-0025) 둔다 —
  /// 배경음악의 같은 한계(music.dart `_touch`)와 같다.
  static void _follow() {
    final v = _volume;
    for (final p in _players.values) {
      (v > 0 ? p.setVolume(v) : p.stop()).catchError((_) {});
    }
  }

  static AudioPlayer _make(Sfx f) {
    final p = AudioPlayer()..positionUpdater = null; // 위치는 안 쓴다 — 재생 중 매 프레임 묻지 않게(배경음악과 같음)
    p.eventStream.listen((_) {}, onError: (_) => _drop(f, p)); // 재생 중 오류도
    p.setReleaseMode(ReleaseMode.stop).catchError((_) {});
    // 배경음악처럼 다른 앱 소리와 섞고(안드로이드는 오디오 포커스를 안 가져감) 아이폰은 무음 스위치를 따른다
    if (!kIsWeb) {
      p
          .setAudioContext(
            AudioContext(
              android: const AudioContextAndroid(audioFocus: AndroidAudioFocus.none),
              iOS: AudioContextIOS(category: AVAudioSessionCategory.ambient),
            ),
          )
          .catchError((_) {});
    }
    return p;
  }
}
