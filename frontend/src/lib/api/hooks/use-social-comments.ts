import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { PaginatedResponse } from "@/lib/api/types";

export interface SocialComment {
  id: number;
  parent_post_id: number;
  content: string | null;
  nlp_tono: string | null;
  nlp_polaridad: number | null;
  nlp_target: string | null;
  likes: number | null;
  published_at: string | null;
  es_follower: boolean | null;
  is_reply_to_comment: boolean | null;
  data_source: string | null;
  dirigente_nombre: string | null;
  platform: string | null;
  // S5 · dual labels HITL — campos opcionales que el backend popula tras /hitl PATCH/POST
  review_status?: "unreviewed" | "confirmed" | "edited" | null;
  last_reviewed_by?: number | null;
  last_reviewed_by_name?: string | null;
  last_reviewed_at?: string | null;
}

export interface CommentsFilters {
  page?: number;
  page_size?: number;
  tono?: string;
  polaridad?: number;
  platform?: string;
  dirigente_id?: number;
}

export function useSocialComments(filters: CommentsFilters = {}) {
  const params = new URLSearchParams();
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  if (filters.tono) params.set("tono", filters.tono);
  if (filters.polaridad !== undefined) params.set("polaridad", String(filters.polaridad));
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.dirigente_id) params.set("dirigente_id", String(filters.dirigente_id));

  return useQuery({
    queryKey: ["social-comments", filters],
    queryFn: () => api.get<PaginatedResponse<SocialComment>>(`/social/comments?${params}`),
    staleTime: 2 * 60_000,
  });
}
