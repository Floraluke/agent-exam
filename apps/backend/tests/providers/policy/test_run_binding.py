from __future__ import annotations

import pytest

from eval_platform.adapters.execution.provider_access.binding import (
    RunBinding,
    TokenRegistry,
)
from eval_platform.adapters.execution.provider_access.budget import RunBudget
from eval_platform.domain.agent import INTERNAL_TEST_PROVIDER

BUDGET = RunBudget(
    input_tokens_limit=300_000, output_tokens_limit=32_000, deadline_seconds=900
)


def registry(clock=None, token_factory=None) -> TokenRegistry:
    arguments: dict[str, object] = {}
    if clock is not None:
        arguments["clock"] = clock
    if token_factory is not None:
        arguments["token_factory"] = token_factory
    return TokenRegistry(**arguments)


def issue(
    subject: TokenRegistry, run_id: str = "run-1", **overrides: object
) -> RunBinding:
    arguments: dict[str, object] = {
        "run_id": run_id,
        "provider": INTERNAL_TEST_PROVIDER,
        "model": "deepseek-flash",
        "ttl_seconds": 900.0,
        "budget": BUDGET,
    }
    arguments.update(overrides)
    return subject.issue(**arguments)  # type: ignore[arg-type]


def test_a_binding_keeps_its_token_out_of_every_representation():
    binding = issue(registry())
    assert binding.token and binding.token not in repr(binding)
    assert binding.token not in str(binding)


def test_the_same_token_serves_the_whole_run_not_a_single_request():
    subject = registry()
    binding = issue(subject)
    for _ in range(5):
        assert subject.resolve(binding.token, run_id="run-1") is binding


def test_a_token_cannot_cross_to_another_run():
    subject = registry()
    first = issue(subject, "run-1")
    issue(subject, "run-2")
    with pytest.raises(ValueError, match="PROVIDER_TOKEN_CROSS_RUN"):
        subject.resolve(first.token, run_id="run-2")


def test_unknown_tokens_are_rejected():
    subject = registry()
    issue(subject)
    for token in ("", "not-a-token", "guess"):
        with pytest.raises(ValueError, match="PROVIDER_TOKEN_UNKNOWN"):
            subject.resolve(token, run_id="run-1")


def test_expiry_is_enforced_and_the_binding_is_dropped():
    ticks = iter([0.0, 0.0, 901.0, 901.0])
    subject = registry(clock=lambda: next(ticks))
    binding = issue(subject)
    assert subject.resolve(binding.token, run_id="run-1") is binding
    with pytest.raises(ValueError, match="PROVIDER_TOKEN_EXPIRED"):
        subject.resolve(binding.token, run_id="run-1")
    with pytest.raises(ValueError, match="PROVIDER_TOKEN_UNKNOWN"):
        subject.resolve(binding.token, run_id="run-1")
    assert subject.active_run_ids() == ()


def test_revocation_by_token_and_by_run():
    subject = registry()
    first = issue(subject, "run-1")
    second = issue(subject, "run-2")
    assert subject.revoke(first.token) is True
    assert subject.revoke(first.token) is False
    with pytest.raises(ValueError, match="PROVIDER_TOKEN_UNKNOWN"):
        subject.resolve(first.token, run_id="run-1")
    assert subject.resolve(second.token, run_id="run-2") is second
    assert subject.revoke_run("run-2") is True
    assert subject.revoke_run("run-2") is False
    assert subject.active_run_ids() == ()


def test_a_run_holds_exactly_one_token_and_only_run_ids_are_listed():
    subject = registry()
    binding = issue(subject, "run-1")
    issue(subject, "run-2")
    with pytest.raises(ValueError, match="PROVIDER_BINDING_ALREADY_ISSUED"):
        issue(subject, "run-1")
    listed = subject.active_run_ids()
    assert listed == ("run-1", "run-2")
    assert binding.token not in repr(listed)


def test_only_registered_providers_receive_a_binding():
    for provider in ("openai", "anthropic", "unknown"):
        with pytest.raises(ValueError, match="PROVIDER_UNREGISTERED"):
            issue(registry(), provider=provider)
    assert issue(registry(), provider=INTERNAL_TEST_PROVIDER).provider == (
        INTERNAL_TEST_PROVIDER
    )


def test_binding_identity_and_ttl_are_validated():
    with pytest.raises(ValueError, match="PROVIDER_BINDING_IDENTITY_EMPTY"):
        issue(registry(), run_id="  ")
    with pytest.raises(ValueError, match="PROVIDER_BINDING_IDENTITY_EMPTY"):
        issue(registry(), model="")
    with pytest.raises(ValueError, match="PROVIDER_BINDING_TTL_INVALID"):
        issue(registry(), ttl_seconds=0)


def test_a_repeated_factory_token_is_refused_instead_of_overwriting():
    subject = registry(token_factory=lambda: "fixed-token")
    issue(subject, "run-1")
    with pytest.raises(ValueError, match="PROVIDER_TOKEN_NOT_UNIQUE"):
        issue(subject, "run-2")
    assert subject.active_run_ids() == ("run-1",)


def test_the_binding_carries_the_run_budget():
    binding = issue(registry())
    assert binding.budget is BUDGET
