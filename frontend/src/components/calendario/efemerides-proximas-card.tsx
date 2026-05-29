/**
 * EfemeridesProximasCard — lista de próximas fechas conmemorativas + botón generar post.
 * D-CALENDARIO-1 (2026-05-12).
 */
"use client";

import { useState } from "react";
import { Calendar, Sparkles, Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";

import {
  type Efemeride,
  useCalendarioProximas,
} from "@/lib/api/hooks/use-calendario";
import { SugerirPostModal } from "./sugerir-post-modal";

interface Props {
  dirigenteId: number;
  days?: number;
}

const VIRALIDAD_COLOR: Record<string, string> = {
  alta: "bg-emerald-500/15 text-emerald-700 border-emerald-500/30",
  media: "bg-amber-500/15 text-amber-700 border-amber-500/30",
  baja: "bg-slate-500/15 text-slate-700 border-slate-500/30",
};

const TIPO_LABEL: Record<string, string> = {
  civica: "Cívica",
  internacional: "Internacional",
  social: "Social",
  emocional: "Emocional",
  familiar: "Familiar",
  comunidad: "Comunidad",
};

export function EfemeridesProximasCard({ dirigenteId, days = 30 }: Props) {
  const { data, isLoading, isError } = useCalendarioProximas(days);
  const [selected, setSelected] = useState<Efemeride | null>(null);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2 text-base font-semibold">
          <Calendar className="h-4 w-4 text-accent" />
          Próximas fechas estratégicas
        </CardTitle>
        <Badge variant="outline" className="text-[10px] font-medium">
          {days} días
        </Badge>
      </CardHeader>

      <CardContent className="space-y-2 pt-0">
        {isLoading && (
          <div className="space-y-2" data-testid="efemerides-loading">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm text-destructive">
            No se pudieron cargar las fechas.
          </p>
        )}

        {data && data.length === 0 && (
          <p className="text-sm text-muted-foreground italic">
            No hay efemérides en los próximos {days} días.
          </p>
        )}

        {data && data.length > 0 && (
          <ul className="space-y-2" data-testid="efemerides-list">
            {data.slice(0, 6).map((ef) => (
              <li
                key={ef.id}
                className="flex items-start gap-3 rounded-md border border-border/60 px-3 py-2 hover:bg-accent/5 transition-colors"
              >
                <div className="min-w-[3.5rem] text-center">
                  <p className="font-heading text-lg font-bold tabular-nums leading-tight">
                    {ef.dia}
                  </p>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {new Date(ef.fecha_proxima).toLocaleDateString("es-MX", { month: "short" })}
                  </p>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <p className="text-sm font-medium leading-tight truncate">
                      {ef.titulo}
                    </p>
                    {ef.ideas_politicas.length > 0 && (
                      <Popover>
                        <PopoverTrigger asChild>
                          <button
                            type="button"
                            className="inline-flex items-center text-muted-foreground hover:text-foreground"
                            aria-label="Ver ideas políticas sugeridas"
                          >
                            <Info className="h-3.5 w-3.5" />
                          </button>
                        </PopoverTrigger>
                        <PopoverContent side="top" className="w-64 text-xs">
                          <p className="font-semibold mb-1.5">Ideas políticas sugeridas</p>
                          <ul className="space-y-0.5 list-disc list-inside text-muted-foreground">
                            {ef.ideas_politicas.map((idea) => (
                              <li key={idea}>{idea}</li>
                            ))}
                          </ul>
                        </PopoverContent>
                      </Popover>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Badge
                      variant="outline"
                      className={`text-[9px] font-bold uppercase tracking-wider ${VIRALIDAD_COLOR[ef.viralidad] ?? ""}`}
                    >
                      {ef.viralidad}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground">
                      {TIPO_LABEL[ef.tipo] ?? ef.tipo}
                    </span>
                    <span className="text-[10px] text-muted-foreground">·</span>
                    <span className="text-[10px] text-muted-foreground">
                      en {ef.dias_hasta} {ef.dias_hasta === 1 ? "día" : "días"}
                    </span>
                  </div>
                </div>

                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="shrink-0 h-7 px-2 text-[11px]"
                  onClick={() => setSelected(ef)}
                  data-testid={`generar-post-${ef.id}`}
                >
                  <Sparkles className="h-3 w-3 mr-1" />
                  Post
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>

      {selected && (
        <SugerirPostModal
          efemeride={selected}
          dirigenteId={dirigenteId}
          onClose={() => setSelected(null)}
        />
      )}
    </Card>
  );
}
