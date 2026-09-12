from hashlib import sha256
from io import BytesIO

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import ArtifactRef


def reference(content=b"fixed snapshot"):
    return ArtifactRef(
        "tasks/test/snapshot.json",
        "task_source_snapshot",
        len(content),
        sha256(content).hexdigest(),
        "application/json",
        "long_term",
    )


def client():
    return boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:59999",
        region_name="us-east-1",
        aws_access_key_id="synthetic-access",
        aws_secret_access_key="synthetic-secret",
    )


def test_object_read_checks_actual_bytes_and_closes_stream():
    s3 = client()
    stream = BytesIO(b"changed bytes!")
    with Stubber(s3) as stub:
        stub.add_response(
            "get_object",
            {
                "Body": StreamingBody(stream, 14),
                "ContentLength": 14,
            },
        )
        store = MinioArtifactStore(s3, "synthetic-bucket")
        with pytest.raises(ArtifactUnavailable):
            store.read_verified(reference())
    assert stream.closed


@pytest.mark.integration
def test_real_minio_concurrent_writers_cannot_replace_first_content(minio_sandbox):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    store, _, _ = minio_sandbox
    barrier = Barrier(2, timeout=10)
    choices = [b"first possible snapshot", b"second possible snapshot"]

    def put(content):
        barrier.wait()
        try:
            store.put_immutable(reference(content), content)
            return content
        except ArtifactUnavailable:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(put, choices))
    winners = [item for item in results if item is not None]
    assert len(winners) == 1
    winner = winners[0]
    assert store.read_verified(reference(winner)) == winner
    store.put_immutable(reference(winner), winner)
    assert store.read_verified(reference(winner)) == winner


@pytest.mark.integration
def test_real_minio_missing_and_corrupted_objects_fail_closed(minio_sandbox):
    store, service, bucket = minio_sandbox
    content = b"fixed snapshot"
    expected = reference(content)
    store.put_immutable(expected, content)
    service.delete_object(Bucket=bucket, Key=expected.object_key)
    with pytest.raises(ArtifactUnavailable):
        store.read_verified(expected)
    # Synthetic external fault, not the adapter's supported write operation.
    service.put_object(Bucket=bucket, Key=expected.object_key, Body=b"changed bytes!")
    with pytest.raises(ArtifactUnavailable):
        store.read_verified(expected)


@pytest.mark.parametrize(
    "status,code", [(404, "NoSuchKey"), (503, "ServiceUnavailable")]
)
def test_missing_or_unavailable_object_is_a_safe_dependency_error(status, code):
    s3 = client()
    with Stubber(s3) as stub:
        stub.add_client_error(
            "get_object", service_error_code=code, http_status_code=status
        )
        with pytest.raises(ArtifactUnavailable):
            MinioArtifactStore(s3, "synthetic-bucket").read_verified(reference())


def test_conditional_reentry_verifies_existing_bytes():
    s3 = client()
    content = b"fixed snapshot"
    stream = BytesIO(content)
    with Stubber(s3) as stub:
        stub.add_client_error(
            "put_object", service_error_code="PreconditionFailed", http_status_code=412
        )
        stub.add_response(
            "get_object",
            {
                "Body": StreamingBody(stream, len(content)),
                "ContentLength": len(content),
            },
        )
        store = MinioArtifactStore(s3, "synthetic-bucket")
        store.put_immutable(reference(), content)
    assert stream.closed
