"use client";

import { AlertTriangle, ArrowLeft, Info } from "lucide-react";
import Link from "next/link";
import { useDiagnosticoTier1 } from "@/lib/api/hooks/use-diagnostico-tier1";
import { useDirigente } from "@/lib/api/hooks/use-dirigentes";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CardB01,
  CardB02,
  CardB03,
  CardB04,
  CardB05,
  CardB06,
  CardB07,
  CardB08,
  CardB09,
  CardB10WithDrilldown,
  CardSkeleton,
} from "@/components/diagnostico/cards";

interface Props {
  params: { dirigenteId: string };
}

export default function DiagnosticoPage({ params }: Props) {
  const { dirigenteId } = params;
  const numericId = Number.parseInt(dirigenteId, 10);

  const { data, isLoading, isError, error } = useDiagnosticoTier1(
    Number.isNaN(numericId) ? undefined : numericId,
  );
  const { data: dirigente } = useDirigente(
    Number.isNaN(numericId) ? "" : String(numericId),
  );

  // ----- Header -----
  const nombre = dirigente?.full_name ?? `Dirigente #${dirigenteId}`;
  const resumen = data?.resumen;

  return (
    <div className="space-y-6" data-testid="page-diagnostico-tier1">
      {/* Header */}
      <header className="flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Button variant="ghost" size="sm" asChild className="-ml-2 h-7 px-2">
              <Link href="/dashboard/dirigentes" className="flex items-center gap-1">
                <ArrowLeft className="h-3 w-3" aria-hidden="true" />
                Dirigentes
              </Link>
            </Button>
            <span aria-hidden="true">/</span>
            <span>Diagnóstico Tier 1</span>
          </div>
          <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
            Diagnóstico Digital · {nombre}
          </h1>
          <p className="text-sm text-muted-foreground">
            Cómo se comporta tu contenido: alcance, interacciones y tono percibido por la audiencia.
          </p>
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
      </header>

      {/* Contexto breve · lenguaje llano (antes: D-19 con referencias académicas) */}
      {data && !isLoading && (
        <div
          className="flex items-start gap-2.5 rounded-md border border-border/60 bg-muted/25 px-3.5 py-2.5 text-[12px] leading-snug"
          data-testid="tier1-contexto-d19"
        >
          <Info className="h-4 w-4 shrink-0 text-muted-foreground mt-0.5" aria-hidden="true" />
          <div className="space-y-0.5 text-muted-foreground">
            <p>
              Los rangos que ves aquí se comparan contra{" "}
              <span className="font-medium text-foreground">otros políticos mexicanos</span>
              {" "}de tu mismo tamaño de audiencia, no contra influencers comerciales. La política
              mexicana tiene menos interacción que el promedio comercial, así que los umbrales
              son específicos a este contexto.
            </p>
            <p className="text-[11px]">
              Un bloque en{" "}
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500 align-middle" aria-hidden="true" />{" "}
              rojo significa que estás por debajo de lo que logran políticos comparables,
              no que tu cuenta esté "mal" en abstracto.{" "}
              <a
                href="https://github.com/MarxCha/crece-v2/blob/main/backend/data/zenodo/v1/methodology.md"
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
              >
                Detalle técnico →
              </a>
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div
          className="flex items-start gap-3 rounded-md border border-destructive/50 bg-destructive/5 p-4 text-destructive"
          role="alert"
          data-testid="error-state"
        >
          <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true" />
          <div className="space-y-1">
            <p className="text-sm font-medium">No se pudo cargar el diagnóstico</p>
            <p className="text-xs text-destructive/80">
              {(error as Error)?.message ?? "Error desconocido"}
            </p>
          </div>
        </div>
      )}

      {/* Loading state — 10 skeletons */}
      {isLoading && (
        <div
          className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
          data-testid="loading-state"
        >
          {Array.from({ length: 10 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Success — 10 cards */}
      {data && !isLoading && (
        <div
          className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
          data-testid="cards-grid"
        >
          <CardB01 bloque={data.bloques.B01_er_normalizado} />
          <CardB02 bloque={data.bloques.B02_breakout_scale} />
          <CardB03 bloque={data.bloques.B03_matriz_2x2} />
          <CardB04 bloque={data.bloques.B04_benchmark} />
          <CardB05 bloque={data.bloques.B05_sentiment_plutchik} />
          <CardB06 bloque={data.bloques.B06_crisis_spike} />
          <CardB07 bloque={data.bloques.B07_growth_attribution} />
          <CardB08 bloque={data.bloques.B08_sov} />
          <CardB09 bloque={data.bloques.B09_share_like_ratio} />
          <CardB10WithDrilldown
            bloque={data.bloques.B10_humanizacion}
            dirigenteId={numericId}
          />
        </div>
      )}

      {/* Footer nota */}
      {data && (
        <footer className="border-t pt-3 text-[11px] text-muted-foreground">
          Versión del cómputo: <span className="font-mono">{data.bloque_version}</span>
          {" · "}
          Dirigente ID: <span className="font-mono">{data.dirigente_id}</span>
        </footer>
      )}
    </div>
  );
}
