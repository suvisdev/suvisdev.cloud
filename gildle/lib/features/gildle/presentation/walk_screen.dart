import 'package:flutter/material.dart';
import 'package:flutter_naver_map/flutter_naver_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/gildle_theme.dart';
import 'format.dart';
import 'walk_detail_screen.dart';
import 'walk_session_controller.dart';

/// 산책 중 — 현재 위치를 따라가며 걸은 길을 그리고, 종료하면 `POST /walks`에 저장한다.
class WalkScreen extends ConsumerStatefulWidget {
  const WalkScreen({super.key, this.planned});

  final PlannedRoute? planned;

  @override
  ConsumerState<WalkScreen> createState() => _WalkScreenState();
}

class _WalkScreenState extends ConsumerState<WalkScreen> {
  NaverMapController? _map;

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(walkSessionProvider.notifier).start(planned: widget.planned));
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(walkSessionProvider);
    ref.listen<WalkSessionState>(walkSessionProvider, (prev, next) {
      if (prev?.points.length != next.points.length) _drawWalked(next);
      if (next.error != null && prev?.error != next.error) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(content: Text(next.error!)));
      }
    });

    return PopScope(
      canPop: state.status != WalkStatus.tracking,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _confirmStop();
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('산책 중')),
        body: Stack(
          children: [
            NaverMap(
              options: const NaverMapViewOptions(
                initialCameraPosition: NCameraPosition(target: NLatLng(37.5665, 126.9780), zoom: 15),
                locationButtonEnable: true,
              ),
              onMapReady: (c) async {
                _map = c;
                c.setLocationTrackingMode(NLocationTrackingMode.follow);
                await _drawPlanned();
                await _drawWalked(ref.read(walkSessionProvider));
              },
            ),
            Positioned(left: 12, right: 12, bottom: 12, child: _StatsCard(state: state, onStop: _confirmStop)),
          ],
        ),
      ),
    );
  }

  Future<void> _drawPlanned() async {
    final planned = widget.planned;
    final map = _map;
    if (planned == null || map == null || planned.coordinates.length < 2) return;
    final muted = Theme.of(context).extension<GildleExtras>()!.muted;
    await map.addOverlay(NPolylineOverlay(
      id: 'planned',
      coords: planned.coordinates.map((c) => NLatLng(c.lat, c.lng)).toList(),
      color: muted.withValues(alpha: 0.7),
      width: 5,
      pattern: const [12, 8],
    ));
  }

  Future<void> _drawWalked(WalkSessionState state) async {
    final map = _map;
    if (map == null || state.points.length < 2) return;
    final accent = Theme.of(context).colorScheme.primary;
    await map.addOverlay(NPolylineOverlay(
      id: 'walked',
      coords: state.points.map((c) => NLatLng(c.lat, c.lng)).toList(),
      color: accent,
      width: 7,
    ));
  }

  Future<void> _confirmStop() async {
    final notifier = ref.read(walkSessionProvider.notifier);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('산책을 끝낼까요?'),
        content: const Text('끝내면 지금까지 걸은 길이 기록에 저장됩니다.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('계속 걷기')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('끝내기')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    await notifier.stop();
    if (!mounted) return;
    final state = ref.read(walkSessionProvider);
    if (state.points.length < 2) {
      final keep = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('위치가 잡히지 않았습니다'),
          content: const Text('걸은 길이 없어 저장할 내용이 없습니다. 기록을 버릴까요?'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('그래도 저장')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('버리기')),
          ],
        ),
      );
      if (keep == true) {
        notifier.discard();
        if (mounted) Navigator.of(context).pop();
        return;
      }
    }
    final saved = await notifier.save();
    if (!mounted) return;
    if (saved) {
      final detail = ref.read(walkSessionProvider).saved!;
      notifier.discard();
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => WalkDetailScreen(id: detail.id, initial: detail)),
      );
    }
  }
}

class _StatsCard extends StatelessWidget {
  const _StatsCard({required this.state, required this.onStop});

  final WalkSessionState state;
  final VoidCallback onStop;

  @override
  Widget build(BuildContext context) {
    final pace = state.paceMinPerKm;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                StatTile(label: '거리', value: formatKm(state.distanceM)),
                StatTile(label: '시간', value: formatDuration(state.elapsed)),
                StatTile(label: '페이스', value: pace == null ? '—' : '${pace.toStringAsFixed(1)}분/km'),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: state.status == WalkStatus.tracking ? onStop : null,
                icon: state.status == WalkStatus.saving
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.stop),
                label: Text(state.status == WalkStatus.saving ? '저장 중…' : '산책 끝내기'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

