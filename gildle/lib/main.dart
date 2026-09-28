import 'package:flutter/material.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:kakao_flutter_sdk_common/kakao_flutter_sdk_common.dart';

import 'auth.dart';
import 'core/config/env.dart';
import 'core/theme/gildle_theme.dart';
import 'features/gildle/presentation/app_services.dart';
import 'features/gildle/presentation/gildle_map_screen.dart';
import 'features/gildle/presentation/profile_screen.dart';
import 'features/gildle/presentation/walks_screen.dart';
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

/// 길들 앱 루트(2026-09-27, susu→gildle 전환, 09-27 저녁 패키지명·폴더도 gildle로). 테마는 웹 gildle.css 토큰.
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

/// 앱 진입점 — 세션 유무를 기록하고 항상 HomeScreen(지도)으로. 로그인은 필요한 곳에서.
/// (09-27 저녁: Suvisdev 인트로 영상 4~5초 대기를 없앴다 — 산책 앱에 맞지 않고 출시 심사에서
/// "왜 기다리나"가 된다. 네이티브 스플래시 색은 launch_background.xml.)
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _decideNextScreen();
  }

  Future<void> _decideNextScreen() async {
    // 로그인 없이도 지도·경로 추천을 쓴다(2026-09-28) — 세션 유무만 기록하고 항상 지도로.
    final hasSession = await AuthSession.hasStoredSession();
    if (!mounted) return;
    ProviderScope.containerOf(context).read(loggedInProvider.notifier).state = hasSession;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const HomeScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GildleColors.lightAccent,
      body: const Center(
        child: Text(
          '길들',
          style: TextStyle(color: Colors.white, fontSize: 40, fontWeight: FontWeight.w900, letterSpacing: 2),
        ),
      ),
    );
  }
}

/// 메인 — 지도 · 기록 · 내 정보 탭. 탭을 오가도 지도 상태가 살아 있게 IndexedStack.
/// 지도는 로그인 없이, 기록·내 정보는 로그인 뒤에 보인다.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _index = 0;

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      if (ref.read(loggedInProvider)) ref.read(pushRegistrarProvider).register();
    });
  }

  Future<void> _logout() async {
    await ref.read(pushRegistrarProvider).unregister();
    await AuthSession.logout();
    if (!mounted) return;
    ref.read(loggedInProvider.notifier).state = false;
    setState(() => _index = 0);
  }

  /// 회원 탈퇴 — 확인은 ProfileScreen이 받는다. 성공하면 게스트 상태로 지도에.
  Future<void> _deleteAccount() async {
    await ref.read(pushRegistrarProvider).unregister();
    await AuthSession.deleteAccount();
    if (!mounted) return;
    ref.read(loggedInProvider.notifier).state = false;
    setState(() => _index = 0);
  }

  @override
  Widget build(BuildContext context) {
    // 로그인하면(기록·내 정보·산책 저장에서) 그때 푸시 토큰을 등록한다.
    ref.listen<bool>(loggedInProvider, (prev, next) {
      if (next && prev != true) ref.read(pushRegistrarProvider).register();
    });
    // 최소 지원 버전 미만이면 닫을 수 없는 안내를 띄운다(스토어 링크는 등록 뒤 store_url로).
    ref.listen(versionCheckProvider, (_, next) {
      final info = next.valueOrNull;
      if (info == null) return;
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (_) => PopScope(
          canPop: false,
          child: AlertDialog(
            title: const Text('업데이트가 필요합니다'),
            content: Text('이 버전은 더 이상 지원되지 않습니다. 최신 버전 ${info.latestVersion}으로 업데이트해 주세요.'),
          ),
        ),
      );
    });
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [
          const GildleMapScreen(),
          const WalksScreen(),
          ProfileScreen(onLogout: _logout, onDeleteAccount: _deleteAccount),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.map_outlined), selectedIcon: Icon(Icons.map), label: '지도'),
          NavigationDestination(icon: Icon(Icons.history), label: '기록'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: '내 정보'),
        ],
      ),
    );
  }
}
