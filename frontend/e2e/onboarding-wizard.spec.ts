import {
  expect,
  test,
  type BrowserContext,
  type Page,
  type Route,
} from "@playwright/test";

/**
 * S5 · Onboarding Wizard E2E — Agent C
 *
 * Verifica el flujo completo de los 9 pasos del wizard + reglas duras:
 *   - D-23: activar scraping requiere confirmación humana explícita
 *   - D-22: competidores mínimo 1 bloquean el stepper
 *   - navegación stepper atrás/adelante/saltar
 *   - screenshots de cada paso para demo CEO
 *
 * NOTA: Los endpoints del Agent B pueden no estar mergeados en el momento
 * de correr este test. Todos los endpoints usan `page.route()` mocks que
 * respetan el contrato del spec SPRINT-S5-SCOPING §T1-T9. Cuando el backend
 * esté live, basta con quitar los mocks.
 */

const ADMIN_USER = {
  id: 1,
  email: "md-admin@crece.mx",
  full_name: "Admin MD",
  role: "admin",
  is_active: true,
  org_id: 3,
  dirigente_id: null,
};

const DIRIGENTE_ID = 1;

async function setupAuth(page: Page, context: BrowserContext) {
  await context.addCookies([
    {
      name: "crece_access_token",
      value: "fake-token-for-e2e",
      domain: "localhost",
      path: "/",
      httpOnly: false,
      secure: false,
      sameSite: "Lax",
      expires: Math.floor(Date.now() / 1000) + 86400,
    },
  ]);
  await page.goto("/login", { waitUntil: "commit" });
  await page.evaluate(() => {
    localStorage.setItem("crece_access_token", "fake-token-for-e2e");
    localStorage.setItem("crece_refresh_token", "fake-refresh-for-e2e");
    // Cookie duplicada vía document.cookie para compat con patrón de plan-ia
    document.cookie =
      "crece_access_token=fake-token-for-e2e; path=/; max-age=86400; SameSite=Lax";
    // Limpiar wizard state previo
    localStorage.removeItem("crece_onboarding_wizard");
  });
}

async function mockShellApis(page: Page) {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(ADMIN_USER),
    }),
  );
  await page.route("**/api/v1/overview/kpi**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_dirigentes: 1,
        avg_ipd_score: 4.2,
        posts_monitored_24h: 120,
        active_alerts: 0,
        dirigentes_change: 0,
        ipd_change: 0,
        posts_change: 0,
        alerts_change: 0,
        total_audiencia: 2231,
        contactos_periodo: 0,
        tema_urgente: null,
      }),
    }),
  );
  await page.route("**/api/v1/alerts**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    }),
  );
  await page.route("**/api/v1/organizaciones/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 50, pages: 0 }),
    }),
  );
  await page.route("**/api/v1/organizaciones?**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 50, pages: 0 }),
    }),
  );
  await page.route("**/api/v1/dirigentes**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 50, pages: 0 }),
    }),
  );
  // Catch-all último recurso — evita 401 silenciosos que redirigen a /login
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    }),
  );
}

/**
 * Mocks del contrato T1-T9 de SPRINT-CURRENT.
 * Si Agent B cambia el shape, ajustar aquí sin tocar el wizard UI.
 */
async function mockOnboardingApis(page: Page) {
  const handler = async (route: Route) => {
    const url = route.request().url();
    const method = route.request().method();

    // T3 · SERP search
    if (url.includes("/serp-search")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          provider: "brightdata",
          candidates: [
            {
              platform: "INSTAGRAM",
              url: "https://instagram.com/alejandro.pinha",
              handle: "alejandro.pinha",
              full_name: "Alejandro Piña",
              score: 0.85,
              verified: true,
              followers: 2231,
            },
            {
              platform: "TWITTER",
              url: "https://x.com/Alejandro_Pinha",
              handle: "Alejandro_Pinha",
              full_name: "Alejandro Piña",
              score: 0.72,
              verified: false,
              followers: 3100,
            },
          ],
        }),
      });
    }

    // T4 · validate-account
    if (url.includes("/validate-account")) {
      const body = route.request().postDataJSON() as {
        platform: string;
        url: string;
      };
      const handle =
        new URL(body.url).pathname.replace(/^\/+|\/+$/g, "").split("/")[0] ??
        "unknown";
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          platform: body.platform,
          url: body.url,
          handle: handle.replace(/^@/, ""),
          full_name: "Alejandro Piña",
          verified: true,
          followers: 2231,
          posts_count: 487,
          score: 0.85,
          signals: {
            full_name_match: true,
            verified: true,
            followers_above_50k: false,
            posts_above_20: true,
          },
        }),
      });
    }

    // T6 · oauth init → stub
    if (url.includes("/oauth/init")) {
      const body = route.request().postDataJSON() as { platform: string };
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          platform: body.platform,
          redirect_url: "https://example.com/oauth/stub",
          status: "stub",
          message: "Stub OAuth — pendiente Meta App Review (DIFERIDO-02)",
        }),
      });
    }

    // T9 · activate
    if (url.match(/\/onboarding\/activate\/\d+/) && method === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          dirigente_id: DIRIGENTE_ID,
          sync_status: "scraping",
          task_id: "task-mock-123",
          data_fidelity_tier_by_platform: {
            INSTAGRAM: "T2",
            FACEBOOK: "T2",
            TWITTER: "T3",
          },
          message: "Activación disparada — scraping en progreso",
        }),
      });
    }

    // Resto: T1, T2, T5, T7, T8 — persistencia silenciosa
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  };

  await page.route("**/api/v1/onboarding/**", handler);
}

