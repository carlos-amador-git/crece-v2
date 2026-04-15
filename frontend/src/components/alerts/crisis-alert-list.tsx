"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { useBackendAlerts, type BackendAlert } from "@/hooks/use-crisis-alerts";

interface CrisisAlertListProps {
  limit?: number;
}

const SEVERITY_LABEL: Record<string, string> = {
  critica: "Crisis",
  alta: "Alta",
  media: "Media",
};

const SEVERITY_CLASS: Record<string, string> = {
  critica: "border-rose-500/30 bg-rose-500/5",
  alta: "border-amber-500/30 bg-amber-500/5",
  media: "border-yellow-500/30 bg-yellow-500/5",
};

const BADGE_CLASS: Record<string, string> = {
  critica: "bg-rose-500/15 text-rose-400 border-rose-500/30",
  alta: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  media: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
};

function AlertRow({ alert }: { alert: BackendAlert }) {
  const sev = alert.severidad ?? "media";
  return (
    <div className={`flex items-start gap-3 rounded-lg border p-3 ${SEVERITY_CLASS[sev]}`}>
      <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${sev === "critica" ? "text-rose-400" : sev === "alta" ? "text-amber-400" : "text-yellow-400"}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={`text-xs ${BADGE_CLASS[sev]}`}>
            {SEVERITY_LABEL[sev] ?? sev}
          </Badge>
        </div>
        <p className="mt-1 text-sm text-foreground/80">{alert.descripcion}</p>
      </div>
    </div>
  );
}

export function CrisisAlertList({ limit = 5 }: CrisisAlertListProps) {
  const { data: alerts, isLoading, isError } = useBackendAlerts();

  const active = (alerts ?? []).filter((a) => a.estado === "abierta");
  const visibleAlerts = active.slice(0, limit);
  const totalCount = active.length;

  return (
    <section aria-label="Alertas de crisis activas">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-base">Alertas de Crisis</CardTitle>
          {!isLoading && totalCount > 0 && (
            <Badge variant="danger">
              {totalCount} activa{totalCount !== 1 ? "s" : ""}
            </Badge>
          )}
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          {isLoading && <AlertListSkeleton />}

          {isError && !isLoading && (
            <p className="py-6 text-center text-sm text-destructive">
              Error al cargar alertas.
            </p>
          )}

          {!isLoading && !isError && visibleAlerts.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <ShieldCheck className="mb-3 h-10 w-10 text-emerald-500/50" />
              <p className="text-sm font-medium text-muted-foreground">Sin alertas activas</p>
              <p className="mt-1 text-xs text-muted-foreground/70">
                El sentimiento esta dentro de parametros normales.
              </p>
            </div>
          )}

          {!isLoading && !isError && visibleAlerts.map((alert) => (
            <AlertRow key={alert.id} alert={alert} />
          ))}

          {!isLoading && totalCount > limit && (
            <p className="pt-1 text-center text-xs text-muted-foreground">
              Mostrando {limit} de {totalCount} alertas
            </p>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

/* ────────────────────────────────────────────────────────────
 * Skeleton loading state
 * ──────────────────────────────────────────────────────────── */
function AlertListSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Cargando alertas">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="flex items-start gap-3 rounded-lg border border-border/50 p-4"
        >
          <Skeleton className="h-5 w-5 shrink-0 rounded" />
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-16 rounded-md" />
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-5 w-14 rounded-md" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="flex gap-2 pt-1">
              <Skeleton className="h-7 w-20 rounded-md" />
              <Skeleton className="h-7 w-24 rounded-md" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
