"use client";

/**
 * D-23-H · Phase B · Doble KPI hero · KPI IA vs KPI Ajustado + brecha visible.
 *
 * Decisión Claude IA · 2026-04-25 · La transparencia es el audit, no el cap.
 * Cap pesos 0.5-1.5 sin doble métrica visible es teatro. Mostrar ambos hace
 * el self-serving bias auditable.
 */
import { Card, CardContent } from "@/components/ui/card";
import type { ActividadAlineada } from "@/lib/api/types";

interface DobleKpiHeroProps {
  defaultKpi: ActividadAlineada | undefined;
  ajustadoKpi: ActividadAlineada | undefined;
}

const TONE_BY_BRECHA = {
  ok: "text-muted-foreground",
  alta: "text-amber-600 dark:text-amber-400",
  critica: "text-rose-600 dark:text-rose-400",
} as const;

function colorForScore(pct: number | null | undefined): string {
  if (pct == null) return "text-muted-foreground";
  if (pct >= 60) return "text-emerald-600 dark:text-emerald-400";
  if (pct >= 30) return "text-amber-600 dark:text-amber-400";
  return "text-rose-600 dark:text-rose-400";
}

export function DobleKpiHero({ defaultKpi, ajustadoKpi }: DobleKpiHeroProps) {
  const defPct = defaultKpi?.score_pct ?? null;
  const ajuPct = ajustadoKpi?.score_pct ?? null;
  const brecha =
    defPct != null && ajuPct != null ? Math.round(ajuPct - defPct) : null;
  const empty = defaultKpi?.empty_state === "no_classified";

  let toneKey: keyof typeof TONE_BY_BRECHA = "ok";
  if (brecha != null) {
    const abs = Math.abs(brecha);
    if (abs >= 30) toneKey = "critica";
    else if (abs >= 15) toneKey = "alta";
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">Análisis IA</p>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
              Comparativa
            </span>
          </div>
          <p className={`mt-2 font-heading text-4xl font-bold ${colorForScore(defPct)}`}>
            {empty ? "—" : `${defPct}%`}
          </p>
          <p className="mt-1 text-[11px] text-muted-foreground/80">
            Lectura sin ajuste · usada para comparativas inter-dirigentes.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">Tu Lectura</p>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
              Personal
            </span>
          </div>
          <p className={`mt-2 font-heading text-4xl font-bold ${colorForScore(ajuPct)}`}>
            {empty ? "—" : `${ajuPct}%`}
          </p>
          <p className="mt-1 text-[11px] text-muted-foreground/80">
            Con tus pesos · solo visible para ti y MD.
          </p>
        </CardContent>
      </Card>

      {brecha != null && Math.abs(brecha) >= 15 && (
        <div className="md:col-span-2">
          <div className={`rounded-lg border bg-muted/30 px-4 py-2 text-xs ${TONE_BY_BRECHA[toneKey]}`}>
            <strong className="font-medium">Brecha {brecha > 0 ? "+" : ""}{brecha}pp</strong>
            {" · "}
            {Math.abs(brecha) >= 30
              ? "Tu lectura difiere mucho del Análisis IA. Revisa pesos o consulta con tu equipo MD."
              : "Tu lectura difiere del Análisis IA. Considera revisar pesos."}
          </div>
        </div>
      )}
    </div>
  );
}
