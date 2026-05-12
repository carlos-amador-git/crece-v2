"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useIADirigenteSummary } from "@/lib/api/hooks/use-indice-aceptacion";
import { CheckCircle2, XCircle, MessageSquare } from "lucide-react";

export function IASummaryCard({ dirigenteId }: { dirigenteId: number }) {
  const { data, isLoading } = useIADirigenteSummary(dirigenteId);

  if (isLoading) return <Skeleton className="h-48" />;
  if (!data || data.posts_con_ia === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Índice de Aceptación — resumen</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          No hay publicaciones con suficientes comments para calcular IA aún. Se actualiza automáticamente.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Índice de Aceptación — resumen</CardTitle>
          <Badge variant="outline" className="text-xs">
            {data.posts_con_ia} publicaciones
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-md bg-emerald-500/10 p-3">
            <div className="flex items-center gap-1 text-xs text-emerald-400">
              <CheckCircle2 className="h-3 w-3" /> Aprobación promedio
            </div>
            <div className="mt-1 text-2xl font-bold text-emerald-400">
              {data.aprobacion_promedio.toFixed(1)}%
            </div>
          </div>
          <div className="rounded-md bg-rose-500/10 p-3">
            <div className="flex items-center gap-1 text-xs text-rose-400">
              <XCircle className="h-3 w-3" /> Rechazo promedio
            </div>
            <div className="mt-1 text-2xl font-bold text-rose-400">
              {data.rechazo_promedio.toFixed(1)}%
            </div>
          </div>
        </div>

        {data.top_aprobacion.length > 0 && (
          <div>
            <div className="mb-2 text-xs font-medium text-muted-foreground">
              Top publicaciones mejor recibidas:
            </div>
            <div className="space-y-2">
              {data.top_aprobacion.slice(0, 3).map((p) => (
                <div key={p.post_id} className="flex items-start gap-2 rounded-md border border-border p-2 text-xs">
                  <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-emerald-400" />
                  <div className="min-w-0 flex-1">
                    <div className="line-clamp-1 text-foreground/80">{p.snippet}</div>
                    <div className="mt-0.5 flex gap-3 text-muted-foreground">
                      <span>{p.aprobacion_pct}% aprobación</span>
                      <span className="flex items-center gap-0.5">
                        <MessageSquare className="h-3 w-3" /> {p.n_comments}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.top_rechazo.length > 0 && (
          <div>
            <div className="mb-2 text-xs font-medium text-muted-foreground">
              Publicaciones con mayor rechazo:
            </div>
            <div className="space-y-2">
              {data.top_rechazo.slice(0, 2).map((p) => (
                <div key={p.post_id} className="flex items-start gap-2 rounded-md border border-border p-2 text-xs">
                  <XCircle className="mt-0.5 h-3 w-3 shrink-0 text-rose-400" />
                  <div className="min-w-0 flex-1">
                    <div className="line-clamp-1 text-foreground/80">{p.snippet}</div>
                    <div className="mt-0.5 flex gap-3 text-muted-foreground">
                      <span>{p.rechazo_pct}% rechazo</span>
                      <span className="flex items-center gap-0.5">
                        <MessageSquare className="h-3 w-3" /> {p.n_comments}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
