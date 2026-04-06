import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type {
  KpiOverview,
  Alert,
  Dirigente,
  CrisisAlert,
  SystemStatus,
  HealthCheck,
} from "../types";

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
    queryFn: async () => {
      const res = await api.get<{ items: Dirigente[] }>(`/dirigentes/?per_page=${limit}`);
      const items = res.items ?? [];
      return items.sort((a, b) => (b.ipd_score ?? 0) - (a.ipd_score ?? 0));
    },
  });
}

export function useCrisisAlerts() {
  return useQuery({
    queryKey: ["crisis-alerts"],
    queryFn: () => api.get<CrisisAlert[]>("/alerts?severity=high&type=crisis"),
    refetchInterval: 30_000,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: ["system-status"],
    queryFn: () => api.get<SystemStatus>("/dashboard/status"),
    refetchInterval: 60_000,
  });
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<HealthCheck>("/health/"),
    refetchInterval: 120_000,
  });
}
