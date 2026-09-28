import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth.dart';
import '../../../core/theme/gildle_theme.dart';
import '../data/models/walk.dart';
import 'format.dart';
import 'map_controller.dart';
import 'walk_detail_screen.dart';
import 'walk_session_controller.dart';

/// 목록·통계는 화면이 열릴 때마다 다시 받는다(저장·삭제 뒤 최신을 보장하는 가장 단순한 방법).
final walksListProvider = FutureProvider.autoDispose<List<WalkSummary>>(
  (ref) => ref.watch(walksApiProvider).list(),
);
final walkStatsProvider = FutureProvider.autoDispose<WalkStats>(
  (ref) => ref.watch(walksApiProvider).stats(),
);

class WalksScreen extends ConsumerWidget {
  const WalksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!ref.watch(loggedInProvider)) {
      return Scaffold(
        appBar: AppBar(title: const Text('기록')),
        body: const LoginPrompt(message: '로그인하면 산책 기록을 저장하고 다시 볼 수 있어요.'),
      );
    }
    final walks = ref.watch(walksListProvider);
    final stats = ref.watch(walkStatsProvider);
    final muted = Theme.of(context).extension<GildleExtras>()!.muted;

    return Scaffold(
      appBar: AppBar(title: const Text('기록')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(walksListProvider);
          ref.invalidate(walkStatsProvider);
          await ref.read(walksListProvider.future);
        },
        child: walks.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            children: [
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(describeApiError(e, '기록을'), textAlign: TextAlign.center),
              ),
            ],
          ),
          data: (items) => ListView(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 24),
            children: [
              stats.maybeWhen(
                data: (s) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        StatTile(label: '산책', value: '${s.totalCount}회'),
                        StatTile(label: '누적 거리', value: formatKm(s.totalDistanceM.toDouble())),
                        StatTile(label: '누적 시간', value: formatDuration(Duration(seconds: s.totalDurationS))),
                      ],
                    ),
                  ),
                ),
                orElse: () => const SizedBox.shrink(),
              ),
              if (items.isEmpty)
                Padding(
                  padding: const EdgeInsets.all(32),
                  child: Text('아직 산책 기록이 없습니다.\n지도에서 산책을 시작해 보세요.',
                      textAlign: TextAlign.center, style: TextStyle(color: muted)),
                ),
              for (final w in items)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.directions_walk),
                    title: Text('${formatKm(w.distanceM.toDouble())} · ${formatDuration(Duration(seconds: w.durationS))}'),
                    subtitle: Text(
                      '${formatDate(w.startedAt)} · ${seasonLabels[w.seasonMode] ?? w.seasonMode}'
                      '${w.avgShadeScore != null ? ' · 그늘 ${(w.avgShadeScore! * 100).round()}%' : ''}',
                    ),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => WalkDetailScreen(id: w.id)),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
