"""Explicitly gated synthetic HTTP server for browser wiring tests only."""

import os

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.app import create_app
from eval_platform.delivery.http.config import HttpConfig
from identity.memory import MemoryIdentityRepository

if os.environ.get("AGENTEXAM_IDENTITY_BROWSER_TEST") != "1":
    raise RuntimeError("Synthetic identity server requires the browser-test gate")

service = IdentityService(MemoryIdentityRepository(), Argon2Passwords())
service.bootstrap_owner("owner", "synthetic browser password")
app = create_app(
    service,
    HttpConfig(public_origin="http://127.0.0.1:3100", allow_insecure_loopback=True),
)
