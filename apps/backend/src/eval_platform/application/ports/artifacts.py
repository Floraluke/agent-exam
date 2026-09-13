from dataclasses import dataclass
from typing import Protocol

from eval_platform.domain.result import ArtifactRef


@dataclass(frozen=True, slots=True)
class VerifiedArtifactBody:
    content: bytes
    original_size_bytes: int
    truncated: bool


class ArtifactReader(Protocol):
    def read_verified(self, reference: ArtifactRef) -> bytes: ...

    def read_bounded_verified(
        self, reference: ArtifactRef, maximum: int
    ) -> VerifiedArtifactBody: ...


class ArtifactStore(ArtifactReader, Protocol):
    """Immutable object writes and bounded, byte-verified reads.

    Same key/content can be reused only after a real byte check. Any missing,
    corrupt or unavailable object raises ArtifactUnavailable. Never delete an
    object merely because a later database operation fails.
    """

    def put_immutable(self, reference: ArtifactRef, content: bytes) -> None: ...

    def delete_verified(self, reference: ArtifactRef) -> bool:
        """Delete one exact live object; false means it was already absent."""
        ...
