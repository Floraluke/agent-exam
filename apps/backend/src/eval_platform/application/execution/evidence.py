"""Normalize trusted adapter outputs into durable, public-safe run evidence."""

import json
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from hashlib import sha256

from eval_platform.application.execution.public_evidence import (
    normalize_test_summary,
    normalize_trajectory,
    validate_public_text,
)
from eval_platform.application.execution.raw_evidence import publish_raw
from eval_platform.application.ports.artifacts import ArtifactReader, ArtifactStore
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import ArtifactRef, DeterministicResult


class EvidencePublication:
    def __init__(
        self,
        source: ArtifactReader,
        destination: ArtifactStore,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.source = source
        self.destination = destination
        self.clock = clock

    def publish_raw(
        self,
        run_id: str,
        sources: Iterable[ArtifactRef],
        artifact_limit: int,
        run_limit: int,
    ) -> tuple[tuple[ArtifactRef, ...], tuple[str, ...]]:
        return publish_raw(
            self.source,
            self.destination,
            self.clock,
            run_id,
            sources,
            artifact_limit,
            run_limit,
        )

    def prepare_patch(
        self, run_id: str, reference: ArtifactRef
    ) -> tuple[ArtifactRef, bytes]:
        if reference.artifact_type not in {"model_patch", "agent_patch"}:
            raise ValueError("Execution patch evidence has an unsupported type")
        content = self.source.read_verified(reference)
        validate_public_text(content)
        return self._reference(
            run_id, "agent_patch", "text/x-diff", reference, content
        ), content

    def persist(self, reference: ArtifactRef, content: bytes) -> None:
        self.destination.put_immutable(reference, content)
        self.destination.read_verified(reference)

    def publish_evaluation(
        self,
        run_id: str,
        result: DeterministicResult,
    ) -> tuple[ArtifactRef, ...]:
        report, logs = result.report_ref, result.log_refs
        if report.artifact_type not in {"harness_report", "harness_summary"}:
            raise ValueError("Evaluator report evidence has an unsupported type")
        self.source.read_verified(report)
        summary = normalize_test_summary(result.tests_status_summary or {})
        report_body = json.dumps(
            {
                "patch_successfully_applied": result.patch_applied,
                "resolved": result.resolved,
                "tests_status_summary": json.loads(summary),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        published = [
            self._publish_derived(
                run_id, report.artifact_type, "application/json", report_body
            )
        ]
        outputs = [item for item in logs if self._is_test_output(item)]
        if len(outputs) > 1:
            raise ValueError("Evaluator returned multiple test outputs")
        if outputs:
            self.source.read_verified(outputs[0])
            output = b"Deterministic test counts are stored in tests_status_summary.\n"
            published.append(
                self._publish_derived(
                    run_id, "harness_test_output", "text/plain", output
                )
            )
        return tuple(published)

    def publish_test_summary(
        self, run_id: str, summary: dict[str, object]
    ) -> ArtifactRef:
        content = normalize_test_summary(summary)
        return self._publish_derived(
            run_id, "public_test_summary", "application/json", content
        )

    def publish_trajectory(
        self,
        run_id: str,
        source: ArtifactRef | None,
        agent_source: str,
        occurred_at: datetime,
    ) -> ArtifactRef | None:
        if source is None:
            return None
        if source.artifact_type != "agent_trajectory":
            raise ArtifactUnavailable
        content = normalize_trajectory(
            self.source.read_verified(source), agent_source, occurred_at
        )
        return self._publish_derived(
            run_id, "public_trajectory", "application/x-ndjson", content
        )

    def _publish_derived(
        self, run_id: str, kind: str, content_type: str, content: bytes
    ) -> ArtifactRef:
        digest = sha256(content).hexdigest()
        reference = ArtifactRef(
            f"runs/{run_id}/{kind}/{digest}",
            kind,
            len(content),
            digest,
            content_type,
            "long_term",
            created_at=self.clock(),
        )
        self.persist(reference, content)
        return reference

    def _publish(
        self, run_id: str, kind: str, content_type: str, source: ArtifactRef
    ) -> ArtifactRef:
        content = self.source.read_verified(source)
        reference = self._reference(run_id, kind, content_type, source, content)
        self.persist(reference, content)
        return reference

    @staticmethod
    def _reference(
        run_id: str,
        kind: str,
        content_type: str,
        source: ArtifactRef,
        content: bytes,
    ) -> ArtifactRef:
        digest = sha256(content).hexdigest()
        if len(content) != source.size_bytes or digest != source.sha256:
            raise ArtifactUnavailable
        return ArtifactRef(
            f"runs/{run_id}/{kind}/{digest}",
            kind,
            len(content),
            digest,
            content_type,
            "long_term",
            created_at=source.created_at or datetime.now(UTC),
            warnings=source.warnings,
        )

    @staticmethod
    def _is_test_output(reference: ArtifactRef) -> bool:
        if reference.artifact_type == "harness_test_output":
            return True
        name = reference.object_key.replace("\\", "/").rsplit("/", 1)[-1]
        return reference.artifact_type == "harness_log" and name == "test_output.txt"
