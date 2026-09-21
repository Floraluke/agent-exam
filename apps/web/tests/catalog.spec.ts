import { expect, test } from "@playwright/test";
import { loginOwner, navigation } from "./support/workbench";

test("multiple task and configuration summaries remain browsable", async ({ page }) => {
  const task = {
    task_id: "00000000-0000-0000-0000-000000000001", instance_id: "first-task",
    dataset_id: "synthetic", dataset_revision: "fixed", split: "train", repo: "first/repo",
    base_commit: "a".repeat(40), problem_statement_preview: "Visible preview",
  };
  const configuration = {
    agent_configuration_id: "00000000-0000-0000-0000-000000000003",
    display_name: "first-config", agent_type: "codex", agent_version: "test",
    model_provider: "openai_chatgpt", model: "test", configuration_fingerprint: "b".repeat(64),
    enabled: true,
  };
  await page.route("**/api/v1/tasks?**", (route) => route.fulfill({ json: {
    items: [task, { ...task, task_id: "00000000-0000-0000-0000-000000000002",
      instance_id: "second-task" }], next_cursor: null,
  } }));
  await page.route("**/api/v1/agent-configurations?**", (route) => route.fulfill({ json: {
    items: [configuration, { ...configuration,
      agent_configuration_id: "00000000-0000-0000-0000-000000000004",
      display_name: "second-config" }], next_cursor: null,
  } }));
  await loginOwner(page);
  await navigation(page).getByRole("button", { name: "任务目录" }).click();
  await expect(page.getByRole("button", { name: "查看 first-task" })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看 second-task" })).toBeVisible();
  await navigation(page).getByRole("button", { name: "配置目录" }).click();
  await expect(page.getByRole("button", { name: "查看 first-config" })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看 second-config" })).toBeVisible();
});

test("owner registers catalogs; collaborator browses but cannot manage them", async ({ page, browser }) => {
  await loginOwner(page);
  await navigation(page).getByRole("button", { name: "任务目录" }).click();
  const tasks = page.getByRole("region", { name: "任务目录" });
  await expect(tasks).toBeVisible();
  await tasks.getByRole("button", { name: "登记已核验题目" }).click();
  await tasks.getByRole("button", { name: "查看 example__repo-1" }).click();
  await expect(tasks.getByText("Fix the visible bug.", { exact: true })).toBeVisible();
  await navigation(page).getByRole("button", { name: "配置目录" }).click();
  const agents = page.getByRole("region", { name: "Codex 配置目录" });
  await agents.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  await agents.getByRole("button", { name: "查看 Synthetic Codex" }).click();
  await expect(agents.getByText("推理强度：medium")).toBeVisible();

  await navigation(page).getByRole("button", { name: "成员管理" }).click();
  const members = page.getByRole("region", { name: "成员管理" });
  await members.getByRole("button", { name: "创建邀请码" }).click();
  const token = await members.getByLabel("仅此一次的邀请码").inputValue();
  const guest = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const join = await guest.newPage();
    await join.goto(page.url());
    await join.getByRole("button", { name: "使用邀请码加入" }).click();
    await join.getByLabel("邀请码", { exact: true }).fill(token);
    await join.getByLabel("新账号", { exact: true }).fill("catalog_teammate");
    await join.getByLabel("新密码", { exact: true }).fill("synthetic teammate password");
    await join.getByRole("button", { name: "加入平台" }).click();
    await expect(join.getByText("加入成功，请使用新账号登录。")).toBeVisible();
    await join.getByLabel("账号", { exact: true }).fill("catalog_teammate");
    await join.getByLabel("密码", { exact: true }).fill("synthetic teammate password");
    await join.getByRole("button", { name: "登录", exact: true }).click();
    await navigation(join).getByRole("button", { name: "任务目录" }).click();
    const guestTasks = join.getByRole("region", { name: "任务目录" });
    await guestTasks.getByLabel("仓库筛选").fill("no/match");
    await guestTasks.getByRole("button", { name: "筛选任务" }).click();
    await expect(guestTasks.getByText("暂无匹配任务")).toBeVisible();
    await guestTasks.getByLabel("仓库筛选").fill("example/repo");
    await guestTasks.getByRole("button", { name: "筛选任务" }).click();
    await guestTasks.getByRole("button", { name: "查看 example__repo-1" }).click();
    await expect(guestTasks.getByText("Fix the visible bug.", { exact: true })).toBeVisible();
    await expect(join.getByRole("button", { name: "登记已核验题目" })).toHaveCount(0);
    await expect(join.getByRole("button", { name: "禁用 Synthetic Codex" })).toHaveCount(0);
    await navigation(page).getByRole("button", { name: "配置目录" }).click();
    await agents.getByRole("button", { name: "禁用 Synthetic Codex" }).click();
    await expect(agents.getByText("已禁用（保留历史）")).toBeVisible();
    await navigation(join).getByRole("button", { name: "配置目录" }).click();
    await join.reload();
    await expect(join.getByText("已禁用（保留历史）")).toBeVisible();
    await expect(join.locator("body")).not.toContainText("HIDDEN_ANSWER");
    await expect(join.locator("body")).not.toContainText("private-test-reference");
  } finally { await guest.close(); }
});
