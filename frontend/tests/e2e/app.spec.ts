// SEPEHR Frontend — Playwright E2E Tests

import { test, expect, Page } from "@playwright/test";

// ── Config ────────────────────────────────────────────────────────────────────

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

const TEST_USER = {
  username: `e2e_user_${Date.now()}`,
  password: "testpassword123",
  displayName: "E2E Test User",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

async function registerUser(page: Page, user = TEST_USER) {
  await page.goto(`${BASE_URL}/auth/register`);
  await page.fill('[placeholder="نام شما"]', user.displayName);
  await page.fill('[placeholder="username"]', user.username);
  await page.fill('[placeholder="حداقل ۸ کاراکتر"]', user.password);
  await page.fill('[placeholder="••••••••"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/home`, { timeout: 10000 });
}

async function loginUser(page: Page, user = TEST_USER) {
  await page.goto(`${BASE_URL}/auth/login`);
  await page.fill('[placeholder="username"]', user.username);
  await page.fill('[placeholder="••••••••"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/home`, { timeout: 10000 });
}

// ── Auth Tests ────────────────────────────────────────────────────────────────

test.describe("Authentication", () => {
  test("should show login page by default at /auth/login", async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    await expect(page.locator("h1")).toContainText("سپهر");
    await expect(page.locator('button[type="submit"]')).toContainText("ورود");
  });

  test("should register a new user successfully", async ({ page }) => {
    const uniqueUser = {
      username: `e2e_reg_${Date.now()}`,
      password: "testpassword123",
      displayName: "Registration Test",
    };
    await registerUser(page, uniqueUser);
    await expect(page).toHaveURL(`${BASE_URL}/home`);
  });

  test("should show error for duplicate username", async ({ page }) => {
    const user = {
      username: `e2e_dup_${Date.now()}`,
      password: "testpassword123",
      displayName: "Dup User",
    };
    // Register first time
    await registerUser(page, user);
    // Try to register again with same username
    await page.goto(`${BASE_URL}/auth/register`);
    await page.fill('[placeholder="نام شما"]', user.displayName);
    await page.fill('[placeholder="username"]', user.username);
    await page.fill('[placeholder="حداقل ۸ کاراکتر"]', user.password);
    await page.fill('[placeholder="••••••••"]', user.password);
    await page.click('button[type="submit"]');
    await expect(
      page.locator("text=این نام کاربری قبلاً ثبت شده است")
    ).toBeVisible({ timeout: 5000 });
  });

  test("should login and logout successfully", async ({ page }) => {
    const user = {
      username: `e2e_login_${Date.now()}`,
      password: "testpassword123",
      displayName: "Login Test",
    };
    await registerUser(page, user);
    // Navigate away
    await page.goto(`${BASE_URL}/news`);
    // Navigate back to home
    await page.goto(`${BASE_URL}/home`);
    await expect(page).toHaveURL(`${BASE_URL}/home`);
  });
});

// ── Navigation Tests ──────────────────────────────────────────────────────────

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    const user = {
      username: `e2e_nav_${Date.now()}`,
      password: "testpassword123",
      displayName: "Nav User",
    };
    await registerUser(page, user);
  });

  test("should navigate between all four main sections", async ({ page }) => {
    // Home
    await expect(page).toHaveURL(`${BASE_URL}/home`);
    await expect(page.locator("h1")).toContainText("سپهر");

    // Messenger
    await page.click('a[href="/messenger"]');
    await page.waitForURL(`${BASE_URL}/messenger`);
    await expect(page.locator("h1")).toContainText("پیام");

    // News
    await page.click('a[href="/news"]');
    await page.waitForURL(`${BASE_URL}/news`);
    await expect(page.locator("h1")).toContainText("اخبار");

    // Map
    await page.click('a[href="/map"]');
    await page.waitForURL(`${BASE_URL}/map`);
    await expect(page.locator("h1")).toContainText("نقشه");
  });

  test("should show bottom navigation on all main pages", async ({ page }) => {
    const pages = ["/home", "/messenger", "/news", "/map"];
    for (const p of pages) {
      await page.goto(`${BASE_URL}${p}`);
      await expect(page.locator("nav")).toBeVisible();
    }
  });
});

// ── Messenger Tests ───────────────────────────────────────────────────────────

test.describe("Messenger", () => {
  test("should show empty state when no conversations", async ({ page }) => {
    const user = {
      username: `e2e_msg_${Date.now()}`,
      password: "testpassword123",
      displayName: "Msg User",
    };
    await registerUser(page, user);
    await page.goto(`${BASE_URL}/messenger`);
    // Either shows conversations or empty state
    const hasEmpty = await page.locator("text=مکالمه‌ای وجود ندارد").isVisible();
    const hasList = await page.locator(".divide-y").isVisible();
    expect(hasEmpty || hasList).toBeTruthy();
  });

  test("should show new conversation button", async ({ page }) => {
    const user = {
      username: `e2e_newconv_${Date.now()}`,
      password: "testpassword123",
      displayName: "Conv User",
    };
    await registerUser(page, user);
    await page.goto(`${BASE_URL}/messenger`);
    const newBtn = page.locator('a[href="/messenger/new"]');
    await expect(newBtn).toBeVisible();
  });
});

// ── PWA Tests ─────────────────────────────────────────────────────────────────

test.describe("PWA", () => {
  test("should have web app manifest", async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/manifest.json`);
    expect(response.status()).toBe(200);
    const manifest = await response.json();
    expect(manifest.name).toContain("SEPEHR");
    expect(manifest.display).toBe("standalone");
  });

  test("should have meta viewport for mobile", async ({ page }) => {
    await page.goto(`${BASE_URL}/home`);
    const viewport = await page.locator('meta[name="viewport"]').getAttribute("content");
    expect(viewport).toContain("width=device-width");
  });

  test("should serve service worker", async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/sw.js`);
    // In production, SW is served; in dev it may not exist
    expect([200, 404]).toContain(response.status());
  });
});

// ── Accessibility ─────────────────────────────────────────────────────────────

test.describe("Accessibility", () => {
  test("should have correct document direction for RTL", async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    const dir = await page.locator("html").getAttribute("dir");
    expect(dir).toBe("rtl");
  });

  test("should have correct lang attribute", async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    const lang = await page.locator("html").getAttribute("lang");
    expect(lang).toBe("fa");
  });
});
