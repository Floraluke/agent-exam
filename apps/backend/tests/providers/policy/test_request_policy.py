from __future__ import annotations

from types import MappingProxyType

import pytest

from eval_platform.adapters.execution.provider_access.request_policy import (
    PATH,
    RequestPolicy,
    check_request,
    strip_client_auth,
)

POLICY = RequestPolicy(
    model="deepseek-flash", max_output_tokens=32000, allowed_tools=frozenset({"shell"})
)


def body(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": "deepseek-flash",
        "stream": True,
        "input": "repair the failing test",
    }
    payload.update(overrides)
    return payload


def check(**overrides: object):
    arguments = {"method": "POST", "path": PATH, "body": body()}
    arguments.update(overrides)
    return check_request(POLICY, **arguments)


def test_admits_the_observed_request_shape():
    result = check(body=body(max_output_tokens=1000))
    assert isinstance(result, MappingProxyType)
    assert result["model"] == "deepseek-flash"
    assert result["stream"] is True
    with pytest.raises(TypeError):
        result["model"] = "other"  # type: ignore[index]


def test_rejects_anything_that_is_not_the_fixed_endpoint():
    with pytest.raises(ValueError, match="REQUEST_METHOD_NOT_ALLOWED"):
        check(method="GET")
    for path in ("/v1/responses", "/responses?stream=true", "/responses/x", "/"):
        with pytest.raises(ValueError, match="REQUEST_PATH_NOT_ALLOWED"):
            check(path=path)


def test_rejects_an_absolute_url_and_odd_bodies():
    with pytest.raises(ValueError, match="REQUEST_PATH_NOT_ALLOWED"):
        check(path="https://api.deepseek.com/responses")
    for malformed in ([], "input", None, {1: "x"}):
        with pytest.raises(ValueError, match="REQUEST_BODY_NOT_OBJECT"):
            check(body=malformed)


def test_rejects_unknown_and_missing_fields():
    with pytest.raises(ValueError, match="REQUEST_UNKNOWN_FIELD"):
        check(body=body(base_url="https://evil.example.com"))
    with pytest.raises(ValueError, match="REQUEST_UNKNOWN_FIELD"):
        check(body=body(web_search=True))
    with pytest.raises(ValueError, match="REQUEST_REQUIRED_FIELD_MISSING"):
        check(body={"model": "deepseek-flash", "stream": True})
    with pytest.raises(ValueError, match="REQUEST_REQUIRED_FIELD_MISSING"):
        check(body={"input": "x", "stream": True})


def test_rejects_a_model_other_than_the_bound_one():
    with pytest.raises(ValueError, match="REQUEST_MODEL_MISMATCH"):
        check(body=body(model="kimi-k3"))


def test_requires_streaming_and_a_non_empty_input():
    for stream in (False, None, "true"):
        with pytest.raises(ValueError, match="REQUEST_STREAM_REQUIRED"):
            check(body=body(stream=stream))
    with pytest.raises(ValueError, match="REQUEST_STREAM_REQUIRED"):
        check(body={"model": "deepseek-flash", "input": "x"})
    for empty in ("", "   ", [], ()):
        with pytest.raises(ValueError, match="REQUEST_INPUT_EMPTY"):
            check(body=body(input=empty))
    with pytest.raises(ValueError, match="REQUEST_INPUT_INVALID"):
        check(body=body(input=7))


def test_output_ceiling_is_enforced_without_truncating():
    assert check(body=body(max_output_tokens=32000))["max_output_tokens"] == 32000
    with pytest.raises(ValueError, match="REQUEST_MAX_OUTPUT_TOKENS_EXCEEDED"):
        check(body=body(max_output_tokens=32001))
    for invalid in (0, -1, "32000", True):
        with pytest.raises(ValueError, match="REQUEST_MAX_OUTPUT_TOKENS_INVALID"):
            check(body=body(max_output_tokens=invalid))


def test_only_registered_tool_types_are_admitted():
    assert check(body=body(tools=[]))["tools"] == []
    assert check(body=body(tools=[{"type": "shell"}]))["tools"]
    with pytest.raises(ValueError, match="REQUEST_TOOL_NOT_ALLOWED"):
        check(body=body(tools=[{"type": "web_search"}]))
    with pytest.raises(ValueError, match="REQUEST_TOOL_NOT_ALLOWED"):
        check(body=body(tools=[{"type": "computer_use_preview"}]))
    for malformed in ([{"name": "shell"}], ["shell"], [{"type": 7}], {"type": "shell"}):
        with pytest.raises(ValueError, match="REQUEST_TOOLS_INVALID"):
            check(body=body(tools=malformed))


def test_client_authentication_is_stripped_case_insensitively():
    stripped = strip_client_auth(
        {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-fake-client-value",
            "API-KEY": "sk-fake-client-value",
            "Accept": "text/event-stream",
        }
    )
    assert stripped == {"Accept": "text/event-stream"}
    assert "sk-fake-client-value" not in repr(stripped)


def test_client_routing_headers_never_reach_the_fixed_upstream():
    for name in ("Host", "X-Forwarded-Host", "Forwarded", "Proxy-Connection"):
        with pytest.raises(ValueError, match="REQUEST_HEADER_NOT_ALLOWED"):
            strip_client_auth({name: "attacker.invalid", "Accept": "text/event-stream"})


def test_policy_rejects_an_unusable_configuration():
    with pytest.raises(ValueError, match="REQUEST_POLICY_MODEL_EMPTY"):
        RequestPolicy(model="  ", max_output_tokens=10, allowed_tools=frozenset())
    with pytest.raises(ValueError, match="REQUEST_POLICY_CEILING_INVALID"):
        RequestPolicy(model="m", max_output_tokens=0, allowed_tools=frozenset())
    with pytest.raises(ValueError, match="REQUEST_POLICY_TOOLS_NOT_IMMUTABLE"):
        RequestPolicy(model="m", max_output_tokens=1, allowed_tools={"shell"})  # type: ignore[arg-type]
