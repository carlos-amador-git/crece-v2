import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

export type PuntoEstado = "pendiente" | "visitado" | "no_encontrado" | "rechazado";

export interface RoutePunto {
  id: number;
  orden: number;
  direccion: string;
  lat: number;
  lng: number;
  estado: PuntoEstado;
  notas?: string;
}

export interface CanvassingRoute {
  id: number;
  nombre: string;
  seccion_id: string;
  encuestador: string;
  fecha: string;
  puntos_total: number;
  puntos_completados: number;
  puntos: RoutePunto[];
  created_at: string;
}

export interface OptimizeRoutePayload {
  seccion_id: string;
  encuestador: string;
  fecha: string;
  max_puntos: number;
}

export function useRoutes() {
  return useQuery({
    queryKey: ["canvassing-routes"],
    queryFn: () => api.get<CanvassingRoute[]>("/canvassing/routes"),
  });
}

export function useRouteDetail(id?: number) {
  return useQuery({
    queryKey: ["canvassing-route", id],
    queryFn: () => api.get<CanvassingRoute>(`/canvassing/routes/${id}`),
    enabled: !!id,
  });
}

export function useOptimizeRoute() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OptimizeRoutePayload) =>
      api.post<CanvassingRoute>("/canvassing/optimize", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["canvassing-routes"] });
    },
  });
}
