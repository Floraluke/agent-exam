"""Browser-gated leaderboard projection over synthetic in-memory Jobs."""

from collections.abc import Callable
from datetime import datetime

from eval_platform.domain.leaderboard import (
    AgentIdentity,
    AttemptMetrics,
    ComparisonScope,
    LeaderboardAttempt,
    LeaderboardPage,
    LeaderboardQuery,
    LeaderboardTask,
    build_rows,
    paginate,
)


class BrowserLeaderboardRepository:
    def __init__(self, tasks, jobs, clock: Callable[[], datetime]) -> None:
        self.tasks = tasks
        self.jobs = jobs
        self.clock = clock

    def page(self, query: LeaderboardQuery) -> LeaderboardPage:
        records = tuple(
            record
            for record in self.tasks.records.values()
            if record.task.dataset_id == query.dataset_id
            and record.task.dataset_revision == query.dataset_revision
            and record.task.split == query.split
            and (query.repo is None or record.task.repo == query.repo)
        )
        tasks = tuple(
            LeaderboardTask(item.task_id, item.task.instance_id, item.task.repo)
            for item in records
        )
        attempts = tuple(
            self._attempt(job, run)
            for job in self.jobs.records.values()
            for run in job.runs
            if job.evaluation_track == query.evaluation_track
            and (
                query.tool_profile_id is None
                or job.tool_profile_id == query.tool_profile_id
            )
        )
        rows = build_rows(tasks, attempts, self.clock(), "internal_test")
        return paginate(rows, query.cursor, query.limit)

    def _attempt(self, job, run) -> LeaderboardAttempt:
        report = self.jobs.get_run_report(run.run_id)
        result = report.deterministic_result
        usage = report.process_metrics.usage
        resources = report.process_metrics.resources
        task, agent = run.task, run.agent
        return LeaderboardAttempt(
            ComparisonScope(
                task.dataset_id,
                task.dataset_revision,
                task.split,
                task.repo,
                job.evaluation_track,
                job.network_policy_id,
                job.network_policy_snapshot,
                job.tool_profile_id,
                job.tool_profile_snapshot,
                job.limit_profile_id,
                job.limit_snapshot,
                job.harbor_revision,
                job.swe_gym_revision,
                job.swe_bench_fork_revision,
                run.execution_contract_version,
            ),
            AgentIdentity(
                agent.agent_configuration_id,
                agent.display_name,
                agent.agent_type,
                agent.agent_version,
                agent.model_provider,
                agent.model,
                agent.reasoning_effort,
                agent.configuration_fingerprint,
            ),
            task.task_id,
            task.instance_id,
            job.job_id,
            job.rerun_of_job_id,
            run.run_id,
            job.created_at,
            run.finished_at or job.finished_at or job.created_at,
            job.status,
            run.status,
            run.failure_code,
            None if result is None else result.resolved,
            None if result is None else result.created_at,
            AttemptMetrics(
                usage.n_input_tokens,
                usage.n_cache_tokens,
                usage.n_output_tokens,
                usage.cost_usd,
                resources.wall_time_sec,
                resources.cpu_time_sec,
                resources.peak_memory_bytes,
            ),
            job.result_scope,
        )
