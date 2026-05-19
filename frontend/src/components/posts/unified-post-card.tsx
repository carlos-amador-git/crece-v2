"use client";

/**
 * F1 UnifiedPostCard · 2026-05-19
 *
 * Componente canónico para representar un post en cualquier vista de la app.
 * Reemplaza progresivamente:
 *  - PostCard en /dashboard/social/Monitoreo (F2)
 *  - Render de ranking en /dashboard/content/top (F2 · usar variant ranking)
 *  - TopPostsCards en Fans y Perfiles (F3 · variant compact)
 *
 * Diseño unifica el lenguaje de "post" en toda la app con campos canónicos
 * y badge de fuente de datos. Mitiga la disonancia semántica observada por
 * el CEO (likes_publicos snapshot Apify vs reactors_capturados RADAR).
 *
 * Per Gemini cross-audit (plan Content Hub v2 F1):
 *  - Tooltips shadcn explican disonancia semántica de cada métrica
 *  - Skeleton con dimensiones idénticas → CLS <0.05
 *  - 3 empty states distintos según tipo de carencia
 *  - Adapters por hook (en lugar de modificar shapes backend)
 */

import { useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PlatformIcon } from "@/components/social/platform-icon";
import {
  ExternalLink,
  Eye,
  Heart,
  MessageCircle,
  Share2,
} from "lucide-react";
import { formatNumber, formatRelativeTime } from "@/lib/utils";

/** Modelo canónico de post · todos los campos opcionales excepto identificador. */
export interface PostUnified {
  id: number | string;
  published_at: string | null;
  platform: string;
  content: string | null;
  url: string | null;
  /** Snapshot público del scraper (típicamente Apify) · puede haber cambiado en FB. */
  likes_publicos: number | null;
  /** Reactors individuales capturados por RADAR (watched_like_events). */
  reactors_capturados: number | null;
  /** % cobertura = reactors_capturados / likes_publicos cuando ambos > 0 */
  cobertura_pct?: number | null;
  comments_total: number | null;
  comments_classified_pct?: number | null;
  /** Polaridad promedio de comments con NLP (-1 a +1). */
  polaridad_avg?: number | null;
  polaridad_label?: "positivo" | "negativo" | "neutral" | "mixto" | null;
  views?: number | null;
  shares?: number | null;
  data_source: "apify" | "radar" | "manual" | "mixed" | "unknown";
  dirigente_nombre?: string | null;
  handle?: string | null;
}

type Variant = "feed" | "ranking" | "compact";

interface UnifiedPostCardProps {
  post: PostUnified;
  variant?: Variant;
  rank?: number;
  onClick?: () => void;
}

const DATA_SOURCE_LABELS: Record<PostUnified["data_source"], string> = {
  apify: "Apify",
  radar: "RADAR",
  manual: "Manual",
  mixed: "Mixto",
  unknown: "—",
};

const DATA_SOURCE_TOOLTIPS: Record<PostUnified["data_source"], string> = {
  apify:
    "Datos snapshot público (Apify Actor). Likes/comments/views son los visibles para cualquier usuario en FB al momento del scrape.",
  radar:
    "Datos reactors individuales (RADAR Hugo). Cada reaction es una persona identificada que reaccionó al post.",
  manual: "Datos ingresados manualmente desde admin.",
  mixed: "Combinación de Apify (snapshot) + RADAR (reactors individuales).",
  unknown: "Fuente de datos no especificada.",
};

export function UnifiedPostCardSkeleton({ variant = "feed" }: { variant?: Variant }) {
  // Dimensiones idénticas al render real → diff CLS <0.05 per Gemini concern.
  const height = variant === "compact" ? 96 : variant === "ranking" ? 220 : 168;
  return <Skeleton className="w-full" style={{ height: `${height}px` }} />;
}

