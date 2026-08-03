import 'package:dio/dio.dart';

import 'models/photo_upload_response.dart';

/// suvisdev/apps/media/router.py — POST /api/media/photos. 로그인(카카오 모바일
/// JWT) 필요 — Authorization 헤더는 dio_client.dart 인터셉터가 자동으로 싣는다.
class MediaApi {
  final Dio _dio;

  const MediaApi(this._dio);

  Future<PhotoUploadResponse> uploadPhoto({
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        bytes,
        filename: filename,
        contentType: DioMediaType.parse(contentType),
      ),
    });
    final resp = await _dio.post('/api/media/photos', data: formData);
    return PhotoUploadResponse.fromJson(resp.data as Map<String, dynamic>);
  }
}
