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

// ── Sprint 3: tareas editables del plan ─────────────────────────────

export type EstadoTarea = "TODO" | "IN_PROGRESS" | "DONE";

export type PlanTarea = {
  id: number;
  plan_id: number;
  orden: number;
  titulo: string;
  descripcion: string;
  plataforma: string | null;
  formato: string | null;
  frecuencia: string | null;
  responsable: string | null;
  deadline: string | null;
  metrica_objetivo: string | null;
  metrica_valor_objetivo: number | null;
  metrica_valor_real: number | null;
  estado: EstadoTarea;
  completado_at: string | null;
  cambios_historial: Array<Record<string, unknown>> | null;
  created_at: string;
  updated_at: string;
};

export type PlanProgreso = {
  plan_id: number;
  total_tareas: number;
  tareas_todo: number;
  tareas_in_progress: number;
  tareas_done: number;
  porcentaje_ejecutado: number;
  impacto_acumulado: Record<string, number>;
};

export function usePlanTareas(planId: number | string) {
  return useQuery({
    queryKey: ["plan-tareas", planId],
    queryFn: () => api.get<PlanTarea[]>(`/planes/${planId}/tareas`),
    enabled: !!planId,
  });
}

export function usePlanProgreso(planId: number | string) {
  return useQuery({
    queryKey: ["plan-progreso", planId],
    queryFn: () => api.get<PlanProgreso>(`/planes/${planId}/progreso`),
    enabled: !!planId,
  });
}

export function useUpdateTarea(planId: number | string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, patch }: { taskId: number; patch: Partial<PlanTarea> }) =>
      api.patch<PlanTarea>(`/planes/${planId}/tareas/${taskId}`, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plan-tareas", planId] });
      queryClient.invalidateQueries({ queryKey: ["plan-progreso", planId] });
    },
  });
}

export function useCompleteTarea(planId: number | string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      metrica_valor_real,
      nota,
    }: {
      taskId: number;
      metrica_valor_real: number;
      nota?: string;
    }) =>
      api.post<PlanTarea>(`/planes/${planId}/tareas/${taskId}/complete`, {
        metrica_valor_real,
        nota,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plan-tareas", planId] });
      queryClient.invalidateQueries({ queryKey: ["plan-progreso", planId] });
    },
  });
}
