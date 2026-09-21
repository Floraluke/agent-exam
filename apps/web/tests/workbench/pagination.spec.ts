import { expect, test } from "@playwright/test";

test("job list pages forward and back with the server cursor", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const navigation = page.getByRole("navigation", { name: "主导航" });
  await navigation.getByRole("button", { name: "任务目录" }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await navigation.getByRole("button", { name: "配置目录" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();

  await page.evaluate(async () => {
    const read = async (path: string) => (await fetch(path)).json();
    const tasks = await read("/api/v1/tasks?limit=20");
    const agents = await read("/api/v1/agent-configurations?limit=20&enabled=true");
    const options = await read("/api/v1/job-options");
    const body = {
      task_ids: [tasks.items[0].task_id],
      agent_configuration_ids: [agents.items[0].agent_configuration_id],
      evaluation_track: "closed_book",
      batch_preset: options.batch_presets[0].batch_preset,
      limit_profile_id: options.limit_profiles[0].limit_profile_id,
    };
    for (let index = 0; index < 21; index += 1) {
      const response = await fetch("/api/v1/jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-AgentExam-Request": "1",
          "Idempotency-Key": `pagination-job-${String(index).padStart(4, "0")}`,
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(`setup failed: ${response.status}`);
    }
  });

  await navigation.getByRole("button", { name: "评测", exact: true }).click();
  const list = page.getByRole("region", { name: "评测列表" });
  await expect(list.locator(".job-row")).toHaveCount(20);
  await list.getByRole("button", { name: "下一页" }).click();
  await expect(list.locator(".job-row")).toHaveCount(1);
  await expect(list.getByRole("button", { name: "上一页" })).toBeVisible();
  await list.getByRole("button", { name: "上一页" }).click();
  await expect(list.locator(".job-row")).toHaveCount(20);
});
