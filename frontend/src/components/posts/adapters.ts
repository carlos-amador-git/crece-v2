/**
 * F1 adapters · 2026-05-19
 *
 * Adapta los shapes heterogéneos de los hooks existentes al modelo canónico
 * `PostUnified`. Permite migrar progresivamente las vistas (F2/F3) sin tocar
 * los hooks de fetching ni los endpoints backend.
 */
import type { PostUnified } from "./unified-post-card";
import type { SocialPost } from "@/lib/api/types";
import type { TopPostItem } from "@/lib/api/hooks/use-top-posts";

export function adaptSocialPost(p: SocialPost): PostUnified {
  return {
    id: p.id,
    published_at: p.published_at,
    platform: p.platform,
    content: p.content,
    url: p.url,
    likes_publicos: p.likes,
    reactors_capturados: null, // Monitoreo Social no traía esto · viene en Fans/RADAR
    comments_total: p.comments,
    shares: p.shares,
    views: p.views ?? null,
    polaridad_avg: p.sentiment_score ?? null,
    polaridad_label: null,
    data_source: "apify",
    dirigente_nombre: p.dirigente_nombre ?? null,
    handle: null,
  };
}

export function adaptTopPost(p: TopPostItem): PostUnified {
  return {
    id: p.post_id,
    published_at: p.published_at,
    platform: p.platform,
    content: p.snippet,
    url: p.url,
    likes_publicos: p.likes,
    reactors_capturados: null,
    comments_total: p.comments,
    shares: p.shares,
    views: p.views ?? null,
    polaridad_avg: null, // p.sentiment_label es categorical, no score
    data_source: "apify",
    dirigente_nombre: null,
    handle: p.handle,
  };
}

/** Adapter para items que vienen de TopPostsCards en Fans y Perfiles
 *  (winners/losers de polaridad_promedio sobre comments) */
export interface FansTopPostInput {
  post_id: number;
  published_at: string;
  content_snippet: string;
  likes: number;
  n_comments: number;
  n_classified_comments?: number;
  avg_polaridad: number;
  sample_quotes?: Array<{ text: string; polaridad: number }>;
  post_url?: string | null;
  platform?: string;
}

export function adaptFansTopPost(p: FansTopPostInput): PostUnified {
  return {
    id: p.post_id,
    published_at: p.published_at,
    platform: p.platform ?? "FACEBOOK",
    content: p.content_snippet,
    url: p.post_url ?? null,
    likes_publicos: p.likes,
    reactors_capturados: null, // count viene aparte, no en este shape
    comments_total: p.n_comments,
    comments_classified_pct:
      p.n_classified_comments && p.n_comments
        ? Math.round((p.n_classified_comments / p.n_comments) * 100)
        : null,
    polaridad_avg: p.avg_polaridad,
    polaridad_label:
      p.avg_polaridad > 0.1 ? "positivo" : p.avg_polaridad < -0.1 ? "negativo" : "neutral",
    data_source: "mixed", // likes públicos Apify + polaridad RADAR/NLP
    dirigente_nombre: null,
    handle: null,
  };
}
