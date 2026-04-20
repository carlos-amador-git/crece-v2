/**
 * Hooks Plan IA v2 — ciclo completo 5 fases D-17.
 *
 * Consume endpoints que Agent A (backend-architect) está exponiendo:
 *   - GET  /api/v1/plan-ia/recomendaciones?estado=propuesta       (cola admin T5)
 *   - GET  /api/v1/plan-ia/recomendaciones?dirigente_id=X         (vista cliente T6)
 *   - POST /api/v1/plan-ia/generate/{dirigente_id}                (genera propuesta)
 *   - PUT  /api/v1/plan-ia/{id}/estado                            (transición de estado)
 *   - PUT  /api/v1/plan-ia/{id}/post-ejecutor                     (T7 vinculación)
 *   - GET  /api/v1/plan-ia/{id}/seguimiento                       (#10.5 ventana)
 *   - GET  /api/v1/dirigentes/{id}/posts?limit=30                 (selector ejecutor)
 *
 * BLOCKER: si Agent A no expuso aún estos endpoints al momento del merge,
 * cada hook degrada a estado vacío sin romper la UI. La E2E usa page.route
 * mocking para no depender del backend durante tests.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

export type TipoRecomendacion = "start" | "stop" | "continue";

export type EstadoRecomendacion =
  | "propuesta"
  | "aprobada"
  | "rechazada"
  | "modificada"
  | "ejecutada"
  | "completada"
  | "fallida";

export type VeredictoRecomendacion = "exitosa" | "parcial" | "fallida" | null;

export interface CriterioExito {
  metrica?: string;
  objetivo?: number;
  unidad?: string;
  descripcion?: string;
}

export interface EvidenciaRespaldo {
  post_id?: number;
  post_url?: string;
  metrica_baseline?: number;
  fuente?: string;
  bloques?: string[];
}

export interface MetadatosLLM {
  generador?: string;
  modelo?: string;
  prompt_version?: string;
  temperature?: number;
  seed?: number;
  generated_at?: string;
}

export interface Recomendacion {
  id: number;
  plan_ia_id: number | null;
  dirigente_id: number;
  dirigente_nombre?: string;
  org_id: number;
  tipo: TipoRecomendacion;
  accion_texto: string;
  ventana_inicio: string | null;
  ventana_fin: string | null;
  ventana_duracion_dias: number;
  criterio_exito: CriterioExito | null;
  principio_conductual: string | null;
  evidencia_respaldo: EvidenciaRespaldo | null;
  metadatos_llm?: MetadatosLLM | null;
  estado: EstadoRecomendacion;
  post_ejecutor_id: number | null;
  metricas_predichas: Record<string, number> | null;
  metricas_observadas: Record<string, number> | null;
  veredicto: VeredictoRecomendacion;
  veredicto_editado_por_cliente: boolean;
  veredicto_original: VeredictoRecomendacion;
  notas_cliente: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecomendacionFilters {
  estado?: EstadoRecomendacion | EstadoRecomendacion[];
  dirigente_id?: number;
  tipo?: TipoRecomendacion;
  desde?: string;
  hasta?: string;
}

function buildQuery(filters?: RecomendacionFilters): string {
  if (!filters) return "";
  const qs = new URLSearchParams();
  if (filters.estado) {
    if (Array.isArray(filters.estado)) {
      filters.estado.forEach((e) => qs.append("estado", e));
    } else {
      qs.set("estado", filters.estado);
    }
  }
  if (filters.dirigente_id) qs.set("dirigente_id", String(filters.dirigente_id));
  if (filters.tipo) qs.set("tipo", filters.tipo);
  if (filters.desde) qs.set("desde", filters.desde);
  if (filters.hasta) qs.set("hasta", filters.hasta);
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export function useRecomendaciones(filters?: RecomendacionFilters) {
  return useQuery({
    queryKey: ["recomendaciones", filters],
    queryFn: () =>
      api.get<Recomendacion[]>(`/plan-ia/recomendaciones${buildQuery(filters)}`),
  });
}

export function useRecomendacion(id: number | undefined) {
  return useQuery({
    queryKey: ["recomendacion", id],
    queryFn: () => api.get<Recomendacion>(`/plan-ia/${id}`),
    enabled: !!id,
  });
}

export function useGenerarRecomendacion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dirigenteId: number) =>
      api.post<Recomendacion[]>(`/plan-ia/generate/${dirigenteId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recomendaciones"] });
    },
  });
}

export interface TransicionEstadoPayload {
  estado: EstadoRecomendacion;
  motivo?: string;
  notas?: string;
  accion_texto?: string;
  criterio_exito?: CriterioExito;
  ventana_duracion_dias?: number;
}

export function useTransicionarEstado() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: TransicionEstadoPayload }) =>
      api.put<Recomendacion>(`/plan-ia/${id}/estado`, payload),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["recomendaciones"] });
      queryClient.invalidateQueries({ queryKey: ["recomendacion", id] });
    },
  });
}

export function useVincularPostEjecutor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, postId }: { id: number; postId: number }) =>
      api.put<Recomendacion>(`/plan-ia/${id}/post-ejecutor`, { post_id: postId }),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["recomendaciones"] });
      queryClient.invalidateQueries({ queryKey: ["recomendacion", id] });
    },
  });
}

export interface SeguimientoData {
  recomendacion_id: number;
  ventana_inicio: string;
  ventana_fin: string;
  dias_transcurridos: number;
  dias_totales: number;
  porcentaje_progreso: number;
  metricas_predichas: Record<string, number> | null;
  metricas_observadas: Record<string, number> | null;
  serie_observada: Array<{ fecha: string; valor: number; metrica: string }>;
  veredicto_provisional?: VeredictoRecomendacion;
}

export function useSeguimiento(recomendacionId: number | undefined) {
  return useQuery({
    queryKey: ["seguimiento", recomendacionId],
    queryFn: () =>
      api.get<SeguimientoData>(`/plan-ia/${recomendacionId}/seguimiento`),
    enabled: !!recomendacionId,
    refetchInterval: 60_000,
  });
}

// Posts del dirigente para el selector del post ejecutor (T7).
export interface PostDirigente {
  id: number;
  platform: string;
  content: string;
  url: string;
  likes: number;
  comments: number;
  shares: number;
  published_at: string;
}

export function usePostsDirigente(dirigenteId: number | undefined, limit = 30) {
  return useQuery({
    queryKey: ["posts-dirigente", dirigenteId, limit],
    queryFn: () =>
      api.get<PostDirigente[]>(`/dirigentes/${dirigenteId}/posts?limit=${limit}`),
    enabled: !!dirigenteId,
  });
}
