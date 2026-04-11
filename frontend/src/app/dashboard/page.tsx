"use client";

import { useState } from "react";
// import dynamic from "next/dynamic";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SentimentLineChart } from "@/components/charts/sentiment-line-chart";
import { PostCard } from "@/components/social/post-card";
import { useKpiOverview, useTopDirigentes, useSystemStatus } from "@/lib/api/hooks/use-overview";
import { useSentimentTrend, useSocialPosts } from "@/lib/api/hooks/use-social";
import { formatNumber, formatRelativeTime } from "@/lib/utils";
import { CrisisAlertList } from "@/components/alerts/crisis-alert-list";
import {
  Users,
  TrendingUp,
  MessageSquare,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Activity,
  Cpu,
} from "lucide-react";

// Electoral map hidden until INE shapefiles are loaded
// const ElectoralMap = dynamic(
//   () =>
//     import("@/components/maps/electoral-map").then((m) => m.ElectoralMap),
//   { ssr: false, loading: () => <Skeleton className="h-[300px] w-full rounded-lg" /> }
// );

/* Default values shown while API loads */
const DEFAULT_KPI = {
  total_dirigentes: 0,
  avg_ipd_score: 0,
  posts_monitored_24h: 0,
  active_alerts: 0,
  dirigentes_change: 0,
  ipd_change: 0,
  posts_change: 0,
  alerts_change: 0,
  total_audiencia: 0,
  contactos_periodo: 0,
  tema_urgente: null as string | null,
};

const TIME_FILTERS = [
  { label: "Hoy", value: "today" as const },
  { label: "7 dias", value: "7d" as const },
  { label: "30 dias", value: "30d" as const },
  { label: "90 dias", value: "90d" as const },
];

const kpiCards = [
  {
    title: "Tu Audiencia",
    subtitle: "Personas que te siguen",
    key: "total_audiencia" as const,
    changeKey: "posts_change" as const, // proxy — no history yet
    icon: Users,
    format: (v: number) => formatNumber(v),
    isAlerts: false,
  },
  {
    title: "Presencia Digital",
    subtitle: "Tu IPD sobre 10",
    key: "avg_ipd_score" as const,
    changeKey: "ipd_change" as const,
    icon: TrendingUp,
    format: (v: number) => `${v.toFixed(1)} / 10`,
    isAlerts: false,
  },
  {
    title: "Conversacion",
    subtitle: "Posts monitoreados en el periodo",
    key: "posts_monitored_24h" as const,
    changeKey: "posts_change" as const,
    icon: MessageSquare,
    format: (v: number) => formatNumber(v),
    isAlerts: false,
  },
  {
    title: "Tema Urgente",
    subtitle: "Alerta mas reciente",
    key: "active_alerts" as const,
    changeKey: "alerts_change" as const,
    icon: AlertTriangle,
    format: (v: number) => formatNumber(v),
    isAlerts: true,
  },
];

