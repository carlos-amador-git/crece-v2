import type { SocialPost } from "@/lib/api/types";
import { Card, CardContent } from "@/components/ui/card";
import { PlatformIcon } from "./platform-icon";
import { SentimentBadge } from "./sentiment-badge";
import { formatRelativeTime, formatNumber } from "@/lib/utils";
import { Heart, MessageCircle, Share2, Eye, ExternalLink } from "lucide-react";

interface PostCardProps {
  post: SocialPost;
}

export function PostCard({ post }: PostCardProps) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5">
            <PlatformIcon platform={post.platform} size={20} />
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
                sentiment={post.sentiment}
                score={post.sentiment_score}
              />
            </div>
            <p className="mb-3 line-clamp-3 text-sm text-foreground/90">
              {post.content}
            </p>
            <div className="flex items-center gap-4 text-xs text-muted-foreground tabular-nums">
              <span className="flex items-center gap-1" aria-label={`${formatNumber(post.likes)} me gusta`}>
                <Heart className="h-3.5 w-3.5" />
                {formatNumber(post.likes)}
              </span>
              <span className="flex items-center gap-1" aria-label={`${formatNumber(post.comments)} comentarios`}>
                <MessageCircle className="h-3.5 w-3.5" />
                {formatNumber(post.comments)}
              </span>
              <span className="flex items-center gap-1" aria-label={`${formatNumber(post.shares)} compartidos`}>
                <Share2 className="h-3.5 w-3.5" />
                {formatNumber(post.shares)}
              </span>
              {post.views != null && (
                <span className="flex items-center gap-1" aria-label={`${formatNumber(post.views)} vistas`}>
                  <Eye className="h-3.5 w-3.5" />
                  {formatNumber(post.views)}
                </span>
              )}
              <a
                href={post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto flex items-center gap-1 transition-colors hover:text-foreground"
                aria-label="Ver publicacion original"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
