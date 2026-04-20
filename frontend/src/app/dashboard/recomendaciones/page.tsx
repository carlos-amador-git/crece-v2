"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Inbox,
  Loader2,
  RefreshCcw,
  Sparkles,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/lib/auth";
import {
  useRecomendaciones,
  useTransicionarEstado,
  useVincularPostEjecutor,
  type Recomendacion,
} from "@/lib/api/hooks/use-recomendaciones";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { RecomendacionCard } from "@/components/plan-ia/recomendacion-card";
import { RechazoDialog } from "@/components/plan-ia/rechazo-dialog";
import {
  ModificarDialog,
  type ModificarPayload,
} from "@/components/plan-ia/modificar-dialog";
import { PostEjecutorDialog } from "@/components/plan-ia/post-ejecutor-dialog";
import { SeguimientoCard } from "@/components/plan-ia/seguimiento-card";

function useCurrentDirigenteId(): number | null {
  try {
    const { user } = useAuth();
    const u = user as { dirigente_id?: number | null } | null;
    return u?.dirigente_id ?? null;
  } catch {
    return null;
  }
}

export default function RecomendacionesClientePage() {
  const dirigenteId = useCurrentDirigenteId();
  const { data: dirigentesData } = useDirigentes({ per_page: 50 });
  const dirigenteNombre =
    dirigentesData?.items.find((d) => d.id === dirigenteId)?.full_name;

  // Recomendaciones visibles para el cliente
  const {
    data: aprobadas,
    isLoading,
    isError,
    error,
    refetch,
  } = useRecomendaciones({
    estado: ["aprobada", "modificada"],
    dirigente_id: dirigenteId ?? undefined,
  });

  const { data: enSeguimiento } = useRecomendaciones({
    estado: "ejecutada",
    dirigente_id: dirigenteId ?? undefined,
  });

  const { data: historicas } = useRecomendaciones({
    estado: ["completada", "fallida", "rechazada"],
    dirigente_id: dirigenteId ?? undefined,
  });

  const transicion = useTransicionarEstado();
  const vincular = useVincularPostEjecutor();

  const [rechazoTarget, setRechazoTarget] = useState<Recomendacion | null>(null);
  const [modificarTarget, setModificarTarget] = useState<Recomendacion | null>(null);
  const [aceptarTarget, setAceptarTarget] = useState<Recomendacion | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  const aprobadasList = useMemo(() => aprobadas ?? [], [aprobadas]);
  const seguimientoList = useMemo(() => enSeguimiento ?? [], [enSeguimiento]);
  const historicasList = useMemo(() => historicas ?? [], [historicas]);

  const handleAceptar = (r: Recomendacion) => {
    // Abre el dialog T7 — el paso a 'ejecutada' lo hace el endpoint de vinculación
    setAceptarTarget(r);
  };

  const handleConfirmPostEjecutor = (post: { id: number }) => {
    if (!aceptarTarget) return;
    vincular.mutate(
      { id: aceptarTarget.id, postId: post.id },
      {
        onSuccess: () => {
          setSuccessBanner(
            `Vinculado al post #${post.id}. Seguimiento activo por ${aceptarTarget.ventana_duracion_dias} días.`,
          );
          setAceptarTarget(null);
        },
      },
    );
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

  return (
    <div className="space-y-6 p-6" data-testid="page-recomendaciones-cliente">
      <header className="flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Dashboard</span>
            <span aria-hidden>/</span>
            <span>Recomendaciones</span>
          </div>
          <h1 className="flex items-center gap-2 font-heading text-2xl font-bold tracking-tight sm:text-3xl">
            <Sparkles className="h-6 w-6 text-accent" />
            Recomendaciones Plan IA
          </h1>
          <p className="text-sm text-muted-foreground">
            Acciones curadas por MD para{" "}
            {dirigenteNombre ?? "tu perfil"}. Decide qué aceptar, rechazar o ajustar.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="gap-1">
            <Inbox className="h-3 w-3" />
            {aprobadasList.length} pendientes
          </Badge>
          <Badge
            variant="outline"
            className="gap-1 border-sky-500/40 text-sky-700 dark:text-sky-300"
          >
            {seguimientoList.length} en seguimiento
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

      {successBanner && (
        <div
          className="flex items-start gap-3 rounded-md border border-emerald-500/40 bg-emerald-500/5 p-3 text-sm text-emerald-800 dark:text-emerald-300"
          data-testid="success-banner"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{successBanner}</span>
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
            <p className="text-sm font-medium">No se pudieron cargar tus recomendaciones</p>
            <p className="text-xs">{(error as Error)?.message ?? "Error desconocido"}</p>
          </div>
        </div>
      )}

      <Tabs defaultValue="pendientes" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pendientes" data-testid="tab-pendientes">
            Pendientes ({aprobadasList.length})
          </TabsTrigger>
          <TabsTrigger value="seguimiento" data-testid="tab-seguimiento">
            En seguimiento ({seguimientoList.length})
          </TabsTrigger>
          <TabsTrigger value="historico" data-testid="tab-historico">
            Histórico ({historicasList.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pendientes" className="space-y-3">
          {isLoading && (
            <div
              className="flex items-center justify-center gap-2 rounded-md border bg-muted/20 p-6 text-sm text-muted-foreground"
              data-testid="loading-state"
            >
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando recomendaciones…
            </div>
          )}
          {!isLoading && aprobadasList.length === 0 && (
            <Card data-testid="empty-pendientes">
              <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
                <Sparkles className="h-10 w-10 text-muted-foreground/50" />
                <p className="font-medium">Sin recomendaciones por ahora</p>
                <p className="text-sm text-muted-foreground">
                  Tu equipo MD está preparando la siguiente tanda de acciones. Te
                  avisaremos.
                </p>
              </CardContent>
            </Card>
          )}
          <div className="grid gap-3 lg:grid-cols-2">
            {aprobadasList.map((r) => (
              <RecomendacionCard
                key={r.id}
                recomendacion={r}
                mode="cliente"
                dirigenteNombre={dirigenteNombre}
                onAceptar={handleAceptar}
                onRechazar={(x) => setRechazoTarget(x)}
                onModificar={(x) => setModificarTarget(x)}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="seguimiento" className="space-y-3">
          {seguimientoList.length === 0 ? (
            <Card data-testid="empty-seguimiento">
              <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
                <Inbox className="h-10 w-10 text-muted-foreground/50" />
                <p className="font-medium">Nada en seguimiento</p>
                <p className="text-sm text-muted-foreground">
                  Cuando aceptes una recomendación y la vincules a un post, verás aquí su
                  progreso de 14 días.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {seguimientoList.map((r) => (
                <SeguimientoCard key={r.id} recomendacion={r} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="historico" className="space-y-3">
          {historicasList.length === 0 ? (
            <Card data-testid="empty-historico">
              <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
                <Inbox className="h-10 w-10 text-muted-foreground/50" />
                <p className="font-medium">Sin histórico aún</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {historicasList.map((r) => (
                <RecomendacionCard
                  key={r.id}
                  recomendacion={r}
                  mode="cliente"
                  dirigenteNombre={dirigenteNombre}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <PostEjecutorDialog
        recomendacion={aceptarTarget}
        onClose={() => setAceptarTarget(null)}
        onConfirm={handleConfirmPostEjecutor}
        isLoading={vincular.isPending}
      />
      <RechazoDialog
        recomendacion={rechazoTarget}
        onClose={() => setRechazoTarget(null)}
        onConfirm={handleConfirmRechazo}
        isLoading={transicion.isPending}
      />
      <ModificarDialog
        mode="cliente"
        recomendacion={modificarTarget}
        onClose={() => setModificarTarget(null)}
        onConfirm={handleConfirmModificar}
        isLoading={transicion.isPending}
      />
    </div>
  );
}
