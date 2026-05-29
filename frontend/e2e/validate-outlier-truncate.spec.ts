import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3005";
const SAYMI = { email: "pineda@crece.mx", password: "demo2026!" };

test.setTimeout(60000);

test("outlier truncation N2 · localhost", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    if (r.status() >= 500) errors.push(`5xx: ${r.url()} → ${r.status()}`);
  });

  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', SAYMI.email);
  await page.fill('input[type="password"]', SAYMI.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/dashboard/, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1500);

  await page.goto(`${BASE}/dashboard/aceptacion/fans-y-perfiles`, { waitUntil: "networkidle" });
  await page.waitForTimeout(4000);

  // El badge "↑" debe aparecer si yCap calculó < max
  const upBadges = await page.locator('text=/↑\\s/').count();
  console.log(`badges '↑ ...': ${upBadges}`);

  // Subtítulo debe mencionar "barras ámbar"
  const subtitle = await page.locator("text=/barras ámbar/i").count();
  console.log(`subtítulo 'barras ámbar' visible: ${subtitle > 0 ? "✓" : "ausente"}`);

  await page.screenshot({ path: "/tmp/outlier-truncate-test.png", fullPage: true });

  console.log(`errores: ${errors.length}`);
  expect(errors.length).toBe(0);
  expect(upBadges).toBeGreaterThan(0);
  expect(subtitle).toBeGreaterThan(0);
});
