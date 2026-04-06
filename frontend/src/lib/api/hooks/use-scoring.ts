import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

export interface ScoringSegment {
  segment: "promotable" | "persuadible" | "indeciso" | "opositor";
  count: number;
  percentage: number;
}

export interface ScoringKpi {
  total_scored: number;
  avg_score: number;
  segments: ScoringSegment[];
}

export interface SeccionScore {
  seccion_id: string;
  avg_score: number;
  total: number;
  promotable: number;
  persuadible: number;
  indeciso: number;
  opositor: number;
}

export function useSegments() {
  return useQuery({
    queryKey: ["scoring-segments"],
    queryFn: async () => {
      const res = await api.get<ScoringSegment[] | ScoringKpi>("/voter-scoring/segments");
      // Backend returns array of {segmento, count, percentage}
      if (Array.isArray(res)) {
        const segments = res.map((s: any) => ({
          segment: s.segmento ?? s.segment,
          count: s.count,
          percentage: s.percentage,
        }));
        const total = segments.reduce((acc: number, s: ScoringSegment) => acc + s.count, 0);
        const avg = total > 0 ? segments.reduce((acc: number, s: ScoringSegment) => acc + s.count * (s.segment === "promotable" ? 80 : s.segment === "persuadible" ? 50 : s.segment === "indeciso" ? 30 : 10), 0) / total : 0;
        return { total_scored: total, avg_score: Math.round(avg * 10) / 10, segments };
      }
      return res;
    },
  });
}

export function useSeccionScores(seccionId?: string) {
  return useQuery({
    queryKey: ["scoring-seccion", seccionId],
    queryFn: () =>
      api.get<SeccionScore[]>(
        seccionId
          ? `/voter-scoring/by-seccion/${seccionId}`
          : "/voter-scoring/by-seccion"
      ),
    enabled: seccionId !== undefined || true,
  });
}

export function useRunScoring() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ status: string }>("/voter-scoring/run"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scoring-segments"] });
      queryClient.invalidateQueries({ queryKey: ["scoring-seccion"] });
    },
  });
}
