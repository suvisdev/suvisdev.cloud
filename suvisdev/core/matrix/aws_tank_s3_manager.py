"""AWS S3 클라이언트를 한 객체에서 관리한다(온프레미스 유일 S3 경로).

자격 증명은 **boto3 기본 자격증명 체인**을 따른다 — 명시적 키를 boto3에 넘기지
않고 `region_name`만 지정한다. 이렇게 하면 로컬·EC2가 단일 경로로 처리된다:
- 로컬/컨테이너: `.env`의 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`가
  `os.environ`에 있으면(Keymaker가 임포트 시 load_dotenv로 로드, compose는
  env_file로 주입) 기본 체인이 그걸 집는다.
- EC2: 인스턴스 IAM Role이 자격증명을 자동 주입 → 기본 체인이 그걸 집는다.
리전·버킷 이름은 Keymaker가 `.env`에서 읽어 보관한 값을 쓴다. 자격증명이 없으면
호출 시점에 boto3가 `NoCredentialsError`를 던진다.
"""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.matrix.vauly_keymaker_secret_manager import get_keymaker

logger = logging.getLogger(__name__)


class Tank:
    """boto3 기본 자격증명 체인으로 S3 클라이언트를 제공한다(로컬 .env / EC2 IAM Role 공통)."""

    def __init__(self) -> None:
        # get_keymaker() 임포트가 .env를 os.environ에 로드해 기본 체인이 키를 집게 한다.
        km = get_keymaker()
        self.region: str = km.aws_region
        self.bucket: str = km.vision_s3_bucket
        self._client = None

    @property
    def client(self) -> Any:
        """boto3 S3 클라이언트(캐시). 자격증명은 기본 체인이 해결하며, 없으면
        호출 시점에 boto3가 NoCredentialsError를 던진다.

        endpoint_url을 리전 전용으로 명시한다 — region_name만 주면 boto3가
        글로벌 엔드포인트(s3.amazonaws.com)로 URL을 만드는데, us-east-1이
        아닌 버킷(여기는 ap-northeast-2)은 S3가 리전 엔드포인트로 307
        리다이렉트시킨다. SigV4 서명에 Host 헤더가 포함돼 있어 리다이렉트된
        새 호스트에서는 서명이 안 맞아 presigned URL이 403으로 깨진다
        (실측: /lesson/photos 갤러리 썸네일이 전부 깨져 있던 원인).
        """
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=self.region,
                endpoint_url=f"https://s3.{self.region}.amazonaws.com",
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
            result: bytes = response["Body"].read()
            return result
        except (BotoCoreError, ClientError) as e:
            logger.exception("[Tank] S3 다운로드 실패 | bucket=%s key=%s", target, key)
            raise RuntimeError(f"S3 다운로드 실패: {e}") from e

    def list_objects(self, prefix: str, *, bucket: str | None = None) -> list[str]:
        """prefix로 시작하는 객체 key 목록(list_objects_v2, 페이지네이션 포함)."""
        target = self._resolve_bucket(bucket)
        keys: list[str] = []
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=target, Prefix=prefix):
                keys.extend(obj["Key"] for obj in page.get("Contents", []))
        except (BotoCoreError, ClientError) as e:
            logger.exception("[Tank] S3 목록 조회 실패 | bucket=%s prefix=%s", target, prefix)
            raise RuntimeError(f"S3 목록 조회 실패: {e}") from e
        return keys

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
            url: str = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": target, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except (BotoCoreError, ClientError) as e:
            logger.exception("[Tank] presigned URL 생성 실패 | bucket=%s key=%s", target, key)
            raise RuntimeError(f"presigned URL 생성 실패: {e}") from e


tank = Tank()


def get_tank() -> Tank:
    return tank
