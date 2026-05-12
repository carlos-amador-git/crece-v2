import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type {
  Dirigente,
  DirigenteDetail,
  DirigenteFilters,
  PaginatedResponse,
} from "../types";

export function useDirigentes(
  filters: DirigenteFilters = {},
  options: { enabled?: boolean } = {},
) {
  const params = new URLSearchParams();
  if (filters.partido) params.set("partido", filters.partido);
  if (filters.estado) params.set("estado", filters.estado);
  if (filters.ipd_min != null) params.set("ipd_min", String(filters.ipd_min));
  if (filters.ipd_max != null) params.set("ipd_max", String(filters.ipd_max));
  if (filters.search) params.set("search", filters.search);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));

  const qs = params.toString();
  const endpoint = `/dirigentes${qs ? `?${qs}` : ""}`;

  return useQuery({
    queryKey: ["dirigentes", filters],
    queryFn: () => api.get<PaginatedResponse<Dirigente>>(endpoint),
    enabled: options.enabled ?? true,
  });
}

export function useDirigente(id: number | string) {
  return useQuery({
    queryKey: ["dirigente", id],
    queryFn: () => api.get<DirigenteDetail>(`/dirigentes/${id}`),
    enabled: !!id,
  });
}

export interface CrecimientoPlatform {
  platform: string;
  handle: string;
  followers_now: number;
  delta_pct: { "7d": number | null; "30d": number | null; "90d": number | null };
  trend_30v30_pct: number | null;
  semaforo: "verde" | "ambar" | "rojo" | "desconocido";
  data_source: string;
  last_manual_update: string | null;
  stale_manual: boolean;
}

export interface CrecimientoSeriesPoint {
  taken_at: string;
  platform: string;
  followers: number;
  posts: number;
}

export interface CrecimientoResponse {
  dirigente_id: number;
  platforms: CrecimientoPlatform[];
  series: CrecimientoSeriesPoint[];
}

export function useDirigenteCrecimiento(id: number | string) {
  return useQuery({
    queryKey: ["dirigente-crecimiento", id],
    queryFn: () => api.get<CrecimientoResponse>(`/dirigentes/${id}/crecimiento`),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateDirigente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Dirigente>) =>
      api.post<Dirigente>("/dirigentes", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dirigentes"] });
    },
  });
}

export function useUpdateDirigente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Dirigente> }) =>
      api.patch<Dirigente>(`/dirigentes/${id}`, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["dirigentes"] });
      queryClient.invalidateQueries({ queryKey: ["dirigente", variables.id] });
    },
  });
}

export function useDeleteDirigente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/dirigentes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dirigentes"] });
    },
  });
}
