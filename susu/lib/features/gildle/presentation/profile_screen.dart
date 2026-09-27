import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'format.dart';
import 'walks_screen.dart';

/// 내 정보 — 누적 통계와 로그아웃. 즐겨찾기·설정은 아직 없다.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key, required this.onLogout});

  final Future<void> Function() onLogout;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
        ],
      ),
    );
  }
}
