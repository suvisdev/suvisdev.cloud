import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../auth.dart';
import 'format.dart';
import 'walks_screen.dart';

/// 내 정보 — 누적 통계, 로그아웃, 회원 탈퇴(Google Play 계정 삭제 정책). 비로그인이면 로그인 안내.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key, required this.onLogout, required this.onDeleteAccount});

  final Future<void> Function() onLogout;
  final Future<void> Function() onDeleteAccount;

  Future<void> _confirmDelete(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('회원 탈퇴'),
        content: const Text('계정과 모든 산책 기록이 즉시 삭제되며 되돌릴 수 없습니다. 탈퇴할까요?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('탈퇴', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await onDeleteAccount();
      messenger.showSnackBar(const SnackBar(content: Text('탈퇴했습니다. 그동안 함께 걸어 주셔서 고마워요.')));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('탈퇴하지 못했습니다: $e')));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!ref.watch(loggedInProvider)) {
      return Scaffold(
        appBar: AppBar(title: const Text('내 정보')),
        body: const Column(
          children: [
            Expanded(child: LoginPrompt(message: '로그인하면 누적 산책 통계를 볼 수 있어요.')),
            _PolicyLinks(),
          ],
        ),
      );
    }
    final stats = ref.watch(walkStatsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('내 정보')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: stats.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (_, _) => const Text('통계를 불러오지 못했습니다.'),
                data: (s) => Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    StatTile(label: '산책', value: '${s.totalCount}회'),
                    StatTile(label: '누적 거리', value: formatKm(s.totalDistanceM.toDouble())),
                    StatTile(label: '누적 시간', value: formatDuration(Duration(seconds: s.totalDurationS))),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: onLogout,
            icon: const Icon(Icons.logout),
            label: const Text('로그아웃'),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => _confirmDelete(context),
            child: const Text('회원 탈퇴', style: TextStyle(color: Colors.red)),
          ),
          const _PolicyLinks(),
        ],
      ),
    );
  }
}

/// 개인정보처리방침·계정 삭제 안내 — 앱 안에서도 언제든 볼 수 있게(스토어 정책).
class _PolicyLinks extends StatelessWidget {
  const _PolicyLinks();

  Future<void> _open(String url) =>
      launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Wrap(
        alignment: WrapAlignment.center,
        spacing: 8,
        children: [
          TextButton(
            onPressed: () => _open('https://suvisdev.cloud/gildle/privacy'),
            child: const Text('개인정보처리방침'),
          ),
          TextButton(
            onPressed: () => _open('https://suvisdev.cloud/gildle/account-deletion'),
            child: const Text('계정 삭제 안내'),
          ),
        ],
      ),
    );
  }
}

