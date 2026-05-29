"use client";

/**
 * War Room Personal · W8
 *
 * Sección "Competencia monitoreada" para el perfil del dirigente
 * (/dashboard/dirigentes/[id]). Diseño validado por Gemini + cross-audit Claude.
 *
 * Principios:
 * - El cliente (dirigente) DOMINA visualmente · los competidores SUBORDINAN.
 * - Avatares de competidores grayscale 50% + opacity 80 por default · full color en hover/tap.
 * - Mobile: carousel horizontal (snap-x) · NO grid colapsado.
 * - Desktop: drawer lateral (Sheet) · Mobile: bottom-sheet (mismo componente).
 * - Empty state accionable con copy CRECE.
 * - Métricas: solo externas (followers, engagement, posts/mes). NO NLP.
 * - Botón puente: "Ver análisis comparativo →" lleva a /dashboard/aceptacion/[id].
 */

import { useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Swords, Users, TrendingUp, ExternalLink, BarChart3, Clock } from "lucide-react";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  useCompetitorsGrouped,
  useCompetitorDetail,
  type CompetitorGrouped,
  type CompetitorMonthlyMetric,
} from "@/lib/api/hooks/use-competitors";
import { formatNumber } from "@/lib/utils";

interface Props {
  dirigenteId: number;
  dirigenteFollowers: number;
  dirigenteFirstName?: string;
}

const PLATFORM_LABEL: Record<string, string> = {
  FACEBOOK: "FB",
  INSTAGRAM: "IG",
  TWITTER: "X",
  TIKTOK: "TT",
  YOUTUBE: "YT",
};

const PLATFORM_DOT: Record<string, string> = {
  FACEBOOK: "bg-blue-600",
  INSTAGRAM: "bg-pink-500",
  TWITTER: "bg-sky-500",
  TIKTOK: "bg-neutral-800",
  YOUTUBE: "bg-red-500",
};

export function CompetitorsSection({ dirigenteId, dirigenteFollowers, dirigenteFirstName }: Props) {
  // A8 fix (2026-05-15): usamos endpoint /grouped que agrupa profiles por
  // persona. Antes 1 card por (persona, plataforma) → "Taboada duplicado".
  // Ahora 1 card por persona con badges de plataformas.
  const { data: competitors, isLoading } = useCompetitorsGrouped(dirigenteId);
  const [openId, setOpenId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-48" />
        </CardHeader>
        <CardContent>
          <div className="flex gap-3 overflow-hidden">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-32 w-40 shrink-0" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!competitors || competitors.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Swords className="h-4 w-4 text-muted-foreground" /> Competencia monitoreada
          </CardTitle>
          <CardDescription>Referentes externos · sin análisis NLP por diseño</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            {/* Siluetas placeholder · 3 círculos en arco */}
            <div className="flex items-end gap-2">
              <div className="size-10 rounded-full bg-muted/70" />
              <div className="size-14 rounded-full bg-muted/80" />
              <div className="size-10 rounded-full bg-muted/70" />
            </div>
            <p className="max-w-sm text-sm text-muted-foreground">
              Ningún referente configurado. Monitorea el crecimiento de otros perfiles
              políticos frente al tuyo.
            </p>
            <Button variant="outline" size="sm" disabled>
              Solicitar monitoreo al equipo CRECE
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Swords className="h-4 w-4 text-muted-foreground" /> Competencia monitoreada
          </CardTitle>
          <CardDescription>
            {competitors.length} {competitors.length === 1 ? "referente externo" : "referentes externos"} · sin análisis NLP
          </CardDescription>
        </div>
        <Link href={`/dashboard/aceptacion/${dirigenteId}`}>
          <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
            Análisis comparativo
            <BarChart3 className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {/* Carousel horizontal con snap · mobile-friendly */}
        <div
          className="flex gap-3 overflow-x-auto pb-2 snap-x snap-mandatory scroll-pl-1 [scrollbar-width:thin]"
          role="list"
          aria-label="Competidores monitoreados"
        >
          {competitors.map((c) => (
            <CompetitorCardMini
              key={`${c.display_name}-${c.dirigente_objetivo_id}`}
              competitor={c}
              onClick={() => {
                // Drawer carga el detalle del primer profile (más reciente
                // por orden verified DESC + platform del backend). Si tiene
                // múltiples plataformas, el drawer mostrará tabs.
                const first = c.profiles[0];
                if (first) setOpenId(first.id);
              }}
            />
          ))}
        </div>
      </CardContent>

      {/* Drawer detalle (desktop lateral · mobile bottom-sheet via shadcn Sheet side prop) */}
      <Sheet open={openId !== null} onOpenChange={(o) => !o && setOpenId(null)}>
        <SheetContent side="right" className="w-full sm:max-w-md">
          {openId !== null && (
            <CompetitorDetailDrawer
              competitorId={openId}
              dirigenteId={dirigenteId}
              dirigenteFollowers={dirigenteFollowers}
              dirigenteFirstName={dirigenteFirstName}
            />
          )}
        </SheetContent>
      </Sheet>
    </Card>
  );
}

