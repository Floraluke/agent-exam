"""Run-bound access tokens for the isolated proxy.

A token is bound to exactly one run, one provider and one model, and it carries
the run's deadline and ledger. It is deliberately *not* single-use: one run
contains many model requests, so the same token legitimately appears repeatedly
until the run ends. What must never happen is a token crossing to another run,
outliving its deadline, or surviving revocation, so all three checks live here
rather than in the request path.

Tokens are excluded from every representation, and the registry never exposes
them again after issue.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from secrets import token_urlsafe

from eval_platform.adapters.execution.provider_access.budget import RunBudget
from eval_platform.adapters.execution.provider_access.secrets import (
    REGISTERED_UPSTREAMS,
)

TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class RunBinding:
    """One run's limited access capability; the token stays out of repr."""

    run_id: str
    provider: str
    model: str
    expires_at: float
    budget: RunBudget
    token: str = field(repr=False, compare=False)


class TokenRegistry:
    """Issues, resolves and revokes run bindings under a single lock."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock
        self._token_factory = token_factory or (lambda: token_urlsafe(TOKEN_BYTES))
        self._lock = threading.Lock()
        self._by_token: dict[str, RunBinding] = {}
        self._by_run: dict[str, str] = {}

    def issue(
        self,
        *,
        run_id: str,
        provider: str,
        model: str,
        ttl_seconds: float,
        budget: RunBudget,
    ) -> RunBinding:
        """Create the single binding for a run; a run cannot hold two tokens."""

        if not run_id.strip() or not model.strip():
            raise ValueError("PROVIDER_BINDING_IDENTITY_EMPTY")
        if provider not in REGISTERED_UPSTREAMS:
            raise ValueError("PROVIDER_UNREGISTERED")
        if ttl_seconds <= 0:
            raise ValueError("PROVIDER_BINDING_TTL_INVALID")
        with self._lock:
            if run_id in self._by_run:
                raise ValueError("PROVIDER_BINDING_ALREADY_ISSUED")
            token = self._token_factory()
            if not token or token in self._by_token:
                raise ValueError("PROVIDER_TOKEN_NOT_UNIQUE")
            binding = RunBinding(
                run_id=run_id,
                provider=provider,
                model=model,
                expires_at=self._clock() + ttl_seconds,
                budget=budget,
                token=token,
            )
            self._by_token[token] = binding
            self._by_run[run_id] = token
            return binding

    def resolve(self, token: str, *, run_id: str) -> RunBinding:
        """Return the binding for this token and run, or fail closed."""

        with self._lock:
            binding = self._by_token.get(token)
            if binding is None:
                raise ValueError("PROVIDER_TOKEN_UNKNOWN")
            if binding.run_id != run_id:
                raise ValueError("PROVIDER_TOKEN_CROSS_RUN")
            if self._clock() >= binding.expires_at:
                self._forget(binding)
                raise ValueError("PROVIDER_TOKEN_EXPIRED")
            return binding

    def revoke(self, token: str) -> bool:
        """Drop one token; returns whether it was still held."""

        with self._lock:
            binding = self._by_token.get(token)
            if binding is None:
                return False
            self._forget(binding)
            return True

    def revoke_run(self, run_id: str) -> bool:
        """End-of-run revocation; returns whether a token was still held."""

        with self._lock:
            token = self._by_run.get(run_id)
            if token is None:
                return False
            self._forget(self._by_token[token])
            return True

    def active_run_ids(self) -> tuple[str, ...]:
        """Run identities only; tokens are never listed."""

        with self._lock:
            return tuple(sorted(self._by_run))

    def _forget(self, binding: RunBinding) -> None:
        self._by_token.pop(binding.token, None)
        self._by_run.pop(binding.run_id, None)
