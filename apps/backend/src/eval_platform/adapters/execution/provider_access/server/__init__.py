"""Proxy process side: admission pipeline, HTTP surface and stream relay.

An internal subpackage of the execution adapter. It exposes no application-visible
port and is not imported by `delivery` or `domain`.
"""

from eval_platform.adapters.execution.provider_access.server.contracts import (
    MAX_BODY_BYTES,
    Admission,
    ProviderRejection,
    ProxyIdentity,
)
from eval_platform.adapters.execution.provider_access.server.http import build_server
from eval_platform.adapters.execution.provider_access.server.runner import (
    Relay,
    RunOutcome,
    RunRunner,
)
from eval_platform.adapters.execution.provider_access.server.service import (
    ProviderProxyService,
)

__all__ = [
    "MAX_BODY_BYTES",
    "build_server",
    "Admission",
    "ProviderProxyService",
    "ProviderRejection",
    "ProxyIdentity",
    "Relay",
    "RunOutcome",
    "RunRunner",
]
