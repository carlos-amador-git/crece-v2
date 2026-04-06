"use client";

import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useDirigente } from "@/lib/api/hooks/use-dirigentes";
import { useSentimentTrend } from "@/lib/api/hooks/use-social";
import { usePlanes } from "@/lib/api/hooks/use-planes";
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
import { ArrowLeft, MessageSquare, Users, Brain } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const ElectoralMap = dynamic(
  () => import("@/components/maps/electoral-map").then((m) => m.ElectoralMap),
  { ssr: false, loading: () => <Skeleton className="h-[400px] w-full rounded-lg" /> }
);

/* No mock data — all data fetched from API */

export default function DirigenteDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { data: dirigente, isLoading, isError } = useDirigente(id);
  const { data: sentimentTrendData } = useSentimentTrend(30, dirigente?.id);
  const { data: planesData } = usePlanes(undefined, 1);

  const sentimentTrend = sentimentTrendData ?? [];
  // Filter plans for this dirigente
  const dirigentePlans = (planesData?.items ?? []).filter(
    (p) => p.dirigente_id === Number(id)
  );

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

  if (isError || !dirigente) {
    return (
      <div className="space-y-6">
        <Link href="/dashboard/dirigentes">
          <Button variant="ghost" size="sm" className="gap-1.5">
            <ArrowLeft className="h-4 w-4" />
            Volver a Dirigentes
          </Button>
        </Link>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Users className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="font-medium">No se pudo cargar el dirigente</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Verifica que el ID sea correcto o intenta de nuevo
            </p>
          </CardContent>
        </Card>
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
              {dirigente.stats?.total_posts_7d ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Engagement (7d)</p>
            <p className="mt-1 font-heading text-xl font-bold">
              {formatNumber(dirigente.stats?.total_engagement_7d ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Sentimiento Prom.</p>
            <SentimentBadge
              sentiment={
                (dirigente.stats?.sentiment_avg_7d ?? 0.5) > 0.6
                  ? "positive"
                  : (dirigente.stats?.sentiment_avg_7d ?? 0.5) > 0.4
                  ? "neutral"
                  : "negative"
              }
              score={dirigente.stats?.sentiment_avg_7d ?? 0.5}
            />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Crecimiento (30d)</p>
            <p className="mt-1 font-heading text-xl font-bold text-emerald-600 dark:text-emerald-400">
              +{dirigente.stats?.follower_growth_30d ?? 0}%
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
                <SentimentLineChart data={sentimentTrend} />
              </CardContent>
            </Card>
          </div>
          <div>
            <h3 className="mb-3 font-heading text-lg font-semibold">
              Publicaciones Recientes
            </h3>
            <div className="space-y-3">
              {(dirigente.recent_posts ?? []).map((post) => (
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
                <SentimentLineChart data={sentimentTrend} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Engagement por Plataforma</CardTitle>
              </CardHeader>
              <CardContent>
                <EngagementBarChart
                  data={(dirigente.social_accounts ?? []).map((a) => ({
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
              {(dirigente.recent_posts ?? []).map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
            {(dirigente.recent_posts ?? []).length === 0 && (
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
              {(dirigente.secciones ?? []).map((seccion) => (
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
          {dirigentePlans.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <Brain className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No hay planes generados para este dirigente
                </p>
              </CardContent>
            </Card>
          ) : (
            dirigentePlans.map((plan) => (
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
