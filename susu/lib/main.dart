import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:kakao_flutter_sdk_common/kakao_flutter_sdk_common.dart';
import 'package:video_player/video_player.dart';

import 'auth.dart';
import 'core/config/env.dart';
import 'core/theme/gildle_theme.dart';
import 'features/gildle/presentation/gildle_map_screen.dart';
import 'kakao_config.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await KakaoSdk.init(nativeAppKey: kakaoNativeAppKey);
  if (AppConfig.naverMapClientId.isNotEmpty) {
    await FlutterNaverMap().init(
      clientId: AppConfig.naverMapClientId,
      onAuthFailed: (e) => debugPrint('네이버 지도 인증 실패: $e'),
    );
  }
  runApp(const ProviderScope(child: GildleApp()));
}

// go_router는 진입점(root) 하나만 등록한다 — Splash → Auth → Home 전환은
// Navigator.push(imperative)를 그대로 쓴다.
final _router = GoRouter(
  routes: [GoRoute(path: '/', builder: (context, state) => const SplashScreen())],
);

/// 길들 앱 루트(2026-09-27, susu → gildle 전환). 테마는 웹 gildle.css 토큰.
class GildleApp extends StatelessWidget {
  const GildleApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: '길들',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.system,
      theme: gildleLightTheme(),
      darkTheme: gildleDarkTheme(),
      routerConfig: _router,
    );
  }
}

/// 앱 진입점 — 저장된 모바일 세션이 있으면 곧바로 HomeScreen(지도)으로, 없으면
/// 인트로 영상을 4~5초 재생한 뒤 AuthScreen(카카오 로그인)으로 자동 전환한다.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  VideoPlayerController? _videoController;
  Timer? _autoAdvanceTimer;

  @override
  void initState() {
    super.initState();
    _decideNextScreen();
  }

  Future<void> _decideNextScreen() async {
    final hasSession = await AuthSession.hasStoredSession();
    if (!mounted) return;

    if (hasSession) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const HomeScreen()),
      );
      return;
    }

    final controller = VideoPlayerController.asset('assets/videos/intro.mp4');
    _videoController = controller;
    await controller.initialize();
    if (!mounted) return;
    setState(() {});
    controller.play();

    _autoAdvanceTimer = Timer(const Duration(seconds: 5), () {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const AuthScreen()),
      );
    });
  }

  @override
  void dispose() {
    _autoAdvanceTimer?.cancel();
    _videoController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _videoController;
    return Scaffold(
      backgroundColor: Colors.black,
      body: (controller != null && controller.value.isInitialized)
          ? Center(
              child: AspectRatio(
                aspectRatio: controller.value.aspectRatio,
                child: VideoPlayer(controller),
              ),
            )
          : const SizedBox.shrink(),
    );
  }
}

/// 로그인 뒤 메인 — 지도 화면에 로그아웃 버튼만 얹는다. 기록·마이페이지 탭은 다음 단계.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  Future<void> _logout(BuildContext context) async {
    await AuthSession.logout();
    if (!context.mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return GildleMapScreen(
      actions: [
        IconButton(
          icon: const Icon(Icons.logout),
          tooltip: '로그아웃',
          onPressed: () => _logout(context),
        ),
      ],
    );
  }
}
