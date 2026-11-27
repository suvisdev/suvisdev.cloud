import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/widgets.dart';

import 'settings.dart';

/// 배경음악(11-26 사용자: 우선 넣고 나중에 바꿈). 한 곡을 앱 내내 반복하고, 음량·음소거 옵션을 바로 따른다.
/// 앱이 뒤로 가면 멈추고 돌아오면 이어 튼다. 곡을 바꾸려면 assets/audio/의 파일만 바꾼다.
///
/// 재생기는 [_loop] 한 곳만 만진다 — '지금 틀어야 하나'([_want])와 '틀고 있나'([_live])를 차례로 맞춘다. 숨김·음소거·
/// 복귀가 준비 중에 끼어도 끝난 뒤 다시 맞추므로, 재생과 멈춤 요청이 엇갈려 멈춘 채 남지 않는다(리뷰 7~13차).
class Music {
  static final _player = AudioPlayer();
  static AppLifecycleListener? _life;
  static var _on = false; // 재생을 시작해도 되나(앱은 처음부터, 웹은 첫 터치 뒤)
  static var _visible = true; // 앱·탭이 보이는 중
  static var _live = false; // 재생기에 틀라고 했고 그게 끝났다
  static var _dirty = false;
  static var _rewind = false; // 곡이 끝나 되감는 중
  static var _listening = false; // 웹 첫 터치 감시 중
  static var _broken = false; // 재생 오류 — 다음 재생 전에 재생기를 비운다
  static Future<void>? _run;

  static bool get _want => _on && _visible && Settings.musicVolume > 0;

  static Future<void> start() async {
    if (_life != null) return;
    // detached → resumed는 onShow 없이 onResume만 온다 — 둘 다 보이는 것으로(리뷰 20차)
    _life = AppLifecycleListener(onHide: _hide, onShow: _show, onResume: _show);
    // 리스너는 등록 때의 상태로 onHide를 부르지 않는다 — 설정을 읽는 사이 이미 뒤로 갔으면 숨은 채로 시작(리뷰 18차)
    final now = WidgetsBinding.instance.lifecycleState;
    _visible = now == null || now == AppLifecycleState.resumed || now == AppLifecycleState.inactive;
    Settings.music.addListener(_sync);
    Settings.muted.addListener(_sync);
    // 반복은 재생기에 맡기지 않고 곡이 끝나면 맞추기로 다시 튼다 — iOS 재생기의 반복은 처음으로 되감기가 끝나면 멈춤·
    // 음소거를 무시하고 다시 틀어 버린다(리뷰 10·14차)
    // 재생 위치는 안 쓴다 — 기본 갱신기는 재생 중 매 프레임 위치를 물어 화면이 멈춰 있어도 프레임을 돌린다(리뷰 26차)
    _player.positionUpdater = null;
    await _player.setReleaseMode(ReleaseMode.stop).catchError((_) {}); // 실패해도 아래 시작은 이어 간다(리뷰 21차)
    _player.onPlayerComplete.listen(
      (_) async {
        // 안드로이드는 재생 오류 뒤에도 완료를 알린다 — 그때 다시 틀면 오류가 이어질 때 비우기·재시도가 끝없이 돈다.
        // 다음 재생은 복귀·음소거 해제 같은 맞추기가 한다(리뷰 25차)
        if (_broken) return;
        _rewind = true;
        // iOS 재생기는 완료를 먼저 알리고 처음으로 되감기를 마친 뒤(onSeekComplete) 재생 상태를 끈다 — 그 전에 다시 틀면
        // 그 끄기가 새 재생을 덮어 다음 반복이 끊긴다. 되감기 완료를 기다리고, 그동안은 틀고 있는 것으로 둬 음량 조절이
        // 새로 틀지 않게(리뷰 15~17차). 다른 플랫폼은 되감지 않으니 바로
        if (defaultTargetPlatform == TargetPlatform.iOS && !kIsWeb) {
          // 기다리는 사이 재생기 오류가 와도 아래로 — 안 그러면 _rewind가 켜진 채 남아 다시 틀 수 없다(리뷰 23차)
          await _player.onSeekComplete.first.timeout(const Duration(seconds: 3), onTimeout: () {}).catchError((_) {});
        }
        _rewind = false;
        _live = false;
        _sync();
      },
      // 재생 중 오류(안드로이드 미디어 서비스가 죽는 등) — 재생기는 준비 안 된 상태가 되고 같은 파일로 play()해도 다시 준비하지
      // 않는다. 표시만 해 두고 비우기는 맞추기(_loop)가 다음 재생 직전에 한다 — 여기서 비우면 그사이 복귀로 시작한 재생과
      // 겹쳐 방금 튼 소스를 지울 수 있다(리뷰 22·23차). 여기서 바로 다시 틀지 않는다 — 계속 실패하면 오류·재생이 끝없이 돈다
      onError: (_) {
        _live = false;
        _broken = true;
      },
    );
    if (!kIsWeb) {
      // 다른 앱 소리(팟캐스트 등)와 섞어 튼다(리뷰 3·4차: pause만으로는 포커스를 돌려주지 않는다). 안드로이드는 오디오
      // 포커스를 가져가지 않고, 아이폰은 ambient — 저절로 섞이고 무음 스위치도 따른다. ambient에 섞기 옵션을 따로
      // 주면 설정이 거절된다(리뷰 5차). 설정이 실패해도 기본 세션으로 튼다 — 여기서 멈추면 _on이 안 켜져 음악이 영영
      // 안 나온다(리뷰 21차)
      try {
        await _player.setAudioContext(
          AudioContext(
            android: const AudioContextAndroid(audioFocus: AndroidAudioFocus.none),
            iOS: AudioContextIOS(category: AVAudioSessionCategory.ambient),
          ),
        );
      } catch (_) {}
    }
    // 웹은 사용자가 누르기 전에는 소리를 막는다(재생기의 AudioContext가 멈춘 채라 준비조차 안 끝나 30초를
    // 기다린다) — 터치 때 튼다. 앱은 바로
    if (kIsWeb) {
      _listening = true;
      GestureBinding.instance.pointerRouter.addGlobalRoute(_touch);
    } else {
      _on = true;
      await _sync();
    }
  }

