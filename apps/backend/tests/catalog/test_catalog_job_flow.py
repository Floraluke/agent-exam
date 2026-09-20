"""目录 → HTTP options → 提交 → 冻结 Job/Runs/初始事件：C 侧打通链。

任务 04 第 6 条要求打通这条链。现有测试只断言过 `/job-options` 的响应形状，没有走完
"目录读回 → 选项 → 提交 → 一次性读回落库结果"这一段。本文件覆盖两件事：

1. 用目录列表与 HTTP 选项驱动一次 6 题 × 2 配置的提交，验证：
   冻结身份与目录记录逐字段一致、全部 Runs 恰好覆盖 题目 × 配置 的笛卡尔积、
   Job 与每个 Run 都带初始事件。
2. 冻结之后目录发生变更（配置被停用），旧 Job 仍按落库时的冻结身份读回，不被改写；
   只有新提交会被停用状态拦住。
"""

import pytest
from identity.conftest import WRITE_HEADERS
from jobs.conftest import job_api
from jobs.test_http import submission, submit


@pytest.fixture
def flow_api():
    with job_api() as api:
        yield api


def error_code(response):
    return response.json()["error"]["code"]


def test_catalog_and_options_drive_one_frozen_submission(flow_api):
    api = flow_api
    assert api.login().status_code == 200

    tasks = [
        api.register_task(name)
        for name in ["verified-task"]
        + [f"verified-task-{index}" for index in range(2, 7)]
    ]
    agents = [api.register_agent(f"verified-codex{suffix}") for suffix in ("", "-2")]

    # 目录列表是向导的真实数据源：登记的题与配置都能读回
    task_page = api.client.get("/api/v1/tasks").json()
    listed_tasks = {item["task_id"] for item in task_page["items"]}
    assert {task["task_id"] for task in tasks} <= listed_tasks
    agent_page = api.client.get("/api/v1/agent-configurations").json()
    listed_agents = {item["agent_configuration_id"] for item in agent_page["items"]}
    assert {agent["agent_configuration_id"] for agent in agents} <= listed_agents

    # 选项由服务端自有：连续 1–20 与总量上限都在这里
    options = api.client.get("/api/v1/job-options").json()
    continuous = next(
        preset
        for preset in options["batch_presets"]
        if preset["batch_preset"] == "continuous"
    )
    assert continuous["minimum_tasks"] == 1
    assert continuous["maximum_tasks"] == 20
    assert options["maximum_agent_configurations"] == 3
    assert options["maximum_runs"] == 60
    # 6 题在 continuous 档内、在 demo(1–3) 档外；6 × 2 = 12 不超过 60
    assert continuous["minimum_tasks"] <= len(tasks) <= continuous["maximum_tasks"]
    assert len(tasks) * len(agents) <= options["maximum_runs"]

    body = {
        "task_ids": [task["task_id"] for task in tasks],
        "agent_configuration_ids": [
            agent["agent_configuration_id"] for agent in agents
        ],
        "evaluation_track": options["evaluation_tracks"][0],
        "batch_preset": continuous["batch_preset"],
        "limit_profile_id": options["limit_profiles"][0]["limit_profile_id"],
    }
    response = submit(api, body, "catalog-flow-0001")
    assert response.status_code == 202
    created = response.json()
    assert created["status"] == "AWAITING_OWNER_APPROVAL"
    assert created["trial_count"] == len(tasks) * len(agents)
    assert len(created["run_ids"]) == len(tasks) * len(agents)

    frozen = api.client.get("/api/v1/jobs/" + created["job_id"]).json()

    # 冻结的题目身份与目录记录逐字段一致（落库瞬间防漂移）
    catalog_tasks = {task["task_id"]: task for task in tasks}
    assert len(frozen["task_snapshots"]) == len(tasks)
    for snapshot in frozen["task_snapshots"]:
        record = catalog_tasks[snapshot["task_id"]]
        assert snapshot["instance_id"] == record["instance_id"]
        assert snapshot["dataset_id"] == record["dataset_id"]
        assert snapshot["dataset_revision"] == record["dataset_revision"]
        assert snapshot["split"] == record["split"]
        assert snapshot["base_commit"] == record["base_commit"]
        assert snapshot["problem_statement"] == record["problem_statement"]

    catalog_agents = {agent["agent_configuration_id"]: agent for agent in agents}
    assert len(frozen["agent_snapshots"]) == len(agents)
    for snapshot in frozen["agent_snapshots"]:
        record = catalog_agents[snapshot["agent_configuration_id"]]
        assert (
            snapshot["configuration_fingerprint"] == record["configuration_fingerprint"]
        )

    # 全部 Runs 恰好覆盖一次 题目 × 配置，且 Job 与每个 Run 都有初始事件
    expected_pairs = {
        (task["task_id"], agent["agent_configuration_id"])
        for task in tasks
        for agent in agents
    }
    assert {
        (run["task_id"], run["agent_configuration_id"]) for run in frozen["runs"]
    } == expected_pairs
    assert [event["reason_code"] for event in frozen["job_state_events"]] == [
        "JOB_SUBMITTED"
    ]
    for run in frozen["runs"]:
        assert [event["reason_code"] for event in run["state_events"]] == [
            "JOB_SUBMITTED"
        ]


def test_frozen_job_keeps_its_snapshot_when_the_catalog_changes(flow_api):
    api = flow_api
    api.login()
    task = api.register_task("verified-task")
    agent = api.register_agent("verified-codex")
    body = submission(task["task_id"], agent["agent_configuration_id"])
    body["batch_preset"] = "continuous"

    created = submit(api, body, "freeze-0001").json()
    frozen = api.client.get("/api/v1/jobs/" + created["job_id"]).json()

    disabled = api.client.post(
        "/api/v1/agent-configurations/" + agent["agent_configuration_id"] + "/disable",
        json={},
        headers=WRITE_HEADERS,
    )
    assert disabled.status_code == 204

    # 旧 Job 仍按落库时的冻结身份读回，不被目录变更改写
    reread = api.client.get("/api/v1/jobs/" + created["job_id"]).json()
    assert reread["agent_snapshots"] == frozen["agent_snapshots"]
    assert reread["task_snapshots"] == frozen["task_snapshots"]
    assert reread["status"] == "AWAITING_OWNER_APPROVAL"

    # 只有新提交会被停用状态拦住
    blocked = submit(api, body, "freeze-0002")
    assert blocked.status_code == 409
    assert error_code(blocked) == "AGENT_CONFIGURATION_DISABLED"