export function UnifiedPostCard({
  post,
  variant = "feed",
  rank,
  onClick,
}: UnifiedPostCardProps) {
  const [imgFailed, setImgFailed] = useState(false);
  const hasUrl = Boolean(post.url && post.url.trim().length > 0);

  // Empty states · 3 según tipo
  if (!post.id && !post.content) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Sin datos de post
        </CardContent>
      </Card>
    );
  }

  const showCompact = variant === "compact";
  const showRanking = variant === "ranking";

  // Display handle (P0 #3 sanitize)
  const displayHandle = post.handle
    ? post.handle.startsWith("@")
      ? post.handle
      : `@${post.handle}`
    : null;

  const cardInner = (
    <>
      <CardHeader className={showCompact ? "pb-2" : "pb-3"}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1 px-1.5 py-0 text-[10px] font-medium">
              {/* PlatformIcon espera SocialPlatform lowercase · normalizamos */}
              <PlatformIcon
                platform={post.platform.toLowerCase() as Parameters<typeof PlatformIcon>[0]["platform"]}
                className="h-3 w-3"
              />
              {post.platform.charAt(0).toUpperCase() + post.platform.slice(1).toLowerCase()}
            </Badge>
            {displayHandle && (
              <span className="text-xs text-muted-foreground">{displayHandle}</span>
            )}
            <span
              title={DATA_SOURCE_TOOLTIPS[post.data_source]}
              className="rounded border border-dashed border-muted-foreground/30 px-1.5 py-0 text-[10px] text-muted-foreground"
            >
              {DATA_SOURCE_LABELS[post.data_source]}
            </span>
          </div>
          {showRanking && rank != null && (
            <Badge variant="secondary" className="font-mono text-[10px]">
              #{rank}
            </Badge>
          )}
          {post.published_at && !showRanking && (
            <span className="text-xs text-muted-foreground">
              {formatRelativeTime(post.published_at)}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className={`flex flex-col gap-3 ${showCompact ? "pb-3 pt-0" : "pb-4 pt-0"}`}>
        {post.content && (
          <p
            className={`leading-relaxed text-foreground/90 ${
              showCompact ? "line-clamp-2 text-xs" : "line-clamp-3 text-sm"
            }`}
          >
            {post.content}
          </p>
        )}

        {/* Métricas con tooltips de disonancia semántica */}
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground tabular-nums">
          {post.likes_publicos != null && (
            <span
              className="flex items-center gap-1"
              title="Likes públicos snapshot Apify. Es lo que FB muestra a cualquier usuario al ver el post; puede haber cambiado desde el scrape."
            >
              <Heart className="h-3.5 w-3.5" />
              <span className="font-medium">{formatNumber(post.likes_publicos)}</span>
              <span className="text-[10px] text-muted-foreground/70">likes</span>
            </span>
          )}
          {post.reactors_capturados != null && post.reactors_capturados > 0 && (
            <span
              className="flex items-center gap-1 text-violet-600 dark:text-violet-400"
              title="Reactors individuales capturados por RADAR. Cada uno es una persona identificada. Si < likes públicos = cobertura RADAR parcial."
            >
              <Heart className="h-3.5 w-3.5" />
              <span className="font-medium">{formatNumber(post.reactors_capturados)}</span>
              <span className="text-[10px] opacity-70">reactors</span>
            </span>
          )}
          {post.comments_total != null && (
            <span className="flex items-center gap-1" title="Comments totales en el post.">
              <MessageCircle className="h-3.5 w-3.5" />
              <span className="font-medium">{formatNumber(post.comments_total)}</span>
              <span className="text-[10px] text-muted-foreground/70">coment.</span>
            </span>
          )}
          {post.shares != null && post.shares > 0 && !showCompact && (
            <span className="flex items-center gap-1">
              <Share2 className="h-3.5 w-3.5" />
              <span className="font-medium">{formatNumber(post.shares)}</span>
              <span className="text-[10px] text-muted-foreground/70">shares</span>
            </span>
          )}
          {post.views != null && post.views > 0 && !showCompact && (
            <span className="flex items-center gap-1">
              <Eye className="h-3.5 w-3.5" />
              <span className="font-medium">{formatNumber(post.views)}</span>
              <span className="text-[10px] text-muted-foreground/70">vistas</span>
            </span>
          )}
          {post.polaridad_avg != null && (
            <span
              className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                post.polaridad_avg > 0.1
                  ? "bg-emerald-100 text-emerald-700"
                  : post.polaridad_avg < -0.1
                    ? "bg-rose-100 text-rose-700"
                    : "bg-slate-100 text-slate-700"
              }`}
              title="Polaridad promedio de los comments clasificados con NLP (-1 a +1)."
            >
              polaridad {post.polaridad_avg.toFixed(2)}
            </span>
          )}
          {hasUrl && (
            <ExternalLink
              className="ml-auto h-3.5 w-3.5 text-muted-foreground/70"
              aria-hidden="true"
            />
          )}
        </div>
      </CardContent>
    </>
  );

  const wrapperClass = showCompact ? "h-full" : "";
  if (hasUrl && !onClick) {
    return (
      <Card className={`${wrapperClass} transition-shadow hover:shadow-md`}>
        <Link
          href={post.url!}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Abrir publicación en ${post.platform}`}
          className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {cardInner}
        </Link>
      </Card>
    );
  }
  if (onClick) {
    return (
      <Card
        className={`${wrapperClass} cursor-pointer transition-shadow hover:shadow-md`}
        onClick={onClick}
      >
        {cardInner}
      </Card>
    );
  }
  return <Card className={wrapperClass}>{cardInner}</Card>;
}
