// Verifica credenciales Ballesteros end-to-end contra Vercel prod
import pw from "/Users/marxchavez/Projects/crece-v2/frontend/node_modules/playwright/index.js";
const { chromium } = pw;
import { join } from "path";
import { mkdirSync } from "fs";

const FRONTEND = "https://frontend-zeta-sepia-46.vercel.app";
const OUT = "/Users/marxchavez/Projects/crece-v2/.context/frontend-review-2026-04-20/ballesteros-vercel";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
const errs = [];
page.on("console", (m) => m.type() === "error" && errs.push(m.text()));

await page.goto(`${FRONTEND}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(3000);
await page.fill('input[type="email"], input[name="email"]', "ballesteros@crece.mx");
await page.fill('input[type="password"], input[name="password"]', "Ballesteros2026!");
await page.click('button[type="submit"], button:has-text("Iniciar")');
await page.waitForURL(/dashboard/, { timeout: 45000 }).catch(() => {});
await page.waitForTimeout(5000);

const postLoginUrl = page.url();
console.log(`Post-login URL: ${postLoginUrl}`);
await page.screenshot({ path: join(OUT, "01-dashboard.png"), fullPage: true });

// Ir a recomendaciones (4 aprobadas deben verse)
await page.goto(`${FRONTEND}/dashboard/recomendaciones`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(5000);
await page.screenshot({ path: join(OUT, "02-recomendaciones.png"), fullPage: true });

// Tier 1 diagnostic
await page.goto(`${FRONTEND}/dashboard/diagnostico/8`, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(5000);
await page.screenshot({ path: join(OUT, "03-diagnostico-tier1.png"), fullPage: true });

await ctx.close();
await browser.close();
console.log(`Post-login URL: ${postLoginUrl}`);
console.log(`Console errors: ${errs.length}`);
console.log(`Screenshots: ${OUT}`);
