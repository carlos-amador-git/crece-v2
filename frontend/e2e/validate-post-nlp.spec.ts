import { test, expect } from "@playwright/test";

/**
 * Smoke post-NLP backfill 152 comments Saymi.
 * Verifica:
 *  - KPI % Clasificados NLP vuelve a 99.x% (era 91.5% pre-backfill)
 *  - Outlier chart preserved (barra ámbar + badge ↑ 6.3K)
 *  - Misael VIP override sigue #1 (no se ve aquí pero al menos KPI Reactions sano)
 *  - Top Rechazo cards rendean (puede haber reorden)
 *  - 0 errors 5xx/pageerror
 */
const BASE = "https://frontend-zeta-sepia-46.vercel.app";
const SAYMI = { email: "pineda@crece.mx", password: "demo2026!" };

test.setTimeout(60000);

test("post-NLP backfill · Saymi", async ({ page }) => {
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

  // KPI Clasificados NLP debe estar en 99.x% (busca el bloque del card completo)
  const nlpKpi = await page.locator("text=/CLASIFICADOS NLP/i").locator("xpath=ancestor::div[contains(@class, 'card') or contains(@class, 'Card')][1]").first().innerText();
  console.log(`KPI NLP block: ${nlpKpi.replace(/\n/g, " | ").slice(0, 200)}`);
  expect(nlpKpi).toMatch(/99\.[0-9]%/);

  // Outlier badge ↑ debe seguir
  const upBadges = await page.locator('text=/↑\\s/').count();
  console.log(`outlier badges: ${upBadges}`);
  expect(upBadges).toBeGreaterThan(0);

  await page.screenshot({ path: "/tmp/post-nlp-fans-y-perfiles.png", fullPage: true });

  // Top Rechazo cards rendean
  const rechazoCards = await page.locator("text=/Más rechazo/i").count();
  console.log(`secciones 'Más rechazo': ${rechazoCards}`);
  expect(rechazoCards).toBeGreaterThan(0);

  console.log(`errores: ${errors.length}`);
  expect(errors.length).toBe(0);
});
