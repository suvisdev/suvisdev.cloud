import 'package:flutter/material.dart';

/// 길들 앱 테마 — 웹(`suvis/app/gildle/gildle.css`)의 토큰을 그대로 옮긴다.
///
/// mova 토큰(어두운 영화관 + 핑크)을 쓰지 않는 이유: 산책 앱과 톤이 맞지 않는다.
/// 웹과 같은 값을 쓰면 같은 서비스라는 인상이 유지된다(2026-09-22).
abstract final class GildleColors {
  // 다크
  static const darkBg = Color(0xFF0A0D0A);
  static const darkSurface = Color(0xFF121A14);
  static const darkSurface2 = Color(0xFF1A261C);
  static const darkAccent = Color(0xFF34D399);
  static const darkAccentBright = Color(0xFF6EE7B7);
  static const darkText = Color(0xFFF0FDF4);
  static const darkMuted = Color(0xFF9CA3AF);

  // 라이트
  static const lightBg = Color(0xFFF4F9F0);
  static const lightSurface = Color(0xFFFAFDF7);
  static const lightSurface2 = Color(0xFFE2EDDA);
  static const lightAccent = Color(0xFF16A34A);
  static const lightAccentBright = Color(0xFF15803D);
  static const lightText = Color(0xFF0F1A0A);
  static const lightMuted = Color(0xFF4A5D3E);

  /// 그늘·나무를 가리키는 보조색(웹 `--gildle-warm`)
  static const darkWarm = Color(0xFFD4A574);
  static const lightWarm = Color(0xFFA16207);
}

ThemeData gildleLightTheme() => _build(
      brightness: Brightness.light,
      bg: GildleColors.lightBg,
      surface: GildleColors.lightSurface,
      surfaceAlt: GildleColors.lightSurface2,
      accent: GildleColors.lightAccent,
      text: GildleColors.lightText,
      muted: GildleColors.lightMuted,
    );

ThemeData gildleDarkTheme() => _build(
      brightness: Brightness.dark,
      bg: GildleColors.darkBg,
      surface: GildleColors.darkSurface,
      surfaceAlt: GildleColors.darkSurface2,
      accent: GildleColors.darkAccent,
      text: GildleColors.darkText,
      muted: GildleColors.darkMuted,
    );

ThemeData _build({
  required Brightness brightness,
  required Color bg,
  required Color surface,
  required Color surfaceAlt,
  required Color accent,
  required Color text,
  required Color muted,
}) {
  final scheme = ColorScheme.fromSeed(
    seedColor: accent,
    brightness: brightness,
  ).copyWith(
    primary: accent,
    surface: surface,
    onSurface: text,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: bg,
    appBarTheme: AppBarTheme(
      backgroundColor: bg,
      foregroundColor: text,
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: surface,
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: accent,
        foregroundColor: brightness == Brightness.dark ? GildleColors.darkBg : Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: surface,
      indicatorColor: accent.withValues(alpha: 0.18),
      elevation: 0,
    ),
    textTheme: Typography.material2021(platform: TargetPlatform.android)
        .black
        .apply(bodyColor: text, displayColor: text),
    dividerColor: surfaceAlt,
    extensions: <ThemeExtension<dynamic>>[
      GildleExtras(
        surfaceAlt: surfaceAlt,
        muted: muted,
        warm: brightness == Brightness.dark ? GildleColors.darkWarm : GildleColors.lightWarm,
      ),
    ],
  );
}

/// ColorScheme에 자리가 없는 길들 고유 색(보조 배경·흐린 글씨·그늘 색).
class GildleExtras extends ThemeExtension<GildleExtras> {
  const GildleExtras({required this.surfaceAlt, required this.muted, required this.warm});

  final Color surfaceAlt;
  final Color muted;
  final Color warm;

  @override
  GildleExtras copyWith({Color? surfaceAlt, Color? muted, Color? warm}) => GildleExtras(
        surfaceAlt: surfaceAlt ?? this.surfaceAlt,
        muted: muted ?? this.muted,
        warm: warm ?? this.warm,
      );

  @override
  GildleExtras lerp(ThemeExtension<GildleExtras>? other, double t) {
    if (other is! GildleExtras) return this;
    return GildleExtras(
      surfaceAlt: Color.lerp(surfaceAlt, other.surfaceAlt, t)!,
      muted: Color.lerp(muted, other.muted, t)!,
      warm: Color.lerp(warm, other.warm, t)!,
    );
  }
}
