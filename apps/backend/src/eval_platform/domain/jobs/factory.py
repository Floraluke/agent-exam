"""Create a complete immutable pending Job from validated frozen inputs."""

from datetime import datetime
from uuid import uuid4

from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.models import (
    AgentSnapshot,
    EvaluationJob,
    EvaluationRun,
    LimitSnapshot,
    StateEvent,
    TaskSnapshot,
)
from eval_platform.domain.jobs.policy import SubmissionPolicy


def build_job(
    actor: AuthenticatedActor,
    tasks: tuple[TaskSnapshot, ...],
    agents: tuple[AgentSnapshot, ...],
    batch_preset: str,
    limit_profile_id: str,
    limits: LimitSnapshot,
    policy: SubmissionPolicy,
    now: datetime,
    *,
    created_by: str | None = None,
    rerun_of_job_id: str | None = None,
) -> EvaluationJob:
    creator = created_by or actor.user_id
    job_id = str(uuid4())
    event = StateEvent(
        str(uuid4()),
        1,
        None,
        "AWAITING_OWNER_APPROVAL",
        "JOB_SUBMITTED",
        now,
        actor.user_id,
    )
    backend = "mock" if policy.result_scope == "internal_test" else "harbor"
    runs = tuple(
        EvaluationRun(
            str(uuid4()),
            job_id,
            task,
            agent,
            "PENDING",
            backend,
            policy.harbor_revision,
            policy.execution_contract_version,
            now,
            (
                StateEvent(
                    str(uuid4()),
                    1,
                    None,
                    "PENDING",
                    "JOB_SUBMITTED",
                    now,
                ),
            ),
        )
        for task in tasks
        for agent in agents
    )
    return EvaluationJob(
        job_id,
        creator,
        now,
        "AWAITING_OWNER_APPROVAL",
        "closed_book",
        policy.result_scope,
        batch_preset,
        limit_profile_id,
        limits,
        policy.network_policy_id,
        policy.network_policy_snapshot,
        policy.tool_profile_id,
        policy.tool_profile_snapshot,
        policy.harbor_revision,
        policy.swe_gym_revision,
        policy.swe_bench_fork_revision,
        runs,
        (event,),
        rerun_of_job_id=rerun_of_job_id,
    )
