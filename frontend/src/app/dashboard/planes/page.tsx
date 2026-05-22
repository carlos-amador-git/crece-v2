"use client";

/**
 * Planes IA · Concepto 3 (Ecosistema por Dominios) · 2026-05-21
 *
 * Rediseño completo aprobado por CEO 2026-05-21 tras consulta Gemini.
 * D-PLANES-CONCEPTO-3 · 3 tabs visuales independientes:
 *
 *   [Diagnóstico] [Estrategia] [Contenido]
 *
 * Cada tab tiene UI propia adaptada al tipo de plan:
 * - Diagnóstico: Hero IPD score + Insight Bala + Fortalezas/Debilidades/Riesgos
 *   + Top 3 acciones priorizadas con CTA. Sintetiza B01-B18 del módulo
 *   Diagnóstico+Diferenciadores via regen_diagnostico_v2.py.
 * - Estrategia: Plan 90 días (próximamente · empty state hasta arrancar Fase 2).
 * - Contenido: Calendario editorial (próximamente · empty state).
 *
 * Sin CTA "Generar Plan" en header (D-CTA-GENERATE-REMOVED 2026-05-21).
 * Multi-dirigente selector solo para admin/analyst (D-ACEPTACION-DEDUPE patrón).
 * RBAC backend `_check_org` + endpoint filtra auto por user.dirigente_id.
 */

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { usePlanes } from "@/lib/api/hooks/use-planes";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PlanIA, DiagnosticoEstructura, ConsolidacionEstructura, ContenidoEstructura } from "@/lib/api/types";
import {
  Stethoscope,
  Target,
  Calendar,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  ArrowRight,
  Clock,
  Users,
  Megaphone,
  Hash,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

// D-PLANES-DIAGNOSTICO-REMOVED-2026-05-22 · tab Diagnóstico eliminado.
// Análisis vive en menú Diagnóstico (Recepción · Diferenciadores · FODA).
// Planes IA queda enfocado en lo prospectivo: Estrategia + Contenido.
const TAB_VALUES = ["estrategia", "contenido"] as const;
type TabKey = (typeof TAB_VALUES)[number];

function isAdminRole(role: string | undefined): boolean {
  return role === "admin" || role === "analyst";
}

function PlanesInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const tabParam = searchParams.get("tab");
  // Default "estrategia" (antes "diagnostico" · removido 2026-05-22).
  // Bookmarks viejos con tab=diagnostico caen silenciosamente a estrategia.
  const initialTab: TabKey =
    TAB_VALUES.includes((tabParam ?? "") as TabKey) ? (tabParam as TabKey) : "estrategia";

  const userRole = (user as { role?: string } | null)?.role;
  const userDirigenteId = (user as { dirigente_id?: number } | null)?.dirigente_id;
  const showSelector = isAdminRole(userRole);

  // Lista dirigentes solo si admin (para selector)
  const { data: dirigentesData } = useDirigentes({ per_page: 50 });
  const dirigentesList = dirigentesData?.items ?? [];

  const [selectedDirigenteId, setSelectedDirigenteId] = useState<number | null>(null);

  // Inicialización: viewer → su dirigente · admin → primero de la lista
  useEffect(() => {
    if (selectedDirigenteId != null) return;
    if (userDirigenteId) {
      setSelectedDirigenteId(userDirigenteId);
    } else if (dirigentesList.length > 0) {
      setSelectedDirigenteId(dirigentesList[0].id);
    }
  }, [userDirigenteId, dirigentesList, selectedDirigenteId]);

  const onTabChange = (val: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", val);
    router.replace(`/dashboard/planes?${params.toString()}`);
  };

  if (selectedDirigenteId == null) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-[60vh]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight">Planes IA</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Diagnóstico estratégico, plan trimestral y calendario editorial generados con inteligencia
          artificial.
        </p>
      </div>

      {showSelector && dirigentesList.length > 1 && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Dirigente:</span>
          <Select
            value={String(selectedDirigenteId)}
            onValueChange={(v) => setSelectedDirigenteId(Number(v))}
          >
            <SelectTrigger className="w-[280px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {dirigentesList.map((d) => (
                <SelectItem key={d.id} value={String(d.id)}>
                  {d.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <Tabs defaultValue={initialTab} onValueChange={onTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
          <TabsTrigger value="estrategia" className="gap-2">
            <Target className="h-4 w-4" /> Estrategia
          </TabsTrigger>
          <TabsTrigger value="contenido" className="gap-2">
            <Calendar className="h-4 w-4" /> Contenido
          </TabsTrigger>
        </TabsList>

        <TabsContent value="estrategia" className="mt-6">
          <EstrategiaTab dirigenteId={selectedDirigenteId} />
        </TabsContent>

        <TabsContent value="contenido" className="mt-6">
          <ContenidoTab dirigenteId={selectedDirigenteId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

/* ─────── Tab Diagnóstico ─────── */

function DiagnosticoTab({ dirigenteId }: { dirigenteId: number }) {
  const { data, isLoading, error } = usePlanes(undefined, 1);
  const allPlans = data?.items ?? [];

  const planesDiagnostico = useMemo(
    () =>
      allPlans
        .filter((p) => p.tipo === "DIAGNOSTICO" && p.dirigente_id === dirigenteId)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [allPlans, dirigenteId],
  );

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48" />
        <Skeleton className="h-32" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-destructive">
          No se pudo cargar el diagnóstico.
        </CardContent>
      </Card>
    );
  }

  const vigente = planesDiagnostico[0];
  const historicos = planesDiagnostico.slice(1);

  if (!vigente) {
    return <EmptyDiagnostico />;
  }

  const estructura = vigente.estructura_json as DiagnosticoEstructura | undefined;
  const isDiagnosticoV2 = estructura && typeof estructura.ipd_score === "number";

  return (
    <div className="space-y-6">
      {isDiagnosticoV2 ? (
        <DiagnosticoVigente plan={vigente} estructura={estructura as DiagnosticoEstructura} />
      ) : (
        <DiagnosticoLegacy plan={vigente} />
      )}

      {historicos.length > 0 && (
        <Card className="border-dashed">
          <CardContent className="p-4">
            <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
              Histórico ({historicos.length})
            </h3>
            <div className="space-y-1.5">
              {historicos.slice(0, 5).map((h) => (
                <div
                  key={h.id}
                  className="flex items-center justify-between rounded-md border bg-card px-3 py-2 text-xs"
                >
                  <span className="text-muted-foreground">
                    {new Date(h.created_at).toLocaleDateString("es-MX", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </span>
                  <span className="text-muted-foreground">{h.modelo_ia}</span>
                </div>
              ))}
              {historicos.length > 5 && (
                <p className="text-center text-xs text-muted-foreground">
                  + {historicos.length - 5} versiones anteriores
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function DiagnosticoVigente({
  plan,
  estructura,
}: {
  plan: PlanIA;
  estructura: DiagnosticoEstructura;
}) {
  const bucketColor = {
    BAJO: "text-rose-500",
    MEDIO: "text-amber-500",
    ALTO: "text-emerald-500",
  }[estructura.ipd_bucket];

  const bucketBg = {
    BAJO: "bg-rose-500",
    MEDIO: "bg-amber-500",
    ALTO: "bg-emerald-500",
  }[estructura.ipd_bucket];

  const scorePct = Math.min(100, (estructura.ipd_score / 10) * 100);

  return (
    <div className="space-y-6">
      {/* Hero IPD */}
      <Card className="overflow-hidden">
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex items-baseline gap-3">
                <span className={`font-heading text-6xl font-bold tabular-nums ${bucketColor}`}>
                  {estructura.ipd_score.toFixed(1)}
                </span>
                <span className="text-sm text-muted-foreground">/ 10</span>
                <Badge variant="outline" className={`uppercase ${bucketColor}`}>
                  {estructura.ipd_bucket}
                </Badge>
                {estructura.delta_vs_anterior != null && (
                  <span
                    className={`text-sm font-medium ${
                      estructura.delta_vs_anterior >= 0 ? "text-emerald-500" : "text-rose-500"
                    }`}
                  >
                    {estructura.delta_vs_anterior >= 0 ? "+" : ""}
                    {estructura.delta_vs_anterior.toFixed(1)} vs anterior
                  </span>
                )}
              </div>
              <div className="mt-3 h-2 w-full max-w-md overflow-hidden rounded-full bg-muted">
                <div
                  className={`h-full transition-all ${bucketBg}`}
                  style={{ width: `${scorePct}%` }}
                />
              </div>
              <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                Generado{" "}
                {new Date(plan.created_at).toLocaleDateString("es-MX", {
                  day: "2-digit",
                  month: "long",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                · modelo {plan.modelo_ia}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Insight Bala */}
      <Card className="border-l-4 border-l-accent bg-accent/5">
        <CardContent className="p-5">
          <p className="font-heading text-lg font-medium leading-snug">
            {estructura.insight_bala}
          </p>
        </CardContent>
      </Card>

      {/* Fortalezas · Debilidades · Riesgos · 3 columnas */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <FactorBlock
          titulo="Fortalezas"
          icon={<ShieldCheck className="h-4 w-4 text-emerald-500" />}
          accent="emerald"
          items={estructura.fortalezas}
        />
        <FactorBlock
          titulo="Debilidades"
          icon={<TrendingUp className="h-4 w-4 rotate-180 text-amber-500" />}
          accent="amber"
          items={estructura.debilidades}
        />
        <FactorBlock
          titulo="Riesgos"
          icon={<AlertTriangle className="h-4 w-4 text-rose-500" />}
          accent="rose"
          items={estructura.riesgos}
        />
      </div>

      {/* Top 3 acciones */}
      <div>
        <h3 className="mb-3 font-heading text-lg font-semibold">Acciones prioritarias</h3>
        <div className="space-y-3">
          {estructura.acciones_top3.map((a) => (
            <Card key={a.orden} className="overflow-hidden transition-shadow hover:shadow-md">
              <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/15 font-heading text-base font-bold text-accent">
                  {a.orden}
                </div>
                <div className="flex-1">
                  <p className="text-sm leading-snug">{a.texto}</p>
                  <Badge variant="outline" className="mt-1.5 text-[10px]">
                    Origen: {a.card_origen}
                  </Badge>
                </div>
                {a.cta_href && (
                  <Link href={a.cta_href}>
                    <Button variant="outline" size="sm" className="gap-1.5">
                      {a.cta_label}
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </Link>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function FactorBlock({
  titulo,
  icon,
  accent,
  items,
}: {
  titulo: string;
  icon: React.ReactNode;
  accent: "emerald" | "amber" | "rose";
  items: { card: string; titulo: string; evidencia: string }[];
}) {
  const accentBorder = {
    emerald: "border-emerald-500/30",
    amber: "border-amber-500/30",
    rose: "border-rose-500/30",
  }[accent];
  return (
    <Card className={`border ${accentBorder}`}>
      <CardContent className="p-4">
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider">
          {icon}
          {titulo}
        </h4>
        <ul className="space-y-2.5">
          {items.map((it, idx) => (
            <li key={idx} className="space-y-0.5">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono text-[10px]">
                  {it.card}
                </Badge>
                <span className="text-sm font-medium">{it.titulo}</span>
              </div>
              <p className="pl-1 text-xs leading-relaxed text-muted-foreground">{it.evidencia}</p>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function DiagnosticoLegacy({ plan }: { plan: PlanIA }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-2 flex items-center justify-between">
          <Badge variant="outline">Versión legacy (pre-Concepto 3)</Badge>
          <span className="text-xs text-muted-foreground">
            {new Date(plan.created_at).toLocaleDateString("es-MX")}
          </span>
        </div>
        <pre className="whitespace-pre-wrap text-sm leading-relaxed">{plan.contenido}</pre>
      </CardContent>
    </Card>
  );
}

function EmptyDiagnostico() {
  return (
    <Card className="border-dashed">
      <CardContent className="p-10 text-center">
        <Stethoscope className="mx-auto h-12 w-12 text-muted-foreground/40" />
        <h3 className="mt-4 font-heading text-lg font-semibold">Listo para analizar</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          Aún no hay diagnóstico estratégico generado para este dirigente. El análisis sintetizará
          los 18 indicadores del módulo Diagnóstico + Diferenciadores en un score IPD con
          fortalezas, debilidades, riesgos y acciones prioritarias.
        </p>
        <p className="mx-auto mt-4 max-w-md text-xs text-muted-foreground">
          La generación se ejecuta desde el script{" "}
          <code className="rounded bg-muted px-1.5 py-0.5">regen_diagnostico_v2.py</code> · próximo
          sprint integramos el CTA aquí.
        </p>
      </CardContent>
    </Card>
  );
}

function EmptyTabState({
  icon,
  titulo,
  descripcion,
}: {
  icon: React.ReactNode;
  titulo: string;
  descripcion: string;
}) {
  return (
    <Card className="border-dashed">
      <CardContent className="p-10 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center">{icon}</div>
        <h3 className="mt-4 font-heading text-lg font-semibold">{titulo}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">{descripcion}</p>
      </CardContent>
    </Card>
  );
}

/* ─────── Tab Estrategia ─────── */

function EstrategiaTab({ dirigenteId }: { dirigenteId: number }) {
  const { data, isLoading } = usePlanes(undefined, 1);
  const planes = useMemo(
    () =>
      (data?.items ?? [])
        .filter((p) => p.tipo === "CONSOLIDACION" && p.dirigente_id === dirigenteId)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [data, dirigenteId],
  );

  if (isLoading) return <Skeleton className="h-[60vh]" />;
  const vigente = planes[0];
  if (!vigente) {
    return (
      <EmptyTabState
        icon={<Target className="h-12 w-12 text-muted-foreground/50" />}
        titulo="Plan 90 días"
        descripcion="Aún no hay plan estratégico generado. La estrategia trimestral se construye a partir del Diagnóstico vigente."
      />
    );
  }
  const estr = vigente.estructura_json as ConsolidacionEstructura | undefined;
  if (!estr?.resumen_ejecutivo) {
    return (
      <Card>
        <CardContent className="p-5 text-sm text-muted-foreground">
          Plan legacy sin estructura · {vigente.contenido?.slice(0, 200)}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Hero · resumen + objetivo */}
      <Card className="border-l-4 border-l-emerald-500 bg-emerald-500/5">
        <CardContent className="p-5">
          <Badge variant="outline" className="mb-2 border-emerald-500/40 text-emerald-700 dark:text-emerald-300">
            Plan 90 días · Generado {new Date(vigente.created_at).toLocaleDateString("es-MX")}
          </Badge>
          <p className="font-heading text-lg font-medium leading-snug">{estr.resumen_ejecutivo}</p>
          {estr.objetivo_90d?.narrativa && (
            <p className="mt-3 text-sm text-muted-foreground">
              <span className="font-semibold">Objetivo:</span> {estr.objetivo_90d.narrativa}
            </p>
          )}
        </CardContent>
      </Card>

      {/* KPIs target */}
      {estr.objetivo_90d?.kpis_target && estr.objetivo_90d.kpis_target.length > 0 && (
        <div>
          <h3 className="mb-3 font-heading text-base font-semibold">KPIs objetivo del trimestre</h3>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {estr.objetivo_90d.kpis_target.map((k, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <div className="text-xs uppercase tracking-wider text-muted-foreground">{k.metrica}</div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="font-heading text-2xl font-bold tabular-nums">
                      {k.valor_target}
                    </span>
                    <span className="text-xs text-muted-foreground">{k.unidad}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    de {k.valor_baseline} {k.unidad} baseline
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Narrativa central */}
      <Card>
        <CardContent className="p-5">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider">
            <Megaphone className="h-4 w-4" /> Narrativa central
          </h3>
          <p className="text-base leading-snug">{estr.narrativa_central}</p>
        </CardContent>
      </Card>

      {/* 3 Pilares */}
      <div>
        <h3 className="mb-3 font-heading text-base font-semibold">3 pilares estratégicos</h3>
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {estr.pilares.map((p, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="mb-2 flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent">
                    {i + 1}
                  </span>
                  <h4 className="font-semibold">{p.titulo}</h4>
                </div>
                <p className="text-sm text-muted-foreground">{p.descripcion}</p>
                {p.tacticas && p.tacticas.length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {p.tacticas.map((t, j) => (
                      <li key={j} className="text-xs text-foreground/80">
                        ▸ {t}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Roadmap 3 hitos */}
      <div>
        <h3 className="mb-3 font-heading text-base font-semibold">Roadmap trimestre</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {estr.roadmap_3_hitos.map((h) => (
            <Card key={h.mes} className="relative">
              <CardContent className="p-4">
                <Badge variant="outline" className="mb-2">
                  Mes {h.mes}
                </Badge>
                <p className="text-sm font-medium">{h.hito}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  <span className="font-semibold">KPI:</span> {h.kpi_control}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Audiencias prioritarias */}
      {estr.audiencias_prioritarias && estr.audiencias_prioritarias.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider">
              <Users className="h-4 w-4" /> Audiencias prioritarias
            </h3>
            <ul className="space-y-2">
              {estr.audiencias_prioritarias.map((a, i) => (
                <li key={i} className="border-l-2 border-accent/30 pl-3">
                  <span className="font-semibold">{a.nombre}</span> · {a.rationale}
                  <p className="mt-1 text-xs text-muted-foreground">{a.tactica_clave}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Riesgos */}
      {estr.riesgos && estr.riesgos.length > 0 && (
        <Card className="border-rose-500/30">
          <CardContent className="p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-rose-500">
              <AlertTriangle className="h-4 w-4" /> Riesgos del trimestre
            </h3>
            <ul className="space-y-2">
              {estr.riesgos.map((r, i) => (
                <li key={i} className="text-sm">
                  <Badge variant="outline" className="mr-2 text-[10px] uppercase">
                    {r.tipo}
                  </Badge>
                  {r.descripcion}
                  <p className="mt-0.5 pl-1 text-xs text-muted-foreground">
                    <span className="font-semibold">Mitigación:</span> {r.mitigacion}
                  </p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ─────── Tab Contenido ─────── */

const PLAT_COLOR: Record<string, string> = {
  facebook: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  instagram: "bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300",
  twitter: "bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300",
  tiktok: "bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200",
  youtube: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
};

function ContenidoTab({ dirigenteId }: { dirigenteId: number }) {
  const { data, isLoading } = usePlanes(undefined, 1);
  const planes = useMemo(
    () =>
      (data?.items ?? [])
        .filter((p) => p.tipo === "CONTENIDO" && p.dirigente_id === dirigenteId)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [data, dirigenteId],
  );

  if (isLoading) return <Skeleton className="h-[60vh]" />;
  const vigente = planes[0];
  if (!vigente) {
    return (
      <EmptyTabState
        icon={<Calendar className="h-12 w-12 text-muted-foreground/50" />}
        titulo="Calendario Editorial"
        descripcion="Aún no hay calendario editorial generado. Próximas 4 semanas con cadencia, pilares, efemérides y posts sugeridos."
      />
    );
  }
  const estr = vigente.estructura_json as ContenidoEstructura | undefined;
  if (!estr?.ventana) {
    return (
      <Card>
        <CardContent className="p-5 text-sm text-muted-foreground">
          Plan legacy · {vigente.contenido?.slice(0, 200)}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="border-l-4 border-l-amber-500 bg-amber-500/5">
        <CardContent className="p-5">
          <Badge variant="outline" className="mb-2 border-amber-500/40 text-amber-700 dark:text-amber-300">
            Calendario Editorial
          </Badge>
          <p className="font-heading text-lg font-medium">
            {estr.ventana.inicio} → {estr.ventana.fin} · {estr.ventana.semanas} semanas
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Generado {new Date(vigente.created_at).toLocaleDateString("es-MX")} · modelo{" "}
            {vigente.modelo_ia}
          </p>
        </CardContent>
      </Card>

      {/* Cadencia recomendada */}
      <div>
        <h3 className="mb-3 font-heading text-base font-semibold">Cadencia recomendada</h3>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {Object.entries(estr.cadencia_recomendada).map(([plat, val]) => (
            <Card key={plat}>
              <CardContent className="p-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">{plat}</div>
                <div className="mt-1 text-sm font-medium">{val}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Pilares editoriales */}
      <div>
        <h3 className="mb-3 font-heading text-base font-semibold">Pilares editoriales</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {estr.pilares_editoriales.map((p, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="font-semibold">{p.titulo}</h4>
                  <Badge variant="outline">{p.frecuencia_semanal_pct}%</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{p.descripcion}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Posts sugeridos · grid */}
      <div>
        <h3 className="mb-3 font-heading text-base font-semibold">
          {estr.posts_sugeridos.length} posts sugeridos
        </h3>
        <div className="space-y-3">
          {estr.posts_sugeridos.map((p, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {p.fecha_sugerida} · {p.hora_optima}
                  </Badge>
                  <Badge className={PLAT_COLOR[p.plataforma] ?? "bg-muted"}>{p.plataforma}</Badge>
                  <Badge variant="outline">{p.tipo}</Badge>
                  <Badge variant="outline" className="text-[10px]">
                    {p.tono}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    Pilar: <span className="font-semibold">{p.pilar}</span>
                  </span>
                </div>
                <p className="text-sm leading-snug">{p.copy}</p>
                {p.hashtags && p.hashtags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {p.hashtags.map((h, j) => (
                      <span key={j} className="text-xs text-accent">
                        <Hash className="inline h-3 w-3" />
                        {h.replace(/^#/, "")}
                      </span>
                    ))}
                  </div>
                )}
                {p.rationale && (
                  <p className="mt-2 text-xs italic text-muted-foreground">
                    <Sparkles className="mr-1 inline h-3 w-3" />
                    {p.rationale}
                  </p>
                )}
                {p.cta_label && (
                  <div className="mt-3">
                    <Button variant="outline" size="sm" className="gap-1.5">
                      {p.cta_label}
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Veda warnings */}
      {estr.veda_warnings && estr.veda_warnings.length > 0 && (
        <Card className="border-rose-500/40 bg-rose-500/5">
          <CardContent className="p-4">
            <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-rose-500">
              <AlertTriangle className="h-4 w-4" /> Veda electoral
            </h3>
            {estr.veda_warnings.map((v, i) => (
              <p key={i} className="text-sm">
                <span className="font-semibold">
                  {v.fecha_inicio} → {v.fecha_fin}:
                </span>{" "}
                {v.descripcion}
              </p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function PlanesPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[60vh] w-full" />}>
      <PlanesInner />
    </Suspense>
  );
}
