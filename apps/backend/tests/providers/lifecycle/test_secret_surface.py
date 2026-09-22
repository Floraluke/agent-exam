"""S6e：秘密外表面与受控文案的端到端扫描——只用假值探针，不用真实凭据。

受控文案的哨兵表复用 `policy/test_controlled_failures.py`（单一来源），但把扫描面扩到
**端到端**：每条失败路径经真实 HTTP 表面返回的正文、响应头、进程的标准输出与错误输出、
进程环境与 `argv`、以及代理运行目录里落下的文件。同时断言**经代理发出的凭据**确实是代理
自己的假值，而做题侧的令牌一次都没有到达上游。

两类哨兵分开用：给"面向用户的短文案"用完整拓扑词表；给**任意文本**（环境变量、文件、
响应头）只用**秘密值与上游身份**——`/`、`key`、`internal` 这类词在普通文本里必然误报，
拿它们扫环境变量只会得到噪声。

不在本片范围的两面：`docker inspect` 可见配置与容器内文件/进程（集成层 S11）、
网页呈现（B 侧，触发条件已记在任务单 Comments）。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from providers.contract.support.fake_responses import FakeUpstream, Script
from providers.lifecycle.support import (
    CLIENT_TOKEN,
    FAKE_SECRET,
    PROFILE_ID,
    make_harness,
    request_body,
    served_proxy,
)
from providers.policy.test_controlled_failures import SENTINELS

# Values that must never appear anywhere, plus the fake provider's own identity.
VALUE_SENTINELS = (
    FAKE_SECRET,
    CLIENT_TOKEN,
    PROFILE_ID,
    "fake-upstream",
    "t05.invalid",
    "api.deepseek.com",
    "api.moonshot.cn",
)
# The registered upstream URL necessarily spells the provider's identity: that is the
# file's purpose. Everything outside this set is a leak; the run token is not here.
EXPECTED_IN_PROFILE = (FAKE_SECRET, PROFILE_ID, "t05.invalid", "fake-upstream")


def leaked(text: str, sentinels: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [item for item in sentinels if item.lower() in lowered]


def request_once(
    url: str, body: bytes, token: str = CLIENT_TOKEN, method: str = "POST"
) -> tuple[int, str, dict[str, str]]:
    request = urllib.request.Request(
        url + "/responses",
        data=body if method == "POST" else None,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            return answer.status, answer.read().decode("utf-8"), dict(answer.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8"), dict(error.headers)


@pytest.fixture
def upstream():
    with FakeUpstream() as fake:
        yield fake


def test_every_error_answer_is_controlled_text_without_a_sentinel(upstream, tmp_path):
    """Each refusal path, in the words the client is actually given."""

    upstream.script(Script(status=503))
    with served_proxy(upstream, tmp_path) as (_harness, url, _outcomes):
        answers = [
            request_once(url, request_body(), token="not-this-run"),
            request_once(url, request_body(base_url="https://api.deepseek.com")),
            request_once(url, request_body(tools=[{"type": "web_search"}])),
            request_once(url, request_body(), method="GET"),
            request_once(url, request_body()),
        ]

    for status, body, headers in answers:
        assert body, "an error answer must say something controlled"
        error = json.loads(body)["error"]
        # The JSON wire form escapes non-ASCII, so the sentinel scan runs on the text
        # the user is actually given, not on its transport encoding.
        text = f"{error['code']} {error['message']}"
        assert leaked(text, SENTINELS) == [], f"leak in {status}: {text}"
        assert leaked(json.dumps(headers), VALUE_SENTINELS) == []
        assert error["code"].startswith("PROVIDER_")
    assert [status for status, _body, _headers in answers] == [403, 400, 400, 405, 502]


def test_the_client_token_never_reaches_the_upstream(upstream, tmp_path):
    """The credential on the wire is the proxy's own; the run token stays inside."""

    with served_proxy(upstream, tmp_path) as (_harness, url, _outcomes):
        status, body, headers = request_once(url, request_body())

    assert status == 200 and body
    assert leaked(json.dumps(headers), VALUE_SENTINELS) == []
    recorded = upstream.requests[0]
    assert recorded.authorization == f"Bearer {FAKE_SECRET}"
    assert leaked(json.dumps(list(recorded.header_names)), VALUE_SENTINELS) == []
    assert CLIENT_TOKEN not in json.dumps(recorded.body)


def test_the_process_surface_stays_clean(upstream, tmp_path, capsys):
    """No log line, no environment entry and no file gains the secret."""

    environment = dict(os.environ)
    arguments = list(sys.argv)
    with served_proxy(upstream, tmp_path) as (harness, url, _outcomes):
        request_once(url, request_body())
        request_once(url, request_body(), token="not-this-run")
    captured = capsys.readouterr()

    assert leaked(captured.out, VALUE_SENTINELS) == []
    assert leaked(captured.err, VALUE_SENTINELS) == []
    assert leaked(json.dumps(environment), VALUE_SENTINELS) == []
    assert leaked(json.dumps(arguments), VALUE_SENTINELS) == []
    assert leaked(environment.get("AGENTEXAM_RUN_ID", ""), VALUE_SENTINELS) == []
    assert leaked(repr(harness.ledger), VALUE_SENTINELS) == []
    assert leaked(repr(harness.registry.active_run_ids()), VALUE_SENTINELS) == []

    written = sorted(path.name for path in Path(tmp_path).iterdir())
    assert written == ["provider-private.json"]
    contents = Path(tmp_path, "provider-private.json").read_text(encoding="utf-8")
    # The private file is the one place the owner's credential legitimately lives; the
    # client's run token must not be there, and nothing else may join the pair.
    assert sorted(leaked(contents, VALUE_SENTINELS)) == sorted(EXPECTED_IN_PROFILE)
    assert CLIENT_TOKEN not in contents


def test_the_proxy_state_carries_amounts_and_identity_not_credentials(tmp_path):
    harness = make_harness(tmp_path)
    assert leaked(repr(harness.service), VALUE_SENTINELS) == []
    assert leaked(repr(harness.binding), VALUE_SENTINELS) == []
    assert harness.binding.token not in repr(harness.binding)
    assert sorted(path.name for path in Path(tmp_path).iterdir()) == [
        "provider-private.json"
    ]
