import { test, expect, type Page } from "@playwright/test";

/**
 * E2E tests for Sprint S2 T5 — Dashboard Diagnóstico Tier 1 (10 cards).
 *
 * PRINCIPIO MD: NO se mockea el backend — tests van contra data real.
 * Requisito: backend FastAPI corriendo en http://localhost:8002 con seed de Piña
 * (dirigente_id=1, org_id=1).
 *
 * Flujo:
 *   1. Hacer login real via POST /api/v1/auth/login con admin MD
 *   2. Inyectar token y org_id en localStorage (+ cookie)
 *   3. Navegar a /dashboard/diagnostico/1
 *   4. Validar las 10 cards + headline numérico de B01 + insufficient states
 */

const BACKEND_URL = process.env.API_URL || "http://localhost:8002/api/v1";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@consultoriamd.com";
const ADMIN_PASS = process.env.E2E_ADMIN_PASS || "crece2026!";
const PIÑA_DIRIGENTE_ID = 1;
const PIÑA_ORG_ID = 1;

// Dev server compila JIT — primera navegación del route group puede tomar 2-4 min.
// En CI/prod se sirve estático; timeouts grandes solo impactan dev local.
const NAV_TIMEOUT = 180_000;
const TEST_TIMEOUT = 300_000;
test.setTimeout(TEST_TIMEOUT);

async function loginReal(page: Page): Promise<string> {
  const body = new URLSearchParams({
    username: ADMIN_EMAIL,
    password: ADMIN_PASS,
  });
  const res = await page.request.post(`${BACKEND_URL}/auth/login`, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    data: body.toString(),
    timeout: 30_000,
  });
  expect(res.ok(), `login failed: ${res.status()}`).toBeTruthy();
  const { access_token } = await res.json();
  expect(access_token).toBeTruthy();
  return access_token as string;
}

async function injectAuthReal(page: Page, token: string): Promise<void> {
  await page.goto("/login", { waitUntil: "commit", timeout: NAV_TIMEOUT });
  await page.evaluate(
    ({ t, org }) => {
      localStorage.setItem("crece_access_token", t);
      localStorage.setItem("crece_refresh_token", t);
      localStorage.setItem("crece_active_org_id", String(org));
      document.cookie = `crece_access_token=${t}; path=/; max-age=86400; SameSite=Lax`;
    },
    { t: token, org: PIÑA_ORG_ID },
  );
}

// Token compartido entre tests para evitar rate-limit 429 en /auth/login.
// Se obtiene 1 sola vez en beforeAll.
let sharedToken: string = "";

