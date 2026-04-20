"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertCircle,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Flame,
  Network,
  ShieldAlert,
  ShieldCheck,
  Target,
  Users2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CardShell, EmptyMetric } from "@/components/diagnostico/card-shell";
import { Badge } from "@/components/ui/badge";
import type { BloqueBase } from "@/lib/api/hooks/use-diagnostico-tier1";
import type {
  B11Data,
  B12Data,
  B13Data,
  B14Data,
  B15Data,
  B16Data,
  B17Data,
  B18Data,
} from "@/lib/api/hooks/use-diagnostico-tier2";

// =========================================================================
// Helpers
// =========================================================================

const fmtPct = (v: number | undefined | null, decimals = 1) =>
  v == null || Number.isNaN(v) ? "—" : `${v.toFixed(decimals)}%`;

const fmtNum = (v: number | undefined | null, decimals = 2) =>
  v == null || Number.isNaN(v) ? "—" : v.toFixed(decimals);

const tooltipStyle = {
  backgroundColor: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "var(--radius)",
  color: "hsl(var(--popover-foreground))",
  fontSize: 11,
};

// Paleta 5 partidos — HSL consistente con design system
const PARTIDO_COLORS: Record<string, string> = {
  MC: "hsl(30 95% 55%)", // naranja MC
  MORENA: "hsl(0 75% 50%)", // guinda MORENA
  PAN: "hsl(215 80% 50%)", // azul PAN
  PRI: "hsl(140 60% 40%)", // verde PRI
  PVEM: "hsl(90 60% 45%)", // verde PVEM
  PT: "hsl(0 70% 40%)", // rojo PT
  UNKNOWN: "hsl(var(--chart-neutral))",
};

