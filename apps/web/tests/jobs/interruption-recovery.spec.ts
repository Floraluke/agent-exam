import { expect, test } from "@playwright/test";
import { loginOwner, openWizard, registerCatalog, reviewSelection } from "../support/workbench";

const backend = "http://127.0.0.1:8875/__test__";
const controlHeaders = {
  Origin: "https://127.0.0.1:3100", "X-AgentExam-Request": "1",
};

test.afterEach(async ({ request }) => {
  await request.post(`${backend}/worker/resume`, { headers: controlHeaders });
});

test("owner closes an expired job and creates a separately approved retry", async ({
  page,
}) => {
  await loginOwner(page);
  await registerCatalog(page);
  const jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1"]);
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  expect((await page.request.post(`${backend}/worker/pause`, {
    headers: controlHeaders,
  })).ok()).toBeTruthy();
  const approved = page.waitForResponse((candidate) =>
    candidate.request().method() === "POST" &&
    new URL(candidate.url()).pathname.endsWith("/approve"),
  );
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  expect((await approved).ok()).toBeTruthy();
  const interrupted = await page.request.post(`${backend}/jobs/interrupt-next`, {
    headers: controlHeaders,
  });
  expect(interrupted.ok()).toBeTruthy();
  const source = (await interrupted.json()).job_id as string;
  expect(source).toBeTruthy();

  await jobs.getByRole("button", { name: "刷新当前批次" }).click();
  const recovery = jobs.getByRole("region", { name: "中断恢复" });
  await expect(recovery).toContainText("系统不会自动续跑");
  const recovered = page.waitForResponse((candidate) =>
    candidate.request().method() === "POST" &&
    new URL(candidate.url()).pathname.endsWith(`/jobs/${source}/recover`),
  );
  await recovery.getByRole("button", { name: "检查并收束中断" }).click();
  expect(await (await recovered).json()).toMatchObject({
    status: "FAILED", failure_code: "INFRASTRUCTURE_INTERRUPTED",
  });
  await expect(recovery).toContainText("已完成 Run 的结果保持不变");
  await expect(recovery).toContainText("阶段中断");
  await expect(recovery).not.toContainText("internal-browser-interrupted");

  const retried = page.waitForResponse((candidate) =>
    candidate.request().method() === "POST" &&
    new URL(candidate.url()).pathname.endsWith(`/jobs/${source}/retry`),
  );
  await recovery.getByRole("button", { name: "新建重试批次" }).click();
  const replacement = await (await retried).json();
  expect(replacement.job_id).not.toBe(source);
  expect(replacement).toMatchObject({
    status: "AWAITING_OWNER_APPROVAL", rerun_of_job_id: source,
  });
  await expect.poll(() => new URL(page.url()).searchParams.get("job"))
    .toBe(replacement.job_id);
  await expect(jobs.getByText("等待所有者批准", { exact: true })).toBeVisible();
  await expect(jobs).toContainText(`重试来源：${source}`);
});
