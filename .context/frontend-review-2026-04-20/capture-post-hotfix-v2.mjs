// Post-hotfix-v2 capture · F-01/F-02/F-03/F-04/F-05/F-07
// Login Piña local + capture diagnóstico Tier1/Tier2 + onboarding 9 pasos

import pw from "/Users/marxchavez/Projects/crece-v2/frontend/node_modules/playwright/index.js";
const { chromium } = pw;
import { join } from "path";
import { mkdirSync } from "fs";

const FRONTEND = "http://localhost:3005";
const OUT = "/Users/marxchavez/Projects/crece-v2/.context/frontend-review-2026-04-20/post-hotfix-v2";
mkdirSync(OUT, { recursive: true });

async function login(page, email, password) {
  await page.goto(`${FRONTEND}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await page.click('button[type="submit"], button:has-text("Iniciar")');
  await page.waitForURL(/dashboard/, { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(3500);
}

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
const errs = [];
page.on("console", (m) => m.type() === "error" && errs.push(m.text()));
page.on("pageerror", (e) => errs.push(`pageerror: ${e.message}`));

// ============================================================
// 1) Login Piña + Tier 1 overview (F-05 + F-01 + F-02 fixes)
// ============================================================
await login(page, "pina@crece.mx", "Pina2026!");
console.log(`Piña URL post-login: ${page.url()}`);

// Tier 1 diagnostic
await page.goto(`${FRONTEND}/dashboard/diagnostico/1`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(4000);
await page.screenshot({ path: join(OUT, "01-tier1-overview-d19.png"), fullPage: true });
console.log("01 · Tier 1 overview con contexto D-19 capturado");

// B01 card focus
const b01 = page.locator('[data-testid="card-b01"]').first();
if (await b01.isVisible().catch(() => false)) {
  await b01.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await b01.screenshot({ path: join(OUT, "02-b01-rango-empirico-zenodo.png") });
  console.log("02 · B01 rango empírico Zenodo capturado");
}

// B04 card focus (demo banner)
const b04 = page.locator('[data-testid="card-b04"]').first();
if (await b04.isVisible().catch(() => false)) {
  await b04.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await b04.screenshot({ path: join(OUT, "03-b04-demo-banner.png") });
  console.log("03 · B04 demo banner capturado");
}

// ============================================================
// 2) Tier 2 Diferenciadores (F-04 B13 + F-07 B14)
// ============================================================
await page.goto(`${FRONTEND}/dashboard/diagnostico-tier2/1`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(4000);
await page.screenshot({ path: join(OUT, "04-tier2-overview.png"), fullPage: true });
console.log("04 · Tier 2 overview capturado");

const b13 = page.locator('[data-testid="card-b13"]').first();
if (await b13.isVisible().catch(() => false)) {
  await b13.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await b13.screenshot({ path: join(OUT, "05-b13-narrative-comercial.png") });
  console.log("05 · B13 narrative comercial capturado");
}

const b14 = page.locator('[data-testid="card-b14"]').first();
if (await b14.isVisible().catch(() => false)) {
  await b14.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await b14.screenshot({ path: join(OUT, "06-b14-warning-calibracion.png") });
  console.log("06 · B14 warning calibración capturado");
}

// ============================================================
// 3) Onboarding wizard · 9 pasos (F-03)
// ============================================================
// Wizard uses dirigenteId in path. Piña = 1
await page.goto(`${FRONTEND}/dashboard/onboarding/1`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(3000);

for (let step = 1; step <= 9; step++) {
  // Navigate via stepper button if available
  const stepBtn = page.locator(`[data-testid="stepper-btn-${step}"], button:has-text("${step}")`).first();

  // Try direct navigation via store by clicking on the step indicator
  const stepperItem = page.locator(`nav[aria-label*="Pasos" i] button, ol button`).nth(step - 1);
  if (await stepperItem.isVisible().catch(() => false)) {
    await stepperItem.click({ force: true }).catch(() => {});
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: join(OUT, `07-onboarding-paso-${step}.png`), fullPage: true });
  console.log(`07-${step} · Onboarding paso ${step} capturado`);
}

await ctx.close();
await browser.close();

console.log(`\nTotal console errors: ${errs.length}`);
if (errs.length) console.log(errs.slice(0, 5));
console.log(`Screenshots: ${OUT}`);
