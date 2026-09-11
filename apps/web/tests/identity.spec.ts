import { expect, test } from "@playwright/test";

test("owner logs in through HTTP, survives reload, and logs out", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码").fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByText("已登录：owner")).toBeVisible();
  await page.reload();
  await expect(page.getByText("已登录：owner")).toBeVisible();
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByLabel("账号", { exact: true })).toBeVisible();
  await page.screenshot({ path: "../../runtime/tests/identity-login.png", fullPage: true });
});

test("wrong password is explained without signing the owner in", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码").fill("wrong synthetic password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("region", { name: "平台账号" }).getByRole("alert"))
    .toHaveText("账号或密码不正确，或登录已失效。");
  await expect(page.getByRole("button", { name: "退出登录" })).toHaveCount(0);
  await expect(page.getByLabel("密码")).toHaveValue("");
});
