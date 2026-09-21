"""受控文案：代理内部错误码 → 面向用户的受控短文案（HTTP_API §10.2）。

钉住两件事：内部码集合不许漂移（源码出现新码而映射表没决定即失败）；
发布出去的文案不含任何哨兵（主机名/URL、路径、profile 名、令牌片段、拓扑词）。
"""

from __future__ import annotations

import re
from pathlib import Path

from eval_platform.adapters.execution.provider_access import failures

PACKAGE = Path(failures.__file__).parent
_LITERAL = re.compile(r'"([A-Z][A-Z0-9_]{3,})"')

# Words that must never reach a user: upstream identity, URL or path markers,
# credential profile names, topology vocabulary, anything token-like.
SENTINELS = (
    "api.deepseek.com",
    "api.moonshot.cn",
    "fake-upstream",
    "t05.invalid",
    "http",
    "://",
    "/",
    "\\",
    "t05-fake-provider",
    "owner-codex",
    "token",
    "bearer",
    "key",
    "secret",
    "profile",
    "docker",
    "container",
    "network",
    "subnet",
    "sidecar",
    "egress",
    "internal",
    "172.",
    ".json",
    ".toml",
)

# Not error codes: HTTP verbs the policy also compares against.
_NON_CODES = frozenset({"POST", "GET", "PUT", "DELETE"})


def _codes_in_package() -> set[str]:
    """Every upper-case code literal the proxy modules can raise."""
    found: set[str] = set()
    for path in sorted(PACKAGE.glob("*.py")):
        if path.name == "failures.py":
            continue
        found.update(_LITERAL.findall(path.read_text(encoding="utf-8")))
    return found - _NON_CODES


def test_every_internal_code_has_a_decision():
    """New codes must be mapped or declared configuration-only, not silently generic."""
    undecided = _codes_in_package() - failures.ALL_INTERNAL_CODES
    assert undecided == set(), f"undecided internal codes: {sorted(undecided)}"


def test_known_vocabulary_is_complete_and_disjoint():
    expected = frozenset(failures.MAPPED_CODES) | failures.CONFIGURATION_ONLY
    assert failures.ALL_INTERNAL_CODES == expected
    assert not (set(failures.MAPPED_CODES) & failures.CONFIGURATION_ONLY)


def test_published_text_carries_no_sentinel_and_stays_short():
    for internal, (failure_code, summary) in failures.MAPPED_CODES.items():
        text = f"{failure_code} {summary}".lower()
        for sentinel in SENTINELS:
            assert sentinel.lower() not in text, f"{internal} leaked {sentinel!r}"
        assert failure_code.isupper() and "_" in failure_code
        assert 0 < len(summary) <= 40, f"{internal} summary is not a short sentence"


def test_every_group_maps_to_a_distinct_controlled_code():
    codes = {code for code, _ in failures.MAPPED_CODES.values()}
    assert len(codes) == len(failures._GROUPS)  # one distinct code per group
    for internal, (failure_code, _) in failures.MAPPED_CODES.items():
        assert failure_code.startswith("PROVIDER_"), internal


def test_unknown_and_configuration_codes_become_the_generic_pair():
    for internal in ("SOMETHING_UNREVIEWED", "BUDGET_LIMITS_INVALID", ""):
        assert failures.controlled_failure(internal) == failures.GENERIC_FAILURE


def test_representative_codes_map_to_their_own_class():
    cases = {
        "PROVIDER_TOKEN_CROSS_RUN": "PROVIDER_ACCESS_DENIED",
        "PROVIDER_TOKEN_EXPIRED": "PROVIDER_ACCESS_DENIED",
        "PRIVATE_FILE_PERMISSIONS_TOO_WIDE": "PROVIDER_CREDENTIAL_UNAVAILABLE",
        "PRIVATE_PROFILE_NOT_FOUND": "PROVIDER_CREDENTIAL_UNAVAILABLE",
        "REQUEST_UNKNOWN_FIELD": "PROVIDER_REQUEST_REJECTED",
        "REQUEST_TOOL_NOT_ALLOWED": "PROVIDER_REQUEST_REJECTED",
        "BUDGET_DEADLINE_EXCEEDED": "PROVIDER_BUDGET_EXHAUSTED",
        "BUDGET_RUN_CLOSED": "PROVIDER_BUDGET_EXHAUSTED",
    }
    for internal, expected in cases.items():
        assert failures.controlled_failure(internal)[0] == expected
