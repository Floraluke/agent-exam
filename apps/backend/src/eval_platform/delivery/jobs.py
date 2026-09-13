"""Explicit local Job schema and owner-only artifact maintenance."""

import argparse
import getpass
import sys
import warnings
from datetime import UTC, datetime

from eval_platform.adapters.artifacts.minio import MinioArtifactStore
from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.adapters.persistence.jobs import initialize_schema
from eval_platform.adapters.persistence.jobs.repository import PostgresJobRepository
from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.identity import IdentityService
from eval_platform.application.job_lifecycle.cancellation import JobCancellation
from eval_platform.application.job_lifecycle.recovery import JobRecovery
from eval_platform.application.job_lifecycle.retention import ArtifactRetention
from eval_platform.application.job_submission import JobSubmission
from eval_platform.application.owner_approval import OwnerApproval
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.delivery.http.config import database_url
from eval_platform.delivery.job_presets import submission_policy
from eval_platform.domain.catalog import ArtifactUnavailable
from eval_platform.domain.identity import AuthenticationRequired, IdentityUnavailable
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
    parser = argparse.ArgumentParser(description="AgentExam 本机 Job 维护")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="仅在空白专属数据库建立 Job 表")
    cleanup = commands.add_parser(
        "cleanup-artifacts", help="所有者逐对象清理已到期 raw_30d 正文"
    )
    cleanup.add_argument("username")
    cleanup.add_argument("--limit", type=int, default=100)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "cleanup-artifacts" and not sys.stdin.isatty():
            raise ValueError("密码只能从本机交互终端输入")
        dsn = database_url()
        if arguments.command == "init-db":
            initialize_schema(dsn)
            print("Job 表已建立；未创建批次、读取凭据或运行评测。")
            return 0
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("当前所有者密码（不回显）：")
        identity = IdentityService(
            PostgresIdentityRepository(dsn),
            Argon2Passwords(),
        )
        login = identity.login(arguments.username, password)
        try:
            result = ArtifactRetention(
                PostgresJobRepository(dsn),
                MinioArtifactStore(None, ""),
            ).cleanup(login.actor, datetime.now(UTC), arguments.limit)
        finally:
            identity.logout(login.token)
        print(
            f"已检查 {result.scanned} 个到期制品；"
            f"删除 {result.deleted} 个，补记审计 {result.recovered} 个。"
        )
        return 0
    except (
        ArtifactUnavailable,
        AuthenticationRequired,
        getpass.GetPassWarning,
        IdentityUnavailable,
        JobError,
        PermissionError,
        ValueError,
    ):
        print(
            "本机维护未确认成功；请使用本机交互终端和专属存储配置。",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
