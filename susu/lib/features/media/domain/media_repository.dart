import '../data/models/photo_upload_response.dart';

abstract class MediaRepository {
  Future<PhotoUploadResponse> uploadPhoto({
    required List<int> bytes,
    required String filename,
    required String contentType,
  });
}
