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
  if (!data || data.empty_state === "no_classified") {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">Actividad Política Alineada</p>
          <p className="mt-1 font-heading text-xl font-bold text-muted-foreground">
            —
          </p>
          <p className="mt-1 text-[10px] text-muted-foreground/70">
            Análisis en proceso · clasificación IA pendiente
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
