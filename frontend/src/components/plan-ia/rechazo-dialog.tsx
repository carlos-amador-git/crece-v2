"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import type { Recomendacion } from "@/lib/api/hooks/use-recomendaciones";

interface Props {
  recomendacion: Recomendacion | null;
  onClose: () => void;
  onConfirm: (motivo: string) => void;
  isLoading?: boolean;
}

export function RechazoDialog({ recomendacion, onClose, onConfirm, isLoading }: Props) {
  const [motivo, setMotivo] = useState("");
  const open = !!recomendacion;

  const handleSubmit = () => {
    if (motivo.trim().length < 5) return;
    onConfirm(motivo.trim());
    setMotivo("");
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          setMotivo("");
          onClose();
        }
      }}
    >
      <DialogContent data-testid="dialog-rechazo">
        <DialogHeader>
          <DialogTitle>Rechazar recomendación</DialogTitle>
          <DialogDescription>
            {recomendacion?.accion_texto ?? "—"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <label htmlFor="motivo-rechazo" className="text-sm font-medium">
            Motivo (obligatorio)
          </label>
          <Textarea
            id="motivo-rechazo"
            data-testid="input-motivo-rechazo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Explica por qué rechazas esta recomendación. Mínimo 5 caracteres."
            rows={4}
          />
          <p className="text-xs text-muted-foreground">
            Este motivo queda en historial auditable MD.
          </p>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={motivo.trim().length < 5 || isLoading}
            data-testid="btn-confirmar-rechazo"
            className="bg-rose-600 hover:bg-rose-700"
          >
            {isLoading ? "Rechazando…" : "Rechazar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
