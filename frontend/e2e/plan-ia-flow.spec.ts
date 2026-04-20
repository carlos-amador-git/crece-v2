import { expect, test, type BrowserContext, type Page, type Route } from "@playwright/test";

/**
 * Setup robusto de auth para E2E:
 * 1. Cookie del context ANTES de cualquier nav (middleware SSR la ve desde req 1)
 * 2. localStorage inicializado via addInitScript para que AuthProvider no llame /auth/me
 *    antes de tener el token
 * 3. Mock de /auth/me ya hecho por el caller
 */
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
  // Ir a /login primero para establecer origin y luego setear localStorage.
  // SIN esto, localStorage.setItem antes de navegación falla con "access denied".
  await page.goto("/login", { waitUntil: "commit" });
  await page.evaluate(() => {
    localStorage.setItem("crece_access_token", "fake-token-for-e2e");
    localStorage.setItem("crece_refresh_token", "fake-refresh-for-e2e");
  });
}

/**
 * S4 · T5 + T6 + T7 — Flujo E2E completo Plan IA
 *
 * 1. Admin MD abre /dashboard/admin/plan-ia-review → ve cola con 1 recomendación
 * 2. Aprueba la recomendación → transiciona a 'aprobada'
 * 3. Logout → login como cliente → /dashboard/recomendaciones
 * 4. Ve la recomendación aprobada · click "Aceptar y publicar"
 * 5. Selecciona un post ejecutor → vincula (estado='ejecutada')
 * 6. Verifica transición a tab "En seguimiento"
 * 7. Screenshot del flujo
 *
 * Toda la interacción con el backend usa page.route mocks — el test valida
 * solo el comportamiento de la UI. Cuando Agent A termine los endpoints,
 * se quitan los mocks y se corre contra backend real.
 */

// --- Fixtures --------------------------------------------------------

const ADMIN_USER = {
  id: 1,
  email: "md-admin@crece.mx",
  full_name: "Admin MD",
  role: "admin",
  is_active: true,
  org_id: 3,
  dirigente_id: null,
};

const CLIENTE_USER = {
  id: 2,
  email: "pina@crece.mx",
  full_name: "Alejandro Piña",
  role: "viewer",
  is_active: true,
  org_id: 3,
  dirigente_id: 1,
};

interface Recomendacion {
  id: number;
  plan_ia_id: number | null;
  dirigente_id: number;
  dirigente_nombre?: string;
  org_id: number;
  tipo: "start" | "stop" | "continue";
  accion_texto: string;
  ventana_inicio: string | null;
  ventana_fin: string | null;
  ventana_duracion_dias: number;
  criterio_exito: Record<string, unknown> | null;
  principio_conductual: string | null;
  evidencia_respaldo: Record<string, unknown> | null;
  metadatos_llm: Record<string, unknown> | null;
  estado:
    | "propuesta"
    | "aprobada"
    | "rechazada"
    | "modificada"
    | "ejecutada"
    | "completada"
    | "fallida";
  post_ejecutor_id: number | null;
  metricas_predichas: Record<string, number> | null;
  metricas_observadas: Record<string, number> | null;
  veredicto: null;
  veredicto_editado_por_cliente: boolean;
  veredicto_original: null;
  notas_cliente: string | null;
  created_at: string;
  updated_at: string;
}

function seedRecomendacion(): Recomendacion {
  return {
    id: 101,
    plan_ia_id: 42,
    dirigente_id: 1,
    dirigente_nombre: "Alejandro Piña",
    org_id: 3,
    tipo: "start",
    accion_texto:
      "Publicar un reel semanal en Instagram los martes 20h mostrando rendición de cuentas visual",
    ventana_inicio: null,
    ventana_fin: null,
    ventana_duracion_dias: 14,
    criterio_exito: {
      descripcion: "Levantar ER de reels por encima del baseline",
      metrica: "engagement_rate",
      objetivo: 8,
      unidad: "%",
    },
    principio_conductual:
      "Cialdini · Reciprocidad: muestra inversión personal antes de pedir voto",
    evidencia_respaldo: {
      post_id: 9001,
      post_url: "https://www.instagram.com/p/ABC123/",
      metrica_baseline: 4.6,
      fuente: "Piña dashboard B01",
      bloques: ["B01", "B07"],
    },
    metadatos_llm: {
      generador: "Gemma 3:12b",
      modelo: "gemma3:12b-instruct",
      prompt_version: "v1.0",
      temperature: 0.2,
      seed: 42,
      generated_at: "2026-04-19T12:00:00Z",
    },
    estado: "propuesta",
    post_ejecutor_id: null,
    metricas_predichas: { engagement_rate: 8 },
    metricas_observadas: null,
    veredicto: null,
    veredicto_editado_por_cliente: false,
    veredicto_original: null,
    notas_cliente: null,
    created_at: "2026-04-19T11:45:00Z",
    updated_at: "2026-04-19T11:45:00Z",
  };
}

