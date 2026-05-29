import { useQuery } from "@tanstack/react-query";

import { api } from "../client";

export interface OAuthPlatformStatus {
  connected: boolean;
  is_stub: boolean | null;
  expires_at: string | null;
  scopes?: string[];
  platform_username?: string | null;
  note?: string;
}

export interface OAuthStatusResponse {
  dirigente_id: number;
  platforms: Record<string, OAuthPlatformStatus>;
  oauth_count: number;
  stub_count: number;
}

export function useOAuthStatus(dirigenteId: number | null | undefined) {
  return useQuery({
    queryKey: ["oauth-status", dirigenteId],
    queryFn: () =>
      api.get<OAuthStatusResponse>(`/oauth/status/${dirigenteId}`),
    enabled: dirigenteId != null,
    staleTime: 30_000,
  });
}

export type FollowerPlatform =
  | "twitter"
  | "instagram"
  | "facebook"
  | "tiktok"
  | "youtube"
  | "bluesky"
  | "threads"
  | "telegram";

export interface FollowerItem {
  id: number;
  platform: FollowerPlatform;
  follower_external_id: string;
  follower_handle: string | null;
  follower_display_name: string | null;
  follower_avatar_url: string | null;
  follower_is_verified: boolean;
  is_real: boolean;
  bot_score: number | null;
  first_seen_at: string;
  last_seen_at: string;
  last_active_at: string | null;
  source: "oauth" | "scraper_auth" | "public_scraper";
  engagement_summary: {
    total_engagements: number;
    by_type: Record<string, number>;
  };
}

export interface FollowersResponse {
  dirigente_id: number;
  total: number;
  page: number;
  page_size: number;
  items: FollowerItem[];
}

export interface UseFollowersFilters {
  platform?: FollowerPlatform;
  onlyWithComments?: boolean;
  onlyVerified?: boolean;
  page?: number;
  pageSize?: number;
}

export function useFollowers(
  dirigenteId: number | null | undefined,
  filters: UseFollowersFilters = {},
) {
  const params = new URLSearchParams();
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.onlyWithComments) params.set("only_with_comments", "true");
  if (filters.onlyVerified) params.set("only_verified", "true");
  if (filters.page) params.set("page", String(filters.page));
  if (filters.pageSize) params.set("page_size", String(filters.pageSize));

  const qs = params.toString();
  const endpoint = `/dirigentes/${dirigenteId}/followers${qs ? `?${qs}` : ""}`;

  return useQuery({
    queryKey: ["followers", dirigenteId, filters],
    queryFn: () => api.get<FollowersResponse>(endpoint),
    enabled: dirigenteId != null,
    staleTime: 60_000,
  });
}
