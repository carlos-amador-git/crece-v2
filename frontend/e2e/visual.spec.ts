import { test, expect } from "@playwright/test";
import { injectAuthState, mockDashboardApis } from "./helpers/auth";

// ---------------------------------------------------------------------------
// Visual smoke tests — capture screenshots and verify structural integrity
// ---------------------------------------------------------------------------

test.describe("Visual smoke tests", () => {
  test.describe("Login page", () => {
    test("screenshot — desktop viewport", async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 720 });
      await page.goto("/login");
      await page.waitForLoadState("networkidle");

      await page.screenshot({
        path: "e2e/screenshots/login-desktop.png",
        fullPage: true,
      });
    });

    test("screenshot — mobile viewport", async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto("/login");
      await page.waitForLoadState("networkidle");

      await page.screenshot({
        path: "e2e/screenshots/login-mobile.png",
        fullPage: true,
      });
    });
  });

  test.describe("Dashboard pages (authenticated)", () => {
    test.beforeEach(async ({ page }) => {
      await mockDashboardApis(page);
      await injectAuthState(page);
    });

    test("screenshot — dashboard overview", async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto("/dashboard");
      await page.waitForLoadState("networkidle");

      await page.screenshot({
        path: "e2e/screenshots/dashboard-overview.png",
        fullPage: true,
      });
    });

    test("screenshot — dirigentes page", async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto("/dashboard/dirigentes");
      await page.waitForLoadState("networkidle");

      await page.screenshot({
        path: "e2e/screenshots/dirigentes.png",
        fullPage: true,
      });
    });

    test("screenshot — electoral page", async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto("/dashboard/electoral");
      await page.waitForLoadState("networkidle");

      await page.screenshot({
        path: "e2e/screenshots/electoral.png",
        fullPage: true,
      });
    });
  });
});

// ---------------------------------------------------------------------------
// Console error checks — verify pages render without JS errors
// ---------------------------------------------------------------------------

test.describe("Console error checks", () => {
  test("login page has no console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    // Filter out known noise (e.g. favicon 404, React dev mode warnings)
    const significantErrors = errors.filter(
      (e) =>
        !e.includes("favicon") &&
        !e.includes("404") &&
        !e.includes("Failed to load resource") &&
        !e.includes("Download the React DevTools")
    );

    expect(significantErrors).toEqual([]);
  });

  test("dashboard page has no console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    await mockDashboardApis(page);
    await injectAuthState(page);
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    const significantErrors = errors.filter(
      (e) =>
        !e.includes("favicon") &&
        !e.includes("404") &&
        !e.includes("Failed to load resource") &&
        !e.includes("Download the React DevTools")
    );

    expect(significantErrors).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Layout structure checks — verify key layout elements exist
// ---------------------------------------------------------------------------

test.describe("Layout structure", () => {
  test.beforeEach(async ({ page }) => {
    await mockDashboardApis(page);
    await injectAuthState(page);
  });

  test("dashboard has sidebar navigation", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/dashboard");

    // Look for nav element (sidebar) or an aside
    const sidebar = page.locator("nav, aside").first();
    await expect(sidebar).toBeVisible();
  });

  test("dashboard has main content area", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator("main")).toBeVisible();
  });

  test("dashboard layout contains navigation links", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/dashboard");

    // There should be multiple links in the sidebar/navigation
    const navLinks = page.locator("nav a, aside a");
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(0);
  });
});
