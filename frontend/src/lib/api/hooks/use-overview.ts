import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { KpiOverview, Alert, Dirigente } from "../types";

export function useKpiOverview() {
  return useQuery({
    queryKey: ["kpi-overview"],
    queryFn: () => api.get<KpiOverview>("/dashboard/overview"),
    refetchInterval: 60_000,
  });
}

export function useAlerts(unreadOnly = false) {
  const params = unreadOnly ? "?unread=true" : "";
  return useQuery({
    queryKey: ["alerts", unreadOnly],
    queryFn: () => api.get<Alert[]>(`/alerts${params}`),
    refetchInterval: 30_000,
  });
}

export function useTopDirigentes(limit = 10) {
  return useQuery({
    queryKey: ["top-dirigentes", limit],
    queryFn: () =>
      api.get<Dirigente[]>(`/dirigentes/top?limit=${limit}&sort=ipd_score`),
  });
}
