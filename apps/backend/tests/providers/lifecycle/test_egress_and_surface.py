"""S6c：出站（一次 POST，绝不重试）与流透传（客户端收到的字节与上游一致）。

两条"以记录为证"的断言在这里第一次真正吃紧：**假上游自己的请求记录**既证明"经代理发出"，
也证明被拒绝/失败时**只有一次尝试**（不重试、不换模型）。连接器（connector）是注入的，
因为代理→上游那段必须是 TLS 而假上游是明文 HTTP：TLS 包装归集成层，本片不假装已有。

最后一条用例覆盖最危险的形状：**客户端中途消失**——写回失败也必须结算并关闭该 Run。
"""

from __future__ import annotations

import json
import socket
import struct
import time
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest

from eval_platform.adapters.execution.provider_access.budget import UNKNOWN_USAGE_REASON
from eval_platform.adapters.execution.provider_access.server import (
    ProviderRejection,
    RunRunner,
)
from providers.contract.support.fake_responses import FAKE_USAGE, FakeUpstream, Script
from providers.contract.support.responses_events import completed
from providers.lifecycle.support import (
    CLIENT_TOKEN,
    FAKE_SECRET,
    MODEL,
    make_harness,
    request_body,
    sender_for,
    served_proxy,
)

SMALL_TIMEOUT_SECONDS = 1.0
BIG_TEXT = "x" * (256 * 1024)


def frames(index: int = 1) -> list[bytes]:
    return completed(f"resp_{index}", MODEL, "FAKE-ANSWER", FAKE_USAGE)


@pytest.fixture
def upstream() -> Iterator[FakeUpstream]:
    with FakeUpstream() as fake:
        yield fake


def test_the_positive_control_reaches_the_fake_upstream(upstream, tmp_path):
    harness = make_harness(tmp_path)
    admission = harness.decide(body=request_body(max_output_tokens=1_000))
    relay = RunRunner(harness.ledger, sender=sender_for(upstream)).relay(admission)

    relayed = b"".join(relay)

    assert upstream.request_count == 1
    recorded = upstream.requests[0]
    assert (recorded.method, recorded.path) == ("POST", "/responses")
    assert recorded.body is not None and recorded.body["model"] == MODEL
    assert recorded.authorization == f"Bearer {FAKE_SECRET}"
    assert CLIENT_TOKEN not in json.dumps(list(recorded.header_names))
    assert relayed == b"".join(frames())
    assert relay.outcome is not None
    assert relay.outcome.settlement.measured is True


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "TRANSPORT_UPSTREAM_UNAUTHORIZED"),
        (403, "TRANSPORT_UPSTREAM_UNAUTHORIZED"),
        (429, "TRANSPORT_UPSTREAM_RATE_LIMITED"),
        (400, "TRANSPORT_UPSTREAM_REFUSED"),
        (500, "TRANSPORT_UPSTREAM_UNAVAILABLE"),
        (503, "TRANSPORT_UPSTREAM_UNAVAILABLE"),
        (302, "TRANSPORT_REDIRECT_NOT_PERMITTED"),
    ],
)
def test_a_refused_call_is_never_a_second_call(upstream, tmp_path, status, code):
    upstream.script(Script(status=status))
    harness = make_harness(tmp_path)
    relay = RunRunner(harness.ledger, sender=sender_for(upstream)).relay(
        harness.decide()
    )

    with pytest.raises(ProviderRejection, match=code):
        b"".join(relay)

    assert upstream.request_count == 1
    assert relay.outcome is not None
    assert relay.outcome.settlement.measured is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_a_held_upstream_times_out_without_a_second_attempt(upstream, tmp_path):
    upstream.script(Script(hang=True))
    harness = make_harness(tmp_path)
    sender = sender_for(upstream, timeout=SMALL_TIMEOUT_SECONDS)
    relay = RunRunner(harness.ledger, sender=sender).relay(harness.decide())

    with pytest.raises(ProviderRejection, match="TRANSPORT_UPSTREAM_TIMEOUT"):
        b"".join(relay)

    assert upstream.request_count == 1
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_a_cut_stream_is_an_interruption_not_a_short_answer(upstream, tmp_path):
    upstream.script(Script(text="FAKE-ANSWER", cut_after=2))
    harness = make_harness(tmp_path)
    relay = RunRunner(harness.ledger, sender=sender_for(upstream)).relay(
        harness.decide()
    )

    with pytest.raises(ProviderRejection, match="TRANSPORT_STREAM_INTERRUPTED"):
        b"".join(relay)

    assert upstream.request_count == 1
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_a_clean_early_end_is_not_a_successful_answer(upstream, tmp_path):
    upstream.script(Script(text="FAKE-ANSWER", end_early_at=2))
    harness = make_harness(tmp_path)
    relay = RunRunner(harness.ledger, sender=sender_for(upstream)).relay(
        harness.decide()
    )
    relayed = b"".join(relay)

    assert relayed and b"response.completed" not in relayed
    assert upstream.request_count == 1
    assert relay.outcome is not None and relay.outcome.ended is False
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_transport_headers_belong_to_the_transport(upstream, tmp_path):
    """The client's framing and routing headers must not reach the upstream."""

    harness = make_harness(tmp_path)
    admission = harness.decide(
        headers={
            "Host": "evil.example.com",
            "Content-Length": "9999",
            "Accept-Encoding": "gzip",
            "X-Trace": "keep",
        }
    )
    relay = RunRunner(harness.ledger, sender=sender_for(upstream)).relay(admission)
    b"".join(relay)

    names = list(upstream.requests[0].header_names)
    assert names.count("Host") == 1
    assert names.count("Content-Length") == 1
    assert names.count("Accept-Encoding") == 1
    assert "X-Trace" in names


