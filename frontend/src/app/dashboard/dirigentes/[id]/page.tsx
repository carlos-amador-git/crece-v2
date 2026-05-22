"use client";

import { useParams } from "next/navigation";
// import dynamic from "next/dynamic";
import { useDirigente, useDirigenteCrecimiento } from "@/lib/api/hooks/use-dirigentes";
import { useTonoDiscursoTrend } from "@/lib/api/hooks/use-social";
import { usePlanes } from "@/lib/api/hooks/use-planes";
import { TendenciaPorRedWidget } from "@/components/charts/tendencia-por-red-widget";
import { SemaforoCrecimiento } from "@/components/dashboard/semaforo-crecimiento";
import { ActividadAlineadaCard } from "@/components/dashboard/actividad-alineada-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ProfileHeader } from "@/components/dirigentes/profile-header";
import { CompetitorsSection } from "@/components/dirigentes/competitors-section";
import { IpdRadarChart } from "@/components/charts/ipd-radar-chart";
import { TonoDiscursoChart } from "@/components/charts/tono-discurso-chart";
import { EngagementBarChart } from "@/components/charts/engagement-bar-chart";
import { PostCard } from "@/components/social/post-card";
// SentimentBadge ya no se usa en ficha dirigente · D-23-G' KPI hero ahora es ActividadAlineadaCard.
// El componente se preserva para PostCard y otras vistas (no se borra del bundle · decisión CEO 2026-04-25).
import { formatNumber, formatDate, cn } from "@/lib/utils";
import { ArrowLeft, MessageSquare, Users, Brain } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

// Electoral map hidden until INE shapefiles are loaded
// const ElectoralMap = dynamic(
//   () => import("@/components/maps/electoral-map").then((m) => m.ElectoralMap),
//   { ssr: false, loading: () => <Skeleton className="h-[400px] w-full rounded-lg" /> }
// );

/* No mock data — all data fetched from API */

