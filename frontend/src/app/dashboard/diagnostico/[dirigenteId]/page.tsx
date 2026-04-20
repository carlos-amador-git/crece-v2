"use client";

import { AlertTriangle, ArrowLeft } from "lucide-react";
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
  CardB10,
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
            10 bloques Tier 1 MVP — rendimiento algorítmico y de audiencia (MASTER §3.1)
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
          <CardB10 bloque={data.bloques.B10_humanizacion} />
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
