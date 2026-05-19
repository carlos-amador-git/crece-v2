"use client";

import Link from "next/link";
import { Info, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface CardShellProps {
  code: string; // B01..B10
  title: string;
  pregunta: string;
  fidelity?: string; // p.ej. "T1" | "T2" | "T3_proxy"
  status: "ok" | "insufficient_data";
  missing?: string[];
  warnings?: string[];
  testId: string;
  children: React.ReactNode;
  className?: string;
  persistentBanner?: React.ReactNode;
  signal?: {
    label: string;
    variant: "positive" | "negative" | "warning" | "neutral";
  };
  /**
   * Notas técnicas detalladas que se muestran SOLO en el Popover del ícono Info,
   * fuera del flujo principal. Reduce carga cognitiva en el view default.
   */
  technicalNotes?: React.ReactNode;
  /**
   * Cuando true, atenúa visualmente el contenido (opacidad + saturación reducida)
   * para indicar que la métrica está en calibración. La info se sigue mostrando
   * para no perder señal relativa pero NO compite con cards confiables.
   */
  calibrating?: boolean;
}

export function CardShell({
  code,
  title,
  pregunta,
  fidelity,
  status,
  missing,
  warnings,
  testId,
  children,
  className,
  persistentBanner,
  signal,
  technicalNotes,
  calibrating,
}: CardShellProps) {
  const insufficient = status === "insufficient_data";

  const signalStyles = {
    positive: "bg-[hsl(var(--chart-positive))]/10 text-[hsl(var(--chart-positive))] border-[hsl(var(--chart-positive))]/20",
    negative: "bg-[hsl(var(--chart-negative))]/10 text-[hsl(var(--chart-negative))] border-[hsl(var(--chart-negative))]/20",
    warning: "bg-amber-500/10 text-amber-600 border-amber-500/20",
    neutral: "bg-muted text-muted-foreground border-border",
  };

  return (
    <Card
      className={cn(
        "card-elevated flex flex-col overflow-hidden border-border/60 shadow-sm",
        insufficient && "opacity-95",
        className,
      )}
      data-testid={testId}
      data-status={status}
    >
      <CardHeader className="flex flex-row items-start gap-2 space-y-0 pb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="font-heading text-[10px] font-semibold uppercase tracking-wider text-muted-foreground tabular-nums"
              aria-label={`Bloque ${code}`}
            >
              {code}
            </span>
            {fidelity && (
              <Badge
                variant="outline"
                className="h-4 px-1.5 text-[9px] font-medium uppercase tracking-wide"
              >
                {fidelity}
              </Badge>
            )}
            {signal && !insufficient && (
              <Badge
                variant="outline"
                className={cn(
                  "h-4 px-1.5 text-[9px] font-bold uppercase tracking-wide border",
                  signalStyles[signal.variant]
                )}
              >
                {signal.label}
              </Badge>
            )}
          </div>
          <CardTitle className="mt-1 line-clamp-2 font-heading text-sm font-semibold leading-tight">
            {title}
          </CardTitle>
        </div>
        <Popover>
          <PopoverTrigger asChild>
            <button
              type="button"
              aria-label={`Acerca de ${title}`}
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground/70 transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <Info className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </PopoverTrigger>
          <PopoverContent side="left" align="start" className="text-xs space-y-2 max-w-sm">
            <p className="leading-snug">{pregunta}</p>
            {technicalNotes && (
              <div className="rounded-md border border-border/60 bg-muted/30 px-2 py-1.5 text-[11px] leading-snug text-muted-foreground">
                {technicalNotes}
              </div>
            )}
            <Link
              href={`/dashboard/sistema/metodologia#${code.toLowerCase()}`}
              className="inline-flex items-center gap-1 font-medium text-foreground hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring rounded"
            >
              Ver metodología en Configuración →
            </Link>
          </PopoverContent>
        </Popover>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-3 pt-0">
        {persistentBanner}
        {insufficient ? (
          <div
            className="flex flex-1 flex-col items-start justify-center gap-2 rounded-md border border-dashed border-border bg-muted/30 p-4"
            role="status"
            aria-live="polite"
            data-testid={`${testId}-insufficient`}
          >
            <div className="flex items-center gap-2 text-muted-foreground">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              <span className="text-xs font-medium">
                Datos insuficientes
              </span>
            </div>
            {missing && missing.length > 0 && (
              <ul className="space-y-0.5 text-[11px] leading-tight text-muted-foreground">
                {missing.slice(0, 2).map((m, i) => (
                  <li key={i} className="break-words">
                    {m}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div
            className={cn(
              "flex flex-1 flex-col gap-3",
              calibrating && "opacity-60 saturate-50",
            )}
            data-calibrating={calibrating ? "true" : undefined}
          >
            {children}
            {warnings && warnings.length > 0 && (
              <p className="text-[10px] italic text-muted-foreground/80">
                {warnings[0]}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Fallback/placeholder para métricas numéricas faltantes — NUNCA inventar números.
 */
export function EmptyMetric({ label = "—" }: { label?: string }) {
  return (
    <span className="font-heading text-3xl font-bold text-muted-foreground/40 tabular-nums">
      {label}
    </span>
  );
}
