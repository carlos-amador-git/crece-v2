"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { CrecimientoPlatform } from "@/lib/api/hooks/use-dirigentes";
import { AlertTriangle } from "lucide-react";

interface Props {
  platforms: CrecimientoPlatform[];
}

const SEMAFORO_CLASS: Record<CrecimientoPlatform["semaforo"], string> = {
  verde: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  ambar: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  rojo: "bg-red-500/10 text-red-600 dark:text-red-400",
  desconocido: "bg-muted text-muted-foreground",
};

const SEMAFORO_LABEL: Record<CrecimientoPlatform["semaforo"], string> = {
  verde: "Mejorando",
  ambar: "Estable",
  rojo: "Decayendo",
  desconocido: "Necesita 7d más",
};

const SEMAFORO_TOOLTIP: Record<CrecimientoPlatform["semaforo"], string> = {
  verde: "Crecimiento ≥ +1% en 30d vs 30d anteriores",
  ambar: "Cambio entre -1% y +1% en 30d (estable)",
  rojo: "Decaimiento ≤ -1% en 30d vs 30d anteriores",
  desconocido:
    "Necesitamos al menos 7 días más de snapshots para comparar. El cron de followers empezó hoy — los próximos días llenarán la serie.",
};

export function SemaforoCrecimiento({ platforms }: Props) {
  if (platforms.length === 0) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Aún no hay perfiles registrados.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="card-elevated">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-base">
          ¿Estoy mejorando o decayendo?
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Compara 30 días actuales vs. 30 días anteriores (followers promedio).
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {platforms.map((p) => (
          <div
            key={p.platform}
            className="flex items-center justify-between rounded-md border p-3"
          >
            <div className="flex flex-col">
              <span className="text-sm font-medium capitalize">
                {p.platform.toLowerCase()}
              </span>
              <span className="text-xs text-muted-foreground">
                {p.followers_now.toLocaleString("es-MX")} followers
                {p.delta_pct["30d"] !== null && (
                  <>
                    {" · "}
                    {p.delta_pct["30d"] > 0 ? "+" : ""}
                    {p.delta_pct["30d"]}% en 30d
                  </>
                )}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {p.stale_manual && (
                <Badge
                  variant="outline"
                  className="gap-1.5 border-amber-500/50 bg-amber-500/15 font-medium text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                  title={`Última actualización manual: ${p.last_manual_update ?? "nunca"}`}
                >
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-500 opacity-75" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-500" />
                  </span>
                  <AlertTriangle className="h-3 w-3" />
                  {">48h sin update"}
                </Badge>
              )}
              <Badge
                className={SEMAFORO_CLASS[p.semaforo]}
                title={SEMAFORO_TOOLTIP[p.semaforo]}
              >
                {SEMAFORO_LABEL[p.semaforo]}
              </Badge>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
