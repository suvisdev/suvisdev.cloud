import '../domain/media_repository.dart';
import 'media_api.dart';
import 'models/photo_upload_response.dart';

class MediaRepositoryImpl implements MediaRepository {
  final MediaApi _api;

  const MediaRepositoryImpl(this._api);

  @override
  Future<PhotoUploadResponse> uploadPhoto({
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) {
    return _api.uploadPhoto(bytes: bytes, filename: filename, contentType: contentType);
  }
}
