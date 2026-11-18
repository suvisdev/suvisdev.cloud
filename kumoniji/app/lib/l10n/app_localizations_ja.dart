// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Japanese (`ja`).
class AppLocalizationsJa extends AppLocalizations {
  AppLocalizationsJa([String locale = 'ja']) : super(locale);

  @override
  String get title => 'クモニジ';

  @override
  String get newGame => '新しいゲーム';

  @override
  String get play => '出す';

  @override
  String get pass => 'パス';

  @override
  String get today => '今日の柄';

  @override
  String get illegal => 'その組み合わせは出せません';

  @override
  String get yourTurn => 'あなたの番';

  @override
  String get passed => 'パス';

  @override
  String get you => 'あなた';

  @override
  String bot(int n) {
    return 'ボット$n';
  }

  @override
  String points(int n) {
    return '$n点';
  }

  @override
  String winner(String name) {
    return '$nameが上がりました！';
  }

  @override
  String get result => '結果';

  @override
  String get serverError => 'サーバーに接続できません。もう一度お試しください。';
}
