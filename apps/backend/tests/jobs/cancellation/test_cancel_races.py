from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from jobs.test_postgres import postgres_api

from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.domain.jobs.decisions import JobStateConflict
from eval_platform.domain.jobs.execution import JobLeaseConflict
from eval_platform.domain.jobs.models import run_order_key

pytestmark = pytest.mark.integration


def _submitted(jobs, owner, key):
    task = jobs.tasks.register(owner, "verified-task")
    agent = jobs.agents.register(owner, "verified-codex")
    return jobs.submit(
        owner,
        [task.task_id],
        [agent.configuration.configuration_id],
        "closed_book",
        "demo",
        "default-single-host-v1",
        key,
    )


def test_postgres_cancel_and_approval_serialize_to_canceled(postgres_sandbox):
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        created = _submitted(jobs, owner, "cancel-approval-race-source-0001")
        cancellation = JobCancellation(repository)
        approval = OwnerApproval(repository)
        barrier = Barrier(2, timeout=10)

        def cancel():
            barrier.wait()
            try:
                return cancellation.cancel(
                    owner, created.job_id, "race", "cancel-approval-race-0001"
                )
            except JobStateConflict:
                return None

        def approve():
            barrier.wait()
            try:
                return approval.decide(
                    owner, created.job_id, "approve", "race", "approval-race-0001"
                )
            except JobStateConflict:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = (pool.submit(cancel), pool.submit(approve))
            results = tuple(future.result() for future in outcomes)

        assert results[0] is not None
        stored = repository.get(created.job_id)
        assert stored.status == "CANCELED"
        assert {run.status for run in stored.runs} == {"CANCELED"}
        reasons = [event.reason_code for event in stored.state_events]
        assert reasons in [
            ["JOB_SUBMITTED", "JOB_CANCELED"],
            ["JOB_SUBMITTED", "OWNER_APPROVED", "JOB_CANCELED"],
        ]
        assert (results[1] is not None) == ("OWNER_APPROVED" in reasons)


def test_postgres_cancel_claim_race_never_leaves_an_executable_trial(
    postgres_sandbox,
):
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        created = _submitted(jobs, owner, "cancel-claim-race-source-0001")
        OwnerApproval(repository).decide(
            owner, created.job_id, "approve", None, "approve-claim-race-0001"
        )
        cancellation = JobCancellation(repository)
        barrier = Barrier(2, timeout=10)

        def cancel():
            barrier.wait()
            try:
                return cancellation.cancel(
                    owner, created.job_id, "race", "cancel-claim-race-0001"
                )
            except JobStateConflict:
                return None

        def claim():
            barrier.wait()
            return repository.claim("race-worker", cancellation.clock())

        with ThreadPoolExecutor(max_workers=2) as pool:
            canceled = pool.submit(cancel)
            claimed = pool.submit(claim)
            cancel_result = canceled.result()
            worker_claim = claimed.result()

        stored = repository.get(created.job_id)
        if cancel_result is not None:
            assert stored.status == "CANCELED"
            assert {run.status for run in stored.runs} == {"CANCELED"}
        else:
            assert stored.status == "PREPARING"
        if worker_claim is not None:
            if cancel_result is not None:
                with pytest.raises(JobLeaseConflict):
                    repository.start_execution(worker_claim.lease, cancellation.clock())
            else:
                repository.start_execution(worker_claim.lease, cancellation.clock())


def test_postgres_reconciliation_stop_and_replay_preserve_first_outcome(
    postgres_sandbox,
):
    with postgres_api(postgres_sandbox) as (_client, jobs, repository, owner):
        first = jobs.tasks.register(owner, "verified-task")
        second = jobs.tasks.register(owner, "verified-task-2")
        agent = jobs.agents.register(owner, "verified-codex")
        created = jobs.submit(
            owner,
            [first.task_id, second.task_id],
            [agent.configuration.configuration_id],
            "closed_book",
            "demo",
            "default-single-host-v1",
            "cancel-reconcile-postgres-source-0001",
        )
        OwnerApproval(repository).decide(
            owner, created.job_id, "approve", None, "cancel-reconcile-approve-0001"
        )
        cancellation = JobCancellation(repository)
        claimed = repository.claim("reconcile-postgres-worker", cancellation.clock())
        assert claimed is not None
        lease = repository.start_execution(claimed.lease, cancellation.clock())
        first_outcome = cancellation.cancel(
            owner,
            created.job_id,
            "对账期间停止",
            "cancel-reconcile-postgres-0001",
        )

        ordered = sorted(claimed.job.runs, key=run_order_key)
        lease = repository.fail(
            lease,
            ordered[0].run_id,
            "BACKEND_RESULT_IDENTITY_INVALID",
            "受控对账失败。",
            cancellation.clock(),
        )
        lease = repository.start_finalizing(lease, cancellation.clock())
        repository.finish(lease, cancellation.clock())
        replay = cancellation.cancel(
            owner,
            created.job_id,
            "对账期间停止",
            "cancel-reconcile-postgres-0001",
        )

        assert first_outcome.accepted_status == "CANCEL_REQUESTED"
        assert replay.accepted_status == first_outcome.accepted_status
        assert replay.record.status == "CANCELED"
        assert {run.status for run in replay.record.runs} == {"CANCELED"}
        assert all(run.failure_code is None for run in replay.record.runs)
