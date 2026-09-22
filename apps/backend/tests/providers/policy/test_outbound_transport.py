from __future__ import annotations

import pytest

from eval_platform.adapters.execution.provider_access.transport import (
    OutboundRequest as Request,
)
from eval_platform.adapters.execution.provider_access.transport import (
    build_outbound,
)
from eval_platform.domain.agent import INTERNAL_TEST_PROVIDER, INTERNAL_TEST_UPSTREAM

FAKE_KEY = "sk-fake-0000-not-a-real-credential"
BODY = {"model": "deepseek-flash", "stream": True, "input": "repair the test"}


def build(**overrides: object) -> Request:
    arguments: dict[str, object] = {
        "provider": INTERNAL_TEST_PROVIDER,
        "body": BODY,
        "client_headers": {"Content-Type": "application/json"},
        "secret": FAKE_KEY,
    }
    arguments.update(overrides)
    return build_outbound(**arguments)  # type: ignore[arg-type]


def test_the_destination_comes_from_the_registry_not_the_request():
    assert build().url == f"{INTERNAL_TEST_UPSTREAM}/responses"


def test_client_input_cannot_move_the_destination():
    for header in ("Host", "X-Forwarded-Host", "Location"):
        with pytest.raises(ValueError, match="REQUEST_HEADER_NOT_ALLOWED"):
            build(client_headers={header: "evil.example.com"})


def test_client_authentication_is_stripped_and_replaced_by_the_trusted_side():
    request = build(
        client_headers={
            "Authorization": "Bearer sk-fake-client",
            "api-key": "sk-fake-client",
            "Accept": "text/event-stream",
        }
    )
    assert request.send_headers()["Authorization"] == f"Bearer {FAKE_KEY}"
    assert "sk-fake-client" not in repr(request.headers)
    assert request.headers["Accept"] == "text/event-stream"


def test_retry_and_redirect_are_structurally_refused():
    base = {
        "url": f"{INTERNAL_TEST_UPSTREAM}/responses",
        "headers": {},
        "payload": b"{}",
        "authorization": "Bearer fake",
    }
    with pytest.raises(ValueError, match="TRANSPORT_RETRY_NOT_PERMITTED"):
        Request(**{**base, "max_attempts": 2})
    with pytest.raises(ValueError, match="TRANSPORT_REDIRECT_NOT_PERMITTED"):
        Request(**{**base, "follow_redirects": True})
    request = build()
    assert request.max_attempts == 1 and request.follow_redirects is False


def test_a_plaintext_upstream_is_refused():
    with pytest.raises(ValueError, match="TRANSPORT_UPSTREAM_NOT_ENCRYPTED"):
        Request(
            url="http://fake-upstream.t05.invalid/responses",
            headers={},
            payload=b"{}",
            authorization="Bearer fake",
        )


def test_the_payload_and_credential_never_appear_in_a_representation():
    request = build(body={**BODY, "input": FAKE_KEY})
    for rendered in (repr(request), str(request), repr(request.headers)):
        assert FAKE_KEY not in rendered
    assert "repair the test" not in repr(request)


def test_the_credential_is_held_apart_from_the_client_headers():
    request = build()
    assert FAKE_KEY not in repr(request.headers)
    assert request.send_headers()["Authorization"] == f"Bearer {FAKE_KEY}"
    with pytest.raises(ValueError, match="TRANSPORT_CREDENTIAL_EMPTY"):
        Request(
            url=f"{INTERNAL_TEST_UPSTREAM}/responses",
            headers={},
            payload=b"{}",
            authorization=" ",
        )


def test_the_safe_summary_reports_shapes_and_sizes_only():
    request = build(body={**BODY, "input": FAKE_KEY})
    summary = request.safe_summary()
    assert summary["method"] == "POST"
    assert summary["url"] == f"{INTERNAL_TEST_UPSTREAM}/responses"
    assert summary["header_names"] == ("Authorization", "Content-Type")
    assert summary["payload_bytes"] == len(request.payload)
    rendered = repr(dict(summary))
    assert FAKE_KEY not in rendered
    assert "Bearer" not in rendered
    assert "repair the test" not in rendered


def test_only_registered_providers_can_be_called():
    with pytest.raises(ValueError, match="TRANSPORT_PROVIDER_UNREGISTERED"):
        build(provider="openai")
    with pytest.raises(ValueError, match="TRANSPORT_PROVIDER_UNREGISTERED"):
        build(provider="https://evil.example.com")


def test_an_empty_credential_and_an_unserializable_body_are_refused():
    with pytest.raises(ValueError, match="TRANSPORT_CREDENTIAL_EMPTY"):
        build(secret="   ")
    with pytest.raises(ValueError, match="TRANSPORT_PAYLOAD_NOT_SERIALIZABLE"):
        build(body={"input": object()})


def test_the_payload_is_serialized_deterministically():
    first = build(body={"b": 1, "a": 2})
    second = build(body={"a": 2, "b": 1})
    assert first.payload == second.payload == b'{"a":2,"b":1}'
