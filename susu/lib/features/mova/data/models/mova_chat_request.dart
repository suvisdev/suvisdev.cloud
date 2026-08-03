/// suvisdev/apps/mova/adapter/inbound/api/schemas/market_chat_schema.py의
/// MovaChatRequest와 필드명을 그대로 맞춘다.
class MovaChatRequest {
  final String message;
  final List<Map<String, String>> history;
  final String? model;
  final int? userId;

  const MovaChatRequest({
    required this.message,
    this.history = const [],
    this.model,
    this.userId,
  });

  Map<String, dynamic> toJson() => {
    'message': message,
    'history': history,
    'model': model,
    'user_id': userId,
  };
}
