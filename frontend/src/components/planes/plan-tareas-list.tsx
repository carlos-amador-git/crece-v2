"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  usePlanTareas,
  usePlanProgreso,
  useUpdateTarea,
  useCompleteTarea,
  type PlanTarea,
  type EstadoTarea,
} from "@/lib/api/hooks/use-planes";
import { CheckCircle2, Circle, Clock, Edit3, Target, TrendingUp } from "lucide-react";
import { mapPlataforma, parseFodaTag, detechnicalize, mapMetrica, mapResponsable } from "@/lib/labels";
import { renderRichText } from "@/components/render-rich";

const ESTADO_LABEL: Record<EstadoTarea, { label: string; color: string; icon: typeof Circle }> = {
  TODO: { label: "Pendiente", color: "bg-muted text-muted-foreground", icon: Circle },
  IN_PROGRESS: { label: "En progreso", color: "bg-amber-500/15 text-amber-400", icon: Clock },
  DONE: { label: "Completada", color: "bg-emerald-500/15 text-emerald-400", icon: CheckCircle2 },
};

function progresoPct(t: PlanTarea): number {
  if (!t.metrica_valor_objetivo || t.metrica_valor_objetivo === 0) return 0;
  const real = t.metrica_valor_real ?? 0;
  return Math.min(100, (real / t.metrica_valor_objetivo) * 100);
}

