"""S6a：流水线的形状、鉴权、策略与凭据——全部发生在出站之前。

本片只做"决定"：`decide()` 返回一份待发送描述，**不发送任何东西**。所以每条拒绝
都有两个断言面：固定内部码，以及"假上游自己的请求记录为空"。

第二个面在本片按构造就是真的（还没有发送方），因此本片附一条**正对照**——真的对假上游
发一次请求、计数从 0 变 1——用来证明那个计数器有区分力。否则"计数为 0"只是"还没接线"
的同义反复，而按项目规则，出站计数必须以假上游的记录为证，不能凭日志推断。

替身与固定令牌见 `support.py`。
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Iterator

import pytest

from eval_platform.adapters.execution.provider_access.budget import (
    FRAMING_ALLOWANCE_TOKENS,
)
from eval_platform.adapters.execution.provider_access.server import (
    MAX_BODY_BYTES,
    ProviderRejection,
)
from eval_platform.domain.agent import INTERNAL_TEST_UPSTREAM
from providers.contract.support.fake_responses import FakeUpstream
from providers.lifecycle.support import (
    BUDGET,
    CLIENT_TOKEN,
    FAKE_SECRET,
    MODEL,
    OTHER_RUN_TOKEN,
    RUN_ID,
    issue_binding,
    make_harness,
    owner_unverifiable,
    permissions_too_wide,
    platform_verified,
    profile_document,
    request_body,
)


@pytest.fixture
def upstream() -> Iterator[FakeUpstream]:
    with FakeUpstream() as fake:
        yield fake


def post_once(upstream: FakeUpstream) -> None:
    request = urllib.request.Request(
        upstream.base_url + "/responses",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as answer:
        answer.read()


def test_the_request_log_would_notice_a_real_call(upstream):
    """正对照：计数为 0 必须有区分力，否则它只是"没接线"的同义反复。"""

    assert upstream.request_count == 0
    post_once(upstream)
    assert upstream.request_count == 1


def test_the_injected_owner_proof_is_the_one_that_runs(tmp_path):
    """The platform proof is required, and its refusal reaches the caller unchanged."""

    make_harness(tmp_path, verify_access=platform_verified).decide()
    with pytest.raises(ProviderRejection, match="PRIVATE_ACCESS_UNVERIFIABLE"):
        make_harness(tmp_path, verify_access=owner_unverifiable).decide()
    with pytest.raises(ProviderRejection, match="PRIVATE_FILE_PERMISSIONS_TOO_WIDE"):
        make_harness(tmp_path, verify_access=permissions_too_wide).decide()


def test_only_post_to_the_responses_path_is_a_request(tmp_path):
    harness = make_harness(tmp_path)
    for method in ("GET", "HEAD", "PUT", "DELETE", "OPTIONS"):
        with pytest.raises(ProviderRejection, match="REQUEST_METHOD_NOT_ALLOWED"):
            harness.decide(method=method)
    for path in (
        "/v1/responses",
        "/",
        "/responses/extra",
        "/responses?x=1",
        "http://evil.example.com/responses",
    ):
        with pytest.raises(ProviderRejection, match="REQUEST_PATH_NOT_ALLOWED"):
            harness.decide(path=path)


def test_the_body_is_bounded_and_must_be_a_json_object(tmp_path):
    harness = make_harness(tmp_path)
    with pytest.raises(ProviderRejection, match="REQUEST_BODY_TOO_LARGE"):
        harness.decide(body=b"x" * (MAX_BODY_BYTES + 1))
    for raw in (b"", b"{", b"not json"):
        with pytest.raises(ProviderRejection, match="REQUEST_BODY_MALFORMED"):
            harness.decide(body=raw)
    for raw in (b"[]", b'"text"', b"7"):
        with pytest.raises(ProviderRejection, match="REQUEST_BODY_NOT_OBJECT"):
            harness.decide(body=raw)


def test_a_request_without_a_usable_token_is_refused(tmp_path):
    harness = make_harness(tmp_path)
    with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_UNKNOWN"):
        harness.decide(authorization=False)
    for token in ("", "guess", CLIENT_TOKEN + "x"):
        with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_UNKNOWN"):
            harness.decide(token=token)
    with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_UNKNOWN"):
        harness.decide(
            headers={"Authorization": f"Basic {CLIENT_TOKEN}"}, authorization=False
        )
    # The scheme is matched case-insensitively, so a lowercase bearer still counts.
    assert harness.decide(
        headers={"authorization": f"bearer {CLIENT_TOKEN}"}, authorization=False
    )


def test_expired_and_revoked_tokens_stop_being_tokens(tmp_path):
    now = [0.0]
    harness = make_harness(tmp_path, clock=lambda: now[0])
    harness.decide()
    now[0] = BUDGET.deadline_seconds + 1
    with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_EXPIRED"):
        harness.decide()

    revoked = make_harness(tmp_path)
    revoked.decide()
    assert revoked.registry.revoke_run(RUN_ID) is True
    with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_UNKNOWN"):
        revoked.decide()


def test_a_token_from_another_run_is_refused(tmp_path):
    """Another run's token is not a credential here, even though it is well formed."""

    harness = make_harness(tmp_path, tokens=(CLIENT_TOKEN, OTHER_RUN_TOKEN))
    issue_binding(harness.registry, run_id="run-2")
    harness.decide()
    with pytest.raises(ProviderRejection, match="PROVIDER_TOKEN_CROSS_RUN"):
        harness.decide(token=OTHER_RUN_TOKEN)


