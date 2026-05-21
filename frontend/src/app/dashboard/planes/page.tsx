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
import type { PlanIA, DiagnosticoEstructura } from "@/lib/api/types";
import {
  Stethoscope,
  Target,
  Calendar,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  ArrowRight,
  Clock,
} from "lucide-react";
import Link from "next/link";

const TAB_VALUES = ["diagnostico", "estrategia", "contenido"] as const;
type TabKey = (typeof TAB_VALUES)[number];

function isAdminRole(role: string | undefined): boolean {
  return role === "admin" || role === "analyst";
}

function PlanesInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const tabParam = searchParams.get("tab");
  const initialTab: TabKey =
    TAB_VALUES.includes((tabParam ?? "") as TabKey) ? (tabParam as TabKey) : "diagnostico";

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
        <TabsList className="grid w-full grid-cols-3 lg:w-[600px]">
          <TabsTrigger value="diagnostico" className="gap-2">
            <Stethoscope className="h-4 w-4" /> Diagnóstico
          </TabsTrigger>
          <TabsTrigger value="estrategia" className="gap-2">
            <Target className="h-4 w-4" /> Estrategia
          </TabsTrigger>
          <TabsTrigger value="contenido" className="gap-2">
            <Calendar className="h-4 w-4" /> Contenido
          </TabsTrigger>
        </TabsList>

        <TabsContent value="diagnostico" className="mt-6">
          <DiagnosticoTab dirigenteId={selectedDirigenteId} />
        </TabsContent>

        <TabsContent value="estrategia" className="mt-6">
          <EmptyTabState
            icon={<Target className="h-12 w-12 text-muted-foreground/50" />}
            titulo="Plan 90 días"
            descripcion="Próximamente. La estrategia trimestral se generará a partir del diagnóstico vigente, los pilares editoriales y el contexto del corpus actualizado."
          />
        </TabsContent>

        <TabsContent value="contenido" className="mt-6">
          <EmptyTabState
            icon={<Calendar className="h-12 w-12 text-muted-foreground/50" />}
            titulo="Calendario Editorial"
            descripcion="Próximamente. Cadencia recomendada, efemérides relevantes y posts sugeridos por plataforma con tono y hora óptima."
          />
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

export default function PlanesPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[60vh] w-full" />}>
      <PlanesInner />
    </Suspense>
  );
}
