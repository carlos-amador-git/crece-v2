"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
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
import { FadeUp } from "@/components/motion/fade-up";
import { CompetitorSnapshotCard } from "@/components/dashboard/competitor-snapshot-card";
import { rolFromPartido, disclaimerSentimientoCrudo } from "@/lib/politica/rol";

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
  dirigentes_change: null as number | null,
  ipd_change: null as number | null,
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
  const router = useRouter();
  const { user } = useAuth();
  const [activeFilter, setActiveFilter] = useState<"today" | "7d" | "30d" | "90d">("30d");
  const [platformFilter, setPlatformFilter] = useState<"" | "twitter" | "instagram" | "facebook" | "tiktok" | "youtube">("");
  const [includeRts, setIncludeRts] = useState(false);

  useEffect(() => {
    if (user?.role === "admin") {
      router.replace("/dashboard/admin/overview");
    }
  }, [user, router]);

  const { data: kpi, isLoading: kpiLoading } = useKpiOverview(activeFilter);
  const { data: topDirigentes, isLoading: topLoading } = useTopDirigentes(10);
  const { data: postsData, isLoading: postsLoading } = useSocialPosts({ per_page: 5 });
  const { data: systemStatus } = useSystemStatus();

  // Use first dirigente's ID for sentiment trend (backend requires dirigente_id)
  const firstDirigenteId = topDirigentes?.[0]?.id;
  const filterDays: Record<typeof activeFilter, number> = { today: 1, "7d": 7, "30d": 30, "90d": 90 };
  const { data: sentimentData, isLoading: sentimentLoading } = useSentimentTrend(
    filterDays[activeFilter],
    firstDirigenteId,
    { platform: platformFilter || undefined, includeRts },
  );

  const kpiData = kpi ?? DEFAULT_KPI;
  const trendData = sentimentData ?? [];
  const posts = postsData?.items ?? [];

  // Aggregate followers by platform across all visible dirigentes
  const PLATFORM_LABELS: Record<string, string> = {
    twitter: "Twitter", x: "Twitter",
    instagram: "Instagram",
    facebook: "Facebook",
    tiktok: "TikTok",
    youtube: "YouTube",
    bluesky: "Bluesky",
  };
  const platformColors: Record<string, string> = {
    Twitter: "#1DA1F2",
    Instagram: "#E4405F",
    Facebook: "#1877F2",
    TikTok: "#010101",
    YouTube: "#FF0000",
    Bluesky: "#0085FF",
  };
  const platformData = (() => {
    const map: Record<string, number> = {};
    for (const d of topDirigentes ?? []) {
      for (const p of (d as any).social_profiles ?? []) {
        const raw = (p.platform ?? "").toLowerCase();
        const label = PLATFORM_LABELS[raw] ?? (raw.charAt(0).toUpperCase() + raw.slice(1));
        map[label] = (map[label] ?? 0) + (p.followers_count ?? p.followers ?? 0);
      }
    }
    return Object.entries(map)
      .map(([name, value]) => ({ name, value, fill: platformColors[name] ?? "hsl(var(--chart-accent))" }))
      .sort((a, b) => b.value - a.value);
  })();

  const hasActiveAlerts = kpiData.active_alerts > 0;

  // Disclaimer role-aware · interim mientras el motor §9.8 conecta afiliación al sentimiento
  // Ver .context/BLOCKERS.md B-23-03
  const primaryDirigente = topDirigentes?.[0];
  const rolInferido = rolFromPartido(primaryDirigente?.partido);
  const sentimientoDisclaimer = disclaimerSentimientoCrudo(rolInferido);

  return (
    <div className="space-y-6 w-full min-w-0">
      {/* ── Header ──────────────────────────────────────────── */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-balance">
            Dashboard
          </h1>
          <CurrentDateTime />
          <a
            href="/dashboard/settings/analisis-politico"
            className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700 hover:bg-emerald-100 dark:border-emerald-900 dark:bg-emerald-900/20 dark:text-emerald-400"
            title="Tu análisis es deliberado por 3 IAs y revisado por MD Consultoría"
          >
            <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Analisis Contextual · 3 IAs deliberaron
          </a>
        </div>

        <nav aria-label="Filtros de periodo" className="flex flex-wrap gap-2">
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

      {/* ── KPI Cards — BentoGrid ─────────────────────────────── */}
      <section
        className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 w-full min-w-0"
        aria-label="Indicadores clave"
      >
        {kpiLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="card-elevated bento-enter">
                <CardContent className="p-6">
                  <Skeleton className="h-4 w-24 mb-3" />
                  <Skeleton className={i < 2 ? "h-10 w-20" : "h-8 w-16"} />
                </CardContent>
              </Card>
            ))
          : kpiCards.map((card, idx) => {
              const rawValue = kpiData[card.key];
              const change = kpiData[card.changeKey];
              const hasChange = change !== null && change !== undefined;
              const isPositive = hasChange && (change as number) >= 0;
              const showPulse = card.isAlerts && hasActiveAlerts;
              const isHero = idx < 2;

              // Special rendering for "Tema Urgente" — show the alert text
              const isTemaCard = card.key === "active_alerts";
              const temaText = kpiData.tema_urgente;

              return (
                <FadeUp key={card.key} index={idx}>
                <Card
                  className={`card-elevated ${card.isAlerts ? "accent-bar-left" : ""}`}
                  data-active={card.isAlerts && hasActiveAlerts ? "true" : undefined}
                >
                  <CardContent className={isHero ? "p-6" : "p-6"}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className={`font-medium text-muted-foreground ${isHero ? "text-sm" : "text-sm"}`}>
                          {card.title}
                        </p>
                        {card.subtitle && (
                          <p className="text-xs text-muted-foreground/70">
                            {card.subtitle}
                          </p>
                        )}
                      </div>
                      <div className="relative">
                        <card.icon className={`text-muted-foreground ${isHero ? "h-5 w-5" : "h-4.5 w-4.5"}`} />
                        {showPulse && (
                          <span
                            className="absolute -right-0.5 -top-0.5 block h-2 w-2 rounded-full bg-red-500 pulse-dot"
                            aria-hidden="true"
                          />
                        )}
                      </div>
                    </div>
                    <div className={`flex items-end justify-between ${isHero ? "mt-4" : "mt-2"}`}>
                      {isTemaCard ? (
                        <div className="min-w-0 flex-1 space-y-1.5">
                          <p
                            className={`line-clamp-2 text-sm font-semibold ${
                              temaText ? "text-foreground" : "text-muted-foreground"
                            }`}
                            title={temaText ?? undefined}
                          >
                            {temaText ?? "Sin alertas en el periodo"}
                          </p>
                          {temaText && (
                            <p
                              className="rounded-sm border border-amber-300/40 bg-amber-50/70 px-1.5 py-1 text-[10px] leading-tight text-amber-900 dark:border-amber-800/60 dark:bg-amber-900/20 dark:text-amber-200"
                              title={sentimientoDisclaimer}
                            >
                              <span className="font-semibold">Sentimiento crudo.</span>{" "}
                              {rolInferido === "oposicion"
                                ? "Tu rol es oposición — críticas al gobierno pueden leerse como positivas para tu narrativa."
                                : rolInferido === "oficialismo"
                                  ? "Tu rol es oficialismo — críticas al gobierno aquí son riesgo real."
                                  : "Rol independiente — signo refleja tono literal."}
                            </p>
                          )}
                        </div>
                      ) : (
                        <p
                          className={`tabular-nums font-heading font-bold ${isHero ? "text-3xl" : "text-2xl"}`}
                          data-numeric="true"
                        >
                          {card.format(Number(rawValue))}
                        </p>
                      )}
                      {!isTemaCard && (
                        hasChange ? (
                          <span
                            className={`flex items-center text-xs font-medium ${
                              isPositive
                                ? "text-emerald-600 dark:text-emerald-400"
                                : "text-red-600 dark:text-red-400"
                            }`}
                            aria-label={`${isPositive ? "Aumento" : "Disminucion"} de ${Math.abs(change as number)} por ciento`}
                          >
                            {isPositive ? (
                              <ArrowUpRight className="mr-0.5 h-3.5 w-3.5" aria-hidden="true" />
                            ) : (
                              <ArrowDownRight className="mr-0.5 h-3.5 w-3.5" aria-hidden="true" />
                            )}
                            <span data-numeric="true" className="tabular-nums">
                              {Math.abs(change as number)}%
                            </span>
                          </span>
                        ) : (
                          <span
                            className="text-xs font-medium text-muted-foreground/60 tabular-nums"
                            title="Sin histórico suficiente para calcular delta"
                            aria-label="Sin cambio disponible"
                          >
                            —
                          </span>
                        )
                      )}
                    </div>
                  </CardContent>
                </Card>
                </FadeUp>
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

      {/* ── Alerts + Seguidores por Plataforma ─────────────── */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-5 w-full min-w-0">
        {/* Crisis Alerts — compact column */}
        <div className="md:col-span-2 lg:col-span-3 space-y-2">
          {hasActiveAlerts && (
            <p
              className="rounded-sm border border-amber-300/40 bg-amber-50/70 px-2 py-1 text-[10px] leading-tight text-amber-900 dark:border-amber-800/60 dark:bg-amber-900/20 dark:text-amber-200"
              role="note"
              aria-label="Disclaimer sobre signo de sentimiento"
            >
              <span className="font-semibold">Sentimiento crudo ·</span> {sentimientoDisclaimer}
            </p>
          )}
          {hasActiveAlerts ? (
            <CrisisAlertList limit={3} compact />
          ) : (
            <div className="flex h-full min-h-[80px] items-center justify-center rounded-lg border border-dashed border-border/50 text-sm text-muted-foreground">
              Sin alertas activas
            </div>
          )}
        </div>

        {/* Followers by platform */}
        <Card className="md:col-span-2 lg:col-span-2">
          <CardHeader className="pb-3">
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

      {/* ── Charts Row ──────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Tono Discursivo</CardTitle>
              <CardDescription>
                Clasificación del contenido publicado · últimos 30 días{includeRts ? "" : " · sin RTs"} · &gt;20 chars
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="sr-only">Filtrar por red social</span>
                <select
                  value={platformFilter}
                  onChange={(e) => setPlatformFilter(e.target.value as typeof platformFilter)}
                  className="h-7 rounded-md border border-border bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label="Red social"
                >
                  <option value="">Todas las redes</option>
                  <option value="twitter">Twitter/X</option>
                  <option value="instagram">Instagram</option>
                  <option value="facebook">Facebook</option>
                  <option value="tiktok">TikTok</option>
                  <option value="youtube">YouTube</option>
                </select>
              </label>
              <button
                type="button"
                onClick={() => setIncludeRts((v) => !v)}
                aria-pressed={includeRts}
                className={`h-7 rounded-md border px-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  includeRts
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-background text-muted-foreground hover:text-foreground"
                }`}
                title="Incluir retweets en el análisis"
              >
                RT
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {sentimentLoading ? (
            <Skeleton className="h-[300px] w-full" aria-label="Cargando datos de sentimiento" />
          ) : trendData.length === 0 ? (
            <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground" role="status">
              Sin datos de sentimiento disponibles
            </div>
          ) : (
            <SentimentLineChart data={trendData} />
          )}
        </CardContent>
      </Card>

      {/* ── Competitor Snapshot ──────────────────────────────── */}
      <FadeUp index={0}>
        <CompetitorSnapshotCard />
      </FadeUp>

      {/* ── Bottom Row: Posts ───────────────────────────────── */}
      <section className="space-y-3" aria-label="Publicaciones recientes">
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
