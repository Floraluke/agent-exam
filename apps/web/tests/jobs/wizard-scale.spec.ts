import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { loginOwner, navigation, openWizard, registerCatalog } from "../support/workbench";

const SENTINELS = [
  "HIDDEN_ANSWER", "hidden_test", "hidden_pass", "private-test-reference",
  "gold_patch", "test_patch", "object_key",
];

async function register(page: Page, path: string, presetId: string) {
  const accepted = await page.evaluate(async ({ path, presetId }) => {
    const response = await fetch(path, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-AgentExam-Request": "1" },
      body: JSON.stringify({ preset_id: presetId }),
    });
    return response.ok;
  }, { path, presetId });
  expect(accepted).toBeTruthy();
}

/** registerCatalog 只登记 preset 1/2 与第一个配置；这里补齐到六题两个配置。 */
async function registerFullCatalog(page: Page) {
  await registerCatalog(page, true);
  for (const index of [3, 4, 5, 6]) {
    await register(page, "/api/v1/tasks/register", `swe-gym-lite-example-${index}`);
  }
  await register(page, "/api/v1/agent-configurations", "codex-0153-terra-low");
}

async function selectWizard(page: Page, tasks: string[], agents: string[]) {
  const wizard = await openWizard(page);
  for (const name of tasks) {
    await wizard.getByLabel(`任务 ${name}`, { exact: true }).check();
  }
  await wizard.getByRole("button", { name: "下一步" }).click();
  for (const name of agents) {
    await wizard.getByLabel(`配置 ${name}`).check();
  }
  return wizard;
}

test("six tasks and two configs submit under the continuous scale", async ({ page }) => {
  await loginOwner(page);
  await registerFullCatalog(page);
  const tasks = ["example__repo-1", "example__repo-2", "example__repo-3",
    "example__repo-4", "example__repo-5", "example__repo-6"];
  const wizard = await selectWizard(page, tasks, ["Synthetic Codex", "Synthetic Terra"]);

  // 新预设由服务端提供，前端不硬编码：显示区间与选项都在。
  const batch = wizard.getByLabel("批次规模");
  await expect(batch.getByRole("option", { name: /continuous（1–20 题）/ })).toHaveCount(1);
  await batch.selectOption("continuous");

  await wizard.getByRole("button", { name: "下一步" }).click();
  await expect(wizard.getByText("6 道题 × 2 个配置 = 12 个 Run")).toBeVisible();
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  await expect(page.getByRole("heading", { name: "评测详情" })).toBeVisible();
  await expect(page.getByText("等待所有者批准").first()).toBeVisible();

  // 网页面读取面：目录、向导与详情都不出现隐藏字段哨兵。
  const nav = navigation(page);
  for (const view of ["任务目录", "配置目录"]) {
    await nav.getByRole("button", { name: view, exact: true }).click();
    await expect(page.getByRole("region", { name: view })).toBeVisible();
    for (const sentinel of SENTINELS) {
      await expect(page.locator("body")).not.toContainText(sentinel);
    }
  }
});

test("a scale above the selected preset is refused with a stable error", async ({ page }) => {
  await loginOwner(page);
  await registerFullCatalog(page);
  // demo 的上限是 3 题；选 4 题后提交必须被服务端拒绝，而不是假成功。
  const wizard = await selectWizard(page,
    ["example__repo-1", "example__repo-2", "example__repo-3", "example__repo-4"],
    ["Synthetic Codex"]);
  await expect(wizard.getByLabel("批次规模")).toHaveValue("demo");
  await wizard.getByRole("button", { name: "下一步" }).click();
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  // 向导页上有两个 role="alert"（外层面板与向导各一），限定到向导区域内。
  await expect(page.getByRole("region", { name: "新建评测向导" }).getByRole("alert"))
    .toContainText("任务或配置数量不符合所选批次规模。");
  await expect(page.getByRole("heading", { name: "评测详情" })).not.toBeVisible();

  // 改用 continuous 后同一选择可以提交——错误来自服务端规模，不是选项本身。
  await wizard.getByRole("button", { name: "上一步" }).click();
  await wizard.getByLabel("批次规模").selectOption("continuous");
  await wizard.getByRole("button", { name: "下一步" }).click();
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  await expect(page.getByRole("heading", { name: "评测详情" })).toBeVisible();
});
