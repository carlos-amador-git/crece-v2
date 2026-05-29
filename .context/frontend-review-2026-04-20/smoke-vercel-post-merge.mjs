// Smoke Vercel prod post-merge PR #34 · confirmar fixes visibles en producción
import pw from "/Users/marxchavez/Projects/crece-v2/frontend/node_modules/playwright/index.js";
const { chromium } = pw;
import { join } from "path";
import { mkdirSync } from "fs";

const FRONTEND = "https://frontend-zeta-sepia-46.vercel.app";
const OUT = "/Users/marxchavez/Projects/crece-v2/.context/frontend-review-2026-04-20/smoke-vercel-post-merge";
mkdirSync(OUT, { recursive: true });

async function login(page, email, password) {
  await page.goto(`${FRONTEND}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(3000);
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await page.click('button[type="submit"], button:has-text("Iniciar")');
  await page.waitForURL(/dashboard/, { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(5000);
}

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
const errs = [];
page.on("console", (m) => m.type() === "error" && errs.push(m.text()));
page.on("pageerror", (e) => errs.push(`pageerror: ${e.message}`));

await login(page, "pina@crece.mx", "demo2026!");
console.log(`Piña URL post-login: ${page.url()}`);

// Tier 1 overview (F-05 D-19 context + F-01 B01)
await page.goto(`${FRONTEND}/dashboard/diagnostico/1`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(5000);
await page.screenshot({ path: join(OUT, "01-tier1-vercel-prod.png"), fullPage: true });
console.log("01 · Tier 1 Vercel prod capturado");

const b01 = page.locator('[data-testid="card-b01"]').first();
if (await b01.isVisible().catch(() => false)) {
  await b01.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await b01.screenshot({ path: join(OUT, "02-b01-vercel-prod.png") });
  console.log("02 · B01 Vercel prod capturado");
}

const b04 = page.locator('[data-testid="card-b04"]').first();
if (await b04.isVisible().catch(() => false)) {
  await b04.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await b04.screenshot({ path: join(OUT, "03-b04-vercel-prod.png") });
  console.log("03 · B04 Vercel prod capturado");
}

// Tier 2 (F-04 B13 + F-07 B14)
await page.goto(`${FRONTEND}/dashboard/diagnostico-tier2/1`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(5000);
await page.screenshot({ path: join(OUT, "04-tier2-vercel-prod.png"), fullPage: true });
console.log("04 · Tier 2 Vercel prod capturado");

const b13 = page.locator('[data-testid="card-b13"]').first();
if (await b13.isVisible().catch(() => false)) {
  await b13.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await b13.screenshot({ path: join(OUT, "05-b13-vercel-prod.png") });
  console.log("05 · B13 Vercel prod capturado");
}

const b14 = page.locator('[data-testid="card-b14"]').first();
if (await b14.isVisible().catch(() => false)) {
  await b14.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await b14.screenshot({ path: join(OUT, "06-b14-vercel-prod.png") });
  console.log("06 · B14 Vercel prod capturado");
}

// Plan IA cliente (validar PR #32 holds)
await page.goto(`${FRONTEND}/dashboard/recomendaciones`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(5000);
await page.screenshot({ path: join(OUT, "07-plan-ia-cliente-vercel-prod.png"), fullPage: true });
console.log("07 · Plan IA cliente capturado");

await ctx.close();
await browser.close();

console.log(`\nTotal console errors: ${errs.length}`);
if (errs.length) console.log(errs.slice(0, 3));
console.log(`Screenshots: ${OUT}`);