test.describe("Diagnóstico Tier 1 — Piña (dirigente_id=1)", () => {
  test.beforeAll(async ({ request }) => {
    if (sharedToken) return;
    // Retry login hasta 5 veces en caso de 429 (rate limit)
    for (let i = 0; i < 5; i++) {
      const res = await request.post(`${BACKEND_URL}/auth/login`, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        data: new URLSearchParams({ username: ADMIN_EMAIL, password: ADMIN_PASS }).toString(),
        timeout: 30_000,
      });
      if (res.ok()) {
        const body = await res.json();
        sharedToken = body.access_token;
        break;
      }
      if (res.status() === 429) {
        // eslint-disable-next-line no-console
        console.log(`[auth/login] rate limited (429), retry ${i + 1}/5 en 15s`);
        await new Promise((r) => setTimeout(r, 15_000));
        continue;
      }
      throw new Error(`login failed status=${res.status()}`);
    }
    if (!sharedToken) throw new Error("No se pudo obtener token después de reintentos");
  });

  test.beforeEach(async ({ page }) => {
    await injectAuthReal(page, sharedToken);
  });

  test("renderiza las 10 cards del diagnóstico con data real", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto(`/dashboard/diagnostico/${PIÑA_DIRIGENTE_ID}`, { waitUntil: "commit", timeout: NAV_TIMEOUT });

    // Esperar a que el grid de cards aparezca (post-fetch client-side)
    const grid = page.getByTestId("cards-grid");
    await expect(grid).toBeVisible({ timeout: 90_000 });

    // Las 10 cards deben estar presentes
    for (const code of ["b01", "b02", "b03", "b04", "b05", "b06", "b07", "b08", "b09", "b10"]) {
      const card = page.getByTestId(`card-${code}`);
      await expect(card, `card-${code} no está visible`).toBeVisible();
    }

    // Resumen badge refleja el conteo total
    await expect(page.getByTestId("resumen-badges")).toContainText("/ 10");

    // Console errors: 0 (ignora errores conocidos fuera del scope del dashboard:
    // chatwoot widget externo, 429 de rate-limit en tooling de dev, favicon)
    const realErrors = consoleErrors.filter(
      (e) =>
        !e.includes("chatwoot") &&
        !e.includes("chatmx.mdconsultoria") &&
        !e.toLowerCase().includes("favicon") &&
        !e.includes("429"),
    );
    expect(realErrors, `console errors: ${realErrors.join("\n")}`).toHaveLength(0);
  });

  test("B01 ER muestra headline numérico con porcentaje (no placeholder)", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico/${PIÑA_DIRIGENTE_ID}`, { waitUntil: "commit", timeout: NAV_TIMEOUT });

    const headlineB01 = page.getByTestId("b01-headline");
    await expect(headlineB01).toBeVisible({ timeout: 90_000 });

    const text = await headlineB01.innerText();
    // Piña tiene data real en B01 → headline debe contener "%" y NO ser solo "—"
    expect(text, "B01 headline should contain % sign").toContain("%");
    expect(text.trim(), "B01 headline should not be only em-dash").not.toBe("—");
  });

  test("cards con insufficient_data renderizan el mensaje pero NO se colapsan", async ({
    page,
  }) => {
    await page.goto(`/dashboard/diagnostico/${PIÑA_DIRIGENTE_ID}`, { waitUntil: "commit", timeout: NAV_TIMEOUT });
    await expect(page.getByTestId("cards-grid")).toBeVisible({ timeout: 90_000 });

    // B07 y B08 esperan insufficient_data según SERVICES-REPORT Piña
    const b07 = page.getByTestId("card-b07");
    const b08 = page.getByTestId("card-b08");

    // Ambas cards siguen visibles en el DOM
    await expect(b07).toBeVisible();
    await expect(b08).toBeVisible();

    // Al menos una de las dos muestra el bloque de insufficient data
    const b07Status = await b07.getAttribute("data-status");
    const b08Status = await b08.getAttribute("data-status");
    const anyInsufficient =
      b07Status === "insufficient_data" || b08Status === "insufficient_data";
    expect(anyInsufficient, "Expected B07 or B08 to be insufficient_data").toBe(true);

    // Si está insufficient, el sub-div del estado insuficiente está presente
    if (b07Status === "insufficient_data") {
      await expect(page.getByTestId("card-b07-insufficient")).toBeVisible();
      await expect(page.getByTestId("card-b07-insufficient")).toContainText(
        /insuficient/i,
      );
    }
    if (b08Status === "insufficient_data") {
      await expect(page.getByTestId("card-b08-insufficient")).toBeVisible();
    }
  });

  test("screenshot de referencia del dashboard Piña", async ({ page }) => {
    await page.goto(`/dashboard/diagnostico/${PIÑA_DIRIGENTE_ID}`, { waitUntil: "commit", timeout: NAV_TIMEOUT });
    await expect(page.getByTestId("cards-grid")).toBeVisible({ timeout: 90_000 });

    // pequeña espera a que animaciones/recharts rendereen
    await page.waitForTimeout(1200);

    await page.screenshot({
      path: "test-results/diagnostico-piña.png",
      fullPage: true,
    });
  });
});
