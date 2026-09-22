"""受控集合之外的存量记录：失败关闭成受控错误，而不是 500，也不回落默认值。

B 在任务 05 的契约对齐行动里指出 `_controlled` 抛裸 `ValueError`、而 `app.py`
没有 `ValueError` 处理器，因此这条路径当时表现成 500。本文件钉住修复后的两件事：
域层拒绝伪装身份，HTTP 层给出契约第 5 节的 503 受控响应。
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from catalog.conftest import catalog_api
from catalog.memory import MemoryAgents
from eval_platform.delivery.http.catalog_schemas import AgentDetail
from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.catalog import CatalogUnavailable, RegisteredAgent

DAMAGED_ID = "11111111-1111-1111-1111-111111111111"


def _damaged(provider: str = "openai_chatgpt", agent_name: str = "codex"):
    """A record that reached storage before the registry and the CHECK existed."""
    return RegisteredAgent(
        AgentConfiguration(
            DAMAGED_ID,
            agent_name,
            "0.153.0",
            provider,
            "some-model",
            "chatgpt_auth_json",
            "private-reference",
            {"reasoning_effort": "medium"},
        ),
        "Damaged record",
        datetime.now(UTC),
    )


class DamagedAgents(MemoryAgents):
    """Repository holding one record the registry and the CHECK would reject."""

    def __init__(self, record):
        super().__init__()
        self.records[record.configuration.configuration_id] = record


@pytest.mark.parametrize(
    ("provider", "agent_name", "code"),
    [
        ("deepseek", "codex", "UNCONTROLLED_PROVIDER"),
        ("openai_chatgpt", "aider", "UNCONTROLLED_AGENT_TYPE"),
    ],
)
def test_schema_refuses_to_publish_an_uncontrolled_identity(provider, agent_name, code):
    """The domain layer names the offending field and never falls back."""
    with pytest.raises(CatalogUnavailable, match=code):
        AgentDetail.from_record(_damaged(provider, agent_name))


@pytest.mark.parametrize(
    ("provider", "agent_name"),
    [("deepseek", "codex"), ("openai_chatgpt", "aider")],
)
def test_uncontrolled_record_is_a_controlled_503_not_a_500(provider, agent_name):
    """Contract section 5 answers a damaged catalog record with 503, not a 500."""
    record = _damaged(provider, agent_name)
    with catalog_api(agents=DamagedAgents(record)) as api:
        assert api.login().status_code == 200
        responses = (
            api.client.get("/api/v1/agent-configurations"),
            api.client.get(f"/api/v1/agent-configurations/{DAMAGED_ID}"),
        )
        for response in responses:
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
            # Neither the internal marker nor the record's own values leak.
            assert "UNCONTROLLED" not in response.text
            assert provider not in response.text
            assert agent_name not in response.text
