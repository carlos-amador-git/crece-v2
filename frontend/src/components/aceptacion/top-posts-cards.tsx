"use client";

/**
 * Sprint C · PLAN-2026-05-17-fans-dashboard.md
 *
 * 2 columnas (Ganadores | Críticos) con los top 3 posts por polaridad
 * neta de comments. Click en una card abre modal con sample_quotes
 * (3 quotes anónimas alineadas con la polaridad — winners: ≥+1, losers: ≤-1).
 *
 * Riesgo R-7 mitigado: el endpoint backend ya devuelve `LEFT(content, 140)`
 * + sin `author_hash` para evitar identificación contextual.
 *
 * Si NLP backfill (Sprint D) aún no ha clasificado suficientes comments
 * el endpoint devuelve [] → empty state legítimo, NO mock numérico.
 */

import { useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  ExternalLink,
  MessageSquare,
  ThumbsUp,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useWatchedTopPosts,
  type TopPostItem,
} from "@/lib/api/hooks/use-watched-profiles";
import { formatNumber } from "@/lib/utils";

interface TopPostsCardsProps {
  dirigenteId: number;
  days?: number;
  limit?: number;
  /** D-PLATFORM-SELECTOR-2026-05-21 · None=cross */
  platform?: string;
}

function fmtDate(iso: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
}

function PostCard({
  item,
  kind,
  onClick,
}: {
  item: TopPostItem;
  kind: "winners" | "losers";
  onClick: () => void;
}) {
  const winner = kind === "winners";
  const accentText = winner ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400";
  const Icon = winner ? ArrowUpRight : ArrowDownRight;
  const pol = item.avg_polaridad ?? 0;
  return (
    <button
      type="button"
      onClick={onClick}
      className="group w-full rounded-lg border bg-card p-3 text-left transition-all hover:border-foreground/20 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="tabular-nums">{fmtDate(item.published_at)}</span>
          {item.post_url && (
            <ExternalLink
              className="h-3 w-3 opacity-60 group-hover:opacity-100"
              onClick={(e) => {
                e.stopPropagation();
                window.open(item.post_url!, "_blank", "noopener,noreferrer");
              }}
            />
          )}
        </div>
        <span className={`inline-flex items-center gap-0.5 text-xs font-medium tabular-nums ${accentText}`}>
          <Icon className="h-3 w-3" />
          {pol > 0 ? "+" : ""}
          {pol.toFixed(2)}
        </span>
      </div>
      <p className="mt-2 line-clamp-3 text-sm leading-snug">
        {item.content_snippet || <span className="italic text-muted-foreground">Sin texto</span>}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground tabular-nums">
        <span className="inline-flex items-center gap-1">
          <ThumbsUp className="h-3 w-3" />
          {formatNumber(item.likes)}
        </span>
        <span className="inline-flex items-center gap-1">
          <MessageSquare className="h-3 w-3" />
          {formatNumber(item.n_comments)}
        </span>
        <span
          className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium ${
            item.n_classified_comments < 5
              ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200"
              : "bg-muted text-muted-foreground"
          }`}
          title={
            item.n_classified_comments < 5
              ? "Muestra pequeña: el promedio se calcula sobre pocos comments y puede no reflejar opinión generalizada"
              : "Comments clasificados por NLP que entran al promedio"
          }
        >
          Muestra: {item.n_classified_comments} {item.n_classified_comments === 1 ? "comment" : "comments"} NLP
          {item.n_classified_comments < 5 && " · pequeña"}
        </span>
      </div>
    </button>
  );
}

function EmptyState({ kind }: { kind: "winners" | "losers" }) {
  return (
    <div className="rounded-lg border border-dashed bg-muted/30 p-4 text-center">
      <p className="text-xs text-muted-foreground">
        Sin posts con {kind === "winners" ? "recepción favorable" : "rechazo concentrado"} en este periodo.
        <br />
        <span className="text-[10px]">Requiere posts con likes ≥ 1 y ≥3 comments clasificados por NLP.</span>
      </p>
    </div>
  );
}

function Column({
  kind,
  items,
  isLoading,
  onSelect,
}: {
  kind: "winners" | "losers";
  items: TopPostItem[];
  isLoading: boolean;
  onSelect: (item: TopPostItem) => void;
}) {
  const winner = kind === "winners";
  const Icon = winner ? TrendingUp : TrendingDown;
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Icon
            className={`h-4 w-4 ${
              winner ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
            }`}
          />
          {winner ? "Más audiencia favorable" : "Más rechazo en comments"}
          <Badge variant="outline" className="ml-auto font-normal">
            {items.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-2.5">
        {isLoading ? (
          <>
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </>
        ) : items.length === 0 ? (
          <EmptyState kind={kind} />
        ) : (
          items.map((it) => (
            <PostCard key={it.post_id} item={it} kind={kind} onClick={() => onSelect(it)} />
          ))
        )}
      </CardContent>
    </Card>
  );
}

export function TopPostsCards({ dirigenteId, days = 30, limit = 3, platform }: TopPostsCardsProps) {
  const winnersQ = useWatchedTopPosts(dirigenteId, "winners", limit, days, platform);
  const losersQ = useWatchedTopPosts(dirigenteId, "losers", limit, days, platform);
  const [selected, setSelected] = useState<{ item: TopPostItem; kind: "winners" | "losers" } | null>(null);

  return (
    <>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Column
          kind="winners"
          items={winnersQ.data ?? []}
          isLoading={winnersQ.isLoading}
          onSelect={(it) => setSelected({ item: it, kind: "winners" })}
        />
        <Column
          kind="losers"
          items={losersQ.data ?? []}
          isLoading={losersQ.isLoading}
          onSelect={(it) => setSelected({ item: it, kind: "losers" })}
        />
      </div>

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-lg">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="text-base">
                  Post del {fmtDate(selected.item.published_at)}
                  <Badge
                    variant="outline"
                    className={`ml-2 ${
                      selected.kind === "winners"
                        ? "border-emerald-500/30 bg-emerald-50 text-emerald-700"
                        : "border-rose-500/30 bg-rose-50 text-rose-700"
                    }`}
                  >
                    {selected.kind === "winners" ? "Ganador" : "Crítico"} ·{" "}
                    {(selected.item.avg_polaridad ?? 0).toFixed(2)}
                  </Badge>
                </DialogTitle>
                <DialogDescription className="line-clamp-4 text-sm">
                  {selected.item.content_snippet}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Comentarios representativos ({selected.item.sample_quotes.length}):
                </p>
                {selected.item.sample_quotes.length === 0 ? (
                  <p className="rounded-md bg-muted/30 p-3 text-xs italic text-muted-foreground">
                    Sin quotes representativas disponibles.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {selected.item.sample_quotes.map((q, i) => (
                      <li
                        key={i}
                        className={`rounded-md border-l-2 px-3 py-2 text-sm ${
                          q.polaridad > 0
                            ? "border-emerald-500 bg-emerald-50/50"
                            : q.polaridad < 0
                              ? "border-rose-500 bg-rose-50/50"
                              : "border-muted-foreground/30 bg-muted/30"
                        }`}
                      >
                        <p className="leading-snug">{q.text}</p>
                        <p className="mt-1 text-[10px] tabular-nums text-muted-foreground">
                          polaridad {q.polaridad > 0 ? "+" : ""}
                          {q.polaridad}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {selected.item.post_url && (
                <a
                  href={selected.item.post_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
                >
                  Ver post original
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
