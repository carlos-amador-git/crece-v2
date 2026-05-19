"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useAceptacionOverview } from "@/lib/api/hooks/use-aceptacion";
import { useIADirigenteSummary } from "@/lib/api/hooks/use-indice-aceptacion";
import { CompetitorComparisonCard } from "@/components/aceptacion/competitor-comparison-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber } from "@/lib/utils";
import {
  ArrowLeft,
  CheckCircle2,
  Ghost,
  MessageSquare,
  Share2,
  Users,
  XCircle,
} from "lucide-react";

export default function AceptacionDirigentePage() {
  const params = useParams();
  const id = parseInt(params.dirigente_id as string, 10);

  const { data: overview, isLoading: overviewLoading } = useAceptacionOverview();
  const { data: summary, isLoading: summaryLoading } = useIADirigenteSummary(id);

  const row = overview?.dirigentes.find((d) => d.dirigente_id === id);
  const isLoading = overviewLoading || summaryLoading;

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-12 w-72" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!row) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            Dirigente no encontrado.{" "}
            <Link href="/dashboard/aceptacion" className="underline">
              Volver al resumen
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link href="/dashboard/aceptacion">
          <Button variant="ghost" size="sm" className="mt-1 gap-1">
            <ArrowLeft className="h-4 w-4" /> Resumen
          </Button>
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-2xl font-bold tracking-tight">
              {row.full_name}
            </h1>
            {row.rol_politico && (
              <Badge
                variant="outline"
                className={
                  row.rol_politico === "oposicion"
                    ? "border-amber-500/40 text-amber-500"
                    : "border-emerald-500/40 text-emerald-500"
                }
              >
                {row.rol_politico === "oficialismo" ? "Gobierno" : row.rol_politico}
              </Badge>
            )}
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Índice de Aceptación — vista detallada
          </p>
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KPICard
          icon={<Users className="h-4 w-4" />}
          label="Activación"
          value={`${row.pct_activados.toFixed(2)}%`}
          sub={`${formatNumber(row.unique_commenters)} / ${formatNumber(row.total_followers)}`}
          tone="info"
        />
        <KPICard
          icon={<Ghost className="h-4 w-4" />}
          label="Fantasmas"
          value={`${row.pct_fantasma.toFixed(2)}%`}
          sub="Followers sin señal"
          tone={row.pct_fantasma > 99 ? "danger" : row.pct_fantasma > 95 ? "warn" : "ok"}
        />
        <KPICard
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="Aprobación"
          value={`${row.pct_aprobacion.toFixed(1)}%`}
          sub={`${formatNumber(row.total_comments)} comments`}
          tone="ok"
        />
        <KPICard
          icon={<XCircle className="h-4 w-4" />}
          label="Rechazo"
          value={`${row.pct_rechazo.toFixed(1)}%`}
          sub="Polaridad −1"
          tone="danger"
        />
      </div>

      {/* Audiencia / Fantasmas detail */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Ghost className="h-4 w-4" /> Análisis de audiencia
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-3 text-center">
            <div>
              <div className="font-heading text-3xl font-bold tabular-nums">
                {formatNumber(row.total_followers)}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">Total followers</div>
            </div>
            <div>
              <div className="font-heading text-3xl font-bold tabular-nums text-emerald-400">
                {formatNumber(row.unique_commenters)}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">Comentaristas únicos</div>
            </div>
            <div>
              <div
                className={`font-heading text-3xl font-bold tabular-nums ${
                  row.pct_fantasma > 99
                    ? "text-rose-400"
                    : row.pct_fantasma > 95
                      ? "text-amber-400"
                      : "text-emerald-400"
                }`}
              >
                {formatNumber(row.total_followers - row.unique_commenters)}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                Fantasmas ({row.pct_fantasma.toFixed(1)}%)
              </div>
            </div>
          </div>
          <div className="mt-5 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-emerald-500 transition-all"
              style={{ width: `${Math.min(100, row.pct_activados)}%` }}
            />
          </div>
          <div className="mt-1.5 flex justify-between text-xs text-muted-foreground">
            <span>Activados {row.pct_activados.toFixed(2)}%</span>
            <span>Fantasmas {row.pct_fantasma.toFixed(2)}%</span>
          </div>
        </CardContent>
      </Card>

      {/* Top aprobación */}
      {summary && summary.top_aprobacion.length > 0 && (
        <div>
          <h2 className="mb-3 font-heading text-lg font-semibold">
            Publicaciones mejor recibidas
          </h2>
          <div className="space-y-2">
            {summary.top_aprobacion.map((p) => (
              <Card key={p.post_id}>
                <CardContent className="flex items-start gap-3 p-4">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 text-sm text-foreground/90">{p.snippet}</p>
                    <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                      <span className="font-medium text-emerald-400">
                        {p.aprobacion_pct}% aprobación
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" /> {p.n_comments}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Top rechazo */}
      {summary && summary.top_rechazo.length > 0 && (
        <div>
          <h2 className="mb-3 font-heading text-lg font-semibold">
            Publicaciones con mayor rechazo
          </h2>
          <div className="space-y-2">
            {summary.top_rechazo.map((p) => (
              <Card key={p.post_id}>
                <CardContent className="flex items-start gap-3 p-4">
                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 text-sm text-foreground/90">{p.snippet}</p>
                    <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                      <span className="font-medium text-rose-400">
                        {p.rechazo_pct}% rechazo
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" /> {p.n_comments}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Expansión */}
      {summary && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-4 p-4">
            <Share2 className="h-5 w-5 text-muted-foreground" />
            <div>
              <div className="text-sm font-medium">Expansión promedio</div>
              <div className="text-xs text-muted-foreground">
                Ratio likes/shares en comments vs total interactions
              </div>
            </div>
            <div className="ml-auto font-heading text-2xl font-bold tabular-nums">
              {summary.expansion_promedio.toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comparativa con competidor (war-room-personal · W3) */}
      <CompetitorComparisonCard
        dirigenteId={id}
        dirigenteFollowers={row.total_followers}
        dirigenteFirstName={row.full_name?.split(" ")[0]}
      />
    </div>
  );
}

function KPICard({
  icon,
  label,
  value,
  sub,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
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
        <div className="mt-2 font-heading text-2xl font-bold tabular-nums">{value}</div>
        <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>
      </CardContent>
    </Card>
  );
}
