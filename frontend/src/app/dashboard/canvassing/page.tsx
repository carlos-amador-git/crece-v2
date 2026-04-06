"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { ProgressBar } from "@/components/dashboard/progress-bar";
import {
  useRoutes, useRouteDetail, useOptimizeRoute,
  type RutaCanvassingResponse, type PuntoRutaResponse, type ResultadoVisita,
} from "@/lib/api/hooks/use-canvassing";
import { formatDate } from "@/lib/utils";
import { MapPin, Plus, Loader2, Route, CheckCircle2, XCircle, Clock, HelpCircle } from "lucide-react";

function puntoIcon(punto: PuntoRutaResponse) {
  if (!punto.visitado) {
    return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
  const resultMap: Record<string, React.ReactNode> = {
    encuesta_completada: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
    no_en_casa: <HelpCircle className="h-4 w-4 text-amber-500" />,
    rechazo: <XCircle className="h-4 w-4 text-red-500" />,
    reagendado: <Clock className="h-4 w-4 text-blue-500" />,
    direccion_incorrecta: <HelpCircle className="h-4 w-4 text-amber-500" />,
  };
  return punto.resultado ? (resultMap[punto.resultado] ?? <CheckCircle2 className="h-4 w-4 text-emerald-500" />) : <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
}

function resultadoLabel(resultado: ResultadoVisita | null): string {
  if (!resultado) return "pendiente";
  const labels: Record<ResultadoVisita, string> = {
    encuesta_completada: "completado",
    no_en_casa: "no en casa",
    rechazo: "rechazado",
    reagendado: "reagendado",
    direccion_incorrecta: "dir. incorrecta",
  };
  return labels[resultado] ?? resultado;
}

function RouteCard({ route, onSelect, isSelected }: { route: RutaCanvassingResponse; onSelect: (id: number) => void; isSelected: boolean }) {
  return (
    <Card
      className={`card-elevated cursor-pointer transition-all ${isSelected ? "ring-2 ring-accent" : ""}`}
      onClick={() => onSelect(route.id)} role="button" tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(route.id); } }}
      aria-pressed={isSelected}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="font-heading text-base font-semibold">{route.nombre}</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              {route.seccion_id ? `Seccion ${route.seccion_id}` : "Sin seccion"} -- Encuestador #{route.encuestador_id} -- {formatDate(route.fecha_asignada)}
            </p>
          </div>
          <Route className="h-5 w-5 shrink-0 text-muted-foreground" />
        </div>
        <div className="mt-3"><ProgressBar completed={route.puntos_completados} total={route.puntos_total} /></div>
      </CardContent>
    </Card>
  );
}

export default function CanvassingPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [form, setForm] = useState({ seccion_id: "", encuestador_id: "", fecha: "", max_puntos: "20" });

  const { data: routes, isLoading } = useRoutes();
  const { data: routeDetail } = useRouteDetail(selectedId ?? undefined);
  const optimizeRoute = useOptimizeRoute();

  const handleOptimize = async () => {
    if (!form.seccion_id || !form.encuestador_id || !form.fecha) return;
    await optimizeRoute.mutateAsync({
      seccion_id: Number(form.seccion_id),
      encuestador_id: Number(form.encuestador_id),
      fecha: form.fecha,
      max_puntos: Number(form.max_puntos),
    });
    setDialogOpen(false);
    setForm({ seccion_id: "", encuestador_id: "", fecha: "", max_puntos: "20" });
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Smart Canvassing</h1>
          <p className="text-sm text-muted-foreground">Rutas optimizadas para trabajo de campo</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild><Button className="gap-2"><Plus className="h-4 w-4" />Optimize Route</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Optimizar Ruta</DialogTitle>
              <DialogDescription>Genera una ruta optimizada para trabajo de campo.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2"><label htmlFor="cv-seccion" className="text-sm font-medium">Seccion Electoral</label><Input id="cv-seccion" placeholder="ID de seccion" value={form.seccion_id} onChange={(e) => setForm((f) => ({ ...f, seccion_id: e.target.value }))} /></div>
              <div className="grid gap-2"><label htmlFor="cv-enc" className="text-sm font-medium">Encuestador ID</label><Input id="cv-enc" type="number" placeholder="ID del encuestador" value={form.encuestador_id} onChange={(e) => setForm((f) => ({ ...f, encuestador_id: e.target.value }))} /></div>
              <div className="grid gap-2"><label htmlFor="cv-fecha" className="text-sm font-medium">Fecha</label><Input id="cv-fecha" type="date" value={form.fecha} onChange={(e) => setForm((f) => ({ ...f, fecha: e.target.value }))} /></div>
              <div className="grid gap-2"><label htmlFor="cv-max" className="text-sm font-medium">Max Puntos</label><Input id="cv-max" type="number" min="1" max="100" value={form.max_puntos} onChange={(e) => setForm((f) => ({ ...f, max_puntos: e.target.value }))} /></div>
            </div>
            <DialogFooter>
              <Button onClick={handleOptimize} disabled={optimizeRoute.isPending} className="gap-2">
                {optimizeRoute.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Route className="h-4 w-4" />}
                Optimizar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </header>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="space-y-3 lg:col-span-2" aria-label="Lista de rutas">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => <Card key={i} className="card-elevated"><CardContent className="p-5"><Skeleton className="mb-2 h-5 w-40" /><Skeleton className="h-2 w-full" /></CardContent></Card>)
          ) : !routes || routes.length === 0 ? (
            <Card><CardContent className="flex flex-col items-center justify-center py-12 text-center"><MapPin className="mb-3 h-10 w-10 text-muted-foreground/50" /><p className="text-sm text-muted-foreground">No hay rutas. Optimiza la primera.</p></CardContent></Card>
          ) : routes.map((r) => <RouteCard key={r.id} route={r} onSelect={setSelectedId} isSelected={selectedId === r.id} />)}
        </section>

        <div className="space-y-6 lg:col-span-3">
          <Card>
            <CardHeader><CardTitle>Mapa de Ruta</CardTitle><CardDescription>{selectedId ? `Ruta #${selectedId}` : "Selecciona una ruta"}</CardDescription></CardHeader>
            <CardContent>
              <div className="flex h-[180px] items-center justify-center rounded-lg border-2 border-dashed border-muted bg-muted/30">
                <div className="text-center"><MapPin className="mx-auto mb-2 h-6 w-6 text-muted-foreground/40" /><p className="text-xs text-muted-foreground">Mapa disponible proximamente</p></div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Puntos de Visita</CardTitle><CardDescription>{routeDetail ? `${routeDetail.puntos.length} puntos` : "Selecciona una ruta"}</CardDescription></CardHeader>
            <CardContent>
              {!selectedId ? (
                <div className="flex h-20 items-center justify-center text-sm text-muted-foreground">Selecciona una ruta para ver los puntos</div>
              ) : !routeDetail ? (
                <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
              ) : routeDetail.puntos.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">Sin puntos en esta ruta</div>
              ) : (
                <ul className="space-y-2">
                  {routeDetail.puntos.map((p) => (
                    <li key={p.id} className="flex items-center gap-3 rounded-md border p-2.5">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold tabular-nums text-muted-foreground">{p.orden}</span>
                      {puntoIcon(p)}
                      <span className="min-w-0 flex-1 truncate text-sm">{p.ciudadano_nombre ?? `Ciudadano #${p.ciudadano_id}`}</span>
                      <Badge variant="outline" className="shrink-0 text-xs">{p.visitado ? resultadoLabel(p.resultado) : "pendiente"}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
