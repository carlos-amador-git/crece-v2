import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

// ── Enums matching backend ────────────────────────────────

export type ResultadoVisita =
  | "encuesta_completada"
  | "no_en_casa"
  | "rechazo"
  | "reagendado"
  | "direccion_incorrecta";

export type EstadoRuta =
  | "pendiente"
  | "en_progreso"
  | "completada"
  | "cancelada";

// ── Response types matching backend Pydantic schemas ──────

export interface PuntoRutaResponse {
  id: number;
  orden: number;
  ciudadano_id: number;
  ciudadano_nombre: string | null;
  visitado: boolean;
  visitado_at: string | null;
  resultado: ResultadoVisita | null;
  notas: string | null;
  lat: number | null;
  lon: number | null;
}

export interface RouteProgressResponse {
  total: number;
  completados: number;
  porcentaje: number;
  distancia_restante_km: number | null;
}

export interface RutaCanvassingResponse {
  id: number;
  org_id: number | null;
  encuestador_id: number;
  seccion_id: number | null;
  nombre: string;
  fecha_asignada: string;
  estado: EstadoRuta;
  distancia_total_km: number | null;
  tiempo_estimado_min: number | null;
  puntos_total: number;
  puntos_completados: number;
  notas: string | null;
  created_at: string;
  updated_at: string;
  puntos: PuntoRutaResponse[];
  progress: RouteProgressResponse | null;
  geometry_geojson: Record<string, unknown> | null;
}

export interface NearbyCiudadanoResponse {
  id: number;
  nombre: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  direccion: string | null;
  lat: number | null;
  lon: number | null;
  distancia_km: number;
}

// ── Request types matching backend Pydantic schemas ───────

export interface OptimizeRoutePayload {
  seccion_id: number;
  encuestador_id: number;
  fecha: string;
  ciudadano_ids?: number[] | null;
  max_puntos?: number;
  priorizar_score?: boolean;
}

export interface MarkVisitadoPayload {
  resultado: ResultadoVisita;
  notas?: string | null;
}

export function useRoutes(params?: {
  encuestador_id?: number;
  fecha?: string;
  estado?: EstadoRuta;
  seccion_id?: number;
  limit?: number;
  offset?: number;
}) {
  const qs = params
    ? Object.entries(params)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
        .join("&")
    : "";
  return useQuery({
    queryKey: ["canvassing-routes", params],
    queryFn: () =>
      api.get<RutaCanvassingResponse[]>(
        `/canvassing/routes${qs ? `?${qs}` : ""}`
      ),
  });
}

export function useRouteDetail(id?: number) {
  return useQuery({
    queryKey: ["canvassing-route", id],
    queryFn: () =>
      api.get<RutaCanvassingResponse>(`/canvassing/routes/${id}`),
    enabled: !!id,
  });
}

export function useRouteProgress(routeId?: number) {
  return useQuery({
    queryKey: ["canvassing-route-progress", routeId],
    queryFn: () =>
      api.get<RouteProgressResponse>(
        `/canvassing/routes/${routeId}/progress`
      ),
    enabled: !!routeId,
  });
}

export function useOptimizeRoute() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OptimizeRoutePayload) =>
      api.post<RutaCanvassingResponse>("/canvassing/optimize", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["canvassing-routes"] });
    },
  });
}

export function useMarkPuntoVisited() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      routeId,
      puntoId,
      payload,
    }: {
      routeId: number;
      puntoId: number;
      payload: MarkVisitadoPayload;
    }) =>
      api.patch<PuntoRutaResponse>(
        `/canvassing/routes/${routeId}/punto/${puntoId}`,
        payload
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["canvassing-route", variables.routeId],
      });
      queryClient.invalidateQueries({ queryKey: ["canvassing-routes"] });
    },
  });
}

export function useNearby(params: {
  lat: number;
  lon: number;
  radius_km?: number;
  seccion_id?: number;
}) {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");
  return useQuery({
    queryKey: ["canvassing-nearby", params],
    queryFn: () =>
      api.get<NearbyCiudadanoResponse[]>(`/canvassing/nearby?${qs}`),
    enabled: params.lat !== 0 && params.lon !== 0,
  });
}

export function useCancelRoute() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (routeId: number) =>
      api.delete(`/canvassing/routes/${routeId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["canvassing-routes"] });
    },
  });
}

// ── Geo visualization (ciudadanos_legacy) ──────────────────

export interface CanvassingGeoFilters {
  alcaldia_id?: number;
  estrato?: string;
  volatilidad_min?: number;
  volatilidad_max?: number;
  nivel_participacion?: number;
  contactado?: string;
  seccion?: string;
  dtto_local?: string;
  dtto_federal?: string;
  limit?: number;
}

export interface GeoStatsAlcaldia {
  alcaldia_id: number;
  nombre: string;
  count: number;
}

export interface GeoStatsEstrato {
  estrato: string;
  count: number;
}

export interface GeoStatsNivel {
  nivel: string;
  count: number;
}

export interface CanvassingGeoStats {
  total: number;
  con_geo: number;
  por_alcaldia: GeoStatsAlcaldia[];
  por_estrato: GeoStatsEstrato[];
  por_nivel_participacion: GeoStatsNivel[];
  volatilidad_range: { min: number; max: number; avg: number };
}

export function useCanvassingGeo(filters: CanvassingGeoFilters) {
  const qs = Object.entries(filters)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");
  return useQuery<GeoJSON.FeatureCollection>({
    queryKey: ["canvassing-geo", filters],
    queryFn: () =>
      api.get<GeoJSON.FeatureCollection>(
        `/canvassing/geo${qs ? `?${qs}` : ""}`
      ),
  });
}

export function useCanvassingGeoStats() {
  return useQuery<CanvassingGeoStats>({
    queryKey: ["canvassing-geo-stats"],
    queryFn: () =>
      api.get<CanvassingGeoStats>("/canvassing/geo-stats"),
  });
}
