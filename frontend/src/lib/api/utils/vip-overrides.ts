/**
 * VIP overrides — Sprint C · PLAN-2026-05-17-fans-dashboard.md
 *
 * Mockups frontend-only para casos de cliente donde la BD aún no refleja
 * la realidad pero el dirigente necesita ver la persona destacada.
 *
 * D-3 del plan: BD jamás se toca. Estos overrides viven sólo en el
 * pipeline de render del TopFansRanking. `applyVipOverrides()` se invoca
 * únicamente desde el hook de top-fans — política R-3.
 *
 * Cliente request 2026-05-17:
 *   Saymi (dirigente_id=3) debe ver a Misael (cliente_seed Director TICs
 *   Sría Turismo Oaxaca) en posición 1 del Top Fans con números
 *   realistas (~80 reactions / 12 comments). La BD aún no tiene cobertura
 *   suficiente de reactors para Misael (postmortem S-8.1 → 0/13 matches),
 *   pero el cliente necesita ver al "fan #1" en la demo.
 *
 * IMPORTANTE: la BD no se altera. El override se aplica EN MEMORIA al
 * armar el ranking. Cualquier endpoint analítico (engagement detalle,
 * benchmarking) NUNCA debe leer de aquí — usar el dataset crudo de BD.
 */

export interface VipOverride {
  external_id: string;
  position: number;
  reactions: number;
  comments: number;
  display_name?: string;
  badge: string;
  reason: string;
}

export const VIP_OVERRIDES: Record<number, Record<string, VipOverride>> = {
  // Saymi Pineda Velasco · dirigente_id=3
  3: {
    // D-MISAEL-VIP-250-FIX (2026-05-20 post-consolidación): ext_id ahora apunta
    // al row cliente_seed REAL de Misael (FB numeric ID `61578398601244`) en vez
    // del ext_id virtual `misael.gomez.981351` (que NO existía en BD).
    //
    // Bug original que esto corrige (CEO 2026-05-20 09:00):
    //   "Misael no puede estar Fan #1 con 250 Y en lugar 3 dentro de Audiencia
    //    Objetivo simultáneamente."
    //
    // Causa raíz: applyVipOverrides usa el ext_id como key para REEMPLAZAR un
    // row existente. Como `misael.gomez.981351` no matcheaba ningún row de BD,
    // el override INSERTABA un Misael virtual SEPARADO del Misael cliente_seed
    // real (87 reactions reales post-consolidación). Resultado: Misael
    // aparecía 2 veces (#1 virtual + #N real).
    //
    // Post-fix: el override matchea con cliente_seed `61578398601244`, lo
    // reemplaza por la entry mockup con 250 reactions, y NO se duplica.
    "61578398601244": {
      external_id: "61578398601244",
      position: 1,
      reactions: 250,
      comments: 12,
      display_name: "Misael Gómez",
      badge: "⭐ Fan #1",
      reason: "CEO 2026-05-20 · cliente_seed Misael ext_id=61578398601244 (post consolidación duplicados)",
    },
  },
};

export interface FanRankingEntry {
  external_id: string;
  display_name: string | null;
  handle: string | null;
  platform: string;
  source: string;
  reactions: number;
  comments: number;
  score: number;
  badge?: string;
  isVip: boolean;
}

const REACTION_WEIGHT = 1;
const COMMENT_WEIGHT = 2.5;

export function computeScore(reactions: number, comments: number): number {
  return reactions * REACTION_WEIGHT + comments * COMMENT_WEIGHT;
}

/**
 * Construye el ranking aplicando overrides VIP por dirigente.
 * - El VIP se inserta en su posición declarada.
 * - Si el VIP YA existía en la lista cruda, se REEMPLAZAN sus números por
 *   los del override (no se duplica).
 * - El resto se ordena por score desc.
 */
export function applyVipOverrides(
  dirigenteId: number,
  rawEntries: Omit<FanRankingEntry, "score" | "isVip" | "badge">[]
): FanRankingEntry[] {
  const overrides = VIP_OVERRIDES[dirigenteId] ?? {};

  // Mapa por external_id para dedupe cuando el VIP ya existe
  const byId = new Map<string, FanRankingEntry>();
  for (const e of rawEntries) {
    byId.set(e.external_id, {
      ...e,
      score: computeScore(e.reactions, e.comments),
      isVip: false,
    });
  }

  // Aplica overrides (puede inyectar entry nuevo o pisar uno existente)
  for (const ov of Object.values(overrides)) {
    const existing = byId.get(ov.external_id);
    byId.set(ov.external_id, {
      external_id: ov.external_id,
      display_name: ov.display_name ?? existing?.display_name ?? null,
      handle: existing?.handle ?? null,
      platform: existing?.platform ?? "FACEBOOK",
      source: existing?.source ?? "cliente_seed",
      reactions: ov.reactions,
      comments: ov.comments,
      score: computeScore(ov.reactions, ov.comments),
      badge: ov.badge,
      isVip: true,
    });
  }

  const list = Array.from(byId.values());

  // Sort base por score desc
  list.sort((a, b) => b.score - a.score);

  // Forzar posiciones declaradas en VIP_OVERRIDES (1-indexed)
  for (const ov of Object.values(overrides)) {
    const targetIdx = ov.position - 1;
    const currentIdx = list.findIndex((e) => e.external_id === ov.external_id);
    if (currentIdx >= 0 && currentIdx !== targetIdx && targetIdx >= 0) {
      const [vip] = list.splice(currentIdx, 1);
      list.splice(Math.min(targetIdx, list.length), 0, vip);
    }
  }

  return list;
}
