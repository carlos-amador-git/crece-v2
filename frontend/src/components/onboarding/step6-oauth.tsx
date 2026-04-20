"use client";

import {
  AlertCircle,
  Clock,
  Facebook,
  Instagram,
  Loader2,
  Lock,
  Music2,
  Twitter,
  Youtube,
  Zap,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  useInitOAuth,
  useWizardStore,
  type OnboardingPlatform,
} from "@/lib/api/hooks/use-onboarding";

interface Row {
  id: OnboardingPlatform;
  label: string;
  icon: typeof Instagram;
  grayed?: boolean;
  reason?: string;
}

const ROWS: Row[] = [
  { id: "INSTAGRAM", label: "Instagram Business", icon: Instagram },
  { id: "FACEBOOK", label: "Facebook Page", icon: Facebook },
  { id: "TIKTOK", label: "TikTok Business", icon: Music2 },
  { id: "YOUTUBE", label: "YouTube (Google)", icon: Youtube },
  {
    id: "TWITTER",
    label: "X / Twitter",
    icon: Twitter,
    grayed: true,
    reason: "T3 permanente — D-19",
  },
];

export function Step6OAuth({ dirigenteId }: { dirigenteId: number }) {
  const { oauthStatuses, setOAuthStatus } = useWizardStore();
  const init = useInitOAuth(dirigenteId);

  const connect = (platform: OnboardingPlatform) => {
    init.mutate(platform, {
      onSuccess: (res) => {
        setOAuthStatus(platform, res.status);
      },
      onError: () => {
        setOAuthStatus(platform, "pending");
      },
    });
  };

  return (
    <div className="space-y-6" data-testid="step-6-oauth">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 6 de 9 · Opcional post-firma
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          Conecta OAuth oficial
        </h2>
        <p className="text-sm text-muted-foreground">
          El piloto funciona sin esto. OAuth sube tier a T1 con reach oficial.
          Puedes saltarlo y activarlo cuando firme el contrato.
        </p>
      </header>

      <div className="space-y-3">
        {ROWS.map(({ id, label, icon: Icon, grayed, reason }) => {
          const status = oauthStatuses[id] ?? "pending";
          const pending = init.isPending && init.variables === id;
          return (
            <Card
              key={id}
              className={grayed ? "opacity-60" : ""}
              data-testid={`oauth-row-${id}`}
            >
              <CardContent className="flex items-center justify-between gap-3 p-4">
                <div className="flex items-center gap-3">
                  <Icon className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">{label}</p>
                    {grayed ? (
                      <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Lock className="h-3 w-3" /> {reason}
                      </p>
                    ) : status === "stub" ? (
                      <p className="flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300">
                        <Clock className="h-3 w-3" /> Stub activo — pendiente Meta
                        App Review
                      </p>
                    ) : status === "live" ? (
                      <p className="flex items-center gap-1 text-xs text-emerald-700 dark:text-emerald-300">
                        <Zap className="h-3 w-3" /> Conectado · T1
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground">No conectado</p>
                    )}
                  </div>
                </div>

                {grayed ? (
                  <Badge variant="outline" className="text-[10px]">
                    Deshabilitado
                  </Badge>
                ) : status === "live" ? (
                  <Badge className="bg-emerald-500/10 text-emerald-700 border-emerald-500/30 dark:text-emerald-300">
                    Activo
                  </Badge>
                ) : (
                  <Button
                    size="sm"
                    variant={status === "stub" ? "outline" : "default"}
                    onClick={() => connect(id)}
                    disabled={pending}
                    data-testid={`btn-oauth-${id}`}
                  >
                    {pending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                    {status === "stub" ? "Reintentar" : "Conectar"}
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {init.isError && (
        <div
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
          role="alert"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>No se pudo iniciar el flujo OAuth. Puedes saltar y continuar.</span>
        </div>
      )}
    </div>
  );
}
