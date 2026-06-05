/**
 * Watched profiles — perfiles bajo observación nominada del cliente.
 * Endpoints: /api/v1/aceptacion/watched-profiles/...
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export type WatchedSource = "cliente_seed" | "manual" | "auto_suggested" | "competidor";

export type WatchedPlatform =
  | "TWITTER" | "INSTAGRAM" | "FACEBOOK" | "TIKTOK" | "YOUTUBE"
  | "BLUESKY" | "THREADS" | "TELEGRAM";

export interface WatchedProfile {
  id: number;
  dirigente_observador_id: number;
  platform: WatchedPlatform;
  profile_external_id: string;
  profile_handle: string | null;
  profile_url: string | null;
  display_name: string | null;
  avatar_url: string | null;
  source: WatchedSource;
  tags: string[];
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  n_comments: number;
  n_likes: number;
  last_engagement: string | null;
}

export interface WatchedSummary {
  dirigente_id: number;
  total_watched: number;
  by_source: Record<string, number>;
  by_platform: Record<string, number>;
  activos_engagement: number;
  inactivos: number;
  comments_total: number;
  likes_total: number;
  auto_suggested_pending: number;
}

export interface EngagementEntry {
  type: "comment" | "like";
  post_id: number;
  platform_post_id: string;
  post_url: string | null;
  post_published_at: string | null;
  content: string | null;
  reaction_type: string | null;
  detected_at: string;
  source: string;
}

export interface SuggestionRow {
  author_hash: string;
  n_comments: number;
  last_comment: string | null;
  platform: string;
  commenter_handle: string | null;
}

// Sprint A · Dashboard stats (PLAN-2026-05-17)
export interface TimelinePoint {
  date: string; // YYYY-MM-DD
  n_posts: number;
  n_reactions: number;
  n_comments: number;
  window_quality: "complete" | "partial";
}

export interface TopPostSampleQuote {
  text: string;
  polaridad: number;
}

export interface TopPostItem {
  post_id: number;
  published_at: string;
  content_snippet: string;
  likes: number;
  n_comments: number;
  n_classified_comments: number;
  avg_polaridad: number | null;
  sample_quotes: TopPostSampleQuote[];
  post_url: string | null;
  platform: string | null;
}

export interface InteractionsSummary {
  dirigente_id: number;
  /** null cuando all_time=true · UI muestra "histórico" en vez de "Nd". */
  window_days: number | null;
  total_reactions: number;
  total_comments: number;
  comments_classified: number;
  comments_classified_pct: number;
  posts_in_window: number;
  by_reaction_type: Record<string, number>;
  reaction_type_quality: "placeholder_like_only" | "fully_classified";
}

interface ListParams {
  dirigente_id?: number;
  platform?: string;
  source?: WatchedSource;
  tag?: string;
  active_only?: boolean;
  has_engagement?: boolean;
  limit?: number;
}

