"use client";

import { AlertCircle, Search, Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  useSerpSearch,
  useWizardStore,
  type SerpCandidate,
} from "@/lib/api/hooks/use-onboarding";

function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  const color =
    score >= 0.7
      ? "bg-emerald-500"
      : score >= 0.4
        ? "bg-amber-500"
        : "bg-rose-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-[10px] text-muted-foreground">
        {score.toFixed(2)}
      </span>
    </div>
  );
}

export function Step3SerpOpcional({ dirigenteId }: { dirigenteId: number }) {
  const { serpEnabled, setSerpEnabled, serpResults, setSerpResults } =
    useWizardStore();
  const [fullName, setFullName] = useState("");
  const [cargo, setCargo] = useState("");

  const search = useSerpSearch(dirigenteId);

  const runSearch = () => {
    if (!fullName.trim() || !cargo.trim()) return;
    search.mutate(
      { full_name: fullName, cargo },
      {
        onSuccess: (data) => {
          setSerpResults(data.candidates);
        },
      },
    );
  };

  return (
    <div className="space-y-6" data-testid="step-3-serp">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 3 de 9 · Opcional
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          ¿Te ayudamos a encontrar sus perfiles?
        </h2>
        <p className="text-sm text-muted-foreground">
          Si no conoces todas las URLs, ejecutamos una búsqueda SERP con
          Brightdata para sugerir candidatos. Tú decides cuáles son correctos.
        </p>
      </header>

      <Card>
        <CardContent className="flex items-start gap-3 p-4">
          <Checkbox
            id="serp-toggle"
            data-testid="toggle-serp"
            checked={serpEnabled}
            onCheckedChange={(v) => setSerpEnabled(Boolean(v))}
            className="mt-1"
          />
          <div className="flex-1 space-y-1">
            <Label htmlFor="serp-toggle" className="cursor-pointer">
              Activar búsqueda asistida
            </Label>
            <p className="text-xs text-muted-foreground">
              Usa Brightdata como primary y Apify como fallback. Toma 10-20
              segundos.
            </p>
          </div>
        </CardContent>
      </Card>

      {serpEnabled && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="serp-name">Nombre completo</Label>
              <Input
                id="serp-name"
                data-testid="input-serp-name"
                placeholder="Alejandro Piña"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="serp-cargo">Cargo o contexto</Label>
              <Input
                id="serp-cargo"
                data-testid="input-serp-cargo"
                placeholder="Diputado CDMX MC"
                value={cargo}
                onChange={(e) => setCargo(e.target.value)}
              />
            </div>
          </div>
          <Button
            onClick={runSearch}
            disabled={search.isPending || !fullName || !cargo}
            data-testid="btn-serp-search"
          >
            <Search className="mr-2 h-4 w-4" />
            {search.isPending ? "Buscando…" : "Buscar candidatos"}
          </Button>

          {search.isError && (
            <div
              className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
              role="alert"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>No se pudieron obtener candidatos. Puedes seguir en modo manual.</span>
            </div>
          )}

          {serpResults.length > 0 && (
            <div className="space-y-2" data-testid="serp-results">
              <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                <Sparkles className="h-3 w-3" /> Top {Math.min(5, serpResults.length)} resultados
              </p>
              {serpResults.slice(0, 5).map((c: SerpCandidate) => (
                <Card key={`${c.platform}-${c.handle}`}>
                  <CardContent className="flex items-center justify-between gap-3 p-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono text-sm">
                        @{c.handle}{" "}
                        <Badge variant="outline" className="ml-1 text-[10px]">
                          {c.platform}
                        </Badge>
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {c.full_name ?? "—"}
                      </p>
                    </div>
                    <ScoreBar score={c.score} />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {!serpEnabled && (
        <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
          Puedes saltar este paso si ya tienes las URLs capturadas en el paso 2.
        </p>
      )}
    </div>
  );
}