// =========================================================================
// B11 — Cross-Partisan Validation Score
// =========================================================================
export function CardB11({ bloque }: { bloque: BloqueBase & { data?: B11Data } }) {
  const d = bloque.data;
  const score = d?.score_cross_partisan_0_100;
  const partidoSelf = d?.partido_dirigente;

  // Armar distribución incluyendo UNKNOWN al final
  const distRaw = d?.comments_por_partido ?? {};
  const ordered = Object.entries(distRaw)
    .filter(([k]) => k !== "UNKNOWN")
    .sort(([, a], [, b]) => (b as number) - (a as number));
  const unknownN = distRaw["UNKNOWN"] ?? 0;
  const total = Object.values(distRaw).reduce((a, b) => a + (b as number), 0);

  const chartData = ordered.map(([partido, n]) => ({
    partido,
    valor: n as number,
    fill: PARTIDO_COLORS[partido] ?? PARTIDO_COLORS.UNKNOWN,
  }));

  return (
    <CardShell
      code="B11"
      title="Cross-Partisan Validation"
      pregunta="¿Mi mensaje cruza líneas partidistas o solo habla a mi base?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b11"
    >
      <div className="flex items-baseline gap-3" data-testid="b11-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {score != null ? score.toFixed(1) : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">
          score 0-100 · {partidoSelf ? `base ${partidoSelf}` : ""}
        </span>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {d?.n_comments_clasificados ?? 0} clasificados de {d?.n_comments_total ?? 0} comments
        {unknownN > 0 && (
          <> · <span className="italic">{unknownN} sin afiliación inferible</span></>
        )}
      </p>

      {chartData.length > 0 && (
        <div className="h-28 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="valor"
                nameKey="partido"
                innerRadius={28}
                outerRadius={50}
                paddingAngle={2}
                strokeWidth={0}
                label={(entry: { partido: string }) => entry.partido}
                labelLine={false}
              >
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <RTooltip
                contentStyle={tooltipStyle}
                formatter={(v: number, _n: string, item) => {
                  const partido = (item as { payload?: { partido?: string } })?.payload?.partido ?? "";
                  return [`${v} comments`, partido];
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {total > 0 && (
        <p className="text-[10px] italic text-muted-foreground/80 leading-snug">
          Score sobre comments clasificados solamente. Diccionario conservador — extender
          en Sprint S4 NLP pass.
        </p>
      )}
    </CardShell>
  );
}

// =========================================================================
// B12 — CIB Detector
// =========================================================================
export function CardB12({ bloque }: { bloque: BloqueBase & { data?: B12Data } }) {
  const d = bloque.data;
  const flagged = d?.flagged_cib ?? [];
  const confidence = d?.confidence_score;

  const severityTone =
    confidence == null
      ? ""
      : confidence >= 0.7
        ? "text-[hsl(var(--chart-negative))]"
        : confidence >= 0.4
          ? "text-amber-600"
          : "text-muted-foreground";

  return (
    <CardShell
      code="B12"
      title="CIB Detector (ITESO/DFRLab)"
      pregunta="¿Hay comportamiento coordinado inauténtico en los comments?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b12"
    >
      <div className="flex items-baseline gap-3" data-testid="b12-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {d?.n_flagged_total ?? <EmptyMetric />}
        </span>
        <div className="flex flex-col leading-tight">
          <span className="text-xs text-muted-foreground">flagged</span>
          {confidence != null && (
            <span className={cn("text-[11px] font-medium", severityTone)}>
              conf {fmtNum(confidence)}
            </span>
          )}
        </div>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {d?.n_authors_unicos ?? 0} authors únicos · {d?.total_comments_analizados ?? 0} comments
      </p>

      {flagged.length > 0 ? (
        <ul
          className="space-y-1.5 text-[11px] max-h-40 overflow-y-auto pr-1"
          data-testid="b12-flagged-list"
        >
          {flagged.slice(0, 5).map((f) => (
            <li
              key={f.author_hash}
              className="rounded-md border border-border/50 bg-card px-2 py-1.5 flex items-start gap-2"
            >
              <Network className="h-3 w-3 mt-0.5 shrink-0 text-muted-foreground" aria-hidden="true" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] truncate">
                    {f.author_hash.slice(0, 12)}…
                  </span>
                  <span className={cn("text-[10px] font-medium tabular-nums", severityTone)}>
                    {fmtNum(f.confidence)}
                  </span>
                </div>
                <div className="mt-0.5 flex flex-wrap gap-0.5">
                  {f.razones.slice(0, 2).map((r, i) => (
                    <Badge key={i} variant="outline" className="text-[9px] px-1 py-0 h-3.5">
                      {r.split(":")[0]}
                    </Badge>
                  ))}
                  <span className="text-[10px] text-muted-foreground ml-1">
                    · {f.n_comments} comments
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[11px] text-muted-foreground italic">
          Sin authors flagged — señal limpia.
        </p>
      )}
    </CardShell>
  );
}

// =========================================================================
// B13 — Filtro de Realidad
// =========================================================================
const IMPACT_STYLES = {
  alto: { text: "text-[hsl(var(--chart-negative))]", bg: "bg-[hsl(var(--chart-negative))]" },
  medio: { text: "text-amber-600", bg: "bg-amber-500" },
  bajo: { text: "text-[hsl(var(--chart-positive))]", bg: "bg-[hsl(var(--chart-positive))]" },
} as const;

export function CardB13({
  bloque,
}: {
  bloque: BloqueBase & { data?: B13Data };
}) {
  const d = bloque.data;
  const pct = d?.pct_comments_flagged;
  const impact = d?.impact_hint;
  const styleImpact = impact ? IMPACT_STYLES[impact] : null;

  const widthPct = pct != null ? Math.min(pct, 100) : 0;

  return (
    <CardShell
      code="B13"
      title="Filtro de Realidad"
      pregunta="¿Cuál es mi engagement orgánico si excluyo comportamiento inauténtico?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b13"
    >
      <div className="flex items-baseline gap-3" data-testid="b13-headline">
        <span
          className={cn(
            "font-heading text-3xl font-bold tabular-nums",
            styleImpact?.text,
          )}
        >
          {pct != null ? fmtPct(pct) : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">comments inauténticos</span>
      </div>

      <div className="space-y-1">
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn(
              "h-full transition-all",
              styleImpact?.bg || "bg-muted-foreground/30",
            )}
            style={{ width: `${widthPct}%` }}
            role="progressbar"
            aria-valuenow={widthPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Porcentaje comments CIB"
          />
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
          <span>0%</span>
          <span>5% medio</span>
          <span>20% alto</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="rounded-md border border-border/50 bg-muted/20 p-2">
          <div className="font-heading text-lg font-bold tabular-nums leading-none">
            {d?.er_organico_comments ?? "—"}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
            Orgánico
          </div>
        </div>
        <div className="rounded-md border border-border/50 bg-muted/20 p-2">
          <div className="font-heading text-lg font-bold tabular-nums leading-none">
            {d?.delta_comments_cib ?? "—"}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
            Excluidos
          </div>
        </div>
      </div>

      {impact && (
        <p className="text-[11px] text-muted-foreground italic">
          Impacto <span className={cn("font-semibold", styleImpact?.text)}>{impact}</span>
          {d?.flagged_author_count != null && (
            <> · {d.flagged_author_count} authors excluidos</>
          )}
        </p>
      )}
    </CardShell>
  );
}

// =========================================================================
// B14 — Topic Drift
// =========================================================================
function driftColor(score: number): string {
  // 0=alineado (verde) → 1=drift total (rojo)
  if (score < 0.4) return "hsl(var(--chart-positive))";
  if (score < 0.75) return "hsl(30 95% 55%)";
  return "hsl(var(--chart-negative))";
}

export function CardB14({ bloque }: { bloque: BloqueBase & { data?: B14Data } }) {
  const d = bloque.data;
  const posts = d?.posts_con_drift ?? [];
  const avg = d?.drift_score_promedio;
  const altos = d?.posts_drift_alto ?? 0;

  // Heatmap: mostrar hasta 24 posts en grid 6 cols x 4 rows
  const heatmap = posts.slice(0, 24);

  return (
    <CardShell
      code="B14"
      title="Topic Drift Detector"
      pregunta="¿Mi caption habla de lo que los comments discuten?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b14"
    >
      <div className="flex items-baseline gap-3" data-testid="b14-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {avg != null ? fmtNum(avg, 3) : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">
          drift promedio · 0=alineado / 1=total
        </span>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {d?.n_posts_analizados ?? 0} posts analizados · {altos} con drift alto (&gt;
        {d?.umbral_drift_alto ?? 0.75})
      </p>

      {heatmap.length > 0 && (
        <div className="space-y-1.5" data-testid="b14-heatmap">
          <div className="grid grid-cols-6 gap-1">
            {heatmap.map((p) => (
              <div
                key={p.post_id}
                className="aspect-square rounded-sm"
                style={{ backgroundColor: driftColor(p.drift_score) }}
                title={`Post #${p.post_id} · drift ${p.drift_score.toFixed(3)} · ${p.n_comments} comments`}
                data-testid="b14-heatmap-cell"
              />
            ))}
          </div>
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-sm bg-[hsl(var(--chart-positive))]" />
              alineado
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: "hsl(30 95% 55%)" }} />
              medio
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-sm bg-[hsl(var(--chart-negative))]" />
              alto
            </span>
          </div>
        </div>
      )}

      {posts.length > 0 && (
        <ol className="space-y-0.5 text-[11px]" data-testid="b14-top-posts">
          {posts.slice(0, 3).map((p) => (
            <li key={p.post_id} className="flex items-center gap-2">
              <span
                className="h-2 w-2 rounded-sm shrink-0"
                style={{ backgroundColor: driftColor(p.drift_score) }}
                aria-hidden="true"
              />
              <span className="flex-1 truncate text-muted-foreground">
                #{p.post_id} · caption: {p.caption_tokens_top5.slice(0, 2).join(", ") || "—"}
              </span>
              <span className="font-medium tabular-nums">{fmtNum(p.drift_score, 2)}</span>
            </li>
          ))}
        </ol>
      )}
    </CardShell>
  );
}

// =========================================================================
// B15 — Rage Click Flag
// =========================================================================
export function CardB15({ bloque }: { bloque: BloqueBase & { data?: B15Data } }) {
  const d = bloque.data;
  const pct = d?.pct_engagement_rage ?? 0;
  const detectados = d?.rage_clicks_detectados ?? 0;

  const level = pct >= 20 ? "rojo" : pct >= 5 ? "amarillo" : "verde";
  const styles = {
    verde: {
      bg: "bg-[hsl(var(--chart-positive))]/10",
      border: "border-[hsl(var(--chart-positive))]/40",
      text: "text-[hsl(var(--chart-positive))]",
      Icon: CheckCircle2,
      label: "Engagement sano",
    },
    amarillo: {
      bg: "bg-amber-500/10",
      border: "border-amber-500/40",
      text: "text-amber-600",
      Icon: AlertCircle,
      label: "Vigilar indignación",
    },
    rojo: {
      bg: "bg-[hsl(var(--chart-negative))]/10",
      border: "border-[hsl(var(--chart-negative))]/40",
      text: "text-[hsl(var(--chart-negative))]",
      Icon: Flame,
      label: "Rage dominante",
    },
  }[level];
  const Icon = styles.Icon;

  const top = d?.top_posts_rage ?? [];

  return (
    <CardShell
      code="B15"
      title="Rage Click Flag"
      pregunta="¿Mi engagement es conversión o indignación?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b15"
    >
      <div
        className={cn(
          "flex items-center gap-3 rounded-md border p-3",
          styles.bg,
          styles.border,
        )}
        data-testid="b15-headline"
      >
        <Icon className={cn("h-6 w-6 shrink-0", styles.text)} aria-hidden="true" />
        <div className="flex flex-col">
          <span className={cn("font-heading text-base font-bold leading-tight", styles.text)}>
            {styles.label}
          </span>
          <span className="text-[11px] text-muted-foreground">
            {detectados} posts rage · {fmtPct(pct)} del total
          </span>
        </div>
      </div>

      {top.length > 0 ? (
        <ol className="space-y-1.5 text-[11px]" data-testid="b15-top-posts">
          {top.slice(0, 3).map((p) => (
            <li
              key={p.post_id}
              className="rounded-md border border-border/50 bg-card px-2 py-1.5"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[10px] truncate">#{p.post_id}</span>
                <span className="font-medium tabular-nums text-[hsl(var(--chart-negative))]">
                  score {p.score_rage}
                </span>
              </div>
              <div className="mt-0.5 flex flex-wrap gap-0.5">
                {p.signals.slice(0, 2).map((s, i) => (
                  <Badge key={i} variant="outline" className="text-[9px] px-1 py-0 h-3.5">
                    {s.split(":")[0]}
                  </Badge>
                ))}
                <span className="text-[10px] text-muted-foreground ml-1">
                  {p.n_comments_hostiles}/{p.n_comments_total} hostiles
                </span>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-[11px] text-muted-foreground italic">
          Sin posts rage detectados en la ventana.
        </p>
      )}
    </CardShell>
  );
}

// =========================================================================
// B16 — Rastreador Promesas
// =========================================================================
export function CardB16({ bloque }: { bloque: BloqueBase & { data?: B16Data } }) {
  const d = bloque.data;
  const total = d?.n_promesas_total ?? 0;
  const cumplidas = d?.promesas_cumplidas?.length ?? 0;
  const pendientes = d?.promesas_pendientes?.length ?? 0;
  const contradichas = d?.promesas_contradichas?.length ?? 0;

  const pctCumplidas = total > 0 ? (cumplidas / total) * 100 : 0;
  const pctPendientes = total > 0 ? (pendientes / total) * 100 : 0;
  const pctContradichas = total > 0 ? (contradichas / total) * 100 : 0;

  return (
    <CardShell
      code="B16"
      title="Rastreador Promesas"
      pregunta="¿Cumplí las promesas que registré?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b16"
    >
      <div className="flex items-baseline gap-3" data-testid="b16-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {total > 0 ? `${cumplidas}/${total}` : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">
          {total > 0 ? `${fmtPct(d?.pct_cumplidas ?? 0, 0)} cumplidas` : "promesas registradas"}
        </span>
      </div>

      {total > 0 ? (
        <div className="space-y-2" data-testid="b16-progress">
          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="flex items-center gap-1 text-[hsl(var(--chart-positive))]">
                <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                Cumplidas
              </span>
              <span className="font-medium tabular-nums">
                {cumplidas} · {fmtPct(pctCumplidas, 0)}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-[hsl(var(--chart-positive))] transition-all"
                style={{ width: `${pctCumplidas}%` }}
                role="progressbar"
                aria-valuenow={pctCumplidas}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="flex items-center gap-1 text-amber-600">
                <CalendarClock className="h-3 w-3" aria-hidden="true" />
                Pendientes
              </span>
              <span className="font-medium tabular-nums">
                {pendientes} · {fmtPct(pctPendientes, 0)}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-amber-500 transition-all"
                style={{ width: `${pctPendientes}%` }}
                role="progressbar"
                aria-valuenow={pctPendientes}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="flex items-center gap-1 text-[hsl(var(--chart-negative))]">
                <AlertCircle className="h-3 w-3" aria-hidden="true" />
                Contradichas
              </span>
              <span className="font-medium tabular-nums">
                {contradichas} · {fmtPct(pctContradichas, 0)}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-[hsl(var(--chart-negative))] transition-all"
                style={{ width: `${pctContradichas}%` }}
                role="progressbar"
                aria-valuenow={pctContradichas}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>
        </div>
      ) : (
        <p className="text-[11px] text-muted-foreground italic" data-testid="b16-empty-inline">
          Sin promesas registradas. Activar B16 requiere registrar promesas en la
          tabla <span className="font-mono">promesas_dirigente</span>.
        </p>
      )}
    </CardShell>
  );
}

// =========================================================================
// B17 — Veda INE Compliance
// =========================================================================
export function CardB17({ bloque }: { bloque: BloqueBase & { data?: B17Data } }) {
  const d = bloque.data;
  const puede = d?.puede_publicar;
  const vedaActiva = d?.ventana_veda_activa;
  const nRiesgo = d?.n_posts_riesgo ?? 0;
  const keywords = d?.keywords_prohibidas ?? [];

  const puedeTone = puede
    ? {
        bg: "bg-[hsl(var(--chart-positive))]/10",
        border: "border-[hsl(var(--chart-positive))]/40",
        text: "text-[hsl(var(--chart-positive))]",
        Icon: ShieldCheck,
        label: "Puede publicar",
      }
    : {
        bg: "bg-[hsl(var(--chart-negative))]/10",
        border: "border-[hsl(var(--chart-negative))]/40",
        text: "text-[hsl(var(--chart-negative))]",
        Icon: ShieldAlert,
        label: "Bloquear publicación",
      };
  const IconP = puedeTone.Icon;

  return (
    <CardShell
      code="B17"
      title="Veda INE Compliance"
      pregunta="¿Puedo publicar en ventana veda electoral?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b17"
    >
      <div
        className={cn(
          "flex items-center gap-3 rounded-md border p-3",
          puedeTone.bg,
          puedeTone.border,
        )}
        data-testid="b17-headline"
      >
        <IconP className={cn("h-6 w-6 shrink-0", puedeTone.text)} aria-hidden="true" />
        <div className="flex flex-col">
          <span className={cn("font-heading text-base font-bold leading-tight", puedeTone.text)}>
            {puedeTone.label}
          </span>
          <span className="text-[11px] text-muted-foreground">{d?.razon ?? "—"}</span>
        </div>
      </div>

      {/* Mini calendar / ventana veda */}
      <div
        className={cn(
          "flex items-center gap-2 rounded-md border border-border/50 px-3 py-2 text-[11px]",
          vedaActiva && "border-amber-500/40 bg-amber-500/5",
        )}
        data-testid="b17-ventana"
      >
        <CalendarClock
          className={cn("h-4 w-4", vedaActiva ? "text-amber-600" : "text-muted-foreground")}
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          <div className="font-medium">
            {vedaActiva ? "Ventana veda activa" : "Sin veda activa"}
          </div>
          <div className="text-[10px] text-muted-foreground">
            Distrito: {d?.distrito ?? "—"} · ventana {d?.ventana_dias ?? 14}d
          </div>
        </div>
      </div>

      {nRiesgo > 0 && (
        <p className="text-[11px] text-muted-foreground" data-testid="b17-riesgo">
          <span className="font-medium text-[hsl(var(--chart-negative))]">
            {nRiesgo} posts
          </span>{" "}
          con keywords de riesgo en ventana
        </p>
      )}

      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1" data-testid="b17-keywords">
          {keywords.slice(0, 6).map((k, i) => (
            <Badge key={i} variant="outline" className="text-[9px] px-1 py-0 h-4">
              {k}
            </Badge>
          ))}
        </div>
      )}
    </CardShell>
  );
}

// =========================================================================
// B18 — Violencia Política
// =========================================================================
const SEVERITY_COLORS = {
  LOW: "hsl(45 95% 50%)",
  MEDIUM: "hsl(30 95% 55%)",
  HIGH: "hsl(var(--chart-negative))",
} as const;

export function CardB18({ bloque }: { bloque: BloqueBase & { data?: B18Data } }) {
  const d = bloque.data;
  const pct = d?.pct_violento;
  const dist = d?.severity_dist ?? {};
  const top = d?.comments_violencia ?? [];

  const chartDist = (["LOW", "MEDIUM", "HIGH"] as const).map((sev) => ({
    severity: sev,
    count: dist[sev] ?? 0,
    fill: SEVERITY_COLORS[sev],
  }));

  const hasAny = chartDist.some((c) => c.count > 0);
  const worst: "LOW" | "MEDIUM" | "HIGH" = (dist["HIGH"] ?? 0) > 0
    ? "HIGH"
    : (dist["MEDIUM"] ?? 0) > 0
      ? "MEDIUM"
      : "LOW";
  const worstColor = hasAny ? SEVERITY_COLORS[worst] : "hsl(var(--chart-neutral))";

  return (
    <CardShell
      code="B18"
      title="Violencia Política"
      pregunta="¿Hay amenazas o violencia política de género en comments?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b18"
    >
      <div className="flex items-baseline gap-3" data-testid="b18-headline">
        <span
          className="font-heading text-3xl font-bold tabular-nums"
          style={{ color: worstColor }}
        >
          {pct != null ? fmtPct(pct) : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">
          {d?.n_violentos ?? 0} de {d?.total_analizados ?? 0} comments
        </span>
      </div>

      {hasAny && (
        <div className="h-20 w-full" data-testid="b18-severity-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartDist} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis
                dataKey="severity"
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
                width={28}
              />
              <RTooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {chartDist.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {top.length > 0 && (
        <ul className="space-y-1 text-[11px] max-h-28 overflow-y-auto pr-1" data-testid="b18-top-comments">
          {top.slice(0, 5).map((c) => (
            <li
              key={c.comment_id}
              className="rounded-md border border-border/50 bg-card px-2 py-1"
            >
              <div className="flex items-center justify-between gap-2">
                <Badge
                  variant="outline"
                  className="text-[9px] px-1 py-0 h-3.5"
                  style={{ color: SEVERITY_COLORS[c.severity], borderColor: SEVERITY_COLORS[c.severity] }}
                >
                  {c.severity}
                </Badge>
                <span className="text-[10px] text-muted-foreground">
                  {c.categorias.slice(0, 2).join(", ")}
                </span>
              </div>
              <p className="mt-0.5 text-[10px] text-muted-foreground line-clamp-2 leading-snug">
                {c.snippet}
              </p>
            </li>
          ))}
        </ul>
      )}

      {!hasAny && (
        <p className="text-[11px] text-muted-foreground italic flex items-center gap-1.5">
          <ShieldCheck className="h-3 w-3 text-[hsl(var(--chart-positive))]" aria-hidden="true" />
          Sin comments violentos detectados en la ventana.
        </p>
      )}
    </CardShell>
  );
}

// =========================================================================
// Skeleton (reutiliza forma del Tier 1)
// =========================================================================
export function CardTier2Skeleton() {
  return (
    <div className="card-elevated flex h-[320px] flex-col gap-3 rounded-lg border border-border/60 bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="space-y-1.5">
          <div className="h-3 w-8 animate-pulse rounded bg-muted" />
          <div className="h-4 w-44 animate-pulse rounded bg-muted" />
        </div>
        <div className="h-6 w-6 animate-pulse rounded bg-muted" />
      </div>
      <div className="h-10 w-32 animate-pulse rounded bg-muted" />
      <div className="mt-auto h-32 w-full animate-pulse rounded bg-muted" />
    </div>
  );
}

// Re-export lucide icons used en header externamente
export { Target, Users2 };
