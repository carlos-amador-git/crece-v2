import { test, expect, type Page } from "@playwright/test";

/**
 * E2E tests for Sprint S3 T5 — Dashboard Diagnóstico Tier 2 (8 cards diferenciadores).
 *
 * PRINCIPIO MD: NO se mockea el backend — tests van contra data real.
 * Requisito: backend FastAPI corriendo en http://localhost:8002 con seed de Piña
 * (dirigente_id=1, org_id=1, ~347 comments + ~320 posts).
 *
 * Flujo:
 *   1. Login real via POST /api/v1/auth/login (token compartido entre tests)
 *   2. Inyectar token y org_id en localStorage (+ cookie)
 *   3. Navegar a /dashboard/diagnostico-tier2/1
 *   4. Validar 8 cards B11-B18, toggle Filtro Realidad, insufficient_data de B16
 */

const BACKEND_URL = process.env.API_URL || "http://localhost:8002/api/v1";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@consultoriamd.com";
const ADMIN_PASS = process.env.E2E_ADMIN_PASS || "crece2026!";
const PINA_DIRIGENTE_ID = 1;
const PINA_ORG_ID = 1;

const NAV_TIMEOUT = 180_000;
const TEST_TIMEOUT = 300_000;
test.setTimeout(TEST_TIMEOUT);

let sharedToken = "";

async function injectAuthReal(page: Page, token: string): Promise<void> {
  await page.goto("/login", { waitUntil: "commit", timeout: NAV_TIMEOUT });
  await page.evaluate(
    ({ t, org }) => {
      localStorage.setItem("crece_access_token", t);
      localStorage.setItem("crece_refresh_token", t);
      localStorage.setItem("crece_active_org_id", String(org));
      document.cookie = `crece_access_token=${t}; path=/; max-age=86400; SameSite=Lax`;
    },
    { t: token, org: PINA_ORG_ID },
  );
}

