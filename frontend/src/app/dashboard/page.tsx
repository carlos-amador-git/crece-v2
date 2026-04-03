"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SentimentLineChart } from "@/components/charts/sentiment-line-chart";
import { EngagementBarChart } from "@/components/charts/engagement-bar-chart";
import { PostCard } from "@/components/social/post-card";
import { useKpiOverview, useTopDirigentes } from "@/lib/api/hooks/use-overview";
import { useSentimentTrend, useSocialPosts } from "@/lib/api/hooks/use-social";
import { formatNumber } from "@/lib/utils";
import {
  Users,
  TrendingUp,
  MessageSquare,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  ArrowRight,
  Clock,
  Activity,
  Cpu,
} from "lucide-react";

const ElectoralMap = dynamic(
  () =>
    import("@/components/maps/electoral-map").then((m) => m.ElectoralMap),
  { ssr: false, loading: () => <Skeleton className="h-[300px] w-full rounded-lg" /> }
);

/* ---- Mock data for development while API is not connected ---- */
const MOCK_KPI = {
  total_dirigentes: 142,
  avg_ipd_score: 6.4,
  posts_monitored_24h: 3847,
  active_alerts: 7,
  dirigentes_change: 5.2,
  ipd_change: 0.3,
  posts_change: 12.1,
  alerts_change: -2,
};

const MOCK_SENTIMENT_TREND = Array.from({ length: 30 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toISOString().slice(0, 10),
    positive: Math.floor(40 + Math.random() * 30),
    negative: Math.floor(10 + Math.random() * 20),
    neutral: Math.floor(20 + Math.random() * 15),
  };
});

const MOCK_TOP_DIRIGENTES = [
  { name: "Ana Martinez", value: 9.2 },
  { name: "Carlos Ruiz", value: 8.7 },
  { name: "Maria Lopez", value: 8.1 },
  { name: "Jose Garcia", value: 7.8 },
  { name: "Laura Sanchez", value: 7.5 },
  { name: "Pedro Hernandez", value: 7.2 },
  { name: "Sofia Torres", value: 6.9 },
  { name: "Roberto Diaz", value: 6.5 },
  { name: "Isabel Morales", value: 6.1 },
  { name: "Miguel Flores", value: 5.8 },
];

const MOCK_POSTS = [
  {
    id: 1,
    dirigente_id: 1,
    dirigente_nombre: "Ana Martinez",
    platform: "twitter" as const,
    content:
      "Hoy visitamos las comunidades rurales del distrito. Escuchamos sus necesidades y comprometimos acciones concretas para mejorar la infraestructura hidrica.",
    url: "https://twitter.com/example/status/1",
    sentiment: "positive" as const,
    sentiment_score: 0.87,
    likes: 1420,
    comments: 89,
    shares: 234,
    views: 45200,
    published_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    collected_at: new Date().toISOString(),
  },
  {
    id: 2,
    dirigente_id: 2,
    dirigente_nombre: "Carlos Ruiz",
    platform: "facebook" as const,
    content:
      "La reforma presupuestal no considera las necesidades reales de los municipios. Exigimos una revision inmediata del proyecto de ley.",
    url: "https://facebook.com/example/posts/2",
    sentiment: "negative" as const,
    sentiment_score: 0.72,
    likes: 890,
    comments: 156,
    shares: 312,
    published_at: new Date(Date.now() - 5 * 3600000).toISOString(),
    collected_at: new Date().toISOString(),
  },
  {
    id: 3,
    dirigente_id: 3,
    dirigente_nombre: "Maria Lopez",
    platform: "instagram" as const,
    content:
      "Inauguracion del nuevo centro comunitario en la colonia San Miguel. Un espacio que la comunidad merecia desde hace anos.",
    url: "https://instagram.com/p/example3",
    sentiment: "positive" as const,
    sentiment_score: 0.91,
    likes: 3200,
    comments: 201,
    shares: 89,
    published_at: new Date(Date.now() - 8 * 3600000).toISOString(),
    collected_at: new Date().toISOString(),
  },
];
/* ---- End mock data ---- */

