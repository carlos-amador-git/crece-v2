"use client";

import { EvaluadorRow } from "./EvaluadorRow";
import type { HitlComment, HitlEditPayload } from "@/lib/api/hitl";
import { ExternalLink, MessageCircle } from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";

interface Props {
  comment: HitlComment;
  saving?: boolean;
  error?: string | null;
  hideParentContext?: boolean;
  onSave: (id: number, payload: HitlEditPayload) => Promise<void>;
  onConfirm: (id: number) => Promise<void>;
}

export function CommentEvaluator({
  comment,
  saving,
  error,
  hideParentContext = false,
  onSave,
  onConfirm,
}: Props) {
  return (
    <EvaluadorRow
      reviewStatus={comment.review_status}
      systemTono={comment.nlp_tono}
      systemTarget={comment.nlp_target}
      systemOffTopic={comment.off_topic}
      saving={saving}
      error={error}
      onSave={(payload) => onSave(comment.id, payload)}
      onConfirm={() => onConfirm(comment.id)}
    >
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <MessageCircle className="h-3.5 w-3.5" />
          <span>
            {comment.author_username
              ? `@${comment.author_username}`
              : "Autor anónimo"}
          </span>
          {comment.platform && (
            <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
              {comment.platform}
            </span>
          )}
          {comment.published_at && (
            <span>{formatRelativeTime(comment.published_at)}</span>
          )}
          {!hideParentContext && comment.parent_post_url && (
            <a
              href={comment.parent_post_url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
            >
              Ver post original
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
        {!hideParentContext && (comment.parent_post_snippet || comment.parent_post_url) && (
          <div className="rounded-md border-l-2 border-accent/40 bg-muted/40 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              En respuesta a esta publicación
            </p>
            {comment.parent_post_snippet ? (
              <p className="mt-1 line-clamp-2 text-xs italic text-foreground/80">
                {comment.parent_post_snippet}
              </p>
            ) : (
              <p className="mt-1 text-xs italic text-muted-foreground">
                (sin texto disponible — abre el enlace para ver)
              </p>
            )}
          </div>
        )}
        <p className="text-sm leading-relaxed text-foreground">
          {comment.content ?? "—"}
        </p>
      </header>
    </EvaluadorRow>
  );
}
