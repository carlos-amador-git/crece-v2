"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

export interface StepDef {
  index: number;
  label: string;
  short: string;
  optional?: boolean;
}

export const STEPS: StepDef[] = [
  { index: 1, label: "Perfil", short: "Perfil" },
  { index: 2, label: "Cuentas manuales", short: "Cuentas" },
  { index: 3, label: "SERP asistido", short: "SERP", optional: true },
  { index: 4, label: "Validación Apify", short: "Validar" },
  { index: 5, label: "Confirmación humana", short: "Confirmar" },
  { index: 6, label: "OAuth oficial", short: "OAuth", optional: true },
  { index: 7, label: "Competidores", short: "Competidores" },
  { index: 8, label: "Promesas", short: "Promesas" },
  { index: 9, label: "Activación", short: "Activar" },
];

export function Stepper({
  current,
  onStepClick,
}: {
  current: number;
  onStepClick: (i: number) => void;
}) {
  const pct = Math.round(((current - 1) / (STEPS.length - 1)) * 100);

  return (
    <div className="space-y-4" data-testid="stepper">
      {/* Progress bar + mobile indicator */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span data-testid="stepper-label-current">
            Paso {current} de {STEPS.length} · {STEPS[current - 1]?.label}
          </span>
          <span className="font-mono tabular-nums">{pct}%</span>
        </div>
        <Progress value={pct} aria-label="Progreso del onboarding" />
      </div>

      {/* Desktop stepper — dots with labels */}
      <ol className="hidden grid-cols-9 gap-1 md:grid" role="list">
        {STEPS.map((s) => {
          const state =
            s.index < current ? "done" : s.index === current ? "active" : "future";
          return (
            <li key={s.index} className="flex flex-col items-center gap-1">
              <button
                type="button"
                onClick={() => onStepClick(s.index)}
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition-colors",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                  state === "done" && "border-emerald-500 bg-emerald-500 text-white",
                  state === "active" &&
                    "border-accent bg-accent text-accent-foreground shadow-md",
                  state === "future" &&
                    "border-border bg-muted/40 text-muted-foreground",
                )}
                aria-current={state === "active" ? "step" : undefined}
                aria-label={`Paso ${s.index}: ${s.label}`}
                data-testid={`stepper-dot-${s.index}`}
              >
                {state === "done" ? <Check className="h-4 w-4" /> : s.index}
              </button>
              <span
                className={cn(
                  "text-center text-[10px] leading-tight",
                  state === "active"
                    ? "font-medium text-foreground"
                    : "text-muted-foreground",
                )}
              >
                {s.short}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
