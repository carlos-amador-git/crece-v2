"use client";

import { Activity, CheckCircle2, Clock, XCircle } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  useSeguimiento,
  type Recomendacion,
} from "@/lib/api/hooks/use-recomendaciones";

interface Props {
  recomendacion: Recomendacion;
}

const veredictoStyles: Record<string, string> = {
  exitosa: "bg-emerald-500/10 text-emerald-700 border-emerald-500/30 dark:text-emerald-300",
  parcial: "bg-amber-500/10 text-amber-700 border-amber-500/30 dark:text-amber-300",
  fallida: "bg-rose-500/10 text-rose-700 border-rose-500/30 dark:text-rose-300",
};

export function SeguimientoCard({ recomendacion: r }: Props) {
  const { data, isLoading } = useSeguimiento(r.id);

  const predichas = data?.metricas_predichas ?? r.metricas_predichas ?? {};
  const observadas = data?.metricas_observadas ?? r.metricas_observadas ?? {};
  const pct =
    data?.porcentaje_progreso ??
    (r.ventana_inicio && r.ventana_fin
      ? Math.max(
          0,
          Math.min(
            100,
            (100 * (Date.now() - new Date(r.ventana_inicio).getTime())) /
              Math.max(
                1,
                new Date(r.ventana_fin).getTime() -
                  new Date(r.ventana_inicio).getTime(),
              ),
          ),
        )
      : 0);

  const metricasLabels = Array.from(
    new Set([...Object.keys(predichas), ...Object.keys(observadas)]),
  );

  const serie = (data?.serie_observada ?? []).map((s) => ({
    fecha: (() => {
      try {
        return new Intl.DateTimeFormat("es-MX", {
          day: "numeric",
          month: "short",
        }).format(new Date(s.fecha));
      } catch {
        return s.fecha;
      }
    })(),
    valor: s.valor,
    metrica: s.metrica,
  }));

  const veredicto = data?.veredicto_provisional ?? r.veredicto;

  return (
    <Card
      className="border-sky-500/30 bg-sky-500/[0.02]"
      data-testid={`seguimiento-${r.id}`}
    >
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Activity className="h-4 w-4 text-sky-500" />
              En seguimiento
            </CardTitle>
            <p className="line-clamp-2 text-sm text-muted-foreground">
              {r.accion_texto}
            </p>
          </div>
          {veredicto && (
            <Badge
              variant="outline"
              className={cn("gap-1 text-[11px]", veredictoStyles[veredicto] ?? "")}
            >
              {veredicto === "exitosa" && <CheckCircle2 className="h-3 w-3" />}
              {veredicto === "fallida" && <XCircle className="h-3 w-3" />}
              Veredicto provisional: {veredicto}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Ventana {r.ventana_duracion_dias} días
            </span>
            <span className="tabular-nums font-medium text-foreground">
              {pct.toFixed(0)}%
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-sky-500 transition-all"
              style={{ width: `${pct}%` }}
              data-testid="progress-bar"
            />
          </div>
        </div>

        {metricasLabels.length > 0 && (
          <div className="grid gap-2 sm:grid-cols-2">
            {metricasLabels.map((m) => (
              <div
                key={m}
                className="rounded-md border border-border/70 bg-background/40 p-2 text-xs"
              >
                <div className="mb-1 font-medium uppercase tracking-wider text-muted-foreground">
                  {m}
                </div>
                <div className="flex items-baseline justify-between tabular-nums">
                  <span className="text-foreground">
                    obs:{" "}
                    <strong className="text-sm">
                      {observadas[m] !== undefined ? observadas[m] : "—"}
                    </strong>
                  </span>
                  <span className="text-muted-foreground">
                    pred: {predichas[m] !== undefined ? predichas[m] : "—"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {serie.length > 0 && (
          <div className="h-28" data-testid="seguimiento-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={serie} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="fecha" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "6px",
                    fontSize: 11,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="valor"
                  stroke="hsl(var(--accent))"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {isLoading && serie.length === 0 && (
          <p className="text-xs text-muted-foreground">
            Cargando métricas observadas…
          </p>
        )}
      </CardContent>
    </Card>
  );
}
