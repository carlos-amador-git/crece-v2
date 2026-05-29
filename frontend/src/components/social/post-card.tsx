"use client";

import { useState } from "react";
import type { SocialPost } from "@/lib/api/types";
import { Card, CardContent } from "@/components/ui/card";
import { PlatformIcon } from "./platform-icon";
import { SentimentBadge } from "./sentiment-badge";
import { formatRelativeTime, formatNumber } from "@/lib/utils";
import { Heart, MessageCircle, Share2, Eye, ExternalLink } from "lucide-react";

interface PostCardProps {
  post: SocialPost;
}

const PLATFORM_LABELS: Record<string, string> = {
  twitter: "Twitter",
  x: "X (Twitter)",
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  youtube: "YouTube",
  bluesky: "Bluesky",
};

export function PostCard({ post }: PostCardProps) {
  const hasUrl = Boolean(post.url && post.url.trim().length > 0);
  const platformLabel =
    PLATFORM_LABELS[post.platform?.toLowerCase() ?? ""] ??
    (post.platform ? post.platform.charAt(0).toUpperCase() + post.platform.slice(1) : "Red social");
  const thumbnail = post.media_urls?.[0];
  const [imgFailed, setImgFailed] = useState(false);
  const showThumb = Boolean(thumbnail) && !imgFailed;

  const cardInner = (
    <CardContent className="p-4">
      <div className="flex items-start gap-3">
        {/* Miniatura · spm_media1 · 60×60 con fallback a PlatformIcon · 2026-05-12 */}
        <div className="relative shrink-0">
          {showThumb ? (
            <div className="relative h-[60px] w-[60px] overflow-hidden rounded-md border bg-muted">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={thumbnail}
                alt=""
                loading="lazy"
                referrerPolicy="no-referrer"
                onError={() => setImgFailed(true)}
                className="h-full w-full object-cover"
              />
              {/* Mini-badge plataforma sobre la miniatura */}
              <div className="absolute bottom-0.5 right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-background/90 ring-1 ring-border">
                <PlatformIcon platform={post.platform} size={10} />
              </div>
            </div>
          ) : (
            <div
              className="flex h-[60px] w-[60px] flex-col items-center justify-center gap-1 rounded-md border bg-muted/40"
              aria-label={platformLabel}
            >
              <PlatformIcon platform={post.platform} size={20} />
              <span className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground/80">
                {platformLabel.slice(0, 5)}
              </span>
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {post.dirigente_nombre && (
                <span className="text-sm font-medium">
                  {post.dirigente_nombre}
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                {formatRelativeTime(post.published_at)}
              </span>
            </div>
            <SentimentBadge
              sentiment={post.sentiment_label}
              score={post.sentiment_score}
              tonoDiscurso={post.tono_discurso}
            />
          </div>
          <p className="mb-3 line-clamp-3 text-sm text-foreground/90">
            {post.content}
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-foreground tabular-nums">
            <span className="flex items-center gap-1" aria-label={`${formatNumber(post.likes)} me gusta`}>
              <Heart className="h-3.5 w-3.5" />
              <span className="font-medium">{formatNumber(post.likes)}</span>
              <span className="text-[10px] text-muted-foreground/70">likes</span>
            </span>
            <span className="flex items-center gap-1" aria-label={`${formatNumber(post.comments)} comentarios`}>
              <MessageCircle className="h-3.5 w-3.5" />
              <span className="font-medium">{formatNumber(post.comments)}</span>
              <span className="text-[10px] text-muted-foreground/70">coment.</span>
            </span>
            <span className="flex items-center gap-1" aria-label={`${formatNumber(post.shares)} compartidos`}>
              <Share2 className="h-3.5 w-3.5" />
              <span className="font-medium">{formatNumber(post.shares)}</span>
              <span className="text-[10px] text-muted-foreground/70">shares</span>
            </span>
            {post.views != null && (
              <span className="flex items-center gap-1" aria-label={`${formatNumber(post.views)} vistas`}>
                <Eye className="h-3.5 w-3.5" />
                <span className="font-medium">{formatNumber(post.views)}</span>
                <span className="text-[10px] text-muted-foreground/70">vistas</span>
              </span>
            )}
            {hasUrl && (
              <span className="ml-auto flex items-center gap-1 text-muted-foreground/80">
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="text-[10px]">Abrir</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </CardContent>
  );

  if (hasUrl) {
    return (
      <a
        href={post.url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`Abrir publicación en ${platformLabel}`}
        className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Card className="transition-shadow hover:shadow-md cursor-pointer">
          {cardInner}
        </Card>
      </a>
    );
  }

  return <Card className="transition-shadow hover:shadow-md">{cardInner}</Card>;
}
