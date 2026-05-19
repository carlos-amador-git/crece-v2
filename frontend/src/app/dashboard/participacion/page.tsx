"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FilterSelect } from "@/components/dashboard/filter-select";
import {
  useSolicitudes,
  useParticipacionDashboard,
} from "@/lib/api/hooks/use-participacion";
import type {
  SolicitudTipo,
  SolicitudEstado,
  SolicitudPrioridad,
  SolicitudFilters,
  Solicitud,
} from "@/lib/api/hooks/use-participacion";
import {
  Inbox,
  Clock,
  MapPin,
  AlertTriangle,
  MessageSquare,
  FileText,
  Megaphone,
  ThumbsUp,
  ShieldAlert,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatCard, StatCardSkeleton } from "@/components/dashboard/stat-card";
import { FadeUp } from "@/components/motion/fade-up";

// ── Config maps ───────────────────────────────────────────────────

const TIPO_CONFIG: Record<SolicitudTipo, { label: string; icon: React.ComponentType<{ className?: string }>; color: string }> = {
  queja: { label: "Queja", icon: AlertTriangle, color: "bg-red-500/10 text-red-600 dark:text-red-400" },
  peticion: { label: "Peticion", icon: MessageSquare, color: "bg-blue-500/10 text-blue-600 dark:text-blue-400" },
  propuesta: { label: "Propuesta", icon: Megaphone, color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" },
  denuncia: { label: "Denuncia", icon: ShieldAlert, color: "bg-amber-500/10 text-amber-600 dark:text-amber-400" },
  informacion: { label: "Informacion", icon: HelpCircle, color: "bg-purple-500/10 text-purple-600 dark:text-purple-400" },
};

const ESTADO_CONFIG: Record<SolicitudEstado, { label: string; variant: "default" | "warning" | "success" | "danger" }> = {
  nueva: { label: "Nueva", variant: "default" },
  en_proceso: { label: "En proceso", variant: "warning" },
  resuelta: { label: "Resuelta", variant: "success" },
  cerrada: { label: "Cerrada", variant: "default" },
  rechazada: { label: "Rechazada", variant: "danger" },
};

const PRIORIDAD_CONFIG: Record<SolicitudPrioridad, { label: string; color: string }> = {
  alta: { label: "Alta", color: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800" },
  media: { label: "Media", color: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800" },
  baja: { label: "Baja", color: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800" },
};

const TIPO_OPTIONS = Object.entries(TIPO_CONFIG).map(([value, cfg]) => ({
  value,
  label: cfg.label,
}));

const ESTADO_OPTIONS = Object.entries(ESTADO_CONFIG).map(([value, cfg]) => ({
  value,
  label: cfg.label,
}));

const PRIORIDAD_OPTIONS = Object.entries(PRIORIDAD_CONFIG).map(([value, cfg]) => ({
  value,
  label: cfg.label,
}));

// ── Helpers ───────────────────────────────────────────────────────

function formatDateShort(iso: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(iso));
}

function formatHours(hours: number): string {
  if (hours < 1) return "<1h";
  if (hours < 24) return `${Math.round(hours)}h`;
  const days = Math.round(hours / 24);
  return `${days}d`;
}

// ── Components ────────────────────────────────────────────────────

function SolicitudCard({ solicitud }: { solicitud: Solicitud }) {
  const tipo = TIPO_CONFIG[solicitud.tipo];
  const estado = ESTADO_CONFIG[solicitud.estado];
  const prioridad = PRIORIDAD_CONFIG[solicitud.prioridad];
  const TipoIcon = tipo.icon;

  return (
    <Card className="group transition-shadow duration-150 hover:shadow-md">
      <CardContent className="p-5">
        <div className="flex flex-col gap-3">
          {/* Top row: badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold ${tipo.color}`}
            >
              <TipoIcon className="h-3 w-3" />
              {tipo.label}
            </span>
            <Badge variant={estado.variant}>{estado.label}</Badge>
            <span
              className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold ${prioridad.color}`}
            >
              {prioridad.label}
            </span>
          </div>

          {/* Title + description */}
          <div>
            <h3 className="font-heading text-base font-semibold leading-snug">
              {solicitud.titulo}
            </h3>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground line-clamp-2">
              {solicitud.descripcion}
            </p>
          </div>

          {/* Metadata */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            {solicitud.ciudadano_nombre && (
              <span className="flex items-center gap-1">
                <FileText className="h-3 w-3" />
                {solicitud.ciudadano_nombre}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDateShort(solicitud.created_at)}
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium">
              {solicitud.canal}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SolicitudCardSkeleton() {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-16 rounded-md" />
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-4 w-12 rounded-md" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full" />
          </div>
          <div className="flex items-center gap-3">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function TipoBreakdown({ porTipo }: { porTipo: Record<SolicitudTipo, number> }) {
  const entries = Object.entries(porTipo) as [SolicitudTipo, number][];
  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  if (total === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <BarChart3 className="h-4 w-4 text-cta" />
          Desglose por tipo
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {entries.map(([tipo, count]) => {
          const cfg = TIPO_CONFIG[tipo];
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          const TIcon = cfg.icon;

          return (
            <div key={tipo} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1.5">
                  <TIcon className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="font-medium">{cfg.label}</span>
                </span>
                <span className="tabular-nums text-xs text-muted-foreground">
                  {count} ({pct}%)
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-cta transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

// ── Main page ─────────────────────────────────────────────────────

export default function ParticipacionPage() {
  const [filters, setFilters] = useState<SolicitudFilters>({
    page: 1,
    per_page: 20,
  });

  const {
    data: dashboardData,
    isLoading: dashboardLoading,
    isError: dashboardError,
  } = useParticipacionDashboard();

  const {
    data: solicitudesData,
    isLoading: solicitudesLoading,
    isError: solicitudesError,
  } = useSolicitudes(filters);

  const solicitudes = solicitudesData?.items ?? [];
  const totalPages = solicitudesData?.pages ?? 1;
  const currentPage = filters.page ?? 1;

  // Find top tipo from dashboard data
  const topTipo = dashboardData?.por_tipo
    ? (Object.entries(dashboardData.por_tipo) as [SolicitudTipo, number][])
        .sort(([, a], [, b]) => b - a)[0]
    : undefined;

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────── */}
      <header>
        <h1 className="font-heading text-2xl font-bold">
          Participacion Ciudadana
        </h1>
        <p className="text-sm text-muted-foreground">
          Solicitudes, quejas y propuestas ciudadanas
        </p>
      </header>

      {/* ── KPI Cards ──────────────────────────────────── */}
      <section
        className="grid gap-4 sm:grid-cols-2 md:grid-cols-4"
        aria-label="Estadisticas de participacion"
      >
        {dashboardLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : dashboardError ? (
          <Card className="col-span-full">
            <CardContent className="flex items-center gap-3 p-4 text-sm text-red-600 dark:text-red-400">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              Error al cargar estadisticas del dashboard
            </CardContent>
          </Card>
        ) : (
          <>
            <FadeUp index={0}>
              <StatCard
                label="Total Solicitudes"
                value={dashboardData?.total ?? 0}
                icon={Inbox}
              />
            </FadeUp>
            <FadeUp index={1}>
              <StatCard
                label="Tipo Mas Frecuente"
                value={topTipo ? TIPO_CONFIG[topTipo[0]].label : "--"}
                icon={MessageSquare}
                description={topTipo ? `${topTipo[1]} solicitudes` : undefined}
              />
            </FadeUp>
            <FadeUp index={2}>
              <StatCard
                label="Tiempo Promedio Resolucion"
                value={dashboardData?.avg_resolution_hours != null ? formatHours(dashboardData.avg_resolution_hours) : "--"}
                icon={Clock}
                description="promedio en horas"
              />
            </FadeUp>
            <FadeUp index={3}>
              <StatCard
                label="Por Estado"
                value={dashboardData?.por_estado?.nueva ?? 0}
                icon={ThumbsUp}
                description="solicitudes nuevas"
              />
            </FadeUp>
          </>
        )}
      </section>

      {/* ── Tipo Breakdown Chart ───────────────────────── */}
      {dashboardData?.por_tipo && !dashboardLoading && (
        <TipoBreakdown porTipo={dashboardData.por_tipo} />
      )}

      {/* ── Filters ────────────────────────────────────── */}
      <section className="flex flex-wrap items-center gap-3">
        <FilterSelect
          value={filters.tipo}
          onValueChange={(v) =>
            setFilters((f) => ({ ...f, tipo: v as SolicitudTipo | undefined, page: 1 }))
          }
          placeholder="Tipo"
          options={TIPO_OPTIONS}
          allLabel="Todos los tipos"
        />
        <FilterSelect
          value={filters.estado}
          onValueChange={(v) =>
            setFilters((f) => ({ ...f, estado: v as SolicitudEstado | undefined, page: 1 }))
          }
          placeholder="Estado"
          options={ESTADO_OPTIONS}
          allLabel="Todos los estados"
        />
        <FilterSelect
          value={filters.prioridad}
          onValueChange={(v) =>
            setFilters((f) => ({ ...f, prioridad: v as SolicitudPrioridad | undefined, page: 1 }))
          }
          placeholder="Prioridad"
          options={PRIORIDAD_OPTIONS}
          allLabel="Todas las prioridades"
        />
      </section>

      {/* ── Solicitudes List ───────────────────────────── */}
      <section aria-label="Lista de solicitudes">
        {solicitudesLoading ? (
          <div className="grid gap-4 md:grid-cols-2">
            <SolicitudCardSkeleton />
            <SolicitudCardSkeleton />
            <SolicitudCardSkeleton />
            <SolicitudCardSkeleton />
          </div>
        ) : solicitudesError ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <AlertTriangle className="mb-3 h-10 w-10 text-red-400" />
              <p className="text-sm font-medium text-red-600 dark:text-red-400">
                Error al cargar solicitudes
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Verifica la conexion con el servidor e intenta de nuevo.
              </p>
            </CardContent>
          </Card>
        ) : solicitudes.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <Inbox className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm font-medium text-muted-foreground">
                No hay solicitudes
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {filters.tipo || filters.estado || filters.prioridad
                  ? "Intenta ajustar los filtros para ver mas resultados."
                  : "Aun no se han registrado solicitudes ciudadanas."}
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              {solicitudes.map((s) => (
                <SolicitudCard key={s.id} solicitud={s} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-4">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={() =>
                    setFilters((f) => ({ ...f, page: currentPage - 1 }))
                  }
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="tabular-nums text-sm text-muted-foreground">
                  Pagina {currentPage} de {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage >= totalPages}
                  onClick={() =>
                    setFilters((f) => ({ ...f, page: currentPage + 1 }))
                  }
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
