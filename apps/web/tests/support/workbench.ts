import type { Locator, Page } from "@playwright/test";

export async function loginOwner(page: Page) {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
}

export function navigation(page: Page) {
  return page.getByRole("navigation", { name: "主导航" });
}

export async function registerCatalog(page: Page, secondTask = false) {
  const nav = navigation(page);
  await nav.getByRole("button", { name: "任务目录" }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  if (secondTask) {
    await page.evaluate(async () => {
      const response = await fetch("/api/v1/tasks/register", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-AgentExam-Request": "1" },
        body: JSON.stringify({ preset_id: "swe-gym-lite-example-2" }),
      });
      if (!response.ok) throw new Error("second synthetic task registration failed");
    });
  }
  await nav.getByRole("button", { name: "配置目录" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
}

export async function openWizard(page: Page) {
  await navigation(page).getByRole("button", { name: "新建评测" }).click();
  return page.getByRole("region", { name: "提交评测" });
}

export async function reviewSelection(jobs: Locator, taskNames: string[]) {
  for (const name of taskNames) await jobs.getByLabel(`任务 ${name}`).check();
  await jobs.getByRole("button", { name: "下一步" }).click();
  await jobs.getByLabel("配置 Synthetic Codex").check();
  await jobs.getByRole("button", { name: "下一步" }).click();
}