def post(url: str, body: bytes, token: str = CLIENT_TOKEN) -> bytes:
    request = urllib.request.Request(
        url + "/responses",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as answer:
        return answer.read()


def test_a_successful_request_is_relayed_byte_for_byte(upstream, tmp_path):
    with served_proxy(upstream, tmp_path) as (harness, url, outcomes):
        answer = post(url, request_body(max_output_tokens=1_000))

    assert answer == b"".join(frames())
    assert upstream.request_count == 1
    assert [item.settlement.measured for item in outcomes] == [True]
    assert harness.ledger.closed_reason is None


def test_a_bad_token_is_answered_with_controlled_text(upstream, tmp_path):
    with served_proxy(upstream, tmp_path) as (_harness, url, _outcomes):
        with pytest.raises(urllib.error.HTTPError) as error:
            post(url, request_body(), token="not-this-run")

    assert error.value.code == 403
    text = error.value.read().decode("utf-8")
    assert json.loads(text)["error"]["code"] == "PROVIDER_ACCESS_DENIED"
    assert CLIENT_TOKEN not in text and FAKE_SECRET not in text
    assert "fake-upstream" not in text and ".json" not in text and "t05" not in text
    assert upstream.request_count == 0


def test_a_non_post_is_refused_with_its_own_status(upstream, tmp_path):
    with served_proxy(upstream, tmp_path) as (_harness, url, _outcomes):
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(url + "/responses", timeout=10)

    assert error.value.code == 405
    code = json.loads(error.value.read())["error"]["code"]
    assert code == "PROVIDER_REQUEST_REJECTED"
    assert upstream.request_count == 0


def test_an_upstream_failure_before_the_answer_is_a_controlled_502(upstream, tmp_path):
    upstream.script(Script(status=503))
    with served_proxy(upstream, tmp_path) as (harness, url, _outcomes):
        with pytest.raises(urllib.error.HTTPError) as error:
            post(url, request_body())

    assert error.value.code == 502
    assert json.loads(error.value.read())["error"]["code"] == "PROVIDER_UPSTREAM_FAILED"
    assert upstream.request_count == 1
    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON


def test_a_client_that_vanishes_still_settles_and_stops_the_run(upstream, tmp_path):
    """The answer is far larger than any socket buffer, so the writes cannot finish."""

    upstream.script(Script(text=BIG_TEXT))
    with served_proxy(upstream, tmp_path) as (harness, url, _outcomes):
        host, port = "127.0.0.1", int(url.rsplit(":", 1)[1])
        payload = request_body()
        request = (
            f"POST /responses HTTP/1.1\r\nHost: {host}\r\n"
            f"Authorization: Bearer {CLIENT_TOKEN}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\n\r\n"
        ).encode()
        sock = socket.socket()
        # A tiny receive buffer is what makes this test honest: without it the host
        # buffers the whole answer and the client's disappearance is never noticed.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        sock.settimeout(10)
        sock.connect((host, port))
        sock.sendall(request + payload)
        time.sleep(0.3)  # let the proxy start relaying into a socket nobody reads
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        sock.close()
        deadline = time.monotonic() + 10
        while harness.ledger.closed_reason is None and time.monotonic() < deadline:
            time.sleep(0.02)

    assert harness.ledger.closed_reason == UNKNOWN_USAGE_REASON
    # The hold for a request with no declared ceiling is the whole remaining output.
    assert harness.ledger.consumed_output_tokens == 32_000
