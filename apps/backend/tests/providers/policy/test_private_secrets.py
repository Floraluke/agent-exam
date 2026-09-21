from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from eval_platform.adapters.execution.provider_access.secrets import (
    MAX_BYTES,
    STRUCTURE_VERSION,
    PrivateProfile,
    load_profile,
    owner_only_verifier,
)
from eval_platform.domain.agent import INTERNAL_TEST_PROVIDER, INTERNAL_TEST_UPSTREAM

FAKE_KEY = "sk-fake-0000-not-a-real-credential"
POSIX = hasattr(os, "geteuid")


def allow(path: Path) -> None:
    return None


def document(**overrides: object) -> bytes:
    entry = {
        "provider": INTERNAL_TEST_PROVIDER,
        "model": "deepseek-flash",
        "upstream_base_url": INTERNAL_TEST_UPSTREAM,
        "secret": FAKE_KEY,
    }
    entry.update(overrides)
    return json.dumps(
        {"version": STRUCTURE_VERSION, "profiles": {"run-a": entry}}
    ).encode()


def write(tmp_path: Path, payload: bytes, name: str = "providers.json") -> Path:
    target = tmp_path / name
    target.write_bytes(payload)
    return target


def test_loads_the_single_requested_profile(tmp_path):
    profile = load_profile(write(tmp_path, document()), "run-a", verify_access=allow)
    assert isinstance(profile, PrivateProfile)
    assert (profile.provider, profile.model) == (
        INTERNAL_TEST_PROVIDER,
        "deepseek-flash",
    )
    assert profile.upstream_base_url == INTERNAL_TEST_UPSTREAM


def test_secret_is_excluded_from_the_representation(tmp_path):
    profile = load_profile(write(tmp_path, document()), "run-a", verify_access=allow)
    assert FAKE_KEY not in repr(profile)
    assert FAKE_KEY not in str(profile)


def test_missing_and_non_regular_targets_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="PRIVATE_FILE_UNREADABLE"):
        load_profile(tmp_path / "absent.json", "run-a", verify_access=allow)
    with pytest.raises(ValueError, match="PRIVATE_FILE_NOT_REGULAR"):
        load_profile(tmp_path, "run-a", verify_access=allow)


def test_sync_location_is_rejected_before_reading(tmp_path):
    synced = tmp_path / "OneDrive" / "secrets"
    synced.mkdir(parents=True)
    target = write(synced, document())
    with pytest.raises(ValueError, match="PRIVATE_FILE_IN_SYNC_LOCATION"):
        load_profile(target, "run-a", verify_access=allow)


def test_symlinked_component_is_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    write(real, document())
    link = tmp_path / "linked"
    try:
        link.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("This platform cannot create a directory symlink")
    with pytest.raises(ValueError, match="PRIVATE_FILE_SYMLINK_COMPONENT"):
        load_profile(link / "providers.json", "run-a", verify_access=allow)


def test_oversized_file_is_rejected_before_parsing(tmp_path):
    oversized = document()
    oversized += b" " * (MAX_BYTES + 1 - len(oversized))
    with pytest.raises(ValueError, match="PRIVATE_FILE_TOO_LARGE"):
        load_profile(write(tmp_path, oversized), "run-a", verify_access=allow)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"not json", "PRIVATE_FILE_MALFORMED"),
        (b'{"version": 99, "profiles": {}}', "PRIVATE_FILE_STRUCTURE_INVALID"),
        (
            json.dumps({"version": STRUCTURE_VERSION}).encode(),
            "PRIVATE_FILE_STRUCTURE_INVALID",
        ),
        (document(), "PRIVATE_PROFILE_NOT_FOUND"),
    ],
)
def test_structure_rejections(tmp_path, payload, code):
    profile_id = "missing" if code == "PRIVATE_PROFILE_NOT_FOUND" else "run-a"
    with pytest.raises(ValueError, match=code):
        load_profile(write(tmp_path, payload), profile_id, verify_access=allow)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        (
            "upstream_base_url",
            "http://fake-upstream.t05.invalid",
            "PRIVATE_UPSTREAM_NOT_REGISTERED",
        ),
        (
            "upstream_base_url",
            "https://evil.example.com",
            "PRIVATE_UPSTREAM_NOT_REGISTERED",
        ),
        ("secret", "   ", "PRIVATE_FILE_STRUCTURE_INVALID"),
        ("model", "", "PRIVATE_FILE_STRUCTURE_INVALID"),
        ("provider", 7, "PRIVATE_FILE_STRUCTURE_INVALID"),
    ],
)
def test_profile_field_rejections(tmp_path, field, value, code):
    payload = document(**{field: value})
    with pytest.raises(ValueError, match=code):
        load_profile(write(tmp_path, payload), "run-a", verify_access=allow)


def test_error_messages_never_echo_the_path_or_the_secret(tmp_path):
    target = write(tmp_path, document(secret=""))
    with pytest.raises(ValueError) as failure:
        load_profile(target, "run-a", verify_access=allow)
    message = str(failure.value)
    assert str(target) not in message and tmp_path.name not in message
    assert FAKE_KEY not in message
    assert message.isupper() or message.replace("_", "").isalpha()


def test_verifier_rejection_propagates_without_loading(tmp_path):
    def deny(path: Path) -> None:
        raise ValueError("PRIVATE_FILE_PERMISSIONS_TOO_WIDE")

    with pytest.raises(ValueError, match="PRIVATE_FILE_PERMISSIONS_TOO_WIDE"):
        load_profile(write(tmp_path, document()), "run-a", verify_access=deny)


def test_file_replacement_during_access_verification_is_rejected(tmp_path):
    target = write(tmp_path, document())
    replacement = write(
        tmp_path,
        document(secret="sk-fake-replacement-not-a-real-credential"),
        "replacement.json",
    )

    def swap(path: Path) -> None:
        replacement.replace(path)

    with pytest.raises(ValueError, match="PRIVATE_FILE_CHANGED"):
        load_profile(target, "run-a", verify_access=swap)


@pytest.mark.skipif(not POSIX, reason="POSIX owner/permission bits only")
def test_owner_only_verifier_accepts_a_private_file_and_rejects_wide_bits(tmp_path):
    target = write(tmp_path, document())
    target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    owner_only_verifier(target)
    target.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IROTH)
    with pytest.raises(ValueError, match="PRIVATE_FILE_PERMISSIONS_TOO_WIDE"):
        owner_only_verifier(target)


def test_owner_only_verifier_fails_closed_where_posix_bits_are_unavailable(tmp_path):
    if POSIX:
        pytest.skip("This platform exposes POSIX owner bits")
    with pytest.raises(ValueError, match="PRIVATE_ACCESS_UNVERIFIABLE"):
        owner_only_verifier(write(tmp_path, document()))
