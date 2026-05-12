"use client";

import { useState, useMemo } from "react";
import { useSocialPosts } from "@/lib/api/hooks/use-social";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SentimentBadge } from "@/components/social/sentiment-badge";
import { formatNumber } from "@/lib/utils";
import { MessageSquare } from "lucide-react";
import type { SocialPost } from "@/lib/api/types";

export default function ComentariosPage() {
  const [platform, setPlatform] = useState<string>("all");
  const [sentiment, setSentiment] = useState<string>("all");

  const { data, isLoading, error } = useSocialPosts({
    page: 1,
    per_page: 100,
    platform: platform === "all" ? undefined : (platform as SocialPost["platform"]),
    sentiment: sentiment === "all" ? undefined : (sentiment as "positive" | "negative" | "neutral"),
  });

  const posts: SocialPost[] = data?.items ?? [];
  const ranked = useMemo(
    () => [...posts].sort((a, b) => (b.comments ?? 0) - (a.comments ?? 0)).slice(0, 50),
    [posts],
  );
  const totalComments = ranked.reduce((s, p) => s + (p.comments ?? 0), 0);

  return (
    <div className="space-y-6 p-6">
      <div>
        <div className="flex items-center gap-2">
          <MessageSquare className="h-6 w-6 text-accent" />
          <h1 className="font-heading text-2xl font-bold tracking-tight">
            Comentarios — conversación
          </h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Top 50 publicaciones con más comentarios. Suma de comentarios mostrados:{" "}
          {formatNumber(totalComments)}.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row">
          <div className="flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Plataforma</label>
            <Select value={platform} onValueChange={setPlatform}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="twitter">Twitter / X</SelectItem>
                <SelectItem value="instagram">Instagram</SelectItem>
                <SelectItem value="facebook">Facebook</SelectItem>
                <SelectItem value="tiktok">TikTok</SelectItem>
                <SelectItem value="youtube">YouTube</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Sentimiento</label>
            <Select value={sentiment} onValueChange={setSentiment}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="positive">Positivo</SelectItem>
                <SelectItem value="neutral">Neutral</SelectItem>
                <SelectItem value="negative">Negativo</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : error || ranked.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            Sin publicaciones que coincidan con los filtros.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Publicación</th>
                    <th className="px-4 py-2 text-left font-medium">Plataforma</th>
                    <th className="px-4 py-2 text-left font-medium">Sentimiento</th>
                    <th className="px-4 py-2 text-right font-medium">Comentarios</th>
                    <th className="px-4 py-2 text-right font-medium">Likes</th>
                    <th className="px-4 py-2 text-right font-medium">Shares</th>
                  </tr>
                </thead>
                <tbody>
                  {ranked.map((p) => (
                    <tr key={p.id} className="border-b last:border-0 align-top">
                      <td className="max-w-md px-4 py-3">
                        <p className="line-clamp-2 text-sm">{p.content ?? "—"}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {p.published_at ? new Date(p.published_at).toLocaleString() : ""}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-xs uppercase text-muted-foreground">
                        {p.platform}
                      </td>
                      <td className="px-4 py-3">
                        {p.sentiment_label ? <SentimentBadge sentiment={p.sentiment_label} /> : "—"}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums font-medium">
                        {formatNumber(p.comments ?? 0)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                        {formatNumber(p.likes ?? 0)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                        {formatNumber(p.shares ?? 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
