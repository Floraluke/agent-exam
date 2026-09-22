// 动作后刷新失败的呈现：写请求已经被服务端受理，但随后的重读失败时，
// 页面必须显式说明"当前显示的可能不是最新状态"，且不得出现假成功。
// 造数据靠夹具控制端点 POST /__test__/http/fail-next-response（一次生效）；
// 本 spec 独立成文件，因为造数据的用例不能与别的用例共享后端状态。
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import {
  loginOwner, openWizard, registerCatalog, reviewSelection,
} from "../support/workbench";

const backend = "http://127.0.0.1:8875/__test__";
const controlHeaders = {
  Origin: "https://127.0.0.1:3100", "X-AgentExam-Request": "1",
};
// 用户可见的过期提示（与 submit.tsx 的文案一致）。
const STALE = "刷新失败，当前显示的可能不是最新状态，请手动刷新。";

// 注入：让下一次匹配的响应以给定稳定错误码收束。只对 GET 的批次详情生效，
// 因此同一次点击里的写请求（POST /approve）不受影响。
async function failNextDetailRead(page: Page, jobId: string) {
  const armed = await page.request.post(`${backend}/http/fail-next-response`, {
    headers: controlHeaders,
    data: {
      method: "GET", path_suffix: `/api/v1/jobs/${jobId}`,
      status: "503", code: "DEPENDENCY_UNAVAILABLE",
    },
  });
  expect(armed.ok()).toBeTruthy();
}

async function submitSingle(page: Page) {
  const jobs = await openWizard(page);
  await reviewSelection(jobs, ["example__repo-1"]);
  // 批次 ID 取自创建响应：URL 的 job 参数是提交成功后才写上的。
  const created = page.waitForResponse((response) =>
    response.request().method() === "POST" &&
    new URL(response.url()).pathname === "/api/v1/jobs");
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  const jobId = (await (await created).json()).job_id as string;
  expect(jobId).toBeTruthy();
  await expect(jobs.getByText("等待所有者批准", { exact: true })).toBeVisible();
  return { jobs, jobId };
}

// 端点未调用时行为必须不变：没有注入时详情重读照常成功、页面照常推进。
test("未注入故障时批准照常重读详情", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page);
  const { jobs } = await submitSingle(page);
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  await expect(jobs.getByText(/^决定者：/)).toBeVisible();
  await expect(jobs.getByRole("alert")).toHaveCount(0);
  await expect(jobs.getByText(STALE)).toHaveCount(0);
});

test("批准成功但重读失败：提示可能已过期，且不出现假成功", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page);
  const { jobs, jobId } = await submitSingle(page);
  await failNextDetailRead(page, jobId);

  await jobs.getByRole("button", { name: "批准并排队" }).click();
  // 原有的重读失败文案照常显示，另加过期提示。
  await expect(jobs.getByRole("alert"))
    .toHaveText("平台存储暂不可用，请稍后重试。");
  await expect(jobs.getByText(STALE)).toBeVisible();
  // 不得出现假成功：页面无法确认新状态时，不能自称已批准。
  await expect(jobs.getByText("已批准，等待执行", { exact: true })).toHaveCount(0);
  await expect(jobs.getByText(/^决定者：/)).toHaveCount(0);
  // 提示不是摆设：手动刷新成功一次后，页面读出真实状态，提示随之消失。
  await jobs.getByRole("button", { name: "刷新当前批次" }).click();
  await expect(jobs.getByText(/^决定者：/)).toBeVisible();
  await expect(jobs.getByText(STALE)).toHaveCount(0);
});

test("动作冲突且重读失败：保留冲突文案并提示可能已过期", async ({ page }) => {
  await loginOwner(page);
  await registerCatalog(page);
  const { jobs, jobId } = await submitSingle(page);

  // 外部先批准这个批次，让本页的决定必然冲突（本页仍停留在等待批准）。
  // 走同源代理路径，才会带上浏览器的会话 Cookie；可信写请求头仍按服务端要求显式给出。
  const approved = await page.request.post(`/api/v1/jobs/${jobId}/approve`, {
    headers: { ...controlHeaders, "Idempotency-Key": "external-approval-key" },
    data: {},
  });
  expect(approved.ok(), `${approved.status()} ${await approved.text()}`)
    .toBeTruthy();
  await failNextDetailRead(page, jobId);

  await jobs.getByRole("button", { name: "拒绝批次" }).click();
  // 既有错误文案逐字保留。
  await expect(jobs.getByRole("alert"))
    .toHaveText("批次状态已经改变，请刷新后查看。");
  await expect(jobs.getByText(STALE)).toBeVisible();
  // 不得出现假成功：被拒绝是页面没有确认过的事，不能显示。
  await expect(jobs.getByText("已拒绝", { exact: true })).toHaveCount(0);
  await expect(jobs.getByText("等待所有者批准", { exact: true })).toBeVisible();
});
