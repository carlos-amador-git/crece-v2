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
    queryFn: () => api.get<ScoringKpi>("/voter-scoring/segments"),
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
