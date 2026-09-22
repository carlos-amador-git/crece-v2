"use client";

import { useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Eye,
  EyeOff,
  Megaphone,
  ScanSearch,
  ShieldAlert,
  Sparkles,
  Target,
  type LucideIcon,
} from "lucide-react";
import {
  useDiagnosticoTier2,
  type DiagnosticoTier2Response,
} from "@/lib/api/hooks/use-diagnostico-tier2";
import { useDiagnosticoTier1 } from "@/lib/api/hooks/use-diagnostico-tier1";
import { useDirigente } from "@/lib/api/hooks/use-dirigentes";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  CardB11,
  CardB12,
  CardB13,
  CardB14,
  CardB15,
  CardB16,
  CardB17,
  CardB18,
  CardTier2Skeleton,
} from "@/components/diagnostico_tier2/cards";

interface Props {
  params: { dirigenteId: string };
}

export default function DiagnosticoTier2Page({ params }: Props) {
  const { dirigenteId } = params;
  const numericId = Number.parseInt(dirigenteId, 10);
  const validId = !Number.isNaN(numericId);

  // Toggle global Filtro de Realidad (B13) — solicita ?recompute_tier1=true
  const [filtroActivo, setFiltroActivo] = useState(false);

  const { data, isLoading, isError, error } = useDiagnosticoTier2(
    validId ? numericId : undefined,
    filtroActivo,
  );

  // Traer Tier 1 baseline SIEMPRE para mostrar comparativa (antes/después del filtro).
  // El backend Tier 1 no cambia con el toggle — sólo muestra el ER actual como referencia.
  const { data: tier1 } = useDiagnosticoTier1(validId ? numericId : undefined);

  const { data: dirigente } = useDirigente(validId ? String(numericId) : "");

  const nombre = dirigente?.full_name ?? `Dirigente #${dirigenteId}`;
  const resumen = data?.resumen;
  // Primer bloque que declare su ventana. Todos los servicios Tier 2 usan la
  // misma constante VENTANA_DIAS, así que basta con el primero disponible.
  const ventanaDias: number | undefined = (() => {
    const bloques = data?.bloques as Record<string, { data?: { ventana_dias?: number } }> | undefined;
    if (!bloques) return undefined;
    for (const b of Object.values(bloques)) {
      const v = b?.data?.ventana_dias;
      if (typeof v === "number") return v;
    }
    return undefined;
  })();

  // ------- Cálculo del delta Tier 1 para demo del Filtro de Realidad -------
  const deltaTier1 = computeTier1Delta(tier1, data, filtroActivo);

  return (
    <div
      className={cn(
        "space-y-6 transition-colors",
        filtroActivo && "bg-[hsl(var(--chart-accent))]/[0.03] -mx-4 px-4 -my-4 py-4 rounded-lg",
      )}
      data-testid="page-diagnostico-tier2"
      data-filtro-activo={filtroActivo ? "true" : "false"}
    >
      {/* ---------- Header ---------- */}
      <header className="flex flex-col gap-3 border-b pb-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Button variant="ghost" size="sm" asChild className="-ml-2 h-7 px-2">
            <Link href="/dashboard/dirigentes" className="flex items-center gap-1">
              <ArrowLeft className="h-3 w-3" aria-hidden="true" />
              Dirigentes
            </Link>
          </Button>
          <span aria-hidden="true">/</span>
          <Link
            href={`/dashboard/diagnostico/${dirigenteId}`}
            className="hover:text-foreground transition-colors"
          >
            Diagnóstico Tier 1
          </Link>
          <span aria-hidden="true">/</span>
          <span>Diferenciadores Tier 2</span>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <Sparkles
                className="h-5 w-5 text-[hsl(var(--chart-accent))]"
                aria-hidden="true"
              />
              <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
                Diferenciadores · {nombre}
              </h1>
            </div>
            <p className="text-sm text-muted-foreground">
              8 bloques Tier 2 killer features (MASTER §3.2 #11-#18) — lo que ni
              Brandwatch ni Meltwater calculan
            </p>
            {/* La ventana de análisis se lee del payload, no se escribe fija:
                si VENTANA_DIAS cambia en el backend, la etiqueta acompaña.
                Sin esto, las tarjetas con datos no declaraban qué período
                cubren y podían leerse como "los últimos días". */}
            {ventanaDias != null && (
              <p
                className="text-xs text-muted-foreground"
                data-testid="tier2-ventana"
              >
                Ventana de análisis: últimos{" "}
                <span className="font-medium">{ventanaDias} días</span>
                {" · comentarios y posts publicados en ese período"}
              </p>
            )}
          </div>

          {resumen && (
            <div className="flex flex-wrap items-center gap-2" data-testid="resumen-badges">
              <Badge variant="default" className="gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
                {resumen.ok} / {resumen.total} con datos
              </Badge>
              {resumen.insufficient_data > 0 && (
                <Badge variant="outline" className="gap-1 text-muted-foreground">
                  <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                  {resumen.insufficient_data} insuficiente
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* ---------- Toggle Filtro de Realidad (B13 global) ---------- */}
        <div
          className={cn(
            "flex flex-col gap-2 rounded-lg border p-3 transition-colors sm:flex-row sm:items-center sm:justify-between",
            filtroActivo
              ? "border-[hsl(var(--chart-accent))]/50 bg-[hsl(var(--chart-accent))]/5"
              : "border-border/60 bg-muted/20",
          )}
          data-testid="filtro-realidad-toggle"
        >
          <div className="flex items-start gap-3">
            <Target
              className={cn(
                "h-5 w-5 shrink-0 mt-0.5",
                filtroActivo
                  ? "text-[hsl(var(--chart-accent))]"
                  : "text-muted-foreground",
              )}
              aria-hidden="true"
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-heading text-sm font-semibold">
                  Filtro de Realidad (B13)
                </span>
                <Badge
                  variant={filtroActivo ? "default" : "outline"}
                  className="text-[9px] px-1.5 py-0 h-4"
                >
                  {filtroActivo ? "ACTIVO" : "INACTIVO"}
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                {filtroActivo
                  ? "Excluye comments de authors flagged por B12 CIB Detector. Recalcula Tier 1 baseline con ER orgánico."
                  : "Activa para ver el impacto real excluyendo comportamiento inauténtico coordinado."}
              </p>

              {filtroActivo && deltaTier1 && (
                <div
                  className="mt-2 flex flex-wrap items-center gap-2 text-[11px]"
                  data-testid="delta-tier1"
                >
                  <span className="text-muted-foreground">Impacto Tier 1:</span>
                  <span className="font-mono tabular-nums">
                    ER {deltaTier1.erBaseline.toFixed(2)}%
                  </span>
                  <span className="text-muted-foreground">→</span>
                  <span
                    className={cn(
                      "font-mono tabular-nums font-semibold",
                      deltaTier1.deltaPct < 0
                        ? "text-[hsl(var(--chart-negative))]"
                        : "text-[hsl(var(--chart-positive))]",
                    )}
                    data-testid="delta-tier1-valor"
                  >
                    {deltaTier1.erFiltrado.toFixed(2)}%
                  </span>
                  <span className="text-muted-foreground">
                    · {deltaTier1.deltaPct >= 0 ? "+" : ""}
                    {deltaTier1.deltaPct.toFixed(2)}% ·{" "}
                    {deltaTier1.cibExcluidos} authors CIB excluidos
                  </span>
                </div>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={() => setFiltroActivo((v) => !v)}
            role="switch"
            aria-checked={filtroActivo}
            aria-label="Activar filtro de realidad"
            className={cn(
              "group inline-flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition-colors",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
              filtroActivo
                ? "bg-[hsl(var(--chart-accent))] text-[hsl(var(--chart-accent-foreground,0_0%_100%))] hover:opacity-90"
                : "border border-border bg-card hover:bg-muted",
            )}
            data-testid="filtro-realidad-btn"
          >
            {filtroActivo ? (
              <>
                <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                Viendo orgánico
              </>
            ) : (
              <>
                <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
                Activar filtro
              </>
            )}
          </button>
        </div>
      </header>

      {/* ---------- Error ---------- */}
      {isError && (
        <div
          className="flex items-start gap-3 rounded-md border border-destructive/50 bg-destructive/5 p-4 text-destructive"
          role="alert"
          data-testid="error-state"
        >
          <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true" />
          <div className="space-y-1">
            <p className="text-sm font-medium">No se pudo cargar el diagnóstico Tier 2</p>
            <p className="text-xs text-destructive/80">
              {(error as Error)?.message ?? "Error desconocido"}
            </p>
          </div>
        </div>
      )}

      {/* ---------- Loading ---------- */}
      {isLoading && (
        <div
          className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
          data-testid="loading-state"
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <CardTier2Skeleton key={i} />
          ))}
        </div>
      )}

      {/* ---------- Success: 8 cards agrupadas en 3 zonas ---------- */}
      {data && !isLoading && (
        <div className="space-y-8" data-testid="cards-grid-tier2">
          <ZonaSection
            id="autenticidad"
            icon={ScanSearch}
            titulo="Autenticidad"
            pregunta="¿Es real lo que pasa?"
            descripcion="Detecta amplificación inauténtica y excluye ruido coordinado del cálculo."
          >
            <CardB11 bloque={data.bloques.B11_cross_partisan} />
            <CardB12 bloque={data.bloques.B12_cib_detector} />
            <CardB13 bloque={data.bloques.B13_filtro_realidad} />
          </ZonaSection>

          <ZonaSection
            id="narrativa"
            icon={Megaphone}
            titulo="Narrativa"
            pregunta="¿Estamos comunicando bien?"
            descripcion="Mide si tu mensaje llega a la audiencia, qué temas dominan y si cumples lo prometido."
          >
            <CardB14 bloque={data.bloques.B14_topic_drift} />
            <CardB15 bloque={data.bloques.B15_rage_click} />
            <CardB16 bloque={data.bloques.B16_promesas} />
          </ZonaSection>

          <ZonaSection
            id="legal-riesgo"
            icon={ShieldAlert}
            titulo="Legal / Riesgo"
            pregunta="¿Estamos seguros?"
            descripcion="Cumplimiento veda electoral y vigilancia de violencia política en tus canales."
          >
            <CardB17 bloque={data.bloques.B17_veda_compliance} />
            <CardB18 bloque={data.bloques.B18_violencia_politica} />
          </ZonaSection>
        </div>
      )}

      {/* ---------- Footer ---------- */}
      {data && (
        <footer className="border-t pt-3 text-[11px] text-muted-foreground">
          Versión del cómputo: <span className="font-mono">{data.bloque_version}</span>
          {" · "}
          Dirigente ID: <span className="font-mono">{data.dirigente_id}</span>
          {filtroActivo && data.tier1_recomputed && (
            <>
              {" · "}
              <span className="text-[hsl(var(--chart-accent))]">
                Tier 1 recomputed con {data.tier1_recomputed.cib_hashes_excluidos.length}{" "}
                hashes CIB excluidos
              </span>
            </>
          )}
        </footer>
      )}
    </div>
  );
}

// -------------------------------------------------------------------------
// ZonaSection — agrupa cards Tier 2 por dominio temático (Autenticidad /
// Narrativa / Legal-Riesgo). Reduce las 8 cards independientes a 3 zonas
// escaneables visualmente (review CEO 2026-05-13 noche).
// -------------------------------------------------------------------------
interface ZonaSectionProps {
  id: string;
  icon: LucideIcon;
  titulo: string;
  pregunta: string;
  descripcion: string;
  children: React.ReactNode;
}

function ZonaSection({
  id,
  icon: Icon,
  titulo,
  pregunta,
  descripcion,
  children,
}: ZonaSectionProps) {
  return (
    <section
      id={`zona-${id}`}
      aria-labelledby={`zona-${id}-titulo`}
      data-testid={`zona-${id}`}
    >
      <header className="mb-3 flex items-start gap-3">
        <Icon
          className="mt-0.5 h-5 w-5 shrink-0 text-[hsl(var(--chart-accent))]"
          aria-hidden
        />
        <div className="min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h2
              id={`zona-${id}-titulo`}
              className="font-heading text-base font-semibold tracking-tight"
            >
              {titulo}
            </h2>
            <span className="text-xs text-muted-foreground italic">
              {pregunta}
            </span>
          </div>
          <p className="mt-0.5 text-[11px] text-muted-foreground leading-snug">
            {descripcion}
          </p>
        </div>
      </header>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {children}
      </div>
    </section>
  );
}

// -------------------------------------------------------------------------
// Helper: calcular delta ER Tier 1 baseline vs filtrado
// -------------------------------------------------------------------------
interface DeltaTier1 {
  erBaseline: number;
  erFiltrado: number;
  deltaPct: number;
  cibExcluidos: number;
}

function computeTier1Delta(
  tier1: { bloques?: { B01_er_normalizado?: { data?: { er_por_plataforma?: Record<string, { er_actual_pct?: number }> } } } } | undefined,
  tier2: DiagnosticoTier2Response | undefined,
  filtroActivo: boolean,
): DeltaTier1 | null {
  if (!filtroActivo || !tier1 || !tier2) return null;

  const erPlat = tier1.bloques?.B01_er_normalizado?.data?.er_por_plataforma;
  if (!erPlat) return null;

  const entries = Object.values(erPlat);
  const erBaseline =
    entries.reduce((acc, p) => acc + (p?.er_actual_pct ?? 0), 0) / (entries.length || 1);

  const b13 = tier2.bloques.B13_filtro_realidad?.data;
  if (!b13) return null;

  // Proxy de impacto: ER orgánico se reduce proporcionalmente al % de comments CIB.
  // Backend aclaró que el recompute real de B01 requiere desacoplar engagement por
  // author_hash (Sprint S4+). Hoy mostramos el delta como factor visible.
  const pctFlagged = b13.pct_comments_flagged ?? 0;
  const factor = 1 - pctFlagged / 100;
  const erFiltrado = erBaseline * factor;
  const deltaPct = erFiltrado - erBaseline;

  return {
    erBaseline,
    erFiltrado,
    deltaPct,
    cibExcluidos: tier2.tier1_recomputed?.cib_hashes_excluidos.length ?? b13.flagged_author_count ?? 0,
  };
}
