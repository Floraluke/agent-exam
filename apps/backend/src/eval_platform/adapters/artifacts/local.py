"""Read trusted local adapter evidence without weakening durable-store rules."""

from hashlib import sha256
from pathlib import Path

from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.result import ArtifactRef

_MAX_SOURCE_BYTES = 50 * 1024 * 1024
_SOURCE_TYPES = {
    "agent_patch",
    "model_patch",
    "harness_report",
    "harness_summary",
    "harness_log",
    "harness_test_output",
    "agent_trajectory",
}


class LocalArtifactReader:
    """Verify references emitted by trusted Harbor/Fork adapters under one root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def read_verified(self, reference: ArtifactRef) -> bytes:
        try:
            if (
                reference.retention_class != "prototype"
                or reference.artifact_type not in _SOURCE_TYPES
                or reference.size_bytes > _MAX_SOURCE_BYTES
            ):
                raise ArtifactUnavailable
            raw = Path(reference.object_key)
            path = raw if raw.is_absolute() else self.root / raw
            if path.is_symlink():
                raise ArtifactUnavailable
            resolved = path.resolve(strict=True)
            resolved.relative_to(self.root)
            if (
                not resolved.is_file()
                or resolved.stat().st_size != reference.size_bytes
            ):
                raise ArtifactUnavailable
            content = resolved.read_bytes()
            if sha256(content).hexdigest() != reference.sha256:
                raise ArtifactUnavailable
            return content
        except (OSError, RuntimeError, ValueError):
            raise ArtifactUnavailable from None