// ── Card mini · 1 por persona, badges de N plataformas ────────────────

function CompetitorCardMini({
  competitor,
  onClick,
}: {
  competitor: CompetitorGrouped;
  onClick: () => void;
}) {
  const initials = competitor.display_name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  const isMulti = competitor.profiles.length > 1;

  return (
    <button
      type="button"
      onClick={onClick}
      role="listitem"
      className="group flex w-40 shrink-0 snap-start flex-col items-start gap-2 rounded-md border border-border/40 bg-muted/30 p-3 text-left transition hover:border-border hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="flex w-full items-center gap-2">
        <div
          className="grid size-9 shrink-0 place-items-center rounded-full bg-background text-xs font-semibold text-muted-foreground opacity-80 transition group-hover:opacity-100 group-focus-visible:opacity-100"
          style={{ filter: "grayscale(50%)" }}
          aria-hidden="true"
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-foreground">
            {competitor.display_name}
          </div>
          {competitor.partido && (
            <div className="truncate text-[10px] uppercase tracking-wider text-muted-foreground">
              {competitor.partido}
            </div>
          )}
        </div>
      </div>
      <div className="flex w-full items-center justify-between gap-2">
        <span
          className="inline-flex items-center gap-1 text-[10px] text-muted-foreground"
          aria-label={`${competitor.profiles.length} plataforma${isMulti ? "s" : ""}`}
        >
          {competitor.profiles.map((p) => (
            <span
              key={p.id}
              className={`inline-block size-1.5 rounded-full ${
                PLATFORM_DOT[p.platform] ?? "bg-muted-foreground/40"
              }`}
              aria-hidden="true"
              title={PLATFORM_LABEL[p.platform] ?? p.platform}
            />
          ))}
          <span className="ml-0.5">
            {competitor.profiles
              .map((p) => PLATFORM_LABEL[p.platform] ?? p.platform)
              .join(" · ")}
          </span>
        </span>
        {competitor.verified && (
          <Badge
            variant="outline"
            className="h-5 border-emerald-500/30 px-1.5 text-[9px] text-emerald-600"
          >
            verif
          </Badge>
        )}
      </div>
    </button>
  );
}

// ── Drawer · detalle completo del competidor seleccionado ────────────────

