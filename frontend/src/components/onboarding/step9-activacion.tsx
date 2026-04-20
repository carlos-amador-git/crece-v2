"use client";

import {
  CheckCircle2,
  FileSignature,
  Loader2,
  Rocket,
  ShieldCheck,
  Signal,
  Target,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  useActivate,
  useWizardStore,
  type OnboardingPlatform,
} from "@/lib/api/hooks/use-onboarding";

const PERFIL_LABEL: Record<string, string> = {
  politico_activo: "Político activo",
  funcionario: "Funcionario",
  precampana: "Precampaña",
  empresario: "Empresario",
};

function tierFromConfirmed(
  platform: OnboardingPlatform,
  oauthStatus: string | undefined,
  hasConfirmed: boolean,
): "T1" | "T2" | "T3" | "—" {
  if (!hasConfirmed) return "—";
  if (oauthStatus === "live") return "T1";
  if (platform === "TWITTER") return "T3";
  return "T2";
}

export function Step9Activacion({ dirigenteId }: { dirigenteId: number }) {
  const {
    perfil,
    manualAccounts,
    validations,
    confirmations,
    oauthStatuses,
    competidores,
    promesas,
    activated,
    setActivated,
  } = useWizardStore();

  const activate = useActivate(dirigenteId);

  const confirmedByPlatform: Partial<Record<OnboardingPlatform, boolean>> = {};
  validations.forEach((v) => {
    const key = `${v.platform}:${v.handle}`;
    if (confirmations[key]) confirmedByPlatform[v.platform] = true;
  });

  const handleActivate = () => {
    activate.mutate(undefined, {
      onSuccess: () => setActivated(true),
    });
  };

  return (
    <div className="space-y-6" data-testid="step-9-activation">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 9 de 9 · Último paso
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          Resumen y activación
        </h2>
        <p className="text-sm text-muted-foreground">
          Revisa todo antes de disparar el scraping. Todo es editable regresando
          en el stepper.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Target className="h-4 w-4 text-accent" />
              Perfil
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {perfil ? PERFIL_LABEL[perfil] : "(no definido)"}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4 text-accent" />
              Competidores
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {competidores.length} registrado{competidores.length === 1 ? "" : "s"}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <FileSignature className="h-4 w-4 text-accent" />
              Promesas
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {promesas.length} registrada{promesas.length === 1 ? "" : "s"}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldCheck className="h-4 w-4 text-accent" />
              Cuentas confirmadas
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {Object.values(confirmations).filter(Boolean).length} de{" "}
            {validations.length}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Signal className="h-4 w-4 text-accent" />
            Data fidelity tier preview
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(["INSTAGRAM", "FACEBOOK", "TWITTER", "TIKTOK", "YOUTUBE"] as const).map(
            (p) => {
              const t = tierFromConfirmed(
                p,
                oauthStatuses[p],
                Boolean(confirmedByPlatform[p]),
              );
              return (
                <div
                  key={p}
                  className="flex items-center justify-between text-sm"
                  data-testid={`tier-${p}`}
                >
                  <span className="font-mono text-xs text-muted-foreground">
                    {p}
                  </span>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {t}
                  </Badge>
                </div>
              );
            },
          )}
        </CardContent>
      </Card>

      {activated ? (
        <div
          className="flex items-center gap-3 rounded-md border border-emerald-500/40 bg-emerald-500/5 p-4 text-sm text-emerald-800 dark:text-emerald-300"
          data-testid="activation-success"
        >
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Cuenta activada</p>
            <p className="text-xs">
              El scraping inicial está corriendo. Verás el primer dashboard en
              ~15 minutos.
            </p>
          </div>
        </div>
      ) : (
        <Button
          size="lg"
          className="w-full"
          onClick={handleActivate}
          disabled={activate.isPending || manualAccounts.length === 0}
          data-testid="btn-activar-cuenta"
        >
          {activate.isPending ? (
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          ) : (
            <Rocket className="mr-2 h-5 w-5" />
          )}
          Activar cuenta y empezar scraping
        </Button>
      )}
    </div>
  );
}
