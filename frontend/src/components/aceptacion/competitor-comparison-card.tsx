"use client";

/**
 * War Room Personal · W3
 *
 * Comparativa contextual del dirigente activo contra UN competidor declarado.
 *
 * Por diseño (D-COMPARE-EXTERNAL-METRICS-ONLY-1): comparamos solo métricas
 * EXTERNAS — followers, engagement, posts/mes. El competidor light NO tiene
 * NLP, por eso no se cruzan curvas de % aceptación.
 *
 * Versión MVP: select de competidor + bar chart de last_6_months.
 * Próxima iter: línea cruzada cuando exista `dirigente_metrics_monthly`.
 */

import { useState, useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { Swords, Users, TrendingUp } from "lucide-react";
import {
  useCompetitors,
  useCompetitorDetail,
} from "@/lib/api/hooks/use-competitors";
import { formatNumber } from "@/lib/utils";

interface Props {
  dirigenteId: number;
  dirigenteFollowers: number;
  dirigenteFirstName?: string;
}

const PLATFORM_LABEL: Record<string, string> = {
  FACEBOOK: "FB",
  INSTAGRAM: "IG",
  TWITTER: "X",
  TIKTOK: "TT",
  YOUTUBE: "YT",
};

export function CompetitorComparisonCard({
  dirigenteId,
  dirigenteFollowers,
  dirigenteFirstName,
}: Props) {
  const { data: competitors, isLoading: listLoading } =
    useCompetitors(dirigenteId);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: detail, isLoading: detailLoading } =
    useCompetitorDetail(selectedId);

  // Auto-seleccionar el primero si hay disponibles
  useMemo(() => {
    if (!selectedId && competitors && competitors.length > 0) {
      setSelectedId(competitors[0].id);
    }
  }, [competitors, selectedId]);

  if (listLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-48 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!competitors || competitors.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Swords className="h-4 w-4" /> Comparar con competencia
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Aún no se han declarado competidores para este dirigente.
            <br />
            Contacta a tu administrador para agregarlos.
          </p>
        </CardContent>
      </Card>
    );
  }

  const lastMonth = detail?.last_6_months[0];
  const chartData = (detail?.last_6_months ?? [])
    .slice()
    .reverse()
    .map((m) => ({
      month: m.month_start.slice(0, 7),
      followers: m.followers_total ?? 0,
      engagement: Math.round((m.engagement_rate ?? 0) * 1000) / 10, // % visible
      posts: m.posts_count,
    }));

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Swords className="h-4 w-4" /> Comparar con competencia
            </CardTitle>
            <CardDescription className="mt-1">
              Métricas externas mensuales. Sin análisis NLP — los competidores
              son referentes ligeros.
            </CardDescription>
          </div>
          <Select
            value={selectedId ? String(selectedId) : ""}
            onValueChange={(v) => setSelectedId(Number(v))}
          >
            <SelectTrigger className="w-[260px]">
              <SelectValue placeholder="Selecciona competidor" />
            </SelectTrigger>
            <SelectContent>
              {competitors.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  <span className="flex items-center gap-2">
                    {c.display_name}
                    {c.partido && (
                      <span className="text-[10px] text-muted-foreground">
                        · {c.partido}
                      </span>
                    )}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent>
        {detailLoading ? (
          <Skeleton className="h-56 w-full" />
        ) : !detail ? (
          <p className="text-sm text-muted-foreground">
            Selecciona un competidor para ver su comparativa.
          </p>
        ) : (
          <>
            {/* Header del competidor */}
            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-md border bg-muted/30 p-3">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{detail.display_name}</span>
                  {detail.verified && (
                    <Badge variant="outline" className="border-emerald-500/40 text-emerald-600">
                      verificado
                    </Badge>
                  )}
                  {detail.partido && (
                    <Badge variant="outline">{detail.partido}</Badge>
                  )}
                </div>
                {detail.cargo && (
                  <p className="text-xs text-muted-foreground">{detail.cargo}</p>
                )}
              </div>
              <Badge variant="secondary">
                {PLATFORM_LABEL[detail.platform] ?? detail.platform}
              </Badge>
            </div>

            {/* Side-by-side stats */}
            {(() => {
              const myFirst = dirigenteFirstName ?? "Tú";
              const rivalFirst = detail.display_name.split(" ")[0];
              const rivalFollowers = lastMonth?.followers_total ?? null;
              const delta =
                rivalFollowers != null ? rivalFollowers - dirigenteFollowers : null;
              return (
                <>
                  <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
                    <StatBlock
                      label={myFirst}
                      value={formatNumber(dirigenteFollowers)}
                      icon={<Users className="h-3.5 w-3.5" />}
                      tone="primary"
                    />
                    <StatBlock
                      label={rivalFirst}
                      value={
                        rivalFollowers != null ? formatNumber(rivalFollowers) : "—"
                      }
                      icon={<Users className="h-3.5 w-3.5" />}
                      tone="rival"
                    />
                    <StatBlock
                      label="Interacción último mes"
                      value={
                        lastMonth?.engagement_rate != null
                          ? `${(lastMonth.engagement_rate * 100).toFixed(1)}%`
                          : "—"
                      }
                      icon={<TrendingUp className="h-3.5 w-3.5" />}
                      tone="rival"
                    />
                  </div>
                  {delta != null && (
                    <div
                      className={`mb-5 flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-xs ${
                        delta > 0
                          ? "border-slate-300/60 bg-slate-100/40 text-foreground dark:border-slate-600/50 dark:bg-slate-800/30"
                          : delta < 0
                          ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400"
                          : "border-muted bg-muted/30 text-muted-foreground"
                      }`}
                    >
                      {delta > 0 ? (
                        <>
                          <span className="font-semibold tabular-nums">
                            +{formatNumber(Math.abs(delta))}
                          </span>
                          <span className="text-muted-foreground">
                            followers más que {myFirst}
                          </span>
                        </>
                      ) : delta < 0 ? (
                        <>
                          <span className="font-semibold tabular-nums">
                            +{formatNumber(Math.abs(delta))}
                          </span>
                          <span>followers de ventaja para {myFirst}</span>
                        </>
                      ) : (
                        <span>Mismo número de followers</span>
                      )}
                    </div>
                  )}
                </>
              );
            })()}

            {/* Bar chart histórico competidor */}
            {chartData.length === 0 ? (
              <p className="rounded-md border border-dashed p-4 text-center text-xs text-muted-foreground">
                Sin métricas mensuales del competidor todavía. El scraper light
                las captura una vez al mes.
              </p>
            ) : chartData.length < 2 ? (
              <div className="rounded-md border border-dashed bg-muted/20 p-4 space-y-3">
                <p className="text-center text-xs text-muted-foreground leading-relaxed">
                  Aún no hay tendencia: solo {chartData.length} medición registrada
                  ({chartData[0].month}). El histórico se grafica desde la 2ª
                  medición mensual (scraper corre el 1° de cada mes).
                </p>
                <div className="mx-auto inline-flex flex-col items-center gap-1 rounded-md bg-card px-4 py-2 text-center">
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Followers {chartData[0].month}
                  </span>
                  <span className="font-heading text-2xl font-bold tabular-nums">
                    {formatNumber(chartData[0].followers)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="h-56 w-full">
                <ResponsiveContainer>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "hsl(var(--background))",
                        border: "1px solid hsl(var(--border))",
                        fontSize: 12,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="followers" fill="#64748b" name="Followers" />
                    {/* Posts/mes solo si tenemos data real (competitor_posts vacío
                        hoy → siempre 0). Ocultamos para no engañar. */}
                    {chartData.some((d) => d.posts > 0) && (
                      <Bar dataKey="posts" fill="#0891b2" name="Posts/mes" />
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function StatBlock({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  tone: "primary" | "rival";
}) {
  return (
    <div
      className={`rounded-md border p-3 ${
        tone === "primary"
          ? "border-emerald-500/30 bg-emerald-500/5"
          : "border-slate-400/30 bg-slate-500/5"
      }`}
    >
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="mt-1 font-heading text-xl font-bold tabular-nums">
        {value}
      </div>
    </div>
  );
}
