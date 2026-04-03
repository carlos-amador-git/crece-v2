"use client";

import { useState } from "react";
import { useSocialPosts, useSentimentDistribution } from "@/lib/api/hooks/use-social";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
import type { SocialFilters, SocialPost, SentimentDistribution } from "@/lib/api/types";
import { AlertTriangle, MessageSquare, Search, TrendingUp } from "lucide-react";

/* ---- Mock data ---- */
const MOCK_POSTS: SocialPost[] = [
  {
    id: 1, dirigente_id: 1, dirigente_nombre: "Ana Martinez",
    platform: "twitter", content: "Hoy visitamos las comunidades rurales del distrito. Escuchamos sus necesidades y comprometimos acciones concretas para mejorar la infraestructura hidrica.",
    url: "#", sentiment: "positive", sentiment_score: 0.87,
    likes: 1420, comments: 89, shares: 234, views: 45200,
    published_at: new Date(Date.now() - 2 * 3600000).toISOString(), collected_at: new Date().toISOString(),
  },
  {
    id: 2, dirigente_id: 2, dirigente_nombre: "Carlos Ruiz",
    platform: "facebook", content: "La reforma presupuestal no considera las necesidades reales de los municipios. Exigimos una revision inmediata del proyecto de ley.",
    url: "#", sentiment: "negative", sentiment_score: 0.72,
    likes: 890, comments: 156, shares: 312,
    published_at: new Date(Date.now() - 5 * 3600000).toISOString(), collected_at: new Date().toISOString(),
  },
  {
    id: 3, dirigente_id: 3, dirigente_nombre: "Maria Lopez",
    platform: "instagram", content: "Inauguracion del nuevo centro comunitario en la colonia San Miguel. Un espacio que la comunidad merecia desde hace anos.",
    url: "#", sentiment: "positive", sentiment_score: 0.91,
    likes: 3200, comments: 201, shares: 89,
    published_at: new Date(Date.now() - 8 * 3600000).toISOString(), collected_at: new Date().toISOString(),
  },
  {
    id: 4, dirigente_id: 4, dirigente_nombre: "Jose Garcia",
    platform: "tiktok", content: "Video explicando los avances del programa de becas deportivas para jovenes del municipio.",
    url: "#", sentiment: "positive", sentiment_score: 0.78,
    likes: 8900, comments: 445, shares: 1200, views: 125000,
    published_at: new Date(Date.now() - 12 * 3600000).toISOString(), collected_at: new Date().toISOString(),
  },
  {
    id: 5, dirigente_id: 5, dirigente_nombre: "Laura Sanchez",
    platform: "twitter", content: "El transporte publico sigue siendo un tema pendiente. No podemos seguir ignorando las quejas de los ciudadanos.",
    url: "#", sentiment: "negative", sentiment_score: 0.68,
    likes: 560, comments: 78, shares: 145,
    published_at: new Date(Date.now() - 16 * 3600000).toISOString(), collected_at: new Date().toISOString(),
  },
  {
    id: 6, dirigente_id: 1, dirigente_nombre: "Ana Martinez",
    platform: "facebook", content: "Sesion ordinaria en la Camara de Diputados. Presentamos iniciativa para proteger los derechos de los trabajadores del campo.",
    url: "#", sentiment: "neutral", sentiment_score: 0.52,
    likes: 780, comments: 45, shares: 67,
    published_at: new Date(Date.now() - 20 * 3600000).toISOString(), collected_at: new Date().toISOString(),
  },
];

const MOCK_DISTRIBUTION: SentimentDistribution = {
  positive: 156, negative: 67, neutral: 89, total: 312,
};

const MOCK_CRISIS_ALERT = {
  active: true,
  message: "Incremento del 340% en menciones negativas para Carlos Ruiz en las ultimas 4 horas",
};
/* ---- End mock data ---- */

export default function SocialPage() {
  const [filters, setFilters] = useState<SocialFilters>({
    page: 1,
    per_page: 20,
  });

  const { data: postsData, isLoading } = useSocialPosts(filters);
  const { data: distData } = useSentimentDistribution();

  const posts = postsData?.items ?? MOCK_POSTS;
  const distribution = distData ?? MOCK_DISTRIBUTION;

  const topPosts = [...posts].sort(
    (a, b) => (b.likes + b.comments + b.shares) - (a.likes + a.comments + a.shares)
  ).slice(0, 3);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold">Monitoreo Social</h1>
        <p className="text-sm text-muted-foreground">
          Seguimiento en tiempo real de publicaciones y sentimiento
        </p>
      </div>

      {/* Crisis alert banner */}
      {MOCK_CRISIS_ALERT.active && (
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
              {MOCK_CRISIS_ALERT.message}
            </p>
          </div>
        </div>
      )}

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
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Post feed */}
        <div className="space-y-3 lg:col-span-2">
          <h2 className="font-heading text-lg font-semibold">
            Feed de Publicaciones
          </h2>
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))
          ) : posts.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <MessageSquare className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No se encontraron publicaciones
                </p>
              </CardContent>
            </Card>
          ) : (
            posts.map((post) => <PostCard key={post.id} post={post} />)
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
                      <SentimentBadge sentiment={post.sentiment} />
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
