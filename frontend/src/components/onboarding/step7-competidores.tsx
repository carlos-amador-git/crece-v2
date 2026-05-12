"use client";

import { Plus, Trash2, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useWizardStore,
  type CompetidorInput,
} from "@/lib/api/hooks/use-onboarding";

export function Step7Competidores() {
  const { competidores, setCompetidores } = useWizardStore();

  const add = () =>
    setCompetidores([
      ...competidores,
      { full_name: "", cargo: "", url_ref: "" },
    ]);

  const update = (idx: number, patch: Partial<CompetidorInput>) =>
    setCompetidores(
      competidores.map((c, i) => (i === idx ? { ...c, ...patch } : c)),
    );

  const remove = (idx: number) =>
    setCompetidores(competidores.filter((_, i) => i !== idx));

  return (
    <div className="space-y-6" data-testid="step-7-competidores">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 7 de 9 · Mínimo 1 requerido
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          ¿Contra quién medimos?
        </h2>
        <p className="text-sm text-muted-foreground">
          Agrega 3-5 contendientes directos del mismo cargo o territorio. Libera
          el bloque #04 (benchmark vs competidores · D-22).
        </p>
      </header>

      {competidores.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-md border border-dashed p-8 text-center">
          <Users className="h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            Aún no hay competidores. Agrega al menos uno para continuar.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {competidores.map((c, idx) => (
          <Card key={idx} data-testid={`competidor-row-${idx}`}>
            <CardContent className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-12">
              <div className="space-y-1 sm:col-span-4">
                <Label htmlFor={`comp-name-${idx}`}>Nombre</Label>
                <Input
                  id={`comp-name-${idx}`}
                  data-testid={`input-comp-name-${idx}`}
                  placeholder="Laura Ballesteros"
                  value={c.full_name}
                  onChange={(e) => update(idx, { full_name: e.target.value })}
                />
              </div>
              <div className="space-y-1 sm:col-span-3">
                <Label htmlFor={`comp-cargo-${idx}`}>Cargo</Label>
                <Input
                  id={`comp-cargo-${idx}`}
                  data-testid={`input-comp-cargo-${idx}`}
                  placeholder="Diputada local"
                  value={c.cargo}
                  onChange={(e) => update(idx, { cargo: e.target.value })}
                />
              </div>
              <div className="space-y-1 sm:col-span-4">
                <Label htmlFor={`comp-url-${idx}`}>URL de referencia</Label>
                <Input
                  id={`comp-url-${idx}`}
                  data-testid={`input-comp-url-${idx}`}
                  placeholder="https://instagram.com/…"
                  value={c.url_ref}
                  onChange={(e) => update(idx, { url_ref: e.target.value })}
                />
              </div>
              <div className="flex items-end justify-end sm:col-span-1">
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => remove(idx)}
                  aria-label="Eliminar competidor"
                  data-testid={`btn-remove-comp-${idx}`}
                >
                  <Trash2 className="h-4 w-4 text-rose-500" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Button
        variant="outline"
        onClick={add}
        data-testid="btn-add-competidor"
        className="w-full sm:w-auto"
      >
        <Plus className="mr-1 h-4 w-4" />
        Agregar competidor
      </Button>
    </div>
  );
}