def test_the_bound_model_is_the_only_model(tmp_path):
    harness = make_harness(tmp_path)
    for model in ("kimi-k3", "gpt-5.6-terra", ""):
        with pytest.raises(ProviderRejection, match="REQUEST_MODEL_MISMATCH"):
            harness.decide(body=request_body(model=model))


def test_unknown_fields_and_unlisted_tools_are_refused_not_ignored(tmp_path):
    harness = make_harness(tmp_path)
    for extra in (
        {"base_url": "https://api.deepseek.com"},
        {"web_search": True},
        {"store": False},
        {"previous_response_id": "resp_1"},
    ):
        with pytest.raises(ProviderRejection, match="REQUEST_UNKNOWN_FIELD"):
            harness.decide(body=request_body(**extra))
    with pytest.raises(ProviderRejection, match="REQUEST_REQUIRED_FIELD_MISSING"):
        harness.decide(body={"model": MODEL, "stream": True})
    with pytest.raises(ProviderRejection, match="REQUEST_STREAM_REQUIRED"):
        harness.decide(body=request_body(stream=False))
    for tool in ("web_search", "computer_use_preview", "shell_root"):
        with pytest.raises(ProviderRejection, match="REQUEST_TOOL_NOT_ALLOWED"):
            harness.decide(body=request_body(tools=[{"type": tool}]))


def test_the_run_remainder_is_the_output_ceiling(tmp_path):
    """An allowance already spent is not spendable again by asking for it."""

    harness = make_harness(tmp_path, consumed=(0, 31_000))
    assert harness.ledger.remaining_output_tokens == 1_000
    with pytest.raises(ProviderRejection, match="REQUEST_MAX_OUTPUT_TOKENS_EXCEEDED"):
        harness.decide(body=request_body(max_output_tokens=1_001))
    assert harness.ledger.remaining_output_tokens == 1_000

    spent = make_harness(tmp_path, consumed=(0, 32_000))
    with pytest.raises(ProviderRejection, match="BUDGET_OUTPUT_EXCEEDED"):
        spent.decide()


