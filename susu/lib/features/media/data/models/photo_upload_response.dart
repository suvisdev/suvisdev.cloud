/// suvisdev/apps/media/schemas.py의 PhotoUploadResponse와 필드명을 그대로 맞춘다.
class PhotoUploadResponse {
  final String key;
  final String url;
  final int sizeBytes;
  final String contentType;

  const PhotoUploadResponse({
    required this.key,
    required this.url,
    required this.sizeBytes,
    required this.contentType,
  });

  factory PhotoUploadResponse.fromJson(Map<String, dynamic> json) {
    return PhotoUploadResponse(
      key: json['key'] as String,
      url: json['url'] as String,
      sizeBytes: json['size_bytes'] as int,
      contentType: json['content_type'] as String,
    );
  }
}
