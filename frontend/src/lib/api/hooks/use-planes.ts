import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { PlanIA, PlanType, PlanStatus, PaginatedResponse } from "../types";

export function usePlanes(status?: PlanStatus, page = 1) {
  const params = new URLSearchParams({ page: String(page) });
  if (status) params.set("status", status);

  return useQuery({
    queryKey: ["planes", status, page],
    queryFn: () => api.get<PaginatedResponse<PlanIA>>(`/planes?${params}`),
  });
}

export function usePlan(id: number | string) {
  return useQuery({
    queryKey: ["plan", id],
    queryFn: () => api.get<PlanIA>(`/planes/${id}`),
    enabled: !!id,
  });
}

export function useGeneratePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { dirigente_id: number; tipo: PlanType }) =>
      api.post<PlanIA>("/planes/generate", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["planes"] });
    },
  });
}

export function useApprovePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.patch<PlanIA>(`/planes/${id}/approve`, {}),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["planes"] });
      queryClient.invalidateQueries({ queryKey: ["plan", id] });
    },
  });
}

export function useRejectPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.patch<PlanIA>(`/planes/${id}/reject`, {}),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["planes"] });
      queryClient.invalidateQueries({ queryKey: ["plan", id] });
    },
  });
}