function TareaItem({ planId, tarea }: { planId: number | string; tarea: PlanTarea }) {
  const update = useUpdateTarea(planId);
  const complete = useCompleteTarea(planId);
  const [editing, setEditing] = useState(false);
  const [editMeta, setEditMeta] = useState<string>(
    tarea.metrica_valor_objetivo?.toString() ?? ""
  );
  const [realInput, setRealInput] = useState<string>(
    tarea.metrica_valor_real?.toString() ?? ""
  );

  const estadoInfo = ESTADO_LABEL[tarea.estado];
  const Icon = estadoInfo.icon;
  const pct = progresoPct(tarea);

  const handleEstadoChange = (estado: EstadoTarea) => {
    update.mutate({ taskId: tarea.id, patch: { estado } });
  };

  const handleSaveMeta = () => {
    const parsed = parseFloat(editMeta);
    if (!isNaN(parsed)) {
      update.mutate({
        taskId: tarea.id,
        patch: { metrica_valor_objetivo: parsed },
      });
    }
    setEditing(false);
  };

  const handleSaveReal = () => {
    const parsed = parseFloat(realInput);
    if (!isNaN(parsed)) {
      if (parsed >= (tarea.metrica_valor_objetivo ?? Infinity)) {
        complete.mutate({ taskId: tarea.id, metrica_valor_real: parsed });
      } else {
        update.mutate({
          taskId: tarea.id,
          patch: { metrica_valor_real: parsed, estado: "IN_PROGRESS" },
        });
      }
    }
  };

  return (
    <Card className={tarea.estado === "DONE" ? "opacity-70" : undefined}>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <button
              onClick={() =>
                handleEstadoChange(tarea.estado === "DONE" ? "TODO" : "DONE")
              }
              className="mt-0.5 shrink-0"
              aria-label={`Marcar ${tarea.titulo}`}
            >
              <Icon
                className={
                  tarea.estado === "DONE"
                    ? "h-5 w-5 text-emerald-400"
                    : tarea.estado === "IN_PROGRESS"
                    ? "h-5 w-5 text-amber-400"
                    : "h-5 w-5 text-muted-foreground"
                }
              />
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-muted-foreground">
                  #{tarea.orden}
                </span>
                <h3 className="font-heading text-sm font-semibold">{renderRichText(detechnicalize(tarea.titulo))}</h3>
                <Badge variant="outline" className={`text-xs ${estadoInfo.color}`}>
                  {estadoInfo.label}
                </Badge>
                {tarea.plataforma && (
                  <Badge variant="outline" className="text-xs">
                    {mapPlataforma(tarea.plataforma)}
                  </Badge>
                )}
              </div>
              {(() => {
                const { foda, descripcion } = parseFodaTag(tarea.descripcion);
                return (
                  <>
                    {foda && (
                      <Badge variant="outline" className={`mt-1.5 text-[11px] font-medium ${foda.colorClass}`}>
                        <span className="mr-1">{foda.icon}</span>
                        {foda.label}
                      </Badge>
                    )}
                    <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                      {renderRichText(detechnicalize(descripcion))}
                    </p>
                  </>
                );
              })()}
            </div>
          </div>
        </div>

        {tarea.metrica_objetivo && (
          <div className="space-y-1.5 rounded-md bg-muted/40 p-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Target className="h-3 w-3" /> {mapMetrica(tarea.metrica_objetivo)}
              </span>
              <button
                onClick={() => setEditing(!editing)}
                className="text-xs text-accent hover:underline"
              >
                <Edit3 className="mr-1 inline h-3 w-3" />
                {editing ? "Cancelar" : "Editar meta"}
              </button>
            </div>

            {editing ? (
              <div className="flex gap-2">
                <Input
                  type="number"
                  value={editMeta}
                  onChange={(e) => setEditMeta(e.target.value)}
                  className="h-8 text-sm"
                  placeholder="Meta numérica"
                />
                <Button size="sm" onClick={handleSaveMeta} disabled={update.isPending}>
                  Guardar
                </Button>
              </div>
            ) : (
              <>
                <div className="flex items-baseline justify-between text-sm">
                  <span className="font-semibold">
                    {tarea.metrica_valor_real ?? 0}{" "}
                    <span className="text-xs text-muted-foreground">
                      / {tarea.metrica_valor_objetivo}
                    </span>
                  </span>
                  <span className="text-xs font-semibold text-accent">
                    {pct.toFixed(0)}%
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full ${
                      pct >= 100
                        ? "bg-emerald-500"
                        : pct >= 50
                        ? "bg-amber-500"
                        : "bg-accent"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <Input
                    type="number"
                    value={realInput}
                    onChange={(e) => setRealInput(e.target.value)}
                    className="h-7 text-xs"
                    placeholder="Registrar avance real"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={handleSaveReal}
                    disabled={update.isPending || complete.isPending}
                  >
                    <TrendingUp className="mr-1 h-3 w-3" /> Actualizar
                  </Button>
                </div>
              </>
            )}
          </div>
        )}

        {(tarea.frecuencia || tarea.responsable || tarea.deadline) && (
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            {tarea.frecuencia && <span>🔁 {tarea.frecuencia}</span>}
            {tarea.responsable && <span>👤 {mapResponsable(tarea.responsable)}</span>}
            {tarea.deadline && (
              <span>
                📅 {new Date(tarea.deadline).toLocaleDateString("es-MX")}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function PlanTareasList({ planId }: { planId: number | string }) {
  const { data: tareas, isLoading } = usePlanTareas(planId);
  const { data: progreso } = usePlanProgreso(planId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  if (!tareas || tareas.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Este plan aún no tiene tareas estructuradas. Será generado con deliberación Claude + Gemini próximamente.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {progreso && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Avance del plan</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="text-3xl font-bold">
                  {progreso.porcentaje_ejecutado.toFixed(0)}%
                </span>
                <span className="text-xs text-muted-foreground">
                  {progreso.tareas_done} de {progreso.total_tareas} tareas completadas
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full bg-emerald-500"
                  style={{ width: `${progreso.porcentaje_ejecutado}%` }}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 pt-2 text-xs">
                <div className="text-muted-foreground">
                  <Circle className="mr-1 inline h-3 w-3" />
                  {progreso.tareas_todo} pendientes
                </div>
                <div className="text-amber-400">
                  <Clock className="mr-1 inline h-3 w-3" />
                  {progreso.tareas_in_progress} en curso
                </div>
                <div className="text-emerald-400">
                  <CheckCircle2 className="mr-1 inline h-3 w-3" />
                  {progreso.tareas_done} hechas
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {tareas
          .slice()
          .sort((a, b) => a.orden - b.orden)
          .map((t) => (
            <TareaItem key={t.id} planId={planId} tarea={t} />
          ))}
      </div>
    </div>
  );
}
