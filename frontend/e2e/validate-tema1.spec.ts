import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3005";
const SAYMI = { email: "pineda@crece.mx", password: "demo2026!" };

test("Tema 1 · Fans y Perfiles ruta independiente", async ({ page }) => {
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
  await page.waitForTimeout(1500); // dejar que httpOnly cookie se asiente
  console.log(`✓ login Saymi · landed=${page.url()}`);

  // 1. Ruta nueva
  await page.goto(`${BASE}/dashboard/aceptacion/fans-y-perfiles`, { waitUntil: "networkidle" });
  expect(page.url()).toContain("/aceptacion/fans-y-perfiles");
  const titulo = await page.locator("h1").first().innerText();
  expect(titulo.trim()).toBe("Fans y Perfiles");
  await page.screenshot({ path: "/tmp/tema1-01-fans-y-perfiles.png", fullPage: true });
  console.log(`✓ ruta nueva · h1="${titulo}"`);

  // 2. Fantasmas sin tab observados
  await page.goto(`${BASE}/dashboard/aceptacion/fantasmas`, { waitUntil: "networkidle" });
  const tituloF = await page.locator("h1").first().innerText();
  expect(tituloF.trim()).toBe("Fantasmas");
  const tabs = await page.locator('[role="tab"]').allInnerTexts();
  expect(tabs.length).toBe(2);
  expect(tabs.some((t) => t.toLowerCase().includes("observados"))).toBe(false);
  await page.screenshot({ path: "/tmp/tema1-02-fantasmas.png", fullPage: true });
  console.log(`✓ fantasmas h1="${tituloF}" · tabs=${JSON.stringify(tabs)}`);

  // 3. Redirect 308
  await page.goto(`${BASE}/dashboard/aceptacion/fantasmas?tab=observados`, { waitUntil: "networkidle" });
  expect(page.url()).toContain("/aceptacion/fans-y-perfiles");
  console.log(`✓ redirect 308 → ${page.url()}`);

  // 4. Sidebar item nuevo (DOM-attached; visibilidad depende de accordion group state)
  const sidebarLink = page.locator('a[href="/dashboard/aceptacion/fans-y-perfiles"]');
  await expect(sidebarLink.first()).toBeAttached();
  const ariaCurrent = await sidebarLink.first().getAttribute("aria-current");
  expect(ariaCurrent).toBe("page");
  console.log(`✓ sidebar Fans y Perfiles apunta a ruta nueva (aria-current=page)`);

  // 5. Badge Muestra en TopPostsCards
  await page.waitForTimeout(3000);
  const muestraBadges = await page.locator('text=/Muestra:/').count();
  console.log(`badge 'Muestra:' count=${muestraBadges}`);
  await page.screenshot({ path: "/tmp/tema1-03-muestra-badge.png", fullPage: true });
  expect(muestraBadges).toBeGreaterThan(0);

  // 6. Errors
  console.log(`errores 5xx/pageerror: ${errors.length}`);
  if (errors.length > 0) console.log(errors.join("\n"));
  expect(errors.length).toBe(0);
});
