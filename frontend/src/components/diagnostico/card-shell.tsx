"use client";

import { Info, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
}: CardShellProps) {
  const insufficient = status === "insufficient_data";

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
          </div>
          <CardTitle className="mt-1 line-clamp-2 font-heading text-sm font-semibold leading-tight">
            {title}
          </CardTitle>
        </div>
        <TooltipProvider delayDuration={150}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label={`Acerca de ${title}`}
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground/70 transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <Info className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="left" className="max-w-[260px] text-xs">
              {pregunta}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-3 pt-0">
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
          <>
            {children}
            {warnings && warnings.length > 0 && (
              <p className="text-[10px] italic text-muted-foreground/80">
                {warnings[0]}
              </p>
            )}
          </>
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
