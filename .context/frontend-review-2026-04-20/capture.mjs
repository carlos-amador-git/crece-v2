// Playwright screenshot capture para revisión visual del MVP CRECE v2.
// Usa Vercel prod URL + backend vía tunnel actual.
// Ejecución: node capture.mjs

import { chromium } from "playwright";
import { writeFileSync } from "fs";
import { join } from "path";

import { setServers } from "dns";
setServers(["1.1.1.1", "8.8.8.8"]);

// Local dev frontend · evita DNS issues del tunnel trycloudflare en ISP.
// El código desplegado en Vercel es idéntico (mismo commit main) — misma UI.
const FRONTEND = "http://localhost:3005";
// Login via backend LOCAL (sin DNS lookup tunnel). Browser usa tunnel + resolver cloudflare (OK).
const API_URL = "http://localhost:8002/api/v1";

const OUT_ROOT = "/Users/marxchavez/Projects/crece-v2/.context/frontend-review-2026-04-20";
const DIRIGENTE_ID = 1; // Piña

// Helpers
async function getToken(email, password) {
  const body = new URLSearchParams({ username: email, password });
  const r = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!r.ok) throw new Error(`login failed ${email} · ${r.status}`);
  const { access_token } = await r.json();
  return access_token;
}

async function setupSession(ctx, token) {
  await ctx.addInitScript((t) => {
    localStorage.setItem("crece_access_token", t);
    localStorage.setItem("crece_refresh_token", t);
  }, token);
}

