"use client";

import { EvaluadorRow } from "./EvaluadorRow";
import type { HitlPost, HitlEditPayload } from "@/lib/api/hitl";
import {
  ExternalLink,
  Heart,
  MessageSquare,
  Share2,
} from "lucide-react";
import { formatNumber, formatRelativeTime } from "@/lib/utils";

interface Props {
  post: HitlPost;
  saving?: boolean;
  error?: string | null;
  onSave: (id: number, payload: HitlEditPayload) => Promise<void>;
  onConfirm: (id: number) => Promise<void>;
}

export function PostEvaluator({
  post,
  saving,
  error,
  onSave,
  onConfirm,
}: Props) {
  return (
    <EvaluadorRow
      reviewStatus={post.review_status}
      systemTono={post.nlp_tono}
      systemTarget={post.nlp_target}
      systemOffTopic={post.off_topic}
      saving={saving}
      error={error}
      onSave={(payload) => onSave(post.id, payload)}
      onConfirm={() => onConfirm(post.id)}
    >
      <header className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {post.platform && (
            <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
              {post.platform}
            </span>
          )}
          {post.published_at && (
            <span>{formatRelativeTime(post.published_at)}</span>
          )}
          {post.url && (
            <a
              href={post.url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <ExternalLink className="h-3 w-3" />
              Abrir publicación
            </a>
          )}
        </div>
        <p className="text-sm leading-relaxed text-foreground line-clamp-4">
          {post.content ?? "—"}
        </p>
        <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground tabular-nums">
          <span className="flex items-center gap-1">
            <Heart className="h-3 w-3" />
            {formatNumber(post.likes ?? 0)}
          </span>
          <span className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            {formatNumber(post.comments ?? 0)}
          </span>
          <span className="flex items-center gap-1">
            <Share2 className="h-3 w-3" />
            {formatNumber(post.shares ?? 0)}
          </span>
        </div>
      </header>
    </EvaluadorRow>
  );
}