const posts = [
  {
    id: 9101,
    platform: "INSTAGRAM",
    content: "Reel martes — recorrido en Álvaro Obregón · rendición de cuentas",
    url: "https://www.instagram.com/reel/XYZ777/",
    likes: 842,
    comments: 47,
    shares: 12,
    published_at: "2026-04-18T20:10:00Z",
  },
  {
    id: 9102,
    platform: "TWITTER",
    content: "Hilo: 5 puntos de lo que logramos esta semana",
    url: "https://x.com/alejandro_pinha/status/777",
    likes: 210,
    comments: 18,
    shares: 34,
    published_at: "2026-04-17T10:05:00Z",
  },
];

const dirigentes = {
  items: [
    {
      id: 1,
      full_name: "Alejandro Piña",
      cargo: "Diputado",
      partido: "MC",
      estado: "CDMX",
      social_profiles: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-04-01T00:00:00Z",
    },
  ],
  total: 1,
  page: 1,
  per_page: 50,
  pages: 1,
};

// --- Mocks -----------------------------------------------------------

async function mockCommonApis(page: Page, userFn: () => Record<string, unknown>) {
  // /auth/me devuelve user actual
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(userFn()),
    }),
  );

  // Bloquea 401 de endpoints del shell: dashboard overview, alerts, organizaciones
  await page.route("**/api/v1/dashboard/overview**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
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

  // Dirigentes (para filtros del admin y lookup del cliente)
  await page.route("**/api/v1/dirigentes**", (route) => {
    const url = route.request().url();
    if (url.includes("/posts")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(posts),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(dirigentes),
    });
  });

  // Overview KPI del sidebar
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
}

async function mockRecomendacionesAPI(
  page: Page,
  store: { rec: Recomendacion },
) {
  // GET /plan-ia/recomendaciones?estado=...&dirigente_id=...
  const handler = async (route: Route) => {
    const url = route.request().url();
    const method = route.request().method();

    // Seguimiento endpoint
    if (url.includes("/seguimiento") && method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          recomendacion_id: store.rec.id,
          ventana_inicio: store.rec.ventana_inicio,
          ventana_fin: store.rec.ventana_fin,
          dias_transcurridos: 1,
          dias_totales: store.rec.ventana_duracion_dias,
          porcentaje_progreso: 7,
          metricas_predichas: store.rec.metricas_predichas,
          metricas_observadas: { engagement_rate: 5.2 },
          serie_observada: [
            { fecha: "2026-04-19", valor: 5.2, metrica: "engagement_rate" },
          ],
          veredicto_provisional: null,
        }),
      });
    }

    // Vincular post ejecutor
    if (url.includes("/post-ejecutor") && method === "PUT") {
      const body = route.request().postDataJSON() as { post_id: number };
      store.rec.post_ejecutor_id = body.post_id;
      store.rec.estado = "ejecutada";
      store.rec.ventana_inicio = new Date().toISOString();
      const fin = new Date();
      fin.setDate(fin.getDate() + store.rec.ventana_duracion_dias);
      store.rec.ventana_fin = fin.toISOString();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(store.rec),
      });
    }

    // Transición de estado
    if (url.match(/\/plan-ia\/\d+\/estado/) && method === "PUT") {
      const body = route.request().postDataJSON() as {
        estado: Recomendacion["estado"];
      };
      store.rec.estado = body.estado;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(store.rec),
      });
    }

    // Listar recomendaciones — aplica filtro de estado
    if (url.includes("/plan-ia/recomendaciones") && method === "GET") {
      const parsed = new URL(url);
      const estados = parsed.searchParams.getAll("estado");
      let lista: Recomendacion[] = [];
      if (estados.length === 0 || estados.includes(store.rec.estado)) {
        lista = [store.rec];
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(lista),
      });
    }

    // Fallback silencioso
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  };

  await page.route("**/api/v1/plan-ia/**", handler);
}

// --- Test ------------------------------------------------------------

