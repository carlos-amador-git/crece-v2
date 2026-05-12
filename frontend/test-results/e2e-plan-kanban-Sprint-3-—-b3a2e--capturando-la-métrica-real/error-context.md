# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e/plan-kanban.spec.ts >> Sprint 3 — Kanban del plan estructurado >> completa una tarea capturando la métrica real
- Location: e2e/plan-kanban.spec.ts:303:7

# Error details

```
Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
Call log:
  - navigating to "/login", waiting until "commit"

```

# Test source

```ts
  1   | import { type Page } from "@playwright/test";
  2   | 
  3   | /**
  4   |  * Inject a fake auth token into localStorage so the dashboard shell
  5   |  * considers the user authenticated.
  6   |  *
  7   |  * The AuthProvider in @/lib/auth reads `crece_access_token` from
  8   |  * localStorage and then calls GET /auth/me. We mock both the token
  9   |  * and the API response so the shell renders without a real backend.
  10  |  */
  11  | export async function injectAuthState(page: Page): Promise<void> {
  12  |   const fakeUser = {
  13  |     id: 1,
  14  |     email: "test@crece.mx",
  15  |     nombre: "Test User",
  16  |     rol: "admin",
  17  |     is_active: true,
  18  |   };
  19  | 
  20  |   // Intercept the /auth/me call and return a mock user
  21  |   await page.route("**/api/v1/auth/me", (route) =>
  22  |     route.fulfill({
  23  |       status: 200,
  24  |       contentType: "application/json",
  25  |       body: JSON.stringify(fakeUser),
  26  |     })
  27  |   );
  28  | 
  29  |   // Set localStorage tokens before navigating to any dashboard page.
  30  |   // We need to visit the origin first so localStorage is scoped correctly.
> 31  |   await page.goto("/login", { waitUntil: "commit" });
      |              ^ Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
  32  |   await page.evaluate(() => {
  33  |     localStorage.setItem("crece_access_token", "fake-token-for-e2e");
  34  |     localStorage.setItem("crece_refresh_token", "fake-refresh-for-e2e");
  35  |   });
  36  | }
  37  | 
  38  | /**
  39  |  * Intercept common API calls that dashboard pages make so they don't
  40  |  * hang waiting for a backend. Returns empty/default data.
  41  |  */
  42  | export async function mockDashboardApis(page: Page): Promise<void> {
  43  |   // Overview KPI
  44  |   await page.route("**/api/v1/overview/kpi**", (route) =>
  45  |     route.fulfill({
  46  |       status: 200,
  47  |       contentType: "application/json",
  48  |       body: JSON.stringify({
  49  |         total_dirigentes: 42,
  50  |         avg_ipd_score: 5.5,
  51  |         posts_monitored_24h: 1200,
  52  |         active_alerts: 2,
  53  |         dirigentes_change: 3.1,
  54  |         ipd_change: 0.2,
  55  |         posts_change: 8.5,
  56  |         alerts_change: -1,
  57  |       }),
  58  |     })
  59  |   );
  60  | 
  61  |   // Sentiment trend
  62  |   await page.route("**/api/v1/social/sentiment-trend**", (route) =>
  63  |     route.fulfill({
  64  |       status: 200,
  65  |       contentType: "application/json",
  66  |       body: JSON.stringify([]),
  67  |     })
  68  |   );
  69  | 
  70  |   // Top dirigentes
  71  |   await page.route("**/api/v1/overview/top-dirigentes**", (route) =>
  72  |     route.fulfill({
  73  |       status: 200,
  74  |       contentType: "application/json",
  75  |       body: JSON.stringify([]),
  76  |     })
  77  |   );
  78  | 
  79  |   // Social posts
  80  |   await page.route("**/api/v1/social/posts**", (route) =>
  81  |     route.fulfill({
  82  |       status: 200,
  83  |       contentType: "application/json",
  84  |       body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 10 }),
  85  |     })
  86  |   );
  87  | 
  88  |   // Dirigentes list
  89  |   await page.route("**/api/v1/dirigentes**", (route) =>
  90  |     route.fulfill({
  91  |       status: 200,
  92  |       contentType: "application/json",
  93  |       body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 20 }),
  94  |     })
  95  |   );
  96  | 
  97  |   // Electoral data
  98  |   await page.route("**/api/v1/electoral**", (route) =>
  99  |     route.fulfill({
  100 |       status: 200,
  101 |       contentType: "application/json",
  102 |       body: JSON.stringify({ items: [], total: 0 }),
  103 |     })
  104 |   );
  105 | 
  106 |   // Benchmark data
  107 |   await page.route("**/api/v1/benchmark**", (route) =>
  108 |     route.fulfill({
  109 |       status: 200,
  110 |       contentType: "application/json",
  111 |       body: JSON.stringify({ items: [], total: 0 }),
  112 |     })
  113 |   );
  114 | 
  115 |   // Planes IA
  116 |   await page.route("**/api/v1/planes**", (route) =>
  117 |     route.fulfill({
  118 |       status: 200,
  119 |       contentType: "application/json",
  120 |       body: JSON.stringify({ items: [], total: 0 }),
  121 |     })
  122 |   );
  123 | 
  124 |   // Catch-all for any other API v1 requests to prevent hanging
  125 |   await page.route("**/api/v1/**", (route) => {
  126 |     // Only fulfill if not already handled by a more specific route
  127 |     route.fulfill({
  128 |       status: 200,
  129 |       contentType: "application/json",
  130 |       body: JSON.stringify({}),
  131 |     });
```