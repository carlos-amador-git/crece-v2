import { test, expect, type Page } from "@playwright/test";

/**
 * E2E Smoke Test for Pepe Monroy (dirigente_id = 57, org_id = 4).
 * Verifies that the diagnostic dashboard (10 cards) renders correctly
 * and that no raw technical strings (e.g. "emotions", "topics_extracted")
 * are visible to the client, confirming our translateMissing mapping works.
 */

const BACKEND_URL = process.env.API_URL || "http://localhost:8002/api/v1";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@consultoriamd.com";
const ADMIN_PASS = process.env.E2E_ADMIN_PASS || "crece2026!";
const PEPE_DIRIGENTE_ID = 57;
const PEPE_ORG_ID = 4;

const NAV_TIMEOUT = 90_000;
const TEST_TIMEOUT = 120_000;
test.setTimeout(TEST_TIMEOUT);

async function injectAuth(page: Page, token: string): Promise<void> {
  await page.goto("/login", { waitUntil: "commit", timeout: NAV_TIMEOUT });
  await page.evaluate(
    ({ t, org }) => {
      localStorage.setItem("crece_access_token", t);
      localStorage.setItem("crece_refresh_token", t);
      localStorage.setItem("crece_active_org_id", String(org));
      document.cookie = `crece_access_token=${t}; path=/; max-age=86400; SameSite=Lax`;
    },
    { t: token, org: PEPE_ORG_ID },
  );
}

let sharedToken: string = "";

test.describe("Diagnóstico E2E Smoke Test — Pepe Monroy (dirigente_id=57)", () => {
  test.beforeAll(async ({ request }) => {
    if (sharedToken) return;
    
    // Login to obtain the JWT token
    const res = await request.post(`${BACKEND_URL}/auth/login`, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      data: new URLSearchParams({ username: ADMIN_EMAIL, password: ADMIN_PASS }).toString(),
      timeout: 30_000,
    });
    
    expect(res.ok(), `Login failed with status ${res.status()}`).toBeTruthy();
    const body = await res.json();
    sharedToken = body.access_token;
    expect(sharedToken).toBeTruthy();
  });

  test.beforeEach(async ({ page }) => {
    await injectAuth(page, sharedToken);
  });

  test("debe cargar las 10 tarjetas del diagnóstico y enmascarar los textos técnicos del backend", async ({ page }) => {
    // Navigate directly to Pepe Monroy's diagnostic dashboard
    await page.goto(`/dashboard/diagnostico/${PEPE_DIRIGENTE_ID}`, { waitUntil: "commit", timeout: NAV_TIMEOUT });

    // Wait for the grid of cards to appear
    const grid = page.getByTestId("cards-grid");
    await expect(grid).toBeVisible({ timeout: 45_000 });

    // Verify all 10 cards are visible in the DOM
    const cards = ["b01", "b02", "b03", "b04", "b05", "b06", "b07", "b08", "b09", "b10"];
    for (const code of cards) {
      const card = page.getByTestId(`card-${code}`);
      await expect(card, `La tarjeta card-${code} no está visible`).toBeVisible();
    }

    // Verify that the overview badge shows 10/10 cards
    await expect(page.getByTestId("resumen-badges")).toContainText("/ 10");

    // Take a screenshot of the dashboard for visual verification
    await page.screenshot({
      path: "test-results/diagnostico-pepe-monroy.png",
      fullPage: true,
    });

    // Extract the body text to perform checks for technical/debug strings
    const bodyText = await page.locator("body").innerText();

    // Verify that NO raw technical error/missing strings are present in the DOM
    const rawTechnicalPatterns = [
      "self sin social_profiles",
      "competidor_directo_ids vac",
      "Todos los rivales sin datos en ventana",
      "social_profiles=0",
      "social_posts.emotions=NULL",
      "sentiment_analyses.emotions=NULL",
      "extensión NLP Plutchik",
      "topics_extracted en 28d",
      "topics_extracted",
    ];

    for (const pattern of rawTechnicalPatterns) {
      expect(bodyText, `Se encontró la cadena técnica cruda '${pattern}' en la UI, lo cual no es amigable para el cliente.`).not.toContain(pattern);
    }

    console.log("Smoke test passed: all cards are visible, and technical keys are masked correctly.");
  });
});