async function loginViaForm(page, email, password) {
  await page.goto(`${FRONTEND}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(2000);
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await page.click('button[type="submit"], button:has-text("Iniciar")');
  await page.waitForURL(/dashboard/, { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);
}

const findings = [];
function log(category, route, notes) {
  findings.push({ category, route, notes });
  console.log(`[${category}] ${route} · ${notes}`);
}

async function shoot(page, filename, { waitMs = 2500, errors = [] } = {}) {
  await page.waitForTimeout(waitMs);
  // Capture console errors accumulated
  const consoleErrors = errors.filter((e) => e.type === "error");
  await page.screenshot({ path: filename, fullPage: true });
  return consoleErrors.length;
}

(async () => {
  const browser = await chromium.launch({ headless: true });

  // ───────────────── VIEWER SESSION (Piña) ─────────────────
  const ctxPina = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pagePina = await ctxPina.newPage();
  await loginViaForm(pagePina, "pina@crece.mx", "demo2026!");
  console.log("login Piña via form OK · URL=" + pagePina.url());
  const errorsPina = [];
  pagePina.on("console", (msg) => {
    if (msg.type() === "error") errorsPina.push({ type: "error", text: msg.text() });
  });
  pagePina.on("pageerror", (err) => errorsPina.push({ type: "pageerror", text: err.message }));

  // Categoria 1 · Tier 1 Diagnóstico
  const cat1 = join(OUT_ROOT, "01-tier1-diagnostico");
  await pagePina.goto(`${FRONTEND}/dashboard/diagnostico/${DIRIGENTE_ID}`, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  const errs1 = await shoot(pagePina, join(cat1, "00-overview.png"));
  log("01-tier1", "/dashboard/diagnostico/1 overview", `console_errors=${errs1}`);

  // Hover/click en cada card Tier 1 — si la card tiene drill-down (ej B10 tiene "Ver ejemplos")
  // Vamos a intentar screenshot de cada card individual haciendo scroll hasta ella
  const tier1Blocks = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10"];
  for (const b of tier1Blocks) {
    const card = pagePina.locator(`[data-testid="card-${b.toLowerCase()}"], [data-testid="${b}"], :has-text("${b}")`).first();
    const visible = await card.isVisible().catch(() => false);
    if (visible) {
      await card.scrollIntoViewIfNeeded().catch(() => {});
      await pagePina.waitForTimeout(500);
      await card.screenshot({ path: join(cat1, `${b}.png`) }).catch((e) => {
        log("01-tier1", b, `card screenshot fail: ${e.message}`);
      });
      log("01-tier1", b, "card capturada");
    } else {
      log("01-tier1", b, "card no visible · skip");
    }
  }

  // B10 drill-down · click "Ver ejemplos"
  const b10btn = pagePina.locator('button:has-text("Ver ejemplos")').first();
  if (await b10btn.isVisible().catch(() => false)) {
    await b10btn.click().catch(() => {});
    await pagePina.waitForTimeout(2500);
    await pagePina.screenshot({ path: join(cat1, "B10-drilldown.png"), fullPage: true });
    log("01-tier1", "B10 drilldown", "drawer abierto");
    await pagePina.keyboard.press("Escape").catch(() => {});
  }

  // Categoria 2 · Tier 2 Diferenciadores
  const cat2 = join(OUT_ROOT, "02-tier2-diferenciadores");
  await pagePina.goto(`${FRONTEND}/dashboard/diagnostico-tier2/${DIRIGENTE_ID}`, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  const errs2 = await shoot(pagePina, join(cat2, "00-overview.png"));
  log("02-tier2", "/dashboard/diagnostico-tier2/1 overview", `console_errors=${errs2}`);

  const tier2Blocks = ["B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18"];
  for (const b of tier2Blocks) {
    const card = pagePina.locator(`[data-testid="card-${b.toLowerCase()}"], [data-testid="${b}"], :has-text("${b}")`).first();
    const visible = await card.isVisible().catch(() => false);
    if (visible) {
      await card.scrollIntoViewIfNeeded().catch(() => {});
      await pagePina.waitForTimeout(500);
      await card.screenshot({ path: join(cat2, `${b}.png`) }).catch((e) => {
        log("02-tier2", b, `card screenshot fail: ${e.message}`);
      });
      log("02-tier2", b, "card capturada");
    } else {
      log("02-tier2", b, "card no visible · skip");
    }
  }

  // Toggle Filtro Realidad
  const toggleFiltro = pagePina.locator('button:has-text("Filtro"), [role="switch"]').first();
  if (await toggleFiltro.isVisible().catch(() => false)) {
    await toggleFiltro.click().catch(() => {});
    await pagePina.waitForTimeout(3000);
    await pagePina.screenshot({ path: join(cat2, "99-filtro-realidad-on.png"), fullPage: true });
    log("02-tier2", "filtro-realidad-on", "toggle activado · delta visible");
  }

  // Categoria 3 · Plan IA cliente
  const cat3 = join(OUT_ROOT, "03-plan-ia-cliente");
  await pagePina.goto(`${FRONTEND}/dashboard/recomendaciones`, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  const errs3 = await shoot(pagePina, join(cat3, "00-overview.png"));
  log("03-plan-ia-cliente", "/dashboard/recomendaciones overview", `console_errors=${errs3}`);

  const tabNames = ["Pendientes", "Seguimiento", "Histórico", "Memoria", "Reporte"];
  for (const t of tabNames) {
    const tab = pagePina.locator(`[role="tab"]:has-text("${t}")`).first();
    if (await tab.isVisible().catch(() => false)) {
      await tab.click().catch(() => {});
      await pagePina.waitForTimeout(2000);
      await pagePina.screenshot({ path: join(cat3, `tab-${t.toLowerCase()}.png`), fullPage: true });
      log("03-plan-ia-cliente", `tab-${t}`, "tab capturada");
    } else {
      log("03-plan-ia-cliente", `tab-${t}`, "tab no visible");
    }
  }

  // Categoria 5 · Onboarding wizard
  const cat5 = join(OUT_ROOT, "05-onboarding-wizard");
  await pagePina.goto(`${FRONTEND}/dashboard/onboarding/${DIRIGENTE_ID}`, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  const errs5 = await shoot(pagePina, join(cat5, "step1-inicial.png"));
  log("05-onboarding", "step1 perfil", `console_errors=${errs5}`);

  // Intentar navegar pasos del wizard con "Siguiente"
  for (let step = 2; step <= 9; step++) {
    const nextBtn = pagePina.locator('button:has-text("Siguiente"), button:has-text("Continuar")').first();
    if (await nextBtn.isEnabled().catch(() => false)) {
      await nextBtn.click().catch(() => {});
      await pagePina.waitForTimeout(1500);
      await pagePina.screenshot({ path: join(cat5, `step${step}.png`), fullPage: true });
      log("05-onboarding", `step${step}`, "navegado + capturado");
    } else {
      await pagePina.screenshot({ path: join(cat5, `step${step}-blocked.png`), fullPage: true });
      log("05-onboarding", `step${step}`, "Siguiente DISABLED (validación bloquea) · capturado");
      break;
    }
  }

  // Categoria 6 · Settings + OAuth (puede o no existir · intentamos varias rutas)
  const cat6 = join(OUT_ROOT, "06-settings-oauth");
  const settingsRoutes = ["/dashboard/settings", "/dashboard/config", "/dashboard/oauth", "/dashboard/admin/settings"];
  for (const r of settingsRoutes) {
    const resp = await pagePina.goto(`${FRONTEND}${r}`, { waitUntil: "networkidle", timeout: 30000 }).catch(() => null);
    const status = resp ? resp.status() : 0;
    await pagePina.waitForTimeout(1500);
    await pagePina.screenshot({ path: join(cat6, `route-${r.replace(/\//g, "_")}.png`), fullPage: true });
    log("06-settings", r, `http=${status}`);
  }

  await ctxPina.close();

  // ───────────────── ADMIN SESSION (HITL) ─────────────────
  const ctxAdmin = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pageAdmin = await ctxAdmin.newPage();
  await loginViaForm(pageAdmin, "admin@consultoriamd.com", "crece2026!");
  console.log("login admin via form OK · URL=" + pageAdmin.url());
  const errorsAdmin = [];
  pageAdmin.on("console", (msg) => {
    if (msg.type() === "error") errorsAdmin.push({ type: "error", text: msg.text() });
  });

  // Categoria 4 · Plan IA admin HITL
  const cat4 = join(OUT_ROOT, "04-plan-ia-admin-hitl");
  await pageAdmin.goto(`${FRONTEND}/dashboard/admin/plan-ia-review`, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  const errs4 = await shoot(pageAdmin, join(cat4, "00-overview.png"));
  log("04-plan-ia-admin", "/dashboard/admin/plan-ia-review overview", `console_errors=${errs4}`);

  // Capturar una recomendación individual (si hay cards)
  const firstCard = pageAdmin.locator('[data-testid^="rec-card"], article').first();
  if (await firstCard.isVisible().catch(() => false)) {
    await firstCard.scrollIntoViewIfNeeded().catch(() => {});
    await pageAdmin.waitForTimeout(500);
    await firstCard.screenshot({ path: join(cat4, "01-first-rec-card.png") });
    log("04-plan-ia-admin", "first-rec-card", "card individual capturada");
  }

  await ctxAdmin.close();
  await browser.close();

  // Reporte
  writeFileSync(
    join(OUT_ROOT, "_findings.json"),
    JSON.stringify(findings, null, 2)
  );
  console.log(`\nTotal findings: ${findings.length}`);
  console.log(`Output: ${OUT_ROOT}`);
})();
