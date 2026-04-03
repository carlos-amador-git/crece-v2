"use client";

import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useDirigente } from "@/lib/api/hooks/use-dirigentes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ProfileHeader } from "@/components/dirigentes/profile-header";
import { IpdRadarChart } from "@/components/charts/ipd-radar-chart";
import { SentimentLineChart } from "@/components/charts/sentiment-line-chart";
import { EngagementBarChart } from "@/components/charts/engagement-bar-chart";
import { PostCard } from "@/components/social/post-card";
import { SentimentBadge } from "@/components/social/sentiment-badge";
import { formatNumber, formatDate } from "@/lib/utils";
import type { DirigenteDetail, SocialPost, SentimentTrend } from "@/lib/api/types";
import { ArrowLeft, TrendingUp, MessageSquare, Users, Brain } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const ElectoralMap = dynamic(
  () => import("@/components/maps/electoral-map").then((m) => m.ElectoralMap),
  { ssr: false, loading: () => <Skeleton className="h-[400px] w-full rounded-lg" /> }
);

/* ---- Mock data for development ---- */
const MOCK_DIRIGENTE: DirigenteDetail = {
  id: 1,
  nombre: "Ana",
  apellido_paterno: "Martinez",
  apellido_materno: "Vega",
  cargo: "Diputada Federal",
  partido: "MORENA",
  estado: "CDMX",
  municipio: "Coyoacan",
  avatar_url: undefined,
  ipd_score: 9.2,
  platforms: ["twitter", "instagram", "facebook"],
  last_activity: new Date(Date.now() - 1800000).toISOString(),
  created_at: "2024-01-15",
  updated_at: "2024-12-01",
  bio: "Diputada Federal por el Distrito 10 de CDMX. Enfocada en politicas de desarrollo social y participacion ciudadana.",
  social_accounts: [
    { platform: "twitter", username: "anamartinez_mx", url: "https://twitter.com/anamartinez_mx", followers: 245000, verified: true },
    { platform: "instagram", username: "ana.martinez.oficial", url: "https://instagram.com/ana.martinez.oficial", followers: 180000, verified: true },
    { platform: "facebook", username: "AnaMartinezOficial", url: "https://facebook.com/AnaMartinezOficial", followers: 320000, verified: false },
  ],
  ipd_breakdown: {
    twitter: 9.5,
    instagram: 8.8,
    facebook: 9.0,
    tiktok: 0,
    youtube: 0,
    engagement: 9.4,
  },
  secciones: [
    { id: 1, seccion_id: "0901", estado: "CDMX", municipio: "Coyoacan", a_favor: 68, en_contra: 18, indeciso: 14, total_encuestas: 450 },
    { id: 2, seccion_id: "0902", estado: "CDMX", municipio: "Coyoacan", a_favor: 72, en_contra: 15, indeciso: 13, total_encuestas: 380 },
  ],
  recent_posts: [
    {
      id: 1, dirigente_id: 1, platform: "twitter",
      content: "Hoy visitamos las comunidades rurales del distrito. Escuchamos sus necesidades y comprometimos acciones concretas.",
      url: "https://twitter.com/example/1", sentiment: "positive", sentiment_score: 0.87,
      likes: 1420, comments: 89, shares: 234, views: 45200,
      published_at: new Date(Date.now() - 2 * 3600000).toISOString(),
      collected_at: new Date().toISOString(),
    },
    {
      id: 2, dirigente_id: 1, platform: "instagram",
      content: "Inauguracion del programa de becas para jovenes de nuestra comunidad. 500 beneficiarios en la primera etapa.",
      url: "https://instagram.com/p/2", sentiment: "positive", sentiment_score: 0.92,
      likes: 5200, comments: 312, shares: 145,
      published_at: new Date(Date.now() - 12 * 3600000).toISOString(),
      collected_at: new Date().toISOString(),
    },
    {
      id: 3, dirigente_id: 1, platform: "facebook",
      content: "Es inaceptable que el presupuesto para educacion se recorte un 15%. Presentaremos una contrapropuesta el lunes.",
      url: "https://facebook.com/p/3", sentiment: "negative", sentiment_score: 0.65,
      likes: 890, comments: 256, shares: 412,
      published_at: new Date(Date.now() - 24 * 3600000).toISOString(),
      collected_at: new Date().toISOString(),
    },
  ],
  stats: {
    total_posts_7d: 28,
    total_engagement_7d: 124500,
    sentiment_avg_7d: 0.72,
    follower_growth_30d: 3.2,
  },
};

const MOCK_SENTIMENT_TREND: SentimentTrend[] = Array.from({ length: 30 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toISOString().slice(0, 10),
    positive: Math.floor(50 + Math.random() * 25),
    negative: Math.floor(5 + Math.random() * 15),
    neutral: Math.floor(15 + Math.random() * 10),
  };
});

const MOCK_PLANS = [
  { id: 1, titulo: "Plan de Crecimiento Q1 2025", tipo: "crecimiento", status: "approved", created_at: "2025-01-05" },
  { id: 2, titulo: "Respuesta a Crisis Presupuestal", tipo: "crisis", status: "executed", created_at: "2025-02-12" },
  { id: 3, titulo: "Estrategia de Engagement TikTok", tipo: "engagement", status: "draft", created_at: "2025-03-20" },
];
/* ---- End mock data ---- */

