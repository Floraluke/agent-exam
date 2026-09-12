from dataclasses import replace
from datetime import UTC, datetime

from jobs.execution.support.fakes import Backend, Evaluator, MemoryArtifacts
from jobs.execution.support.fixtures import queued_batch
from jobs.execution.support.memory import ExecutableMemoryJobs

from eval_platform.application.execute_job import JobExecutor
from eval_platform.delivery.worker.main import WorkerShell
from eval_platform.domain.agent import AgentConfiguration


def test_two_by_two_matrix_uses_task_then_configuration_order():
    now = datetime(2026, 9, 12, 15, 30, tzinfo=UTC)
    job, bundles = queued_batch(now, size=2)
    first, second = job.runs
    first_task = replace(first.task, task_id="00000000-0000-4000-8000-000000000001")
    second_task = replace(second.task, task_id="00000000-0000-4000-8000-000000000002")
    first_agent = replace(
        first.agent,
        agent_configuration_id="00000000-0000-4000-8000-000000000001",
    )
    configuration = AgentConfiguration(
        "00000000-0000-4000-8000-000000000002",
        first.agent.agent_type,
        first.agent.agent_version,
        first.agent.model_provider,
        "test-model-second",
        first.agent.authentication_type,
        first.agent.credential_profile_id,
        {"reasoning_effort": first.agent.reasoning_effort},
    )
    second_agent = replace(
        first_agent,
        agent_configuration_id=configuration.configuration_id,
        display_name="Synthetic Codex 2",
        model=configuration.model_name,
        configuration_fingerprint=configuration.fingerprint,
    )
    runs = (
        replace(
            first,
            run_id="00000000-0000-4000-8000-000000000004",
            task=first_task,
            agent=first_agent,
        ),
        replace(
            first,
            run_id="00000000-0000-4000-8000-000000000001",
            task=first_task,
            agent=second_agent,
        ),
        replace(
            second,
            run_id="00000000-0000-4000-8000-000000000003",
            task=second_task,
            agent=first_agent,
        ),
        replace(
            second,
            run_id="00000000-0000-4000-8000-000000000002",
            task=second_task,
            agent=second_agent,
        ),
    )
    job = replace(job, runs=runs)
    repository, artifacts = ExecutableMemoryJobs(job), MemoryArtifacts()
    backend = Backend(artifacts, b"diff --git a/a b/a\n")
    source = type(
        "Source",
        (),
        {
            "load": lambda self, identity: {
                item.public.instance_id: item for item in bundles
            }[identity]
        },
    )()

    executor = JobExecutor(
        repository, artifacts, backend, Evaluator(artifacts), source, lambda: now
    )
    assert WorkerShell(repository, executor, lambda: now).run_once("matrix-worker")

    assert [
        (item.task.instance_id, item.agent.configuration_id)
        for item in backend.requests[0].runs
    ] == [
        (task.instance_id, agent.agent_configuration_id)
        for task in (first_task, second_task)
        for agent in (first_agent, second_agent)
    ]
    assert repository.get(job.job_id).status == "COMPLETED"
