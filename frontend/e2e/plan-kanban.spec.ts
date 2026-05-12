import { test, expect, type Page } from "@playwright/test";
import { injectAuthState } from "./helpers/auth";

/**
 * S3.9 — Kanban del plan estructurado
 *
 * Verifica el flujo end-to-end del tablero Kanban (Sprint 3):
 *   1. Admin abre un plan existente con tareas estructuradas
 *   2. Ve las tareas distribuidas en 3 columnas (Por hacer / En curso / Hecho)
 *   3. Mueve una tarea TODO → IN_PROGRESS
 *   4. Edita un campo inline
 *   5. Completa una tarea capturando la métrica real
 *   6. Verifica que la barra de progreso refleja el cambio
 *
 * Toda la interacción con el backend está mockeada — este test valida SOLO
 * el comportamiento del componente KanbanBoard y el routing, no el backend.
 */

const PLAN_ID = 42;

type TaskState = "TODO" | "IN_PROGRESS" | "DONE";

interface MockTarea {
  id: number;
  plan_id: number;
  orden: number;
  titulo: string;
  descripcion: string;
  plataforma: string | null;
  formato: string | null;
  frecuencia: string | null;
  responsable: string | null;
  deadline: string | null;
  metrica_objetivo: string | null;
  metrica_valor_objetivo: number | null;
  metrica_valor_real: number | null;
  estado: TaskState;
  completado_at: string | null;
  cambios_historial: Array<Record<string, unknown>> | null;
  created_at: string;
  updated_at: string;
}

function makeTarea(over: Partial<MockTarea>): MockTarea {
  const base: MockTarea = {
    id: 0,
    plan_id: PLAN_ID,
    orden: 0,
    titulo: "Tarea sin título",
    descripcion: "Descripción por defecto de la tarea",
    plataforma: null,
    formato: null,
    frecuencia: null,
    responsable: null,
    deadline: null,
    metrica_objetivo: null,
    metrica_valor_objetivo: null,
    metrica_valor_real: null,
    estado: "TODO",
    completado_at: null,
    cambios_historial: null,
    created_at: "2026-04-11T10:00:00Z",
    updated_at: "2026-04-11T10:00:00Z",
  };
  return { ...base, ...over };
}

/**
 * Mutable in-memory store shared between route handlers so PATCH/complete
 * can reflect updates back into subsequent GET calls.
 */
async function setupKanbanMocks(page: Page): Promise<void> {
  const tareas: MockTarea[] = [
    makeTarea({
      id: 1,
      orden: 0,
      titulo: "Publicar reel semanal en Instagram",
      descripcion:
        "Grabar y publicar un reel corto sobre movilidad los martes a las 20:00",
      plataforma: "INSTAGRAM",
      formato: "reel",
      frecuencia: "1 vez por semana",
      responsable: "Community manager",
      metrica_objetivo: "engagement_rate",
      metrica_valor_objetivo: 0.08,
      estado: "TODO",
    }),
    makeTarea({
      id: 2,
      orden: 1,
      titulo: "Hilo semanal de rendición de cuentas en X",
      descripcion:
        "Hilo de 5-7 tweets resumiendo las reuniones de la semana del dirigente",
      plataforma: "TWITTER",
      formato: "hilo",
      frecuencia: "1 vez por semana",
      responsable: "Equipo comunicación",
      metrica_objetivo: "impressions",
      metrica_valor_objetivo: 5000,
      estado: "IN_PROGRESS",
    }),
    makeTarea({
      id: 3,
      orden: 2,
      titulo: "Hacer directo de Facebook sobre seguridad",
      descripcion: "Transmisión en vivo de 15 min respondiendo preguntas de seguridad",
      plataforma: "FACEBOOK",
      formato: "live",
      frecuencia: "una sola vez",
      responsable: "Dirigente",
      metrica_objetivo: "reach",
      metrica_valor_objetivo: 2000,
      metrica_valor_real: 2150,
      completado_at: "2026-04-10T22:30:00Z",
      estado: "DONE",
    }),
  ];

  function computeProgreso() {
    const counts = { TODO: 0, IN_PROGRESS: 0, DONE: 0 };
    const impacto: Record<string, number> = {};
    for (const t of tareas) {
      counts[t.estado]++;
      if (t.metrica_objetivo && t.metrica_valor_real !== null) {
        impacto[t.metrica_objetivo] =
          (impacto[t.metrica_objetivo] ?? 0) + t.metrica_valor_real;
      }
    }
    return {
      plan_id: PLAN_ID,
      total_tareas: tareas.length,
      tareas_todo: counts.TODO,
      tareas_in_progress: counts.IN_PROGRESS,
      tareas_done: counts.DONE,
      porcentaje_ejecutado:
        tareas.length === 0 ? 0 : Math.round((counts.DONE / tareas.length) * 1000) / 10,
      impacto_acumulado: impacto,
    };
  }

  // Plan detail (minimal, so the kanban page header renders)
  await page.route(`**/api/v1/planes/${PLAN_ID}`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: PLAN_ID,
        dirigente_id: 1,
        tipo: "CONSOLIDACION",
        contenido: "Tesis central del plan de consolidación",
        modelo_ia: "ollama/gemma3:12b",
        prompt_usado: "prompt mock",
        datos_entrada: null,
        generado_por_id: 1,
        aprobado: false,
        created_at: "2026-04-11T09:00:00Z",
      }),
    })
  );

  // List of tareas (GET)
  await page.route(`**/api/v1/planes/${PLAN_ID}/tareas`, async (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(tareas),
      });
    }
    return route.fallback();
  });

  // Progreso aggregate
  await page.route(`**/api/v1/planes/${PLAN_ID}/progreso`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(computeProgreso()),
    })
  );

  // PATCH individual tarea — update in-memory store and echo back
  await page.route(
    new RegExp(`/api/v1/planes/${PLAN_ID}/tareas/(\\d+)$`),
    async (route) => {
      const req = route.request();
      const match = req.url().match(/tareas\/(\d+)$/);
      if (!match) return route.fallback();
      const taskId = Number(match[1]);
      const tarea = tareas.find((t) => t.id === taskId);
      if (!tarea) {
        return route.fulfill({ status: 404, body: "{}" });
      }
      if (req.method() === "PATCH") {
        const patch = JSON.parse(req.postData() || "{}");
        Object.assign(tarea, patch, {
          updated_at: new Date().toISOString(),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(tarea),
      });
    }
  );

  // POST complete tarea
  await page.route(
    new RegExp(`/api/v1/planes/${PLAN_ID}/tareas/(\\d+)/complete$`),
    async (route) => {
      const req = route.request();
      const match = req.url().match(/tareas\/(\d+)\/complete$/);
      if (!match) return route.fallback();
      const taskId = Number(match[1]);
      const tarea = tareas.find((t) => t.id === taskId);
      if (!tarea) {
        return route.fulfill({ status: 404, body: "{}" });
      }
      const body = JSON.parse(req.postData() || "{}");
      tarea.estado = "DONE";
      tarea.metrica_valor_real = body.metrica_valor_real ?? null;
      tarea.completado_at = new Date().toISOString();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(tarea),
      });
    }
  );
}

