import { expect, test, type Page } from "@playwright/test";
import { rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const clockFile = resolve(__dirname, "../../../runtime/tests/identity-browser-clock.txt");
test.afterEach(async () => { await rm(clockFile, { force: true }); });

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("账号", { exact: true }).fill("owner");
  await page.getByLabel("密码").fill("synthetic browser password");
  const pending = page.waitForResponse((response) =>
    response.url().endsWith("/api/v1/auth/login") && response.request().method() === "POST");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const response = await pending;
  expect(response.status()).toBe(200);
  await expect(page.getByText("已登录：owner")).toBeVisible();
  return response;
}

test("HTTPS session cookie is protected and absent from scripts and response bodies", async ({ page }) => {
  const response = await signIn(page);
  const cookies = await page.context().cookies();
  expect(cookies).toEqual(expect.arrayContaining([expect.objectContaining({
    name: "__Host-agentexam_session", secure: true, httpOnly: true,
    sameSite: "Strict", path: "/",
  })]));
  const cookie = cookies.find((item) => item.name === "__Host-agentexam_session")!;
  const visibleCookie = await page.evaluate(() => document.cookie);
  expect(visibleCookie).not.toContain(cookie.name);
  expect(visibleCookie).not.toContain(cookie.value);
  expect(await response.text()).not.toContain(cookie.value);
  expect(await response.text()).not.toContain("synthetic browser password");
  expect(Object.keys(await response.json()).sort()).toEqual(["role", "user_id", "username"]);
});

test("replaying a cookie after logout cannot restore the browser identity", async ({ page }) => {
  await signIn(page);
  const cookie = (await page.context().cookies())
    .find((item) => item.name === "__Host-agentexam_session")!;
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByLabel("账号", { exact: true })).toBeVisible();
  await page.context().addCookies([cookie]);
  const pending = page.waitForResponse((response) => response.url().endsWith("/api/v1/auth/me"));
  await page.reload();
  expect((await pending).status()).toBe(401);
  await expect(page.getByLabel("账号", { exact: true })).toBeVisible();
});

test("server expiry rejects a still-present browser cookie after eight hours", async ({ page }) => {
  await signIn(page);
  await writeFile(clockFile, "28800", "ascii");
  expect((await page.context().cookies())
    .some((cookie) => cookie.name === "__Host-agentexam_session")).toBe(true);
  const pending = page.waitForResponse((response) => response.url().endsWith("/api/v1/auth/me"));
  await page.reload();
  expect((await pending).status()).toBe(401);
  await expect(page.getByLabel("账号", { exact: true })).toBeVisible();
});

for (const endpoint of ["login", "logout"]) {
  test(`cross-site ${endpoint} form is rejected without changing the owner identity`, async ({ page }) => {
    await signIn(page);
    const action = new URL(`/api/v1/auth/${endpoint}`, page.url()).href;
    // Only the synthetic attacker page is intercepted; the platform POST is real.
    await page.route("https://attacker.invalid/**", (route) => route.fulfill({
      contentType: "text/html; charset=utf-8",
      body: `<meta charset="utf-8"><form method="POST" action="${action}">
        <input name="username" value="owner">
        <input name="password" value="synthetic browser password">
        <button>提交跨站表单</button></form>`,
    }));
    await page.goto("https://attacker.invalid/");
    const pending = page.waitForResponse((response) => response.url() === action);
    await page.getByRole("button", { name: "提交跨站表单" }).click();
    const response = await pending;
    expect(await response.request().headerValue("origin")).toBe("https://attacker.invalid");
    expect(await response.request().headerValue("cookie")).toBeNull();
    expect(response.status()).toBe(403);
    expect((await response.json()).error.code).toBe("FORBIDDEN");
    await page.goto("/");
    await expect(page.getByText("已登录：owner")).toBeVisible();
  });
}

test("same-origin writes still require the explicit request header", async ({ page }) => {
  await signIn(page);
  const status = await page.evaluate(async () => {
    const response = await fetch("/api/v1/auth/logout", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
    });
    return response.status;
  });
  expect(status).toBe(403);
  await page.reload();
  await expect(page.getByText("已登录：owner")).toBeVisible();
});
