"""Explicit local Job schema upgrade; API startup never runs migrations."""

import argparse
import sys

from eval_platform.adapters.persistence.jobs import initialize_schema
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.application.job_lifecycle.recovery import JobRecovery
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.config import database_url
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.domain.jobs.models import JobError


def create_jobs(
    dsn: str, tasks: TaskCatalog, agents: AgentRegistry
) -> tuple[JobSubmission, OwnerApproval, JobCancellation, JobRecovery]:
    repository = PostgresJobRepository(dsn)
    submission = JobSubmission(
        tasks,
        agents,
        repository,
        submission_policy(),
    )
    return (
        submission,
        OwnerApproval(repository),
        JobCancellation(repository),
        JobRecovery(repository, submission),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentExam 本机 Job 存储升级")
    parser.add_argument("command", choices=["init-db"])
    parser.parse_args(argv)
    try:
        initialize_schema(database_url())
        print("Job 四表已建立；未创建批次、读取凭据或运行评测。")
        return 0
    except (ValueError, JobError):
        print("Job 存储升级未确认成功；不输出连接或凭据信息。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
