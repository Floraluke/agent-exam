"""S2 配置渲染：指向代理入口的固定 TOML、摘要与两个重试参数置零。

两条纪律：

1. **渲染结果绝不含凭据**——函数只接受环境变量的**名字**，凭据结构上无从进入。
2. **重试上限在两个层级都写成 0**：设计冻结要求显式关闭（固定 CLI 的默认值不是零），
   但仓库内没有"固定 0.153.0 从哪一层读这两个参数"的依据。两个都写不会静默丢失上限，
   严格解析器若拒绝额外键会响亮失败，正好在契约层复核时暴露。复核即 S2 的验证内容。
"""

from __future__ import annotations

import pytest

from eval_platform.adapters.execution.codex.provider_config import (
    RETRY_KEYS,
    RETRY_VALUE,
    render_provider_config,
)
from eval_platform.adapters.execution.provider_access.secrets import (
    REGISTERED_UPSTREAMS,
)

FAKE = "internal_test_fake"
ENTRY = "http://proxy:8080"
ENV_KEY = "AGENTEXAM_RUN_TOKEN"


def render(**overrides: str):
    options = {"provider": FAKE, "base_url": ENTRY, "env_key": ENV_KEY, **overrides}
    return render_provider_config(**options)


def test_points_at_the_proxy_entry_and_names_the_token_variable():
    config = render()
    assert f'model_provider = "{FAKE}"' in config.text
    assert f"[model_providers.{FAKE}]" in config.text
    assert f'base_url = "{ENTRY}"' in config.text
    assert f'env_key = "{ENV_KEY}"' in config.text
    assert 'wire_api = "responses"' in config.text


def test_retry_keys_are_only_ever_written_as_zero():
    """Both placements are zero, and no non-zero value for them exists anywhere."""
    config = render()
    for key in RETRY_KEYS:
        assert config.text.count(f"{key} = {RETRY_VALUE}") == 2, key
        others = [
            line
            for line in config.text.splitlines()
            if line.startswith(key) and line != f"{key} = {RETRY_VALUE}"
        ]
        assert others == []


def test_the_render_is_deterministic_so_the_digest_can_be_recorded():
    first, second = render(), render()
    assert first.text == second.text
    assert first.digest == second.digest
    assert len(first.digest) == 64
    assert render(base_url="http://other-host:8080").digest != first.digest


def test_no_credential_can_enter_the_rendered_file():
    """The function takes a variable *name*; a value has nowhere to go."""
    import inspect

    parameters = inspect.signature(render_provider_config).parameters
    assert set(parameters) == {"provider", "base_url", "env_key"}
    config = render()
    for forbidden in ("Bearer", "sk-", "secret", "token="):
        assert forbidden not in config.text
    assert "AGENTEXAM_RUN_TOKEN" in config.text  # the name is expected


def test_no_host_path_or_real_upstream_appears():
    text = render().text
    assert "C:" not in text and "/home/" not in text and "/Users/" not in text
    for upstream in REGISTERED_UPSTREAMS.values():
        assert upstream not in text


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.deepseek.com",  # a real provider belongs on the proxy side
        "https://api.moonshot.cn/v1",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://proxy:8080/responses",  # a path is not a base URL
        "http://user:pass@proxy:8080",  # credentials never belong in the entry
        "ftp://proxy:8080",
        "proxy:8080",
        "",
    ],
)
def test_entries_that_are_not_the_isolated_proxy_are_refused(base_url):
    with pytest.raises(ValueError, match="PROVIDER_CONFIG_ENTRY"):
        render(base_url=base_url)


@pytest.mark.parametrize("provider", ["deepseek; rm", "DeepSeek", "", "unregistered"])
def test_unknown_or_malformed_providers_are_refused(provider):
    with pytest.raises(ValueError, match="PROVIDER_CONFIG_PROVIDER"):
        render(provider=provider)


@pytest.mark.parametrize("env_key", ["token", "1TOKEN", "AGENTEXAM-RUN", ""])
def test_malformed_environment_variable_names_are_refused(env_key):
    with pytest.raises(ValueError, match="PROVIDER_CONFIG_ENV_KEY_INVALID"):
        render(env_key=env_key)


def test_repr_stays_free_of_credentials():
    """Records keep the digest and the entry, never a credential value."""
    config = render()
    assert ENV_KEY in repr(config) and config.digest in repr(config)
    assert "Bearer" not in repr(config)
