import { expect, test } from "@playwright/test";

test("owner lands on the A workbench and navigation stays client-side", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();

  const navigation = page.getByRole("navigation", { name: "主导航" });
  await expect(page.getByRole("heading", { name: "所有者工作台" })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "工作台" })).toHaveAttribute(
    "aria-current",
    "page",
  );

  const writes: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "GET") writes.push(request.url());
  });
  await navigation.getByRole("button", { name: "新建评测" }).click();
  await expect(page.getByRole("heading", { name: "新建评测" })).toBeVisible();
  await expect.poll(() => new URL(page.url()).searchParams.get("view")).toBe("new");
  expect(writes).toEqual([]);
});

test("owner reaches existing catalogs through the A sidebar and reloads the view", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();

  const navigation = page.getByRole("navigation", { name: "主导航" });
  await navigation.getByRole("button", { name: "任务目录" }).click();
  await expect(page.getByRole("region", { name: "任务目录" })).toBeVisible();
  await page.getByRole("button", { name: "登记已核验题目" }).click();

  await navigation.getByRole("button", { name: "配置目录" }).click();
  await expect(page.getByRole("region", { name: "Codex 配置目录" })).toBeVisible();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get("view"))
    .toBe("agents");

  await page.reload();
  await expect(page.getByRole("region", { name: "Codex 配置目录" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "主导航" })
    .getByRole("button", { name: "配置目录" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});

test("three-step submission keeps selections and opens the created job", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const navigation = page.getByRole("navigation", { name: "主导航" });
  await navigation.getByRole("button", { name: "任务目录" }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await navigation.getByRole("button", { name: "配置目录" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  await navigation.getByRole("button", { name: "新建评测" }).click();

  const wizard = page.getByRole("region", { name: "新建评测向导" });
  await expect(wizard.getByRole("heading", { name: "选择评测任务" })).toBeVisible();
  await wizard.getByLabel("任务 example__repo-1").check();
  await wizard.getByRole("button", { name: "下一步" }).click();
  await expect(wizard.getByRole("heading", { name: "选择 Agent 配置" }))
    .toBeVisible();
  await wizard.getByLabel("配置 Synthetic Codex").check();
  await wizard.getByRole("button", { name: "下一步" }).click();
  await expect(wizard.getByRole("heading", { name: "核对并提交" })).toBeVisible();
  await expect(wizard).toContainText("1 道题 × 1 个配置 = 1 个 Run");

  await wizard.getByRole("button", { name: "上一步" }).click();
  await expect(wizard.getByLabel("配置 Synthetic Codex")).toBeChecked();
  await wizard.getByRole("button", { name: "上一步" }).click();
  await expect(wizard.getByLabel("任务 example__repo-1")).toBeChecked();
  await wizard.getByRole("button", { name: "下一步" }).click();
  await wizard.getByRole("button", { name: "下一步" }).click();

  const submitted = page.waitForResponse((response) =>
    response.request().method() === "POST" &&
    new URL(response.url()).pathname === "/api/v1/jobs",
  );
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  const created = await (await submitted).json();
  await expect.poll(() => new URL(page.url()).searchParams.get("job"))
    .toBe(created.job_id);
  await expect.poll(() => new URL(page.url()).searchParams.get("view")).toBe("jobs");
  await expect(page.getByText("等待所有者批准", { exact: true })).toBeVisible();
});

test("job list filters server results and restores a linked detail", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const navigation = page.getByRole("navigation", { name: "主导航" });
  await navigation.getByRole("button", { name: "任务目录" }).click();
  await page.getByRole("button", { name: "登记已核验题目" }).click();
  await navigation.getByRole("button", { name: "配置目录" }).click();
  await page.getByRole("button", { name: "登记固定 Codex 配置" }).click();
  await navigation.getByRole("button", { name: "新建评测" }).click();
  const wizard = page.getByRole("region", { name: "新建评测向导" });
  await wizard.getByLabel("任务 example__repo-1").check();
  await wizard.getByRole("button", { name: "下一步" }).click();
  await wizard.getByLabel("配置 Synthetic Codex").check();
  await wizard.getByRole("button", { name: "下一步" }).click();
  const submitted = page.waitForResponse((response) =>
    response.request().method() === "POST" &&
    new URL(response.url()).pathname === "/api/v1/jobs",
  );
  await wizard.getByRole("button", { name: "提交并等待批准" }).click();
  const created = await (await submitted).json();

  await navigation.getByRole("button", { name: "评测", exact: true }).click();
  const list = page.getByRole("region", { name: "评测列表" });
  await expect(list).toBeVisible();
  await list.getByLabel("状态筛选").selectOption("AWAITING_OWNER_APPROVAL");
  await list.getByRole("button", { name: "应用筛选" }).click();
  await expect(list).toContainText(created.job_id);
  await list.getByRole("button", { name: `查看评测 ${created.job_id}` }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get("job"))
    .toBe(created.job_id);

  await page.reload();
  await expect(page.getByText("等待所有者批准", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "返回评测列表" }).click();
  await expect(page.getByRole("region", { name: "评测列表" })
    .getByLabel("状态筛选")).toHaveValue("AWAITING_OWNER_APPROVAL");
  await expect(page.getByRole("region", { name: "评测列表" }))
    .toContainText(created.job_id);
});
