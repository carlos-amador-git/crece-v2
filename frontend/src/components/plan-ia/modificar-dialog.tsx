"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type {
  CriterioExito,
  Recomendacion,
} from "@/lib/api/hooks/use-recomendaciones";

export interface ModificarPayload {
  accion_texto: string;
  criterio_exito: CriterioExito;
  ventana_duracion_dias: number;
}

interface Props {
  recomendacion: Recomendacion | null;
  onClose: () => void;
  onConfirm: (patch: ModificarPayload) => void;
  isLoading?: boolean;
  mode: "admin" | "cliente";
}

export function ModificarDialog({
  recomendacion,
  onClose,
  onConfirm,
  isLoading,
  mode,
}: Props) {
  const [accion, setAccion] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [metrica, setMetrica] = useState("");
  const [objetivo, setObjetivo] = useState("");
  const [unidad, setUnidad] = useState("");
  const [ventana, setVentana] = useState(14);
  const open = !!recomendacion;

  useEffect(() => {
    if (!recomendacion) return;
    setAccion(recomendacion.accion_texto ?? "");
    setDescripcion(recomendacion.criterio_exito?.descripcion ?? "");
    setMetrica(recomendacion.criterio_exito?.metrica ?? "");
    setObjetivo(
      recomendacion.criterio_exito?.objetivo !== undefined
        ? String(recomendacion.criterio_exito.objetivo)
        : "",
    );
    setUnidad(recomendacion.criterio_exito?.unidad ?? "");
    setVentana(recomendacion.ventana_duracion_dias ?? 14);
  }, [recomendacion]);

  const handleSubmit = () => {
    if (accion.trim().length < 5) return;
    const criterio: CriterioExito = {};
    if (descripcion.trim()) criterio.descripcion = descripcion.trim();
    if (metrica.trim()) criterio.metrica = metrica.trim();
    if (objetivo.trim() !== "" && !Number.isNaN(Number(objetivo))) {
      criterio.objetivo = Number(objetivo);
    }
    if (unidad.trim()) criterio.unidad = unidad.trim();
    onConfirm({
      accion_texto: accion.trim(),
      criterio_exito: criterio,
      ventana_duracion_dias: Math.max(1, Math.min(90, ventana)),
    });
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <DialogContent data-testid="dialog-modificar" className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Modificar recomendación</DialogTitle>
          <DialogDescription>
            {mode === "admin"
              ? "Ajustes de MD antes de aprobar a cliente. Quedará marcada como modificada."
              : "Ajusta la acción o el criterio antes de aceptarla."}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="accion" className="text-sm font-medium">
              Acción
            </label>
            <Textarea
              id="accion"
              data-testid="input-accion"
              value={accion}
              onChange={(e) => setAccion(e.target.value)}
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="descripcion" className="text-sm font-medium">
              Descripción criterio éxito
            </label>
            <Textarea
              id="descripcion"
              data-testid="input-descripcion"
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              rows={2}
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="space-y-2">
              <label htmlFor="metrica" className="text-sm font-medium">
                Métrica
              </label>
              <Input
                id="metrica"
                data-testid="input-metrica"
                value={metrica}
                onChange={(e) => setMetrica(e.target.value)}
                placeholder="engagement_rate"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="objetivo" className="text-sm font-medium">
                Objetivo
              </label>
              <Input
                id="objetivo"
                data-testid="input-objetivo"
                value={objetivo}
                onChange={(e) => setObjetivo(e.target.value)}
                placeholder="10"
                type="number"
                step="0.1"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="unidad" className="text-sm font-medium">
                Unidad
              </label>
              <Input
                id="unidad"
                data-testid="input-unidad"
                value={unidad}
                onChange={(e) => setUnidad(e.target.value)}
                placeholder="%"
              />
            </div>
          </div>
          <div className="space-y-2">
            <label htmlFor="ventana" className="text-sm font-medium">
              Ventana seguimiento (días)
            </label>
            <Input
              id="ventana"
              data-testid="input-ventana"
              type="number"
              min={1}
              max={90}
              value={ventana}
              onChange={(e) => setVentana(Number(e.target.value) || 14)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={accion.trim().length < 5 || isLoading}
            data-testid="btn-confirmar-modificar"
          >
            {isLoading ? "Guardando…" : "Guardar cambios"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
