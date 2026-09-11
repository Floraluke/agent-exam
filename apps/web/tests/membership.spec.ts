import { expect, test } from "@playwright/test";

test("owner invites a collaborator and disabling the member revokes browser access", async ({ page, browser }) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const members = page.getByRole("region", { name: "成员管理" });
  await expect(members).toBeVisible();
  await members.getByRole("button", { name: "创建邀请码" }).click();
  const token = await members.getByLabel("仅此一次的邀请码").inputValue();
  expect(token.length).toBeGreaterThan(30);
  await members.getByRole("button", { name: "刷新成员与邀请" }).click();
  await expect(members.getByLabel("仅此一次的邀请码")).toHaveCount(0);
  await page.reload();
  await expect(members.getByLabel("仅此一次的邀请码")).toHaveCount(0);

  const guest = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const join = await guest.newPage();
    await join.goto(page.url());
    await join.getByRole("button", { name: "使用邀请码加入" }).click();
    await join.getByLabel("邀请码", { exact: true }).fill(token);
    await join.getByLabel("新账号", { exact: true }).fill("browser_teammate");
    await join.getByLabel("新密码", { exact: true }).fill("synthetic teammate password");
    await join.getByRole("button", { name: "加入平台" }).click();
    await expect(join.getByText("加入成功，请使用新账号登录。")).toBeVisible();
    await join.getByLabel("账号", { exact: true }).fill("browser_teammate");
    await join.getByLabel("密码", { exact: true }).fill("synthetic teammate password");
    await join.getByRole("button", { name: "登录", exact: true }).click();
    await expect(join.getByText("已登录：browser_teammate")).toBeVisible();
    await expect(join.getByRole("region", { name: "成员管理" })).toHaveCount(0);
    await page.reload();
    await members.getByRole("button", { name: "停用 browser_teammate" }).click();
    await expect(members.getByText("browser_teammate（已停用）")).toBeVisible();
    await join.reload();
    await expect(join.getByLabel("账号", { exact: true })).toBeVisible();
  } finally { await guest.close(); }
});
