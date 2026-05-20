"use client";

/**
 * Sprint B · PLAN-2026-05-17-fans-dashboard.md
 *
 * 4 KPI cards para el header del dashboard fans:
 * - Total reactions (44d window)
 * - Total comments (44d)
 * - % comments clasificados NLP
 * - Posts en ventana
 *
 * Banner adicional si `reaction_type_quality === 'placeholder_like_only'`
 * advirtiendo que los tipos detallados están pendientes del fix RADAR Sprint 9.
 */

import { AlertTriangle, Heart, MessageSquare, Sparkles, Newspaper } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import { useWatchedInteractionsSummary } from "@/lib/api/hooks/use-watched-profiles";
import { formatNumber } from "@/lib/utils";

interface InteractionsKPIsProps {
  dirigenteId: number;
  days?: number;
  /** Si true, ignora la ventana de días y muestra el histórico completo.
   * Default true desde 2026-05-20 (CEO: "ponerlas todas, sin filtro de fecha"). */
  allTime?: boolean;
}

export function InteractionsKPIs({
  dirigenteId,
  days = 44,
  allTime = true,
}: InteractionsKPIsProps) {
  const { data, isLoading, isError } = useWatchedInteractionsSummary(dirigenteId, days, allTime);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        No se pudieron cargar los KPIs de interacciones.
      </div>
    );
  }

  const showPlaceholderBanner = data.reaction_type_quality === "placeholder_like_only";

  // window_days = null → all_time (CEO 2026-05-20: "ponerlas todas, sin filtro de fecha")
  const windowSuffix = data.window_days != null ? `${data.window_days}d` : "histórico";
  const windowTooltipSuffix = data.window_days != null
    ? `en los últimos ${data.window_days} días`
    : "en todo el histórico de captura RADAR (sin filtro de fecha)";

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* P2 #5 (2026-05-19) · glosario disonancia: el KPI cuenta reactors
            INDIVIDUALES capturados por RADAR (watched_like_events), NO los
            likes públicos del post (que sí están en social_posts.likes pero
            son snapshot Apify). Tooltip aclara la diferencia. */}
        <div
          title={`Reactors individuales capturados por RADAR ${windowTooltipSuffix} (1 evento = 1 persona reaccionó). Diferente a 'likes públicos' del post que muestran las cards (snapshot Apify).`}
        >
          <StatCard
            label={`Reacciones · ${windowSuffix}`}
            value={formatNumber(data.total_reactions)}
            icon={Heart}
            variant="compact"
          />
        </div>
        <div
          title={`Comments en posts del dirigente ${windowTooltipSuffix}. Cuenta total de comments en BD.`}
        >
          <StatCard
            label={`Comments · ${windowSuffix}`}
            value={formatNumber(data.total_comments)}
            icon={MessageSquare}
            variant="compact"
          />
        </div>
        <StatCard
          label="% Clasificados NLP"
          value={`${data.comments_classified_pct.toFixed(1)}%`}
          icon={Sparkles}
          hint={`${data.comments_classified} de ${data.total_comments}`}
          variant="compact"
          accent={
            data.comments_classified_pct >= 80
              ? "good"
              : data.comments_classified_pct >= 50
                ? "warn"
                : "bad"
          }
        />
        <StatCard
          label={data.window_days != null ? "Posts en ventana" : "Posts (histórico)"}
          value={formatNumber(data.posts_in_window)}
          icon={Newspaper}
          variant="compact"
        />
      </div>
      {showPlaceholderBanner && (
        <div
          className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
          role="status"
        >
          <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <p>
            Reacciones marcadas como <strong>“like”</strong> son placeholder — los tipos
            detallados (love, wow, haha, sad, angry) llegan con el fix RADAR Sprint 9.
          </p>
        </div>
      )}
    </div>
  );
}
