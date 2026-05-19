/**
 * Hooks calendario de efemérides.
 * D-CALENDARIO-1 (2026-05-12).
 */
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

export interface Efemeride {
  id: number;
  mes: number;
  dia: number;
  titulo: string;
  tipo: "civica" | "internacional" | "social" | "emocional" | "familiar" | "comunidad";
  descripcion: string | null;
  ideas_politicas: string[];
  viralidad: "alta" | "media" | "baja";
  ambito: "nacional" | "internacional" | "regional";
  dias_hasta: number;
  fecha_proxima: string;
}

export function useCalendarioProximas(days: number = 30, viralidadMin?: "alta" | "media" | "baja") {
  const qs = new URLSearchParams({ days: String(days) });
  if (viralidadMin) qs.set("viralidad_minima", viralidadMin);
  return useQuery({
    queryKey: ["calendario-proximas", days, viralidadMin],
    queryFn: () => api.get<Efemeride[]>(`/calendario/proximas?${qs.toString()}`),
    staleTime: 5 * 60_000, // 5 min — fechas no cambian seguido
  });
}

export interface SugerirPostRequest {
  efemeride_id: number;
  dirigente_id: number;
  plataforma: "FACEBOOK" | "INSTAGRAM" | "TWITTER" | "TIKTOK" | "YOUTUBE";
}

export interface SugerirPostResponse {
  efemeride_titulo: string;
  dirigente_full_name: string;
  plataforma: string;
  contenido: string;
  hashtags: string[];
  fuente: "claude_api" | "plantilla_fallback";
  aviso: string | null;
}

export function useSugerirPost() {
  return useMutation({
    mutationFn: (body: SugerirPostRequest) =>
      api.post<SugerirPostResponse>("/calendario/sugerir-post", body),
  });
}

export interface ConvertirRecomendacionRequest {
  dirigente_id: number;
  plan_ia_id?: number;
}

export interface ConvertirRecomendacionResponse {
  recomendacion_id: number;
  estado: string;
  mensaje: string;
}

export function useConvertirEfemerideARecomendacion() {
  return useMutation({
    mutationFn: ({
      efemerideId,
      body,
    }: {
      efemerideId: number;
      body: ConvertirRecomendacionRequest;
    }) =>
      api.post<ConvertirRecomendacionResponse>(
        `/calendario/efemerides/${efemerideId}/convertir-recomendacion`,
        body,
      ),
  });
}
