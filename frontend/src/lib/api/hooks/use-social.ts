import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type {
  SocialPost,
  SocialFilters,
  SentimentDistribution,
  PaginatedResponse,
} from "../types";

export function useSocialPosts(filters: SocialFilters = {}) {
  const params = new URLSearchParams();
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.sentiment) params.set("sentiment", filters.sentiment);
  if (filters.dirigente_id) params.set("dirigente_id", String(filters.dirigente_id));
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));

  const qs = params.toString();
  const endpoint = `/social/posts${qs ? `?${qs}` : ""}`;

  return useQuery({
    queryKey: ["social-posts", filters],
    queryFn: () => api.get<PaginatedResponse<SocialPost>>(endpoint),
  });
}

// D14 (2026-05-19) · sentiment legacy hooks removidos · migrado 100% a
// useTonoDiscursoTrend + useTonoDiscursoCoverage. Endpoint backend
// /social/sentiment-timeline diferido hasta confirmar 0 consumers externos.

// ──────────────────────────────────────────────────────────────
// Tono Discursivo · matriz polaridad v2 (2026-05-19)
// Endpoint paralelo al sentiment legacy. Migración de Overview +
// Dirigentes/[id] a este hook · sentiment-timeline queda para
// cleanup en sprint posterior cuando todos consuman este.
// ──────────────────────────────────────────────────────────────

export interface TonoDiscursoTimelinePoint {
  date: string;
  post_count: number;
  tonos: Record<string, number>;
}

export interface TonoDiscursoTrendOptions {
  platform?: string;
  includeRts?: boolean;
}

export function useTonoDiscursoTrend(
  days: number = 30,
  dirigenteId?: number,
  options: TonoDiscursoTrendOptions = {},
) {
  const params = new URLSearchParams();
  if (dirigenteId) params.set("dirigente_id", String(dirigenteId));
  if (options.platform) params.set("platform", options.platform.toUpperCase());
  if (options.includeRts) params.set("include_rts", "true");

  return useQuery({
    queryKey: ["tono-discurso-trend", days, dirigenteId, options.platform ?? "", options.includeRts ?? false],
    queryFn: () =>
      api.get<TonoDiscursoTimelinePoint[]>(`/social/tono-discurso-timeline?${params}`),
    enabled: dirigenteId != null,
  });
}

export interface TonoDiscursoCoverage {
  dirigente_id: number;
  days: number;
  total_posts: number;
  classified: number;
  passed_filters: number;
  coverage_pct: number;
  tonos_distribution: Record<string, number>;
}

export function useTonoDiscursoCoverage(
  dirigenteId: number | undefined,
  days: number = 30,
  includeRts: boolean = false,
) {
  const params = new URLSearchParams();
  if (dirigenteId) params.set("dirigente_id", String(dirigenteId));
  params.set("days", String(days));
  if (includeRts) params.set("include_rts", "true");

  return useQuery({
    queryKey: ["tono-discurso-coverage", dirigenteId, days, includeRts],
    queryFn: () => api.get<TonoDiscursoCoverage>(`/social/tono-discurso-coverage?${params}`),
    enabled: dirigenteId != null,
  });
}

export function useSentimentDistribution(dirigenteId?: number) {
  // Distribution endpoint not yet implemented — return empty data
  return useQuery({
    queryKey: ["sentiment-distribution", dirigenteId],
    queryFn: () =>
      Promise.resolve({ positive: 0, negative: 0, neutral: 0, total: 0 } as SentimentDistribution),
    enabled: !!dirigenteId,
  });
}

export function useTopPosts(limit: number = 10) {
  return useQuery({
    queryKey: ["top-posts", limit],
    queryFn: () =>
      api.get<SocialPost[]>(`/social/posts/top?limit=${limit}`),
  });
}
