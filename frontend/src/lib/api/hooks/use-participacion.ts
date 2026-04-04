import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { PaginatedResponse } from "../types";

export type SolicitudTipo = "queja" | "peticion" | "propuesta" | "denuncia" | "informacion";
export type SolicitudEstado = "nueva" | "en_proceso" | "resuelta" | "cerrada" | "rechazada";
export type SolicitudPrioridad = "alta" | "media" | "baja";
export type SolicitudCanal = "presencial" | "telefono" | "whatsapp" | "web" | "redes_sociales";

export interface Solicitud {
  id: number;
  tipo: SolicitudTipo;
  titulo: string;
  descripcion: string;
  estado: SolicitudEstado;
  prioridad: SolicitudPrioridad;
  canal: SolicitudCanal;
  ciudadano_nombre?: string;
  created_at: string;
  updated_at: string;
}

export interface ParticipacionDashboard {
  total: number;
  por_tipo: Record<SolicitudTipo, number>;
  por_estado: Record<SolicitudEstado, number>;
  avg_resolution_hours: number;
}

export interface SolicitudFilters {
  tipo?: SolicitudTipo;
  estado?: SolicitudEstado;
  prioridad?: SolicitudPrioridad;
  page?: number;
  per_page?: number;
}

export interface CreateSolicitudPayload {
  tipo: SolicitudTipo;
  titulo: string;
  descripcion: string;
  canal: SolicitudCanal;
}

export function useSolicitudes(filters: SolicitudFilters = {}) {
  const params = new URLSearchParams();
  if (filters.tipo) params.set("tipo", filters.tipo);
  if (filters.estado) params.set("estado", filters.estado);
  if (filters.prioridad) params.set("prioridad", filters.prioridad);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));
  const qs = params.toString();

  return useQuery({
    queryKey: ["solicitudes", filters],
    queryFn: () =>
      api.get<PaginatedResponse<Solicitud>>(
        `/participacion/${qs ? `?${qs}` : ""}`
      ),
  });
}

export function useParticipacionDashboard() {
  return useQuery({
    queryKey: ["participacion-dashboard"],
    queryFn: () => api.get<ParticipacionDashboard>("/participacion/dashboard"),
  });
}

export function useCreateSolicitud() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateSolicitudPayload) =>
      api.post<Solicitud>("/participacion/", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["solicitudes"] });
      queryClient.invalidateQueries({ queryKey: ["participacion-dashboard"] });
    },
  });
}
