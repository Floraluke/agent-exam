from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest

from eval_platform.domain.jobs.execution import JobLeaseConflict
from jobs.execution.support.fixtures import queued_job
from jobs.execution.support.memory import ExecutableMemoryJobs


def test_two_workers_claim_at_most_one_active_job():
    now = datetime(2026, 9, 12, 9, 0, tzinfo=UTC)
    first, _ = queued_job(now)
    second, _ = queued_job(now)
    repository = ExecutableMemoryJobs(first, second)
    barrier = Barrier(2, timeout=5)

    def claim(worker):
        barrier.wait()
        return repository.claim(worker, now)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(claim, ("worker-one", "worker-two")))
    assert sum(item is not None for item in outcomes) == 1
    assert sum(item.status == "PREPARING" for item in repository.records.values()) == 1
    assert sum(item.status == "QUEUED" for item in repository.records.values()) == 1


def test_claim_skips_unapproved_rejected_claimed_and_multi_run_jobs():
    now = datetime(2026, 9, 12, 9, 0, tzinfo=UTC)
    queued, _ = queued_job(now)
    extra_run = replace(queued.runs[0], run_id=str(uuid4()))
    multi = replace(queued, job_id=str(uuid4()), runs=(queued.runs[0], extra_run))
    awaiting = replace(queued, job_id=str(uuid4()), status="AWAITING_OWNER_APPROVAL")
    rejected = replace(queued, job_id=str(uuid4()), status="REJECTED")
    repository = ExecutableMemoryJobs(multi, awaiting, rejected)
    assert repository.claim("worker-one", now) is None

    repository = ExecutableMemoryJobs(queued)
    assert repository.claim("worker-one", now) is not None
    assert repository.claim("worker-two", now) is None


def test_wrong_worker_stale_version_and_expired_lease_cannot_advance():
    now = datetime(2026, 9, 12, 9, 0, tzinfo=UTC)
    job, _ = queued_job(now)
    repository = ExecutableMemoryJobs(job)
    claimed = repository.claim("worker-one", now)
    assert claimed is not None
    lease = claimed.lease

    for invalid, timestamp in (
        (replace(lease, worker_id="worker-two"), now),
        (replace(lease, job_version=lease.job_version - 1), now),
        (replace(lease, run_version=lease.run_version - 1), now),
        (lease, lease.lease_expires_at),
    ):
        with pytest.raises(JobLeaseConflict):
            repository.start_execution(invalid, timestamp)
    assert repository.get(job.job_id).status == "PREPARING"
