/**
 * D-23-H · Phase B · Presets políticos
 *
 * Decisión Claude IA · 2026-04-25 · 3 presets + Personalizado en lugar de
 * sliders abstractos Baja/Normal/Alta. Lenguaje del usuario, no abstracción
 * matemática. 80% elige preset · sin tocar custom.
 *
 * Calibración v0 · iterar con Piña/Ballesteros pre-ship piloto.
 */
import type { PesosTargetPolitico } from "@/lib/api/types";

export type PresetKey = "conservador" | "balanceado" | "combativo" | "personalizado";

export interface PresetDef {
  key: PresetKey;
  label: string;
  description: string;
  pesos: PesosTargetPolitico;
}

export const PRESETS: Record<Exclude<PresetKey, "personalizado">, PresetDef> = {
  conservador: {
    key: "conservador",
    label: "Conservador",
    description: "Pesos neutros · KPI sin ajuste · igual que la lectura IA pura.",
    pesos: { oficialismo: 1.0, oposicion: 1.0, propio: 1.0, personal: 1.0 },
  },
  balanceado: {
    key: "balanceado",
    label: "Balanceado",
    description:
      "Sube ligeramente la crítica al rival y mantiene tu agenda propia. Por defecto para la mayoría.",
    pesos: { oficialismo: 1.0, oposicion: 1.3, propio: 1.0, personal: 1.0 },
  },
  combativo: {
    key: "combativo",
    label: "Combativo",
    description:
      "Premia fuerte la confrontación con el rival y tu propia agenda. Reduce el peso de lo personal.",
    pesos: { oficialismo: 1.0, oposicion: 1.5, propio: 1.2, personal: 0.8 },
  },
};

export const DEFAULT_PESOS: PesosTargetPolitico = {
  oficialismo: 1.0,
  oposicion: 1.0,
  propio: 1.0,
  personal: 1.0,
};

// 5 puntos discretos para selector custom · cap 0.5-1.5.
export const PESO_OPTIONS = [0.5, 0.75, 1.0, 1.25, 1.5] as const;
export type PesoOption = (typeof PESO_OPTIONS)[number];

export const PESO_LABELS: Record<PesoOption, string> = {
  0.5: "Muy bajo",
  0.75: "Bajo",
  1.0: "Normal",
  1.25: "Alto",
  1.5: "Muy alto",
};

export function detectPreset(p: PesosTargetPolitico): PresetKey {
  for (const def of Object.values(PRESETS)) {
    const match = (Object.keys(def.pesos) as Array<keyof PesosTargetPolitico>).every(
      (k) => Math.abs(def.pesos[k] - p[k]) < 0.01,
    );
    if (match) return def.key;
  }
  return "personalizado";
}
