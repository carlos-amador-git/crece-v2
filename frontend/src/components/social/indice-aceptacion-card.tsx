"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useIAPost } from "@/lib/api/hooks/use-indice-aceptacion";
import { CheckCircle2, XCircle, Circle, Users, AlertCircle, TrendingUp } from "lucide-react";

const CONFIDENCE_LABEL: Record<string, { label: string; color: string }> = {
  none: { label: "Sin datos", color: "bg-muted text-muted-foreground" },
  low: { label: "Baja confianza", color: "bg-amber-500/20 text-amber-400" },
  medium: { label: "Confianza media", color: "bg-blue-500/20 text-blue-400" },
  high: { label: "Confianza alta", color: "bg-emerald-500/20 text-emerald-400" },
};

export function IndiceAceptacionCard({ postId }: { postId: number }) {
  const { data: ia, isLoading, error } = useIAPost(postId);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <Skeleton className="h-24" />
        </CardContent>
      </Card>
    );
  }

  if (error || !ia) {
    return (
      <Card className="border-muted">
        <CardContent className="p-4 text-sm text-muted-foreground">
          IA no disponible para esta publicación.
        </CardContent>
      </Card>
    );
  }

  if (ia.total_comments === 0) {
    return (
      <Card className="border-muted">
        <CardContent className="p-4 text-xs text-muted-foreground">
          <AlertCircle className="mb-1 inline h-3 w-3" /> Sin comentarios analizados. Se actualizará cuando ingresen comments via pipeline.
        </CardContent>
      </Card>
    );
  }

  const confInfo = CONFIDENCE_LABEL[ia.confidence] || CONFIDENCE_LABEL.none;
  const total = ia.aprobacion_pct + ia.rechazo_pct + ia.neutral_pct;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base">Índice de Aceptación</CardTitle>
          <Badge variant="outline" className={`text-xs ${confInfo.color}`}>
            {confInfo.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stacked bar */}
        <div className="space-y-1.5">
          <div className="flex h-8 w-full overflow-hidden rounded-md">
            <div
              className="flex items-center justify-center bg-emerald-500 text-xs font-semibold text-white"
              style={{ width: `${(ia.aprobacion_pct / total) * 100}%` }}
              title={`Aprobación: ${ia.aprobacion_pct}%`}
            >
              {ia.aprobacion_pct >= 8 ? `${ia.aprobacion_pct.toFixed(0)}%` : ""}
            </div>
            <div
              className="flex items-center justify-center bg-muted text-xs font-semibold text-muted-foreground"
              style={{ width: `${(ia.neutral_pct / total) * 100}%` }}
              title={`Neutral: ${ia.neutral_pct}%`}
            >
              {ia.neutral_pct >= 8 ? `${ia.neutral_pct.toFixed(0)}%` : ""}
            </div>
            <div
              className="flex items-center justify-center bg-rose-500 text-xs font-semibold text-white"
              style={{ width: `${(ia.rechazo_pct / total) * 100}%` }}
              title={`Rechazo: ${ia.rechazo_pct}%`}
            >
              {ia.rechazo_pct >= 8 ? `${ia.rechazo_pct.toFixed(0)}%` : ""}
            </div>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" /> Aprobación {ia.aprobacion_pct}%
            </span>
            <span className="flex items-center gap-1">
              <Circle className="h-3 w-3" /> Neutral {ia.neutral_pct}%
            </span>
            <span className="flex items-center gap-1">
              <XCircle className="h-3 w-3 text-rose-400" /> Rechazo {ia.rechazo_pct}%
            </span>
          </div>
        </div>

        {/* Metrics row */}
        <div className="grid grid-cols-3 gap-3 border-t border-border pt-3 text-xs">
          <div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <Users className="h-3 w-3" /> Authors únicos
            </div>
            <div className="mt-0.5 text-sm font-semibold">{ia.unique_authors}</div>
          </div>
          <div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <TrendingUp className="h-3 w-3" /> Expansión
            </div>
            <div className="mt-0.5 text-sm font-semibold">{ia.expansion_pct}%</div>
          </div>
          <div>
            <div className="text-muted-foreground">Total comments</div>
            <div className="mt-0.5 text-sm font-semibold">{ia.total_comments}</div>
          </div>
        </div>

        {/* Tono breakdown */}
        {Object.keys(ia.tono_breakdown).length > 0 && (
          <div className="border-t border-border pt-3">
            <div className="mb-2 text-xs text-muted-foreground">Distribución de tonos:</div>
            <div className="flex flex-wrap gap-1">
              {Object.entries(ia.tono_breakdown)
                .sort((a, b) => b[1] - a[1])
                .map(([tono, count]) => (
                  <Badge key={tono} variant="outline" className="text-xs">
                    {tono}: {count}
                  </Badge>
                ))}
            </div>
          </div>
        )}

        {ia.confidence === "low" && (
          <div className="rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
            <AlertCircle className="mb-0.5 mr-1 inline h-3 w-3" />
            IA con pocos comentarios ({ia.total_comments}). Intervalos de confianza amplios.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
