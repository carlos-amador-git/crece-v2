"use client";

import { useState, useMemo } from "react";
import { useSocialPosts } from "@/lib/api/hooks/use-social";
import { useCrisisAlerts } from "@/lib/api/hooks/use-overview";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PostCard } from "@/components/social/post-card";
import { SentimentPieChart } from "@/components/charts/sentiment-pie-chart";
import { SentimentBadge } from "@/components/social/sentiment-badge";
import { TrendingAlcaldiaCard } from "@/components/social/trending-alcaldia-card";
import type { SocialFilters, SocialPost, SentimentDistribution } from "@/lib/api/types";
import { AlertTriangle, MessageSquare, Search, Repeat2, Pen } from "lucide-react";

function isRetweet(post: SocialPost): boolean {
  const content = post.content ?? "";
  return (
    content.startsWith("RT @") ||
    content.startsWith("RT:") ||
    content.includes("[QT]") ||
    content.includes("[Retweet]")
  );
}

function computeDistribution(posts: SocialPost[]): SentimentDistribution {
  let positive = 0, negative = 0, neutral = 0;
  for (const p of posts) {
    const s = (p.sentiment_label ?? "").toLowerCase();
    if (s === "positive") positive++;
    else if (s === "negative") negative++;
    else neutral++;
  }
  return { positive, negative, neutral, total: posts.length };
}

export default function SocialPage() {
  const [filters, setFilters] = useState<SocialFilters>({
    page: 1,
    per_page: 50,
  });
  const [hideRetweets, setHideRetweets] = useState(true);

  const { data: postsData, isLoading } = useSocialPosts(filters);
  const { data: crisisAlerts } = useCrisisAlerts();

  const allPosts = postsData?.items ?? [];

  // Deduplicate by content (same content = duplicate scrape)
  const dedupedPosts = useMemo(() => {
    const seen = new Set<string>();
    return allPosts.filter((p) => {
      const key = `${p.content?.slice(0, 100)}-${p.platform}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [allPosts]);

  // Split into original vs retweets
  const originalPosts = useMemo(() => dedupedPosts.filter((p) => !isRetweet(p)), [dedupedPosts]);
  const retweetPosts = useMemo(() => dedupedPosts.filter((p) => isRetweet(p)), [dedupedPosts]);

  const displayPosts = hideRetweets ? originalPosts : dedupedPosts;

  // Compute distribution from displayed posts
  const distribution = useMemo(() => computeDistribution(displayPosts), [displayPosts]);

  const activeCrisis = crisisAlerts?.find((a) => a.active);

  const topPosts = useMemo(() =>
    [...displayPosts]
      .sort((a, b) => (b.likes + b.comments + b.shares) - (a.likes + a.comments + a.shares))
      .slice(0, 3),
    [displayPosts]
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold">Monitoreo Social</h1>
        <p className="text-sm text-muted-foreground">
          Seguimiento en tiempo real de publicaciones y sentimiento
        </p>
      </div>

      {/* Crisis alert banner */}
      {activeCrisis && (
        <div
          className="flex items-center gap-3 rounded-lg border border-red-500/20 bg-red-500/10 p-4"
          role="alert"
        >
          <AlertTriangle className="h-5 w-5 shrink-0 text-red-600 dark:text-red-400" />
          <div>
            <p className="text-sm font-semibold text-red-600 dark:text-red-400">
              Alerta de Crisis
            </p>
            <p className="text-sm text-red-600/80 dark:text-red-400/80">
              {activeCrisis.message}
            </p>
          </div>
        </div>
      )}

      {/* Stats bar */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/10">
              <MessageSquare className="h-4.5 w-4.5 text-accent" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total Posts</p>
              <p className="font-heading text-lg font-bold tabular-nums">{dedupedPosts.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
              <Pen className="h-4.5 w-4.5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Originales</p>
              <p className="font-heading text-lg font-bold tabular-nums">{originalPosts.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
              <Repeat2 className="h-4.5 w-4.5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Retweets / Replicas</p>
              <p className="font-heading text-lg font-bold tabular-nums">{retweetPosts.length}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* S4.10 — Trending ahora en alcaldía (Sprint 4 Motor de Trends) */}
      <TrendingAlcaldiaCard />

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Buscar en publicaciones..." className="pl-9" />
            </div>
            <Select
              value={filters.platform ?? "all"}
              onValueChange={(v) =>
                setFilters((prev) => ({
                  ...prev,
                  platform: v === "all" ? undefined : (v as any),
                }))
              }
            >
              <SelectTrigger className="w-full sm:w-[160px]">
                <SelectValue placeholder="Plataforma" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="twitter">Twitter</SelectItem>
                <SelectItem value="facebook">Facebook</SelectItem>
                <SelectItem value="instagram">Instagram</SelectItem>
                <SelectItem value="tiktok">TikTok</SelectItem>
                <SelectItem value="youtube">YouTube</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={filters.sentiment ?? "all"}
              onValueChange={(v) =>
                setFilters((prev) => ({
                  ...prev,
                  sentiment: v === "all" ? undefined : (v as any),
                }))
              }
            >
              <SelectTrigger className="w-full sm:w-[160px]">
                <SelectValue placeholder="Sentimiento" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="positive">Positivo</SelectItem>
                <SelectItem value="negative">Negativo</SelectItem>
                <SelectItem value="neutral">Neutral</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant={hideRetweets ? "default" : "outline"}
              size="sm"
              onClick={() => setHideRetweets(!hideRetweets)}
              className="gap-1.5 shrink-0"
            >
              <Repeat2 className="h-3.5 w-3.5" />
              {hideRetweets ? "Solo originales" : "Incluir RTs"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Post feed */}
        <div className="space-y-3 lg:col-span-2">
          <h2 className="font-heading text-lg font-semibold">
            Feed de Publicaciones
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              ({displayPosts.length} {hideRetweets ? "originales" : "total"})
            </span>
          </h2>
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))
          ) : displayPosts.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <MessageSquare className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  {hideRetweets
                    ? "No hay publicaciones originales. Prueba incluyendo RTs."
                    : "No se encontraron publicaciones"}
                </p>
              </CardContent>
            </Card>
          ) : (
            displayPosts.map((post) => <PostCard key={post.id} post={post} />)
          )}
        </div>

        {/* Sidebar: distribution + top posts */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Distribucion de Sentimiento</CardTitle>
            </CardHeader>
            <CardContent>
              <SentimentPieChart data={distribution} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top por Engagement</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {topPosts.map((post) => (
                <div
                  key={post.id}
                  className="flex items-start gap-2 rounded-md border bg-background p-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium">
                      {post.dirigente_nombre}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                      {post.content}
                    </p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <SentimentBadge sentiment={post.sentiment_label} />
                      <span className="text-[10px] text-muted-foreground">
                        {post.likes + post.comments + post.shares} interacciones
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
