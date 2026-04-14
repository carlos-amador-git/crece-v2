import { test, expect } from "@playwright/test";
import { injectAuthState, mockDashboardApis } from "./helpers/auth";

// ---------------------------------------------------------------------------
// Login page tests — no auth needed
// ---------------------------------------------------------------------------

test.describe("Login page", () => {
  test("renders the login form with email, password, and submit button", async ({
    page,
  }) => {
    await page.goto("/login");

    // Brand heading
    await expect(page.getByRole("heading", { name: "CRECE" })).toBeVisible();

    // Form heading
    await expect(
      page.getByRole("heading", { name: /iniciar sesion/i })
    ).toBeVisible();

    // Email input
    const emailInput = page.locator("#login-email");
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toHaveAttribute("type", "email");

    // Password input
    const passwordInput = page.locator("#login-password");
    await expect(passwordInput).toBeVisible();
    await expect(passwordInput).toHaveAttribute("type", "password");

    // Submit button
    const submitButton = page.getByRole("button", {
      name: /iniciar sesion/i,
    });
    await expect(submitButton).toBeVisible();
    await expect(submitButton).toBeEnabled();
  });

  test("displays version badge", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByText("CRECE v2.0")).toBeVisible();
  });

  test("shows feature highlights on desktop viewport", async ({ page }) => {
    // Set a wide viewport to ensure the desktop features are visible
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/login");

    await expect(
      page.getByText("Monitoreo de crisis y alertas en tiempo real")
    ).toBeVisible();
    await expect(
      page.getByText("Benchmarking competitivo con datos del INE")
    ).toBeVisible();
    await expect(
      page.getByText("Inteligencia electoral georreferenciada")
    ).toBeVisible();
  });

  test("email input is autofocused", async ({ page }) => {
    await page.goto("/login");
    const emailInput = page.locator("#login-email");
    await expect(emailInput).toBeFocused();
  });
});

// ---------------------------------------------------------------------------
// Dashboard pages — require mocked auth
// ---------------------------------------------------------------------------

test.describe("Dashboard pages (authenticated)", () => {
  test.beforeEach(async ({ page }) => {
    await mockDashboardApis(page);
    await injectAuthState(page);
  });

  test("dashboard overview renders with KPI cards", async ({ page }) => {
    await page.goto("/dashboard");

    // Page heading
    await expect(
      page.getByRole("heading", { name: "Dashboard" })
    ).toBeVisible();

    // KPI section
    const kpiSection = page.locator('[aria-label="Indicadores clave"]');
    await expect(kpiSection).toBeVisible();

    // Verify KPI card titles match current UI
    await expect(page.getByText("Tu Audiencia")).toBeVisible();
    await expect(page.getByText("Presencia Digital")).toBeVisible();
    await expect(page.getByText("Conversacion")).toBeVisible();
    await expect(page.getByText("Tema Urgente")).toBeVisible();
  });

  test("dashboard overview renders time filter buttons", async ({ page }) => {
    await page.goto("/dashboard");

    const filterNav = page.locator('[aria-label="Filtros de periodo"]');
    await expect(filterNav).toBeVisible();

    await expect(page.getByRole("button", { name: "Hoy" })).toBeVisible();
    await expect(page.getByRole("button", { name: "7 dias" })).toBeVisible();
    await expect(page.getByRole("button", { name: "30 dias" })).toBeVisible();
    await expect(page.getByRole("button", { name: "90 dias" })).toBeVisible();
  });

  test("dashboard overview shows sentiment chart section", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    // Sentiment chart is below the fold — scroll to it
    const sentimentHeading = page.getByText("Tendencia de Sentimiento");
    await sentimentHeading.scrollIntoViewIfNeeded();
    await expect(sentimentHeading).toBeVisible();
  });

  test("dashboard overview shows system status bar", async ({ page }) => {
    await page.goto("/dashboard");

    const statusBar = page.locator('[aria-label="Estado del sistema"]');
    await expect(statusBar).toBeVisible();
  });

  test("dirigentes list page renders", async ({ page }) => {
    await page.goto("/dashboard/dirigentes");

    // The page should render without crashing. Look for heading or table.
    // Wait for either a heading or the main content area to appear.
    await expect(page.locator("main")).toBeVisible();

    // The page should contain some indication it loaded
    await page.waitForLoadState("networkidle");
  });

  test("electoral page renders", async ({ page }) => {
    await page.goto("/dashboard/electoral");
    await expect(page.locator("main")).toBeVisible();
    await page.waitForLoadState("networkidle");
  });

  test("social monitoring page renders", async ({ page }) => {
    await page.goto("/dashboard/social");
    await expect(page.locator("main")).toBeVisible();
    await page.waitForLoadState("networkidle");
  });

  test("benchmark page renders", async ({ page }) => {
    await page.goto("/dashboard/benchmark");
    await expect(page.locator("main")).toBeVisible();
    await page.waitForLoadState("networkidle");
  });

  test("planes page renders", async ({ page }) => {
    await page.goto("/dashboard/planes");
    await expect(page.locator("main")).toBeVisible();
    await page.waitForLoadState("networkidle");
  });
});

// ---------------------------------------------------------------------------
// Auth redirect — unauthenticated user is sent to login
// ---------------------------------------------------------------------------

test.describe("Auth redirect", () => {
  test("unauthenticated user visiting /dashboard is redirected to /login", async ({
    page,
  }) => {
    // Mock /auth/me to return 401 (no valid token)
    await page.route("**/api/v1/auth/me", (route) =>
      route.fulfill({ status: 401, body: JSON.stringify({ detail: "Not authenticated" }) })
    );

    await page.goto("/dashboard", { waitUntil: "commit" });

    // Should end up on /login (middleware adds ?redirect= query param)
    await page.waitForURL("**/login**", { timeout: 10_000 });
    expect(page.url()).toContain("/login");
  });
});
