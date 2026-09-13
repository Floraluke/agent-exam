from base64 import b64encode
from hashlib import md5, sha256
from typing import Any

from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
)

from eval_platform.adapters.artifacts.bounded import read_bounded
from eval_platform.adapters.artifacts.config import MinioConfig, create_client
from eval_platform.adapters.artifacts.policy import validate_reference
from eval_platform.application.ports.artifacts import VerifiedArtifactBody
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import ArtifactRef


class MinioArtifactStore:
    def __init__(self, client: Any, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def _client(self) -> Any:
        if self.client is None:
            try:
                config = MinioConfig.from_environment()
                client = create_client(config)
            except (ValueError, BotoCoreError):
                raise ArtifactUnavailable from None
            self.bucket, self.client = config.bucket, client
        return self.client

    def put_immutable(self, reference: ArtifactRef, content: bytes) -> None:
        self._validate(reference)
        if (
            len(content) != reference.size_bytes
            or sha256(content).hexdigest() != reference.sha256
        ):
            raise ArtifactUnavailable
        try:
            self._client().put_object(
                Bucket=self.bucket,
                Key=reference.object_key,
                Body=content,
                ContentLength=len(content),
                ContentType=reference.content_type,
                ContentMD5=b64encode(
                    md5(content, usedforsecurity=False).digest()
                ).decode(),
                IfNoneMatch="*",
            )
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") not in {
                409,
                412,
            }:
                raise ArtifactUnavailable from None
        except (BotoCoreError, OSError, ValueError):
            raise ArtifactUnavailable from None
        self.read_verified(reference)

    def read_verified(self, reference: ArtifactRef) -> bytes:
        self._validate(reference)
        stream = None
        try:
            response = self._client().get_object(
                Bucket=self.bucket, Key=reference.object_key
            )
            stream = response["Body"]
            if response["ContentLength"] != reference.size_bytes:
                raise ArtifactUnavailable
            content = bytearray()
            while chunk := stream.read(
                min(65536, reference.size_bytes + 1 - len(content))
            ):
                content.extend(chunk)
                if len(content) > reference.size_bytes:
                    raise ArtifactUnavailable
            if (
                len(content) != reference.size_bytes
                or sha256(content).hexdigest() != reference.sha256
            ):
                raise ArtifactUnavailable
            return bytes(content)
        except (ClientError, BotoCoreError, OSError, ValueError, KeyError, TypeError):
            raise ArtifactUnavailable from None
        finally:
            if stream is not None:
                stream.close()

    def read_bounded_verified(
        self, reference: ArtifactRef, maximum: int
    ) -> VerifiedArtifactBody:
        self._validate(reference)
        stream = None
        try:
            response = self._client().get_object(
                Bucket=self.bucket, Key=reference.object_key
            )
            stream = response["Body"]
            if response["ContentLength"] != reference.size_bytes:
                raise ArtifactUnavailable
            return read_bounded(stream, reference.size_bytes, reference.sha256, maximum)
        except (ClientError, BotoCoreError, OSError, ValueError, KeyError, TypeError):
            raise ArtifactUnavailable from None
        finally:
            if stream is not None:
                stream.close()

    def delete_verified(self, reference: ArtifactRef) -> bool:
        self._validate(reference)
        if reference.retention_class != "raw_30d":
            raise ArtifactUnavailable
        try:
            self._client().head_object(Bucket=self.bucket, Key=reference.object_key)
        except ClientError as exc:
            if _missing(exc):
                return False
            raise ArtifactUnavailable from None
        except (BotoCoreError, OSError, ValueError):
            raise ArtifactUnavailable from None
        self.read_verified(reference)
        try:
            self._client().delete_object(
                Bucket=self.bucket,
                Key=reference.object_key,
            )
            self._client().head_object(Bucket=self.bucket, Key=reference.object_key)
        except ClientError as exc:
            if _missing(exc):
                return True
            raise ArtifactUnavailable from None
        except (BotoCoreError, OSError, ValueError):
            raise ArtifactUnavailable from None
        raise ArtifactUnavailable

    @staticmethod
    def _validate(reference: ArtifactRef) -> None:
        validate_reference(reference)


def _missing(error: ClientError) -> bool:
    code = error.response.get("Error", {}).get("Code")
    status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return status == 404 or code in {"404", "NoSuchKey", "NotFound"}
