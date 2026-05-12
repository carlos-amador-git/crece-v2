"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { Alert, SocialPost, PaginatedResponse } from "@/lib/api/types";

/* ────────────────────────────────────────────────────────────
 * Sentiment thresholds for crisis classification
 * ──────────────────────────────────────────────────────────── */
export const CRISIS_THRESHOLD = -0.5;
export const WARNING_THRESHOLD = -0.2;
export const NEGATIVE_THRESHOLD = -0.3;

export type CrisisSeverity = "crisis" | "warning" | "ok";

export function classifySeverity(score: number): CrisisSeverity {
  if (score <= CRISIS_THRESHOLD) return "crisis";
  if (score <= WARNING_THRESHOLD) return "warning";
  return "ok";
}

/* ────────────────────────────────────────────────────────────
 * Derived alert from a negative social post
 * ──────────────────────────────────────────────────────────── */
export interface CrisisPostAlert {
  id: number;
  dirigente_name: string;
  sentiment_score: number;
  platform: string;
  post_content_preview: string;
  published_at: string;
  severity: CrisisSeverity;
  post_url: string;
}

/* ────────────────────────────────────────────────────────────
 * Hook: fetch negative-sentiment posts and transform them
 * into crisis alerts. Polls every 60s.
 * ──────────────────────────────────────────────────────────── */
export function useCrisisPostAlerts(dirigenteId?: number) {
  return useQuery({
    queryKey: ["crisis-post-alerts", dirigenteId],
    queryFn: async (): Promise<CrisisPostAlert[]> => {
      const params = new URLSearchParams({
        sentiment: "negative",
        per_page: "20",
      });
      if (dirigenteId) params.set("dirigente_id", String(dirigenteId));

      const data = await api.get<PaginatedResponse<SocialPost>>(
        `/social/posts?${params}`
      );

      return data.items
        .filter((post) => (post.sentiment_score ?? 0) < NEGATIVE_THRESHOLD)
        .map((post) => {
          const score = post.sentiment_score ?? 0;
          return {
            id: post.id,
            dirigente_name: post.dirigente_nombre ?? "Desconocido",
            sentiment_score: score,
            platform: post.platform,
            post_content_preview:
              post.content.length > 140
                ? `${post.content.slice(0, 140)}...`
                : post.content,
            published_at: post.published_at,
            severity: classifySeverity(score),
            post_url: post.url,
          };
        })
        .sort((a, b) => a.sentiment_score - b.sentiment_score);
    },
    refetchInterval: 60_000,
  });
}

/* ────────────────────────────────────────────────────────────
 * Hook: fetch backend Alert entities (crisis type)
 * ──────────────────────────────────────────────────────────── */
export function useBackendAlerts() {
  return useQuery({
    queryKey: ["backend-crisis-alerts"],
    queryFn: () => api.get<BackendAlert[]>("/alerts"),
    refetchInterval: 30_000,
  });
}

export interface BackendAlert {
  id: number;
  org_id: number;
  perfil_id: number | null;
  tipo: string;
  severidad: "critica" | "alta" | "media";
  descripcion: string;
  post_ids: number[] | null;
  estado: string;
  created_at: string;
}

/* ────────────────────────────────────────────────────────────
 * Mutation: dismiss (mark as read) a backend alert
 * ──────────────────────────────────────────────────────────── */
export function useDismissAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: number) =>
      api.patch(`/alerts/${alertId}/status`, { estado: "descartada" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backend-crisis-alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["kpi-overview"] });
    },
  });
}
