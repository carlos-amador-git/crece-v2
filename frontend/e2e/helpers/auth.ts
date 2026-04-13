import { type Page } from "@playwright/test";

/**
 * Inject a fake auth token into localStorage so the dashboard shell
 * considers the user authenticated.
 *
 * The AuthProvider in @/lib/auth reads `crece_access_token` from
 * localStorage and then calls GET /auth/me. We mock both the token
 * and the API response so the shell renders without a real backend.
 */
export async function injectAuthState(page: Page): Promise<void> {
  const fakeUser = {
    id: 1,
    email: "test@crece.mx",
    nombre: "Test",
    apellido_paterno: "User",
    full_name: "Test User",
    rol: "admin",
    role: "admin",
    is_active: true,
    org_id: 3,
  };

  // Intercept the /auth/me call and return a mock user
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fakeUser),
    })
  );

  // Visit login first to establish origin scope for localStorage and cookies
  await page.goto("/login", { waitUntil: "commit" });
  await page.evaluate(() => {
    localStorage.setItem("crece_access_token", "fake-token-for-e2e");
    localStorage.setItem("crece_refresh_token", "fake-refresh-for-e2e");
    // Cookie for server-side middleware auth check
    document.cookie =
      "crece_access_token=fake-token-for-e2e; path=/; max-age=86400; SameSite=Lax";
  });
}

/**
 * Intercept common API calls that dashboard pages make so they don't
 * hang waiting for a backend. Returns empty/default data.
 */
export async function mockDashboardApis(page: Page): Promise<void> {
  // Overview KPI
  await page.route("**/api/v1/overview/kpi**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_dirigentes: 42,
        avg_ipd_score: 5.5,
        posts_monitored_24h: 1200,
        active_alerts: 2,
        dirigentes_change: 3.1,
        ipd_change: 0.2,
        posts_change: 8.5,
        alerts_change: -1,
      }),
    })
  );

  // Sentiment trend
  await page.route("**/api/v1/social/sentiment-trend**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    })
  );

  // Top dirigentes
  await page.route("**/api/v1/overview/top-dirigentes**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    })
  );

  // Social posts
  await page.route("**/api/v1/social/posts**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 10 }),
    })
  );

  // Dirigentes list
  await page.route("**/api/v1/dirigentes**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 20 }),
    })
  );

  // Electoral data
  await page.route("**/api/v1/electoral**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0 }),
    })
  );

  // Benchmark data
  await page.route("**/api/v1/benchmark**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0 }),
    })
  );

  // Planes IA
  await page.route("**/api/v1/planes**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0 }),
    })
  );

  // Catch-all for any other API v1 requests to prevent hanging
  await page.route("**/api/v1/**", (route) => {
    // Only fulfill if not already handled by a more specific route
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}
