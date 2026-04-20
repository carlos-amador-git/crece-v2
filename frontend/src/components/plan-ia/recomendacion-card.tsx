"use client";

import {
  AlertTriangle,
  ArrowUpRight,
  Brain,
  CalendarClock,
  CheckCircle2,
  Clock,
  ExternalLink,
  FlaskConical,
  Pause,
  PlayCircle,
  Shield,
  Target,
  TrendingUp,
  UserSquare2,
  XCircle,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  EstadoRecomendacion,
  Recomendacion,
  TipoRecomendacion,
} from "@/lib/api/hooks/use-recomendaciones";

const TIPO_META: Record<
  TipoRecomendacion,
  {
    label: string;
    icon: typeof PlayCircle;
    cls: string;
    dotCls: string;
  }
> = {
  start: {
    label: "Start",
    icon: PlayCircle,
    cls: "bg-emerald-500/10 text-emerald-700 border-emerald-500/30 dark:text-emerald-300",
    dotCls: "bg-emerald-500",
  },
  stop: {
    label: "Stop",
    icon: XCircle,
    cls: "bg-rose-500/10 text-rose-700 border-rose-500/30 dark:text-rose-300",
    dotCls: "bg-rose-500",
  },
  continue: {
    label: "Continue",
    icon: TrendingUp,
    cls: "bg-sky-500/10 text-sky-700 border-sky-500/30 dark:text-sky-300",
    dotCls: "bg-sky-500",
  },
};

const ESTADO_META: Record<
  EstadoRecomendacion,
  { label: string; cls: string }
> = {
  propuesta: {
    label: "Propuesta",
    cls: "bg-amber-500/10 text-amber-800 border-amber-500/30 dark:text-amber-300",
  },
  aprobada: {
    label: "Aprobada",
    cls: "bg-emerald-500/10 text-emerald-700 border-emerald-500/30 dark:text-emerald-300",
  },
  modificada: {
    label: "Modificada",
    cls: "bg-indigo-500/10 text-indigo-700 border-indigo-500/30 dark:text-indigo-300",
  },
  rechazada: {
    label: "Rechazada",
    cls: "bg-rose-500/10 text-rose-700 border-rose-500/30 dark:text-rose-300",
  },
  ejecutada: {
    label: "Ejecutada",
    cls: "bg-sky-500/10 text-sky-700 border-sky-500/30 dark:text-sky-300",
  },
  completada: {
    label: "Completada",
    cls: "bg-emerald-600/10 text-emerald-800 border-emerald-600/30 dark:text-emerald-200",
  },
  fallida: {
    label: "Fallida",
    cls: "bg-rose-600/10 text-rose-800 border-rose-600/30 dark:text-rose-200",
  },
};

function CriterioExitoText({ r }: { r: Recomendacion }) {
  const c = r.criterio_exito;
  if (!c) return <span className="text-muted-foreground">Sin criterio definido</span>;
  const parts: string[] = [];
  if (c.descripcion) parts.push(c.descripcion);
  if (c.metrica && c.objetivo !== undefined) {
    const u = c.unidad ?? "";
    parts.push(`Meta: ${c.metrica} ≥ ${c.objetivo}${u}`);
  }
  if (parts.length === 0) return <span className="text-muted-foreground">Sin criterio definido</span>;
  return <span>{parts.join(" · ")}</span>;
}

export interface RecomendacionCardProps {
  recomendacion: Recomendacion;
  mode: "admin" | "cliente";
  onAprobar?: (r: Recomendacion) => void;
  onRechazar?: (r: Recomendacion) => void;
  onModificar?: (r: Recomendacion) => void;
  onAceptar?: (r: Recomendacion) => void;
  dirigenteNombre?: string;
}