const TIME_FILTERS = [
  { label: "Hoy", value: "today" },
  { label: "7 dias", value: "7d" },
  { label: "30 dias", value: "30d" },
  { label: "90 dias", value: "90d" },
] as const;

const kpiCards = [
  {
    title: "Total Dirigentes",
    key: "total_dirigentes" as const,
    changeKey: "dirigentes_change" as const,
    icon: Users,
    format: (v: number) => formatNumber(v),
    isAlerts: false,
  },
  {
    title: "Avg IPD Score",
    key: "avg_ipd_score" as const,
    changeKey: "ipd_change" as const,
    icon: TrendingUp,
    format: (v: number) => v.toFixed(1),
    isAlerts: false,
  },
  {
    title: "Posts (24h)",
    key: "posts_monitored_24h" as const,
    changeKey: "posts_change" as const,
    icon: MessageSquare,
    format: (v: number) => formatNumber(v),
    isAlerts: false,
  },
  {
    title: "Alertas Activas",
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
  const [activeFilter, setActiveFilter] = useState<string>("30d");

  const { data: kpi } = useKpiOverview();
  const { data: sentimentData } = useSentimentTrend(30);
  const { data: topDirigentes } = useTopDirigentes(10);
  const { data: postsData } = useSocialPosts({ per_page: 5 });

  // Use real data if available, otherwise fall back to mock
  const kpiData = kpi ?? MOCK_KPI;
  const trendData = sentimentData ?? MOCK_SENTIMENT_TREND;
  const topData =
    topDirigentes?.map((d) => ({ name: d.nombre, value: d.ipd_score })) ??
    MOCK_TOP_DIRIGENTES;
  const posts = postsData?.items ?? MOCK_POSTS;

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

      {/* ── KPI Cards ───────────────────────────────────────── */}
      <section
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Indicadores clave"
      >
        {kpiCards.map((card) => {
          const value = kpiData[card.key];
          const change = kpiData[card.changeKey];
          const isPositive = change >= 0;
          const showPulse = card.isAlerts && hasActiveAlerts;

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
                  <p className="text-sm font-medium text-muted-foreground">
                    {card.title}
                  </p>
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
                  <p
                    className="tabular-nums font-heading text-2xl font-bold"
                    data-numeric="true"
                  >
                    {card.format(value)}
                  </p>
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
          Ultima sincronizacion: <span className="font-medium text-foreground/80">hace 5 min</span>
        </span>
        <span className="flex items-center gap-1.5">
          <Cpu className="h-3 w-3" />
          Workers:
          <span className="font-medium text-foreground/80" data-numeric="true">3/3</span>
          activos
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" aria-label="Workers activos" />
        </span>
        <span className="flex items-center gap-1.5">
          <Activity className="h-3 w-3" />
          Scrapers:
          <span className="font-medium text-foreground/80" data-numeric="true">2</span>
          ejecutando
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" aria-label="Scrapers activos" />
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
            <SentimentLineChart data={trendData} />
          </CardContent>
        </Card>

        {/* Top dirigentes by IPD */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Top Penetracion Digital</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {topData.slice(0, 10).map((item, index) => (
                <div
                  key={item.name}
                  className="flex items-center gap-3"
                >
                  <span
                    className="tabular-nums flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground"
                    data-numeric="true"
                    aria-label={`Posicion ${index + 1}`}
                  >
                    {index + 1}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm">
                    {item.name}
                  </span>
                  <span
                    className="tabular-nums text-sm font-semibold"
                    data-numeric="true"
                  >
                    {item.value.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
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
          {posts.length === 0 ? (
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

        {/* Map preview */}
        <Card className="flex flex-col lg:col-span-2">
          <CardHeader>
            <CardTitle>Mapa Electoral</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-0">
            <div className="h-[300px] overflow-hidden">
              <ElectoralMap className="h-full" />
            </div>
          </CardContent>
          <CardFooter className="justify-end border-t px-6 py-3">
            <Link
              href="/dashboard/mapa"
              className="flex items-center gap-1 text-sm font-medium text-primary transition-colors duration-150 hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              Ver mapa completo
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </CardFooter>
        </Card>
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