export default function DirigenteDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { data, isLoading } = useDirigente(id);

  const dirigente = data ?? MOCK_DIRIGENTE;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link href="/dashboard/dirigentes">
        <Button variant="ghost" size="sm" className="gap-1.5">
          <ArrowLeft className="h-4 w-4" />
          Volver a Dirigentes
        </Button>
      </Link>

      {/* Profile header */}
      <ProfileHeader dirigente={dirigente} />

      {/* Quick stats */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Posts (7d)</p>
            <p className="mt-1 font-heading text-xl font-bold">
              {dirigente.stats.total_posts_7d}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Engagement (7d)</p>
            <p className="mt-1 font-heading text-xl font-bold">
              {formatNumber(dirigente.stats.total_engagement_7d)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Sentimiento Prom.</p>
            <SentimentBadge
              sentiment={
                dirigente.stats.sentiment_avg_7d > 0.6
                  ? "positive"
                  : dirigente.stats.sentiment_avg_7d > 0.4
                  ? "neutral"
                  : "negative"
              }
              score={dirigente.stats.sentiment_avg_7d}
            />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Crecimiento (30d)</p>
            <p className="mt-1 font-heading text-xl font-bold text-emerald-600 dark:text-emerald-400">
              +{dirigente.stats.follower_growth_30d}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="social">Social</TabsTrigger>
          <TabsTrigger value="electoral">Electoral</TabsTrigger>
          <TabsTrigger value="planes">Planes</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Indice de Penetracion Digital</CardTitle>
              </CardHeader>
              <CardContent>
                <IpdRadarChart data={dirigente.ipd_breakdown} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Sentimiento (30 dias)</CardTitle>
              </CardHeader>
              <CardContent>
                <SentimentLineChart data={MOCK_SENTIMENT_TREND} />
              </CardContent>
            </Card>
          </div>
          <div>
            <h3 className="mb-3 font-heading text-lg font-semibold">
              Publicaciones Recientes
            </h3>
            <div className="space-y-3">
              {dirigente.recent_posts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          </div>
        </TabsContent>

        {/* Social Tab */}
        <TabsContent value="social" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Sentimiento en el Tiempo</CardTitle>
              </CardHeader>
              <CardContent>
                <SentimentLineChart data={MOCK_SENTIMENT_TREND} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Engagement por Plataforma</CardTitle>
              </CardHeader>
              <CardContent>
                <EngagementBarChart
                  data={dirigente.social_accounts.map((a) => ({
                    name: a.platform.charAt(0).toUpperCase() + a.platform.slice(1),
                    value: a.followers,
                  }))}
                />
              </CardContent>
            </Card>
          </div>
          <div>
            <h3 className="mb-3 font-heading text-lg font-semibold">
              Timeline de Publicaciones
            </h3>
            <div className="space-y-3">
              {dirigente.recent_posts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
            {dirigente.recent_posts.length === 0 && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                  <MessageSquare className="mb-3 h-10 w-10 text-muted-foreground/50" />
                  <p className="text-sm text-muted-foreground">
                    No hay publicaciones disponibles
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Electoral Tab */}
        <TabsContent value="electoral" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Mapa de Secciones Electorales</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="h-[500px] overflow-hidden rounded-b-lg">
                <ElectoralMap className="h-full" />
              </div>
            </CardContent>
          </Card>
          <div>
            <h3 className="mb-3 font-heading text-lg font-semibold">
              Detalle de Secciones
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {dirigente.secciones.map((seccion) => (
                <Card key={seccion.id}>
                  <CardContent className="p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="font-heading font-semibold">
                        Seccion {seccion.seccion_id}
                      </span>
                      <Badge variant="secondary">{seccion.municipio}</Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center text-sm">
                      <div>
                        <p className="font-semibold text-emerald-600 dark:text-emerald-400">
                          {seccion.a_favor}%
                        </p>
                        <p className="text-xs text-muted-foreground">A favor</p>
                      </div>
                      <div>
                        <p className="font-semibold text-amber-600 dark:text-amber-400">
                          {seccion.indeciso}%
                        </p>
                        <p className="text-xs text-muted-foreground">Indeciso</p>
                      </div>
                      <div>
                        <p className="font-semibold text-red-600 dark:text-red-400">
                          {seccion.en_contra}%
                        </p>
                        <p className="text-xs text-muted-foreground">En contra</p>
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {seccion.total_encuestas} encuestas
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </TabsContent>

        {/* Plans Tab */}
        <TabsContent value="planes" className="space-y-4">
          {MOCK_PLANS.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <Brain className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No hay planes generados para este dirigente
                </p>
              </CardContent>
            </Card>
          ) : (
            MOCK_PLANS.map((plan) => (
              <Card key={plan.id}>
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <p className="font-medium">{plan.titulo}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <Badge variant="secondary">{plan.tipo}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(plan.created_at)}
                      </span>
                    </div>
                  </div>
                  <Badge
                    variant={
                      plan.status === "approved"
                        ? "success"
                        : plan.status === "executed"
                        ? "default"
                        : plan.status === "rejected"
                        ? "danger"
                        : "secondary"
                    }
                  >
                    {plan.status === "approved"
                      ? "Aprobado"
                      : plan.status === "executed"
                      ? "Ejecutado"
                      : plan.status === "rejected"
                      ? "Rechazado"
                      : "Borrador"}
                  </Badge>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
