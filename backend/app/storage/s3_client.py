"""Cliente de armazenamento de objetos (S3-compatible: AWS S3, MinIO, etc.)."""
from __future__ import annotations

from app.config import get_settings


def get_s3_client():
    import boto3

    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


def upload_file(local_path: str, bucket: str, key: str) -> str:
    client = get_s3_client()
    client.upload_file(local_path, bucket, key)
    return f"s3://{bucket}/{key}"
