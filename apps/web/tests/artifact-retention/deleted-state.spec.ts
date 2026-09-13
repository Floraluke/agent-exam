import { expect, test } from "@playwright/test";

const backend = "http://127.0.0.1:8875/__test__";
const headers = {
  Origin: "https://127.0.0.1:3100", "X-AgentExam-Request": "1",
};

test("run report keeps audit metadata after owner-only local cleanup", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  const jobs = page.getByRole("region", { name: "提交评测" });
  await jobs.getByRole("button", { name: "刷新可提交选项" }).click();
  await jobs.getByLabel("任务 example__repo-1").check();
  await jobs.getByLabel("配置 Synthetic Codex").check();
  const submitted = page.waitForResponse((response) =>
    response.request().method() === "POST" &&
    new URL(response.url()).pathname === "/api/v1/jobs",
  );
  await jobs.getByRole("button", { name: "提交等待批准" }).click();
  const job = await (await submitted).json();
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  await expect.poll(async () => {
    const response = await page.request.get(`/api/v1/jobs/${job.job_id}`);
    return (await response.json()).status;
  }).toBe("COMPLETED");
  await jobs.getByRole("button", { name: "刷新当前批次" }).click();
  await jobs.getByRole("button", { name: "查看单题运行报告" }).click();
  const evidence = jobs.getByRole("region", { name: "安全证据" });
  await expect(evidence).toContainText("受限原始制品：3 个，等待到期维护");

  const report = await page.request.get(`/api/v1/reports/runs/${job.run_ids[0]}`);
  const raw = (await report.json()).artifact_links.filter(
    (item: { retention_class: string }) => item.retention_class === "raw_30d",
  );
  expect(raw).toHaveLength(3);
  const cleaned = await page.request.post(`${backend}/artifacts/expire-and-clean`, {
    headers,
  });
  expect(cleaned.ok()).toBeTruthy();
  expect(await cleaned.json()).toMatchObject({ deleted: 3, recovered: 0 });

  await jobs.getByRole("button", { name: "查看单题运行报告" }).click();
  await expect(evidence).toContainText("已按保留策略清理：3 个；审计仍保留");
  await expect(evidence).not.toContainText("下载原始");
  const updated = await page.request.get(`/api/v1/reports/runs/${job.run_ids[0]}`);
  const deletedRaw = (await updated.json()).artifact_links.filter(
    (item: { retention_class: string }) => item.retention_class === "raw_30d",
  );
  expect(deletedRaw).toHaveLength(3);
  expect(deletedRaw[0]).toMatchObject({
    content_status: "deleted",
    deleted_by: expect.any(String),
    deletion_reason: "raw_retention_expired",
    created_at: expect.any(String),
    deleted_at: expect.any(String),
    size_bytes: expect.any(Number),
    sha256: expect.stringMatching(/^[0-9a-f]{64}$/),
  });
  await expect(evidence).toContainText(deletedRaw[0].sha256);
  await expect(evidence).toContainText(deletedRaw[0].deleted_by);
  const deleted = await page.request.get(
    `/api/v1/artifacts/${raw[0].artifact_id}/content`,
  );
  expect(deleted.status()).toBe(410);
  expect((await deleted.json()).error.code).toBe("ARTIFACT_CONTENT_DELETED");
});
