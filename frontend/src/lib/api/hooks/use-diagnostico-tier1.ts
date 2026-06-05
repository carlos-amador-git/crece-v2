import { useQuery } from "@tanstack/react-query";
import { api } from "../client";

// --- Shapes crudos (del Agent A · confirmado empíricamente Piña id=1) ---

export type BloqueStatus = "ok" | "insufficient_data";

export interface BloqueBase {
  status: BloqueStatus;
  bloque: string;
  bloque_version: string;
  computed_at: string;
  missing?: string[];
  warnings?: string[];
  data?: unknown;
}

// B01 ER normalizado
export interface B01PlatformData {
  er_actual_pct: number;
  er_esperado_rango_pct: [number, number];
  ratio_vs_min: number;
  posicion: "bajo_rango" | "dentro_rango" | "sobre_rango";
  dentro_rango: boolean;
  n_posts: number;
  followers: number;
  zenodo_validated?: boolean;
}
export interface B01Data {
  er_por_plataforma: Record<string, B01PlatformData>;
  estrato: string;
  estrato_inferido: boolean;
  modificador_temporal: number;
  ventana_electoral_activa: boolean;
  dias_a_comicio: number | null;
  ventana_dias_analizada: number;
  n_posts_total: number;
  matriz_version: string;
}

// B02 Breakout Scale
export interface B02Data {
  max_categoria: number;
  posts_por_categoria: Record<string, number>;
  posts_breakout: Array<{
    post_id: number;
    platform: string;
    views: number;
    followers: number;
    ratio: number;
    categoria: number;
  }>;
  views_breakout_pct: number;
  n_posts_evaluados: number;
  fidelity: string;
  nota: string;
}

// B03 Matriz 2x2
export interface B03PostPoint {
  post_id: number;
  platform: string;
  engagement_rate: number;
  sentiment_score: number;
  cuadrante: "INSIGNIA" | "CRISIS" | "VANIDAD" | "MUERTA";
  likes: number;
  comments: number;
  shares: number;
  published_at: string;
}
export interface B03Data {
  posts: B03PostPoint[];
  conteo_cuadrantes: Record<string, number>;
  umbral_engagement: number;
  umbral_sentiment: number;
  n_posts: number;
  leyenda: Record<string, string>;
}

// B04 Benchmark
export interface B04RivalItem {
  dirigente_id: number;
  full_name?: string;
  followers_total: number;
  n_plataformas: number;
  posts_28d: number;
  posts_semana: number;
  er_avg_pct: number | null;
  sentiment_avg: number | null;
  status: string;
}
export interface B04Data {
  self: B04RivalItem & { full_name: string };
  rivales: B04RivalItem[];
  origen_competidores: string;
  ventana_dias: number;
  nota_d22?: string;
}

// B05 Plutchik
export interface B05Data {
  emociones_promedio: Record<string, number>;
  n_posts_con_emotions: number;
  n_comments_con_emotions: number;
  ratio_trust_anger: number;
  warnings?: string[];
  ventana_dias: number;
}

// B06 Crisis Spike
export interface B06Data {
  spike_detected: boolean;
  severity: number;
  ventana_inicio: string;
  ventana_fin: string;
  posts_toxicos_2h: number;
  posts_toxicos_baseline_hora: number;
  tasa_actual_hora: number;
  toxic_posts: Array<{ post_id: number; platform: string; sentiment_score?: number }>;
  umbrales: Record<string, number>;
}

// B07 Growth Attribution (puede ser insufficient)
export interface B07Data {
  top_posts?: Array<{ post_id: number; platform: string; contribution_pct: number; published_at: string }>;
  followers_start?: number;
  followers_end?: number;
  delta_followers?: number;
  half_life_days?: number;
}

// B08 SoV
export interface B08Data {
  self_pct?: number;
  rivales_pct?: Record<string, number>;
  topic_principal?: string;
  topics?: Array<{ topic: string; self_pct: number }>;
}

// B09 Share/Like Ratio
export interface B09Data {
  ratio_promedio: number;
  ratio_mediana: number;
  n_posts: number;
  posts_virales: Array<{
    post_id: number;
    platform: string;
    likes: number;
    shares: number;
    ratio: number;
    published_at: string;
  }>;
  semaforo: "VERDE" | "AMARILLO" | "ROJO";
  percentil_vs_estrato: number;
  estrato: string;
  umbrales: Record<string, number>;
  nota_fidelity?: string;
}

// B10 Humanización
export interface B10Data {
  score_0_100: number;
  factores: Record<string, number>;
  interpretacion: "Institucional" | "Mixto" | "Humano" | string;
  n_posts: number;
  ventana_dias: number;
  pesos_formula: Record<string, number>;
}

// B10 Humanización drill-down (T0.5)
export interface HumanizacionPostExample {
  post_id: number;
  content_preview: string;
  score: number;
  factores: string[];
  published_at: string | null;
  platform: string | null;
}

export interface HumanizacionExamplesResponse {
  status: "ok" | "insufficient_data" | "dirigente_not_found";
  top_institucional: HumanizacionPostExample[];
  top_humanizante: HumanizacionPostExample[];
  keywords_usadas: {
    primera_persona: string[];
    emojis_humanos: string[];
    institucional: string[];
  };
  n_posts_analizados: number;
  ventana_dias: number;
  missing?: string[];
}

export interface DiagnosticoResponse {
  dirigente_id: number;
  bloques: {
    B01_er_normalizado: BloqueBase & { data?: B01Data };
    B02_breakout_scale: BloqueBase & { data?: B02Data };
    B03_matriz_2x2: BloqueBase & { data?: B03Data };
    B04_benchmark: BloqueBase & { data?: B04Data };
    B05_sentiment_plutchik: BloqueBase & { data?: B05Data };
    B06_crisis_spike: BloqueBase & { data?: B06Data };
    B07_growth_attribution: BloqueBase & { data?: B07Data };
    B08_sov: BloqueBase & { data?: B08Data };
    B09_share_like_ratio: BloqueBase & { data?: B09Data };
    B10_humanizacion: BloqueBase & { data?: B10Data };
  };
  resumen: { ok: number; insufficient_data: number; total: number };
  bloque_version: string;
}

export function useDiagnosticoTier1(dirigenteId: number | string | undefined) {
  return useQuery({
    queryKey: ["diagnostico-tier1", dirigenteId],
    queryFn: () =>
      api.get<DiagnosticoResponse>(`/diagnostico/${dirigenteId}`),
    enabled: dirigenteId !== undefined && dirigenteId !== null && dirigenteId !== "",
    staleTime: 60_000, // 1 min — el cómputo no cambia en segundos
  });
}

export function useHumanizacionExamples(
  dirigenteId: number | string | undefined,
  limit = 5,
) {
  return useQuery({
    queryKey: ["humanizacion-examples", dirigenteId, limit],
    queryFn: () =>
      api.get<HumanizacionExamplesResponse>(
        `/diagnostico/${dirigenteId}/humanizacion/examples?limit=${limit}`,
      ),
    enabled: dirigenteId !== undefined && dirigenteId !== null && dirigenteId !== "",
    staleTime: 120_000, // 2 min — drill-down no necesita refresh frecuente
  });
}