function qs(params: Record<string, unknown>) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.append(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function useWatchedProfiles(params: ListParams = {}) {
  return useQuery({
    queryKey: ["watched-profiles", "list", params],
    queryFn: () =>
      api.get<WatchedProfile[]>(`/aceptacion/watched-profiles/${qs(params as Record<string, unknown>)}`),
    staleTime: 30_000,
  });
}

export interface TopFanEntry {
  id: number;
  platform: string;
  profile_external_id: string;
  profile_handle: string | null;
  display_name: string | null;
  source: string;
  n_likes: number;
  n_comments: number;
  score: number;
}

interface TopFansParams {
  dirigente_id: number;
  limit?: number;
  source?: WatchedSource;
  platform?: string;
}

export function useTopFans(params: TopFansParams) {
  return useQuery({
    queryKey: ["watched-profiles", "top-fans", params],
    queryFn: () =>
      api.get<TopFanEntry[]>(`/aceptacion/watched-profiles/top-fans${qs(params as unknown as Record<string, unknown>)}`),
    staleTime: 30_000,
    enabled: !!params.dirigente_id,
  });
}

export function useWatchedSummary(dirigente_id: number) {
  return useQuery({
    queryKey: ["watched-profiles", "summary", dirigente_id],
    queryFn: () =>
      api.get<WatchedSummary>(
        `/aceptacion/watched-profiles/summary?dirigente_id=${dirigente_id}`
      ),
    staleTime: 30_000,
    enabled: !!dirigente_id,
  });
}

export function useWatchedEngagement(watched_id: number | null) {
  return useQuery({
    queryKey: ["watched-profiles", "engagement", watched_id],
    queryFn: () =>
      api.get<EngagementEntry[]>(
        `/aceptacion/watched-profiles/${watched_id}/engagement`
      ),
    staleTime: 30_000,
    enabled: !!watched_id,
  });
}

export function useWatchedSuggestions(dirigente_id: number, min_comments = 2, limit = 20) {
  return useQuery({
    queryKey: ["watched-profiles", "suggestions", dirigente_id, min_comments, limit],
    queryFn: () =>
      api.get<SuggestionRow[]>(
        `/aceptacion/watched-profiles/suggestions?dirigente_id=${dirigente_id}&min_comments=${min_comments}&limit=${limit}`
      ),
    staleTime: 60_000,
    enabled: !!dirigente_id,
  });
}

export interface WatchedUpdatePayload {
  profile_handle?: string;
  display_name?: string;
  tags?: string[];
  notes?: string;
  is_active?: boolean;
}

export function useUpdateWatched() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: WatchedUpdatePayload }) =>
      api.patch<WatchedProfile>(`/aceptacion/watched-profiles/${id}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watched-profiles"] });
    },
  });
}

export function useDeleteWatched() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, hard = false }: { id: number; hard?: boolean }) =>
      api.delete(`/aceptacion/watched-profiles/${id}?hard=${hard}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watched-profiles"] }),
  });
}

// Sprint A hooks · dashboard fans

// D-PLATFORM-SELECTOR-2026-05-21 · platform filter opcional (default cross).

export function useWatchedTimeline(dirigente_id: number, days = 44, platform?: string) {
  return useQuery({
    queryKey: ["watched-profiles", "timeline", dirigente_id, days, platform ?? "all"],
    queryFn: () => {
      const qs = platform
        ? `dirigente_id=${dirigente_id}&days=${days}&platform=${platform}`
        : `dirigente_id=${dirigente_id}&days=${days}`;
      return api.get<TimelinePoint[]>(`/aceptacion/watched-profiles/timeline?${qs}`);
    },
    staleTime: 60_000,
    enabled: !!dirigente_id,
  });
}

export function useWatchedTopPosts(
  dirigente_id: number,
  kind: "winners" | "losers" = "winners",
  limit = 3,
  days = 30,
  platform?: string,
) {
  return useQuery({
    queryKey: ["watched-profiles", "top-posts", dirigente_id, kind, limit, days, platform ?? "all"],
    queryFn: () => {
      const qs = platform
        ? `dirigente_id=${dirigente_id}&kind=${kind}&limit=${limit}&days=${days}&platform=${platform}`
        : `dirigente_id=${dirigente_id}&kind=${kind}&limit=${limit}&days=${days}`;
      return api.get<TopPostItem[]>(`/aceptacion/watched-profiles/top-posts?${qs}`);
    },
    staleTime: 60_000,
    enabled: !!dirigente_id,
  });
}

export function useWatchedInteractionsSummary(
  dirigente_id: number,
  days = 44,
  allTime = false,
  platform?: string,
) {
  return useQuery({
    queryKey: [
      "watched-profiles",
      "interactions-summary",
      dirigente_id,
      days,
      allTime,
      platform ?? "all",
    ],
    queryFn: () => {
      const parts = allTime
        ? [`dirigente_id=${dirigente_id}`, `all_time=true`]
        : [`dirigente_id=${dirigente_id}`, `days=${days}`];
      if (platform) parts.push(`platform=${platform}`);
      return api.get<InteractionsSummary>(
        `/aceptacion/watched-profiles/interactions-summary?${parts.join("&")}`
      );
    },
    staleTime: 60_000,
    enabled: !!dirigente_id,
  });
}