function CompetitorDetailDrawer({
  competitorId,
  dirigenteId,
  dirigenteFollowers,
  dirigenteFirstName,
}: {
  competitorId: number;
  dirigenteId: number;
  dirigenteFollowers: number;
  dirigenteFirstName?: string;
}) {
  const { data: detail, isLoading } = useCompetitorDetail(competitorId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!detail) {
    return (
      <SheetHeader>
        <SheetTitle>Competidor no disponible</SheetTitle>
        <SheetDescription>No se pudo cargar el detalle.</SheetDescription>
      </SheetHeader>
    );
  }

  const lastMonth = detail.last_6_months[0];
  // last_6_months viene en orden DESC (más reciente primero). Para el chart
  // necesitamos ASC. No mutamos el array original.
  const historyAsc = [...detail.last_6_months]
    .filter((m) => m.followers_total != null)
    .reverse();
  const historyPoints = historyAsc.length;

  const lastScrapedLabel = detail.last_scraped_at
    ? new Date(detail.last_scraped_at).toLocaleDateString("es-MX", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  const rivalFirstName = detail.display_name.split(" ")[0];
  const myFirstName = dirigenteFirstName ?? "Tú";
  const rivalInitials = detail.display_name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  // Delta de followers (positivo = el competidor te lleva ventaja).
  const rivalFollowers = lastMonth?.followers_total ?? null;
  const followersDelta =
    rivalFollowers != null ? rivalFollowers - dirigenteFollowers : null;

  return (
    <div className="space-y-5">
      <SheetHeader>
        <div className="flex items-center gap-3">
          <div
            className="grid size-10 shrink-0 place-items-center rounded-full bg-muted text-sm font-semibold text-muted-foreground"
            aria-hidden="true"
          >
            {rivalInitials}
          </div>
          <div className="min-w-0 flex-1">
            <SheetTitle className="flex items-center gap-2">
              <span className="truncate">{detail.display_name}</span>
              {detail.verified && (
                <Badge variant="outline" className="border-emerald-500/30 text-emerald-600">
                  verificado
                </Badge>
              )}
              {detail.profile_url && (
                <a
                  href={detail.profile_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  aria-label={`Abrir perfil en ${PLATFORM_LABEL[detail.platform] ?? detail.platform}`}
                  className="text-muted-foreground transition hover:text-foreground"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </SheetTitle>
            <SheetDescription>
              {detail.cargo ?? "Sin cargo registrado"}
              {detail.partido ? ` · ${detail.partido}` : ""}
            </SheetDescription>
          </div>
        </div>
        {lastScrapedLabel && (
          <div className="flex items-center gap-1.5 pt-1 text-[11px] text-muted-foreground">
            <Clock className="h-3 w-3" />
            Última medición: {lastScrapedLabel}
          </div>
        )}
      </SheetHeader>

      {/* Snapshot side-by-side: cliente vs competidor */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
            <Users className="h-3 w-3" /> {myFirstName}
          </div>
          <div className="mt-1 font-heading text-xl font-bold tabular-nums">
            {formatNumber(dirigenteFollowers)}
          </div>
        </div>
        <div className="rounded-md border border-slate-400/30 bg-slate-500/5 p-3">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
            <Users className="h-3 w-3" /> {rivalFirstName}
          </div>
          <div className="mt-1 font-heading text-xl font-bold tabular-nums">
            {rivalFollowers != null ? formatNumber(rivalFollowers) : "—"}
          </div>
        </div>
      </div>

      {/* Delta — reduce carga cognitiva: el dato valioso es la distancia */}
      {followersDelta != null && (
        <div
          className={`flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-xs ${
            followersDelta > 0
              ? "border-slate-300/60 bg-slate-100/40 text-foreground dark:border-slate-600/50 dark:bg-slate-800/30"
              : "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400"
          }`}
        >
          {followersDelta > 0 ? (
            <>
              <span className="font-semibold tabular-nums">
                +{formatNumber(Math.abs(followersDelta))}
              </span>
              <span className="text-muted-foreground">
                followers más que {myFirstName}
              </span>
            </>
          ) : followersDelta < 0 ? (
            <>
              <span className="font-semibold tabular-nums">
                +{formatNumber(Math.abs(followersDelta))}
              </span>
              <span>followers de ventaja para {myFirstName}</span>
            </>
          ) : (
            <span className="text-muted-foreground">Mismo número de followers</span>
          )}
        </div>
      )}

      {/* Interacción último mes */}
      <div className="rounded-md border bg-muted/30 p-3">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
          <TrendingUp className="h-3 w-3" /> Interacción último mes
        </div>
        <div className="mt-1 font-heading text-lg font-bold tabular-nums">
          {lastMonth?.engagement_rate != null
            ? `${(lastMonth.engagement_rate * 100).toFixed(1)}%`
            : "—"}
        </div>
      </div>

      {/* Histórico mensual */}
      {detail.last_6_months.length > 0 ? (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Histórico de followers
            </h3>
            <span className="text-[10px] text-muted-foreground">
              {historyPoints} {historyPoints === 1 ? "medición" : "mediciones"}
            </span>
          </div>

          {historyPoints >= 2 ? (
            <div className="mb-3 h-32 w-full rounded-md border bg-muted/20 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={historyAsc} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                  <defs>
                    <linearGradient id="grad-comp-followers" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(215, 25%, 45%)" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="hsl(215, 25%, 45%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="month_start"
                    tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => String(v).slice(0, 7)}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => formatNumber(v)}
                    width={48}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "var(--radius)",
                      fontSize: 11,
                    }}
                    labelFormatter={(l) => `Mes ${String(l).slice(0, 7)}`}
                    formatter={(val: number) => [formatNumber(val), "Followers"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="followers_total"
                    stroke="hsl(215, 25%, 45%)"
                    strokeWidth={2}
                    fill="url(#grad-comp-followers)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="mb-3 rounded-md border border-dashed bg-muted/20 px-3 py-2 text-[11px] leading-snug text-muted-foreground">
              Tendencia disponible con 2 mediciones. Próxima captura: 1º del mes.
            </p>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-muted-foreground">
                <tr className="border-b">
                  <th className="py-1.5 text-left font-medium">Mes</th>
                  <th className="py-1.5 text-right font-medium">Followers</th>
                  <th className="py-1.5 text-right font-medium">Posts</th>
                  <th className="py-1.5 text-right font-medium">Eng %</th>
                </tr>
              </thead>
              <tbody>
                {detail.last_6_months.map((m: CompetitorMonthlyMetric) => (
                  <tr key={m.month_start} className="border-b last:border-0">
                    <td className="py-1.5">{m.month_start.slice(0, 7)}</td>
                    <td className="py-1.5 text-right tabular-nums">
                      {m.followers_total != null ? formatNumber(m.followers_total) : "—"}
                    </td>
                    <td className="py-1.5 text-right tabular-nums">{m.posts_count}</td>
                    <td className="py-1.5 text-right tabular-nums">
                      {m.engagement_rate != null
                        ? `${(m.engagement_rate * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <p className="rounded-md border border-dashed p-3 text-center text-xs text-muted-foreground">
          Sin métricas mensuales todavía. El scraper light las captura una vez al mes.
        </p>
      )}

      {/* Puente cross-vista — el link al perfil externo ya está como icono
          junto al nombre en el SheetHeader (D-DRAWER-HEADER-ICON-LINK-1). */}
      <Link href={`/dashboard/aceptacion/${dirigenteId}`}>
        <Button variant="default" size="sm" className="w-full gap-2">
          Ver análisis comparativo completo
          <ExternalLink className="h-3.5 w-3.5" />
        </Button>
      </Link>
    </div>
  );
}