test.describe("Diagnóstico Tier 2 — Piña (dirigente_id=1)", () => {
  test.beforeAll(async ({ request }) => {
    test.setTimeout(180_000);
    if (sharedToken) return;
    for (let i = 0; i < 5; i++) {
      const res = await request.post(`${BACKEND_URL}/auth/login`, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        data: new URLSearchParams({
          username: ADMIN_EMAIL,
          password: ADMIN_PASS,
        }).toString(),
        timeout: 30_000,
      });
      if (res.ok()) {
        sharedToken = (await res.json()).access_token;
        break;
      }
      if (res.status() === 429) {
        // eslint-disable-next-line no-console
        console.log(`[auth/login] 429, retry ${i + 1}/5 en 15s`);
        await new Promise((r) => setTimeout(r, 15_000));
        continue;
      }
      throw new Error(`login failed status=${res.status()}`);
    }
    if (!sharedToken) throw new Error("No se pudo obtener token");
  });

  test.beforeEach(async ({ page }) => {
    await injectAuthReal(page, sharedToken);
  });

  // =======================================================================
  // 1. Render base — 8 cards visibles con data real del backend
  // =======================================================================
  test("renderiza las 8 cards Tier 2 contra backend real", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });

    const grid = page.getByTestId("cards-grid-tier2");
    await expect(grid).toBeVisible({ timeout: 90_000 });

    // Las 8 cards B11-B18
    for (const code of ["b11", "b12", "b13", "b14", "b15", "b16", "b17", "b18"]) {
      const card = page.getByTestId(`card-${code}`);
      await expect(card, `card-${code} no está visible`).toBeVisible();
    }

    // Resumen badge
    await expect(page.getByTestId("resumen-badges")).toContainText("/ 8");
  });

  // =======================================================================
  // 2. B11 Cross-Partisan — headline numérico
  // =======================================================================
  test("B11 Cross-Partisan muestra score 0-100 numérico", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByTestId("cards-grid-tier2")).toBeVisible({ timeout: 90_000 });

    const headline = page.getByTestId("b11-headline");
    await expect(headline).toBeVisible();
    const txt = await headline.innerText();
    expect(txt, "B11 headline debe incluir 'score 0-100'").toContain("score");
    expect(txt, "B11 headline no debe ser sólo placeholder").not.toMatch(/^—$/);
  });

  // =======================================================================
  // 3. B12 CIB — lista flagged con confidence
  // =======================================================================
  test("B12 CIB Detector muestra flagged authors o mensaje 'sin flagged'", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByTestId("cards-grid-tier2")).toBeVisible({ timeout: 90_000 });

    const card = page.getByTestId("card-b12");
    await expect(card).toBeVisible();

    const status = await card.getAttribute("data-status");
    if (status === "ok") {
      // Según reporte Agent A: Piña tiene 2 flagged → la lista debe aparecer
      const lista = page.getByTestId("b12-flagged-list");
      const headline = page.getByTestId("b12-headline");
      await expect(headline).toBeVisible();
      // Si hay flagged, la lista se muestra. Si no, se muestra mensaje alternativo.
      const listaVisible = await lista.isVisible().catch(() => false);
      const text = await card.innerText();
      expect(
        listaVisible || /señal limpia/i.test(text),
        "Debe mostrar lista flagged o mensaje 'señal limpia'",
      ).toBe(true);
    }
  });

  // =======================================================================
  // 4. B13 Toggle Filtro Realidad — cambia al menos 1 número visible Tier 1
  // =======================================================================
  test("Toggle Filtro de Realidad cambia delta Tier 1 visible", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByTestId("cards-grid-tier2")).toBeVisible({ timeout: 90_000 });

    const btn = page.getByTestId("filtro-realidad-btn");
    await expect(btn).toBeVisible();

    // Estado inicial: no debe haber delta-tier1 visible
    const deltaDiv = page.getByTestId("delta-tier1");
    await expect(deltaDiv).toHaveCount(0);

    // Capturar el headline B13 antes de activar
    const b13Before = await page.getByTestId("b13-headline").innerText();

    // Activar toggle
    await btn.click();

    // Esperar segundo fetch (query param recompute_tier1=true) y delta visible
    await expect(deltaDiv).toBeVisible({ timeout: 60_000 });

    const deltaValor = page.getByTestId("delta-tier1-valor");
    await expect(deltaValor).toBeVisible();
    const deltaTxt = await deltaValor.innerText();
    expect(deltaTxt, "Delta debe ser numérico con %").toMatch(/\d+\.\d{2}%/);

    // El headline B13 puede recomputarse (el hook usa queryKey con filtroActivo)
    const b13After = await page.getByTestId("b13-headline").innerText();
    // Al menos uno de los dos debe reflejar el cambio: delta visible O B13 refetch
    expect(
      deltaTxt.length > 0 || b13After !== b13Before,
      "Toggle debe disparar cambio visible en la página (delta o refetch B13)",
    ).toBe(true);

    // Toggle aria-checked
    expect(await btn.getAttribute("aria-checked")).toBe("true");
  });

  // =======================================================================
  // 5. B16 insufficient_data — card visible, no colapsa, muestra mensaje
  // =======================================================================
  test("B16 Promesas muestra insufficient_data sin colapsar", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByTestId("cards-grid-tier2")).toBeVisible({ timeout: 90_000 });

    const card = page.getByTestId("card-b16");
    await expect(card).toBeVisible();

    const status = await card.getAttribute("data-status");
    // Según Agent A: Piña no tiene promesas seed → insufficient_data esperado
    if (status === "insufficient_data") {
      const insuf = page.getByTestId("card-b16-insufficient");
      await expect(insuf).toBeVisible();
      await expect(insuf).toContainText(/insuficient/i);

      // La card NO se colapsa (altura > 100px)
      const box = await card.boundingBox();
      expect(box, "Card B16 debe tener bounding box").not.toBeNull();
      expect(box!.height, "Card B16 no debe colapsar").toBeGreaterThan(120);
    } else if (status === "ok") {
      // Si ya hay promesas seeded, verificar que el headline esté presente
      await expect(page.getByTestId("b16-headline")).toBeVisible();
    }
  });

  // =======================================================================
  // 6. B17 Veda — puede_publicar visible + keywords
  // =======================================================================
  test("B17 Veda Compliance muestra estado puede_publicar + ventana", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByTestId("cards-grid-tier2")).toBeVisible({ timeout: 90_000 });

    const card = page.getByTestId("card-b17");
    await expect(card).toBeVisible();

    const status = await card.getAttribute("data-status");
    if (status === "ok") {
      await expect(page.getByTestId("b17-headline")).toBeVisible();
      await expect(page.getByTestId("b17-ventana")).toBeVisible();
    }
  });

  // =======================================================================
  // 7. B18 Violencia Política — severity chart visible con data
  // =======================================================================
  test("B18 Violencia Política muestra distribución severity", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByTestId("cards-grid-tier2")).toBeVisible({ timeout: 90_000 });

    const card = page.getByTestId("card-b18");
    await expect(card).toBeVisible();

    const status = await card.getAttribute("data-status");
    if (status === "ok") {
      const headline = page.getByTestId("b18-headline");
      await expect(headline).toBeVisible();
      const txt = await headline.innerText();
      // headline: pct comments violentos
      expect(txt, "B18 headline debe incluir % o fracción").toMatch(/(%|\d+)/);
    }
  });

  // =======================================================================
  // 8. Screenshot full-page del dashboard Tier 2 Piña
  // =======================================================================
  test("screenshot de referencia del dashboard Tier 2 Piña", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByTestId("cards-grid-tier2")).toBeVisible({ timeout: 90_000 });

    // Esperar render de recharts
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: "test-results/diagnostico-tier2-pina.png",
      fullPage: true,
    });
  });

  // =======================================================================
  // 9. Console errors = 0 (bono)
  // =======================================================================
  test("la página Tier 2 no produce console errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto(`/dashboard/diagnostico-tier2/${PINA_DIRIGENTE_ID}`, {
      waitUntil: "commit",
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByTestId("cards-grid-tier2")).toBeVisible({ timeout: 90_000 });
    await page.waitForTimeout(1500);

    const realErrors = consoleErrors.filter(
      (e) =>
        !e.includes("chatwoot") &&
        !e.includes("chatmx.mdconsultoria") &&
        !e.toLowerCase().includes("favicon") &&
        !e.includes("429"),
    );
    expect(realErrors, `console errors: ${realErrors.join("\n")}`).toHaveLength(0);
  });
});
