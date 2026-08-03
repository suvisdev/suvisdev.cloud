import '../domain/mova_chat_repository.dart';
import 'models/mova_chat_request.dart';
import 'models/mova_chat_response.dart';
import 'mova_chat_api.dart';

class MovaChatRepositoryImpl implements MovaChatRepository {
  final MovaChatApi _api;

  const MovaChatRepositoryImpl(this._api);

  @override
  Future<MovaChatResponse> sendMessage(MovaChatRequest request) {
    return _api.chat(request);
  }
}
