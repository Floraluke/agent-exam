"""Shared bounded read that still hashes every source byte."""

from collections import deque
from hashlib import sha256
from typing import BinaryIO

from eval_platform.application.ports.artifacts import VerifiedArtifactBody
from eval_platform.domain.catalog import ArtifactUnavailable


def read_bounded(
    stream: BinaryIO,
    expected_size: int,
    expected_sha256: str,
    maximum: int,
) -> VerifiedArtifactBody:
    if maximum < 128 or expected_size < 0:
        raise ArtifactUnavailable
    truncated = expected_size > maximum
    marker = (
        b"\n[AGENTEXAM_RAW_ARTIFACT_TRUNCATED original_size_bytes="
        + str(expected_size).encode("ascii")
        + b"]\n"
        if truncated
        else b""
    )
    head_limit = expected_size if not truncated else (maximum - len(marker)) // 2
    tail_limit = 0 if not truncated else maximum - len(marker) - head_limit
    head = bytearray()
    tail: deque[bytes] = deque()
    tail_size = total = 0
    digest = sha256()
    while chunk := stream.read(65536):
        digest.update(chunk)
        total += len(chunk)
        if len(head) < head_limit:
            head.extend(chunk[: head_limit - len(head)])
        if tail_limit:
            tail.append(chunk)
            tail_size += len(chunk)
            while tail and tail_size - len(tail[0]) >= tail_limit:
                tail_size -= len(tail.popleft())
    if total != expected_size or digest.hexdigest() != expected_sha256:
        raise ArtifactUnavailable
    if not truncated:
        return VerifiedArtifactBody(bytes(head), total, False)
    suffix = b"".join(tail)[-tail_limit:]
    content = bytes(head) + marker + suffix
    if len(content) != maximum:
        raise ArtifactUnavailable
    return VerifiedArtifactBody(content, total, True)
