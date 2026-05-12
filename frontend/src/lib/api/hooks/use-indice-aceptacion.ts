import { useQuery } from "@tanstack/react-query";
import { api } from "../client";

export type IAScores = {
  post_id: number;
  platform_post_id: string;
  total_comments: number;
  aprobacion_pct: number;
  rechazo_pct: number;
  neutral_pct: number;
  expansion_pct: number;
  total_likes_on_comments: number;
  unique_authors: number;
  tono_breakdown: Record<string, number>;
  confidence: "none" | "low" | "medium" | "high";
};

export type IADirigenteSummary = {
  dirigente_id: number;
  posts_con_ia: number;
  aprobacion_promedio: number;
  rechazo_promedio: number;
  expansion_promedio: number;
  top_aprobacion: {
    post_id: number;
    platform_post_id: string;
    snippet: string;
    n_comments: number;
    aprobacion_pct: number;
  }[];
  top_rechazo: {
    post_id: number;
    platform_post_id: string;
    snippet: string;
    n_comments: number;
    rechazo_pct: number;
  }[];
};

export function useIAPost(postId: number | null) {
  return useQuery({
    queryKey: ["ia-post", postId],
    queryFn: () => api.get<IAScores>(`/social/posts/${postId}/ia`),
    enabled: !!postId,
    staleTime: 60_000,
  });
}

export function useIADirigenteSummary(dirigenteId: number | null) {
  return useQuery({
    queryKey: ["ia-dirigente", dirigenteId],
    queryFn: () => api.get<IADirigenteSummary>(`/social/dirigentes/${dirigenteId}/ia-summary`),
    enabled: !!dirigenteId,
    staleTime: 300_000,
  });
}
