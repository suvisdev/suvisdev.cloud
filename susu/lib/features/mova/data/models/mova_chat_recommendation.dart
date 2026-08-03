/// MovaChatRecommendationSchema와 필드명을 한 글자도 바꾸지 않고 그대로 맞춘다.
class MovaChatRecommendation {
  final String id;
  final int? movieId;
  final String title;
  final String year;
  final String poster;
  final String synopsis;
  final String? platform;
  final String hook;

  const MovaChatRecommendation({
    required this.id,
    this.movieId,
    required this.title,
    this.year = '',
    this.poster = '',
    this.synopsis = '',
    this.platform,
    this.hook = '',
  });

  factory MovaChatRecommendation.fromJson(Map<String, dynamic> json) {
    return MovaChatRecommendation(
      id: json['id'] as String,
      movieId: json['movie_id'] as int?,
      title: json['title'] as String,
      year: json['year'] as String? ?? '',
      poster: json['poster'] as String? ?? '',
      synopsis: json['synopsis'] as String? ?? '',
      platform: json['platform'] as String?,
      hook: json['hook'] as String? ?? '',
    );
  }
}
