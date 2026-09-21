"""Race-resistant reading for an owner-verified private file."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path

from eval_platform.adapters.execution.provider_access.failures import (
    ProviderAccessError,
)


def read_verified(
    path: Path, *, max_bytes: int, verify_access: Callable[[Path], None]
) -> bytes:
    try:
        initial = path.lstat()
    except OSError:
        raise ProviderAccessError("PRIVATE_FILE_UNREADABLE") from None
    if not stat.S_ISREG(initial.st_mode):
        raise ProviderAccessError("PRIVATE_FILE_NOT_REGULAR")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise ProviderAccessError("PRIVATE_FILE_UNREADABLE") from None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ProviderAccessError("PRIVATE_FILE_NOT_REGULAR")
        if before.st_size > max_bytes:
            raise ProviderAccessError("PRIVATE_FILE_TOO_LARGE")
        try:
            verify_access(path)
        except OSError:
            raise ProviderAccessError("PRIVATE_FILE_CHANGED") from None
        _require_same_file(path, before)
        payload = os.read(descriptor, max_bytes + 1)
        after = os.fstat(descriptor)
        if _signature(before) != _signature(after):
            raise ProviderAccessError("PRIVATE_FILE_CHANGED")
        _require_same_file(path, after)
        if len(payload) > max_bytes:
            raise ProviderAccessError("PRIVATE_FILE_TOO_LARGE")
        return payload
    finally:
        os.close(descriptor)


def _require_same_file(path: Path, opened: os.stat_result) -> None:
    try:
        current = path.lstat()
    except OSError:
        raise ProviderAccessError("PRIVATE_FILE_CHANGED") from None
    if _signature(current) != _signature(opened):
        raise ProviderAccessError("PRIVATE_FILE_CHANGED")


def _signature(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
    )
