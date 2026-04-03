"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useElectoralMapStore } from "@/lib/store";
import { useSeccionDetail } from "@/lib/api/hooks/use-electoral";
import { Map, Layers, X } from "lucide-react";

const ElectoralMap = dynamic(
  () => import("@/components/maps/electoral-map").then((m) => m.ElectoralMap),
  { ssr: false, loading: () => <Skeleton className="h-full w-full" /> }
);

const LAYERS = [
  { key: "intencion" as const, label: "Intencion de Voto", color: "bg-emerald-500" },
  { key: "coverage" as const, label: "Cobertura Dirigente", color: "bg-sky-500" },
  { key: "penetration" as const, label: "Penetracion Social", color: "bg-violet-500" },
];

export default function ElectoralPage() {
  const { selectedSeccion, activeLayer, setActiveLayer, setSelectedSeccion } =
    useElectoralMapStore();
  const { data: seccionDetail } = useSeccionDetail(selectedSeccion);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-heading text-2xl font-bold">Mapa Electoral</h1>
        <p className="text-sm text-muted-foreground">
          Visualizacion geoespacial de intencion de voto por seccion electoral
        </p>
      </div>

      <div className="relative flex h-[calc(100vh-220px)] gap-4">
        {/* Map */}
        <div className="flex-1 overflow-hidden rounded-lg border">
          <ElectoralMap className="h-full" />
        </div>

        {/* Side panel */}
        <div className="hidden w-80 shrink-0 space-y-4 overflow-y-auto lg:block">
          {/* Layer toggles */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Layers className="h-4 w-4" />
                Capas
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {LAYERS.map((layer) => (
                <button
                  key={layer.key}
                  onClick={() => setActiveLayer(layer.key)}
                  className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                    activeLayer === layer.key
                      ? "bg-accent/10 text-accent font-medium"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  <span
                    className={`h-3 w-3 rounded-full ${layer.color}`}
                    aria-hidden="true"
                  />
                  {layer.label}
                </button>
              ))}
            </CardContent>
          </Card>

          {/* Section detail */}
          {selectedSeccion ? (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    Seccion {selectedSeccion}
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setSelectedSeccion(null)}
                    aria-label="Cerrar detalle"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {seccionDetail ? (
                  <>
                    <div className="text-sm text-muted-foreground">
                      {seccionDetail.municipio}, {seccionDetail.estado}
                    </div>
                    <Separator />
                    <div className="grid grid-cols-3 gap-3 text-center">
                      <div>
                        <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                          {seccionDetail.a_favor}%
                        </p>
                        <p className="text-xs text-muted-foreground">A favor</p>
                      </div>
                      <div>
                        <p className="text-lg font-bold text-amber-600 dark:text-amber-400">
                          {seccionDetail.indeciso}%
                        </p>
                        <p className="text-xs text-muted-foreground">Indeciso</p>
                      </div>
                      <div>
                        <p className="text-lg font-bold text-red-600 dark:text-red-400">
                          {seccionDetail.en_contra}%
                        </p>
                        <p className="text-xs text-muted-foreground">En contra</p>
                      </div>
                    </div>
                    <Separator />
                    <p className="text-xs text-muted-foreground">
                      Basado en {seccionDetail.total_encuestas} encuestas
                    </p>
                  </>
                ) : (
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-16 w-full" />
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-8 text-center">
                <Map className="mb-2 h-8 w-8 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  Haz clic en una seccion del mapa para ver su detalle
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
