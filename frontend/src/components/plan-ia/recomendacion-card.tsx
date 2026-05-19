"use client";

import {
  AlertTriangle,
  ArrowUpRight,
  Brain,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  Facebook,
  FlaskConical,
  Instagram,
  Music,
  Pause,
  Sparkles,
  Target,
  TrendingUp,
  Twitter,
  UserSquare2,
  Wand2,
  XCircle,
  Youtube,
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

// =============================================================================
// UX Redesign 2026-05-12 (cross-audit Gemini)
// - Card en 3 zonas: Header / Body (con bloque draft destacado) / Footer
// - Iconos plataformas detectados desde accion_texto
// - Badge compuesto estado+tipo (Gemini: "Lista para inicio")
// - Estrategia con iconos 🎯/🧠 lado a lado
// - Acciones secundarias ghost-button (menos peso visual)
// - Más whitespace, icono Wand2 (consistencia varita mágica)
// =============================================================================

const TIPO_META: Record<
  TipoRecomendacion,
  { label: string; cls: string; verbo: string }
> = {
  start: { label: "Start", cls: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300", verbo: "Lista para iniciar" },
  stop: { label: "Stop", cls: "bg-rose-500/15 text-rose-700 dark:text-rose-300", verbo: "Marcada para detener" },
  continue: { label: "Continue", cls: "bg-sky-500/15 text-sky-700 dark:text-sky-300", verbo: "Mantener en curso" },
};

const ESTADO_META: Record<EstadoRecomendacion, { label: string; cls: string }> = {
  propuesta: { label: "Propuesta", cls: "bg-amber-500/10 text-amber-800 dark:text-amber-300" },
  aprobada: { label: "Aprobada", cls: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" },
  modificada: { label: "Modificada", cls: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-300" },
  rechazada: { label: "Rechazada", cls: "bg-rose-500/10 text-rose-700 dark:text-rose-300" },
  ejecutada: { label: "Ejecutada", cls: "bg-sky-500/10 text-sky-700 dark:text-sky-300" },
  completada: { label: "Completada", cls: "bg-emerald-600/10 text-emerald-800 dark:text-emerald-200" },
  fallida: { label: "Fallida", cls: "bg-rose-600/10 text-rose-800 dark:text-rose-200" },
};

// Plataformas: detecta menciones en accion_texto y devuelve iconos
const PLATFORM_PATTERNS: { keys: RegExp; icon: typeof Instagram; cls: string; label: string }[] = [
  { keys: /\bIG\b|Instagram/i, icon: Instagram, cls: "text-pink-600", label: "Instagram" },
  { keys: /\bFB\b|Facebook/i, icon: Facebook, cls: "text-blue-600", label: "Facebook" },
  { keys: /\bTwitter\b|\bX\/Twitter\b|\bTikTok\b.* X\b/i, icon: Twitter, cls: "text-sky-500", label: "X / Twitter" },
  { keys: /TikTok/i, icon: Music, cls: "text-zinc-700 dark:text-zinc-200", label: "TikTok" },
  { keys: /YouTube/i, icon: Youtube, cls: "text-red-600", label: "YouTube" },
];

function detectPlataformas(text: string): { icon: typeof Instagram; cls: string; label: string }[] {
  const found: { icon: typeof Instagram; cls: string; label: string }[] = [];
  for (const p of PLATFORM_PATTERNS) {
    if (p.keys.test(text)) {
      found.push({ icon: p.icon, cls: p.cls, label: p.label });
    }
  }
  return found;
}

const PLATFORM_META: Record<string, { icon: typeof Instagram; cls: string; label: string }> = {
  INSTAGRAM: { icon: Instagram, cls: "text-pink-600", label: "Instagram" },
  FACEBOOK: { icon: Facebook, cls: "text-blue-600", label: "Facebook" },
  TWITTER: { icon: Twitter, cls: "text-sky-500", label: "X / Twitter" },
  TIKTOK: { icon: Music, cls: "text-zinc-700 dark:text-zinc-200", label: "TikTok" },
  YOUTUBE: { icon: Youtube, cls: "text-red-600", label: "YouTube" },
};

function plataformasFromStructured(arr: string[] | null | undefined) {
  if (!arr || arr.length === 0) return null;
  const items = arr.map((p) => PLATFORM_META[p]).filter(Boolean);
  return items.length > 0 ? items : null;
}

// Extrae el bloque "Draft" del accion_texto si existe (formato: "Draft (...):\n\"...\"")
function splitDraftBlock(text: string): { intro: string; draft: string | null; outro: string } {
  // Busca el primer bloque entre comillas que se vea como draft de post
  const m = text.match(/Draft[^:]*:\s*\n?\s*"([\s\S]+?)"/);
  if (!m) return { intro: text, draft: null, outro: "" };
  const before = text.slice(0, m.index ?? 0).trim();
  const after = text.slice((m.index ?? 0) + m[0].length).trim();
  return { intro: before, draft: m[1].trim(), outro: after };
}

function CriterioExitoText({ r }: { r: Recomendacion }) {
  const c = r.criterio_exito;
  if (!c) return <span className="text-muted-foreground italic">Sin criterio definido</span>;
  const parts: string[] = [];
  if (c.descripcion) parts.push(c.descripcion);
  if (c.metrica && c.objetivo !== undefined) {
    const u = c.unidad ?? "";
    parts.push(`Meta: ${c.metrica} ≥ ${c.objetivo}${u}`);
  }
  // Para criterios custom (jsonb libre)
  const flat = Object.entries(c)
    .filter(([k]) => !["descripcion", "metrica", "objetivo", "unidad"].includes(k))
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${String(v)}`);
  parts.push(...flat);
  if (parts.length === 0) return <span className="text-muted-foreground italic">Sin criterio definido</span>;
  return <>{parts.join(" · ")}</>;
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

  const createdAt = (() => {
    try {
      const d = new Date(r.created_at);
      return new Intl.DateTimeFormat("es-MX", {
        day: "numeric",
        month: "short",
      }).format(d);
    } catch {
      return r.created_at;
    }
  })();

  // Plataformas: priorizar campo estructurado · fallback a detección regex (compat con recs viejas)
  const plataformas = plataformasFromStructured(r.plataformas_destino) ?? detectPlataformas(r.accion_texto);
  const { intro, draft, outro } = splitDraftBlock(r.accion_texto);
  // Title: primera línea del accion_texto, limpiada.
  // Strip sufijo "— POST IG + FB" o variantes (ya redundante con los iconos
  // de plataforma en el header) · cross-audit Gemini 2026-05-12.
  const firstLine = (intro.split("\n")[0] ?? "").trim();
  const tituloLimpio = (firstLine.length > 0 ? firstLine : "Recomendación IA")
    .replace(
      /\s*[—-]+\s*(POST|REEL|STORY|CARRUSEL|VIDEO|GUION)(\s+(IG|FB|TT|TIKTOK|YT|YOUTUBE|X|TWITTER|INSTAGRAM|FACEBOOK)([\s+/,&]+(IG|FB|TT|TIKTOK|YT|YOUTUBE|X|TWITTER|INSTAGRAM|FACEBOOK))*)?\.?\s*$/i,
      "",
    )
    .replace(/[.\s]+$/, "")
    .trim();
  // Body intro: resto después del título (sin la primera línea)
  const introRest = intro.split("\n").slice(1).join("\n").trim();

  // Badge compuesto: estado + tipo verbo (Gemini: "Lista para inicio")
  const composedLabel =
    r.estado === "aprobada" || r.estado === "modificada"
      ? tipoMeta.verbo
      : `${estadoMeta.label} · ${tipoMeta.label}`;
  const composedCls =
    r.estado === "aprobada" || r.estado === "modificada"
      ? tipoMeta.cls
      : estadoMeta.cls;

  return (
    <Card
      className={cn(
        "flex flex-col gap-0 overflow-hidden border-border/60 shadow-sm transition-shadow hover:shadow-md",
        r.estado === "propuesta" && "border-amber-500/30",
      )}
      data-testid={`recomendacion-card-${r.id}`}
      data-estado={r.estado}
    >
      {/* ────────── HEADER (Gemini Zone 1) ────────── */}
      <CardHeader className="space-y-2 border-b border-border/40 bg-muted/20 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge
                variant="outline"
                className={cn(
                  "gap-1 border-0 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
                  composedCls,
                )}
              >
                <Check className="h-3 w-3" />
                {composedLabel}
              </Badge>
              {r.ventana_duracion_dias && (
                <Badge variant="outline" className="gap-1 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  <Clock className="h-2.5 w-2.5" />
                  {r.ventana_duracion_dias}d
                </Badge>
              )}
              <Badge variant="outline" className="px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {createdAt}
              </Badge>
            </div>
            <h3 className="font-heading text-base font-semibold leading-snug tracking-tight text-foreground sm:text-[17px]">
              {tituloLimpio}
            </h3>
            {(dirigenteNombre || r.dirigente_nombre) && (
              <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <UserSquare2 className="h-3 w-3" />
                {dirigenteNombre ?? r.dirigente_nombre}
              </p>
            )}
          </div>
          {plataformas.length > 0 && (
            <div className="flex shrink-0 items-center gap-1.5">
              {plataformas.map((p, i) => {
                const Icon = p.icon;
                return (
                  <span
                    key={i}
                    title={p.label}
                    className={cn(
                      "flex h-7 w-7 items-center justify-center rounded-md border border-border/40 bg-card",
                      p.cls,
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </CardHeader>

      {/* ────────── BODY (Gemini Zone 2) ────────── */}
      <CardContent className="space-y-4 px-5 py-5">
        {introRest && (
          <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-line">
            {introRest}
          </p>
        )}

        {/* Draft destacado · borde izquierdo color + fondo muted + monospace */}
        {draft && (
          <blockquote
            className="rounded-r-md border-l-4 border-accent/70 bg-muted/30 px-4 py-3 font-mono text-[13px] leading-relaxed text-foreground whitespace-pre-line"
            data-testid={`draft-${r.id}`}
          >
            {draft}
          </blockquote>
        )}

        {outro && (
          <p className="text-xs leading-relaxed text-muted-foreground whitespace-pre-line">
            {outro}
          </p>
        )}

        {/* Estrategia compacta · iconos lado a lado (Gemini) */}
        {(r.criterio_exito || r.principio_conductual) && (
          <div className="grid gap-2 rounded-md bg-muted/20 px-3 py-2.5 text-xs sm:grid-cols-2">
            <div className="flex items-start gap-2">
              <Target className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
              <div className="min-w-0">
                <p className="font-medium uppercase tracking-wider text-[10px] text-muted-foreground">
                  Criterio de éxito
                </p>
                <p className="text-foreground/85 leading-tight">
                  <CriterioExitoText r={r} />
                </p>
              </div>
            </div>
            {r.principio_conductual && (
              <div className="flex items-start gap-2">
                <Brain className="mt-0.5 h-3.5 w-3.5 shrink-0 text-indigo-600" />
                <div className="min-w-0">
                  <p className="font-medium uppercase tracking-wider text-[10px] text-muted-foreground">
                    Principio conductual
                  </p>
                  <p className="text-foreground/85 leading-tight">{r.principio_conductual}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {r.evidencia_respaldo && (
          <details className="text-xs text-muted-foreground">
            <summary className="flex cursor-pointer items-center gap-1 font-medium uppercase tracking-wider text-[10px] hover:text-foreground">
              <FlaskConical className="h-3 w-3" />
              Evidencia y contexto
            </summary>
            <div className="mt-2 flex flex-wrap items-center gap-2 pl-4">
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
                <span className="inline-flex items-center gap-1 rounded-sm bg-muted px-1.5 py-0.5">
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
            </div>
          </details>
        )}
      </CardContent>

      {/* ────────── FOOTER (Gemini Zone 3) — acciones con peso rebalanceado ────────── */}
      {mode === "admin" && r.estado === "propuesta" && (
        <div className="flex flex-wrap items-center gap-2 border-t border-border/40 bg-muted/10 px-5 py-3">
          <Button size="sm" onClick={() => onAprobar?.(r)} data-testid={`btn-aprobar-${r.id}`}>
            <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
            Aprobar
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onModificar?.(r)}
            data-testid={`btn-modificar-${r.id}`}
          >
            Modificar
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-rose-600 hover:bg-rose-500/10 hover:text-rose-700"
            onClick={() => onRechazar?.(r)}
            data-testid={`btn-rechazar-${r.id}`}
          >
            <XCircle className="mr-1 h-3.5 w-3.5" />
            Rechazar
          </Button>
        </div>
      )}

      {mode === "cliente" && (r.estado === "aprobada" || r.estado === "modificada") && (
        <div className="flex flex-wrap items-center gap-2 border-t border-border/40 bg-muted/10 px-5 py-3">
          <Button size="sm" onClick={() => onAceptar?.(r)} data-testid={`btn-aceptar-${r.id}`}>
            <ArrowUpRight className="mr-1 h-3.5 w-3.5" />
            Aceptar y publicar
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onModificar?.(r)}
            data-testid={`btn-modificar-cliente-${r.id}`}
          >
            <Wand2 className="mr-1 h-3.5 w-3.5" />
            Modificar
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-rose-600 hover:bg-rose-500/10 hover:text-rose-700"
            onClick={() => onRechazar?.(r)}
            data-testid={`btn-rechazar-cliente-${r.id}`}
          >
            Rechazar
          </Button>
        </div>
      )}

      {(r.estado === "rechazada" || r.estado === "fallida") && (
        <div className="flex items-start gap-2 border-t border-border/40 bg-muted/10 px-5 py-3 text-xs text-muted-foreground">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-rose-500" />
          <span>{r.notas_cliente ?? "Sin notas registradas."}</span>
        </div>
      )}

      {r.estado === "ejecutada" && r.post_ejecutor_id && (
        <div className="flex items-center gap-2 border-t border-border/40 bg-emerald-500/5 px-5 py-3 text-xs text-emerald-700 dark:text-emerald-300">
          <Pause className="h-3.5 w-3.5" />
          <span>
            Vinculado al post #{r.post_ejecutor_id}. Seguimiento activo por{" "}
            {r.ventana_duracion_dias} días.
          </span>
        </div>
      )}
    </Card>
  );
}
