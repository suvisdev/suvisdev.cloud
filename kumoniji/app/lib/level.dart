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

/// 난이도를 고르는 창. 고르면 기억하고 돌려준다(취소하면 null).
Future<String?> pickLevel(BuildContext context, {required String current, String? title}) async {
  final t = AppLocalizations.of(context)!;
  final choice = await showDialog<String>(
    context: context,
    builder: (c) => SimpleDialog(
      title: Text(title ?? t.chooseLevel),
      children: [
        for (final (lv, desc) in [('easy', t.levelEasyDesc), ('normal', t.levelNormalDesc), ('hard', t.levelHardDesc)])
          ListTile(
            key: ValueKey('level-$lv'),
            title: Text(levelName(t, lv), style: TextStyle(fontWeight: lv == current ? FontWeight.bold : null)),
            subtitle: Text(desc),
            trailing: lv == current ? const Icon(Icons.check, color: gold) : null,
            onTap: () => Navigator.pop(c, lv),
          ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(onPressed: () => Navigator.pop(c), child: Text(t.cancel)),
        ),
      ],
    ),
  );
  if (choice != null) {
    try {
      await (await SharedPreferences.getInstance()).setString('level', choice);
    } catch (_) {}
  }
  return choice;
}
