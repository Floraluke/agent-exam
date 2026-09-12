"""Validate, freeze and query Jobs without executing any Agent or evaluator."""

import hashlib
import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import uuid4

from eval_platform.application.agent_registry import AgentRegistry
from eval_platform.application.ports.repositories import JobRepository
from eval_platform.application.task_catalog import TaskCatalog
from eval_platform.domain.identity import AuthenticatedActor
from eval_platform.domain.jobs.models import (
    AgentSnapshot,
    EvaluationJob,
    EvaluationRun,
    JobConfigurationDisabled,
    JobInputError,
    JobNotFound,
    LimitSnapshot,
    StateEvent,
    TaskSnapshot,
)
from eval_platform.domain.jobs.policy import SubmissionPolicy, canonical_request_sha

_KEY = re.compile(r"[A-Za-z0-9._~-]{8,128}")


class JobSubmission:
    def __init__(
        self,
        tasks: TaskCatalog,
        agents: AgentRegistry,
        repository: JobRepository,
        policy: SubmissionPolicy,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.tasks = tasks
        self.agents = agents
        self.repository = repository
        self.policy = policy
        self.clock = clock

    def submit(
        self,
        actor: AuthenticatedActor,
        task_ids: Sequence[str],
        agent_configuration_ids: Sequence[str],
        evaluation_track: str,
        batch_preset: str,
        limit_profile_id: str,
        idempotency_key: str,
    ) -> EvaluationJob:
        normalized_tasks = tuple(sorted(set(task_ids)))
        normalized_agents = tuple(sorted(set(agent_configuration_ids)))
        batch = self.policy.batch(batch_preset)
        limits = self.policy.limits(limit_profile_id)
        if not normalized_tasks or not normalized_agents:
            raise JobInputError("EMPTY_JOB_SELECTION")
        if evaluation_track != "closed_book":
            raise JobInputError("EVALUATION_TRACK_NOT_ENABLED")
        if limits is None:
            raise JobInputError("LIMIT_PROFILE_NOT_ALLOWED")
        if (
            batch is None
            or not batch.minimum_tasks <= len(normalized_tasks) <= batch.maximum_tasks
            or len(normalized_agents) > self.policy.maximum_agent_configurations
            or len(normalized_tasks) * len(normalized_agents) > self.policy.maximum_runs
        ):
            raise JobInputError("BATCH_PRESET_EXCEEDED")
        if not _KEY.fullmatch(idempotency_key):
            raise JobInputError("IDEMPOTENCY_KEY_INVALID")
        request_sha = canonical_request_sha(
            normalized_tasks,
            normalized_agents,
            evaluation_track,
            batch_preset,
            limit_profile_id,
        )
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        replay = self.repository.resolve_idempotency(
            actor.user_id, key_hash, request_sha
        )
        if replay is not None:
            return replay
        task_snapshots = tuple(
            TaskSnapshot.from_record(self.tasks.get(actor, task_id))
            for task_id in normalized_tasks
        )
        agent_records = tuple(
            self.agents.get(actor, configuration_id)
            for configuration_id in normalized_agents
        )
        if any(not item.enabled for item in agent_records):
            raise JobConfigurationDisabled
        agent_snapshots = tuple(
            AgentSnapshot.from_record(item) for item in agent_records
        )
        record = self._build(
            actor,
            task_snapshots,
            agent_snapshots,
            batch_preset,
            limit_profile_id,
            limits.snapshot(),
        )
        return self.repository.create(record, key_hash, request_sha)

    def get(self, actor: AuthenticatedActor, job_id: str) -> EvaluationJob:
        record = self.repository.get(job_id)
        if actor.role != "owner" and record.created_by != actor.user_id:
            raise JobNotFound
        return record

    def list(
        self,
        actor: AuthenticatedActor,
        filters: dict[str, str],
        cursor: str | None,
        limit: int,
    ) -> tuple[list[EvaluationJob], str | None]:
        requested_creator = filters.pop("created_by", None)
        if actor.role == "owner":
            scope = requested_creator
        elif requested_creator not in {None, actor.user_id}:
            return [], None
        else:
            scope = actor.user_id
        records = self.repository.list(scope, filters, cursor, limit + 1)
        page = records[:limit]
        return page, page[-1].job_id if len(records) > limit else None

    def _build(
        self,
        actor: AuthenticatedActor,
        tasks: tuple[TaskSnapshot, ...],
        agents: tuple[AgentSnapshot, ...],
        batch_preset: str,
        limit_profile_id: str,
        limit_snapshot: LimitSnapshot,
    ) -> EvaluationJob:
        job_id, now = str(uuid4()), self.clock()
        event = StateEvent(
            str(uuid4()),
            1,
            None,
            "AWAITING_OWNER_APPROVAL",
            "JOB_SUBMITTED",
            now,
            actor.user_id,
        )
        backend = "mock" if self.policy.result_scope == "internal_test" else "harbor"
        runs = tuple(
            EvaluationRun(
                str(uuid4()),
                job_id,
                task,
                agent,
                "PENDING",
                backend,
                self.policy.harbor_revision,
                self.policy.execution_contract_version,
                now,
                (StateEvent(str(uuid4()), 1, None, "PENDING", "JOB_SUBMITTED", now),),
            )
            for task in tasks
            for agent in agents
        )
        return EvaluationJob(
            job_id,
            actor.user_id,
            now,
            "AWAITING_OWNER_APPROVAL",
            "closed_book",
            self.policy.result_scope,
            batch_preset,
            limit_profile_id,
            limit_snapshot,
            self.policy.network_policy_id,
            self.policy.network_policy_snapshot,
            self.policy.tool_profile_id,
            self.policy.tool_profile_snapshot,
            self.policy.harbor_revision,
            self.policy.swe_gym_revision,
            self.policy.swe_bench_fork_revision,
            runs,
            (event,),
        )