function CurrentDateTime() {
  const now = new Date();
  const formatted = new Intl.DateTimeFormat("es-MX", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(now);

  return (
    <time
      dateTime={now.toISOString()}
      className="text-sm text-muted-foreground"
    >
      {formatted.charAt(0).toUpperCase() + formatted.slice(1)}
    </time>
  );
}

export default function OverviewPage() {
  const [activeFilter, setActiveFilter] = useState<"today" | "7d" | "30d" | "90d">("30d");

  const { data: kpi, isLoading: kpiLoading } = useKpiOverview(activeFilter);
  const { data: topDirigentes, isLoading: topLoading } = useTopDirigentes(10);
  const { data: postsData, isLoading: postsLoading } = useSocialPosts({ per_page: 5 });
  const { data: systemStatus } = useSystemStatus();

  // Use first dirigente's ID for sentiment trend (backend requires dirigente_id)
  const firstDirigenteId = topDirigentes?.[0]?.id;
  const { data: sentimentData, isLoading: sentimentLoading } = useSentimentTrend(30, firstDirigenteId);

  const kpiData = kpi ?? DEFAULT_KPI;
  const trendData = sentimentData ?? [];
  const posts = postsData?.items ?? [];

  // Aggregate followers by platform across all visible dirigentes
  const platformColors: Record<string, string> = {
    Twitter: "#1DA1F2",
    Instagram: "#E4405F",
    Facebook: "#1877F2",
    TikTok: "#000000",
    YouTube: "#FF0000",
    Bluesky: "#0085FF",
  };
  const platformData = (() => {
    const map: Record<string, number> = {};
    for (const d of topDirigentes ?? []) {
      for (const p of (d as any).social_profiles ?? []) {
        const raw = (p.platform ?? "").toLowerCase();
        const label = raw.charAt(0).toUpperCase() + raw.slice(1);
        map[label] = (map[label] ?? 0) + (p.followers_count ?? p.followers ?? 0);
      }
    }
    return Object.entries(map)
      .map(([name, value]) => ({ name, value, fill: platformColors[name] ?? "hsl(var(--chart-accent))" }))
      .sort((a, b) => b.value - a.value);
  })();

  const hasActiveAlerts = kpiData.active_alerts > 0;

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────── */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-balance">
            Dashboard
          </h1>
          <CurrentDateTime />
        </div>

        <nav aria-label="Filtros de periodo" className="flex gap-2">
          {TIME_FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              onClick={() => setActiveFilter(filter.value)}
              aria-pressed={activeFilter === filter.value}
              className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                activeFilter === filter.value
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              }`}
            >
              {filter.label}
            </button>
          ))}
        </nav>
      </header>

      {/* ── Crisis Alerts ──────────────────────────────────── */}
      {hasActiveAlerts && <CrisisAlertList limit={3} />}

      {/* ── KPI Cards ───────────────────────────────────────── */}
      <section
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Indicadores clave"
      >
        {kpiLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="card-elevated">
                <CardContent className="p-5">
                  <Skeleton className="h-4 w-24 mb-3" />
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))
          : kpiCards.map((card) => {
              const rawValue = kpiData[card.key];
              const change = kpiData[card.changeKey];
              const isPositive = change >= 0;
              const showPulse = card.isAlerts && hasActiveAlerts;

              // Special rendering for "Tema Urgente" — show the alert text
              const isTemaCard = card.key === "active_alerts";
              const temaText = kpiData.tema_urgente;

              return (
                <Card
                  key={card.key}
                  className={`card-elevated ${
                    card.isAlerts ? "accent-bar-left" : ""
                  }`}
                  data-active={card.isAlerts && hasActiveAlerts ? "true" : undefined}
                >
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">
                          {card.title}
                        </p>
                        {card.subtitle && (
                          <p className="text-xs text-muted-foreground/70">
                            {card.subtitle}
                          </p>
                        )}
                      </div>
                      <div className="relative">
                        <card.icon className="h-4.5 w-4.5 text-muted-foreground" />
                        {showPulse && (
                          <span
                            className="absolute -right-0.5 -top-0.5 block h-2 w-2 rounded-full bg-red-500 pulse-dot"
                            aria-hidden="true"
                          />
                        )}
                      </div>
                    </div>
                    <div className="mt-2 flex items-end justify-between">
                      {isTemaCard ? (
                        <p
                          className={`line-clamp-2 text-sm font-semibold ${
                            temaText ? "text-foreground" : "text-muted-foreground"
                          }`}
                          title={temaText ?? undefined}
                        >
                          {temaText ?? "Sin alertas en el periodo"}
                        </p>
                      ) : (
                        <p
                          className="tabular-nums font-heading text-2xl font-bold"
                          data-numeric="true"
                        >
                          {card.format(Number(rawValue))}
                        </p>
                      )}
                      {!isTemaCard && (
                        <span
                          className={`flex items-center text-xs font-medium ${
                            isPositive
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "text-red-600 dark:text-red-400"
                          }`}
                        >
                          {isPositive ? (
                            <ArrowUpRight className="mr-0.5 h-3.5 w-3.5" />
                          ) : (
                            <ArrowDownRight className="mr-0.5 h-3.5 w-3.5" />
                          )}
                          <span data-numeric="true" className="tabular-nums">
                            {Math.abs(change)}%
                          </span>
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
      </section>

      {/* ── Quick Status Bar ────────────────────────────────── */}
      <div
        className="flex flex-wrap items-center gap-x-6 gap-y-1 rounded-md border border-border/50 bg-muted/30 px-4 py-2 text-xs text-muted-foreground"
        role="status"
        aria-label="Estado del sistema"
      >
        <span className="flex items-center gap-1.5">
          <Clock className="h-3 w-3" />
          Ultima sincronizacion:{" "}
          <span className="font-medium text-foreground/80">
            {systemStatus?.last_sync
              ? formatRelativeTime(systemStatus.last_sync)
              : "---"}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <Cpu className="h-3 w-3" />
          Workers:
          <span className="font-medium text-foreground/80" data-numeric="true">
            {systemStatus
              ? `${systemStatus.workers_active}/${systemStatus.workers_total}`
              : "---"}
          </span>
          activos
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              systemStatus && systemStatus.workers_active > 0
                ? "bg-emerald-500"
                : "bg-muted-foreground/30"
            }`}
            aria-label={
              systemStatus && systemStatus.workers_active > 0
                ? "Workers activos"
                : "Workers inactivos"
            }
          />
        </span>
        <span className="flex items-center gap-1.5">
          <Activity className="h-3 w-3" />
          Scrapers:
          <span className="font-medium text-foreground/80" data-numeric="true">
            {systemStatus?.scrapers_running ?? "---"}
          </span>
          ejecutando
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              systemStatus && systemStatus.scrapers_running > 0
                ? "bg-emerald-500"
                : "bg-muted-foreground/30"
            }`}
            aria-label={
              systemStatus && systemStatus.scrapers_running > 0
                ? "Scrapers activos"
                : "Scrapers inactivos"
            }
          />
        </span>
      </div>

      {/* ── Charts Row ──────────────────────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Sentiment trend -- larger */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Tendencia de Sentimiento</CardTitle>
            <CardDescription>Ultimos 30 dias</CardDescription>
          </CardHeader>
          <CardContent>
            {sentimentLoading ? (
              <Skeleton className="h-[300px] w-full" />
            ) : trendData.length === 0 ? (
              <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                Sin datos de sentimiento disponibles
              </div>
            ) : (
              <SentimentLineChart data={trendData} />
            )}
          </CardContent>
        </Card>

        {/* Followers by platform */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Seguidores por Plataforma</CardTitle>
            <CardDescription>Audiencia total por red social</CardDescription>
          </CardHeader>
          <CardContent>
            {topLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : platformData.length === 0 ? (
              <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
                Sin perfiles sociales
              </div>
            ) : (
              <div className="space-y-3">
                {platformData.map((p) => {
                  const max = platformData[0]?.value || 1;
                  const pct = Math.max((p.value / max) * 100, 4);
                  return (
                    <div key={p.name} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{p.name}</span>
                        <span className="tabular-nums text-muted-foreground" data-numeric="true">
                          {formatNumber(p.value)}
                        </span>
                      </div>
                      <div className="h-2.5 w-full rounded-full bg-muted">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${pct}%`, backgroundColor: p.fill }}
                        />
                      </div>
                    </div>
                  );
                })}
                <div className="mt-2 pt-2 border-t flex items-center justify-between text-sm">
                  <span className="font-medium text-muted-foreground">Total</span>
                  <span className="tabular-nums font-bold" data-numeric="true">
                    {formatNumber(platformData.reduce((s, p) => s + p.value, 0))}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Bottom Row: Posts + Map ─────────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Recent posts */}
        <section className="space-y-3 lg:col-span-3" aria-label="Publicaciones recientes">
          <h2 className="font-heading text-lg font-semibold">
            Publicaciones Recientes
          </h2>
          {postsLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full rounded-lg" />
            ))
          ) : posts.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <MessageSquare className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No hay publicaciones recientes
                </p>
              </CardContent>
            </Card>
          ) : (
            posts.map((post) => <PostCard key={post.id} post={post} />)
          )}
        </section>

        {/* Map preview — hidden until INE shapefiles loaded */}
      </div>

      {/* ── Pulse dot animation (CSS-only, respects reduced-motion) ── */}
      <style jsx>{`
        .pulse-dot {
          animation: pulse-ring 2s ease-in-out infinite;
        }
        @keyframes pulse-ring {
          0%, 100% {
            opacity: 1;
            box-shadow: 0 0 0 0 rgb(239 68 68 / 0.5);
          }
          50% {
            opacity: 0.8;
            box-shadow: 0 0 0 4px rgb(239 68 68 / 0);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .pulse-dot {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}
