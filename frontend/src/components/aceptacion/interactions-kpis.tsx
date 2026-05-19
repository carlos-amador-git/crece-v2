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
}

export function InteractionsKPIs({ dirigenteId, days = 44 }: InteractionsKPIsProps) {
  const { data, isLoading, isError } = useWatchedInteractionsSummary(dirigenteId, days);

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

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label={`Reacciones · ${data.window_days}d`}
          value={formatNumber(data.total_reactions)}
          icon={Heart}
          variant="compact"
        />
        <StatCard
          label={`Comments · ${data.window_days}d`}
          value={formatNumber(data.total_comments)}
          icon={MessageSquare}
          variant="compact"
        />
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
          label="Posts en ventana"
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
