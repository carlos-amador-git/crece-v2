"use client";

import { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronDown, ExternalLink, MessageCircle } from "lucide-react";
import type { HitlComment, HitlEditPayload } from "@/lib/api/hitl";
import { CommentEvaluator } from "./CommentEvaluator";

interface RowFeedback {
  saving: boolean;
  error: string | null;
}

interface Props {
  comments: HitlComment[];
  rowState: Record<string, RowFeedback>;
  onSave: (id: number, payload: HitlEditPayload) => Promise<void>;
  onConfirm: (id: number) => Promise<void>;
}

interface PostGroup {
  parent_post_id: number | null;
  parent_post_url: string | null;
  parent_post_snippet: string | null;
  platform: string | null;
  comments: HitlComment[];
  pendingCount: number;
}

function groupByPost(comments: HitlComment[]): PostGroup[] {
  const map = new Map<string, PostGroup>();
  for (const c of comments) {
    const key = c.parent_post_id != null ? String(c.parent_post_id) : "orphan";
    if (!map.has(key)) {
      map.set(key, {
        parent_post_id: c.parent_post_id,
        parent_post_url: c.parent_post_url ?? null,
        parent_post_snippet: c.parent_post_snippet ?? null,
        platform: c.platform,
        comments: [],
        pendingCount: 0,
      });
    }
    const g = map.get(key)!;
    g.comments.push(c);
    if (!c.review_status || c.review_status === "unreviewed") g.pendingCount++;
  }
  return Array.from(map.values()).sort(
    (a, b) => b.comments.length - a.comments.length
  );
}

export function CommentsGroupedByPost({
  comments,
  rowState,
  onSave,
  onConfirm,
}: Props) {
  const groups = useMemo(() => groupByPost(comments), [comments]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    // Default: primer grupo expandido, resto colapsados
    const init: Record<string, boolean> = {};
    groups.forEach((g, idx) => {
      const k = String(g.parent_post_id ?? "orphan");
      init[k] = idx === 0;
    });
    return init;
  });

  if (groups.length === 0) {
    return (
      <Card>
        <CardContent className="p-4 text-sm text-muted-foreground">
          No hay comentarios pendientes con los filtros actuales.
        </CardContent>
      </Card>
    );
  }

  const toggle = (k: string) => setExpanded((prev) => ({ ...prev, [k]: !prev[k] }));
  const expandAll = () => {
    const next: Record<string, boolean> = {};
    groups.forEach((g) => { next[String(g.parent_post_id ?? "orphan")] = true; });
    setExpanded(next);
  };
  const collapseAll = () => setExpanded({});

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {groups.length} {groups.length === 1 ? "publicación con comentarios" : "publicaciones con comentarios"}
        </span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={expandAll}>
            Expandir todo
          </Button>
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={collapseAll}>
            Colapsar todo
          </Button>
        </div>
      </div>

      {groups.map((g) => {
        const k = String(g.parent_post_id ?? "orphan");
        const isOpen = expanded[k] ?? false;
        return (
          <Card key={k} className="overflow-hidden">
            <button
              type="button"
              onClick={() => toggle(k)}
              className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/40"
              aria-expanded={isOpen}
            >
              <ChevronDown
                className={`mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform ${isOpen ? "" : "-rotate-90"}`}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {g.platform && (
                    <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                      {g.platform}
                    </span>
                  )}
                  <span className="inline-flex items-center gap-1 rounded-sm bg-accent/10 px-1.5 py-0.5 text-[10px] font-medium text-accent">
                    <MessageCircle className="h-3 w-3" />
                    {g.comments.length} {g.comments.length === 1 ? "comentario" : "comentarios"}
                  </span>
                  {g.pendingCount > 0 && g.pendingCount < g.comments.length && (
                    <span className="rounded-sm bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                      {g.pendingCount} pendiente{g.pendingCount === 1 ? "" : "s"}
                    </span>
                  )}
                </div>
                <p className="mt-1.5 line-clamp-2 text-sm text-foreground/90">
                  {g.parent_post_snippet ?? "(post sin texto disponible)"}
                </p>
              </div>
              {g.parent_post_url && (
                <a
                  href={g.parent_post_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="shrink-0 inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium text-accent hover:bg-accent/10"
                >
                  Ver post
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </button>
            {isOpen && (
              <div className="space-y-3 border-t bg-muted/10 px-4 py-3">
                {g.comments.map((c) => {
                  const fb = rowState[`comment-${c.id}`];
                  return (
                    <CommentEvaluator
                      key={`comment-${c.id}`}
                      comment={c}
                      saving={fb?.saving}
                      error={fb?.error}
                      hideParentContext
                      onSave={onSave}
                      onConfirm={onConfirm}
                    />
                  );
                })}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
