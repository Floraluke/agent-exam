import { expect, test } from "@playwright/test";

test("390 and 360 layouts use a closing menu without page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();

  const menu = page.getByRole("button", { name: "打开主导航" });
  const navigation = page.getByRole("navigation", { name: "主导航" });
  await expect(menu).toBeVisible();
  await expect(navigation).not.toBeVisible();
  await menu.click();
  await expect(navigation).toBeVisible();
  await navigation.getByRole("button", { name: "新建评测" }).click();
  await expect(navigation).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "新建评测" })).toBeVisible();
  await expect(page.getByRole("button", { name: "取消新建" })).toBeVisible();
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )).toBe(true);
  await page.screenshot({
    path: "../../runtime/tests/task-02-workbench-mobile-390.png", fullPage: true,
  });

  await page.setViewportSize({ width: 360, height: 800 });
  await expect(page.getByRole("heading", { name: "新建评测" })).toBeVisible();
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )).toBe(true);
});
