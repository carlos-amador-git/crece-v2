"use client";

/**
 * D-23-H · Phase B · Panel Editable de Evaluación.
 *
 * Permite a cada dirigente ajustar los pesos por categoría target_politico
 * para personalizar el cálculo del KPI Actividad Política Alineada.
 *
 * Doble métrica visible siempre:
 *   - Análisis IA (pesos default · usado en comparativas inter-dirigentes)
 *   - Tu Lectura (pesos del dirigente · vista personal)
 *
 * Decisiones consolidadas (3 revisiones · Gemini → Claude IA → CEO 2026-04-25):
 *   - Solo Palanca 1 (pesos por categoría) · Palanca 2 (override per-post) → Phase C
 *   - 3 presets políticos + Personalizado · sin sliders abstractos
 *   - last_modified stamp en columna · sin tabla history MVP
 *   - Comparativa entre dirigentes usa SIEMPRE default (no manipulable por ranking)
 */
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Save } from "lucide-react";

import { ProfileHeader } from "@/components/dirigentes/profile-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DobleKpiHero } from "@/components/evaluacion/doble-kpi-hero";
import { PresetSelector } from "@/components/evaluacion/preset-selector";
import {
  DEFAULT_PESOS,
  PRESETS,
  detectPreset,
  type PesoOption,
  type PresetKey,
} from "@/components/evaluacion/presets";
import {
  useDirigente,
  useUpdateDirigentePesos,
} from "@/lib/api/hooks/use-dirigentes";
import type { PesosTargetPolitico } from "@/lib/api/types";

export default function PanelEvaluacionPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params?.id);

  const { data: dirigente, isLoading, error } = useDirigente(id);
  const mutation = useUpdateDirigentePesos();

  // Estado local para edición optimista. Se inicializa con los pesos del backend
  // y se sincroniza vía useEffect cuando llegan los datos.
  const [pesos, setPesos] = useState<PesosTargetPolitico>(DEFAULT_PESOS);
  const [preset, setPreset] = useState<PresetKey>("conservador");
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    const remote = dirigente?.stats?.pesos_target_politico;
    if (remote) {
      setPesos(remote);
      setPreset(detectPreset(remote));
      setDirty(false);
    }
  }, [dirigente?.stats?.pesos_target_politico]);

  const handlePresetChange = (next: PresetKey) => {
    setPreset(next);
    if (next !== "personalizado") {
      const presetDef = PRESETS[next];
      setPesos(presetDef.pesos);
      setDirty(true);
    } else {
      // Custom · mantenemos los pesos actuales como punto de partida
      setDirty(true);
    }
  };

  const handleCustomPesoChange = (
    target: keyof PesosTargetPolitico,
    value: PesoOption,
  ) => {
    setPesos((prev) => ({ ...prev, [target]: value }));
    setPreset("personalizado");
    setDirty(true);
  };

  const handleSave = () => {
    mutation.mutate({ id, pesos });
  };

  // Si la mutación tuvo éxito, el invalidate refresca la query. dirty se resetea
  // en el useEffect cuando llegan los nuevos pesos del servidor.
  useEffect(() => {
    if (mutation.isSuccess) setDirty(false);
  }, [mutation.isSuccess]);

  const stats = dirigente?.stats;
  const defaultKpi = stats?.actividad_alineada_default ?? stats?.actividad_alineada;
  // El backend retorna `actividad_alineada_ajustada` cuando hay pesos. Mientras
  // el usuario edita localmente, el cálculo en vivo lo aproximamos en el cliente
  // con los conteos del breakdown · evita roundtrip por cada cambio de preset.
  const ajustadoLive = useMemo(() => {
    if (!defaultKpi || !stats?.actividad_alineada_ajustada) return undefined;
    if (defaultKpi.empty_state === "no_classified") {
      return stats.actividad_alineada_ajustada;
    }
    const NUMERATOR_BY_ROL: Record<string, Set<string>> = {
      oposicion: new Set(["oficialismo", "propio"]),
      oficialismo: new Set(["propio", "oposicion"]),
      independiente: new Set(["propio"]),
    };
    const PRODUCTIVE = ["oficialismo", "oposicion", "propio", "personal"] as const;
    const rol = (defaultKpi.rol_politico || "independiente").toLowerCase();
    const num = PRODUCTIVE
      .filter((t) => (NUMERATOR_BY_ROL[rol] || NUMERATOR_BY_ROL.independiente).has(t))
      .reduce((acc, t) => acc + pesos[t] * defaultKpi.breakdown[t], 0);
    const den = PRODUCTIVE.reduce(
      (acc, t) => acc + pesos[t] * defaultKpi.breakdown[t],
      0,
    );
    const score = den > 0 ? num / den : 0;
    return {
      ...stats.actividad_alineada_ajustada,
      score,
      score_pct: Math.round(score * 100),
      pesos,
      modo: "ajustado" as const,
    };
  }, [defaultKpi, pesos, stats?.actividad_alineada_ajustada]);

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !dirigente) {
    return (
      <div className="p-4">
        <Card>
          <CardContent className="p-4 text-sm text-rose-600">
            No se pudo cargar el dirigente.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Volver
        </Button>
        <div className="flex items-center gap-2">
          {stats?.pesos_last_modified_at && (
            <span className="text-xs text-muted-foreground">
              Última edición: {new Date(stats.pesos_last_modified_at).toLocaleString("es-MX")}
            </span>
          )}
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!dirty || mutation.isPending}
          >
            <Save className="mr-1 h-4 w-4" />
            {mutation.isPending ? "Guardando…" : dirty ? "Guardar enfoque" : "Guardado"}
          </Button>
        </div>
      </div>

      <ProfileHeader dirigente={dirigente} />

      <div>
        <h2 className="text-base font-semibold">Evaluación de actividad alineada</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Compara la lectura de la IA con tu propia interpretación. La IA
          recibe los conteos por categoría · tú decides cuánto vale cada uno.
        </p>
      </div>

      <DobleKpiHero defaultKpi={defaultKpi} ajustadoKpi={ajustadoLive} />

      <PresetSelector
        selectedPreset={preset}
        pesos={pesos}
        onPresetChange={handlePresetChange}
        onCustomPesoChange={handleCustomPesoChange}
        saving={mutation.isPending}
      />

      {mutation.isError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-xs text-rose-700 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300">
          Error al guardar pesos. Intenta de nuevo.
        </div>
      )}

      <Card>
        <CardContent className="p-4 text-xs text-muted-foreground space-y-2">
          <p>
            <strong className="text-foreground">¿Por qué dos KPIs?</strong>{" "}
            El "Análisis IA" se usa para comparar dirigentes entre sí · nadie
            puede ganar ranking ajustando pesos. "Tu Lectura" es solo para ti
            y tu equipo MD.
          </p>
          <p>
            <strong className="text-foreground">¿Y la transparencia?</strong>{" "}
            Tu equipo MD ve ambos números y la brecha entre ellos. Si la
            brecha es muy grande, sabemos que tu lectura difiere mucho de la
            IA y podemos discutirlo en sesión.
          </p>
        </CardContent>
      </Card>

      <div className="text-center">
        <Link
          href={`/dashboard/dirigentes/${id}`}
          className="text-xs text-muted-foreground underline-offset-2 hover:underline"
        >
          ← Volver a la ficha de {dirigente.full_name}
        </Link>
      </div>
    </div>
  );
}
