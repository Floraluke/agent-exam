from jobs.test_http import submission, submit


def code(response):
    return response.json()["error"]["code"]


def register_tasks(jobs_api, size):
    names = ["verified-task"] + [
        f"verified-task-{index}" for index in range(2, size + 1)
    ]
    return [jobs_api.register_task(name) for name in names]


def test_continuous_preset_accepts_four_six_and_nine_tasks(jobs_api):
    jobs_api.login()
    agent = jobs_api.register_agent("verified-codex")
    for size in (4, 6, 9):
        tasks = register_tasks(jobs_api, size)
        body = submission(tasks[0]["task_id"], agent["agent_configuration_id"])
        body["task_ids"] = [item["task_id"] for item in tasks]
        body["batch_preset"] = "continuous"
        response = submit(jobs_api, body, f"continuous-{size:02d}-0001")
        assert response.status_code == 202
        assert response.json()["trial_count"] == size


def test_continuous_preset_rejects_empty_and_twenty_one_tasks(jobs_api):
    jobs_api.login()
    agent = jobs_api.register_agent("verified-codex")
    tasks = register_tasks(jobs_api, 21)
    body = submission(tasks[0]["task_id"], agent["agent_configuration_id"])
    body["task_ids"] = [item["task_id"] for item in tasks]
    body["batch_preset"] = "continuous"
    response = submit(jobs_api, body, "continuous-21-0001")
    assert response.status_code == 400 and code(response) == "BATCH_PRESET_EXCEEDED"

    body["task_ids"] = []
    response = submit(jobs_api, body, "continuous-00-0001")
    assert response.status_code == 400 and code(response) == "EMPTY_JOB_SELECTION"


def test_continuous_preset_bounds_sixty_runs_and_three_configurations(jobs_api):
    jobs_api.login()
    tasks = register_tasks(jobs_api, 20)
    agents = [
        jobs_api.register_agent(name)
        for name in ("verified-codex", "verified-codex-2", "verified-codex-3")
    ]
    body = submission(tasks[0]["task_id"], agents[0]["agent_configuration_id"])
    body["task_ids"] = [item["task_id"] for item in tasks]
    body["agent_configuration_ids"] = [
        item["agent_configuration_id"] for item in agents
    ]
    body["batch_preset"] = "continuous"
    response = submit(jobs_api, body, "continuous-60-0001")
    assert response.status_code == 202
    assert response.json()["trial_count"] == 60

    fourth = jobs_api.register_agent("verified-codex-4")
    body["agent_configuration_ids"] = [
        *[item["agent_configuration_id"] for item in agents],
        fourth["agent_configuration_id"],
    ]
    response = submit(jobs_api, body, "continuous-63-0001")
    assert response.status_code == 400 and code(response) == "BATCH_PRESET_EXCEEDED"


def test_existing_presets_keep_their_task_ranges(jobs_api):
    jobs_api.login()
    agent = jobs_api.register_agent("verified-codex")
    tasks = register_tasks(jobs_api, 4)
    for preset in ("demo", "quick"):
        body = submission(tasks[0]["task_id"], agent["agent_configuration_id"])
        body["task_ids"] = [item["task_id"] for item in tasks]
        body["batch_preset"] = preset
        response = submit(jobs_api, body, f"range-{preset}-0001")
        assert response.status_code == 400 and code(response) == "BATCH_PRESET_EXCEEDED"
