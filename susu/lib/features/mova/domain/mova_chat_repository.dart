import '../data/models/mova_chat_request.dart';
import '../data/models/mova_chat_response.dart';

/// Schema→DTO 변환은 백엔드가 이미 하므로, 이 계층은 응답 JSON을 모델로
/// 파싱해 그대로 넘기는 역할만 한다(추가 변환 없음).
abstract class MovaChatRepository {
  Future<MovaChatResponse> sendMessage(MovaChatRequest request);
}
