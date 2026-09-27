/// 백엔드 `SeasonMode`(suvisdev/apps/gildle/domain/value_objects/season_mode.py)와 1:1.
enum SeasonMode {
  springAutumn('spring_autumn', '봄·가을'),
  summerShade('summer_shade', '여름 그늘'),
  winterSafety('winter_safety', '겨울 안전');

  const SeasonMode(this.apiValue, this.label);

  final String apiValue;
  final String label;
}
