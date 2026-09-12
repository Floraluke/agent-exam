from hashlib import sha256

from eval_platform.application.ports.evaluator import EvaluationError
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import (
    ArtifactRef,
    DeterministicResult,
    ExecutionTrialResult,
    ResourceSummary,
    TerminationReason,
    UsageSummary,
)


class MemoryArtifacts:
    def __init__(self):
        self.content = {}

    def put_immutable(self, reference, content):
        assert len(content) == reference.size_bytes
        assert sha256(content).hexdigest() == reference.sha256
        previous = self.content.setdefault(reference.object_key, content)
        if previous != content:
            raise AssertionError("immutable object overwritten")

    def read_verified(self, reference):
        try:
            content = self.content[reference.object_key]
        except KeyError:
            raise ArtifactUnavailable from None
        assert len(content) == reference.size_bytes
        assert sha256(content).hexdigest() == reference.sha256
        return content


def artifact(store, run_id, kind, content, content_type):
    digest = sha256(content).hexdigest()
    reference = ArtifactRef(
        f"runs/{run_id}/{kind}/{digest}",
        kind,
        len(content),
        digest,
        content_type,
        "long_term",
    )
    store.put_immutable(reference, content)
    return reference


class Backend:
    def __init__(self, store, patch):
        self.store, self.patch, self.requests = store, patch, []

    def execute(self, request, progress=None):
        self.requests.append(request)
        results = []
        for index, run in enumerate(request.runs, 1):
            if progress is not None:
                progress.trial_started(run.run_id)
            patch = artifact(
                self.store, run.run_id, "agent_patch", self.patch, "text/x-diff"
            )
            result = ExecutionTrialResult(
                run.run_id,
                "harbor-job-one",
                f"harbor-trial-{index}",
                TerminationReason.COMPLETED,
                patch,
                None,
                usage=UsageSummary(11, 2, 3, 0.01),
                resource_summary=ResourceSummary(1.5, 0.5, 4096),
            )
            if progress is not None:
                progress.trial_finished(run.run_id)
            results.append(result)
        return tuple(results)


class Evaluator:
    def __init__(self, store):
        self.store, self.requests = store, []

    def evaluate(self, request):
        self.requests.append(request)
        patch_exists = bool(request.model_patch)
        report = artifact(
            self.store,
            request.run_id,
            "harness_report" if patch_exists else "harness_summary",
            b'{"resolved":true}' if patch_exists else b'{"resolved":false}',
            "application/json",
        )
        outputs = ()
        if patch_exists:
            outputs = (
                artifact(
                    self.store,
                    request.run_id,
                    "harness_test_output",
                    b"1 passed\n",
                    "text/plain",
                ),
            )
        return DeterministicResult(
            request.run_id,
            patch_exists,
            patch_exists,
            report,
            outputs,
            {"FAIL_TO_PASS": {"success": 1, "failure": 0}},
            125,
        )


class FailingEvaluator(Evaluator):
    def __init__(self, store, failed_runs):
        super().__init__(store)
        self.failed_runs = set(failed_runs)

    def evaluate(self, request):
        if request.run_id in self.failed_runs:
            raise EvaluationError("HARNESS_FAILED", "synthetic evaluator failure")
        return super().evaluate(request)


class FailedBackend:
    def execute(self, request, progress=None):
        run_id = request.runs[0].run_id
        if progress is not None:
            progress.trial_started(run_id)
        result = ExecutionTrialResult(
            run_id,
            "harbor-job-one",
            "harbor-trial-one",
            TerminationReason.AGENT_FAILED,
            None,
            None,
        )
        if progress is not None:
            progress.trial_finished(run_id)
        return (result,)
