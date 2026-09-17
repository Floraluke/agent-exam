import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import boto3
import pytest
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
from eval_platform.adapters.artifacts.config import MinioConfig, create_client
from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.domain.result import ArtifactRef

PASSWORD_FILE = Path(r"D:\AgentExamData\private\minio-app-password")
BUCKET = "agentexam-private"
ENDPOINT = "http://127.0.0.1:59000"


def _raw_reference(content: bytes) -> ArtifactRef:
    created = datetime(2026, 9, 17, tzinfo=UTC)
    digest = sha256(content).hexdigest()
    return ArtifactRef(
        f"runs/{uuid4()}/agent_trajectory/{digest}",
        "agent_trajectory",
        len(content),
        digest,
        "application/json",
        "raw_30d",
        created_at=created,
        original_filename="permission-check.json",
        original_size_bytes=len(content),
        expires_at=created + timedelta(days=30),
    )


def _assert_access_denied(call) -> None:
    with pytest.raises(ClientError) as caught:
        call()
    assert caught.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403


def test_application_identity_has_only_required_private_object_access():
    if os.environ.get("AGENTEXAM_RUN_LOCAL_DEPLOYMENT") != "1":
        pytest.skip("真实本机对象存储检查未显式启用")

    secret = PASSWORD_FILE.read_text(encoding="utf-8")
    client = create_client(MinioConfig(ENDPOINT, BUCKET, "agentexam-app", secret))
    anonymous = boto3.session.Session().client(
        "s3",
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
        config=Config(
            signature_version=UNSIGNED,
            connect_timeout=3,
            read_timeout=5,
            retries={"mode": "standard", "total_max_attempts": 1},
            proxies={},
            s3={"addressing_style": "path"},
        ),
    )
    content = b'{"agentexam":"synthetic-permission-check"}'
    reference = _raw_reference(content)
    store = MinioArtifactStore(client, BUCKET)

    try:
        store.put_immutable(reference, content)
        assert store.read_verified(reference) == content
        _assert_access_denied(
            lambda: anonymous.get_object(Bucket=BUCKET, Key=reference.object_key)
        )
        _assert_access_denied(client.list_buckets)
        _assert_access_denied(lambda: client.list_objects_v2(Bucket=BUCKET))
        assert store.delete_verified(reference) is True
    finally:
        client.delete_object(Bucket=BUCKET, Key=reference.object_key)
