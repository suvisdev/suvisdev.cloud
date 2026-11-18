// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Korean (`ko`).
class AppLocalizationsKo extends AppLocalizations {
  AppLocalizationsKo([String locale = 'ko']) : super(locale);

  @override
  String get title => '쿠모니지';

  @override
  String get newGame => '새 게임';

  @override
  String get play => '내기';

  @override
  String get pass => '패스';

  @override
  String get today => '오늘의 무늬';

  @override
  String get illegal => '낼 수 없는 패예요';

  @override
  String get yourTurn => '내 차례';

  @override
  String get passed => '패스';

  @override
  String get you => '나';

  @override
  String bot(int n) {
    return '봇 $n';
  }

  @override
  String points(int n) {
    return '$n점';
  }

  @override
  String winner(String name) {
    return '$name 1등!';
  }

  @override
  String get result => '결과';

  @override
  String get serverError => '서버에 연결하지 못했어요. 다시 시도해 주세요.';
}
