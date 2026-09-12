import os
from uuid import uuid4

import pytest

from eval_platform.adapters.artifacts.config import MinioConfig, create_client
from eval_platform.adapters.artifacts.minio import MinioArtifactStore


@pytest.fixture
def job_minio_sandbox():
    if os.environ.get("AGENTEXAM_RUN_JOB_MINIO") != "1":
        pytest.skip("专属 Job MinIO 集成未显式启用")
    config = MinioConfig.from_environment()
    if (
        config.endpoint != "http://127.0.0.1:9000"
        or not config.access_key.startswith("ae_test_")
        or config.bucket != "agentexam-synthetic-test"
    ):
        pytest.fail("拒绝非专属 Job 对象存储测试配置", pytrace=False)
    client = create_client(config)
    bucket = "ae-job-test-" + uuid4().hex
    client.create_bucket(Bucket=bucket)
    try:
        yield MinioArtifactStore(client, bucket), client, bucket
    finally:
        contents = client.list_objects_v2(Bucket=bucket).get("Contents", [])
        for item in contents:
            client.delete_object(Bucket=bucket, Key=item["Key"])
        client.delete_bucket(Bucket=bucket)
