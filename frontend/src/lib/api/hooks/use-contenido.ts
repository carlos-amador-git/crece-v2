import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { PaginatedResponse } from "../types";

export type ContenidoFormato = "post" | "reel" | "story" | "carrusel" | "video" | "infografia";
export type ContenidoEstado = "borrador" | "revisado" | "aprobado" | "publicado";

export interface Contenido {
  id: number;
  dirigente_id: number;
  dirigente_nombre?: string;
  tema: string;
  formato: ContenidoFormato;
  tono: string;
  contenido: string;
  estado: ContenidoEstado;
  modelo_ia?: string;
  created_at: string;
  updated_at: string;
}

export interface ContenidoFilters {
  formato?: ContenidoFormato;
  estado?: ContenidoEstado;
  dirigente_id?: number;
  page?: number;
  per_page?: number;
}

export interface GenerateContentPayload {
  dirigente_id: number;
  formato: ContenidoFormato;
  tema: string;
  tono: string;
}

export function useContenidos(filters: ContenidoFilters = {}) {
  const params = new URLSearchParams();
  if (filters.formato) params.set("formato", filters.formato);
  if (filters.estado) params.set("estado", filters.estado);
  if (filters.dirigente_id) params.set("dirigente_id", String(filters.dirigente_id));
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));
  const qs = params.toString();

  return useQuery({
    queryKey: ["contenidos", filters],
    queryFn: () =>
      api.get<PaginatedResponse<Contenido>>(`/contenido/${qs ? `?${qs}` : ""}`),
  });
}

export function useGenerateContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateContentPayload) =>
      api.post<Contenido>("/contenido/generate", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contenidos"] });
    },
  });
}

export function useUpdateContenidoEstado() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, estado }: { id: number; estado: ContenidoEstado }) =>
      api.patch<Contenido>(`/contenido/${id}/estado`, { estado }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contenidos"] });
    },
  });
}
