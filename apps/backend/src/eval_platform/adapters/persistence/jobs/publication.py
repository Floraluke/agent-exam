"""One transaction for idempotent Job, full matrix and initial events."""

from dataclasses import asdict
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from eval_platform.domain.catalog import AgentConfigurationNotFound, TaskNotFound
from eval_platform.domain.jobs.models import (
    EvaluationJob,
    JobConfigurationDisabled,
    JobIdempotencyConflict,
    JobUnavailable,
)


def publish(
    connection: psycopg.Connection[Any],
    record: EvaluationJob,
    key_hash: str,
    request_sha256: str,
) -> str:
    inserted = connection.execute(
        "INSERT INTO evaluation_jobs "
        "(job_id,created_by,created_at,status,evaluation_track,result_scope,"
        "batch_preset,limit_profile_id,limit_snapshot,network_policy_id,"
        "network_policy_snapshot,tool_profile_id,tool_profile_snapshot,"
        "harbor_revision,swe_gym_revision,swe_bench_fork_revision,trial_count,"
        "idempotency_key_hash,request_sha256) VALUES "
        "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (created_by,idempotency_key_hash) DO NOTHING RETURNING job_id",
        (
            record.job_id,
            record.created_by,
            record.created_at,
            record.status,
            record.evaluation_track,
            record.result_scope,
            record.batch_preset,
            record.limit_profile_id,
            Jsonb(asdict(record.limit_snapshot)),
            record.network_policy_id,
            Jsonb(asdict(record.network_policy_snapshot)),
            record.tool_profile_id,
            Jsonb(asdict(record.tool_profile_snapshot)),
            record.harbor_revision,
            record.swe_gym_revision,
            record.swe_bench_fork_revision,
            record.trial_count,
            key_hash,
            request_sha256,
        ),
    ).fetchone()
    if inserted is None:
        original = connection.execute(
            "SELECT job_id,request_sha256 FROM evaluation_jobs "
            "WHERE created_by=%s AND idempotency_key_hash=%s",
            (record.created_by, key_hash),
        ).fetchone()
        if original is None or original["request_sha256"] != request_sha256:
            raise JobIdempotencyConflict
        return str(original["job_id"])
    _validate_catalog(connection, record)
    for run in record.runs:
        connection.execute(
            "INSERT INTO evaluation_runs "
            "(run_id,job_id,task_id,agent_configuration_id,attempt_index,"
            "task_snapshot,agent_snapshot,execution_contract_version,backend_kind,"
            "backend_revision,status,created_at) VALUES "
            "(%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s)",
            (
                run.run_id,
                record.job_id,
                run.task.task_id,
                run.agent.agent_configuration_id,
                Jsonb(asdict(run.task)),
                Jsonb(asdict(run.agent)),
                run.execution_contract_version,
                run.backend_kind,
                run.backend_revision,
                run.status,
                run.created_at,
            ),
        )
        event = run.state_events[0]
        connection.execute(
            "INSERT INTO run_state_events VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (
                event.event_id,
                run.run_id,
                event.sequence,
                event.from_status,
                event.to_status,
                event.reason_code,
                event.occurred_at,
            ),
        )
    event = record.state_events[0]
    connection.execute(
        "INSERT INTO job_state_events "
        "(event_id,job_id,sequence,from_status,to_status,reason_code,"
        "actor_user_id,occurred_at,note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            event.event_id,
            record.job_id,
            event.sequence,
            event.from_status,
            event.to_status,
            event.reason_code,
            event.actor_user_id or record.created_by,
            event.occurred_at,
            event.note,
        ),
    )
    return record.job_id


def _validate_catalog(
    connection: psycopg.Connection[Any], record: EvaluationJob
) -> None:
    for run in record.runs:
        task = connection.execute(
            "SELECT t.*,a.artifact_id,a.object_key,a.sha256 FROM evaluation_tasks t "
            "JOIN artifact_records a ON a.artifact_id=t.source_snapshot_ref "
            "WHERE t.task_id=%s FOR SHARE OF t,a",
            (run.task.task_id,),
        ).fetchone()
        if task is None:
            raise TaskNotFound
        expected = {
            "instance_id": run.task.instance_id,
            "dataset_id": run.task.dataset_id,
            "dataset_revision": run.task.dataset_revision,
            "split": run.task.split,
            "repo": run.task.repo,
            "base_commit": run.task.base_commit,
            "problem_statement": run.task.problem_statement,
            "environment_image": run.task.environment_image,
            "raw_record_sha256": run.task.raw_record_sha256,
            "problem_sha256": run.task.problem_sha256,
            "artifact_id": run.task.artifact_id,
            "object_key": run.task.source_object_key,
            "sha256": run.task.source_sha256,
        }
        if any(str(task[key]) != value for key, value in expected.items()):
            raise JobUnavailable
        agent = connection.execute(
            "SELECT * FROM agent_configurations WHERE agent_configuration_id=%s "
            "FOR SHARE",
            (run.agent.agent_configuration_id,),
        ).fetchone()
        if agent is None:
            raise AgentConfigurationNotFound
        if not agent["enabled"]:
            raise JobConfigurationDisabled
        expected_agent = {
            "display_name": run.agent.display_name,
            "agent_type": run.agent.agent_type,
            "agent_version": run.agent.agent_version,
            "model_provider": run.agent.model_provider,
            "model": run.agent.model,
            "authentication_type": run.agent.authentication_type,
            "credential_profile_id": run.agent.credential_profile_id,
            "configuration_fingerprint": run.agent.configuration_fingerprint,
        }
        if any(str(agent[key]) != value for key, value in expected_agent.items()):
            raise JobUnavailable
        if agent["public_options"] != {"reasoning_effort": run.agent.reasoning_effort}:
            raise JobUnavailable
