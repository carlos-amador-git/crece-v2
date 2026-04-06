import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

export type CampanaEstado = "borrador" | "programada" | "activa" | "pausada" | "finalizada";
export type CampanaTipo = "whatsapp" | "sms" | "email" | "mixta";

export interface CampanaFunnel {
  enviados: number;
  entregados: number;
  leidos: number;
  respondidos: number;
}

export interface Campana {
  id: number;
  nombre: string;
  tipo: CampanaTipo;
  estado: CampanaEstado;
  plantilla: string;
  dirigente_id: number;
  dirigente_nombre?: string;
  segmentos: string[];
  total_mensajes: number;
  funnel: CampanaFunnel;
  created_at: string;
  updated_at: string;
}

export interface CampanaAnalytics {
  id: number;
  funnel: CampanaFunnel;
  tasa_apertura: number;
  tasa_respuesta: number;
  costo_total: number;
  costo_por_mensaje: number;
}

export interface CreateCampanaPayload {
  nombre: string;
  tipo: CampanaTipo;
  plantilla: string;
  dirigente_id: number;
}

export function useCampanas() {
  return useQuery({
    queryKey: ["campanas"],
    queryFn: async () => {
      const res = await api.get<{ items: Campana[] } | Campana[]>("/campanas/");
      return Array.isArray(res) ? res : res.items;
    },
  });
}

export function useCampanaAnalytics(id?: number) {
  return useQuery({
    queryKey: ["campana-analytics", id],
    queryFn: () => api.get<CampanaAnalytics>(`/campanas/${id}/analytics`),
    enabled: !!id,
  });
}

export function useCreateCampana() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCampanaPayload) =>
      api.post<Campana>("/campanas/", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campanas"] });
    },
  });
}
