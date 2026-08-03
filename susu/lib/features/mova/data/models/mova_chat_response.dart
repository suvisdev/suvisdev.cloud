import 'mova_chat_recommendation.dart';

/// MovaChatResponseSchema와 필드명을 한 글자도 바꾸지 않고 그대로 맞춘다.
class MovaChatResponse {
  final String reply;
  final List<MovaChatRecommendation> recommendations;
  final String? refinedQuery;
  final List<String> keywords;
  final String? intentType;
  final Map<String, dynamic> searchFilters;

  const MovaChatResponse({
    required this.reply,
    this.recommendations = const [],
    this.refinedQuery,
    this.keywords = const [],
    this.intentType,
    this.searchFilters = const {},
  });

  factory MovaChatResponse.fromJson(Map<String, dynamic> json) {
    return MovaChatResponse(
      reply: json['reply'] as String,
      recommendations: (json['recommendations'] as List<dynamic>? ?? [])
          .map((e) => MovaChatRecommendation.fromJson(e as Map<String, dynamic>))
          .toList(),
      refinedQuery: json['refined_query'] as String?,
      keywords: (json['keywords'] as List<dynamic>? ?? []).cast<String>(),
      intentType: json['intent_type'] as String?,
      searchFilters: (json['search_filters'] as Map<String, dynamic>?) ?? const {},
    );
  }
}
