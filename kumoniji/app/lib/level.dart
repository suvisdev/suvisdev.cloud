import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'l10n/app_localizations.dart';

const gold = Color(0xFFC9A24A);

String levelName(AppLocalizations t, String lv) => switch (lv) {
  'easy' => t.levelEasy,
  'hard' => t.levelHard,
  _ => t.levelNormal,
};

/// 마지막으로 고른 난이도(처음이거나 저장소를 못 쓰면 중급).
Future<String> savedLevel() async {
  try {
    return (await SharedPreferences.getInstance()).getString('level') ?? 'normal';
  } catch (_) {
    return 'normal';
  }
}

/// 난이도를 고르는 창. 눌러 고르고 '시작'으로 확정하면 기억하고 돌려준다(X·취소면 null).
Future<String?> pickLevel(BuildContext context, {required String current, String? title}) async {
  final t = AppLocalizations.of(context)!;
  var picked = current;
  final choice = await showDialog<String>(
    context: context,
    builder: (c) => StatefulBuilder(
      builder: (c, setState) => AlertDialog(
        scrollable: true, // 가로 화면·낮은 창에서도 목록을 스크롤해 고를 수 있게
        titlePadding: const EdgeInsets.fromLTRB(24, 12, 8, 0),
        title: Row(
          children: [
            Expanded(child: Text(title ?? t.chooseLevel)),
            IconButton(
              tooltip: MaterialLocalizations.of(c).closeButtonTooltip,
              icon: const Icon(Icons.close),
              onPressed: () => Navigator.pop(c),
            ),
          ],
        ),
        contentPadding: const EdgeInsets.symmetric(vertical: 8),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final (lv, desc) in [
              ('easy', t.levelEasyDesc),
              ('normal', t.levelNormalDesc),
              ('hard', t.levelHardDesc),
            ])
              ListTile(
                key: ValueKey('level-$lv'),
                selected: lv == picked,
                selectedColor: gold,
                title: Text(levelName(t, lv), style: TextStyle(fontWeight: lv == picked ? FontWeight.bold : null)),
                subtitle: Text(desc),
                trailing: lv == picked ? const Icon(Icons.check, color: gold) : null,
                onTap: () => setState(() => picked = lv),
              ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: Text(t.cancel)),
          FilledButton(
            key: const ValueKey('level-start'),
            onPressed: () => Navigator.pop(c, picked),
            child: Text(t.start),
          ),
        ],
      ),
    ),
  );
  if (choice != null) {
    try {
      await (await SharedPreferences.getInstance()).setString('level', choice);
    } catch (_) {}
  }
  return choice;
}
