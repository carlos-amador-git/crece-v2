"use client";

import { useAceptacionOverview } from "@/lib/api/hooks/use-aceptacion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { IASummaryCard } from "@/components/dashboard/ia-summary-card";
import { formatNumber } from "@/lib/utils";
import { Gauge, Users, Ghost, TrendingUp, TrendingDown, CircleDot } from "lucide-react";

export default function AceptacionPage() {
  const { data, isLoading, error } = useAceptacionOverview();

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-24" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No se pudo cargar el Índice de Aceptación.
          </CardContent>
        </Card>
      </div>
    );
  }

  const rows = data.dirigentes;
  const totalFollowers = rows.reduce((s, r) => s + r.total_followers, 0);
  const totalCommenters = rows.reduce((s, r) => s + r.unique_commenters, 0);
  const avgActivacion =
    totalFollowers > 0 ? (100 * totalCommenters) / totalFollowers : 0;
  const avgFantasma = 100 - avgActivacion;
  const avgAprobacion =
    rows.length > 0
      ? rows.reduce((s, r) => s + r.pct_aprobacion, 0) / rows.length
      : 0;
  const avgRechazo =
    rows.length > 0
      ? rows.reduce((s, r) => s + r.pct_rechazo, 0) / rows.length
      : 0;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Gauge className="h-6 w-6 text-accent" />
          <h1 className="font-heading text-2xl font-bold tracking-tight">
            Índice de Aceptación
          </h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          4 capas: activación, expansión, aceptación y fantasmas — sobre corpus
          de {formatNumber(data.total_corpus_comments)} comentarios clasificados
          con matriz v2 (53 reglas).
        </p>
      </div>

      {/* KPI cards — 4 capas */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          icon={<Users className="h-4 w-4" />}
          label="Activación promedio"
          value={`${avgActivacion.toFixed(2)}%`}
          subtitle={`${formatNumber(totalCommenters)} únicos / ${formatNumber(
            totalFollowers,
          )} followers`}
          tone="info"
        />
        <KPICard
          icon={<Ghost className="h-4 w-4" />}
          label="Fantasmas"
          value={`${avgFantasma.toFixed(2)}%`}
          subtitle="Followers sin señales de vida"
          tone={avgFantasma > 98 ? "danger" : avgFantasma > 95 ? "warn" : "ok"}
        />
        <KPICard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Aprobación promedio"
          value={`${avgAprobacion.toFixed(1)}%`}
          subtitle="Comments con polaridad +1"
          tone="ok"
        />
        <KPICard
          icon={<TrendingDown className="h-4 w-4" />}
          label="Rechazo promedio"
          value={`${avgRechazo.toFixed(1)}%`}
          subtitle="Comments con polaridad -1"
          tone="danger"
        />
      </div>

      {/* Grid por dirigente */}
      <div>
        <h2 className="mb-3 font-heading text-lg font-semibold">
          Resumen por dirigente
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((d) => (
            <IASummaryCard key={d.dirigente_id} dirigenteId={d.dirigente_id} />
          ))}
        </div>
      </div>

      {/* Tabla fantasmas */}
      <div>
        <h2 className="mb-3 font-heading text-lg font-semibold">
          Detalle por dirigente
        </h2>
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Dirigente</th>
                    <th className="px-4 py-2 text-left font-medium">Rol</th>
                    <th className="px-4 py-2 text-right font-medium">Followers</th>
                    <th className="px-4 py-2 text-right font-medium">Comentaristas</th>
                    <th className="px-4 py-2 text-right font-medium">Comments</th>
                    <th className="px-4 py-2 text-right font-medium">Activ. %</th>
                    <th className="px-4 py-2 text-right font-medium">Fantasma %</th>
                    <th className="px-4 py-2 text-right font-medium">Aprob. %</th>
                    <th className="px-4 py-2 text-right font-medium">Rech. %</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((d) => (
                    <tr key={d.dirigente_id} className="border-b last:border-0">
                      <td className="px-4 py-3 font-medium">{d.full_name}</td>
                      <td className="px-4 py-3">
                        {d.rol_politico ? (
                          <Badge
                            variant="outline"
                            className={
                              d.rol_politico === "oposicion"
                                ? "border-amber-500/40 text-amber-500"
                                : "border-emerald-500/40 text-emerald-500"
                            }
                          >
                            {d.rol_politico}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(d.total_followers)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(d.unique_commenters)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(d.total_comments)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums font-medium">
                        {d.pct_activados.toFixed(2)}%
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        <span
                          className={
                            d.pct_fantasma > 99
                              ? "text-rose-500"
                              : d.pct_fantasma > 95
                                ? "text-amber-500"
                                : "text-emerald-500"
                          }
                        >
                          {d.pct_fantasma.toFixed(2)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-emerald-500">
                        {d.pct_aprobacion.toFixed(1)}%
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-rose-500">
                        {d.pct_rechazo.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Metodología */}
      <Card className="border-dashed">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <CircleDot className="h-4 w-4" />
            Metodología
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          {data.metodologia}
        </CardContent>
      </Card>
    </div>
  );
}

function KPICard({
  icon,
  label,
  value,
  subtitle,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  subtitle: string;
  tone: "ok" | "warn" | "danger" | "info";
}) {
  const toneBg = {
    ok: "bg-emerald-500/10 text-emerald-500",
    warn: "bg-amber-500/10 text-amber-500",
    danger: "bg-rose-500/10 text-rose-500",
    info: "bg-blue-500/10 text-blue-500",
  }[tone];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </span>
          <span className={`rounded-md p-1.5 ${toneBg}`}>{icon}</span>
        </div>
        <div className="mt-2 font-heading text-2xl font-bold tabular-nums">
          {value}
        </div>
        <div className="mt-0.5 text-xs text-muted-foreground">{subtitle}</div>
      </CardContent>
    </Card>
  );
}
