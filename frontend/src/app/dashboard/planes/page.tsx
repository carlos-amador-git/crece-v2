"use client";

import { useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { usePlanes, useGeneratePlan, useApprovePlan, useRejectPlan } from "@/lib/api/hooks/use-planes";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDate } from "@/lib/utils";
import type { PlanIA, PlanType } from "@/lib/api/types";
import {
  Brain,
  Check,
  X,
  Loader2,
  Sparkles,
} from "lucide-react";

const PLAN_TYPES: { value: PlanType; label: string }[] = [
  { value: "DIAGNOSTICO", label: "Diagnostico" },
  { value: "CONSOLIDACION", label: "Consolidacion" },
  { value: "CRISIS", label: "Crisis" },
  { value: "CONTENIDO", label: "Contenido" },
];

const TIPO_SUBTITLES: Record<string, string> = {
  DIAGNOSTICO: "Presencia Digital",
  CONSOLIDACION: "Plan 90 dias",
  CRISIS: "Manejo de Crisis",
  CONTENIDO: "Calendario Editorial",
};

const TIPO_COLORS: Record<string, string> = {
  DIAGNOSTICO: "bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200",
  CONSOLIDACION: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200",
  CRISIS: "bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-200",
  CONTENIDO: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200",
};

export default function PlanesPage() {
  const [generateOpen, setGenerateOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<PlanIA | null>(null);
  const [newPlanDirigente, setNewPlanDirigente] = useState("");
  const [newPlanType, setNewPlanType] = useState<PlanType>("DIAGNOSTICO");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const { data, isLoading } = usePlanes(undefined, 1);
  const { data: dirigentesData } = useDirigentes({ per_page: 50 });
  const generateMutation = useGeneratePlan();
  const approveMutation = useApprovePlan();
  const rejectMutation = useRejectPlan();

  const plans = data?.items ?? [];
  const dirigentesForSelect = dirigentesData?.items ?? [];

  // Build dirigente name lookup
  const dirigenteNames: Record<number, string> = {};
  for (const d of dirigentesForSelect) {
    dirigenteNames[d.id] = d.full_name;
  }

  // Filter by status
  const filteredPlans =
    filterStatus === "all"
      ? plans
      : filterStatus === "approved"
      ? plans.filter((p) => p.aprobado)
      : filterStatus === "draft"
      ? plans.filter((p) => !p.aprobado)
      : plans;

  // Group plans by dirigente+tipo for version numbering
  const versionMap = new Map<string, number>();
  const sortedPlans = [...plans].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  for (const plan of sortedPlans) {
    const key = `${plan.dirigente_id}-${plan.tipo}`;
    const current = versionMap.get(key) ?? 0;
    versionMap.set(key, current + 1);
  }
  // Now build version for each plan
  function getPlanVersion(plan: PlanIA): number {
    const key = `${plan.dirigente_id}-${plan.tipo}`;
    const sameGroup = sortedPlans.filter(
      (p) => p.dirigente_id === plan.dirigente_id && p.tipo === plan.tipo
    );
    const idx = sameGroup.findIndex((p) => p.id === plan.id);
    return idx + 1;
  }

  const handleGenerate = async () => {
    if (!newPlanDirigente) return;
    try {
      await generateMutation.mutateAsync({
        dirigente_id: Number(newPlanDirigente),
        tipo: newPlanType,
      });
      setGenerateOpen(false);
    } catch {
      // Error handling managed by React Query
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Planes IA</h1>
          <p className="text-sm text-muted-foreground">
            Planes estrategicos generados con inteligencia artificial
          </p>
        </div>
        <Button onClick={() => setGenerateOpen(true)}>
          <Sparkles className="h-4 w-4" />
          Generar Plan
        </Button>
      </div>

      {/* Status filter */}
      <div className="flex gap-2">
        {[
          { value: "all", label: "Todos" },
          { value: "draft", label: "Borrador" },
          { value: "approved", label: "Aprobado" },
        ].map((status) => (
          <Button
            key={status.value}
            variant={filterStatus === status.value ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterStatus(status.value)}
          >
            {status.label}
          </Button>
        ))}
      </div>

      {/* Plans list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : filteredPlans.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Brain className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="font-medium">No hay planes</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Genera un nuevo plan con IA para comenzar
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredPlans.map((plan) => {
            const preview = (plan.contenido ?? "")
              .slice(0, 250)
              .replace(/[#*|_]/g, "")
              .trim();
            const tipoLabel = PLAN_TYPES.find((t) => t.value === plan.tipo)?.label ?? plan.tipo;
            const subtitle = TIPO_SUBTITLES[plan.tipo] ?? "";
            const tipoColor = TIPO_COLORS[plan.tipo] ?? "bg-muted text-muted-foreground";
            const version = getPlanVersion(plan);
            const dirigenteName = dirigenteNames[plan.dirigente_id] ?? `Dirigente #${plan.dirigente_id}`;
            const createdTime = new Date(plan.created_at).toLocaleString("es-MX", {
              day: "numeric",
              month: "short",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });
            const charCount = ((plan.contenido ?? "").length / 1000).toFixed(1);

            return (
              <Card
                key={plan.id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => setSelectedPlan(plan)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <Badge className={tipoColor}>{plan.tipo}</Badge>
                        <Badge variant="outline" className="text-[10px]">
                          v{version}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {dirigenteName}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {createdTime}
                        </span>
                      </div>
                      <p className="font-heading font-semibold text-foreground">
                        {tipoLabel} — {subtitle}
                      </p>
                      <p className="mt-1.5 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                        {preview || "Sin contenido"}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          {plan.modelo_ia ?? "IA"}
                        </span>
                        <span>{charCount}K caracteres</span>
                        <span>Plan #{plan.id}</span>
                      </div>
                    </div>
                    <Badge variant={plan.aprobado ? "default" : "secondary"} className="shrink-0">
                      {plan.aprobado ? "Aprobado" : "Borrador"}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Plan detail dialog */}
      <Dialog
        open={!!selectedPlan}
        onOpenChange={(open) => !open && setSelectedPlan(null)}
      >
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
          {selectedPlan && (() => {
            const tipoLabel = PLAN_TYPES.find((t) => t.value === selectedPlan.tipo)?.label ?? selectedPlan.tipo;
            const subtitle = TIPO_SUBTITLES[selectedPlan.tipo] ?? "";
            const tipoColor = TIPO_COLORS[selectedPlan.tipo] ?? "bg-muted text-muted-foreground";
            const dirigenteName = dirigenteNames[selectedPlan.dirigente_id] ?? `Dirigente #${selectedPlan.dirigente_id}`;

            return (
              <>
                <DialogHeader>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge className={tipoColor}>{selectedPlan.tipo}</Badge>
                    <Badge variant={selectedPlan.aprobado ? "default" : "secondary"}>
                      {selectedPlan.aprobado ? "Aprobado" : "Borrador"}
                    </Badge>
                  </div>
                  <DialogTitle className="text-xl">
                    {tipoLabel} — {subtitle}
                  </DialogTitle>
                  <DialogDescription>
                    {dirigenteName} &mdash; {formatDate(selectedPlan.created_at)}
                    {selectedPlan.modelo_ia && (
                      <span className="ml-2 inline-flex items-center gap-1">
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        {selectedPlan.modelo_ia}
                      </span>
                    )}
                  </DialogDescription>
                </DialogHeader>
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>{selectedPlan.contenido}</ReactMarkdown>
                </div>
                {!selectedPlan.aprobado && (
                  <DialogFooter className="gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        rejectMutation.mutate(selectedPlan.id);
                        setSelectedPlan(null);
                      }}
                      disabled={rejectMutation.isPending}
                    >
                      <X className="h-4 w-4" />
                      Rechazar
                    </Button>
                    <Button
                      onClick={() => {
                        approveMutation.mutate(selectedPlan.id);
                        setSelectedPlan(null);
                      }}
                      disabled={approveMutation.isPending}
                    >
                      <Check className="h-4 w-4" />
                      Aprobar
                    </Button>
                  </DialogFooter>
                )}
              </>
            );
          })()}
        </DialogContent>
      </Dialog>

      {/* Generate plan dialog */}
      <Dialog open={generateOpen} onOpenChange={setGenerateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generar Plan con IA</DialogTitle>
            <DialogDescription>
              Selecciona el dirigente y tipo de plan para generar una estrategia
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Dirigente</label>
              <Select
                value={newPlanDirigente}
                onValueChange={setNewPlanDirigente}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar dirigente" />
                </SelectTrigger>
                <SelectContent>
                  {dirigentesForSelect.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Tipo de Plan</label>
              <Select
                value={newPlanType}
                onValueChange={(v) => setNewPlanType(v as PlanType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PLAN_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setGenerateOpen(false)}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleGenerate}
              disabled={!newPlanDirigente || generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generando...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Generar
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