test.describe("Onboarding Wizard · S5 flujo 9 pasos", () => {
  test("flujo completo 9 pasos con data real Piña (id=1)", async ({
    page,
    context,
  }) => {
    await mockShellApis(page);
    await mockOnboardingApis(page);
    await setupAuth(page, context);

    await page.goto(`/dashboard/onboarding/${DIRIGENTE_ID}`, {
      waitUntil: "commit",
    });
    await expect(page.getByTestId("page-onboarding-wizard")).toBeVisible({
      timeout: 10_000,
    });

    // ---- Paso 1: Perfil ---------------------------------------------------
    await expect(page.getByTestId("step-1-perfil")).toBeVisible();
    await expect(page.getByTestId("btn-next")).toBeDisabled();
    await page.getByTestId("radio-perfil-politico_activo").click();
    await expect(page.getByTestId("btn-next")).toBeEnabled();
    await page.screenshot({
      path: "test-results/onboarding-step1-perfil.png",
      fullPage: true,
    });
    await page.getByTestId("btn-next").click();

    // ---- Paso 2: Cuentas manuales ----------------------------------------
    await expect(page.getByTestId("step-2-accounts")).toBeVisible();
    await expect(page.getByTestId("btn-next")).toBeDisabled();
    await page
      .getByTestId("input-account-INSTAGRAM")
      .fill("https://instagram.com/alejandro.pinha");
    await expect(page.getByTestId("handle-preview-INSTAGRAM")).toBeVisible();
    await page
      .getByTestId("input-account-TWITTER")
      .fill("https://x.com/Alejandro_Pinha");
    await page.screenshot({
      path: "test-results/onboarding-step2-accounts.png",
      fullPage: true,
    });
    await page.getByTestId("btn-next").click();

    // ---- Paso 3: SERP opcional — saltar -----------------------------------
    await expect(page.getByTestId("step-3-serp")).toBeVisible();
    await page.screenshot({
      path: "test-results/onboarding-step3-serp.png",
      fullPage: true,
    });
    await page.getByTestId("btn-skip").click();

    // ---- Paso 4: Validación (auto) ---------------------------------------
    await expect(page.getByTestId("step-4-validation")).toBeVisible();
    // Espera que aparezcan los badges de score
    await expect(page.getByTestId("all-validated-ok")).toBeVisible({
      timeout: 8000,
    });
    await page.screenshot({
      path: "test-results/onboarding-step4-validation.png",
      fullPage: true,
    });
    await page.getByTestId("btn-next").click();

    // ---- Paso 5: Confirmación humana (D-23 REGLA DURA) -------------------
    await expect(page.getByTestId("step-5-confirmation")).toBeVisible();
    // Antes de confirmar: botón next DEBE estar disabled
    await expect(page.getByTestId("btn-next")).toBeDisabled();
    await expect(
      page.getByTestId("confirmation-required-warning"),
    ).toBeVisible();
    await page.screenshot({
      path: "test-results/onboarding-step5-confirmation-blocked.png",
      fullPage: true,
    });
    // Confirmar al menos una cuenta
    await page.getByTestId("confirm-INSTAGRAM").first().click();
    await expect(page.getByTestId("confirmation-ok")).toBeVisible();
    await expect(page.getByTestId("btn-next")).toBeEnabled();
    await page.screenshot({
      path: "test-results/onboarding-step5-confirmation-ok.png",
      fullPage: true,
    });
    await page.getByTestId("btn-next").click();

    // ---- Paso 6: OAuth — saltable ----------------------------------------
    await expect(page.getByTestId("step-6-oauth")).toBeVisible();
    // X debe estar grayed
    await expect(page.getByTestId("oauth-row-TWITTER")).toBeVisible();
    await page.getByTestId("btn-oauth-INSTAGRAM").click();
    await page.screenshot({
      path: "test-results/onboarding-step6-oauth.png",
      fullPage: true,
    });
    await page.getByTestId("btn-skip").click();

    // ---- Paso 7: Competidores (D-22 mínimo 1) ----------------------------
    await expect(page.getByTestId("step-7-competidores")).toBeVisible();
    await expect(page.getByTestId("btn-next")).toBeDisabled();
    await page.getByTestId("btn-add-competidor").click();
    await page
      .getByTestId("input-comp-name-0")
      .fill("Laura Ballesteros");
    await page.getByTestId("input-comp-cargo-0").fill("Diputada local");
    await page
      .getByTestId("input-comp-url-0")
      .fill("https://instagram.com/lauraballesteros");
    await expect(page.getByTestId("btn-next")).toBeEnabled();
    await page.screenshot({
      path: "test-results/onboarding-step7-competidores.png",
      fullPage: true,
    });
    await page.getByTestId("btn-next").click();

    // ---- Paso 8: Promesas ------------------------------------------------
    await expect(page.getByTestId("step-8-promesas")).toBeVisible();
    await expect(page.getByTestId("btn-next")).toBeDisabled();
    await page.getByTestId("btn-add-promesa").click();
    await page
      .getByTestId("input-prom-text-0")
      .fill("Ampliar la Línea 12 del Metro antes de concluir sexenio");
    await page.getByTestId("input-prom-fecha-0").fill("2027-09-30");
    await expect(page.getByTestId("btn-next")).toBeEnabled();
    await page.screenshot({
      path: "test-results/onboarding-step8-promesas.png",
      fullPage: true,
    });
    await page.getByTestId("btn-next").click();

    // ---- Paso 9: Activación ----------------------------------------------
    await expect(page.getByTestId("step-9-activation")).toBeVisible();
    await expect(page.getByTestId("btn-activar-cuenta")).toBeEnabled();
    await page.screenshot({
      path: "test-results/onboarding-step9-pre-activation.png",
      fullPage: true,
    });
    await page.getByTestId("btn-activar-cuenta").click();
    await expect(page.getByTestId("activation-success")).toBeVisible({
      timeout: 8000,
    });
    await page.screenshot({
      path: "test-results/onboarding-step9-activated.png",
      fullPage: true,
    });
  });

  test("D-23: sin confirmación humana, no se puede avanzar al paso 6", async ({
    page,
    context,
  }) => {
    await mockShellApis(page);
    await mockOnboardingApis(page);
    await setupAuth(page, context);

    await page.goto(`/dashboard/onboarding/${DIRIGENTE_ID}`, {
      waitUntil: "commit",
    });

    // Avanzar hasta paso 5 con el mínimo de datos
    await page.getByTestId("radio-perfil-politico_activo").click();
    await page.getByTestId("btn-next").click();
    await page
      .getByTestId("input-account-INSTAGRAM")
      .fill("https://instagram.com/alejandro.pinha");
    await page.getByTestId("btn-next").click();
    await page.getByTestId("btn-skip").click(); // SERP
    await expect(page.getByTestId("all-validated-ok")).toBeVisible({
      timeout: 8000,
    });
    await page.getByTestId("btn-next").click();

    // Paso 5 — SIN marcar confirmación, el botón next debe estar disabled
    await expect(page.getByTestId("step-5-confirmation")).toBeVisible();
    await expect(page.getByTestId("btn-next")).toBeDisabled();

    // Validar que warning esté visible
    await expect(
      page.getByTestId("confirmation-required-warning"),
    ).toBeVisible();

    // Intentar click — no debe avanzar (disabled)
    await page.getByTestId("btn-next").click({ force: true }).catch(() => {});
    await expect(page.getByTestId("step-5-confirmation")).toBeVisible();
    await expect(page.getByTestId("step-6-oauth")).not.toBeVisible();
  });

  test("D-22: sin competidores, paso 7 bloquea Siguiente", async ({
    page,
    context,
  }) => {
    await mockShellApis(page);
    await mockOnboardingApis(page);
    await setupAuth(page, context);

    await page.goto(`/dashboard/onboarding/${DIRIGENTE_ID}`, {
      waitUntil: "commit",
    });

    // Jump directo al paso 7 via stepper dot (state allowed by wizard)
    await page.getByTestId("radio-perfil-politico_activo").click();
    await page.getByTestId("stepper-dot-7").click();
    await expect(page.getByTestId("step-7-competidores")).toBeVisible();
    await expect(page.getByTestId("btn-next")).toBeDisabled();
  });

  test("Stepper permite retroceder y el state persiste en localStorage", async ({
    page,
    context,
  }) => {
    await mockShellApis(page);
    await mockOnboardingApis(page);
    await setupAuth(page, context);

    await page.goto(`/dashboard/onboarding/${DIRIGENTE_ID}`, {
      waitUntil: "commit",
    });

    await page.getByTestId("radio-perfil-politico_activo").click();
    await page.getByTestId("btn-next").click();
    await page
      .getByTestId("input-account-INSTAGRAM")
      .fill("https://instagram.com/alejandro.pinha");

    // Verificar persistencia: reload y state sigue
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("step-2-accounts")).toBeVisible();
    await expect(page.getByTestId("input-account-INSTAGRAM")).toHaveValue(
      "https://instagram.com/alejandro.pinha",
    );

    // Retroceder funciona
    await page.getByTestId("btn-back").click();
    await expect(page.getByTestId("step-1-perfil")).toBeVisible();
  });
});