test.describe("Plan IA · flujo E2E completo (T5 + T6 + T7)", () => {
  test("admin aprueba → cliente acepta → vincula post → seguimiento", async ({
    page,
    context,
  }) => {
    const store = { rec: seedRecomendacion() };
    let currentUser: Record<string, unknown> = ADMIN_USER;
    await mockCommonApis(page, () => currentUser);
    await mockRecomendacionesAPI(page, store);
    await setupAuth(page, context);

    // Paso 1. Admin navega a cola
    await page.goto("/dashboard/admin/plan-ia-review", {
      waitUntil: "domcontentloaded",
    });
    await expect(page.getByTestId("page-plan-ia-review")).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      page.getByTestId(`recomendacion-card-${store.rec.id}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`recomendacion-card-${store.rec.id}`),
    ).toHaveAttribute("data-estado", "propuesta");
    await page.screenshot({
      path: "test-results/plan-ia-flow-1-admin-queue.png",
      fullPage: true,
    });

    // Paso 2. Aprueba
    await page.getByTestId(`btn-aprobar-${store.rec.id}`).click();
    // Espera a que la cola la saque (ya no es propuesta)
    await expect(
      page.getByTestId(`recomendacion-card-${store.rec.id}`),
    ).toHaveCount(0, { timeout: 5000 });
    await page.screenshot({
      path: "test-results/plan-ia-flow-2-admin-approved.png",
      fullPage: true,
    });

    // Paso 3. Switch a user cliente
    currentUser = CLIENTE_USER;
    await page.goto("/dashboard/recomendaciones", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("page-recomendaciones-cliente")).toBeVisible();
    await expect(page.getByTestId("tab-pendientes")).toBeVisible();

    // Paso 4. Ve recomendación aprobada
    await expect(
      page.getByTestId(`recomendacion-card-${store.rec.id}`),
    ).toBeVisible();
    await page.screenshot({
      path: "test-results/plan-ia-flow-3-cliente-pendientes.png",
      fullPage: true,
    });

    // Click aceptar
    await page.getByTestId(`btn-aceptar-${store.rec.id}`).click();
    await expect(page.getByTestId("dialog-post-ejecutor")).toBeVisible();

    // Paso 5. Selecciona post
    await expect(page.getByTestId(`post-ejecutor-option-${posts[0].id}`)).toBeVisible();
    await page.getByTestId(`post-ejecutor-option-${posts[0].id}`).click();
    await page.getByTestId("btn-confirmar-post-ejecutor").click();

    // Dialog cierra + banner de éxito
    await expect(page.getByTestId("dialog-post-ejecutor")).toBeHidden();
    await expect(page.getByTestId("success-banner")).toBeVisible();
    await page.screenshot({
      path: "test-results/plan-ia-flow-4-cliente-vinculado.png",
      fullPage: true,
    });

    // Paso 6. Verifica tab En seguimiento
    await page.getByTestId("tab-seguimiento").click();
    await expect(page.getByTestId(`seguimiento-${store.rec.id}`)).toBeVisible({
      timeout: 7000,
    });
    await page.screenshot({
      path: "test-results/plan-ia-flow-5-seguimiento.png",
      fullPage: true,
    });
  });

  test("admin sin permisos no ve la cola", async ({ page, context }) => {
    await mockCommonApis(page, () => CLIENTE_USER); // viewer, no admin
    await mockRecomendacionesAPI(page, { rec: seedRecomendacion() });
    await setupAuth(page, context);

    await page.goto("/dashboard/admin/plan-ia-review", { waitUntil: "commit" });
    await expect(page.getByTestId("admin-guard-denied")).toBeVisible();
  });

  test("admin rechaza con motivo obligatorio", async ({ page, context }) => {
    const store = { rec: seedRecomendacion() };
    await mockCommonApis(page, () => ADMIN_USER);
    await mockRecomendacionesAPI(page, store);
    await setupAuth(page, context);

    await page.goto("/dashboard/admin/plan-ia-review", { waitUntil: "commit" });
    await expect(page.getByTestId(`recomendacion-card-${store.rec.id}`)).toBeVisible();

    await page.getByTestId(`btn-rechazar-${store.rec.id}`).click();
    await expect(page.getByTestId("dialog-rechazo")).toBeVisible();

    // Botón deshabilitado sin motivo
    await expect(page.getByTestId("btn-confirmar-rechazo")).toBeDisabled();

    await page.getByTestId("input-motivo-rechazo").fill("Recomendación duplicada vs S3");
    await expect(page.getByTestId("btn-confirmar-rechazo")).toBeEnabled();
    await page.getByTestId("btn-confirmar-rechazo").click();

    await expect(page.getByTestId("dialog-rechazo")).toBeHidden();
  });
});
