"use client";

/**
 * F4 Content Hub · 2026-05-19
 *
 * Hook que consume el endpoint /api/v1/posts/unified (BFF backend que
 * consolida feed/comentarios/top/fans).
 *
 * El backend devuelve shapes distintos según `view` (discriminated union
 * Pydantic). El frontend acepta el shape y delega a UnifiedPostCard que
 * adapta cualquier shape PostUnified al render canónico.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export type UnifiedView = "feed" | "comentarios" | "top" | "fans";

export interface QuoteSample {
  text: string;
  polaridad: number;
}

export interface UnifiedItemBase {
  id: number;
  published_at: string;
  platform: string;
  content: string | null;
  url: string | null;
  likes_publicos: number;
  comments_total: number;
  shares: number;
  views: number | null;
  handle: string | null;
  dirigente_nombre: string | null;
  view: UnifiedView;
  data_source: "apify" | "mixed" | "radar";
  // Campos específicos por view (todos opcionales)
  comments_classified?: number;
  comments_classified_pct?: number | null;
  avg_polaridad?: number | null;
  sample_quotes?: QuoteSample[];
  engagement_rate?: number | null;
  rank_position?: number | null;
  score?: number | null;
  reactors_capturados?: number;
  cobertura_pct?: number | null;
}

export interface UnifiedFilters {
  dirigente_id: number;
  view?: UnifiedView;
  platform?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  per_page?: number;
}

export interface UnifiedResponse {
  view: UnifiedView;
  dirigente_id: number;
  items: UnifiedItemBase[];
  page: number;
  per_page: number;
  total: number;
  pages: number;
}

export function useUnifiedPosts(filters: UnifiedFilters) {
  const params = new URLSearchParams();
  params.set("dirigente_id", String(filters.dirigente_id));
  if (filters.view) params.set("view", filters.view);
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  params.set("page", String(filters.page ?? 1));
  params.set("per_page", String(filters.per_page ?? 20));

  return useQuery({
    queryKey: [
      "posts-unified",
      filters.dirigente_id,
      filters.view ?? "feed",
      filters.platform ?? "",
      filters.date_from ?? "",
      filters.date_to ?? "",
      filters.page ?? 1,
      filters.per_page ?? 20,
    ],
    queryFn: () => api.get<UnifiedResponse>(`/posts/unified?${params}`),
    enabled: !!filters.dirigente_id,
    staleTime: 60_000,
  });
}

/** Adaptador del shape backend al PostUnified del componente.
 *  Mapea los campos específicos de cada view a su slot canónico. */
export function unifiedItemToPostUnified(item: UnifiedItemBase) {
  return {
    id: item.id,
    published_at: item.published_at,
    platform: item.platform,
    content: item.content,
    url: item.url,
    likes_publicos: item.likes_publicos,
    reactors_capturados: item.reactors_capturados ?? null,
    cobertura_pct: item.cobertura_pct ?? null,
    comments_total: item.comments_total,
    comments_classified_pct: item.comments_classified_pct ?? null,
    polaridad_avg: item.avg_polaridad ?? null,
    polaridad_label: item.avg_polaridad
      ? item.avg_polaridad > 0.1
        ? ("positivo" as const)
        : item.avg_polaridad < -0.1
          ? ("negativo" as const)
          : ("neutral" as const)
      : null,
    views: item.views,
    shares: item.shares,
    data_source: item.data_source,
    dirigente_nombre: item.dirigente_nombre,
    handle: item.handle,
  };
}
