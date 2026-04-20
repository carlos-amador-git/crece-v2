"use client";

import { FileSignature, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  useWizardStore,
  type PromesaInput,
} from "@/lib/api/hooks/use-onboarding";

export function Step8Promesas() {
  const { promesas, setPromesas } = useWizardStore();

  const add = () =>
    setPromesas([
      ...promesas,
      { texto_promesa: "", fecha_compromiso: "", evidencia_url: "" },
    ]);

  const update = (idx: number, patch: Partial<PromesaInput>) =>
    setPromesas(promesas.map((p, i) => (i === idx ? { ...p, ...patch } : p)));

  const remove = (idx: number) =>
    setPromesas(promesas.filter((_, i) => i !== idx));

  return (
    <div className="space-y-6" data-testid="step-8-promesas">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 8 de 9 · Mínimo 1 requerido
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          Compromisos de campaña
        </h2>
        <p className="text-sm text-muted-foreground">
          Promesas rastreables del dirigente. Libera bloque B16 (seguimiento
          promesas · D-17).
        </p>
      </header>

      {promesas.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-md border border-dashed p-8 text-center">
          <FileSignature className="h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            Agrega al menos una promesa con fecha de compromiso.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {promesas.map((p, idx) => (
          <Card key={idx} data-testid={`promesa-row-${idx}`}>
            <CardContent className="space-y-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 space-y-1">
                  <Label htmlFor={`prom-text-${idx}`}>Promesa</Label>
                  <Textarea
                    id={`prom-text-${idx}`}
                    data-testid={`input-prom-text-${idx}`}
                    placeholder="Ampliar línea 12 del Metro antes de concluir sexenio…"
                    value={p.texto_promesa}
                    onChange={(e) => update(idx, { texto_promesa: e.target.value })}
                    rows={2}
                  />
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => remove(idx)}
                  aria-label="Eliminar promesa"
                  data-testid={`btn-remove-promesa-${idx}`}
                >
                  <Trash2 className="h-4 w-4 text-rose-500" />
                </Button>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <Label htmlFor={`prom-fecha-${idx}`}>Fecha de compromiso</Label>
                  <Input
                    id={`prom-fecha-${idx}`}
                    data-testid={`input-prom-fecha-${idx}`}
                    type="date"
                    value={p.fecha_compromiso}
                    onChange={(e) => update(idx, { fecha_compromiso: e.target.value })}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`prom-evid-${idx}`}>Evidencia (URL opcional)</Label>
                  <Input
                    id={`prom-evid-${idx}`}
                    data-testid={`input-prom-evid-${idx}`}
                    placeholder="https://…"
                    value={p.evidencia_url ?? ""}
                    onChange={(e) =>
                      update(idx, { evidencia_url: e.target.value })
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Button
        variant="outline"
        onClick={add}
        data-testid="btn-add-promesa"
        className="w-full sm:w-auto"
      >
        <Plus className="mr-1 h-4 w-4" />
        Agregar promesa
      </Button>
    </div>
  );
}
