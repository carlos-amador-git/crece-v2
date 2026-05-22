"use client";

/**
 * Tab "Perfiles Observados" dentro de /dashboard/aceptacion/fantasmas.
 *
 * Watchlist nominada del cliente. Patrón data-dense list view con:
 * - Header de stats agregados (4 KPIs)
 * - Filter bar sticky (platform/source/tag/active)
 * - Tabla densa ordenada por último engagement
 * - Drawer derecho on row click → engagement detalle
 * - Empty states diferenciados según contexto
 */

import { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  Eye,
  ShieldCheck,
  ShieldAlert,
  ExternalLink,
  MessageSquare,
  Heart,
  TrendingUp,
  Filter,
  Sparkles,
  UserPlus,
  Calendar,
  Swords,
  CheckCircle2,
  HelpCircle,
} from "lucide-react";
import {
  useWatchedProfiles,
  useWatchedSummary,
  useWatchedEngagement,
  useWatchedSuggestions,
  type WatchedProfile,
  type WatchedSource,
} from "@/lib/api/hooks/use-watched-profiles";
import { useCompetitors, type Competitor } from "@/lib/api/hooks/use-competitors";
import { formatNumber } from "@/lib/utils";
import { InteractionsKPIs } from "@/components/aceptacion/interactions-kpis";
import { TimelineChart } from "@/components/aceptacion/timeline-chart";
import { TopPostsCards } from "@/components/aceptacion/top-posts-cards";
import { TopFansRanking } from "@/components/aceptacion/top-fans-ranking";
import { CuratedSeedList } from "@/components/aceptacion/curated-seed-list";

const PLATFORM_LABEL: Record<string, string> = {
  FACEBOOK: "FB",
  INSTAGRAM: "IG",
  TWITTER: "X",
  TIKTOK: "TT",
  YOUTUBE: "YT",
  BLUESKY: "BS",
  THREADS: "TH",
  TELEGRAM: "TG",
};

const PLATFORM_DOT: Record<string, string> = {
  FACEBOOK: "bg-blue-600",
  INSTAGRAM: "bg-pink-500",
  TWITTER: "bg-sky-500",
  TIKTOK: "bg-neutral-800",
  YOUTUBE: "bg-red-500",
};

const SOURCE_LABEL: Record<WatchedSource, string> = {
  cliente_seed: "Cliente",
  competidor: "Competidor",
  manual: "Manual",
  auto_suggested: "Auto",
};

const SOURCE_BADGE: Record<WatchedSource, string> = {
  cliente_seed: "border-violet-500/40 text-violet-600 bg-violet-50",
  competidor: "border-rose-500/40 text-rose-600 bg-rose-50",
  manual: "border-sky-500/40 text-sky-600 bg-sky-50",
  auto_suggested: "border-amber-500/40 text-amber-600 bg-amber-50",
};

function fmtRelativeTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffH = diffMs / (1000 * 60 * 60);
  if (diffH < 1) return "hace menos de 1h";
  if (diffH < 24) return `hace ${Math.floor(diffH)}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `hace ${diffD}d`;
  if (diffD < 30) return `hace ${Math.floor(diffD / 7)}sem`;
  return d.toISOString().slice(0, 10);
}

function activityDot(lastEngagement: string | null): {
  color: string;
  label: string;
} {
  if (!lastEngagement) return { color: "bg-muted-foreground/30", label: "Sin actividad" };
  const days =
    (Date.now() - new Date(lastEngagement).getTime()) / (1000 * 60 * 60 * 24);
  if (days < 7) return { color: "bg-emerald-500", label: "Activo (<7d)" };
  if (days < 30) return { color: "bg-amber-500", label: "Tibio (7-30d)" };
  return { color: "bg-muted-foreground/40", label: "Dormido (>30d)" };
}

// ── KPI Cards: ahora usan el canonical `StatCard` de `dashboard/stat-card`
// (Sprint C 2026-05-16 unificación · accent prop integrado)

// ── Source filter ─────────────────────────────────────────────────────

function SourceFilter({
  value,
  onChange,
  counts,
}: {
  value: WatchedSource | "all";
  onChange: (v: WatchedSource | "all") => void;
  counts: Record<string, number>;
}) {
  const allOpts: Array<{ id: WatchedSource | "all"; label: string }> = [
    { id: "all", label: "Todos" },
    { id: "cliente_seed", label: "Cliente" },
    { id: "manual", label: "Manual" },
    { id: "auto_suggested", label: "Sugeridos" },
  ];
  // Solo renderizar "Todos" + filtros con count > 0.
  // Si solo queda una opción con datos además de "Todos", colapsar el bar (no aporta).
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const opts = allOpts.filter((o) => o.id === "all" || (counts[o.id] ?? 0) > 0);
  if (opts.length <= 1) return null;
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as WatchedSource | "all")}>
      <TabsList className="h-9">
        {opts.map((o) => (
          <TabsTrigger key={o.id} value={o.id} className="text-xs">
            {o.label}
            <span className="ml-1.5 rounded-full bg-foreground/10 px-1.5 text-[10px] tabular-nums">
              {o.id === "all" ? total : counts[o.id] ?? 0}
            </span>
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}

// ── Watched row ───────────────────────────────────────────────────────

function WatchedRow({
  w,
  onClick,
}: {
  w: WatchedProfile;
  onClick: () => void;
}) {
  const dot = activityDot(w.last_engagement);
  const inactive = (w.n_comments ?? 0) + (w.n_likes ?? 0) === 0;
  const platLabel = PLATFORM_LABEL[w.platform] ?? w.platform.slice(0, 3);
  const platColor = PLATFORM_DOT[w.platform] ?? "bg-muted-foreground";

  return (
    <tr
      className={`group cursor-pointer border-b transition-colors hover:bg-muted/50 ${
        inactive ? "opacity-60" : ""
      }`}
      onClick={onClick}
    >
      {/* Activity dot + name */}
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          <span
            className={`relative inline-block h-2 w-2 rounded-full ${dot.color}`}
            title={dot.label}
          >
            {dot.color === "bg-emerald-500" && (
              <span className="absolute inset-0 animate-ping rounded-full bg-emerald-500/60" />
            )}
          </span>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium leading-tight">
              {w.display_name || w.profile_handle || w.profile_external_id}
            </div>
            {w.profile_handle && w.display_name ? (
              <div className="truncate text-xs text-muted-foreground">
                @{w.profile_handle}
              </div>
            ) : null}
          </div>
        </div>
      </td>

      {/* Platform */}
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <span className={`inline-block h-1.5 w-1.5 rounded-full ${platColor}`} />
          <span className="text-xs font-mono uppercase text-muted-foreground">{platLabel}</span>
        </div>
      </td>

      {/* Source badge */}
      <td className="px-3 py-2.5">
        <Badge variant="outline" className={`${SOURCE_BADGE[w.source]} text-xs`}>
          {SOURCE_LABEL[w.source]}
        </Badge>
      </td>

      {/* Tags */}
      <td className="px-3 py-2.5">
        {w.tags && w.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {w.tags.slice(0, 3).map((t) => (
              <span
                key={t}
                className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
              >
                {t}
              </span>
            ))}
            {w.tags.length > 3 ? (
              <span className="text-[10px] text-muted-foreground">+{w.tags.length - 3}</span>
            ) : null}
          </div>
        ) : (
          <span className="text-muted-foreground/40">—</span>
        )}
      </td>

      {/* Comments */}
      <td className="px-3 py-2.5 text-right tabular-nums">
        <div className="flex items-center justify-end gap-1.5">
          <MessageSquare className="h-3 w-3 text-muted-foreground" />
          <span className={`text-sm font-medium ${w.n_comments > 0 ? "text-foreground" : "text-muted-foreground/60"}`}>
            {w.n_comments}
          </span>
        </div>
      </td>

      {/* Likes (con indicador de fuente) */}
      <td className="px-3 py-2.5 text-right tabular-nums">
        <div className="flex items-center justify-end gap-1.5">
          <Heart className="h-3 w-3 text-muted-foreground" />
          <span className={`text-sm font-medium ${w.n_likes > 0 ? "text-foreground" : "text-muted-foreground/60"}`}>
            {w.n_likes}
          </span>
        </div>
      </td>

      {/* Último engagement */}
      <td className="px-3 py-2.5 text-right">
        <span className="text-xs text-muted-foreground tabular-nums">
          {fmtRelativeTime(w.last_engagement)}
        </span>
      </td>

      {/* External link */}
      <td className="px-3 py-2.5 text-right">
        {w.profile_url ? (
          <a
            href={w.profile_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground/60 transition-colors hover:bg-muted hover:text-foreground"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        ) : null}
      </td>
    </tr>
  );
}

// ── Engagement Drawer ────────────────────────────────────────────────

function EngagementDrawer({
  watched,
  onClose,
}: {
  watched: WatchedProfile | null;
  onClose: () => void;
}) {
  const { data: engagement, isLoading } = useWatchedEngagement(watched?.id ?? null);

  return (
    <Sheet open={!!watched} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-[480px] sm:max-w-[480px]">
        {watched ? (
          <>
            <SheetHeader className="pb-4">
              <div className="flex items-start gap-3">
                <span
                  className={`mt-1 inline-block h-2.5 w-2.5 rounded-full ${
                    activityDot(watched.last_engagement).color
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <SheetTitle className="text-base leading-tight">
                    {watched.display_name || watched.profile_handle}
                  </SheetTitle>
                  <SheetDescription className="text-xs">
                    @{watched.profile_handle ?? watched.profile_external_id} ·{" "}
                    {watched.platform} · {SOURCE_LABEL[watched.source]}
                  </SheetDescription>
                </div>
                {watched.profile_url ? (
                  <a
                    href={watched.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md border text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                ) : null}
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-md border bg-muted/30 p-2">
                  <div className="text-lg font-semibold tabular-nums">{watched.n_comments}</div>
                  <div className="text-[10px] uppercase text-muted-foreground">Comments</div>
                </div>
                <div className="rounded-md border bg-muted/30 p-2">
                  <div className="text-lg font-semibold tabular-nums">{watched.n_likes}</div>
                  <div className="text-[10px] uppercase text-muted-foreground">Reacciones</div>
                </div>
                <div className="rounded-md border bg-muted/30 p-2">
                  <div className="text-xs font-medium tabular-nums leading-tight">
                    {fmtRelativeTime(watched.last_engagement)}
                  </div>
                  <div className="text-[10px] uppercase text-muted-foreground">Última</div>
                </div>
              </div>
            </SheetHeader>

            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-wider text-muted-foreground">
                <span>Historial</span>
                <span>{engagement?.length ?? 0}</span>
              </div>

              {isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : !engagement || engagement.length === 0 ? (
                <div className="rounded-lg border border-dashed p-6 text-center">
                  <Sparkles className="mx-auto mb-2 h-5 w-5 text-muted-foreground/50" />
                  <div className="text-sm text-muted-foreground">
                    Sin engagement detectado todavía.
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground/60">
                    Aparecerá cuando comente o reaccione a un post del dirigente.
                  </div>
                </div>
              ) : (
                <div className="space-y-2 overflow-y-auto pr-1" style={{ maxHeight: "calc(100vh - 320px)" }}>
                  {engagement.map((e, i) => (
                    <div key={i} className="rounded-md border bg-card p-3 text-sm">
                      <div className="mb-1 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {e.type === "comment" ? (
                            <MessageSquare className="h-3.5 w-3.5 text-sky-600" />
                          ) : (
                            <Heart className="h-3.5 w-3.5 text-rose-500" />
                          )}
                          <span className="text-xs font-medium uppercase">
                            {e.type === "comment" ? "Comment" : `Reaction · ${e.reaction_type}`}
                          </span>
                          {e.source === "visual_evidence" ? (
                            <span title="Confirmación visual (CEO)" className="inline-flex items-center gap-0.5 rounded-md bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-700">
                              <Eye className="h-2.5 w-2.5" /> visual
                            </span>
                          ) : (
                            <span title={`Detectado por: ${e.source}`} className="inline-flex items-center gap-0.5 rounded-md bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                              <ShieldCheck className="h-2.5 w-2.5" /> scrape
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {fmtRelativeTime(e.detected_at)}
                        </span>
                      </div>
                      {e.content ? (
                        <div className="mt-1 line-clamp-3 text-sm leading-snug text-foreground/90">
                          {e.content}
                        </div>
                      ) : null}
                      {e.post_url ? (
                        <a
                          href={e.post_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-2 inline-flex items-center gap-1 text-xs text-sky-600 hover:underline"
                        >
                          Ver post original <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

// ── Suggestions card ─────────────────────────────────────────────────

function SuggestionsCard({ dirigente_id }: { dirigente_id: number }) {
  const { data: suggestions, isLoading } = useWatchedSuggestions(dirigente_id, 2, 8);
  if (isLoading) return null;
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <Card className="border-amber-200/50 bg-amber-50/40">
      <CardContent className="p-4">
        <div className="mb-2 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-amber-600" />
          <span className="text-sm font-semibold">
            {suggestions.length} comentaristas frecuentes sin observar
          </span>
        </div>
        <p className="mb-3 text-xs text-muted-foreground">
          Personas que han comentado ≥2 veces y no están en tu lista. Considéralas para etiquetarlas.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {suggestions.slice(0, 8).map((s) => (
            <span
              key={s.author_hash}
              className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-white px-2 py-1 text-xs"
              title={
                s.commenter_handle
                  ? `${s.commenter_handle} · ${s.n_comments} comments en ${s.platform}`
                  : `${s.n_comments} comments en ${s.platform} · identidad sin resolver`
              }
            >
              {s.commenter_handle ? (
                <span className="text-foreground">@{s.commenter_handle}</span>
              ) : (
                <span className="font-mono text-[10px] text-muted-foreground">
                  {s.author_hash.slice(0, 8)}…
                </span>
              )}
              <span className="rounded bg-amber-100 px-1 text-[10px] tabular-nums text-amber-700">
                {s.n_comments}
              </span>
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main component ───────────────────────────────────────────────────

interface Props {
  dirigenteId: number;
  dirigenteName: string;
}

type PlatformFilter = "all" | "FACEBOOK" | "INSTAGRAM" | "TWITTER" | "TIKTOK" | "YOUTUBE";

export default function WatchedProfilesTab({ dirigenteId, dirigenteName }: Props) {
  const [sourceFilter, setSourceFilter] = useState<WatchedSource | "all">("all");
  const [activityFilter, setActivityFilter] = useState<"all" | "active" | "inactive">("all");
  const [selected, setSelected] = useState<WatchedProfile | null>(null);
  // D-PLATFORM-SELECTOR-2026-05-21 · CEO autorizó autonomía total · filtro
  // plataforma propagado a InteractionsKPIs, TimelineChart, TopPostsCards.
  const [platformFilter, setPlatformFilter] = useState<PlatformFilter>("all");
  const platformParam = platformFilter === "all" ? undefined : platformFilter;

  const { data: summary, isLoading: summaryLoading } = useWatchedSummary(dirigenteId);
  const { data: profiles, isLoading: profilesLoading } = useWatchedProfiles({
    dirigente_id: dirigenteId,
    source: sourceFilter === "all" ? undefined : sourceFilter,
    has_engagement:
      activityFilter === "all" ? undefined : activityFilter === "active",
  });

  const sourceCounts = useMemo(
    () => summary?.by_source ?? {},
    [summary],
  );

  const isLoading = summaryLoading || profilesLoading;

  return (
    <div className="space-y-4">
      {/* Header info — el título lo da el tab; aquí solo contexto */}
      <p className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{dirigenteName}</span> — lista nominada
        de cuentas a monitorear. Conexión detectada automáticamente desde el scraping.
      </p>

      {/* Selector de plataforma · D-PLATFORM-SELECTOR (2026-05-21) */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border bg-muted/20 px-3 py-2">
        <span className="text-xs font-medium text-muted-foreground">Plataforma:</span>
        {(["all", "FACEBOOK", "INSTAGRAM", "TWITTER", "TIKTOK", "YOUTUBE"] as const).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPlatformFilter(p)}
            className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              platformFilter === p
                ? "bg-orange-500/20 text-orange-700 dark:text-orange-300"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
            }`}
          >
            {p === "all" ? "Todas" : p === "FACEBOOK" ? "Facebook" : p === "INSTAGRAM" ? "Instagram" : p === "TWITTER" ? "Twitter" : p === "TIKTOK" ? "TikTok" : "YouTube"}
          </button>
        ))}
      </div>

      {/* Sprint B+C (PLAN-2026-05-17-fans-dashboard) · KPIs + Timeline + Top Posts + Top Fans */}
      <InteractionsKPIs dirigenteId={dirigenteId} days={44} platform={platformParam} />
      <TimelineChart dirigenteId={dirigenteId} days={44} platform={platformParam} />
      <div>
        <h3 className="font-heading text-sm font-semibold mb-1">
          Recepción del público según comentarios
        </h3>
        <p className="text-xs text-muted-foreground mb-2">
          Posts con más audiencia favorable y con más rechazo en comentarios · ranking
          por sentimiento promedio de los comentarios (no por likes ni interacción).
          Últimos 30 días{platformFilter === "all" ? " · todas las plataformas" : ` · solo ${platformFilter}`}.
        </p>
        <TopPostsCards dirigenteId={dirigenteId} days={30} limit={3} platform={platformParam} />
      </div>

      {/* P1 #8 (2026-05-19) · split-view per Gemini approve_split_view (OBS-7).
          Izquierda: ranking dinámico (incluye Misael VIP override).
          Derecha: lista cliente_seed siempre visible con reactions reales.
          Apila vertical en mobile/tablet, 2 columnas en xl+. */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <TopFansRanking dirigenteId={dirigenteId} limit={20} />
        <CuratedSeedList dirigenteId={dirigenteId} />
      </div>

      {/* KPI cards */}
      {summaryLoading ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="Observados"
            value={summary.total_watched}
            hint={`${summary.activos_engagement} activos · ${summary.inactivos} sin actividad`}
            icon={UserPlus}
          />
          <StatCard
            label="Activos"
            value={summary.activos_engagement}
            hint={
              summary.total_watched > 0
                ? `${((summary.activos_engagement / summary.total_watched) * 100).toFixed(0)}% del watchlist`
                : undefined
            }
            icon={TrendingUp}
            accent="good"
          />
          <StatCard
            label="Comments emitidos"
            value={summary.comments_total}
            hint="Detectados en posts del dirigente"
            icon={MessageSquare}
          />
          <StatCard
            label="Reactions detectadas"
            value={summary.likes_total}
            hint="Like + love + care + haha · todos los tipos"
            icon={Heart}
          />
        </div>
      ) : null}

      {/* Competidores monitoreados */}
      <CompetitorsCard dirigenteId={dirigenteId} />

      {/* Suggestions */}
      <SuggestionsCard dirigente_id={dirigenteId} />

      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-3">
        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          <SourceFilter value={sourceFilter} onChange={setSourceFilter} counts={sourceCounts} />
        </div>
        <Tabs value={activityFilter} onValueChange={(v) => setActivityFilter(v as typeof activityFilter)}>
          <TabsList className="h-9">
            <TabsTrigger value="all" className="text-xs">Todos</TabsTrigger>
            <TabsTrigger value="active" className="text-xs">Con actividad</TabsTrigger>
            <TabsTrigger value="inactive" className="text-xs">Sin actividad</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Tabla principal */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !profiles || profiles.length === 0 ? (
            <EmptyState
              filtered={sourceFilter !== "all" || activityFilter !== "all"}
              onClearFilters={() => {
                setSourceFilter("all");
                setActivityFilter("all");
              }}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Perfil</th>
                    <th className="px-3 py-2 text-left font-medium">Red</th>
                    <th className="px-3 py-2 text-left font-medium">Origen</th>
                    <th className="px-3 py-2 text-left font-medium">Tags</th>
                    <th className="px-3 py-2 text-right font-medium">Comments</th>
                    <th className="px-3 py-2 text-right font-medium">Reacciones</th>
                    <th className="px-3 py-2 text-right font-medium">Última actividad</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {profiles.map((w) => (
                    <WatchedRow key={w.id} w={w} onClick={() => setSelected(w)} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Drawer detalle */}
      <EngagementDrawer watched={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function CompetitorsCard({ dirigenteId }: { dirigenteId: number }) {
  const { data: competitors, isLoading } = useCompetitors(dirigenteId);

  if (isLoading) {
    return <Skeleton className="h-24 w-full" />;
  }
  if (!competitors || competitors.length === 0) return null;

  return (
    <Card className="border-rose-500/20 bg-rose-500/[0.02]">
      <CardContent className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <Swords className="h-4 w-4 text-rose-500" />
          <div className="text-sm font-semibold">
            Competidores monitoreados
          </div>
          <Badge variant="outline" className="border-rose-500/30 text-[10px] text-rose-600">
            {competitors.length} {competitors.length === 1 ? "perfil" : "perfiles"}
          </Badge>
          <div className="ml-auto text-[11px] text-muted-foreground">
            Benchmark ligero · scraping mensual · próximamente
          </div>
        </div>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {competitors.map((c) => (
            <CompetitorRow key={c.id} c={c} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function CompetitorRow({ c }: { c: Competitor }) {
  const verifiedIcon = c.verified ? (
    <span className="flex items-center gap-1 text-[10px] text-emerald-600" title="Partido + cargo verificado con fuente oficial">
      <CheckCircle2 className="h-3 w-3" />
      verificado
    </span>
  ) : (
    <span className="flex items-center gap-1 text-[10px] text-amber-600" title="Pendiente confirmación CEO">
      <HelpCircle className="h-3 w-3" />
      pendiente
    </span>
  );

  return (
    <div className="group flex items-center gap-3 rounded-md border bg-card px-3 py-2 transition hover:border-rose-500/30 hover:bg-rose-500/5">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-rose-100 text-xs font-semibold text-rose-700">
        {c.display_name
          .split(" ")
          .map((p) => p[0])
          .slice(0, 2)
          .join("")
          .toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <div className="truncate text-sm font-medium">{c.display_name}</div>
          {verifiedIcon}
        </div>
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          {c.partido ? (
            <Badge variant="outline" className="h-4 border-rose-500/30 px-1.5 text-[9px] text-rose-700">
              {c.partido}
            </Badge>
          ) : (
            <span className="italic">Sin afiliación pública</span>
          )}
          <span>·</span>
          <span className="truncate">{c.cargo ?? "Sin cargo"}</span>
        </div>
      </div>
      {c.profile_url && (
        <a
          href={c.profile_url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-muted-foreground opacity-0 transition group-hover:opacity-100 hover:text-foreground"
          onClick={(e) => e.stopPropagation()}
          aria-label={`Abrir perfil de ${c.display_name}`}
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      )}
    </div>
  );
}

function EmptyState({
  filtered,
  onClearFilters,
}: {
  filtered: boolean;
  onClearFilters: () => void;
}) {
  if (filtered) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 px-4 py-12 text-center">
        <Filter className="h-8 w-8 text-muted-foreground/40" />
        <div className="text-sm text-muted-foreground">
          Ningún perfil coincide con los filtros aplicados.
        </div>
        <Button variant="outline" size="sm" onClick={onClearFilters}>
          Limpiar filtros
        </Button>
      </div>
    );
  }
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-4 py-12 text-center">
      <Eye className="h-8 w-8 text-muted-foreground/40" />
      <div className="text-sm font-medium">Aún no hay perfiles observados.</div>
      <div className="max-w-sm text-xs text-muted-foreground">
        Agrega perfiles del cliente, marca commenters frecuentes o importa una lista
        para empezar a monitorearlos.
      </div>
      <Button variant="outline" size="sm" disabled>
        <UserPlus className="mr-1.5 h-3.5 w-3.5" />
        Agregar perfil (próximamente)
      </Button>
    </div>
  );
}
