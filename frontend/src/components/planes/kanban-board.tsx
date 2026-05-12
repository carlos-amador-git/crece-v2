"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ChevronRight, ChevronLeft, CheckCircle2, Pencil, Target } from "lucide-react";
import {
  type EstadoTarea,
  type PlanTarea,
  useCompleteTarea,
  usePlanProgreso,
  usePlanTareas,
  useUpdateTarea,
} from "@/lib/api/hooks/use-planes";

const COLUMNS: { id: EstadoTarea; label: string; color: string }[] = [
  { id: "TODO", label: "Por hacer", color: "bg-slate-100 dark:bg-slate-900" },
  { id: "IN_PROGRESS", label: "En curso", color: "bg-amber-50 dark:bg-amber-950" },
  { id: "DONE", label: "Hecho", color: "bg-emerald-50 dark:bg-emerald-950" },
];

const NEXT_STATE: Record<EstadoTarea, EstadoTarea | null> = {
  TODO: "IN_PROGRESS",
  IN_PROGRESS: "DONE",
  DONE: null,
};

const PREV_STATE: Record<EstadoTarea, EstadoTarea | null> = {
  TODO: null,
  IN_PROGRESS: "TODO",
  DONE: "IN_PROGRESS",
};

export function KanbanBoard({ planId }: { planId: number | string }) {
  const { data: tareas, isLoading } = usePlanTareas(planId);
  const { data: progreso } = usePlanProgreso(planId);
  const updateTarea = useUpdateTarea(planId);
  const completeTarea = useCompleteTarea(planId);

  const [editing, setEditing] = useState<PlanTarea | null>(null);
  const [completing, setCompleting] = useState<PlanTarea | null>(null);
  const [metricaValorReal, setMetricaValorReal] = useState<string>("");
  const [nota, setNota] = useState<string>("");

  const grouped = useMemo(() => {
    const acc: Record<EstadoTarea, PlanTarea[]> = { TODO: [], IN_PROGRESS: [], DONE: [] };
    (tareas || []).forEach((t) => acc[t.estado].push(t));
    return acc;
  }, [tareas]);

  const move = (tarea: PlanTarea, to: EstadoTarea) => {
    if (to === "DONE") {
      setCompleting(tarea);
      setMetricaValorReal("");
      setNota("");
      return;
    }
    updateTarea.mutate({ taskId: tarea.id, patch: { estado: to } });
  };

  const submitComplete = () => {
    if (!completing) return;
    const val = Number(metricaValorReal);
    if (Number.isNaN(val) || val < 0) return;
    completeTarea.mutate(
      { taskId: completing.id, metrica_valor_real: val, nota: nota || undefined },
      {
        onSuccess: () => {
          setCompleting(null);
          setMetricaValorReal("");
          setNota("");
        },
      }
    );
  };

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Cargando tareas…</div>;
  }

  if (!tareas || tareas.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Este plan no tiene tareas estructuradas. Genera un plan con{" "}
          <code className="rounded bg-muted px-1.5 py-0.5">estructurado: true</code>{" "}
          para ver el tablero Kanban.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {progreso && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Progreso del plan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-emerald-500 transition-all"
                style={{ width: `${progreso.porcentaje_ejecutado}%` }}
              />
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span>{progreso.porcentaje_ejecutado}% ejecutado</span>
              <span>Total: {progreso.total_tareas}</span>
              <span>Hecho: {progreso.tareas_done}</span>
              <span>En curso: {progreso.tareas_in_progress}</span>
              <span>Por hacer: {progreso.tareas_todo}</span>
              {Object.entries(progreso.impacto_acumulado).map(([k, v]) => (
                <span key={k}>
                  <Target className="mr-1 inline h-3 w-3" />
                  {k}: {v.toFixed(2)}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {COLUMNS.map((col) => (
          <div key={col.id} className={`rounded-lg p-3 ${col.color}`}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold">{col.label}</h3>
              <Badge variant="secondary">{grouped[col.id].length}</Badge>
            </div>
            <div className="space-y-2">
              {grouped[col.id].map((t) => (
                <Card key={t.id} className="shadow-sm">
                  <CardContent className="p-3">
                    <div className="mb-1 flex items-start justify-between gap-2">
                      <h4 className="text-sm font-medium leading-tight">{t.titulo}</h4>
                      <button
                        onClick={() => setEditing(t)}
                        className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                        aria-label="Editar"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                    </div>
                    <p className="mb-2 text-xs text-muted-foreground line-clamp-2">
                      {t.descripcion}
                    </p>
                    <div className="mb-2 flex flex-wrap gap-1">
                      {t.plataforma && (
                        <Badge variant="outline" className="text-[10px]">
                          {t.plataforma}
                        </Badge>
                      )}
                      {t.formato && (
                        <Badge variant="outline" className="text-[10px]">
                          {t.formato}
                        </Badge>
                      )}
                      {t.frecuencia && (
                        <Badge variant="outline" className="text-[10px]">
                          {t.frecuencia}
                        </Badge>
                      )}
                    </div>
                    {t.metrica_objetivo && (
                      <p className="mb-2 text-[11px] text-muted-foreground">
                        Meta: {t.metrica_objetivo}
                        {t.metrica_valor_objetivo !== null &&
                          ` = ${t.metrica_valor_objetivo}`}
                        {t.metrica_valor_real !== null && (
                          <span className="ml-1 text-emerald-600 dark:text-emerald-400">
                            → {t.metrica_valor_real}
                          </span>
                        )}
                      </p>
                    )}
                    <div className="flex gap-1">
                      {PREV_STATE[t.estado] && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => move(t, PREV_STATE[t.estado]!)}
                          className="h-7 px-2"
                        >
                          <ChevronLeft className="h-3 w-3" />
                        </Button>
                      )}
                      {NEXT_STATE[t.estado] && (
                        <Button
                          size="sm"
                          variant={NEXT_STATE[t.estado] === "DONE" ? "default" : "ghost"}
                          onClick={() => move(t, NEXT_STATE[t.estado]!)}
                          className="h-7 px-2"
                        >
                          {NEXT_STATE[t.estado] === "DONE" ? (
                            <>
                              <CheckCircle2 className="mr-1 h-3 w-3" /> Completar
                            </>
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar tarea</DialogTitle>
          </DialogHeader>
          {editing && (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium">Título</label>
                <Input
                  defaultValue={editing.titulo}
                  onBlur={(e) => {
                    if (e.target.value !== editing.titulo) {
                      updateTarea.mutate({ taskId: editing.id, patch: { titulo: e.target.value } });
                    }
                  }}
                />
              </div>
              <div>
                <label className="text-xs font-medium">Descripción</label>
                <Textarea
                  defaultValue={editing.descripcion}
                  onBlur={(e) => {
                    if (e.target.value !== editing.descripcion) {
                      updateTarea.mutate({
                        taskId: editing.id,
                        patch: { descripcion: e.target.value },
                      });
                    }
                  }}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-medium">Responsable</label>
                  <Input
                    defaultValue={editing.responsable || ""}
                    onBlur={(e) => {
                      if (e.target.value !== (editing.responsable || "")) {
                        updateTarea.mutate({
                          taskId: editing.id,
                          patch: { responsable: e.target.value || null },
                        });
                      }
                    }}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium">Frecuencia</label>
                  <Input
                    defaultValue={editing.frecuencia || ""}
                    onBlur={(e) => {
                      if (e.target.value !== (editing.frecuencia || "")) {
                        updateTarea.mutate({
                          taskId: editing.id,
                          patch: { frecuencia: e.target.value || null },
                        });
                      }
                    }}
                  />
                </div>
              </div>
              {editing.cambios_historial && editing.cambios_historial.length > 0 && (
                <div>
                  <label className="text-xs font-medium">Historial</label>
                  <div className="max-h-32 space-y-1 overflow-y-auto rounded border border-border p-2 text-[10px]">
                    {editing.cambios_historial.map((c, i) => (
                      <div key={i} className="text-muted-foreground">
                        <span className="font-mono">{String(c.at)?.slice(0, 16)}</span>{" "}
                        <span className="font-medium">{String(c.type)}</span>{" "}
                        {c.field ? <span>· {String(c.field)}</span> : null}{" "}
                        {c.new ? <span>→ {String(c.new)}</span> : null}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Complete dialog — captures metrica real */}
      <Dialog open={!!completing} onOpenChange={(open) => !open && setCompleting(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Completar tarea</DialogTitle>
          </DialogHeader>
          {completing && (
            <div className="space-y-3">
              <p className="text-sm">{completing.titulo}</p>
              <div>
                <label className="text-xs font-medium">
                  Valor real de la métrica
                  {completing.metrica_objetivo && ` (${completing.metrica_objetivo})`}
                </label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={metricaValorReal}
                  onChange={(e) => setMetricaValorReal(e.target.value)}
                  placeholder={
                    completing.metrica_valor_objetivo !== null
                      ? `Meta era ${completing.metrica_valor_objetivo}`
                      : "0.00"
                  }
                />
              </div>
              <div>
                <label className="text-xs font-medium">Nota (opcional)</label>
                <Textarea
                  value={nota}
                  onChange={(e) => setNota(e.target.value)}
                  placeholder="Contexto del cierre, lo que funcionó o no…"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCompleting(null)}>
              Cancelar
            </Button>
            <Button onClick={submitComplete} disabled={!metricaValorReal}>
              Confirmar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
