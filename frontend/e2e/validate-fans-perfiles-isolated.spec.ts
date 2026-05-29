import { test, expect } from "@playwright/test";

/**
 * Sub-check aislado · /fans-y-perfiles post D-ACEPTACION-DEDUPE.
 * Test anterior (validate-aceptacion-dedupe.spec.ts) agotó timeout 30s default
 * acumulado en 6 navegaciones previas. Este corre solo y rápido.
 */

const BASE = "https://frontend-zeta-sepia-46.vercel.app";
const SAYMI = { email: "pineda@crece.mx", password: "demo2026!" };

test.setTimeout(60000);

test("/fans-y-perfiles · intacto post refactor", async ({ page }) => {
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
  console.log(`✓ login`);

  await page.goto(`${BASE}/dashboard/aceptacion/fans-y-perfiles`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1", { timeout: 20000 });
  const h1 = await page.locator("h1").first().innerText();
  expect(h1.trim()).toBe("Fans y Perfiles");
  console.log(`✓ h1="${h1}"`);

  // El selector dirigente combobox específico (no el chip del user-menu)
  await expect(page.locator('[role="combobox"]').first()).toBeVisible({ timeout: 10000 });

  // Esperamos data: TimelineChart o TopPostsCards o lista de fans
  await page.waitForTimeout(3000);
  const muestraBadges = await page.locator("text=/Muestra:/").count();
  const timelineExists = await page.locator("text=/Engagement diario/i").count();
  console.log(`badges Muestra: ${muestraBadges} · TimelineChart: ${timelineExists > 0 ? "✓" : "ausente"}`);

  await page.screenshot({ path: "/tmp/fans-perfiles-isolated.png", fullPage: true });

  console.log(`errores: ${errors.length}`);
  if (errors.length > 0) console.log(errors.join("\n"));
  expect(errors.length).toBe(0);
});
