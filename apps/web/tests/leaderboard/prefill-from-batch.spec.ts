// 排行榜按上下文预填：从批次详情的入口进入排行榜，表单带出这批冻结的比较条件，
// 但**不自动查询**——用户仍要自己点「查询排行榜」，查询仍走原有接口。
// 本 spec 自己造批次数据，因此独立成文件。
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import {
  loginOwner, openWizard, registerCatalog, reviewSelection,
} from "../support/workbench";

// 夹具任务的冻结比较条件（与 tests/catalog/conftest.py 的 task_bundle 一致）。
const FROZEN = {
  datasetId: "synthetic-dataset", datasetRevision: "a".repeat(40),
  split: "train", repo: "example/repo", toolProfileId: "codex-fixed-v1",
};
const ENTRY = "按此条件查排行榜";

// 目录只登记一次：重复登记配置会新增第二个同名配置，把后续定位变成歧义。
test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage();
  await loginOwner(page);
  await registerCatalog(page, true);
  await page.close();
});

async function submit(page: Page, tasks: string[]) {
  const jobs = await openWizard(page);
  await reviewSelection(jobs, tasks);
  const created = page.waitForResponse((response) =>
    response.request().method() === "POST" &&
    new URL(response.url()).pathname === "/api/v1/jobs");
  await jobs.getByRole("button", { name: "提交并等待批准" }).click();
  const jobId = (await (await created).json()).job_id as string;
  await expect(jobs.getByText("等待所有者批准", { exact: true })).toBeVisible();
  return { jobs, jobId };
}

test("从批次入口进排行榜：表单被预填，点查询仍走原有接口", async ({ page }) => {
  const queries: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/v1/leaderboard") {
      queries.push(request.url());
    }
  });
  await loginOwner(page);
  const { jobs } = await submit(page, ["example__repo-1"]);
  // 先让批次进入终态，这样预填出来的条件真的能查到这一批。
  await jobs.getByRole("button", { name: "批准并排队" }).click();
  await expect.poll(async () => {
    await jobs.getByRole("button", { name: "刷新当前批次" }).click();
    return jobs.getByText("执行完成", { exact: true }).count();
  }, { timeout: 20_000 }).toBe(1);

  await page.getByRole("link", { name: ENTRY }).click();
  const leaderboard = page.getByRole("region", { name: "基础排行榜" });
  await expect(leaderboard).toBeVisible();
  // URL 带出冻结条件，且只读：预填不改写、不删除这些参数。
  const url = new URL(page.url());
  expect(url.searchParams.get("view")).toBe("leaderboard");
  expect(url.searchParams.get("dataset_id")).toBe(FROZEN.datasetId);
  expect(url.searchParams.get("dataset_revision")).toBe(FROZEN.datasetRevision);
  expect(url.searchParams.get("split")).toBe(FROZEN.split);
  expect(url.searchParams.get("repo")).toBe(FROZEN.repo);
  expect(url.searchParams.get("tool_profile_id")).toBe(FROZEN.toolProfileId);
  // 表单被预填（含可选的工具策略）。
  await expect(leaderboard.getByLabel("数据集 ID")).toHaveValue(FROZEN.datasetId);
  await expect(leaderboard.getByLabel("数据集 revision"))
    .toHaveValue(FROZEN.datasetRevision);
  await expect(leaderboard.getByLabel("数据集 split")).toHaveValue(FROZEN.split);
  await expect(leaderboard.getByLabel("代码仓库")).toHaveValue(FROZEN.repo);
  await expect(leaderboard.getByLabel("工具策略（可选）"))
    .toHaveValue(FROZEN.toolProfileId);
  // 刻意不自动查询：进来时没有任何榜单请求，也没有结果。
  expect(queries).toEqual([]);
  await expect(leaderboard.getByText("并列第")).toHaveCount(0);

  await leaderboard.getByRole("button", { name: "查询排行榜" }).click();
  await expect(leaderboard).toContainText("并列第 1 名");
  // 分母是范围内全部题目（本夹具已登记两道题），不是本批次跑了几个 Run。
  await expect(leaderboard).toContainText("1 / 2 · 50.0%");
  // 查询仍走原有接口，且用的就是预填出来的冻结条件。
  expect(queries).toHaveLength(1);
  const query = new URL(queries[0]).searchParams;
  expect(new URL(queries[0]).pathname).toBe("/api/v1/leaderboard");
  expect(query.get("evaluation_track")).toBe("closed_book");
  expect(query.get("dataset_id")).toBe(FROZEN.datasetId);
  expect(query.get("dataset_revision")).toBe(FROZEN.datasetRevision);
  expect(query.get("split")).toBe(FROZEN.split);
  expect(query.get("repo")).toBe(FROZEN.repo);
  expect(query.get("tool_profile_id")).toBe(FROZEN.toolProfileId);
});

test("冻结条件不一致的批次不提供排行榜入口", async ({ page }) => {
  await loginOwner(page);
  const { jobs } = await submit(page, ["example__repo-1", "example__repo-2"]);
  // 两道题同属一个数据集时条件一致，入口照常出现。
  await expect(jobs.getByRole("link", { name: ENTRY })).toBeVisible();

  // 让服务端详情里的第二道题落在另一个 revision：条件不再唯一，入口必须消失。
  await page.route(/\/api\/v1\/jobs\/[^/?]+\?*$/, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.task_snapshots[1].dataset_revision = "b".repeat(40);
    await route.fulfill({ response, json: body });
  });
  await jobs.getByRole("button", { name: "刷新当前批次" }).click();
  await expect(jobs.getByRole("link", { name: ENTRY })).toHaveCount(0);
});
