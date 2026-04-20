"use client";

import { AlertTriangle, ShieldCheck } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useWizardStore } from "@/lib/api/hooks/use-onboarding";

/**
 * Regla D-23 (dura): confirmación humana OBLIGATORIA antes de activar scraping.
 * El wizard NO permite avanzar al paso 6 sin al menos una cuenta confirmada.
 */
export function Step5ConfirmacionHumana() {
  const { validations, confirmations, toggleConfirmation } = useWizardStore();

  const atLeastOneConfirmed = Object.values(confirmations).some(Boolean);

  return (
    <div className="space-y-6" data-testid="step-5-confirmation">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 5 de 9 · Regla dura
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          Confirmación humana obligatoria
        </h2>
        <p className="text-sm text-muted-foreground">
          Esta es la única forma de proteger al dirigente de scrapear a la persona
          incorrecta. Marca cada cuenta que SÍ es suya. Sin confirmación, no
          activamos scraping.
        </p>
      </header>

      {validations.length === 0 ? (
        <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          No hay cuentas validadas. Regresa al paso 2 para capturar URLs.
        </div>
      ) : (
        <div className="space-y-3">
          {validations.map((v) => {
            const key = `${v.platform}:${v.handle}`;
            const checked = Boolean(confirmations[key]);
            return (
              <Card
                key={key}
                className={
                  checked
                    ? "border-emerald-500/40 bg-emerald-500/5"
                    : "border-border"
                }
              >
                <CardContent className="flex items-start gap-3 p-4">
                  <Checkbox
                    id={`confirm-${key}`}
                    data-testid={`confirm-${v.platform}`}
                    checked={checked}
                    onCheckedChange={() => toggleConfirmation(key)}
                    className="mt-1"
                  />
                  <Label
                    htmlFor={`confirm-${key}`}
                    className="flex-1 cursor-pointer space-y-1"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="text-[10px]">
                        {v.platform}
                      </Badge>
                      <span className="font-mono text-sm">@{v.handle}</span>
                      <span className="text-xs text-muted-foreground">
                        {v.followers?.toLocaleString() ?? "—"} seg.
                      </span>
                    </div>
                    <p className="text-sm font-semibold">
                      {v.full_name ?? "(sin nombre)"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Confirmo que esta es la cuenta correcta del dirigente.
                    </p>
                  </Label>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {!atLeastOneConfirmed && validations.length > 0 && (
        <div
          className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-sm text-amber-800 dark:text-amber-300"
          role="alert"
          data-testid="confirmation-required-warning"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Marca al menos una cuenta antes de continuar al paso de activación
            (regla D-23).
          </span>
        </div>
      )}

      {atLeastOneConfirmed && (
        <div
          className="flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm text-emerald-700 dark:text-emerald-300"
          data-testid="confirmation-ok"
        >
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Podemos activar scraping con las cuentas confirmadas.</span>
        </div>
      )}
    </div>
  );
}
