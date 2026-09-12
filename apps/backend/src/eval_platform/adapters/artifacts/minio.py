from base64 import b64encode
from hashlib import md5, sha256
from typing import Any
from uuid import UUID

from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
)

from eval_platform.adapters.artifacts.config import MinioConfig, create_client
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import ArtifactRef

_MAX_SNAPSHOT = 50 * 1024 * 1024


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

    @staticmethod
    def _validate(reference: ArtifactRef) -> None:
        task_snapshot = (
            reference.artifact_type == "task_source_snapshot"
            and reference.content_type == "application/json"
            and reference.object_key.startswith("tasks/")
        )
        run_types = {
            "agent_patch": ("text/x-diff", 1024 * 1024),
            "harness_report": ("application/json", _MAX_SNAPSHOT),
            "harness_summary": ("application/json", _MAX_SNAPSHOT),
            "harness_test_output": ("text/plain", _MAX_SNAPSHOT),
            "public_test_summary": ("application/json", _MAX_SNAPSHOT),
            "public_trajectory": ("application/x-ndjson", _MAX_SNAPSHOT),
        }
        run_artifact = _valid_run_reference(reference, run_types)
        if (
            (not task_snapshot and not run_artifact)
            or reference.retention_class != "long_term"
            or reference.deleted_at is not None
            or reference.truncated
            or not 0 <= reference.size_bytes <= _MAX_SNAPSHOT
        ):
            raise ArtifactUnavailable


def _valid_run_reference(
    reference: ArtifactRef, types: dict[str, tuple[str, int]]
) -> bool:
    contract = types.get(reference.artifact_type)
    parts = reference.object_key.split("/")
    if contract is None or len(parts) != 4:
        return False
    try:
        run_id = str(UUID(parts[1]))
    except ValueError:
        return False
    content_type, maximum = contract
    return (
        parts == ["runs", run_id, reference.artifact_type, reference.sha256]
        and reference.content_type == content_type
        and reference.size_bytes <= maximum
    )
