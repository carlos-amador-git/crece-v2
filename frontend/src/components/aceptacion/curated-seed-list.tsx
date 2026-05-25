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
 * Política R-3 D-3: BD jamás se toca aquí. Override VIP aplica también AQUÍ
 * post-2026-05-20 (CEO 3a corrección): Misael debe verse #1 con 250 reactions
 * en AMBAS listas (TopFansRanking + Audiencia Objetivo) para consistencia
 * visual. Antes solo TopFansRanking aplicaba override → Misael salía #1 ahí
 * pero en Audiencia Objetivo aparecía con sus 87 reactions reales en #2. CEO
 * marcó la inconsistencia 3 veces.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWatchedProfiles } from "@/lib/api/hooks/use-watched-profiles";
import { applyVipOverrides } from "@/lib/api/utils/vip-overrides";
import { formatNumber } from "@/lib/utils";
import { MessageSquare, ThumbsUp, Users } from "lucide-react";

interface CuratedSeedListProps {
  dirigenteId: number;
  platform?: string;
}

const PLATFORM_DOT: Record<string, string> = {
  FACEBOOK: "bg-blue-600",
  INSTAGRAM: "bg-pink-500",
  TWITTER: "bg-sky-500",
  TIKTOK: "bg-neutral-800",
  YOUTUBE: "bg-red-500",
};

export function CuratedSeedList({ dirigenteId, platform }: CuratedSeedListProps) {
  const { data: profiles, isLoading } = useWatchedProfiles({
    dirigente_id: dirigenteId,
    source: "cliente_seed",
    platform: platform,
  });

  // Aplicar VIP override (Misael Fan #1 con 250 per CEO 2026-05-20).
  // applyVipOverrides matchea por external_id · si Misael cliente_seed
  // (61578398601244) está en la lista, lo REEMPLAZA con override 250r/12c
  // y fuerza posición 1.
  const ranked = applyVipOverrides(
    dirigenteId,
    (profiles ?? []).map((p) => ({
      external_id: p.profile_external_id,
      display_name: p.display_name,
      handle: p.profile_handle,
      platform: p.platform,
      source: p.source,
      reactions: p.n_likes ?? 0,
      comments: p.n_comments ?? 0,
    })),
  );

  const activos = ranked.filter((p) => p.reactions > 0).length;
  const total = ranked.length;

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
          Perfiles curados por el cliente · perfiles VIP destacados al inicio.
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
            {ranked.map((entry, idx) => {
              const platColor =
                PLATFORM_DOT[entry.platform] ?? "bg-muted-foreground";
              const reactions = entry.reactions;
              const comments = entry.comments;
              const isInactive = reactions === 0 && comments === 0;
              const isVip = entry.isVip;
              return (
                <li
                  key={entry.external_id}
                  className={`flex items-center gap-3 rounded-md px-2.5 py-2 transition-colors ${
                    isInactive
                      ? "opacity-60"
                      : isVip
                        ? "bg-amber-50/50 dark:bg-amber-950/20 hover:bg-amber-50 dark:hover:bg-amber-950/30"
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
                        {entry.display_name || entry.handle || entry.external_id}
                      </span>
                      {isVip && entry.badge && (
                        <Badge
                          variant="outline"
                          className="border-amber-500/40 text-[10px] text-amber-700 dark:text-amber-300"
                          title="Perfil VIP destacado por decisión de cliente"
                        >
                          {entry.badge}
                        </Badge>
                      )}
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
                      Cliente · {entry.handle ?? entry.external_id}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground tabular-nums">
                    <span
                      className="inline-flex items-center gap-1"
                      title={isVip ? "Reactions destacadas (override cliente)" : "Reactions capturadas en BD"}
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
