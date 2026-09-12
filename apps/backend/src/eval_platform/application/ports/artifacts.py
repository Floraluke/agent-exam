from typing import Protocol

from eval_platform.domain.result import ArtifactRef


class ArtifactReader(Protocol):
    def read_verified(self, reference: ArtifactRef) -> bytes: ...


class ArtifactStore(ArtifactReader, Protocol):
    """Immutable object writes and bounded, byte-verified reads.

    Same key/content can be reused only after a real byte check. Any missing,
    corrupt or unavailable object raises ArtifactUnavailable. Never delete an
    object merely because a later database operation fails.
    """

    def put_immutable(self, reference: ArtifactRef, content: bytes) -> None: ...
