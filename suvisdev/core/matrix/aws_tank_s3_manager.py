"""AWS S3 클라이언트를 한 객체에서 관리한다.

자격 증명(IAM 액세스 키)·리전·버킷은 Keymaker(vauly_keymaker_secret_manager)가
`.env`에서 읽어 보관한 값을 그대로 쓴다 — 시크릿은 Keymaker가 단일 관리한다.
키가 없으면 `ready=False`로 두고 클라이언트 접근 시점에 명확한 에러를 낸다.
"""

from __future__ import annotations

import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.matrix.vauly_keymaker_secret_manager import get_keymaker

logger = logging.getLogger(__name__)


class Tank:
    """Keymaker가 보관한 IAM 액세스 키로 S3 클라이언트를 제공한다."""

    def __init__(self) -> None:
        km = get_keymaker()
        self._access_key: str = km.aws_access_key_id
        self._secret_key: str = km.aws_secret_access_key
        self.region: str = km.aws_region
        self.bucket: str = km.vision_s3_bucket
        self._client = None

    @property
    def ready(self) -> bool:
        """IAM 액세스 키가 둘 다 채워졌는지."""
        return bool(self._access_key and self._secret_key)

    @property
    def client(self):
        """boto3 S3 클라이언트(캐시). 키가 없으면 RuntimeError."""
        if not self.ready:
            raise RuntimeError(
                "AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY 환경변수가 설정되지 않았습니다."
            )
        if self._client is None:
            self._client = boto3.client(
                "s3",
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self.region,
            )
        return self._client

    def list_buckets(self) -> list[str]:
        """접근 가능한 버킷 이름 목록(자격 증명 검증용)."""
        response = self.client.list_buckets()
        return [b["Name"] for b in response.get("Buckets", [])]

    def _resolve_bucket(self, bucket: str | None) -> str:
        name = (bucket or self.bucket).strip()
        if not name:
            raise RuntimeError("버킷 이름이 없습니다(VISION_S3_BUCKET 미설정).")
        return name

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        bucket: str | None = None,
    ) -> str:
        """바이트를 업로드하고 객체의 https URL을 반환한다."""
        target = self._resolve_bucket(bucket)
        try:
            self.client.put_object(Bucket=target, Key=key, Body=data, ContentType=content_type)
        except (BotoCoreError, ClientError) as e:
            logger.exception("[Tank] S3 업로드 실패 | bucket=%s key=%s", target, key)
            raise RuntimeError(f"S3 업로드 실패: {e}") from e
        return f"https://{target}.s3.{self.region}.amazonaws.com/{key}"

    def download_bytes(self, key: str, *, bucket: str | None = None) -> bytes:
        """객체를 바이트로 내려받는다."""
        target = self._resolve_bucket(bucket)
        try:
            response = self.client.get_object(Bucket=target, Key=key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as e:
            logger.exception("[Tank] S3 다운로드 실패 | bucket=%s key=%s", target, key)
            raise RuntimeError(f"S3 다운로드 실패: {e}") from e

    def generate_presigned_url(
        self,
        key: str,
        *,
        expires_in: int = 3600,
        bucket: str | None = None,
    ) -> str:
        """객체 조회용 사전 서명 URL(기본 1시간)."""
        target = self._resolve_bucket(bucket)
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": target, "Key": key},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as e:
            logger.exception("[Tank] presigned URL 생성 실패 | bucket=%s key=%s", target, key)
            raise RuntimeError(f"presigned URL 생성 실패: {e}") from e


tank = Tank()


def get_tank() -> Tank:
    return tank
