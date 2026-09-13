import asyncio
import json

from eval_platform.adapters.execution.harbor.config_mapper import (
    HarborJobPlan,
    HarborRunBinding,
    harbor_agent_key,
    harbor_task_path_key,
)
from eval_platform.adapters.execution.harbor.lifecycle.control import (
    permit_path,
    ready_path,
    run_controlled_trials,
    signal,
    stop_path,
)
from eval_platform.adapters.execution.harbor.lifecycle.monitor import (
    HarborProgressMonitor,
)


class Observer:
    def __init__(self, denied=()):
        self.events = []
        self.denied = set(denied)

    def trial_started(self, run_id):
        self.events.append(("started", run_id))
        return run_id not in self.denied

    def trial_finished(self, run_id):
        self.events.append(("finished", run_id))


def _trial(root, name, task, agent, *, result=False):
    directory = root / name
    directory.mkdir(parents=True)
    config = {"task": {"path": str(task)}, "agent": agent}
    (directory / "config.json").write_text(json.dumps(config), encoding="utf-8")
    if result:
        (directory / "result.json").write_text(
            json.dumps({"id": name, "config": config}), encoding="utf-8"
        )
    return directory


def test_harbor_files_emit_ordered_identities_once_and_ignore_malformed(tmp_path):
    job_dir = tmp_path / "job"
    first_task, second_task = tmp_path / "task-one", tmp_path / "task-two"
    agent = {"name": "codex", "model_name": "provider/model", "kwargs": {}}
    plan = HarborJobPlan(
        {},
        (
            HarborRunBinding(
                "run-one",
                harbor_task_path_key(str(first_task)),
                harbor_agent_key(agent),
            ),
            HarborRunBinding(
                "run-two",
                harbor_task_path_key(str(second_task)),
                harbor_agent_key(agent),
            ),
        ),
    )
    observer = Observer()
    monitor = HarborProgressMonitor(plan, job_dir, observer)

    first = _trial(job_dir, "trial-one", first_task, agent)
    monitor.scan()
    monitor.scan()
    (first / "result.json").write_text(
        json.dumps(
            {
                "id": "trial-one",
                "config": {"task": {"path": str(first_task)}, "agent": agent},
            }
        ),
        encoding="utf-8",
    )
    monitor.scan()
    _trial(job_dir, "trial-two", second_task, agent, result=True)
    malformed = job_dir / "malformed"
    malformed.mkdir()
    (malformed / "config.json").write_text("not-json", encoding="utf-8")
    monitor.scan()
    monitor.scan()

    assert observer.events == [
        ("started", "run-one"),
        ("finished", "run-one"),
        ("started", "run-two"),
        ("finished", "run-two"),
    ]


def test_control_handshake_stops_before_a_denied_next_trial(tmp_path):
    job_dir, control = tmp_path / "job", tmp_path / "control"
    control.mkdir()
    first_task, second_task = tmp_path / "task-one", tmp_path / "task-two"
    agent = {"name": "codex", "model_name": "provider/model", "kwargs": {}}
    plan = HarborJobPlan(
        {},
        tuple(
            HarborRunBinding(
                run_id,
                harbor_task_path_key(str(task)),
                harbor_agent_key(agent),
            )
            for run_id, task in (("run-one", first_task), ("run-two", second_task))
        ),
    )
    observer = Observer({"run-two"})
    monitor = HarborProgressMonitor(plan, job_dir, observer, control)

    (control / "ready-0000").touch()
    monitor.scan()
    assert (control / "permit-0000").is_file()
    first = _trial(job_dir, "trial-one", first_task, agent)
    (first / "result.json").write_text(
        json.dumps(
            {
                "id": "trial-one",
                "config": {"task": {"path": str(first_task)}, "agent": agent},
            }
        ),
        encoding="utf-8",
    )
    (control / "ready-0001").touch()
    monitor.scan()

    assert (control / "stop").is_file()
    assert not (control / "permit-0001").exists()
    assert observer.events == [
        ("started", "run-one"),
        ("finished", "run-one"),
        ("started", "run-two"),
    ]


def test_child_queue_waits_for_each_permit_and_never_submits_after_stop(tmp_path):
    control = tmp_path / "control"
    control.mkdir()
    submitted = []

    class Queue:
        def submit(self, config):
            async def execute():
                submitted.append(config)
                return "result-" + config

            return execute()

    class Progress:
        def __init__(self):
            self.advanced = 0

        def advance(self, _task):
            self.advanced += 1

    job = type(
        "Job",
        (),
        {"_remaining_trial_configs": ["one", "two"], "_trial_queue": Queue()},
    )()
    progress = Progress()

    async def scenario():
        running = asyncio.create_task(
            run_controlled_trials(job, control, progress, "task")
        )
        while not ready_path(control, 0).is_file():
            await asyncio.sleep(0)
        signal(permit_path(control, 0))
        while not ready_path(control, 1).is_file():
            await asyncio.sleep(0)
        signal(stop_path(control))
        return await asyncio.wait_for(running, timeout=1)

    assert asyncio.run(scenario()) == ["result-one"]
    assert submitted == ["one"]
    assert progress.advanced == 1
