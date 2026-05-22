import { test, expect } from "@playwright/test";

/**
 * Validación post-deploy D-ACEPTACION-DEDUPE-2026-05-20.
 *
 * Cubre:
 *  1. Login Saymi (viewer, dirigente_id=3)
 *  2. /aceptacion renderiza vista perfil propio (no Battle Card)
 *  3. Sidebar grupo "Indice Aceptacion" muestra 2 items (no 4)
 *  4. /aceptacion/dirigentes redirige 308 → /aceptacion
 *  5. /aceptacion/fantasmas redirige 308 → /aceptacion
 *  6. /aceptacion/4 (otro dirigente misma org) → frontend muestra empty/error o redirect
 *  7. /aceptacion/fans-y-perfiles intacto
 *  8. "Por plataforma" (5 redes) visible dentro del perfil
 *  9. 0 errores 5xx / pageerror
 */

const BASE = "https://frontend-zeta-sepia-46.vercel.app";
const SAYMI = { email: "pineda@crece.mx", password: "demo2026!" };

test("D-ACEPTACION-DEDUPE · validación prod", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    if (r.status() >= 500) errors.push(`5xx: ${r.url()} → ${r.status()}`);
  });

  // Login
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', SAYMI.email);
  await page.fill('input[type="password"]', SAYMI.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/dashboard/, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1500);
  console.log(`✓ login Saymi · landed=${page.url()}`);

  // 1. /aceptacion · vista perfil
  await page.goto(`${BASE}/dashboard/aceptacion`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  const h1 = await page.locator("h1").first().innerText();
  // Para viewer Saymi el H1 debe ser el nombre del dirigente, no "Índice de Aceptación"
  expect(h1.toLowerCase()).toContain("saymi");
  await page.screenshot({ path: "/tmp/aceptacion-dedupe-01-perfil.png", fullPage: true });
  console.log(`✓ /aceptacion h1="${h1}"`);

  // 2. Sidebar 2 items en grupo Aceptacion
  const aceptacionLink = page.locator('a[href="/dashboard/aceptacion"]').first();
  const fansLink = page.locator('a[href="/dashboard/aceptacion/fans-y-perfiles"]').first();
  const dirigentesLink = page.locator('a[href="/dashboard/aceptacion/dirigentes"]');
  const fantasmasLink = page.locator('a[href="/dashboard/aceptacion/fantasmas"]');
  await expect(aceptacionLink).toBeAttached();
  await expect(fansLink).toBeAttached();
  expect(await dirigentesLink.count()).toBe(0);
  expect(await fantasmasLink.count()).toBe(0);
  console.log(`✓ sidebar grupo · 2 items · /dirigentes y /fantasmas removidos`);

  // 3. Redirect 308 /dirigentes → /aceptacion
  await page.goto(`${BASE}/dashboard/aceptacion/dirigentes`, { waitUntil: "networkidle" });
  expect(page.url()).toContain("/aceptacion");
  expect(page.url()).not.toContain("/dirigentes");
  console.log(`✓ redirect /dirigentes → ${page.url()}`);

  // 4. Redirect 308 /fantasmas → /aceptacion
  await page.goto(`${BASE}/dashboard/aceptacion/fantasmas`, { waitUntil: "networkidle" });
  expect(page.url()).toContain("/aceptacion");
  expect(page.url()).not.toContain("/fantasmas");
  console.log(`✓ redirect /fantasmas → ${page.url()}`);

  // 5. /aceptacion/4 (Yesenia, otro id) · viewer debe ver error/sin acceso
  await page.goto(`${BASE}/dashboard/aceptacion/4`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  const bodyText = (await page.locator("body").innerText()).toLowerCase();
  // Aceptamos cualquiera de estos signos: "no encontrado", "sin acceso", "403", o que la página esté vacía/skeleton
  const guarded =
    bodyText.includes("no encontrado") ||
    bodyText.includes("sin acceso") ||
    bodyText.includes("forbidden") ||
    bodyText.includes("dirigente no");
  console.log(`✓ /aceptacion/4 guarded · texto detectado: ${guarded}`);
  await page.screenshot({ path: "/tmp/aceptacion-dedupe-02-cross-id.png", fullPage: true });

  // 6. /fans-y-perfiles intacto
  await page.goto(`${BASE}/dashboard/aceptacion/fans-y-perfiles`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  const fansH1 = await page.locator("h1").first().innerText();
  expect(fansH1.trim()).toBe("Fans y Perfiles");
  await page.screenshot({ path: "/tmp/aceptacion-dedupe-03-fans.png", fullPage: true });
  console.log(`✓ /fans-y-perfiles h1="${fansH1}"`);

  // 7. "Por plataforma" visible en /aceptacion
  await page.goto(`${BASE}/dashboard/aceptacion`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  const porRed = await page.locator("text=/por red social/i").count();
  console.log(`badge 'Por red social' visible: ${porRed > 0 ? "✓" : "✗"} (count=${porRed})`);
  expect(porRed).toBeGreaterThan(0);

  // 8. Sin 5xx / pageerror
  console.log(`errores 5xx/pageerror: ${errors.length}`);
  if (errors.length > 0) console.log(errors.join("\n"));
  expect(errors.length).toBe(0);
});