test.describe("Sprint 3 — Kanban del plan estructurado", () => {
  test.beforeEach(async ({ page }) => {
    await injectAuthState(page);
    await setupKanbanMocks(page);
  });

  test("renderiza 3 columnas con las tareas distribuidas por estado", async ({
    page,
  }) => {
    await page.goto(`/dashboard/planes/${PLAN_ID}/kanban`);

    // Column headers
    await expect(page.getByRole("heading", { name: "Por hacer" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "En curso" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Hecho" })).toBeVisible();

    // Cards by title
    await expect(
      page.getByText("Publicar reel semanal en Instagram")
    ).toBeVisible();
    await expect(
      page.getByText("Hilo semanal de rendición de cuentas en X")
    ).toBeVisible();
    await expect(
      page.getByText("Hacer directo de Facebook sobre seguridad")
    ).toBeVisible();

    // Progress bar reflects 1/3 done = 33.3%
    await expect(page.getByText("33.3% ejecutado")).toBeVisible();
  });

  test("mueve una tarea TODO → IN_PROGRESS vía botón '→'", async ({ page }) => {
    await page.goto(`/dashboard/planes/${PLAN_ID}/kanban`);

    const todoCard = page.locator("text=Publicar reel semanal en Instagram");
    await expect(todoCard).toBeVisible();

    // Locate the forward button inside the same card
    const card = todoCard.locator("..").locator("..").locator("..");
    await card.getByRole("button").last().click();

    // Wait for the PATCH to propagate + refetch
    await expect(page.getByText("En curso").locator("..")).toContainText(
      "Publicar reel semanal en Instagram"
    );
  });

  test("permite editar el título inline en el diálogo de edición", async ({
    page,
  }) => {
    await page.goto(`/dashboard/planes/${PLAN_ID}/kanban`);

    const card = page
      .locator("text=Hilo semanal de rendición de cuentas en X")
      .locator("..")
      .locator("..")
      .locator("..");
    await card.getByRole("button", { name: /editar/i }).click();

    const titleInput = page.getByLabel("Título");
    await expect(titleInput).toBeVisible();
    await titleInput.fill("Hilo diario de rendición de cuentas en X");
    await titleInput.blur();

    await page.getByRole("button", { name: /cerrar/i }).click();
    await expect(
      page.getByText("Hilo diario de rendición de cuentas en X")
    ).toBeVisible();
  });

  test("completa una tarea capturando la métrica real", async ({ page }) => {
    await page.goto(`/dashboard/planes/${PLAN_ID}/kanban`);

    // Move TODO → IN_PROGRESS first so the "Completar" button appears on
    // the IN_PROGRESS card
    const todoCard = page
      .locator("text=Publicar reel semanal en Instagram")
      .locator("..")
      .locator("..")
      .locator("..");
    await todoCard.getByRole("button").last().click();

    // Now the same task should have a Completar button
    const movedCard = page
      .locator("text=Publicar reel semanal en Instagram")
      .locator("..")
      .locator("..")
      .locator("..");
    await movedCard.getByRole("button", { name: /completar/i }).click();

    // Dialog: "Completar tarea"
    await expect(
      page.getByRole("heading", { name: /completar tarea/i })
    ).toBeVisible();
    await page.getByLabel(/valor real/i).fill("0.092");
    await page.getByLabel(/nota/i).fill("Reel de la semana 1 superó la meta");
    await page.getByRole("button", { name: /confirmar/i }).click();

    // Task card moves to DONE column and progress goes to 2/3 = 66.7%
    await expect(page.getByText("66.7% ejecutado")).toBeVisible();
  });
});
