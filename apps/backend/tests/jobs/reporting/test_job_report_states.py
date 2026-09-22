"""批次报告的中间状态契约：未完成批次可读，未产出结果的 Run 记 incomplete。

来源：B 2026-09-22 的"批次报告契约空缺"。D 复现后确认现状已经定义该行为，且前端进度区
就消费这些字段（`apps/web/src/features/jobs/batch-report.tsx` 的 stage_message /
completed_runs / failed_runs / pending_runs），因此未完成批次必须保持可读：
不是 404（那会与"不存在或无权"混淆）、不是 409、也不是把零计数当成结果。
"""

from identity.conftest import WRITE_HEADERS
from jobs.conftest import job_api
from jobs.test_http import submission, submit


def _create(api, key):
    task, agent = api.register_catalogs()
    body = submission(task["task_id"], agent["agent_configuration_id"])
    return submit(api, body, key).json()


def _report(api, job_id):
    return api.client.get(f"/api/v1/reports/jobs/{job_id}")


def test_awaiting_batch_is_readable_and_does_not_fake_zero_results():
    with job_api(result_scope="official") as api:
        assert api.login().status_code == 200
        created = _create(api, "state-awaiting-0001")

        response = _report(api, created["job_id"])
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "AWAITING_OWNER_APPROVAL"
        assert body["stage_message"]
        assert (body["completed_runs"], body["failed_runs"]) == (0, 0)
        assert body["pending_runs"] == 1
        run = body["runs"][0]
        assert run["outcome"] == "incomplete"
        assert run["resolved"] is None
        # report_path 是"去单 Run 报告的链接"，不是"结果是否可用"的标志。
        assert run["report_path"] == f"/api/v1/reports/runs/{run['run_id']}"


def test_queued_and_preparing_batches_stay_readable():
    with job_api(result_scope="official") as api:
        assert api.login().status_code == 200
        created = _create(api, "state-queued-0001")
        job_id = created["job_id"]

        approved = api.client.post(
            f"/api/v1/jobs/{job_id}/approve",
            json={},
            headers={**WRITE_HEADERS, "Idempotency-Key": "state-approve-0001"},
        )
        assert approved.status_code == 200
        queued = _report(api, job_id)
        assert queued.status_code == 200
        assert queued.json()["status"] == "QUEUED"

        claimed = api.repository.claim("state-worker", api.clock())
        assert claimed is not None
        preparing = _report(api, job_id)
        assert preparing.status_code == 200
        assert preparing.json()["status"] == "PREPARING"
        assert preparing.json()["runs"][0]["outcome"] == "incomplete"


def test_comparison_matrix_accepts_a_batch_without_results():
    with job_api(result_scope="official") as api:
        assert api.login().status_code == 200
        created = _create(api, "state-compare-0001")

        response = api.client.get(
            "/api/v1/reports/comparisons", params={"job_ids": created["job_id"]}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["rows"][0]["cells"][0]["outcome"] == "incomplete"
        assert body["totals"][0]["missing"] == 0


def test_canceled_batch_report_stays_readable():
    """2026-09-22 的实际故障：批次取消后查报告曾 500 INTERNAL_ERROR。"""

    with job_api(result_scope="official") as api:
        assert api.login().status_code == 200
        created = _create(api, "state-canceled-0001")
        job_id = created["job_id"]

        canceled = api.client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            json={"reason": "契约回归"},
            headers={**WRITE_HEADERS, "Idempotency-Key": "state-cancel-key"},
        )
        assert canceled.status_code in {200, 202}

        response = _report(api, job_id)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "CANCELED"
        assert body["stage_message"]
        assert body["runs"][0]["outcome"] == "incomplete"
        assert body["runs"][0]["resolved"] is None


def test_cancel_requested_batch_report_stays_readable():
    with job_api(result_scope="official") as api:
        assert api.login().status_code == 200
        created = _create(api, "state-cancel-requested-0001")
        job_id = created["job_id"]

        approved = api.client.post(
            f"/api/v1/jobs/{job_id}/approve",
            json={},
            headers={**WRITE_HEADERS, "Idempotency-Key": "state-cancel-req-approve"},
        )
        assert approved.status_code == 200
        claimed = api.repository.claim("state-cancel-worker", api.clock())
        assert claimed is not None
        api.repository.start_execution(claimed.lease, api.clock())

        requested = api.client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            json={"reason": "契约回归"},
            headers={**WRITE_HEADERS, "Idempotency-Key": "state-cancel-req-key"},
        )
        assert requested.status_code in {200, 202}

        response = _report(api, job_id)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "CANCEL_REQUESTED"
        assert body["stage_message"]


def test_internal_test_batch_stays_hidden():
    with job_api() as api:
        assert api.login().status_code == 200
        created = _create(api, "state-internal-0001")

        response = _report(api, created["job_id"])
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "JOB_NOT_FOUND"
