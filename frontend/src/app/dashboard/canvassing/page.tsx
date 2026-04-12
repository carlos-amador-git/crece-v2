"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProgressBar } from "@/components/dashboard/progress-bar";
import {
  useRoutes,
  useRouteDetail,
  useOptimizeRoute,
  useCanvassingGeo,
  useCanvassingGeoStats,
  type RutaCanvassingResponse,
  type PuntoRutaResponse,
  type ResultadoVisita,
  type CanvassingGeoFilters,
} from "@/lib/api/hooks/use-canvassing";
import { formatDate } from "@/lib/utils";
import {
  MapPin,
  Plus,
  Loader2,
  Route,
  CheckCircle2,
  XCircle,
  Clock,
  HelpCircle,
  Map,
  Users,
  Filter,
} from "lucide-react";

// Dynamic import to avoid SSR issues with MapLibre
const CanvassingGeoMap = dynamic(
  () =>
    import("@/components/maps/canvassing-geo-map").then(
      (m) => m.CanvassingGeoMap
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    ),
  }
);

// ── Helpers ────────────────────────────────────────────────

function puntoIcon(punto: PuntoRutaResponse) {
  if (!punto.visitado) {
    return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
  const resultMap: Record<string, React.ReactNode> = {
    encuesta_completada: (
      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
    ),
    no_en_casa: <HelpCircle className="h-4 w-4 text-amber-500" />,
    rechazo: <XCircle className="h-4 w-4 text-red-500" />,
    reagendado: <Clock className="h-4 w-4 text-blue-500" />,
    direccion_incorrecta: <HelpCircle className="h-4 w-4 text-amber-500" />,
  };
  return punto.resultado
    ? (resultMap[punto.resultado] ?? (
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      ))
    : <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
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

// ── Sub-components ─────────────────────────────────────────

function RouteCard({
  route,
  onSelect,
  isSelected,
}: {
  route: RutaCanvassingResponse;
  onSelect: (id: number) => void;
  isSelected: boolean;
}) {
  return (
    <Card
      className={`card-elevated cursor-pointer transition-all ${
        isSelected ? "ring-2 ring-accent" : ""
      }`}
      onClick={() => onSelect(route.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(route.id);
        }
      }}
      aria-pressed={isSelected}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold">{route.nombre}</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Secc. {route.seccion_id ?? "—"} · Enc. #{route.encuestador_id} ·{" "}
              {formatDate(route.fecha_asignada)}
            </p>
          </div>
          <Route className="h-4 w-4 shrink-0 text-muted-foreground" />
        </div>
        <div className="mt-2">
          <ProgressBar
            completed={route.puntos_completados}
            total={route.puntos_total}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
}) {
  return (
    <div className="stat-card-transition card-elevated flex items-center gap-3 rounded-lg bg-card p-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
        {icon}
      </div>
      <div>
        <p className="text-lg font-bold tabular-nums" data-numeric="true">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────

export default function CanvassingPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [form, setForm] = useState({
    seccion_id: "",
    encuestador_id: "",
    fecha: "",
    max_puntos: "20",
  });
  const [colorMode, setColorMode] = useState<"estrato" | "participacion">(
    "estrato"
  );
  const [filters, setFilters] = useState<CanvassingGeoFilters>({
    limit: 5000,
  });

  const { data: routes, isLoading: routesLoading } = useRoutes();
  const { data: routeDetail } = useRouteDetail(selectedId ?? undefined);
  const optimizeRoute = useOptimizeRoute();
  const { data: geoData, isLoading: geoLoading } = useCanvassingGeo(filters);
  const { data: stats } = useCanvassingGeoStats();

  const handleOptimize = async () => {
    if (!form.seccion_id || !form.encuestador_id || !form.fecha) return;
    await optimizeRoute.mutateAsync({
      seccion_id: Number(form.seccion_id),
      encuestador_id: Number(form.encuestador_id),
      fecha: form.fecha,
      max_puntos: Number(form.max_puntos),
    });
    setDialogOpen(false);
    setForm({
      seccion_id: "",
      encuestador_id: "",
      fecha: "",
      max_puntos: "20",
    });
  };

  const updateFilter = (key: keyof CanvassingGeoFilters, value: string) => {
    setFilters((prev) => {
      const next = { ...prev, limit: 5000 };
      if (value === "" || value === "all") {
        delete next[key];
      } else if (
        key === "alcaldia_id" ||
        key === "nivel_participacion" ||
        key === "limit"
      ) {
        (next as Record<string, unknown>)[key] = Number(value);
      } else if (key === "volatilidad_min" || key === "volatilidad_max") {
        (next as Record<string, unknown>)[key] = Number(value);
      } else {
        (next as Record<string, unknown>)[key] = value;
      }
      return next;
    });
  };

  const featureCount = geoData?.features?.length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Smart Canvassing</h1>
          <p className="text-sm text-muted-foreground">
            Mapa de campo — quién visitar y dónde
          </p>
        </div>
        <div className="flex gap-2">
          <Select
            value={colorMode}
            onValueChange={(v) =>
              setColorMode(v as "estrato" | "participacion")
            }
          >
            <SelectTrigger className="w-[180px]" aria-label="Modo de color del mapa">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="estrato">Por Estrato</SelectItem>
              <SelectItem value="participacion">Por Participación</SelectItem>
            </SelectContent>
          </Select>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Optimizar Ruta
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Optimizar Ruta</DialogTitle>
                <DialogDescription>
                  Genera una ruta optimizada para trabajo de campo.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <label htmlFor="cv-seccion" className="text-sm font-medium">
                    Sección Electoral
                  </label>
                  <Input
                    id="cv-seccion"
                    placeholder="ID de sección"
                    value={form.seccion_id}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, seccion_id: e.target.value }))
                    }
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="cv-enc" className="text-sm font-medium">
                    Encuestador ID
                  </label>
                  <Input
                    id="cv-enc"
                    type="number"
                    placeholder="ID del encuestador"
                    value={form.encuestador_id}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        encuestador_id: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="cv-fecha" className="text-sm font-medium">
                    Fecha
                  </label>
                  <Input
                    id="cv-fecha"
                    type="date"
                    value={form.fecha}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, fecha: e.target.value }))
                    }
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="cv-max" className="text-sm font-medium">
                    Max Puntos
                  </label>
                  <Input
                    id="cv-max"
                    type="number"
                    min="1"
                    max="100"
                    value={form.max_puntos}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, max_puntos: e.target.value }))
                    }
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={handleOptimize}
                  disabled={optimizeRoute.isPending}
                  className="gap-2"
                >
                  {optimizeRoute.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Route className="h-4 w-4" />
                  )}
                  Optimizar
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      {/* Stats bar */}
      {stats ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard
            label="Ciudadanos total"
            value={stats.total.toLocaleString()}
            icon={<Users className="h-4 w-4 text-muted-foreground" />}
          />
          <StatCard
            label="Con geolocalización"
            value={stats.con_geo.toLocaleString()}
            icon={<MapPin className="h-4 w-4 text-muted-foreground" />}
          />
          <StatCard
            label="En mapa (filtrado)"
            value={geoLoading ? "..." : featureCount.toLocaleString()}
            icon={<Map className="h-4 w-4 text-muted-foreground" />}
          />
          <StatCard
            label="Volatilidad promedio"
            value={stats.volatilidad_range?.avg ?? "—"}
            icon={<Filter className="h-4 w-4 text-muted-foreground" />}
          />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[72px]" />
          ))}
        </div>
      )}

      {/* Main content: filters + map */}
      <div className="grid gap-6 lg:grid-cols-6">
        {/* Filters sidebar */}
        <aside className="space-y-4 lg:col-span-1" aria-label="Filtros de mapa">
          <Card className="glass-card rounded-xl">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Filtros</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Alcaldía */}
              <div className="space-y-1.5">
                <label htmlFor="filter-alcaldia" className="text-xs font-medium text-muted-foreground">
                  Alcaldia
                </label>
                <Select
                  value={String(filters.alcaldia_id ?? "all")}
                  onValueChange={(v) => updateFilter("alcaldia_id", v)}
                >
                  <SelectTrigger id="filter-alcaldia" aria-label="Filtrar por alcaldia">
                    <SelectValue placeholder="Todas" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas</SelectItem>
                    {stats?.por_alcaldia.map((a) => (
                      <SelectItem
                        key={a.alcaldia_id}
                        value={String(a.alcaldia_id)}
                      >
                        {a.nombre} ({a.count.toLocaleString()})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Estrato */}
              <div className="space-y-1.5">
                <label htmlFor="filter-estrato" className="text-xs font-medium text-muted-foreground">
                  Estrato
                </label>
                <Select
                  value={filters.estrato ?? "all"}
                  onValueChange={(v) => updateFilter("estrato", v)}
                >
                  <SelectTrigger id="filter-estrato" aria-label="Filtrar por estrato">
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    {stats?.por_estrato.map((e) => (
                      <SelectItem key={e.estrato} value={e.estrato}>
                        {e.estrato} ({e.count.toLocaleString()})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Nivel participación */}
              <div className="space-y-1.5">
                <label htmlFor="filter-participacion" className="text-xs font-medium text-muted-foreground">
                  Participacion
                </label>
                <Select
                  value={
                    filters.nivel_participacion
                      ? String(filters.nivel_participacion)
                      : "all"
                  }
                  onValueChange={(v) =>
                    updateFilter("nivel_participacion", v)
                  }
                >
                  <SelectTrigger id="filter-participacion" aria-label="Filtrar por nivel de participacion">
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="3">Alto (3)</SelectItem>
                    <SelectItem value="2">Medio (2)</SelectItem>
                    <SelectItem value="1">Bajo (1)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Contactado */}
              <div className="space-y-1.5">
                <label htmlFor="filter-contactado" className="text-xs font-medium text-muted-foreground">
                  Contactado
                </label>
                <Select
                  value={filters.contactado ?? "all"}
                  onValueChange={(v) => updateFilter("contactado", v)}
                >
                  <SelectTrigger id="filter-contactado" aria-label="Filtrar por estado de contacto">
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="SI">Sí</SelectItem>
                    <SelectItem value="NO">No</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Volatilidad min */}
              <div className="space-y-1.5">
                <label htmlFor="filter-volatilidad" className="text-xs font-medium text-muted-foreground">
                  Volatilidad min.
                </label>
                <Input
                  id="filter-volatilidad"
                  type="number"
                  min={0}
                  max={100}
                  step={5}
                  placeholder="0"
                  aria-label="Volatilidad minima"
                  value={filters.volatilidad_min ?? ""}
                  onChange={(e) =>
                    updateFilter("volatilidad_min", e.target.value)
                  }
                />
              </div>

              {/* Reset */}
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => setFilters({ limit: 5000 })}
              >
                Limpiar filtros
              </Button>
            </CardContent>
          </Card>
        </aside>

        {/* Map */}
        <section className="lg:col-span-5" aria-label="Mapa de canvassing">
          <Card className="card-elevated overflow-hidden">
            <CardContent className="p-0">
              <div className="h-[500px] lg:h-[600px]">
                {geoLoading ? (
                  <div className="flex h-full items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  <CanvassingGeoMap
                    data={geoData ?? null}
                    colorMode={colorMode}
                    className="h-full"
                  />
                )}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>

      {/* Routes + Points tabs (existing functionality) */}
      <Tabs defaultValue="routes">
        <TabsList>
          <TabsTrigger value="routes" className="gap-2">
            <Route className="h-4 w-4" />
            Rutas ({routes?.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="points" className="gap-2">
            <MapPin className="h-4 w-4" />
            Puntos de visita
          </TabsTrigger>
        </TabsList>

        <TabsContent value="routes" className="mt-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {routesLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <Card key={i} className="card-elevated">
                  <CardContent className="p-4">
                    <Skeleton className="mb-2 h-5 w-40" />
                    <Skeleton className="h-2 w-full" />
                  </CardContent>
                </Card>
              ))
            ) : !routes || routes.length === 0 ? (
              <Card className="sm:col-span-2 lg:col-span-3">
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                  <MapPin className="mb-3 h-10 w-10 text-muted-foreground/50" />
                  <p className="text-sm text-muted-foreground">
                    No hay rutas. Usa &quot;Optimizar Ruta&quot; para crear la
                    primera.
                  </p>
                </CardContent>
              </Card>
            ) : (
              routes.map((r) => (
                <RouteCard
                  key={r.id}
                  route={r}
                  onSelect={setSelectedId}
                  isSelected={selectedId === r.id}
                />
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="points" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Puntos de Visita</CardTitle>
              <CardDescription>
                {routeDetail
                  ? `${routeDetail.puntos.length} puntos — Ruta #${selectedId}`
                  : "Selecciona una ruta para ver los puntos"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!selectedId ? (
                <div className="flex h-20 items-center justify-center text-sm text-muted-foreground">
                  Selecciona una ruta para ver los puntos
                </div>
              ) : !routeDetail ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-8 w-full" />
                  ))}
                </div>
              ) : routeDetail.puntos.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
                  Sin puntos en esta ruta
                </div>
              ) : (
                <ul className="space-y-2">
                  {routeDetail.puntos.map((p) => (
                    <li
                      key={p.id}
                      className="flex items-center gap-3 rounded-md border p-2.5"
                    >
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold tabular-nums text-muted-foreground">
                        {p.orden}
                      </span>
                      {puntoIcon(p)}
                      <span className="min-w-0 flex-1 truncate text-sm">
                        {p.ciudadano_nombre ?? `Ciudadano #${p.ciudadano_id}`}
                      </span>
                      <Badge variant="outline" className="shrink-0 text-xs">
                        {p.visitado
                          ? resultadoLabel(p.resultado)
                          : "pendiente"}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
