// Smoke Vercel prod post-hotfix PR #32.
// Login Piña + admin · captura /dashboard/recomendaciones y /dashboard/admin/plan-ia-review
// contra el Vercel deployado real.

import { chromium } from "playwright";
import { join } from "path";

const FRONTEND = "https://frontend-zeta-sepia-46.vercel.app";
const OUT = "/Users/marxchavez/Projects/crece-v2/.context/frontend-review-2026-04-20/smoke-post-hotfix";
import { mkdirSync } from "fs";
mkdirSync(OUT, { recursive: true });

async function loginViaForm(page, email, password) {
  await page.goto(`${FRONTEND}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(3000);
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await page.click('button[type="submit"], button:has-text("Iniciar")');
  await page.waitForURL(/dashboard/, { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(5000);
}

async function checkNoErrorBanner(page) {
  const errorBanner = page.locator('text=/Not Found|No se pudieron cargar|No se pudo cargar/i').first();
  return !(await errorBanner.isVisible().catch(() => false));
}

const browser = await chromium.launch({ headless: true });

// Piña viewer
const ctxP = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const pageP = await ctxP.newPage();
const errP = [];
pageP.on("console", (m) => m.type() === "error" && errP.push(m.text()));
pageP.on("pageerror", (e) => errP.push(`pageerror: ${e.message}`));

await loginViaForm(pageP, "pina@crece.mx", "demo2026!");
console.log(`Piña URL post-login: ${pageP.url()}`);

await pageP.goto(`${FRONTEND}/dashboard/recomendaciones`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await pageP.waitForTimeout(4000);
const pinaOK = await checkNoErrorBanner(pageP);
await pageP.screenshot({ path: join(OUT, "01-pina-recomendaciones.png"), fullPage: true });
console.log(`Piña /dashboard/recomendaciones · no_error_banner=${pinaOK} · console_errors=${errP.length}`);

// Capture tabs too
for (const tab of ["Pendientes", "Seguimiento", "Histórico"]) {
  const t = pageP.locator(`[role="tab"]:has-text("${tab}")`).first();
  if (await t.isVisible().catch(() => false)) {
    await t.click().catch(() => {});
    await pageP.waitForTimeout(2000);
    await pageP.screenshot({ path: join(OUT, `01-pina-tab-${tab.toLowerCase()}.png`), fullPage: true });
  }
}

await ctxP.close();

// Admin
const ctxA = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const pageA = await ctxA.newPage();
const errA = [];
pageA.on("console", (m) => m.type() === "error" && errA.push(m.text()));
pageA.on("pageerror", (e) => errA.push(`pageerror: ${e.message}`));

await loginViaForm(pageA, "admin@consultoriamd.com", "crece2026!");
console.log(`Admin URL post-login: ${pageA.url()}`);

await pageA.goto(`${FRONTEND}/dashboard/admin/plan-ia-review`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await pageA.waitForTimeout(4000);
const adminOK = await checkNoErrorBanner(pageA);
await pageA.screenshot({ path: join(OUT, "02-admin-plan-ia-review.png"), fullPage: true });
console.log(`Admin /dashboard/admin/plan-ia-review · no_error_banner=${adminOK} · console_errors=${errA.length}`);

await ctxA.close();
await browser.close();

console.log(`\nResumen smoke Vercel post-hotfix:`);
console.log(`  piña OK: ${pinaOK}`);
console.log(`  admin OK: ${adminOK}`);
console.log(`  Screenshots: ${OUT}`);
