"use client";

import { useMemo, useState } from "react";
import {
  useTopPosts,
  type TopPostsMetric,
  type TopPostsPlatform,
} from "@/lib/api/hooks/use-top-posts";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  Heart,
  MessageCircle,
  Share2,
  Eye,
  TrendingUp,
  ExternalLink,
  Twitter,
  Instagram,
  Facebook,
  Youtube,
  Music2,
} from "lucide-react";

const PLATFORMS: { value: TopPostsPlatform; label: string; icon: React.ElementType }[] = [
  { value: "TWITTER", label: "Twitter / X", icon: Twitter },
  { value: "INSTAGRAM", label: "Instagram", icon: Instagram },
  { value: "FACEBOOK", label: "Facebook", icon: Facebook },
  { value: "TIKTOK", label: "TikTok", icon: Music2 },
  { value: "YOUTUBE", label: "YouTube", icon: Youtube },
];

const METRICS: { value: TopPostsMetric; label: string }[] = [
  { value: "engagement_rate", label: "Engagement %" },
  { value: "likes", label: "Likes" },
  { value: "comments", label: "Comentarios" },
  { value: "shares", label: "Shares" },
  { value: "views", label: "Views" },
];

const WINDOWS = [
  { value: 7, label: "7 días" },
  { value: 30, label: "30 días" },
  { value: 90, label: "90 días" },
  { value: 365, label: "1 año" },
];

const WEEKDAY_NAMES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

function PlatformIcon({ platform, className }: { platform: TopPostsPlatform; className?: string }) {
  const entry = PLATFORMS.find((p) => p.value === platform);
  const Icon = entry?.icon;
  return Icon ? <Icon className={className} /> : null;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatScore(metric: TopPostsMetric, score: number): string {
  if (metric === "engagement_rate") return `${score.toFixed(2)}%`;
  return formatNumber(Math.round(score));
}

export default function TopPostsPage() {
  const { user } = useAuth();
  const { data: dirigentesData } = useDirigentes({ per_page: 50 });
  const dirigentes = dirigentesData?.items ?? [];

  const defaultDirigenteId = useMemo<number | undefined>(() => {
    if (user?.dirigente_id) return user.dirigente_id;
    return dirigentes[0]?.id;
  }, [user?.dirigente_id, dirigentes]);

  const [dirigenteId, setDirigenteId] = useState<number | undefined>();
  const effectiveDirigenteId = dirigenteId ?? defaultDirigenteId;

  const [platform, setPlatform] = useState<TopPostsPlatform | "ALL">("ALL");
  const [metric, setMetric] = useState<TopPostsMetric>("engagement_rate");
  const [windowDays, setWindowDays] = useState<number>(90);

  const { data, isLoading, error } = useTopPosts({
    dirigenteId: effectiveDirigenteId,
    platform: platform === "ALL" ? undefined : platform,
    metric,
    windowDays,
    limit: 20,
  });

  const items = data?.items ?? [];
  const dirigenteName = dirigentes.find((d) => d.id === effectiveDirigenteId)?.full_name;

  return (
    <div className="space-y-5 p-6">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight">Top Posts</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Publicaciones con mejor desempeño — insumo para conversación de plan semanal con asistente IA.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 py-4">
          {dirigentes.length > 1 && !user?.dirigente_id && (
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">Dirigente</label>
              <Select
                value={effectiveDirigenteId ? String(effectiveDirigenteId) : ""}
                onValueChange={(v) => setDirigenteId(Number(v))}
              >
                <SelectTrigger className="h-9 w-[220px] text-xs">
                  <SelectValue placeholder="Selecciona dirigente" />
                </SelectTrigger>
                <SelectContent>
                  {dirigentes.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-muted-foreground">Plataforma</label>
            <Select value={platform} onValueChange={(v) => setPlatform(v as TopPostsPlatform | "ALL")}>
              <SelectTrigger className="h-9 w-[170px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todas</SelectItem>
                {PLATFORMS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-muted-foreground">Ordenar por</label>
            <Select value={metric} onValueChange={(v) => setMetric(v as TopPostsMetric)}>
              <SelectTrigger className="h-9 w-[150px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-muted-foreground">Ventana</label>
            <Select value={String(windowDays)} onValueChange={(v) => setWindowDays(Number(v))}>
              <SelectTrigger className="h-9 w-[110px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {WINDOWS.map((w) => (
                  <SelectItem key={w.value} value={String(w.value)}>
                    {w.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {data && (
            <div className="ml-auto text-xs text-muted-foreground">
              Mostrando {data.items.length} de {data.total_candidates} posts elegibles
              {dirigenteName && ` · ${dirigenteName}`}
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <Card>
          <CardContent className="py-6 text-sm text-rose-600">
            No se pudo cargar los top posts. Intenta de nuevo.
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-56" />
          ))}
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Sin posts elegibles en la ventana seleccionada. Prueba ampliar la ventana o cambiar plataforma.
          </CardContent>
        </Card>
      )}

      {!isLoading && items.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item, idx) => {
            const date = new Date(item.published_at);
            const dateLabel = date.toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "2-digit" });
            return (
              <Card key={item.post_id} className="flex h-full flex-col">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <PlatformIcon platform={item.platform} className="h-4 w-4 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">
                        {item.handle
                          ? (item.handle.startsWith("@") ? item.handle : `@${item.handle}`)
                          : "—"}
                      </span>
                    </div>
                    <Badge variant="secondary" className="font-mono text-[10px]">
                      #{idx + 1}
                    </Badge>
                  </div>
                  <CardTitle className="text-base font-semibold leading-snug">
                    {formatScore(metric, item.score)}
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      {METRICS.find((m) => m.value === metric)?.label}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col gap-3 pb-4 pt-0">
                  <p className="text-sm leading-relaxed text-foreground/90 line-clamp-4">
                    {item.snippet || <span className="italic text-muted-foreground">(sin texto)</span>}
                  </p>

                  <div className="grid grid-cols-4 gap-2 text-center">
                    <Stat icon={Heart} value={item.likes} label="likes" />
                    <Stat icon={MessageCircle} value={item.comments} label="coments" />
                    <Stat icon={Share2} value={item.shares} label="shares" />
                    <Stat icon={Eye} value={item.views ?? 0} label="views" />
                  </div>

                  {item.engagement_rate !== null && (
                    <div className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                      <TrendingUp className="h-3.5 w-3.5" />
                      {item.engagement_rate.toFixed(2)}% engagement
                    </div>
                  )}

                  <div className="mt-auto flex items-center justify-between border-t pt-2 text-xs text-muted-foreground">
                    <span>
                      {WEEKDAY_NAMES[item.weekday]} {dateLabel} · {String(item.hour).padStart(2, "0")}h
                    </span>
                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-foreground hover:underline"
                      >
                        Ver <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>

                  {item.topics && item.topics.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {item.topics.map((t) => (
                        <Badge key={t} variant="outline" className="text-[10px]">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Stat({
  icon: Icon,
  value,
  label,
}: {
  icon: React.ElementType;
  value: number;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <div className="flex items-center gap-1 text-xs text-foreground">
        <Icon className="h-3 w-3" />
        <span className="font-medium tabular-nums">{formatNumber(value)}</span>
      </div>
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}
