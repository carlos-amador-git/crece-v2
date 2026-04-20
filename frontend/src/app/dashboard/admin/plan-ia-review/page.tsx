"use client";

import {
  AlertTriangle,
  Brain,
  Filter,
  Inbox,
  Loader2,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/lib/auth";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import {
  useRecomendaciones,
  useTransicionarEstado,
  type Recomendacion,
  type TipoRecomendacion,
} from "@/lib/api/hooks/use-recomendaciones";
import { RecomendacionCard } from "@/components/plan-ia/recomendacion-card";
import { RechazoDialog } from "@/components/plan-ia/rechazo-dialog";
import {
  ModificarDialog,
  type ModificarPayload,
} from "@/components/plan-ia/modificar-dialog";

function useIsAdmin() {
  try {
    const { user } = useAuth();
    return user?.role === "admin";
  } catch {
    return false;
  }
}

export default function PlanIAReviewPage() {
  const isAdmin = useIsAdmin();
  const [filterDirigente, setFilterDirigente] = useState<string>("all");
  const [filterTipo, setFilterTipo] = useState<string>("all");

  const { data: dirigentesData } = useDirigentes({ per_page: 100 });
  const dirigentes = dirigentesData?.items ?? [];

  const {
    data: colaPropuesta,
    isLoading,
    isError,
    error,
    refetch,
  } = useRecomendaciones({ estado: "propuesta" });

  // Aprobadas recientes (para feedback "ya aprobaste X")
  const { data: aprobadasRecientes } = useRecomendaciones({
    estado: ["aprobada", "modificada"],
  });

  const transicion = useTransicionarEstado();

  const [rechazoTarget, setRechazoTarget] = useState<Recomendacion | null>(null);
  const [modificarTarget, setModificarTarget] = useState<Recomendacion | null>(null);

  const filtered = useMemo(() => {
    if (!colaPropuesta) return [];
    return colaPropuesta.filter((r) => {
      if (filterDirigente !== "all" && String(r.dirigente_id) !== filterDirigente)
        return false;
      if (filterTipo !== "all" && r.tipo !== filterTipo) return false;
      return true;
    });
  }, [colaPropuesta, filterDirigente, filterTipo]);

  // Agrupar por dirigente
  const grouped = useMemo(() => {
    const map = new Map<number, { dirigente_id: number; nombre: string; items: Recomendacion[] }>();
    for (const r of filtered) {
      const nombre =
        r.dirigente_nombre ??
        dirigentes.find((d) => d.id === r.dirigente_id)?.full_name ??
        `Dirigente #${r.dirigente_id}`;
      const entry = map.get(r.dirigente_id) ?? {
        dirigente_id: r.dirigente_id,
        nombre,
        items: [],
      };
      entry.items.push(r);
      map.set(r.dirigente_id, entry);
    }
    return Array.from(map.values()).sort((a, b) => a.nombre.localeCompare(b.nombre));
  }, [filtered, dirigentes]);

  const handleAprobar = (r: Recomendacion) => {
    transicion.mutate({
      id: r.id,
      payload: { estado: "aprobada" },
    });
  };

  const handleConfirmRechazo = (motivo: string) => {
    if (!rechazoTarget) return;
    transicion.mutate(
      {
        id: rechazoTarget.id,
        payload: { estado: "rechazada", motivo },
      },
      { onSuccess: () => setRechazoTarget(null) },
    );
  };

  const handleConfirmModificar = (patch: ModificarPayload) => {
    if (!modificarTarget) return;
    transicion.mutate(
      {
        id: modificarTarget.id,
        payload: {
          estado: "modificada",
          ...patch,
        },
      },
      { onSuccess: () => setModificarTarget(null) },
    );
  };

  if (!isAdmin) {
    return (
      <div className="p-6">
        <Card className="border-rose-500/30" data-testid="admin-guard-denied">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-rose-600">
              <ShieldCheck className="h-5 w-5" />
              Acceso restringido
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Esta pantalla es exclusiva del equipo MD Consultoría. Contacta a administración
            si necesitas acceso.
          </CardContent>
        </Card>
      </div>
    );
  }

  const total = colaPropuesta?.length ?? 0;
  const aprobadasCount = aprobadasRecientes?.length ?? 0;

  return (
    <div className="space-y-6 p-6" data-testid="page-plan-ia-review">
      {/* Header */}
      <header className="flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Admin MD</span>
            <span aria-hidden>/</span>
            <span>Plan IA Review</span>
          </div>
          <h1 className="flex items-center gap-2 font-heading text-2xl font-bold tracking-tight sm:text-3xl">
            <Brain className="h-6 w-6 text-accent" />
            Plan IA · Cola MD Review (HITL §3.6)
          </h1>
          <p className="text-sm text-muted-foreground">
            Recomendaciones generadas por Gemma 3:12b pendientes de aprobación humana antes
            de pasar al cliente.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="gap-1">
            <Inbox className="h-3 w-3" />
            {total} en cola
          </Badge>
          <Badge variant="outline" className="gap-1 border-emerald-500/40 text-emerald-700 dark:text-emerald-300">
            <ShieldCheck className="h-3 w-3" />
            {aprobadasCount} aprobadas visibles
          </Badge>
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCcw className={`mr-1 h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
            Refrescar
          </Button>
        </div>
      </header>

      {/* Filtros */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Filter className="h-4 w-4" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Dirigente</label>
            <Select value={filterDirigente} onValueChange={setFilterDirigente}>
              <SelectTrigger data-testid="filter-dirigente">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {dirigentes.map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>
                    {d.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Tipo</label>
            <Select
              value={filterTipo}
              onValueChange={(v) => setFilterTipo(v as TipoRecomendacion | "all")}
            >
              <SelectTrigger data-testid="filter-tipo">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="start">Start</SelectItem>
                <SelectItem value="stop">Stop</SelectItem>
                <SelectItem value="continue">Continue</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Estado carga / error / vacío */}
      {isLoading && (
        <div
          className="flex items-center justify-center gap-2 rounded-md border bg-muted/20 p-6 text-sm text-muted-foreground"
          data-testid="loading-state"
        >
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando cola de recomendaciones…
        </div>
      )}

      {isError && (
        <div
          className="flex items-start gap-3 rounded-md border border-destructive/50 bg-destructive/5 p-4 text-destructive"
          role="alert"
          data-testid="error-state"
        >
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <div className="space-y-1">
            <p className="text-sm font-medium">No se pudo cargar la cola</p>
            <p className="text-xs">{(error as Error)?.message ?? "Error desconocido"}</p>
          </div>
        </div>
      )}

      {!isLoading && !isError && grouped.length === 0 && (
        <Card data-testid="empty-state">
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <Inbox className="h-10 w-10 text-muted-foreground/50" />
            <p className="font-medium">Cola vacía</p>
            <p className="text-sm text-muted-foreground">
              No hay recomendaciones pendientes de MD review en este momento.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Cola agrupada por dirigente */}
      {grouped.map((group) => (
        <section key={group.dirigente_id} className="space-y-3">
          <div className="flex items-baseline justify-between">
            <h2 className="font-heading text-lg font-semibold tracking-tight">
              {group.nombre}
            </h2>
            <Badge variant="outline" className="text-xs">
              {group.items.length} recomendación{group.items.length === 1 ? "" : "es"}
            </Badge>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            {group.items.map((r) => (
              <RecomendacionCard
                key={r.id}
                recomendacion={r}
                mode="admin"
                dirigenteNombre={group.nombre}
                onAprobar={handleAprobar}
                onRechazar={(x) => setRechazoTarget(x)}
                onModificar={(x) => setModificarTarget(x)}
              />
            ))}
          </div>
        </section>
      ))}

      <RechazoDialog
        recomendacion={rechazoTarget}
        onClose={() => setRechazoTarget(null)}
        onConfirm={handleConfirmRechazo}
        isLoading={transicion.isPending}
      />
      <ModificarDialog
        mode="admin"
        recomendacion={modificarTarget}
        onClose={() => setModificarTarget(null)}
        onConfirm={handleConfirmModificar}
        isLoading={transicion.isPending}
      />
    </div>
  );
}
