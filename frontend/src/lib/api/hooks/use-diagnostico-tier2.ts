import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { BloqueBase } from "./use-diagnostico-tier1";

// =========================================================================
// Shapes Tier 2 (Sprint S3 · MASTER §3.2 #11-#18)
// Alineado con SERVICES-TIER2-REPORT.md (Agent A, 2026-04-19).
// =========================================================================

// ----- B11 Cross-Partisan -----
export interface B11PostCrossPartisan {
  post_id: number;
  pct_out_of_base: number;
  n_comments_clasificados: number;
  distribucion: Record<string, number>;
}

export interface B11Data {
  score_cross_partisan_0_100: number;
  comments_por_partido: Record<string, number>;
  pct_out_of_base: number;
  partido_dirigente: string;
  posts_cross_partisan_top: B11PostCrossPartisan[];
  n_comments_clasificados: number;
  n_comments_sin_clasificacion: number;
  n_comments_total: number;
  ventana_dias: number;
  metodologia: string;
}

// ----- B12 CIB Detector -----
export interface B12FlaggedAuthor {
  author_hash: string;
  razones: string[];
  confidence: number;
  n_comments: number;
}

export interface B12Data {
  total_comments_analizados: number;
  flagged_cib: B12FlaggedAuthor[];
  authors_maestro_ceremonias: number;
  authors_coro_cluster: number;
  authors_nuevos_sospechosos: number;
  confidence_score: number;
  n_authors_unicos: number;
  n_flagged_total: number;
  umbrales: Record<string, number>;
  ventana_dias: number;
  metodologia: string;
}

// ----- B13 Filtro Realidad -----
export interface B13Data {
  er_total_comments: number;
  er_organico_comments: number;
  delta_comments_cib: number;
  pct_comments_flagged: number;
  flagged_author_count: number;
  ejemplos_flagged: string[];
  impact_hint: "alto" | "medio" | "bajo";
  flagged_hashes_para_exclusion?: string[];
  ventana_dias: number;
  note: string;
}

// ----- B14 Topic Drift -----
export interface B14PostDrift {
  post_id: number;
  drift_score: number;
  caption_tokens_top5: string[];
  comments_tokens_top5: string[];
  n_comments: number;
  published_at: string | null;
}

export interface B14Data {
  posts_con_drift: B14PostDrift[];
  drift_score_promedio: number;
  n_posts_analizados: number;
  posts_drift_alto: number;
  umbral_drift_alto: number;
  ventana_dias: number;
  metodologia: string;
}

// ----- B15 Rage Click -----
export interface B15RagePost {
  post_id: number;
  score_rage: number;
  n_comments_hostiles: number;
  n_comments_total: number;
  pct_hostil: number;
  er: number;
  signals: string[];
  published_at: string | null;
}

export interface B15Data {
  rage_clicks_detectados: number;
  pct_engagement_rage: number;
  top_posts_rage: B15RagePost[];
  n_posts_analizados: number;
  er_mediano_baseline: number;
  er_umbral_spike: number;
  umbrales: Record<string, number>;
  ventana_dias: number;
}

// ----- B16 Promesas -----
export interface B16PromesaItem {
  promesa_id: number;
  texto_promesa: string;
  fecha_compromiso: string | null;
  estado_registrado: string | null;
  evidencia_url: string | null;
  keywords_promesa: string[];
  posts_match: Array<{
    post_id: number;
    match_ratio: number;
    published_at: string | null;
    snippet: string;
  }>;
  posts_contradictorios: Array<{
    post_id: number;
    match_ratio: number;
    published_at: string | null;
    snippet: string;
  }>;
  vencida?: boolean;
}

export interface B16Data {
  promesas_cumplidas: B16PromesaItem[];
  promesas_pendientes: B16PromesaItem[];
  promesas_contradichas: B16PromesaItem[];
  n_promesas_total: number;
  pct_cumplidas: number;
  ventana_posts_dias: number;
  umbral_match_keywords: number;
  metodologia: string;
}

// ----- B17 Veda Compliance -----
export interface B17PostRiesgo {
  post_id: number;
  published_at: string | null;
  keywords_detectadas: string[];
  snippet: string;
  platform: string | null;
}

export interface B17Data {
  puede_publicar: boolean;
  razon: string;
  ventana_veda_activa: boolean;
  posts_riesgo: B17PostRiesgo[];
  n_posts_analizados: number;
  n_posts_riesgo: number;
  keywords_prohibidas: string[];
  ventana_dias: number;
  calendario_electoral_distrito: string;
  distrito: string | null;
}

// ----- B18 Violencia Política -----
export interface B18CommentViolento {
  comment_id: number;
  post_id: number;
  severity: "LOW" | "MEDIUM" | "HIGH";
  categorias: string[];
  author_hash: string;
  snippet: string;
  nlp_tono: string | null;
  published_at: string | null;
}

export interface B18Data {
  comments_violencia: B18CommentViolento[];
  severity_dist: Partial<Record<"LOW" | "MEDIUM" | "HIGH", number>>;
  total_analizados: number;
  n_violentos: number;
  pct_violento: number;
  dirigentes_objetivo: number[];
  ventana_dias: number;
  diccionarios_version: string;
  nota: string;
}

// ----- Tier1 recomputed (demo Filtro Realidad) -----
export interface Tier1Recomputed {
  er_tier1_baseline: BloqueBase & { data?: unknown };
  cib_hashes_excluidos: string[];
  note: string;
}

// ----- Respuesta agregada -----
export interface DiagnosticoTier2Response {
  dirigente_id: number;
  bloques: {
    B11_cross_partisan: BloqueBase & { data?: B11Data };
    B12_cib_detector: BloqueBase & { data?: B12Data };
    B13_filtro_realidad: BloqueBase & { data?: B13Data };
    B14_topic_drift: BloqueBase & { data?: B14Data };
    B15_rage_click: BloqueBase & { data?: B15Data };
    B16_promesas: BloqueBase & { data?: B16Data };
    B17_veda_compliance: BloqueBase & { data?: B17Data };
    B18_violencia_politica: BloqueBase & { data?: B18Data };
  };
  tier1_recomputed: Tier1Recomputed | null;
  resumen: { ok: number; insufficient_data: number; total: number };
  bloque_version: string;
}

/**
 * Hook principal: diagnóstico Tier 2 agregado.
 *
 * @param dirigenteId  id numérico del dirigente
 * @param filtroCIB    si true, solicita recompute_tier1 para demostrar el
 *                     valor del Filtro de Realidad (B13). El backend devuelve
 *                     ``tier1_recomputed`` con ER baseline + exclusiones.
 */
export function useDiagnosticoTier2(
  dirigenteId: number | string | undefined,
  filtroCIB = false,
) {
  return useQuery({
    queryKey: ["diagnostico-tier2", dirigenteId, filtroCIB],
    queryFn: () => {
      const qs = filtroCIB ? "?recompute_tier1=true" : "";
      return api.get<DiagnosticoTier2Response>(
        `/diagnostico_tier2/${dirigenteId}${qs}`,
      );
    },
    enabled:
      dirigenteId !== undefined && dirigenteId !== null && dirigenteId !== "",
    staleTime: 60_000,
  });
}
