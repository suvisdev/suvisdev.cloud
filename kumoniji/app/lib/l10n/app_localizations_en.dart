// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get title => 'Kumoniji';

  @override
  String get newGame => 'New game';

  @override
  String get play => 'Play';

  @override
  String get pass => 'Pass';

  @override
  String get today => 'Today\'s suit';

  @override
  String get illegal => 'That play isn\'t allowed';

  @override
  String get yourTurn => 'Your turn';

  @override
  String get passed => 'Pass';

  @override
  String get you => 'You';

  @override
  String bot(int n) {
    return 'Bot $n';
  }

  @override
  String points(int n) {
    return '$n pts';
  }

  @override
  String winner(String name) {
    return '$name went out!';
  }

  @override
  String get result => 'Result';

  @override
  String get serverError => 'Couldn\'t reach the server. Try again.';
}
