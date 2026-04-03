"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { usePlanes, useGeneratePlan, useApprovePlan, useRejectPlan } from "@/lib/api/hooks/use-planes";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import type { PlanIA, PlanStatus, PlanType } from "@/lib/api/types";
import {
  Brain,
  Plus,
  Check,
  X,
  FileText,
  Loader2,
  Sparkles,
  Clock,
  CheckCircle2,
  XCircle,
  Rocket,
} from "lucide-react";

const PLAN_TYPES: { value: PlanType; label: string }[] = [
  { value: "crecimiento", label: "Crecimiento" },
  { value: "crisis", label: "Crisis" },
  { value: "engagement", label: "Engagement" },
  { value: "posicionamiento", label: "Posicionamiento" },
  { value: "contenido", label: "Contenido" },
];

const STATUS_CONFIG: Record<
  PlanStatus,
  { label: string; variant: "default" | "secondary" | "success" | "danger"; icon: typeof Clock }
> = {
  draft: { label: "Borrador", variant: "secondary", icon: Clock },
  approved: { label: "Aprobado", variant: "success", icon: CheckCircle2 },
  rejected: { label: "Rechazado", variant: "danger", icon: XCircle },
  executed: { label: "Ejecutado", variant: "default", icon: Rocket },
};

export default function PlanesPage() {
  const [generateOpen, setGenerateOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<PlanIA | null>(null);
  const [newPlanDirigente, setNewPlanDirigente] = useState("");
  const [newPlanType, setNewPlanType] = useState<PlanType>("crecimiento");
  const [filterStatus, setFilterStatus] = useState<PlanStatus | "all">("all");

  const { data, isLoading } = usePlanes(
    filterStatus === "all" ? undefined : filterStatus
  );
  const { data: dirigentesData } = useDirigentes({ per_page: 50 });
  const generateMutation = useGeneratePlan();
  const approveMutation = useApprovePlan();
  const rejectMutation = useRejectPlan();

  const plans = data?.items ?? [];
  const dirigentesForSelect = dirigentesData?.items ?? [];
  const filteredPlans =
    filterStatus === "all"
      ? plans
      : plans.filter((p) => p.status === filterStatus);

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
        {(["all", "draft", "approved", "executed", "rejected"] as const).map(
          (status) => (
            <Button
              key={status}
              variant={filterStatus === status ? "default" : "outline"}
              size="sm"
              onClick={() => setFilterStatus(status)}
            >
              {status === "all" ? "Todos" : STATUS_CONFIG[status].label}
            </Button>
          )
        )}
      </div>

      {/* Plans list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
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
            const statusCfg = STATUS_CONFIG[plan.status];
            const StatusIcon = statusCfg.icon;
            return (
              <Card
                key={plan.id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => setSelectedPlan(plan)}
              >
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10">
                    <FileText className="h-5 w-5 text-accent" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{plan.titulo}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {plan.dirigente_nombre}
                      </span>
                      <Badge variant="secondary" className="text-[10px]">
                        {plan.tipo}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(plan.created_at)}
                      </span>
                    </div>
                  </div>
                  <Badge variant={statusCfg.variant} className="gap-1 shrink-0">
                    <StatusIcon className="h-3 w-3" />
                    {statusCfg.label}
                  </Badge>
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
        <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
          {selectedPlan && (
            <>
              <DialogHeader>
                <DialogTitle>{selectedPlan.titulo}</DialogTitle>
                <DialogDescription>
                  {selectedPlan.dirigente_nombre} &mdash;{" "}
                  {formatDate(selectedPlan.created_at)}
                </DialogDescription>
              </DialogHeader>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{selectedPlan.contenido}</ReactMarkdown>
              </div>
              {selectedPlan.status === "draft" && (
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
          )}
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
                      {d.nombre} {d.apellido_paterno}
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
