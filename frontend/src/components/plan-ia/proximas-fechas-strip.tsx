/**
 * ProximasFechasStrip — listado horizontal de efemerides próximas
 * embebido en /dashboard/recomendaciones (Opción 4 · 2026-05-12).
 *
 * Reemplaza /dashboard/calendario: el catálogo de fechas vive aquí
 * con un botón "Convertir en recomendación" que crea row en
 * recomendaciones_plan_ia (estado=propuesta) vía endpoint backend.
 */
"use client";

import { CalendarDays, ChevronDown, Flame, Plus, Loader2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import {
  useCalendarioProximas,
  useConvertirEfemerideARecomendacion,
  type Efemeride,
} from "@/lib/api/hooks/use-calendario";

interface Props {
  dirigenteId: number | null;
  isAdmin: boolean;
  days?: number;
  onConverted?: () => void;
}

const VIRALIDAD_META = {
  alta: { label: "alta", cls: "bg-rose-500/10 text-rose-700 border-rose-500/30 dark:text-rose-300" },
  media: { label: "media", cls: "bg-amber-500/10 text-amber-700 border-amber-500/30 dark:text-amber-300" },
  baja: { label: "baja", cls: "bg-slate-400/10 text-slate-600 border-slate-400/30 dark:text-slate-300" },
} as const;

function fmtFecha(iso: string): string {
  try {
    const d = new Date(iso + "T00:00:00");
    return new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short" }).format(d);
  } catch {
    return iso;
  }
}

export function ProximasFechasStrip({ dirigenteId, isAdmin, days = 60, onConverted }: Props) {
  const { data, isLoading } = useCalendarioProximas(days, "media");
  const convertir = useConvertirEfemerideARecomendacion();
  const [convertingId, setConvertingId] = useState<number | null>(null);
  const [convertedIds, setConvertedIds] = useState<Set<number>>(new Set());
  const [expanded, setExpanded] = useState(false);

  const INITIAL_VISIBLE = 4;
  const MAX_VISIBLE = 8;

  const allRelevant: Efemeride[] = (data ?? [])
    .filter((e) => e.viralidad === "alta" || e.viralidad === "media")
    .slice(0, MAX_VISIBLE);
  const items = expanded ? allRelevant : allRelevant.slice(0, INITIAL_VISIBLE);
  const remaining = allRelevant.length - items.length;

  if (!dirigenteId) return null;

  const handleConvertir = (e: Efemeride) => {
    if (!isAdmin) return;
    setConvertingId(e.id);
    convertir.mutate(
      { efemerideId: e.id, body: { dirigente_id: dirigenteId } },
      {
        onSuccess: () => {
          setConvertedIds((prev) => new Set([...prev, e.id]));
          setConvertingId(null);
          onConverted?.();
        },
        onError: () => setConvertingId(null),
      },
    );
  };

  return (
    <Card className="border-border/60" data-testid="proximas-fechas-strip">
      <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3 space-y-0">
        <div className="min-w-0 flex-1 space-y-1">
          <CardTitle className="flex items-center gap-2 text-base font-heading">
            <CalendarDays className="h-4 w-4 text-accent" />
            Próximas fechas estratégicas · {days} días
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Catálogo de efemerides relevantes para construir narrativa.{" "}
            {isAdmin
              ? "Convierte cualquiera en recomendación para revisión."
              : "Tu equipo MD las curará en recomendaciones cuando aplique."}
          </p>
        </div>
        {!expanded && remaining > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExpanded(true)}
            className="shrink-0 gap-1 text-[11px]"
            data-testid="btn-ver-mas-fechas"
          >
            <ChevronDown className="h-3.5 w-3.5" />
            Ver {remaining} más
          </Button>
        )}
        {expanded && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(false)}
            className="shrink-0 gap-1 text-[11px] text-muted-foreground"
            data-testid="btn-ver-menos-fechas"
          >
            Ver menos
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-1.5 pt-0">
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Cargando calendario…
          </div>
        )}
        {!isLoading && items.length === 0 && (
          <p className="text-xs text-muted-foreground italic">
            No hay efemerides relevantes en los próximos {days} días.
          </p>
        )}
        {!isLoading && items.length > 0 && (
          <p className="pt-1 text-[10px] text-muted-foreground/80">
            Mostrando {items.length} de {allRelevant.length} fechas relevantes (viralidad alta+media)
          </p>
        )}
        {items.map((e) => {
          const v = VIRALIDAD_META[e.viralidad];
          const converted = convertedIds.has(e.id);
          const isConverting = convertingId === e.id;
          return (
            <div
              key={e.id}
              className="flex items-center gap-3 rounded-md border border-border/40 bg-card/50 px-3 py-2 text-sm transition-colors hover:bg-muted/30"
              data-testid={`efemeride-${e.id}`}
            >
              <div className="flex w-16 shrink-0 flex-col items-center rounded bg-muted/40 px-1.5 py-1">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  {fmtFecha(e.fecha_proxima).split(" ")[1] ?? ""}
                </span>
                <span className="font-heading text-sm font-bold leading-none">{e.dia}</span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="line-clamp-1 text-sm font-medium leading-tight">{e.titulo}</p>
                <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[10px] text-muted-foreground">
                  <Badge variant="outline" className={cn("gap-1 px-1 py-0 text-[9px] uppercase", v.cls)}>
                    {e.viralidad === "alta" && <Flame className="h-2.5 w-2.5" />}
                    {v.label}
                  </Badge>
                  <span>· {e.dias_hasta}d</span>
                  {e.ideas_politicas?.length > 0 && (
                    <span className="line-clamp-1">
                      · {e.ideas_politicas.slice(0, 3).join(" · ")}
                    </span>
                  )}
                </div>
              </div>
              {isAdmin && (
                <Button
                  size="sm"
                  variant={converted ? "outline" : "ghost"}
                  disabled={converted || isConverting}
                  onClick={() => handleConvertir(e)}
                  className="h-7 shrink-0 text-[11px]"
                  data-testid={`btn-convertir-${e.id}`}
                >
                  {isConverting ? (
                    <>
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      Convirtiendo
                    </>
                  ) : converted ? (
                    "✓ Convertida"
                  ) : (
                    <>
                      <Plus className="mr-1 h-3 w-3" />
                      Recomendación
                    </>
                  )}
                </Button>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
