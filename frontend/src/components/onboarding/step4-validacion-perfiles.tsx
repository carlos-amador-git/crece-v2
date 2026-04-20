"use client";

import {
  BadgeCheck,
  CheckCircle2,
  Loader2,
  RotateCcw,
  ShieldAlert,
  Users,
} from "lucide-react";
import { useEffect, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  useValidateAccount,
  useWizardStore,
  type ProfileValidation,
} from "@/lib/api/hooks/use-onboarding";
import { cn } from "@/lib/utils";

function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  const tone =
    score >= 0.7
      ? { bar: "bg-emerald-500", text: "text-emerald-700 dark:text-emerald-300" }
      : score >= 0.4
        ? { bar: "bg-amber-500", text: "text-amber-700 dark:text-amber-300" }
        : { bar: "bg-rose-500", text: "text-rose-700 dark:text-rose-300" };
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-32 overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full transition-all", tone.bar)}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <span className={cn("font-mono text-xs font-semibold tabular-nums", tone.text)}>
        {score.toFixed(2)}
      </span>
    </div>
  );
}

export function Step4ValidacionPerfiles({ dirigenteId }: { dirigenteId: number }) {
  const { manualAccounts, validations, setValidations } = useWizardStore();
  const validate = useValidateAccount(dirigenteId);

  const pending = useMemo(
    () =>
      manualAccounts.filter(
        (a) => !validations.find((v) => v.platform === a.platform && v.url === a.url),
      ),
    [manualAccounts, validations],
  );

  useEffect(() => {
    // Auto-dispara validaciones pendientes al entrar al paso
    if (pending.length === 0) return;
    let cancelled = false;
    (async () => {
      for (const acc of pending) {
        if (cancelled) break;
        try {
          const res = (await validate.mutateAsync(acc)) as ProfileValidation;
          if (cancelled) break;
          setValidations([
            ...useWizardStore.getState().validations.filter(
              (v) => !(v.platform === res.platform && v.url === res.url),
            ),
            res,
          ]);
        } catch {
          // continúa con el siguiente
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manualAccounts.length]);

  const revalidate = async (platform: string, url: string) => {
    const acc = manualAccounts.find((a) => a.platform === platform && a.url === url);
    if (!acc) return;
    const res = (await validate.mutateAsync(acc)) as ProfileValidation;
    setValidations([
      ...validations.filter((v) => !(v.platform === res.platform && v.url === res.url)),
      res,
    ]);
  };

  if (manualAccounts.length === 0) {
    return (
      <div className="space-y-6" data-testid="step-4-validation">
        <header className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-accent">
            Paso 4 de 9
          </p>
          <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
            Validación de perfiles
          </h2>
        </header>
        <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          Regresa al paso 2 para capturar al menos una URL.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="step-4-validation">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 4 de 9
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          Verificamos cada cuenta con Apify
        </h2>
        <p className="text-sm text-muted-foreground">
          Score ≥0.7 = alta confianza · 0.4-0.7 = revisar · &lt;0.4 = posible mismatch.
        </p>
      </header>

      <div className="space-y-3">
        {manualAccounts.map((acc) => {
          const v = validations.find(
            (x) => x.platform === acc.platform && x.url === acc.url,
          );
          const isValidating =
            !v && validate.isPending && validate.variables?.url === acc.url;

          return (
            <Card key={`${acc.platform}-${acc.url}`}>
              <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px]">
                      {acc.platform}
                    </Badge>
                    {v?.verified && (
                      <Badge className="gap-1 bg-sky-500/10 text-sky-700 border-sky-500/30 dark:text-sky-300">
                        <BadgeCheck className="h-3 w-3" />
                        Verificado
                      </Badge>
                    )}
                  </div>
                  {isValidating ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Validando…
                    </div>
                  ) : v ? (
                    <div className="space-y-1">
                      <p className="font-heading text-sm font-semibold">
                        {v.full_name ?? "(sin nombre)"}
                      </p>
                      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          {v.followers?.toLocaleString() ?? "—"} seguidores
                        </span>
                        <span className="font-mono">@{v.handle}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <ShieldAlert className="h-4 w-4 text-rose-500" />
                      <span>Pendiente de validar</span>
                    </div>
                  )}
                </div>

                {v && (
                  <div className="flex items-center gap-3">
                    <ScoreBar score={v.score} />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => revalidate(acc.platform, acc.url)}
                      data-testid={`btn-revalidate-${acc.platform}`}
                      aria-label="Revalidar"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {validations.length > 0 && validations.every((v) => v.score >= 0.7) && (
        <div
          className="flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm text-emerald-700 dark:text-emerald-300"
          data-testid="all-validated-ok"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Todas las cuentas pasaron el umbral de confianza.</span>
        </div>
      )}
    </div>
  );
}
