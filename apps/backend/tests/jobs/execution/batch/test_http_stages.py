from datetime import UTC, datetime

from identity.conftest import WRITE_HEADERS
from jobs.execution.support.fakes import artifact
from jobs.test_http import submission, submit

from eval_platform.domain.result import ExecutionTrialResult, TerminationReason


def _report(jobs_api, job_id):
    response = jobs_api.client.get(f"/api/v1/reports/jobs/{job_id}")
    assert response.status_code == 200
    return response.json()


def test_http_report_exposes_each_persisted_batch_stage(internal_reports_api):
    jobs_api = internal_reports_api
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "batch-stage-source-0001",
    ).json()
    job_id, run_id = created["job_id"], created["run_ids"][0]

    waiting = _report(jobs_api, job_id)
    assert waiting["status"] == "AWAITING_OWNER_APPROVAL"
    assert "不会启动执行" in waiting["stage_message"]

    jobs_api.client.post(
        f"/api/v1/jobs/{job_id}/approve",
        json={},
        headers={**WRITE_HEADERS, "Idempotency-Key": "batch-stage-approve-0001"},
    )
    assert _report(jobs_api, job_id)["status"] == "QUEUED"

    now = datetime(2026, 9, 12, 17, 0, tzinfo=UTC)
    claimed = jobs_api.repository.claim("stage-worker", now)
    assert claimed is not None
    preparing = _report(jobs_api, job_id)
    assert preparing["status"] == "PREPARING"
    assert preparing["runs"][0]["stage"] == "preparing"

    lease = jobs_api.repository.start_execution(claimed.lease, now)
    assert _report(jobs_api, job_id)["status"] == "EXECUTING"
    lease = jobs_api.repository.start_run(lease, run_id, now)
    running = _report(jobs_api, job_id)
    assert running["runs"][0]["stage"] == "running_agent"
    lease = jobs_api.repository.finish_run_execution(lease, run_id, now)
    collecting = _report(jobs_api, job_id)
    assert collecting["runs"][0]["stage"] == "collecting"

    trial = ExecutionTrialResult(
        run_id,
        "harbor-stage-job",
        "harbor-stage-trial",
        TerminationReason.COMPLETED,
        artifact(
            jobs_api.run_artifacts,
            run_id,
            "agent_patch",
            b"diff --git a/a b/a\n",
            "text/x-diff",
        ),
        None,
    )
    lease = jobs_api.repository.start_verifying(lease, trial, now)
    verifying = _report(jobs_api, job_id)
    assert verifying["runs"][0]["stage"] == "verifying"
    lease = jobs_api.repository.fail(
        lease, run_id, "EVIDENCE_UNAVAILABLE", "受控测试失败。", now, trial
    )
    lease = jobs_api.repository.start_finalizing(lease, now)
    assert _report(jobs_api, job_id)["status"] == "FINALIZING"
    jobs_api.repository.finish(lease, now)
    terminal = _report(jobs_api, job_id)
    assert terminal["status"] == "FAILED"
    assert terminal["runs"][0]["outcome"] == "infrastructure_error"
    run_report = jobs_api.client.get(f"/api/v1/reports/runs/{run_id}").json()
    assert run_report["run"]["backend_job_ref"] == "harbor-stage-job"
    assert "\\" not in run_report["run"]["backend_job_ref"]


def test_internal_test_jobs_are_absent_from_both_formal_report_queries(jobs_api):
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "internal-report-filter-0001",
    ).json()

    job = jobs_api.client.get(f"/api/v1/reports/jobs/{created['job_id']}")
    run = jobs_api.client.get(f"/api/v1/reports/runs/{created['run_ids'][0]}")
    assert job.status_code == 404
    assert run.status_code == 404


def test_rejected_report_counts_canceled_run_as_incomplete(internal_reports_api):
    jobs_api = internal_reports_api
    jobs_api.login()
    task, agent = jobs_api.register_catalogs()
    created = submit(
        jobs_api,
        submission(task["task_id"], agent["agent_configuration_id"]),
        "rejected-report-source-0001",
    ).json()
    response = jobs_api.client.post(
        f"/api/v1/jobs/{created['job_id']}/reject",
        json={"reason": "不进入执行"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "rejected-report-0001"},
    )
    assert response.status_code == 200

    report = _report(jobs_api, created["job_id"])
    assert report["status"] == "REJECTED"
    assert report["pending_runs"] == 1
    assert report["runs"][0]["outcome"] == "incomplete"
