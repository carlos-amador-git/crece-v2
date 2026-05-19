import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export type TopPostsMetric = "engagement_rate" | "likes" | "shares" | "comments" | "views";
export type TopPostsPlatform = "TWITTER" | "INSTAGRAM" | "FACEBOOK" | "TIKTOK" | "YOUTUBE";

export interface TopPostItem {
  post_id: number;
  platform: TopPostsPlatform;
  handle: string | null;
  platform_post_id: string;
  url: string | null;
  snippet: string;
  published_at: string;
  hour: number;
  weekday: number;
  likes: number;
  shares: number;
  comments: number;
  views: number | null;
  engagement_rate: number | null;
  sentiment_label: string | null;
  target_politico: string | null;
  topics: string[] | null;
  media_urls: string[] | null;
  score: number;
}

export interface TopPostsResponse {
  dirigente_id: number;
  window_days: number;
  metric: TopPostsMetric;
  total_candidates: number;
  items: TopPostItem[];
}

export interface UseTopPostsParams {
  dirigenteId: number | undefined;
  platform?: TopPostsPlatform;
  metric?: TopPostsMetric;
  windowDays?: number;
  limit?: number;
}

export function useTopPosts({
  dirigenteId,
  platform,
  metric = "engagement_rate",
  windowDays = 90,
  limit = 20,
}: UseTopPostsParams) {
  return useQuery({
    queryKey: ["top-posts", dirigenteId, platform, metric, windowDays, limit],
    enabled: dirigenteId !== undefined,
    queryFn: () => {
      const qs = new URLSearchParams({
        dirigente_id: String(dirigenteId),
        metric,
        window_days: String(windowDays),
        limit: String(limit),
      });
      if (platform) qs.set("platform", platform);
      return api.get<TopPostsResponse>(`/content/top-posts?${qs.toString()}`);
    },
    staleTime: 60_000,
  });
}
