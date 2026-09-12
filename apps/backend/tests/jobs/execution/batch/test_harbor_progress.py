import json

from eval_platform.adapters.execution.harbor.config_mapper import (
    HarborJobPlan,
    HarborRunBinding,
    harbor_agent_key,
    harbor_task_path_key,
)
from eval_platform.adapters.execution.harbor.lifecycle.monitor import (
    HarborProgressMonitor,
)


class Observer:
    def __init__(self):
        self.events = []

    def trial_started(self, run_id):
        self.events.append(("started", run_id))

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
