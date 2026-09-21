"""Owner-private provider file validation. Never returns or logs key material.

Field authority: the private file is the owner-selected location described in
the authentication contract section 4.1. This module only decides whether that
file may be trusted; it does not create it and does not accept a key from any
caller. Every rejection raises a fixed code without echoing the path or value.
"""

from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

MAX_BYTES = 64 * 1024
STRUCTURE_VERSION = 1
PROFILE_ID = re.compile(r"[a-z][a-z0-9-]{1,31}")
# Candidate; the registered presets live in delivery/catalog_presets.py and are
# synced here in S8. An arbitrary host must never be accepted from the file.
REGISTERED_UPSTREAMS = {
    "deepseek": "https://api.deepseek.com",
    "kimi": "https://api.moonshot.cn/v1",
}
_SYNC_MARKERS = (
    "onedrive",
    "dropbox",
    "google drive",
    "googledrive",
    "syncthing",
    "icloud",
    "坚果云",
    "百度网盘",
)


@dataclass(frozen=True, slots=True)
class PrivateProfile:
    """One logical provider binding; the secret is excluded from repr."""

    profile_id: str
    provider: str
    model: str
    upstream_base_url: str
    secret: str = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not PROFILE_ID.fullmatch(self.profile_id):
            raise ValueError("PRIVATE_PROFILE_ID_INVALID")
        if not self.provider.strip() or not self.model.strip():
            raise ValueError("PRIVATE_PROFILE_IDENTITY_EMPTY")
        if REGISTERED_UPSTREAMS.get(self.provider) != self.upstream_base_url:
            raise ValueError("PRIVATE_UPSTREAM_NOT_REGISTERED")
        if not self.secret.strip():
            raise ValueError("PRIVATE_SECRET_EMPTY")


def owner_only_verifier(path: Path) -> None:
    """POSIX owner-only check; fails closed where the platform cannot prove it."""

    if not hasattr(os, "geteuid"):
        raise ValueError("PRIVATE_ACCESS_UNVERIFIABLE")
    info = path.stat()
    if info.st_uid != os.geteuid():
        raise ValueError("PRIVATE_FILE_OWNER_MISMATCH")
    if info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ValueError("PRIVATE_FILE_PERMISSIONS_TOO_WIDE")


def load_profile(
    path: Path,
    profile_id: str,
    *,
    verify_access: Callable[[Path], None],
) -> PrivateProfile:
    """Return the single requested profile, or fail closed.

    ``verify_access`` carries the platform-specific owner/ACL decision and has
    no default, so a caller cannot obtain a profile without stating how the
    private file was proven owner-only.
    """

    _reject_sync_location(path)
    _reject_symlink_components(path)
    info = _stat_regular_file(path)
    if info.st_size > MAX_BYTES:
        raise ValueError("PRIVATE_FILE_TOO_LARGE")
    verify_access(path)
    return _parse(path.read_bytes(), profile_id)


def _reject_sync_location(path: Path) -> None:
    parts = [part.lower() for part in path.absolute().parts]
    if any(marker in part for part in parts for marker in _SYNC_MARKERS):
        raise ValueError("PRIVATE_FILE_IN_SYNC_LOCATION")


def _reject_symlink_components(path: Path) -> None:
    current = path.absolute()
    for candidate in (current, *current.parents):
        if candidate.is_symlink():
            raise ValueError("PRIVATE_FILE_SYMLINK_COMPONENT")


def _stat_regular_file(path: Path) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError:
        raise ValueError("PRIVATE_FILE_UNREADABLE") from None
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("PRIVATE_FILE_NOT_REGULAR")
    return info


def _parse(payload: bytes, profile_id: str) -> PrivateProfile:
    if not PROFILE_ID.fullmatch(profile_id):
        raise ValueError("PRIVATE_PROFILE_ID_INVALID")
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("PRIVATE_FILE_MALFORMED") from None
    if not isinstance(document, dict) or document.get("version") != STRUCTURE_VERSION:
        raise ValueError("PRIVATE_FILE_STRUCTURE_INVALID")
    profiles = document.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("PRIVATE_FILE_STRUCTURE_INVALID")
    if profile_id not in profiles:
        raise ValueError("PRIVATE_PROFILE_NOT_FOUND")
    entry = profiles[profile_id]
    if not isinstance(entry, Mapping):
        raise ValueError("PRIVATE_FILE_STRUCTURE_INVALID")
    return PrivateProfile(
        profile_id=profile_id,
        provider=_text(entry, "provider"),
        model=_text(entry, "model"),
        upstream_base_url=_text(entry, "upstream_base_url"),
        secret=_text(entry, "secret"),
    )


def _text(entry: Mapping[str, Any], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("PRIVATE_FILE_STRUCTURE_INVALID")
    return value


def freeze_profiles(profiles: Mapping[str, PrivateProfile]) -> Mapping[str, Any]:
    """Immutable view for callers that need the loaded identity without secrets."""

    return MappingProxyType(
        {key: (value.provider, value.model) for key, value in profiles.items()}
    )
