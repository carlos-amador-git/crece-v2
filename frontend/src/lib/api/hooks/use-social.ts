import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type {
  SocialPost,
  SocialFilters,
  SentimentTrend,
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

export interface SentimentTrendOptions {
  platform?: string;
  includeRts?: boolean;
}

export function useSentimentTrend(
  days: number = 30,
  dirigenteId?: number,
  options: SentimentTrendOptions = {},
) {
  const params = new URLSearchParams();
  if (dirigenteId) params.set("dirigente_id", String(dirigenteId));
  if (options.platform) params.set("platform", options.platform.toUpperCase());
  if (options.includeRts) params.set("include_rts", "true");

  return useQuery({
    queryKey: ["sentiment-trend", days, dirigenteId, options.platform ?? "", options.includeRts ?? false],
    queryFn: () =>
      api.get<SentimentTrend[]>(`/social/sentiment-timeline?${params}`),
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
