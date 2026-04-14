"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import {
  Activity, AlertCircle, CheckCircle2, Database, FileText, Mic,
  PlayCircle, Target, TrendingUp, Users,
} from "lucide-react";

interface OrgStatus {
  org_id: number;
  nombre: string;
  dirigentes: number;
  posts_total: number;
  posts_clasificados: number;
  coverage_framework_pct: number;
  posts_nlp_procesados: number;
  coverage_nlp_pct: number;
  planes_total: number;
  planes_con_tareas: number;
  tareas_total: number;
}

interface Overview {
  flota: OrgStatus[];
  pipeline_nlp: {
    posts_total: number;
    procesados: number;
    pendientes_sin_texto: number;
    pendientes_con_texto: number;
    coverage_pct: number;
  };
  cola_semanal: {
    posts_pendientes_clasificar: number;
    posts_pendientes_whisper: number;
    planes_sin_tareas_estructuradas: number;
    dirigentes_sin_plan: number;
  };
  health: { db: string; redis: string; overall: string };
  divergencia_alerts: number;
  totales: Record<string, number>;
}

const POLL_MS = 30_000;

function healthColor(s: string) {
  if (s === "OK") return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  if (s === "WARN") return "bg-amber-500/15 text-amber-300 border-amber-500/30";
  return "bg-rose-500/15 text-rose-300 border-rose-500/30";
}

function coverageColor(pct: number) {
  if (pct >= 80) return "text-emerald-400";
  if (pct >= 40) return "text-amber-400";
  return "text-rose-400";
}

export default function AdminOverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const load = async () => {
    try {
      const r = await api.get<Overview>("/admin/overview");
      setData(r);
      setError(null);
      setLastUpdate(new Date());
    } catch (e: any) {
      setError(e?.message ?? "Error cargando overview");
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, []);

  if (error) {
    return (
      <div className="p-6">
        <Card className="border-rose-500/40">
          <CardHeader>
            <CardTitle className="text-rose-300 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" /> Error
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">{error}</CardContent>
        </Card>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-10 w-80" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      </div>
    );
  }

  const { flota, pipeline_nlp, cola_semanal, health, totales } = data;

  return (
    <div className="p-6 space-y-6">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight">Admin · Operación de flota</h1>
          <p className="text-sm text-muted-foreground">
            Vista operativa MD Consultoría · {totales.orgs} orgs · {totales.dirigentes} dirigentes · {totales.posts} posts
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <Badge variant="outline" className={healthColor(health.overall)}>
            <Activity className="mr-1 h-3 w-3" /> Sistema {health.overall}
          </Badge>
          {lastUpdate && <span>Actualizado {lastUpdate.toLocaleTimeString("es-MX")}</span>}
        </div>
      </header>

      {/* Esta semana toca */}
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="h-4 w-4 text-amber-400" /> Esta semana toca
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <div className="text-2xl font-bold">{cola_semanal.posts_pendientes_clasificar}</div>
              <div className="text-xs text-muted-foreground">posts por clasificar</div>
              <Link href="/dashboard/admin/clasificacion" className="mt-2 block">
                <Button size="sm" variant="outline" className="w-full">
                  <PlayCircle className="mr-1 h-3 w-3" /> Clasificar
                </Button>
              </Link>
            </div>
            <div>
              <div className="text-2xl font-bold">{cola_semanal.posts_pendientes_whisper}</div>
              <div className="text-xs text-muted-foreground">TikToks sin transcribir</div>
              <Badge variant="outline" className="mt-2 text-xs">Whisper pipeline</Badge>
            </div>
            <div>
              <div className="text-2xl font-bold">{cola_semanal.planes_sin_tareas_estructuradas}</div>
              <div className="text-xs text-muted-foreground">planes sin tareas medibles</div>
              <Badge variant="outline" className="mt-2 text-xs">Estructurar</Badge>
            </div>
            <div>
              <div className="text-2xl font-bold">{cola_semanal.dirigentes_sin_plan}</div>
              <div className="text-xs text-muted-foreground">dirigentes sin plan</div>
              <Badge variant="outline" className="mt-2 text-xs">Generar</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Flota clientes */}
      <div>
        <h2 className="mb-3 font-heading text-lg font-semibold">Flota de clientes</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {flota.map((o) => (
            <Card key={o.org_id}>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between text-sm">
                  <span className="truncate">{o.nombre}</span>
                  <Badge variant="outline" className="ml-2 text-xs">org {o.org_id}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="flex items-center gap-1"><Users className="h-3 w-3" />Dirigentes</span>
                  <span className="font-semibold text-foreground">{o.dirigentes}</span>
                </div>
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="flex items-center gap-1"><FileText className="h-3 w-3" />Posts</span>
                  <span className="font-semibold text-foreground">{o.posts_total}</span>
                </div>
                <div className="space-y-1 pt-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Framework político</span>
                    <span className={coverageColor(o.coverage_framework_pct)}>
                      {o.coverage_framework_pct.toFixed(1)}% · {o.posts_clasificados}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-amber-500"
                      style={{ width: `${Math.min(100, o.coverage_framework_pct)}%` }}
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>NLP técnico</span>
                    <span className={coverageColor(o.coverage_nlp_pct)}>
                      {o.coverage_nlp_pct.toFixed(1)}% · {o.posts_nlp_procesados}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-emerald-500"
                      style={{ width: `${Math.min(100, o.coverage_nlp_pct)}%` }}
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between border-t border-border pt-2 text-xs text-muted-foreground">
                  <span>Planes: {o.planes_total} · Tareas: {o.tareas_total}</span>
                  <Link href={`/dashboard?as_org=${o.org_id}`}>
                    <Button size="sm" variant="ghost" className="h-6 px-2 text-xs">
                      Ver como cliente →
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Sistema + Pipeline */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-4 w-4" /> Salud del sistema
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">PostgreSQL</span>
              <Badge variant="outline" className={healthColor(health.db)}>{health.db}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Redis</span>
              <Badge variant="outline" className={healthColor(health.redis)}>{health.redis}</Badge>
            </div>
            <div className="flex items-center justify-between border-t border-border pt-2">
              <span className="text-muted-foreground">Divergencia encuestas</span>
              <Badge variant="outline" className="text-xs">{data.divergencia_alerts} alertas</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4" /> Pipeline NLP
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-bold">{pipeline_nlp.coverage_pct.toFixed(1)}%</span>
              <span className="text-xs text-muted-foreground">
                {pipeline_nlp.procesados} / {pipeline_nlp.posts_total}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-emerald-500"
                style={{ width: `${pipeline_nlp.coverage_pct}%` }}
              />
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2 text-xs text-muted-foreground">
              <div>
                <CheckCircle2 className="mr-1 inline h-3 w-3" />
                {pipeline_nlp.procesados} procesados
              </div>
              <div>
                <Mic className="mr-1 inline h-3 w-3" />
                {pipeline_nlp.pendientes_sin_texto} sin texto
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Acciones rápidas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Link href="/dashboard/admin/clasificacion">
              <Button variant="outline" size="sm">
                <PlayCircle className="mr-1 h-3 w-3" /> Panel clasificación
              </Button>
            </Link>
            <Link href="/dashboard/settings/analisis-politico">
              <Button variant="outline" size="sm">
                <Target className="mr-1 h-3 w-3" /> Framework político
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
