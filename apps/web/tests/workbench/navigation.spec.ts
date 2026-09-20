import { expect, test } from "@playwright/test";

test("secondary navigation restores, cancel returns to jobs, and logout clears URL state", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码", { exact: true }).fill("synthetic browser password");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const navigation = page.getByRole("navigation", { name: "主导航" });

  await navigation.getByRole("button", { name: "排行榜" }).click();
  await expect(page.getByRole("region", { name: "基础排行榜" })).toBeVisible();
  await expect.poll(() => new URL(page.url()).searchParams.get("view"))
    .toBe("leaderboard");
  await page.reload();
  await expect(page.getByRole("region", { name: "基础排行榜" })).toBeVisible();

  await page.getByRole("navigation", { name: "主导航" })
    .getByRole("button", { name: "新建评测" }).click();
  await page.getByRole("button", { name: "取消新建" }).click();
  await expect(page.getByRole("region", { name: "评测列表" })).toBeVisible();
  await expect.poll(() => new URL(page.url()).searchParams.get("view")).toBe("jobs");

  await page.getByRole("navigation", { name: "主导航" })
    .getByRole("button", { name: "评测", exact: true }).click();
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByRole("heading", { name: "登录平台" })).toBeVisible();
  await expect.poll(() => new URL(page.url()).search).toBe("");
});
