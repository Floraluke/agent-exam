import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from eval_platform.adapters.artifacts.local import LocalArtifactReader
from eval_platform.adapters.evaluation.result_mapper import artifact
from eval_platform.adapters.execution.harbor.result_values import patch_ref
from eval_platform.application.execution.evidence import EvidencePublication
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import ArtifactRef, DeterministicResult
from jobs.execution.support.fakes import MemoryArtifacts


def test_existing_local_adapter_references_publish_as_durable_run_evidence(tmp_path):
    run_id = "5e87af1c-a652-4c64-a1a3-e454e4638ebd"
    trial = tmp_path / "harbor-trial"
    patch_dir = trial / "artifacts" / "agentexam"
    patch_dir.mkdir(parents=True)
    patch = b"diff --git a/a b/a\n"
    (patch_dir / "model.patch").write_bytes(patch)
    (patch_dir / "patch.sha256").write_text(sha256(patch).hexdigest())
    (patch_dir / "patch.bytes").write_text(str(len(patch)))
    (patch_dir / "patch.binary").write_text("0")
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    report_path = evaluator / "report.json"
    output_path = evaluator / "test_output.txt"
    private_path = evaluator / "fork.stderr.log"
    report_path.write_bytes(b'{"resolved":true,"path":"/tmp/codex-secrets"}')
    output_path.write_bytes(b"hidden_test_id sk-synthetic-secret-1234\n")
    private_path.write_bytes(b"private diagnostic\n")
    destination = MemoryArtifacts()
    publication = EvidencePublication(LocalArtifactReader(tmp_path), destination)

    normalized_patch, content = publication.prepare_patch(run_id, patch_ref(trial))
    publication.persist(normalized_patch, content)
    published = publication.publish_evaluation(
        run_id,
        DeterministicResult(
            run_id,
            True,
            True,
            artifact(report_path, tmp_path, "harness_report"),
            (
                artifact(output_path, tmp_path, "harness_log"),
                artifact(private_path, tmp_path, "harness_log"),
            ),
            {"FAIL_TO_PASS": {"success": 1, "failure": 0}},
        ),
        50 * 1024 * 1024,
    )

    assert normalized_patch.artifact_type == "agent_patch"
    assert {item.artifact_type for item in published} == {
        "harness_report",
        "harness_test_output",
    }
    assert all(item.object_key.startswith(f"runs/{run_id}/") for item in published)
    shared = b"".join(destination.content.values())
    assert b"codex-secrets" not in shared and b"hidden_test_id" not in shared
    assert b"sk-synthetic" not in shared and b"private diagnostic" not in shared


@pytest.mark.parametrize(
    "secret",
    [
        b"diff --git a/a b/a\n+token = 'sk-synthetic-secret-1234'\n",
        b"diff --git a/a b/a\n+/tmp/codex-secrets/auth.json\n",
        b"diff --git a/a b/a\n+gold_patch = 'hidden'\n",
    ],
)
def test_public_patch_rejects_synthetic_secret_and_hidden_markers(secret):
    run_id = "5e87af1c-a652-4c64-a1a3-e454e4638ebd"
    source = MemoryArtifacts()
    reference = ArtifactRef(
        "private/model.patch",
        "model_patch",
        len(secret),
        sha256(secret).hexdigest(),
        "text/x-diff",
    )
    source.content[reference.object_key] = secret

    with pytest.raises(ArtifactUnavailable):
        EvidencePublication(source, MemoryArtifacts()).prepare_patch(run_id, reference)


def test_public_patch_allows_similar_nonsecret_text():
    content = b"diff --git a/api.py b/api.py\n+token_count = 3\n"
    source = MemoryArtifacts()
    reference = ArtifactRef(
        "private/model.patch",
        "model_patch",
        len(content),
        sha256(content).hexdigest(),
        "text/x-diff",
    )
    source.content[reference.object_key] = content

    published, exact = EvidencePublication(source, MemoryArtifacts()).prepare_patch(
        "5e87af1c-a652-4c64-a1a3-e454e4638ebd", reference
    )

    assert exact == content
    assert published.size_bytes == len(content)


def test_public_derivatives_omit_messages_tool_arguments_and_hidden_test_ids():
    run_id = "5e87af1c-a652-4c64-a1a3-e454e4638ebd"
    raw = json.dumps(
        {
            "steps": [
                {
                    "step_id": 1,
                    "source": "agent",
                    "message": "private reasoning sk-synthetic-secret-1234",
                    "tool_calls": [
                        {
                            "function_name": "Read",
                            "arguments": {"path": "/tmp/codex-secrets/auth.json"},
                        }
                    ],
                }
            ]
        }
    ).encode()
    store = MemoryArtifacts()
    source = ArtifactRef(
        "private/trajectory.json",
        "agent_trajectory",
        len(raw),
        sha256(raw).hexdigest(),
        "application/json",
    )
    store.content[source.object_key] = raw
    publication = EvidencePublication(store, store)

    summary = publication.publish_test_summary(
        run_id, {"FAIL_TO_PASS": {"success": 1, "failure": 0}}
    )
    trajectory = publication.publish_trajectory(
        run_id, source, "codex", datetime(2026, 9, 12, tzinfo=UTC)
    )

    assert json.loads(store.read_verified(summary)) == {
        "FAIL_TO_PASS": {"failure": 0, "success": 1}
    }
    assert trajectory is not None
    public = store.read_verified(trajectory)
    assert b"Read" in public
    assert b"private reasoning" not in public
    assert b"codex-secrets" not in public
    assert b"sk-synthetic" not in public
