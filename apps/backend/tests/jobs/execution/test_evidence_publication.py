from hashlib import sha256

from eval_platform.adapters.artifacts.local import LocalArtifactReader
from eval_platform.adapters.evaluation.result_mapper import artifact
from eval_platform.adapters.execution.harbor.result_values import patch_ref
from eval_platform.application.execution.evidence import EvidencePublication
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
    report_path.write_bytes(b'{"resolved":true}')
    output_path.write_bytes(b"1 passed\n")
    private_path.write_bytes(b"private diagnostic\n")
    publication = EvidencePublication(LocalArtifactReader(tmp_path), MemoryArtifacts())

    normalized_patch, content = publication.prepare_patch(run_id, patch_ref(trial))
    publication.persist(normalized_patch, content)
    published = publication.publish_evaluation(
        run_id,
        artifact(report_path, tmp_path, "harness_report"),
        (
            artifact(output_path, tmp_path, "harness_log"),
            artifact(private_path, tmp_path, "harness_log"),
        ),
    )

    assert normalized_patch.artifact_type == "agent_patch"
    assert {item.artifact_type for item in published} == {
        "harness_report",
        "harness_test_output",
    }
    assert all(item.object_key.startswith(f"runs/{run_id}/") for item in published)