  /// 원하는 상태가 바뀌었다 — 맞추기를 한 번 더 돌린다(돌고 있으면 끝난 뒤 이어서).
  static Future<void> _sync() {
    _dirty = true;
    // 음소거·숨김은 소리부터 바로 끈다 — 재생 준비(play) 중이면 맞추기는 준비가 끝난 뒤에야 멈춰, 그 사이 곡이 잠깐
    // 들린다(리뷰 17차). 음량만 바꾸는 건 재생기 상태를 건드리지 않는다
    if (!_want) _player.setVolume(0).catchError((_) {});
    return _run ??= _loop().whenComplete(() => _run = null);
  }

  static Future<void> _loop() async {
    while (_dirty) {
      _dirty = false;
      try {
        if (_want && !_live && !_rewind) {
          // 되감는 중엔 숨겼다 돌아와도 끝난 뒤에 튼다
          if (_broken) {
            _broken = false;
            await _player.release();
            if (!_want) continue; // 비우는 사이 숨겨지거나 음소거됨 — 틀지 않는다(리뷰 24차)
          }
          await _player.setVolume(Settings.musicVolume);
          // 웹 재생기는 터치 허락 시간이 지나 소리가 막히면 AudioContext.resume()을 끝없이 기다린다 — 시간 제한을 둬 실패로
          // 끝내야 맞추기가 풀리고 다음 터치에 다시 시도한다(리뷰 19차)
          await _player.play(AssetSource('audio/cloud_walk.mp3')).timeout(const Duration(seconds: 15));
          _live = !_broken; // 준비하는 사이 오류가 왔으면 틀지 않은 것으로 — 다음 맞추기가 비우고 새로
        } else if (!_want && _live) {
          // 음소거·음량 0이면 재생 자체를 멈춘다 — 소리 없이 틀어도 다른 앱 소리를 끊을 수 있다(리뷰 3차)
          _live = false;
          await _player.pause();
        } else if (_live) {
          await _player.setVolume(Settings.musicVolume);
          // iOS 오디오 인터럽션(전화 등) 뒤엔 시스템이 멈춘 채 두기도 하고, 플러그인 상태는 여전히 '재생 중'이라 알 수 없다 —
          // 맞출 때마다 이어 틀기를 보낸다(재생 중이면 아무 일 없음). 되감는 중엔 보내지 않는다(리뷰 15·26·27차). iOS만 —
          // 웹 재생기의 resume은 재생 중에도 마지막 멈춘 곳으로 되감아 음량을 움직일 때마다 곡이 처음으로 간다(리뷰 28차)
          if (!_rewind && !kIsWeb && defaultTargetPlatform == TargetPlatform.iOS) await _player.resume();
        }
      } catch (_) {
        // 소리가 안 나도 게임은 그대로. 받기에 실패한 재생기는 같은 주소면 다시 받지 않는다 — 비워 두면 다음 시도에
        // 새로 받는다(리뷰 3차)
        _live = false;
        try {
          await _player.release();
        } catch (_) {}
      }
    }
  }

  /// 웹: 터치는 손가락을 뗄 때 브라우저가 소리를 허락한다 — 떼는 순간 틀고, 막히면 다음 터치에 다시(리뷰 2차)
  /// 알고 두는 한계(리뷰 6차): 재생기는 터치 뒤에야 파일을 받아 준비하므로, 그 사이 터치의 허락 시간이 지나면 사파리는
  /// 재생을 막을 수 있다(미리 받기도 터치 전엔 준비가 끝나지 않는다). 웹은 시험 화면이고 출시는 앱만이라(ADR-0025) 둔다.
  static Future<void> _touch(PointerEvent e) async {
    if (e is! PointerUpEvent) return;
    _on = true;
    await _sync();
    if (_live && _listening) {
      _listening = false; // 터치가 겹쳐 둘 다 여기 와도 한 번만 뗀다
      GestureBinding.instance.pointerRouter.removeGlobalRoute(_touch);
    }
  }

  static void _hide() {
    _visible = false;
    _sync();
  }

  static void _show() {
    _visible = true;
    _sync();
  }
}
