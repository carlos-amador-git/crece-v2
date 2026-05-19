"use client";

/**
 * P1 #8 · 2026-05-19 · split-view cliente_seed
 *
 * Lista estática de los perfiles `cliente_seed` (audiencia curada por el
 * cliente/asesor del dirigente). Se renderiza al costado del TopFansRanking
 * para que el cliente vea siempre la lista completa que él curó, NO solo
 * cuando activamente filtra por "Cliente" en el ranking general.
 *
 * Diseño per Gemini approve_split_view (OBS-7):
 * - Zero-state visual intencional cuando un curado tiene 0 reactions
 *   (texto muted + tag "Inactivo") → evita que usuario asuma error de carga.
 * - Misma fuente de datos que TopFansRanking (useWatchedProfiles), pero
 *   filtrada en render a source='cliente_seed' (NO se modifican los hooks).
 *
 * Política R-3 D-3: BD jamás se toca aquí. Override VIP Misael (D-MISAEL-VIP-40)
 * se mantiene SOLO en TopFansRanking → en CuratedSeedList Misael aparece con
 * sus reactions reales (10), no con el override 40.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useWatchedProfiles,
  type WatchedProfile,
} from "@/lib/api/hooks/use-watched-profiles";
import { formatNumber } from "@/lib/utils";
import { MessageSquare, ThumbsUp, Users } from "lucide-react";

interface CuratedSeedListProps {
  dirigenteId: number;
}

const PLATFORM_DOT: Record<string, string> = {
  FACEBOOK: "bg-blue-600",
  INSTAGRAM: "bg-pink-500",
  TWITTER: "bg-sky-500",
  TIKTOK: "bg-neutral-800",
  YOUTUBE: "bg-red-500",
};

export function CuratedSeedList({ dirigenteId }: CuratedSeedListProps) {
  const { data: profiles, isLoading } = useWatchedProfiles({
    dirigente_id: dirigenteId,
    source: "cliente_seed",
  });

  const sorted: WatchedProfile[] = (profiles ?? [])
    .slice()
    .sort((a, b) => (b.n_likes ?? 0) - (a.n_likes ?? 0));

  const activos = sorted.filter((p) => (p.n_likes ?? 0) > 0).length;
  const total = sorted.length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Users className="h-4 w-4 text-violet-600" />
          Audiencia Objetivo
          <Badge
            variant="outline"
            className="ml-auto border-violet-500/40 font-normal text-violet-700 dark:text-violet-300"
          >
            {total}
          </Badge>
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Perfiles curados por el cliente · ordenados por reacciones reales en
          BD.
          {total > 0 && (
            <>
              {" "}
              <strong>
                {activos} de {total}
              </strong>{" "}
              con actividad detectada.
            </>
          )}
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : total === 0 ? (
          <div className="rounded-lg border border-dashed bg-muted/30 p-6 text-center">
            <Users className="mx-auto h-5 w-5 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">
              Sin perfiles curados todavía.
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground/70">
              El cliente o asesor puede agregar perfiles a monitorear desde la
              vista de administración.
            </p>
          </div>
        ) : (
          <ol className="space-y-1.5">
            {sorted.map((entry, idx) => {
              const platColor =
                PLATFORM_DOT[entry.platform] ?? "bg-muted-foreground";
              const reactions = entry.n_likes ?? 0;
              const comments = entry.n_comments ?? 0;
              const isInactive = reactions === 0 && comments === 0;
              return (
                <li
                  key={entry.profile_external_id}
                  className={`flex items-center gap-3 rounded-md px-2.5 py-2 transition-colors ${
                    isInactive
                      ? "opacity-60"
                      : "hover:bg-muted/50"
                  }`}
                >
                  <span className="w-7 shrink-0 text-center text-xs font-semibold tabular-nums text-muted-foreground">
                    #{idx + 1}
                  </span>
                  <span
                    className={`inline-block h-1.5 w-1.5 rounded-full ${platColor}`}
                    title={entry.platform}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 text-sm font-medium leading-tight">
                      <span className="truncate">
                        {entry.display_name ||
                          entry.profile_handle ||
                          entry.profile_external_id}
                      </span>
                      {isInactive && (
                        <Badge
                          variant="outline"
                          className="border-dashed text-[10px] text-muted-foreground"
                          title="Sin reactions ni comments capturados en la ventana actual"
                        >
                          Inactivo
                        </Badge>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      Cliente · {entry.profile_handle ?? entry.profile_external_id}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground tabular-nums">
                    <span
                      className="inline-flex items-center gap-1"
                      title="Reactions capturadas en BD (reales · sin override VIP)"
                    >
                      <ThumbsUp className="h-3 w-3" />
                      {formatNumber(reactions)}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <MessageSquare className="h-3 w-3" />
                      {formatNumber(comments)}
                    </span>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
