import 'package:flutter/material.dart';

import '../../../core/theme/gildle_theme.dart';

String formatKm(double m) => m >= 1000 ? '${(m / 1000).toStringAsFixed(2)} km' : '${m.round()} m';

String formatDuration(Duration d) {
  final h = d.inHours;
  final m = d.inMinutes % 60;
  final s = d.inSeconds % 60;
  final mm = m.toString().padLeft(2, '0');
  final ss = s.toString().padLeft(2, '0');
  return h > 0 ? '$h:$mm:$ss' : '$mm:$ss';
}

String formatDate(DateTime t) =>
    '${t.year}.${t.month.toString().padLeft(2, '0')}.${t.day.toString().padLeft(2, '0')} '
    '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

const seasonLabels = {
  'spring_autumn': '봄·가을',
  'summer_shade': '그늘 모드',
  'winter_safety': '겨울 안전',
};

/// 라벨 위·값 아래 — 지도 카드·산책 중·기록 상세가 같이 쓴다.
class StatTile extends StatelessWidget {
  const StatTile({super.key, required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.extension<GildleExtras>()!.muted;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: theme.textTheme.labelSmall?.copyWith(color: muted)),
        Text(value, style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      ],
    );
  }
}
