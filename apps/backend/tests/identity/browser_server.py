"""Explicitly gated synthetic HTTP server for browser wiring tests only."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from identity.memory import MemoryIdentityRepository

if os.environ.get("AGENTEXAM_IDENTITY_BROWSER_TEST") != "1":
    raise RuntimeError("Synthetic identity server requires the browser-test gate")


def browser_clock():
    clock_file = (
        Path(__file__).resolve().parents[4] / "runtime/tests/identity-browser-clock.txt"
    )
    try:
        offset = int(clock_file.read_text(encoding="ascii"))
    except FileNotFoundError:
        offset = 0
    if not 0 <= offset <= 28800:
        raise ValueError("Browser-test clock offset is outside the test boundary")
    return datetime.now(UTC) + timedelta(seconds=offset)


service = IdentityService(MemoryIdentityRepository(), Argon2Passwords(), browser_clock)
service.bootstrap_owner("owner", "synthetic browser password")
app = create_app(
    service,
    HttpConfig(public_origin="https://127.0.0.1:3100"),
)
