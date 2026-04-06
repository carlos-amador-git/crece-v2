"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck } from "lucide-react";
import { CrisisAlertBanner } from "./crisis-alert-banner";
import {
  useCrisisPostAlerts,
  type CrisisPostAlert,
} from "@/hooks/use-crisis-alerts";

/* ────────────────────────────────────────────────────────────
 * CrisisAlertList
 *
 * Displays a sorted list of active crisis/warning alerts.
 * Three states: loading (skeleton), empty, and populated.
 * Alerts are ordered by severity (worst first).
 * ──────────────────────────────────────────────────────────── */

interface CrisisAlertListProps {
  /** Optional: filter alerts to a specific dirigente */
  dirigenteId?: number;
  /** Max number of alerts to display (default: 5) */
  limit?: number;
  /** Called when "Ver detalle" is clicked on an alert */
  onViewDetail?: (alert: CrisisPostAlert) => void;
}

export function CrisisAlertList({
  dirigenteId,
  limit = 5,
  onViewDetail,
}: CrisisAlertListProps) {
  const { data: alerts, isLoading, isError } = useCrisisPostAlerts(dirigenteId);

  const visibleAlerts = (alerts ?? []).slice(0, limit);
  const totalCount = alerts?.length ?? 0;

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
          {/* Loading state */}
          {isLoading && <AlertListSkeleton />}

          {/* Error state */}
          {isError && !isLoading && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <p className="text-sm text-destructive">
                Error al cargar alertas. Se reintentara automaticamente.
              </p>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !isError && visibleAlerts.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <ShieldCheck className="mb-3 h-10 w-10 text-emerald-500/50" />
              <p className="text-sm font-medium text-muted-foreground">
                Sin alertas activas
              </p>
              <p className="mt-1 text-xs text-muted-foreground/70">
                El sentimiento de todos los dirigentes esta dentro de parametros normales.
              </p>
            </div>
          )}

          {/* Alert list */}
          {!isLoading &&
            !isError &&
            visibleAlerts.map((alert) => (
              <CrisisAlertBanner
                key={alert.id}
                dirigente_name={alert.dirigente_name}
                sentiment_score={alert.sentiment_score}
                platform={alert.platform}
                post_content_preview={alert.post_content_preview}
                severity={alert.severity}
                post_url={alert.post_url}
                onViewDetail={
                  onViewDetail ? () => onViewDetail(alert) : undefined
                }
              />
            ))}

          {/* Overflow indicator */}
          {!isLoading && totalCount > limit && (
            <p className="pt-1 text-center text-xs text-muted-foreground">
              Mostrando{" "}
              <span className="tabular-nums font-medium" data-numeric="true">
                {limit}
              </span>{" "}
              de{" "}
              <span className="tabular-nums font-medium" data-numeric="true">
                {totalCount}
              </span>{" "}
              alertas
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
