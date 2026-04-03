import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { SeccionElectoral, ElectoralMapData } from "../types";

export function useElectoralMap(estado?: string) {
  const params = estado ? `?estado=${estado}` : "";
  return useQuery({
    queryKey: ["electoral-map", estado],
    queryFn: () => api.get<ElectoralMapData>(`/electoral/mapa${params}`),
  });
}

export function useSeccionDetail(seccionId: string | null) {
  return useQuery({
    queryKey: ["seccion", seccionId],
    queryFn: () => api.get<SeccionElectoral>(`/electoral/secciones/${seccionId}`),
    enabled: !!seccionId,
  });
}

export function useElectoralStats() {
  return useQuery({
    queryKey: ["electoral-stats"],
    queryFn: () =>
      api.get<{
        total_secciones: number;
        avg_a_favor: number;
        avg_en_contra: number;
        avg_indeciso: number;
      }>("/electoral/stats"),
  });
}
