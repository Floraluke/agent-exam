import json
from pathlib import Path

POLICY_PATH = Path(__file__).parents[1] / "local" / "minio-app-policy.json"


def test_application_policy_is_limited_to_private_bucket_objects():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    assert policy["Version"] == "2012-10-17"
    assert policy["Statement"] == [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
            ],
            "Resource": "arn:aws:s3:::agentexam-private/*",
        }
    ]
