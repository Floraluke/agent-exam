import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class MinioConfig:
    endpoint: str
    bucket: str
    access_key: str = field(repr=False)
    secret_key: str = field(repr=False)

    def __post_init__(self) -> None:
        endpoint = urlsplit(self.endpoint)
        if (
            not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.path
            or endpoint.query
            or endpoint.fragment
            or (
                endpoint.scheme != "https"
                and not (endpoint.scheme == "http" and endpoint.hostname == "127.0.0.1")
            )
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", self.bucket)
            or not self.access_key
            or not self.secret_key
        ):
            raise ValueError(
                "MinIO requires an explicit private endpoint and credentials"
            )

    @classmethod
    def from_environment(cls) -> "MinioConfig":
        return cls(
            *(
                os.environ.get("AGENTEXAM_MINIO_" + key, "")
                for key in (
                    "ENDPOINT",
                    "BUCKET",
                    "ACCESS_KEY",
                    "SECRET_KEY",
                )
            )
        )


def create_client(config: MinioConfig):  # type: ignore[no-untyped-def]
    return boto3.session.Session().client(
        "s3",
        endpoint_url=config.endpoint,
        aws_access_key_id=config.access_key,
        aws_secret_access_key=config.secret_key,
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            connect_timeout=3,
            read_timeout=5,
            retries={"mode": "standard", "total_max_attempts": 1},
            proxies={},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            s3={"addressing_style": "path", "payload_signing_enabled": True},
        ),
    )