def test_an_unknown_or_mismatched_profile_is_refused(tmp_path):
    harness = make_harness(tmp_path)
    # The positive case runs first: the loop below overwrites the profile file that
    # this harness reads, so asking it again afterwards would be asking a broken file.
    assert harness.decide().binding.run_id == RUN_ID
    with pytest.raises(ProviderRejection, match="PRIVATE_PROFILE_NOT_FOUND"):
        make_harness(tmp_path, profile_id="not-in-the-file").decide()
    for entry in (
        {"model": "kimi-k3"},
        {"provider": "deepseek"},
        {"upstream_base_url": "https://api.deepseek.com"},
        {"secret": "  "},
    ):
        with pytest.raises(ProviderRejection):
            make_harness(tmp_path, document=profile_document(**entry)).decide()


def test_a_refusal_never_carries_the_path_the_secret_or_the_token(tmp_path):
    harness = make_harness(tmp_path)
    refusals = []
    for attempt in (
        lambda: harness.decide(authorization=False),
        lambda: make_harness(
            tmp_path / "wide", verify_access=permissions_too_wide
        ).decide(),
        lambda: harness.decide(body=request_body(tools=[{"type": "web_search"}])),
    ):
        with pytest.raises(ProviderRejection) as error:
            attempt()
        refusals.append(error.value)
    for error in refusals:
        text = f"{error.internal_code} {error.failure_code} {error.failure_summary}"
        assert harness.private.name not in text
        assert str(harness.private.parent) not in text
        assert FAKE_SECRET not in text and CLIENT_TOKEN not in text


def test_a_refusal_keeps_the_ledger_untouched(tmp_path, upstream):
    harness = make_harness(tmp_path)
    for attempt in (
        lambda: harness.decide(method="GET"),
        lambda: harness.decide(path="/v1/responses"),
        lambda: harness.decide(authorization=False),
        lambda: harness.decide(body=request_body(model="kimi-k3")),
        lambda: harness.decide(body=request_body(tools=[{"type": "web_search"}])),
    ):
        with pytest.raises(ProviderRejection):
            attempt()
    assert upstream.request_count == 0
    assert harness.ledger.remaining_output_tokens == 32_000


def test_admission_holds_the_input_bound_and_the_requested_output(tmp_path):
    harness = make_harness(tmp_path)
    raw = request_body(max_output_tokens=1_000)
    admission = harness.decide(body=raw)

    compact = json.dumps(
        json.loads(raw), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert admission.reservation.input_tokens == len(compact) + FRAMING_ALLOWANCE_TOKENS
    assert admission.reservation.max_output_tokens == 1_000
    assert harness.ledger.remaining_output_tokens == 31_000


def test_an_unstated_output_ceiling_holds_the_whole_remainder(tmp_path):
    """A missing ceiling is not zero: the hold must cover the worst case."""

    harness = make_harness(tmp_path, consumed=(0, 8_000))
    admission = harness.decide(body=request_body())
    assert admission.reservation.max_output_tokens == 24_000
    assert harness.ledger.remaining_output_tokens == 0


def test_admission_swaps_the_client_credential_for_the_trusted_one(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide(headers={"Content-Type": "application/json"})

    sent = dict(admission.outbound.send_headers())
    assert sent.pop("Authorization") == f"Bearer {FAKE_SECRET}"
    assert "authorization" not in {name.lower() for name in sent}
    assert CLIENT_TOKEN not in json.dumps(sent)
    assert admission.outbound.url == f"{INTERNAL_TEST_UPSTREAM}/responses"
    assert admission.outbound.max_attempts == 1
    assert admission.outbound.follow_redirects is False


def test_the_destination_is_never_taken_from_the_request(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide(
        headers={
            "Host": "evil.example.com",
            "X-Forwarded-Host": "evil.example.com",
            "Location": "http://evil.example.com/responses",
        }
    )
    assert admission.outbound.url == f"{INTERNAL_TEST_UPSTREAM}/responses"
    assert "evil.example.com" not in admission.outbound.url


def test_no_secret_reaches_a_representation_or_a_client_header(tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide()
    for text in (repr(admission), str(admission), repr(admission.outbound)):
        assert FAKE_SECRET not in text
        assert CLIENT_TOKEN not in text
