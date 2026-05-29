"use client";

/**
 * D-23-H · Phase B · PresetSelector · 3 presets políticos + Personalizado.
 *
 * 80% de dirigentes elegirá un preset · 20% custom · números matemáticos
 * abstractos prohibidos por decisión Claude IA 2026-04-25.
 *
 * Custom mode usa selector 5-puntos por target (0.5/0.75/1.0/1.25/1.5) con
 * labels semánticos (Muy bajo / Bajo / Normal / Alto / Muy alto).
 */
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { PesosTargetPolitico } from "@/lib/api/types";
import {
  PESO_LABELS,
  PESO_OPTIONS,
  PRESETS,
  type PesoOption,
  type PresetKey,
} from "./presets";

const TARGET_LABELS: Record<keyof PesosTargetPolitico, string> = {
  oficialismo: "Crítica al oficialismo",
  oposicion: "Sobre oposición",
  propio: "Tu propia agenda",
  personal: "Personal",
};

const TARGET_HINTS: Record<keyof PesosTargetPolitico, string> = {
  oficialismo: "Posts donde criticas al gobierno o partido oficialista.",
  oposicion: "Posts donde hablas de partidos opositores (incluyendo el tuyo si eres oposición).",
  propio: "Tu propia agenda · logros · iniciativas · trabajo legislativo.",
  personal: "Vida personal · familia · eventos sociales · deportes.",
};

function snapToOption(v: number): PesoOption {
  // Snap valor recibido a la opción más cercana del 5-puntos.
  let best: PesoOption = 1.0;
  let dist = Infinity;
  for (const opt of PESO_OPTIONS) {
    const d = Math.abs(opt - v);
    if (d < dist) {
      dist = d;
      best = opt;
    }
  }
  return best;
}

interface PresetSelectorProps {
  selectedPreset: PresetKey;
  pesos: PesosTargetPolitico;
  onPresetChange: (preset: PresetKey) => void;
  onCustomPesoChange: (target: keyof PesosTargetPolitico, value: PesoOption) => void;
  saving?: boolean;
}

export function PresetSelector({
  selectedPreset,
  pesos,
  onPresetChange,
  onCustomPesoChange,
  saving = false,
}: PresetSelectorProps) {
  const isCustom = selectedPreset === "personalizado";

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div>
          <h3 className="text-sm font-semibold">Tu enfoque</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Elige un preset político o ajusta cada categoría manualmente.
            La IA usa estos pesos solo para tu vista personal.
          </p>
        </div>

        <div className="grid gap-2 md:grid-cols-2">
          {(Object.values(PRESETS) as Array<typeof PRESETS[keyof typeof PRESETS]>).map((p) => (
            <button
              key={p.key}
              type="button"
              onClick={() => onPresetChange(p.key)}
              disabled={saving}
              className={cn(
                "rounded-lg border p-3 text-left transition disabled:opacity-50",
                selectedPreset === p.key
                  ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                  : "border-border hover:bg-muted/50",
              )}
              aria-pressed={selectedPreset === p.key}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "h-3 w-3 rounded-full border-2",
                    selectedPreset === p.key
                      ? "border-primary bg-primary"
                      : "border-muted-foreground/40",
                  )}
                />
                <span className="text-sm font-medium">{p.label}</span>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground leading-snug">
                {p.description}
              </p>
            </button>
          ))}
          <button
            type="button"
            onClick={() => onPresetChange("personalizado")}
            disabled={saving}
            className={cn(
              "rounded-lg border p-3 text-left transition disabled:opacity-50 md:col-span-2",
              isCustom
                ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                : "border-border hover:bg-muted/50",
            )}
            aria-pressed={isCustom}
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "h-3 w-3 rounded-full border-2",
                  isCustom
                    ? "border-primary bg-primary"
                    : "border-muted-foreground/40",
                )}
              />
              <span className="text-sm font-medium">Personalizado</span>
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground leading-snug">
              Ajusta cada categoría individualmente con 5 niveles de peso.
            </p>
          </button>
        </div>

        {isCustom && (
          <div className="rounded-lg border bg-muted/20 p-3 space-y-3">
            {(Object.keys(TARGET_LABELS) as Array<keyof PesosTargetPolitico>).map((target) => {
              const current = snapToOption(pesos[target]);
              return (
                <div key={target}>
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs font-medium">{TARGET_LABELS[target]}</span>
                    <span className="text-[11px] text-muted-foreground">
                      {PESO_LABELS[current]} · {current.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[10px] text-muted-foreground/80 leading-snug">
                    {TARGET_HINTS[target]}
                  </p>
                  <div
                    className="mt-1.5 grid grid-cols-5 gap-1"
                    role="radiogroup"
                    aria-label={TARGET_LABELS[target]}
                  >
                    {PESO_OPTIONS.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        role="radio"
                        aria-checked={current === opt}
                        onClick={() => onCustomPesoChange(target, opt)}
                        disabled={saving}
                        className={cn(
                          "rounded-md border py-1.5 text-[11px] transition disabled:opacity-50",
                          current === opt
                            ? "border-primary bg-primary/10 font-semibold"
                            : "border-border hover:bg-muted/40",
                        )}
                      >
                        {PESO_LABELS[opt]}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
