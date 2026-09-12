from __future__ import annotations

import json
import os
import signal
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from eval_platform.adapters.execution.harbor.artifacts import RAW_ARTIFACT_MAX_BYTES
from eval_platform.adapters.execution.harbor.lifecycle.process_wait import wait_bounded
from eval_platform.adapters.execution.harbor.process_evidence import (
    CapturedLog,
    LogCaptureSession,
    write_log,
)
from eval_platform.adapters.execution.redaction import Redactor

_CLEANUP_TIMEOUT_SEC = 5
_LOG_CAPTURE_TIMEOUT_SEC = 5
_TIMEOUT_EXIT_CODE = 124


@dataclass(frozen=True, slots=True)
class ProcessOutcome:
    returncode: int
    timed_out: bool
    stdout: CapturedLog
    stderr: CapturedLog
    warnings: tuple[str, ...]
    start_error: OSError | None = None


def run_bounded_process(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_sec: int | float,
    evidence_root: Path,
    max_log_bytes: int = RAW_ARTIFACT_MAX_BYTES,
    redactions: tuple[bytes, ...] = (),
    on_poll: Callable[[], None] | None = None,
) -> ProcessOutcome:
    if timeout_sec <= 0 or max_log_bytes < 0:
        raise ValueError("Process limits must be valid")
    redactor = Redactor(redactions)
    stdout_path = evidence_root / "harbor.stdout.log"
    stderr_path = evidence_root / "harbor.stderr.log"
    try:
        process = _start_process(command, cwd, env)
    except OSError as error:
        stdout = write_log(stdout_path, b"", max_log_bytes)
        message = f"{type(error).__name__}: {error}".encode("utf-8", errors="replace")
        stderr = write_log(stderr_path, message, max_log_bytes, redactor=redactor)
        safe_error = error
        if redactions:
            safe_error = type(error)(
                b"".join(
                    redactor.filter((str(error).encode("utf-8", "replace"),))
                ).decode("utf-8", "replace")
            )
        start_warnings = ["HARBOR_PROCESS_START_FAILED"]
        _add_truncation_warnings(start_warnings, stdout, stderr)
        outcome = ProcessOutcome(
            -1, False, stdout, stderr, tuple(start_warnings), safe_error
        )
        _write_manifest(evidence_root, outcome, max_log_bytes)
        return outcome

    assert process.stdout is not None and process.stderr is not None
    capture = LogCaptureSession.start(
        process.stdout, process.stderr, evidence_root, max_log_bytes, redactor=redactor
    )
    warnings: list[str] = []
    timed_out = False
    try:
        timed_out = wait_bounded(process, timeout_sec, on_poll)
        if timed_out:
            warnings.append("HARBOR_PROCESS_TIMEOUT")
            warnings.extend(_terminate_process_tree(process))
    except Exception:
        _terminate_process_tree(process)
        capture.finish(timeout_sec=_LOG_CAPTURE_TIMEOUT_SEC)
        raise
    stdout, stderr, incomplete_logs = capture.finish(
        timeout_sec=_LOG_CAPTURE_TIMEOUT_SEC
    )
    if incomplete_logs:
        warnings.append("HARBOR_LOG_CAPTURE_INCOMPLETE")
    _add_truncation_warnings(warnings, stdout, stderr)
    returncode = (
        _TIMEOUT_EXIT_CODE
        if timed_out
        else process.returncode
        if process.returncode is not None
        else -1
    )
    outcome = ProcessOutcome(returncode, timed_out, stdout, stderr, tuple(warnings))
    _write_manifest(evidence_root, outcome, max_log_bytes)
    return outcome


def _start_process(
    command: Sequence[str], cwd: Path, env: Mapping[str, str]
) -> subprocess.Popen[bytes]:
    if os.name == "nt":
        return subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> tuple[str, ...]:
    if process.poll() is not None:
        return ()
    failed = False
    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=_CLEANUP_TIMEOUT_SEC,
                check=False,
            )
            failed = completed.returncode != 0
        else:
            posix_os = cast(Any, os)
            posix_signal = cast(Any, signal)
            posix_os.killpg(posix_os.getpgid(process.pid), posix_signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        failed = True
    if failed and process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=_CLEANUP_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        failed = True
        process.kill()
        process.wait(timeout=_CLEANUP_TIMEOUT_SEC)
    return ("HARBOR_PROCESS_TREE_CLEANUP_FAILED",) if failed else ()


def _add_truncation_warnings(
    warnings: list[str], stdout: CapturedLog, stderr: CapturedLog
) -> None:
    if stdout.truncated:
        warnings.append("HARBOR_STDOUT_TRUNCATED")
    if stderr.truncated:
        warnings.append("HARBOR_STDERR_TRUNCATED")


def _write_manifest(root: Path, outcome: ProcessOutcome, max_bytes: int) -> None:
    value = {
        "returncode": outcome.returncode,
        "timed_out": outcome.timed_out,
        "start_error_type": type(outcome.start_error).__name__
        if outcome.start_error is not None
        else None,
        "warnings": list(outcome.warnings),
        "logs": {
            "stdout": _log_value(outcome.stdout, max_bytes),
            "stderr": _log_value(outcome.stderr, max_bytes),
        },
    }
    (root / "harbor-process.json").write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )


def _log_value(log: CapturedLog, max_bytes: int) -> dict[str, object]:
    return {
        "file": log.path.name,
        "max_bytes": max_bytes,
        "saved_bytes": log.saved_bytes,
        "truncated": log.truncated,
    }