export default function DirigenteDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { data: dirigente, isLoading, isError } = useDirigente(id);
  // P1 #1 (2026-05-19): migración tono_discurso. Hook legacy queda en backend pero ya no consumido aquí.
  const { data: tonoTrendData } = useTonoDiscursoTrend(30, dirigente?.id);
  const { data: planesData } = usePlanes(undefined, 1);
  const { data: crecimiento } = useDirigenteCrecimiento(id);

  const sentimentTrend = tonoTrendData ?? [];
  // Filter plans for this dirigente, including only updated AI Plans (Estrategia and Contenido)
  const dirigentePlans = (planesData?.items ?? []).filter(
    (p) =>
      p.dirigente_id === Number(id) &&
      (p.tipo === "CONSOLIDACION" || p.tipo === "CONTENIDO")
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
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
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
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
        {/* D-23-G' · KPI hero reformulado · 2026-04-24 · reemplaza Sentimiento Prom. flipeado */}
        {/* D-23-H · Phase B · 2026-04-25 · click ingresa al panel editable de evaluación */}
        <Link
          href={`/dashboard/evaluacion/${dirigente.id}`}
          className="block transition hover:ring-2 hover:ring-primary/30 rounded-lg"
          aria-label="Ajustar pesos de evaluación"
        >
          <ActividadAlineadaCard data={dirigente.stats?.actividad_alineada} />
        </Link>
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
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="relative overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div>
                  <CardTitle>Indice de Penetracion Digital</CardTitle>
                  <p className="text-xs text-muted-foreground">Fortaleza relativa por plataforma (0-10)</p>
                </div>
                {(() => {
                  const values = Object.values(dirigente.ipd_breakdown ?? {});
                  const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
                  const signal = avg > 7 ? { label: "Sobresaliente", class: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" } :
                                avg > 5 ? { label: "Saludable", class: "bg-blue-500/10 text-blue-600 border-blue-500/20" } :
                                avg > 3 ? { label: "Bajo Impacto", class: "bg-amber-500/10 text-amber-600 border-amber-500/20" } :
                                { label: "Crítico", class: "bg-red-500/10 text-red-600 border-red-500/20" };
                  return (
                    <Badge variant="outline" className={cn("font-bold uppercase tracking-wider", signal.class)}>
                      {signal.label}
                    </Badge>
                  );
                })()}
              </CardHeader>
              <CardContent>
                <IpdRadarChart data={dirigente.ipd_breakdown ?? { twitter: 0, instagram: 0, facebook: 0, tiktok: 0, youtube: 0, engagement: 0 }} />
              </CardContent>
            </Card>

            <Card className="flex flex-col">
              <CardHeader>
                <CardTitle>Resumen de Desempeño</CardTitle>
                <p className="text-xs text-muted-foreground">Análisis contextual de los últimos 30 días</p>
              </CardHeader>
              <CardContent className="flex-1 space-y-4">
                <div className="space-y-2">
                  <p className="text-sm font-medium">Fortalezas detectadas</p>
                  <ul className="space-y-1.5 text-xs text-muted-foreground">
                    <li className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      Dominio destacado en {Object.entries(dirigente.ipd_breakdown ?? {}).sort(([,a],[,b]) => b-a)[0]?.[0]}
                    </li>
                    {dirigente.stats?.total_engagement_7d > 5000 && (
                      <li className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        Engagement superior al benchmark del estrato
                      </li>
                    )}
                  </ul>
                </div>
                <div className="space-y-2 pt-2 border-t border-dashed">
                  <p className="text-sm font-medium">Oportunidades de mejora</p>
                  <ul className="space-y-1.5 text-xs text-muted-foreground">
                    {Object.entries(dirigente.ipd_breakdown ?? {}).some(([,v]) => v < 3) && (
                      <li className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                        Presencia digital insuficiente en redes secundarias
                      </li>
                    )}
                    {dirigente.stats?.total_engagement_7d === 0 && (
                      <li className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                        Señal de estancamiento en la conversación activa
                      </li>
                    )}
                  </ul>
                </div>
                <div className="mt-auto pt-4 flex justify-end">
                   <Button asChild variant="outline" size="sm" className="text-[10px] uppercase font-bold tracking-widest h-8">
                     <Link href={`/dashboard/diagnostico?dirigente=${dirigente.id}`}>Ver Diagnóstico Full →</Link>
                   </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Competidores · Sprint W8 war-room-personal */}
          <CompetitorsSection
            dirigenteId={dirigente.id}
            dirigenteFollowers={
              dirigente.social_accounts?.reduce((acc, sa) => acc + (sa.followers ?? 0), 0) ?? 0
            }
            dirigenteFirstName={dirigente.full_name?.split(" ")[0]}
          />

          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-heading text-lg font-semibold">
                Contenido con más Impacto
              </h3>
              <TabsList className="bg-transparent h-auto p-0">
                <TabsTrigger value="social" className="text-xs text-muted-foreground hover:text-foreground p-0 h-auto bg-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:underline">
                  Ver todo el timeline →
                </TabsTrigger>
              </TabsList>
            </div>
            <div className="space-y-3">
              {(dirigente.recent_posts ?? []).slice(0, 3).map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
              {(dirigente.recent_posts ?? []).length === 0 && (
                <p className="text-sm text-muted-foreground italic text-center py-8">Sin publicaciones recientes.</p>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Social Tab */}
        <TabsContent value="social" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-3">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Sentimiento en el Tiempo</CardTitle>
              </CardHeader>
              <CardContent>
                <TonoDiscursoChart data={sentimentTrend} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Engagement por Plataforma</CardTitle>
              </CardHeader>
              <CardContent>
                <EngagementBarChart
                  data={((dirigente.social_accounts ?? (dirigente as any).social_profiles) ?? []).map((a: any) => ({
                    name: a.platform ? a.platform.charAt(0).toUpperCase() + a.platform.slice(1) : "Plataforma",
                    value: a.followers ?? a.followers_count ?? 0,
                  }))}
                />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <div className="md:col-span-2">
              <TendenciaPorRedWidget series={crecimiento?.series ?? []} />
            </div>
            <SemaforoCrecimiento platforms={crecimiento?.platforms ?? []} />
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
          <div>
            <h3 className="mb-3 font-heading text-lg font-semibold">
              Detalle de Secciones
            </h3>
            {(dirigente.secciones ?? []).length === 0 && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center gap-2 py-12 text-center">
                  <MessageSquare className="h-10 w-10 text-muted-foreground/50" aria-hidden="true" />
                  <p className="text-sm font-medium">Sin territorio asignado</p>
                  <p className="max-w-md text-xs text-muted-foreground">
                    {dirigente.cargo?.toLowerCase().includes("plurinominal")
                      ? "Los cargos plurinominales no se asocian a secciones electorales. Si deseas seguir un territorio específico, configúralo en el wizard de onboarding."
                      : "Este dirigente aún no tiene secciones electorales vinculadas. Configúralas en el wizard de onboarding para ver detalle por sección."}
                  </p>
                </CardContent>
              </Card>
            )}
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
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
              <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
                <Brain className="h-10 w-10 text-muted-foreground/50" />
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">
                    No hay planes generados para este dirigente
                  </p>
                  <p className="text-xs text-muted-foreground/80">
                    Genera un plan de acción con IA basado en su diagnóstico actual.
                  </p>
                </div>
                <Button asChild size="sm">
                  <Link href={`/dashboard/planes?dirigente=${dirigente.id}`}>
                    <Brain className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                    Generar plan
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            dirigentePlans.map((plan: any, idx: number) => {
              const preview = (plan.contenido ?? "").slice(0, 250).replace(/[#*|_]/g, "").trim();
              const tipoLabel = plan.tipo === "DIAGNOSTICO" ? "Diagnostico" : plan.tipo === "CONSOLIDACION" ? "Consolidacion" : plan.tipo === "CRISIS" ? "Crisis" : "Contenido";
              const version = dirigentePlans.length - idx;
              const createdTime = new Date(plan.created_at).toLocaleString("es-MX", {
                day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit"
              });

              const targetHref =
                plan.tipo === "CONSOLIDACION"
                  ? `/dashboard/planes?dirigente=${dirigente.id}&tab=estrategia`
                  : plan.tipo === "CONTENIDO"
                  ? `/dashboard/planes?dirigente=${dirigente.id}&tab=contenido`
                  : plan.tipo === "DIAGNOSTICO"
                  ? `/dashboard/diagnostico/${dirigente.id}/foda`
                  : `/dashboard/planes?dirigente=${dirigente.id}`;

              return (
                <Link key={plan.id} href={targetHref}>
                  <Card className="cursor-pointer transition-shadow hover:shadow-md">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="secondary">{plan.tipo}</Badge>
                            <Badge variant="outline" className="text-[10px]">v{version}</Badge>
                            <span className="text-xs text-muted-foreground">{createdTime}</span>
                          </div>
                          <p className="font-heading font-semibold text-foreground">
                            {tipoLabel} — {tipoLabel === "Diagnostico" ? "Presencia Digital" : tipoLabel === "Consolidacion" ? "Plan 90 dias" : tipoLabel === "Crisis" ? "Manejo de Crisis" : "Calendario Editorial"}
                          </p>
                          <p className="mt-1.5 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                            {preview || "Sin contenido"}
                          </p>
                          <div className="mt-2 flex items-center gap-3 text-[10px] text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent" />
                              {plan.modelo_ia ?? "IA"}
                            </span>
                            <span>{((plan.contenido ?? "").length / 1000).toFixed(1)}K caracteres</span>
                            <span>Plan #{plan.id}</span>
                          </div>
                        </div>
                        <Badge variant={plan.aprobado ? "default" : "secondary"}>
                          {plan.aprobado ? "Aprobado" : "Borrador"}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
