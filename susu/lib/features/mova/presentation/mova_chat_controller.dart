import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../data/models/mova_chat_request.dart';
import '../data/models/mova_chat_response.dart';
import '../data/mova_chat_api.dart';
import '../data/mova_chat_repository_impl.dart';
import '../domain/mova_chat_repository.dart';

final movaChatApiProvider = Provider<MovaChatApi>(
  (ref) => MovaChatApi(ref.watch(dioProvider)),
);

final movaChatRepositoryProvider = Provider<MovaChatRepository>(
  (ref) => MovaChatRepositoryImpl(ref.watch(movaChatApiProvider)),
);

enum MovaChatStatus { idle, loading, success, error }

class MovaChatState {
  final MovaChatStatus status;
  final MovaChatResponse? response;
  final String? errorMessage;

  const MovaChatState({
    this.status = MovaChatStatus.idle,
    this.response,
    this.errorMessage,
  });
}

class MovaChatController extends StateNotifier<MovaChatState> {
  final MovaChatRepository _repository;

  MovaChatController(this._repository) : super(const MovaChatState());

  Future<void> sendMessage(String message) async {
    if (message.trim().isEmpty) return;
    state = const MovaChatState(status: MovaChatStatus.loading);
    try {
      final response = await _repository.sendMessage(
        MovaChatRequest(message: message),
      );
      state = MovaChatState(status: MovaChatStatus.success, response: response);
    } catch (e) {
      state = MovaChatState(
        status: MovaChatStatus.error,
        errorMessage: _describeError(e),
      );
    }
  }

  // 에러 응답을 UI에 그대로 노출하지 않는다(.claude/rules/security/auth.md §6) —
  // 원시 payload 대신 짧은 안내 문장만 보여준다.
  String _describeError(Object error) {
    if (error is DioException) {
      final status = error.response?.statusCode;
      if (status == 429) return '요청이 너무 많습니다. 잠시 후 다시 시도하세요.';
      if (status != null) return '추천을 가져오지 못했습니다 (오류 코드 $status).';
      return '서버에 연결할 수 없습니다. 네트워크 상태를 확인하세요.';
    }
    return '추천을 가져오지 못했습니다.';
  }
}

final movaChatControllerProvider =
    StateNotifierProvider<MovaChatController, MovaChatState>(
      (ref) => MovaChatController(ref.watch(movaChatRepositoryProvider)),
    );
