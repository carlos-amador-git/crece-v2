/**
 * @deprecated 2026-04-25 (D-23-G' reformulación · supersedida por Actividad Política Alineada)
 *
 * El KPI principal pasó de "Sentimiento Prom. flipeado" a "Actividad Política
 * Alineada (% por target_politico)". Ver:
 *   - .context/PLAN-D-23-G-actividad-alineada-2026-04-24.md
 *   - app/services/actividad_alineada.py (backend)
 *   - components/dashboard/actividad-alineada-card.tsx (frontend)
 *
 * Este helper se mantiene como referencia · NO se elimina del bundle por
 * decisión CEO (preservar lógica reversible). Si Phase B "humano clasifica"
 * se activa eventualmente, ESTE helper podría reusarse para flipear las
 * sugerencias IA a presentar al dirigente. Mientras tanto, ningún caller
 * en producción debe importarlo.
 *
 * Ajuste de sentimiento por rol político · D-23-G · sesión 2026-04-24.
 *
 * El CEO estableció como regla operativa: el multiplicador de sentimiento
 * se define a nivel de "grupo" (partido → rol). Si el dirigente es
 * oposición, las críticas al oficialismo (que aparecen como sentimiento
 * negativo crudo) son favorables a su narrativa política y deben mostrarse
 * como positivas en su dashboard.
 *
 * Mapeo reutilizado de `./rol.ts` (federal CDMX / nacional):
 *   MORENA/PT/PVEM  → oficialismo → score crudo (sin flip)
 *   MC/PAN/PRI/PRD  → oposicion   → score × -1 (flip)
 *   independiente   → crudo (fallback)
 *
 * Importante: este helper es la ÚNICA fuente del multiplicador de signo.
 * No inventar flips en componentes individuales. Reusar estas funciones.
 *
 * Sin `is_political` confiable en el schema actual, el flip se aplica
 * uniformemente por rol del dirigente. Cuando F1.1 restaure `tono_discurso`
 * + `target_politico` + clasificación Layer 2, este helper debe extenderse
 * a considerar la dimensión política per-post.
 */
import { rolFromPartido } from "./rol";

/**
 * Ajusta un score de sentimiento (-1..+1) al rol del dirigente.
 *
 * Oposición: devuelve `-score` (flip del signo).
 * Oficialismo / independiente: devuelve el score crudo.
 * Null/undefined: devuelve null (no fabricar valor).
 */
export function adjustSentimentScoreForRole(
  score: number | null | undefined,
  partido: string | null | undefined,
): number | null {
  if (score == null) return null;
  const rol = rolFromPartido(partido);
  if (rol === "oposicion") return -score;
  return score;
}

/**
 * Ajusta el label textual de sentimiento al rol del dirigente.
 *
 * Oposición: swap positive ↔ negative. Neutral se mantiene.
 * Oficialismo / independiente: se mantiene el label original.
 * Null/undefined: devuelve null.
 */
export function adjustSentimentLabelForRole(
  label: string | null | undefined,
  partido: string | null | undefined,
): string | null {
  if (!label) return null;
  const rol = rolFromPartido(partido);
  if (rol !== "oposicion") return label;
  const k = label.toLowerCase();
  if (k === "positive") return "negative";
  if (k === "negative") return "positive";
  return label;
}

/**
 * Ajusta una distribución agregada {positive, negative, neutral}.
 *
 * Oposición: swap counts positive ↔ negative.
 * Oficialismo / independiente: distribución sin cambio.
 */
export function adjustSentimentDistributionForRole<
  T extends { positive: number; negative: number; neutral: number },
>(dist: T, partido: string | null | undefined): T {
  const rol = rolFromPartido(partido);
  if (rol !== "oposicion") return dist;
  return { ...dist, positive: dist.negative, negative: dist.positive };
}

/**
 * Deriva el label textual de sentimiento desde un score en rango -1..+1.
 *
 * Thresholds: `>0.2 positive`, `<-0.2 negative`, resto `neutral`.
 * Null/undefined → null (no fabricar).
 *
 * Útil cuando el score ya fue ajustado por rol (flip aplicado) y necesitamos
 * el label coherente con el valor numérico final. Reemplaza el threshold
 * 0.4/0.6 original que estaba mal para rango -1..+1.
 */
export function deriveSentimentLabelFromScore(
  score: number | null | undefined,
): "positive" | "negative" | "neutral" | null {
  if (score == null) return null;
  if (score > 0.2) return "positive";
  if (score < -0.2) return "negative";
  return "neutral";
}
