"""契约层：假 Responses 上游本身的行为与取证能力。

这一层不接真实代理，也不接固定 CLI；它保证"假上游"这个**证据来源**可靠：
出站计数真的来自它自己的请求记录、脚本化的故障真的按脚本返回、事件序列可被解析。
事件名是候选词表（见 support/responses_events.py 的说明），与固定 CLI 的对账在 S2 复核。
"""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest

from providers.contract.support.fake_responses import FAKE_USAGE, FakeUpstream, Script

PLAIN_REQUEST = {
    "model": "deepseek-flash",
    "stream": True,
    "input": [{"role": "user", "content": "hello"}],
}


def read_stream(url: str, body: dict, token: str = "FAKE-T05-SENTINEL") -> list[str]:
    request = urllib.request.Request(
        url + "/responses",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return [
            line.removeprefix("data: ")
            for line in response.read().decode().splitlines()
            if line.startswith("data: ")
        ]


def events_of(lines: list[str]) -> list[dict]:
    return [json.loads(line) for line in lines]


@pytest.fixture
def upstream() -> Iterator[FakeUpstream]:
    with FakeUpstream() as fake:
        yield fake


def test_text_answer_streams_a_parsable_sequence(upstream):
    upstream.script(Script(text="FAKE-ANSWER"))
    lines = read_stream(upstream.base_url, PLAIN_REQUEST)
    events = events_of(lines)
    types = [event["type"] for event in events]
    assert types[0] == "response.created"
    assert types[-1] == "response.completed"
    assert events[-1]["response"]["usage"] == FAKE_USAGE
    assert "FAKE-ANSWER" in json.dumps(events)


def test_tool_call_lets_the_caller_continue_the_loop(upstream):
    upstream.script(Script(tool="shell", arguments='{"command":"ls"}'))
    events = events_of(read_stream(upstream.base_url, PLAIN_REQUEST))
    call = next(
        event["item"]
        for event in events
        if event["type"] == "response.output_item.done"
        and event["item"]["type"] == "function_call"
    )
    assert call["name"] == "shell"
    assert call["call_id"]


def test_completion_without_usage_is_expressible(upstream):
    """Unknown usage is a case the proxy must fail closed on, so it must be possible."""
    upstream.script(Script(usage=None))
    events = events_of(read_stream(upstream.base_url, PLAIN_REQUEST))
    assert events[-1]["type"] == "response.completed"
    assert events[-1]["response"]["usage"] is None


def test_incomplete_answer_ends_on_incomplete_not_completed(upstream):
    upstream.script(Script(incomplete_reason="max_output_tokens"))
    lines = read_stream(upstream.base_url, PLAIN_REQUEST)
    assert [event["type"] for event in events_of(lines)] == ["response.incomplete"]


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_scripted_error_statuses_are_returned_as_themselves(upstream, status):
    upstream.script(Script(status=status))
    with pytest.raises(urllib.error.HTTPError) as error:
        read_stream(upstream.base_url, PLAIN_REQUEST)
    assert error.value.code == status


def test_a_reset_stream_drops_the_connection(upstream):
    """The reader must see a failure, not a short answer: no terminal event arrived."""
    upstream.script(Script(text="FAKE-ANSWER", cut_after=2))
    # Either shape counts: a reset before any byte, or a truncated body afterwards.
    with pytest.raises((http.client.HTTPException, OSError)):
        read_stream(upstream.base_url, PLAIN_REQUEST)


def test_a_stream_can_end_cleanly_without_the_terminal_event(upstream):
    """The dangerous shape: a well-formed end that never says "completed"."""
    upstream.script(Script(text="FAKE-ANSWER", end_early_at=2))
    lines = read_stream(upstream.base_url, PLAIN_REQUEST)
    types = [event["type"] for event in events_of(lines)]
    assert len(types) == 2
    assert "response.completed" not in types


def test_a_hanging_upstream_times_out_rather_than_answering(upstream):
    upstream.script(Script(hang=True))
    with pytest.raises((TimeoutError, OSError)):
        read_stream(upstream.base_url, PLAIN_REQUEST)


def test_the_request_log_is_the_evidence_for_zero_egress(upstream):
    """Evidence for the zero-egress rule: a log that is empty when nothing left."""
    assert upstream.request_count == 0
    upstream.script(Script())
    read_stream(upstream.base_url, PLAIN_REQUEST)
    assert upstream.request_count == 1
    recorded = upstream.requests[0]
    assert recorded.method == "POST"
    assert recorded.path == "/responses"
    assert recorded.body == PLAIN_REQUEST
    assert "Authorization" in recorded.header_names
    assert recorded.authorization == "Bearer FAKE-T05-SENTINEL"


def test_the_request_log_keeps_the_credential_out_of_the_header_names(upstream):
    """Header names are safe to record; the credential is kept apart for assertions."""
    upstream.script(Script())
    read_stream(upstream.base_url, PLAIN_REQUEST)
    recorded = upstream.requests[0]
    assert all("FAKE-T05-SENTINEL" not in name for name in recorded.header_names)
