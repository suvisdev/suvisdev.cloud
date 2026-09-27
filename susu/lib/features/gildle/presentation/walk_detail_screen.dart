import 'package:flutter/material.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/walk.dart';
import 'format.dart';
import 'map_controller.dart';
import 'walk_session_controller.dart';

final walkDetailProvider = FutureProvider.autoDispose.family<WalkDetail, int>(
  (ref, id) => ref.watch(walksApiProvider).detail(id),
);

/// 기록 상세 — 걸은 길 폴리라인 + 수치 + 삭제. 저장 직후엔 `initial`로 재조회 없이 그린다.
class WalkDetailScreen extends ConsumerWidget {
  const WalkDetailScreen({super.key, required this.id, this.initial});

  final int id;
  final WalkDetail? initial;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = initial != null
        ? AsyncValue.data(initial!)
        : ref.watch(walkDetailProvider(id));

    return Scaffold(
      appBar: AppBar(
        title: const Text('산책 기록'),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: '삭제',
            onPressed: () => _delete(context, ref),
          ),
        ],
      ),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text(describeApiError(e, '기록을'))),
        data: (w) => Column(
          children: [
            Expanded(child: _WalkMap(walk: w)),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(formatDate(w.startedAt), style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      StatTile(label: '거리', value: formatKm(w.distanceM.toDouble())),
                      StatTile(label: '시간', value: formatDuration(Duration(seconds: w.durationS))),
                      StatTile(label: '모드', value: seasonLabels[w.seasonMode] ?? w.seasonMode),
                      if (w.avgShadeScore != null)
                        StatTile(label: '그늘', value: '${(w.avgShadeScore! * 100).round()}%'),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _delete(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('이 기록을 삭제할까요?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('삭제')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref.read(walksApiProvider).delete(id);
      if (context.mounted) Navigator.of(context).pop();
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(describeApiError(e, '기록을'))));
      }
    }
  }
}

class _WalkMap extends StatelessWidget {
  const _WalkMap({required this.walk});

  final WalkDetail walk;

  @override
  Widget build(BuildContext context) {
    final accent = Theme.of(context).colorScheme.primary;
    final coords = walk.path.map((c) => NLatLng(c.lat, c.lng)).toList();
    return NaverMap(
      options: NaverMapViewOptions(
        initialCameraPosition: NCameraPosition(
          target: coords.isEmpty ? const NLatLng(37.5665, 126.9780) : coords.first,
          zoom: 15,
        ),
      ),
      onMapReady: (map) async {
        if (coords.length < 2) return;
        await map.addOverlay(NPolylineOverlay(id: 'walked', coords: coords, color: accent, width: 7));
        await map.updateCamera(
          NCameraUpdate.fitBounds(NLatLngBounds.from(coords), padding: const EdgeInsets.all(48)),
        );
      },
    );
  }
}
