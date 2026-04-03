"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

const kpiCards = [
  {
    title: "Total Dirigentes",
    key: "total_dirigentes" as const,
    changeKey: "dirigentes_change" as const,
    icon: Users,
    format: (v: number) => formatNumber(v),
  },
  {
    title: "Avg IPD Score",
    key: "avg_ipd_score" as const,
    changeKey: "ipd_change" as const,
    icon: TrendingUp,
    format: (v: number) => v.toFixed(1),
  },
  {
    title: "Posts (24h)",
    key: "posts_monitored_24h" as const,
    changeKey: "posts_change" as const,
    icon: MessageSquare,
    format: (v: number) => formatNumber(v),
  },
  {
    title: "Alertas Activas",
    key: "active_alerts" as const,
    changeKey: "alerts_change" as const,
    icon: AlertTriangle,
    format: (v: number) => formatNumber(v),
  },
];

export default function OverviewPage() {
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Resumen de actividad politica digital
        </p>
      </div>

      {/* KPI Cards */}
      <section
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Indicadores clave"
      >
        {kpiCards.map((card) => {
          const value = kpiData[card.key];
          const change = kpiData[card.changeKey];
          const isPositive = change >= 0;

          return (
            <Card key={card.key}>
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    {card.title}
                  </p>
                  <card.icon className="h-4.5 w-4.5 text-muted-foreground" />
                </div>
                <div className="mt-2 flex items-end justify-between">
                  <p className="font-heading text-2xl font-bold">
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
                    {Math.abs(change)}%
                  </span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </section>

      {/* Charts row */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Sentiment trend — larger */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Tendencia de Sentimiento</CardTitle>
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
            <EngagementBarChart data={topData} layout="vertical" />
          </CardContent>
        </Card>
      </div>

      {/* Bottom row: posts + map preview */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Recent posts */}
        <div className="space-y-3 lg:col-span-3">
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
        </div>

        {/* Map preview */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Mapa Electoral</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-[300px] overflow-hidden rounded-b-lg">
              <ElectoralMap className="h-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
