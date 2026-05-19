"use client";

/**
 * Sprint C · PLAN-2026-05-17-fans-dashboard.md
 *
 * Ranking nominal de los top 20 perfiles observados ordenados por
 * score = reactions × 1 + comments × 2.5.
 *
 * VIP overrides aplicados vía `applyVipOverrides()` — mockup frontend
 * que inserta Misael en posición 1 para Saymi (D-3 del plan, BD
 * jamás se toca). Política R-3: el override SOLO se aplica en este
 * hook, ningún otro componente analítico lo usa.
 *
 * Filtros por `source`: cliente_seed | competidor | auto_suggested | all.
 */

import { useMemo, useState } from "react";
import { Crown, Flame, Filter, MessageSquare, Search, ThumbsUp, UserMinus, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useWatchedProfiles,
  type WatchedProfile,
  type WatchedSource,
} from "@/lib/api/hooks/use-watched-profiles";
import { applyVipOverrides, type FanRankingEntry } from "@/lib/api/utils/vip-overrides";
import { formatNumber } from "@/lib/utils";

interface TopFansRankingProps {
  dirigenteId: number;
  limit?: number;
}

const SOURCE_LABEL: Record<string, string> = {
  all: "Todos",
  cliente_seed: "Cliente",
  competidor: "Competidor",
  auto_suggested: "Sugeridos",
};

const PLATFORM_DOT: Record<string, string> = {
  FACEBOOK: "bg-blue-600",
  INSTAGRAM: "bg-pink-500",
  TWITTER: "bg-sky-500",
  TIKTOK: "bg-neutral-800",
  YOUTUBE: "bg-red-500",
};

function rankDecor(idx: number) {
  if (idx === 0) return { icon: Crown, color: "text-amber-500" };
  if (idx === 1) return { icon: Flame, color: "text-orange-500" };
  if (idx === 2) return { icon: Flame, color: "text-orange-300" };
  return null;
}

export function TopFansRanking({ dirigenteId, limit = 20 }: TopFansRankingProps) {
  const [sourceFilter, setSourceFilter] = useState<WatchedSource | "all">("all");
  const [query, setQuery] = useState("");

  const { data: profiles, isLoading } = useWatchedProfiles({
    dirigente_id: dirigenteId,
    source: sourceFilter === "all" ? undefined : sourceFilter,
  });

  const ranking: FanRankingEntry[] = useMemo(() => {
    const raw = (profiles ?? []).map((p: WatchedProfile) => ({
      external_id: p.profile_external_id,
      display_name: p.display_name,
      handle: p.profile_handle,
      platform: p.platform,
      source: p.source,
      reactions: p.n_likes ?? 0,
      comments: p.n_comments ?? 0,
    }));
    const withVip = applyVipOverrides(dirigenteId, raw);
    const q = query.trim().toLowerCase();
    const filtered = q
      ? withVip.filter(
          (e) =>
            (e.display_name?.toLowerCase().includes(q) ?? false) ||
            (e.handle?.toLowerCase().includes(q) ?? false) ||
            e.external_id.toLowerCase().includes(q)
        )
      : withVip;
    return filtered.slice(0, limit);
  }, [profiles, dirigenteId, query, limit]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Users className="h-4 w-4" />
          Top Fans
          <Badge variant="outline" className="ml-auto font-normal">
            {ranking.length}
          </Badge>
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Score = reacciones × 1 + comentarios × 2.5. Top {limit}.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Tabs
            value={sourceFilter}
            onValueChange={(v) => setSourceFilter(v as WatchedSource | "all")}
          >
            <TabsList className="h-8">
              {(["all", "cliente_seed", "competidor", "auto_suggested"] as const).map(
                (s) => (
                  <TabsTrigger key={s} value={s} className="text-xs">
                    {SOURCE_LABEL[s]}
                  </TabsTrigger>
                )
              )}
            </TabsList>
          </Tabs>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Filtrar por nombre/handle…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-8 pl-8 text-xs"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : ranking.length === 0 ? (
          <div className="rounded-lg border border-dashed bg-muted/30 p-6 text-center">
            <UserMinus className="mx-auto h-5 w-5 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">
              Sin perfiles observados que coincidan con el filtro.
            </p>
          </div>
        ) : (
          <ol className="space-y-1.5">
            {ranking.map((entry, idx) => {
              const decor = rankDecor(idx);
              const platColor = PLATFORM_DOT[entry.platform] ?? "bg-muted-foreground";
              return (
                <li
                  key={entry.external_id}
                  className={`flex items-center gap-3 rounded-md px-2.5 py-2 transition-colors ${
                    entry.isVip ? "border border-amber-400/40 bg-amber-50/60 dark:bg-amber-950/20" : "hover:bg-muted/50"
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
                      {entry.badge && (
                        <Badge
                          variant="outline"
                          className="border-amber-500/40 bg-amber-100/60 text-[10px] text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                        >
                          {entry.badge}
                        </Badge>
                      )}
                      {decor && !entry.isVip && (
                        <decor.icon className={`h-3.5 w-3.5 ${decor.color}`} />
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      {SOURCE_LABEL[entry.source] ?? entry.source} ·{" "}
                      {entry.handle ?? entry.external_id}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground tabular-nums">
                    <span className="inline-flex items-center gap-1">
                      <ThumbsUp className="h-3 w-3" />
                      {formatNumber(entry.reactions)}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <MessageSquare className="h-3 w-3" />
                      {formatNumber(entry.comments)}
                    </span>
                    <span className="font-semibold text-foreground tabular-nums">
                      {formatNumber(Math.round(entry.score))}
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
