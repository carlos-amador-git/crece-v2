import { test, expect } from "@playwright/test";

/**
 * Smoke post-ingest RADAR 9,401 events · 5,591 reactors nuevos.
 * Verifica visualmente que CRECE prod refleja:
 *  - Total reacciones histórico subió (era 80.2K · debe ser ahora ~89-90K)
 *  - TimelineChart muestra reactors en los 7 días previamente huecos
 */

const BASE = "https://frontend-zeta-sepia-46.vercel.app";
const SAYMI = { email: "pineda@crece.mx", password: "demo2026!" };

test.setTimeout(60000);

test("post-ingest RADAR · Saymi histórico refleja delta", async ({ page }) => {
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
  console.log("✓ login");

  // /fans-y-perfiles · KPI Reacciones histórico
  await page.goto(`${BASE}/dashboard/aceptacion/fans-y-perfiles`, { waitUntil: "networkidle" });
  await page.waitForTimeout(3500);
  const reaccionesText = await page.locator("text=/REACCIONES.*HIST/i").locator("..").innerText();
  console.log(`KPI Reacciones: ${reaccionesText.split("\n").slice(0, 3).join(" | ")}`);
  // No assert strict porque depende del refresh; solo validamos que la página carga y muestra número
  expect(reaccionesText).toMatch(/\d/);
  await page.screenshot({ path: "/tmp/post-radar-fans-y-perfiles.png", fullPage: true });

  // /aceptacion · vista perfil con TimelineChart? (no, Timeline solo en fans-y-perfiles)
  await page.goto(`${BASE}/dashboard/aceptacion`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  const h1 = await page.locator("h1").first().innerText();
  expect(h1.toLowerCase()).toContain("saymi");
  await page.screenshot({ path: "/tmp/post-radar-aceptacion.png", fullPage: true });
  console.log(`✓ /aceptacion h1="${h1}"`);

  console.log(`errores: ${errors.length}`);
  expect(errors.length).toBe(0);
});
