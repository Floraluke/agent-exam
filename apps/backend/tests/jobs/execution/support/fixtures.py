from datetime import datetime
from hashlib import sha256
from uuid import uuid4

from catalog.conftest import task_bundle

from eval_platform.domain.agent import AgentConfiguration
from eval_platform.domain.jobs.models import (
    AgentSnapshot,
    EvaluationJob,
    EvaluationRun,
    LimitSnapshot,
    NetworkPolicySnapshot,
    StateEvent,
    TaskSnapshot,
    ToolProfileSnapshot,
)


def queued_job(now: datetime):
    bundle = task_bundle()
    job_id, run_id = str(uuid4()), str(uuid4())
    task = TaskSnapshot(
        str(uuid4()),
        bundle.public.instance_id,
        bundle.public.dataset_id,
        bundle.public.dataset_revision,
        bundle.public.split,
        bundle.public.repo,
        bundle.public.base_commit,
        bundle.public.problem_statement,
        bundle.public.environment_image,
        bundle.public.raw_record_sha256,
        sha256(bundle.public.problem_statement.encode()).hexdigest(),
        str(uuid4()),
        "tasks/source.json",
        bundle.public.raw_record_sha256,
    )
    config = AgentConfiguration(
        str(uuid4()),
        "codex",
        "test-version",
        "openai_chatgpt",
        "test-model",
        "chatgpt_auth_json",
        "test-profile",
        {"reasoning_effort": "medium"},
    )
    agent = AgentSnapshot(
        config.configuration_id,
        "Synthetic Codex",
        config.agent_name,
        config.agent_version,
        config.model_provider,
        config.model_name,
        config.authentication_type,
        config.credential_configuration_id,
        "medium",
        config.fingerprint,
    )
    run = EvaluationRun(
        run_id,
        job_id,
        task,
        agent,
        "PENDING",
        "mock",
        "a" * 40,
        "v1",
        now,
        (StateEvent(str(uuid4()), 1, None, "PENDING", "JOB_SUBMITTED", now),),
    )
    limits = LimitSnapshot(
        900,
        2,
        8192,
        20480,
        300,
        4,
        16384,
        256,
        262144,
        1048576,
        52428800,
        209715200,
        1,
        0,
    )
    job = EvaluationJob(
        job_id,
        str(uuid4()),
        now,
        "QUEUED",
        "closed_book",
        "internal_test",
        "demo",
        "default-single-host-v1",
        limits,
        "closed-v1",
        NetworkPolicySnapshot("closed_book", "disabled", False),
        "codex-v1",
        ToolProfileSnapshot("codex", "disabled", False),
        "a" * 40,
        "b" * 40,
        "c" * 40,
        (run,),
        (
            StateEvent(
                str(uuid4()),
                1,
                None,
                "AWAITING_OWNER_APPROVAL",
                "JOB_SUBMITTED",
                now,
            ),
            StateEvent(
                str(uuid4()),
                2,
                "AWAITING_OWNER_APPROVAL",
                "QUEUED",
                "OWNER_APPROVED",
                now,
                job_id,
            ),
        ),
        job_id,
        now,
        None,
        1,
    )
    return job, bundle
