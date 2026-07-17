"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { ActividadAlineada } from "@/lib/api/types";

/**
 * D-23-G' · KPI Actividad Política Alineada (2026-04-24)
 *
 * Reemplaza el "Sentimiento Prom." flipeado × -1 que producía resultados
 * contradictorios para oposición con posts personales (Copa Naranja → Negativo
 * -50% sin sustento). Plan: .context/PLAN-D-23-G-actividad-alineada-2026-04-24.md
 *
 * Fórmula por rol:
 * - Oposición: (target=oficialismo + target=propio) / total_clasificado
 * - Oficialismo: (target=propio + target=oposicion) / total_clasificado
 * - Independiente: target=propio / total_clasificado
 *
 * Sin flip · sin score numérico · solo proporción de actividad alineada.
 */

interface ActividadAlineadaCardProps {
  data: ActividadAlineada | undefined;
}

const ROL_FORMULA: Record<string, string> = {
  oposicion:
    "Como oposición, tu trabajo es construir narrativa: criticar al oficialismo o promover tu propia agenda.",
  oficialismo:
    "Como oficialismo, tu trabajo es defender logros propios o responder a la oposición.",
  independiente:
    "Como independiente, tu trabajo es construir agenda propia.",
};

const ROL_BADGE: Record<string, string> = {
  oposicion: "Oposición",
  oficialismo: "Oficialismo",
  independiente: "Independiente",
};

function colorForScore(pct: number | null | undefined): string {
  if (pct == null) return "text-muted-foreground";
  if (pct >= 60) return "text-emerald-600 dark:text-emerald-400";
  if (pct >= 30) return "text-amber-600 dark:text-amber-400";
  return "text-rose-600 dark:text-rose-400";
}

export function ActividadAlineadaCard({ data }: ActividadAlineadaCardProps) {
  // DISENO-actores-politicos-2026-07-16: rol NULL = fallo visible, no número.
  if (data?.empty_state === "rol_sin_clasificar") {
    return (
      <Card className="relative overflow-hidden">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">Actividad Política Alineada</p>
          <div className="mt-1 flex items-baseline gap-2">
            <p className="font-heading text-xl font-bold text-muted-foreground">—</p>
            <span className="inline-flex items-center rounded-full bg-rose-500/15 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:text-rose-400">
              Rol político sin clasificar
            </span>
          </div>
          <p className="mt-1.5 text-[11px] text-muted-foreground/80 leading-tight">
            Un administrador debe asignar el rol (oficialismo · oposición ·
            independiente) para calcular este KPI.
          </p>
        </CardContent>
      </Card>
    );
  }
  if (!data || data.empty_state === "no_classified") {
    return (
      <Card className="relative overflow-hidden">
        {/* Shimmer indicador de proceso activo · 2026-05-12 */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-amber-500/20"
        >
          <div className="h-full w-1/3 animate-[shimmer_2s_linear_infinite] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
        </div>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">Actividad Política Alineada</p>
          <div className="mt-1 flex items-baseline gap-2">
            <p className="font-heading text-xl font-bold text-muted-foreground">—</p>
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-500 opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-500" />
              </span>
              IA procesando
            </span>
          </div>
          <p className="mt-1.5 text-[11px] text-muted-foreground/80 leading-tight">
            Clasificación IA en proceso · revisa en 1h
          </p>
        </CardContent>
      </Card>
    );
  }

  const pct = data.score_pct ?? 0;
  const rol = data.rol_politico || "independiente";
  const formula = ROL_FORMULA[rol] || ROL_FORMULA.independiente;
  const total = data.breakdown.oficialismo + data.breakdown.oposicion + data.breakdown.propio + data.breakdown.personal;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm text-muted-foreground">Actividad Política Alineada · {data.days}d</p>
          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
            {ROL_BADGE[rol] ?? rol}
          </span>
        </div>
        <p className={`mt-1 font-heading text-3xl font-bold ${colorForScore(pct)}`}>
          {pct}%
        </p>
        <p className="text-[11px] text-muted-foreground/80 leading-tight" title={formula}>
          {data.total_classified} de {total} posts contribuyen al rol
        </p>

        {/* Breakdown 4-cat · barras apiladas */}
        <div className="mt-3 space-y-1.5">
          <BreakdownPill
            label="Critica oficialismo"
            count={data.breakdown.oficialismo}
            total={total}
            tone="rose"
          />
          <BreakdownPill
            label="Sobre oposición"
            count={data.breakdown.oposicion}
            total={total}
            tone="violet"
          />
          <BreakdownPill
            label="Propio / agenda"
            count={data.breakdown.propio}
            total={total}
            tone="emerald"
          />
          <BreakdownPill
            label="Personal"
            count={data.breakdown.personal}
            total={total}
            tone="slate"
          />
        </div>
      </CardContent>
    </Card>
  );
}

function BreakdownPill({
  label,
  count,
  total,
  tone,
}: {
  label: string;
  count: number;
  total: number;
  tone: "rose" | "violet" | "emerald" | "slate";
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  const toneClass: Record<typeof tone, string> = {
    rose: "bg-rose-500/70",
    violet: "bg-violet-500/70",
    emerald: "bg-emerald-500/70",
    slate: "bg-slate-400/70",
  };
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <span className="w-32 truncate text-muted-foreground">{label}</span>
      <div className="flex-1 h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full ${toneClass[tone]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right tabular-nums text-muted-foreground">
        {count}
      </span>
    </div>
  );
}
