import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/network/dio_client.dart';
import '../data/media_api.dart';
import '../data/media_repository_impl.dart';
import '../data/models/photo_upload_response.dart';
import '../domain/media_repository.dart';

final mediaApiProvider = Provider<MediaApi>((ref) => MediaApi(ref.watch(dioProvider)));

final mediaRepositoryProvider = Provider<MediaRepository>(
  (ref) => MediaRepositoryImpl(ref.watch(mediaApiProvider)),
);

enum PhotoUploadStatus { idle, loading, success, error }

class PhotoUploadState {
  final PhotoUploadStatus status;
  final PhotoUploadResponse? response;
  final String? errorMessage;

  const PhotoUploadState({
    this.status = PhotoUploadStatus.idle,
    this.response,
    this.errorMessage,
  });
}

class PhotoCaptureController extends StateNotifier<PhotoUploadState> {
  final MediaRepository _repository;
  final ImagePicker _picker;

  PhotoCaptureController(this._repository, {ImagePicker? picker})
    : _picker = picker ?? ImagePicker(),
      super(const PhotoUploadState());

  /// 카메라로 촬영 → 백엔드(/api/media/photos)로 업로드. 사용자가 촬영을
  /// 취소하면 아무 상태 변화 없이 그대로 idle.
  Future<void> captureAndUpload() async {
    final photo = await _picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (photo == null) return;

    state = const PhotoUploadState(status: PhotoUploadStatus.loading);
    try {
      final bytes = await photo.readAsBytes();
      final response = await _repository.uploadPhoto(
        bytes: bytes,
        filename: photo.name,
        contentType: photo.mimeType ?? 'image/jpeg',
      );
      state = PhotoUploadState(status: PhotoUploadStatus.success, response: response);
    } catch (e) {
      state = PhotoUploadState(status: PhotoUploadStatus.error, errorMessage: _describeError(e));
    }
  }

  String _describeError(Object error) {
    if (error is DioException) {
      final status = error.response?.statusCode;
      final data = error.response?.data;
      if (status == 401) return '로그인이 만료됐습니다. 다시 로그인해주세요.';
      if (status == 400 && data is Map && data['detail'] != null) {
        return data['detail'].toString();
      }
      if (status != null) return '사진 업로드에 실패했습니다 (오류 코드 $status).';
      return '서버에 연결할 수 없습니다. 네트워크 상태를 확인하세요.';
    }
    return '사진 업로드에 실패했습니다.';
  }
}

final photoCaptureControllerProvider =
    StateNotifierProvider<PhotoCaptureController, PhotoUploadState>(
      (ref) => PhotoCaptureController(ref.watch(mediaRepositoryProvider)),
    );
