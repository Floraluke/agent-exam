from hashlib import sha256
from io import BytesIO
from uuid import uuid4

import pytest
from botocore.response import StreamingBody

from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import ArtifactRef


def run_reference(content: bytes, kind: str = "agent_patch") -> ArtifactRef:
    run_id, digest = str(uuid4()), sha256(content).hexdigest()
    content_type = {
        "agent_patch": "text/x-diff",
        "public_test_summary": "application/json",
        "public_trajectory": "application/x-ndjson",
    }[kind]
    return ArtifactRef(
        f"runs/{run_id}/{kind}/{digest}",
        kind,
        len(content),
        digest,
        content_type,
        "long_term",
    )


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, **values):
        key, body = values["Key"], values["Body"]
        if key in self.objects:
            error = {
                "Error": {"Code": "PreconditionFailed"},
                "ResponseMetadata": {"HTTPStatusCode": 412},
            }
            from botocore.exceptions import ClientError

            raise ClientError(error, "PutObject")
        self.objects[key] = body

    def get_object(self, **values):
        content = self.objects[values["Key"]]
        return {
            "Body": StreamingBody(BytesIO(content), len(content)),
            "ContentLength": len(content),
        }


class ShortReadS3(FakeS3):
    def get_object(self, **values):
        response = super().get_object(**values)
        response["ContentLength"] += 1
        return response


def test_minio_accepts_only_verified_run_artifact_contract():
    content = b"diff --git a/a b/a\n"
    reference = run_reference(content)
    store = MinioArtifactStore(FakeS3(), "synthetic-bucket")
    store.put_immutable(reference, content)
    assert store.read_verified(reference) == content

    invalid = ArtifactRef(
        reference.object_key.replace("runs/", "private/"),
        reference.artifact_type,
        reference.size_bytes,
        reference.sha256,
        reference.content_type,
        "long_term",
    )
    with pytest.raises(ArtifactUnavailable):
        store.put_immutable(invalid, content)


def test_minio_rejects_a_truncated_public_trajectory():
    content = b'{"sequence":1}\n'
    reference = run_reference(content, "public_trajectory")
    client = ShortReadS3()
    client.objects[reference.object_key] = content
    with pytest.raises(ArtifactUnavailable):
        MinioArtifactStore(client, "synthetic-bucket").read_verified(reference)


@pytest.mark.integration
def test_real_minio_run_evidence_is_immutable_and_missing_is_not_empty(
    job_minio_sandbox,
):
    store, service, bucket = job_minio_sandbox
    content = b"diff --git a/a b/a\n"
    reference = run_reference(content)
    store.put_immutable(reference, content)
    store.put_immutable(reference, content)
    assert store.read_verified(reference) == content
    service.delete_object(Bucket=bucket, Key=reference.object_key)
    with pytest.raises(ArtifactUnavailable):
        store.read_verified(reference)