export function RecomendacionCard({
  recomendacion: r,
  mode,
  onAprobar,
  onRechazar,
  onModificar,
  onAceptar,
  dirigenteNombre,
}: RecomendacionCardProps) {
  const tipoMeta = TIPO_META[r.tipo] ?? TIPO_META.continue;
  const estadoMeta = ESTADO_META[r.estado] ?? ESTADO_META.propuesta;
  const TipoIcon = tipoMeta.icon;

  const createdAt = (() => {
    try {
      const d = new Date(r.created_at);
      return new Intl.DateTimeFormat("es-MX", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(d);
    } catch {
      return r.created_at;
    }
  })();

  return (
    <Card
      className={cn(
        "transition-shadow hover:shadow-md",
        r.estado === "propuesta" && "border-amber-500/30",
        r.estado === "aprobada" && "border-emerald-500/30",
      )}
      data-testid={`recomendacion-card-${r.id}`}
      data-estado={r.estado}
    >
      <CardHeader className="flex flex-col gap-3 pb-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border",
              tipoMeta.cls,
            )}
            aria-hidden
          >
            <TipoIcon className="h-4 w-4" />
          </span>
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge variant="outline" className={cn("gap-1 text-[11px]", tipoMeta.cls)}>
                <span className={cn("h-1.5 w-1.5 rounded-full", tipoMeta.dotCls)} />
                {tipoMeta.label}
              </Badge>
              <Badge variant="outline" className={cn("text-[11px]", estadoMeta.cls)}>
                {estadoMeta.label}
              </Badge>
              {r.ventana_duracion_dias && (
                <Badge variant="outline" className="gap-1 text-[11px]">
                  <Clock className="h-3 w-3" />
                  {r.ventana_duracion_dias}d
                </Badge>
              )}
            </div>
            <h3 className="font-heading text-base font-semibold leading-snug tracking-tight sm:text-lg">
              {r.accion_texto}
            </h3>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {dirigenteNombre ? (
                <span className="inline-flex items-center gap-1">
                  <UserSquare2 className="h-3 w-3" />
                  {dirigenteNombre}
                </span>
              ) : r.dirigente_nombre ? (
                <span className="inline-flex items-center gap-1">
                  <UserSquare2 className="h-3 w-3" />
                  {r.dirigente_nombre}
                </span>
              ) : null}
              <span className="inline-flex items-center gap-1">
                <CalendarClock className="h-3 w-3" />
                {createdAt}
              </span>
              {r.metadatos_llm?.generador && (
                <span className="inline-flex items-center gap-1">
                  <Brain className="h-3 w-3" />
                  {r.metadatos_llm.generador}
                  {r.metadatos_llm.prompt_version &&
                    ` · prompt ${r.metadatos_llm.prompt_version}`}
                </span>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="space-y-1">
            <dt className="flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              <Target className="h-3 w-3" />
              Criterio de éxito
            </dt>
            <dd>
              <CriterioExitoText r={r} />
            </dd>
          </div>
          {r.principio_conductual && (
            <div className="space-y-1">
              <dt className="flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <Shield className="h-3 w-3" />
                Principio conductual
              </dt>
              <dd className="text-foreground/90">{r.principio_conductual}</dd>
            </div>
          )}
          {r.evidencia_respaldo && (
            <div className="space-y-1 sm:col-span-2">
              <dt className="flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <FlaskConical className="h-3 w-3" />
                Evidencia respaldo
              </dt>
              <dd className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                {r.evidencia_respaldo.post_url ? (
                  <Link
                    href={r.evidencia_respaldo.post_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded-sm bg-muted px-1.5 py-0.5 text-foreground/80 hover:bg-accent/10 hover:text-accent"
                  >
                    Post #{r.evidencia_respaldo.post_id}
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                ) : r.evidencia_respaldo.post_id ? (
                  <span className="inline-flex items-center gap-1 rounded-sm bg-muted px-1.5 py-0.5 text-foreground/80">
                    Post #{r.evidencia_respaldo.post_id}
                  </span>
                ) : null}
                {r.evidencia_respaldo.metrica_baseline !== undefined && (
                  <span>
                    Baseline: <strong>{r.evidencia_respaldo.metrica_baseline}</strong>
                  </span>
                )}
                {(r.evidencia_respaldo.bloques ?? []).map((b) => (
                  <span
                    key={b}
                    className="inline-flex rounded-sm bg-accent/10 px-1.5 py-0.5 font-mono text-[10px] uppercase text-accent"
                  >
                    {b}
                  </span>
                ))}
              </dd>
            </div>
          )}
        </dl>

        {mode === "admin" && r.estado === "propuesta" && (
          <div className="flex flex-wrap gap-2 border-t border-border/60 pt-3">
            <Button
              size="sm"
              onClick={() => onAprobar?.(r)}
              data-testid={`btn-aprobar-${r.id}`}
            >
              <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
              Aprobar
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onModificar?.(r)}
              data-testid={`btn-modificar-${r.id}`}
            >
              Modificar
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-rose-600 hover:text-rose-700"
              onClick={() => onRechazar?.(r)}
              data-testid={`btn-rechazar-${r.id}`}
            >
              <XCircle className="mr-1 h-3.5 w-3.5" />
              Rechazar
            </Button>
          </div>
        )}

        {mode === "cliente" &&
          (r.estado === "aprobada" || r.estado === "modificada") && (
            <div className="flex flex-wrap gap-2 border-t border-border/60 pt-3">
              <Button
                size="sm"
                onClick={() => onAceptar?.(r)}
                data-testid={`btn-aceptar-${r.id}`}
              >
                <ArrowUpRight className="mr-1 h-3.5 w-3.5" />
                Aceptar y publicar
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onModificar?.(r)}
                data-testid={`btn-modificar-cliente-${r.id}`}
              >
                Modificar
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="text-rose-600 hover:text-rose-700"
                onClick={() => onRechazar?.(r)}
                data-testid={`btn-rechazar-cliente-${r.id}`}
              >
                Rechazar
              </Button>
            </div>
          )}

        {(r.estado === "rechazada" || r.estado === "fallida") && (
          <div className="flex items-start gap-2 border-t border-border/60 pt-3 text-xs text-muted-foreground">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-rose-500" />
            <span>{r.notas_cliente ?? "Sin notas registradas."}</span>
          </div>
        )}

        {r.estado === "ejecutada" && r.post_ejecutor_id && (
          <div className="flex items-center gap-2 border-t border-border/60 pt-3 text-xs text-emerald-700 dark:text-emerald-300">
            <Pause className="h-3.5 w-3.5" />
            <span>
              Vinculado al post #{r.post_ejecutor_id}. Seguimiento activo por{" "}
              {r.ventana_duracion_dias} días.
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
