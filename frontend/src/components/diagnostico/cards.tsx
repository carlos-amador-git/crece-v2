"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
  Pie,
  PieChart,
} from "recharts";
import { CheckCircle2, AlertCircle, Flame, Minus, TrendingUp, Users2, Info, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { CardShell, EmptyMetric } from "./card-shell";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { useHumanizacionExamples } from "@/lib/api/hooks/use-diagnostico-tier1";
import type {
  B01Data,
  B02Data,
  B03Data,
  B04Data,
  B05Data,
  B06Data,
  B07Data,
  B08Data,
  B09Data,
  B10Data,
  BloqueBase,
} from "@/lib/api/hooks/use-diagnostico-tier1";

// --- helpers ---

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

// Benchmark empírico MX D-19 (Nano × plataformas, n=316)
const BENCHMARK_MX_NANO_PISO = 4.6;
const BENCHMARK_MX_N_OBS = 316;
const ZENODO_METHODOLOGY_URL =
  "https://github.com/MarxCha/crece-v2/blob/main/backend/data/zenodo/v1/methodology.md";

// ========================================================================
// B01 — ER Normalizado por Estrato
// ========================================================================
export function CardB01({ bloque }: { bloque: BloqueBase & { data?: B01Data } }) {
  const d = bloque.data;
  const platforms = d?.er_por_plataforma ? Object.entries(d.er_por_plataforma) : [];

  const chartData = platforms.map(([platform, p]) => ({
    platform: platform.slice(0, 3),
    actual: Number(p.er_actual_pct ?? 0),
    min: Number(p.er_esperado_rango_pct?.[0] ?? 0),
  }));

  // headline = promedio actual vs promedio mínimo esperado
  const avgActual = platforms.length
    ? platforms.reduce((acc, [, p]) => acc + (p.er_actual_pct ?? 0), 0) / platforms.length
    : null;
  const avgMin = platforms.length
    ? platforms.reduce((acc, [, p]) => acc + (p.er_esperado_rango_pct?.[0] ?? 0), 0) /
      platforms.length
    : null;

  return (
    <CardShell
      code="B01"
      title="ER normalizado por estrato"
      pregunta="¿Mi Engagement Rate está en el rango esperado para mi estrato y plataforma?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b01"
    >
      <div className="flex items-baseline gap-3" data-testid="b01-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {avgActual != null ? fmtPct(avgActual) : <EmptyMetric />}
        </span>
        {avgMin != null && (
          <span className="text-xs text-muted-foreground">
            vs piso {fmtPct(avgMin)}
          </span>
        )}
      </div>
      <p className="text-[11px] text-muted-foreground">
        Estrato <span className="font-medium text-foreground">{d?.estrato ?? "—"}</span>
        {d?.n_posts_total != null && <> · {d.n_posts_total} posts / {d.ventana_dias_analizada}d</>}
      </p>

      {/* Contexto explicativo D-19 — T0.6 */}
      <div
        className="rounded-md border border-border/50 bg-muted/30 px-3 py-2 text-[11px] space-y-1"
        data-testid="b01-contexto-benchmark"
      >
        <p className="text-muted-foreground leading-snug">
          Tu ER <span className="font-medium text-foreground">{avgActual != null ? fmtPct(avgActual) : "—"}</span>
          {" · "}Benchmark empírico MX{" "}
          <span className="font-medium text-foreground">{BENCHMARK_MX_NANO_PISO}%</span>
          {" "}(Zenodo v1, n={BENCHMARK_MX_N_OBS})
        </p>
        <p className="text-muted-foreground leading-snug">
          El benchmark comercial histórico (Sprout Social · Rival IQ · IM commercial)
          sobre-estimaba este rango hasta{" "}
          <span className="font-medium text-foreground">~100×</span>{" "}
          para contenido político.
        </p>
        <div className="flex items-center gap-2 pt-0.5">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-label="Explicación del benchmark ER"
                  className="flex items-center gap-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Info className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground transition-colors" aria-hidden="true" />
                  <span className="text-muted-foreground hover:text-foreground transition-colors">¿Por qué es más bajo que Sprout Social?</span>
                </button>
              </TooltipTrigger>
              <TooltipContent
                side="top"
                className="max-w-xs text-[11px] leading-snug"
              >
                <p>
                  Dictamen externo 2026-04-19 (D-19 CRECE v2) demostró que las tablas
                  comerciales de Influencer Marketing sobre-estiman el ER político mexicano
                  por factor 3-100×. Ver metodología reproducible en bundle Zenodo v1.
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <a
            href={ZENODO_METHODOLOGY_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-0.5 text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            aria-label="Ver metodología en GitHub (abre en nueva pestaña)"
          >
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
            <span>Ver metodología</span>
          </a>
        </div>
      </div>

      <div className="h-32 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis
              dataKey="platform"
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <RTooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v.toFixed(2)}%`} />
            <Bar dataKey="actual" fill="hsl(var(--chart-accent))" name="ER actual" radius={[3, 3, 0, 0]} />
            <Bar dataKey="min" fill="hsl(var(--chart-neutral))" name="Piso esperado" radius={[3, 3, 0, 0]} opacity={0.5} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CardShell>
  );
}

// ========================================================================
// B02 — Breakout Scale (Brookings 1-6)
// ========================================================================
const CAT_EMOJIS = ["·", "▪", "▲", "⬢", "✦", "★", "☀"]; // 0..6
const CAT_LABELS = ["—", "Baseline", "Amplificado", "Breakout", "Viral", "Nacional", "Global"];

export function CardB02({ bloque }: { bloque: BloqueBase & { data?: B02Data } }) {
  const d = bloque.data;
  const cat = d?.max_categoria ?? 0;
  const label = CAT_LABELS[Math.min(cat, 6)] ?? "—";
  const icon = CAT_EMOJIS[Math.min(cat, 6)] ?? "·";
  const pct = d?.views_breakout_pct ?? 0;

  return (
    <CardShell
      code="B02"
      title="Breakout Scale (Brookings)"
      pregunta="¿Crucé fronteras algorítmicas hacia audiencia no-seguidora?"
      fidelity={d?.fidelity || "T1"}
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b02"
    >
      <div className="flex items-center gap-3" data-testid="b02-headline">
        <span className="font-heading text-5xl font-bold tabular-nums" aria-hidden="true">
          {icon}
        </span>
        <div className="flex flex-col">
          <span className="font-heading text-2xl font-bold tabular-nums">
            Cat {d ? cat : "—"}
          </span>
          <span className="text-xs text-muted-foreground">{label}</span>
        </div>
      </div>
      <div className="space-y-1">
        <div className="flex justify-between text-[11px]">
          <span className="text-muted-foreground">Progreso hacia Cat 6</span>
          <span className="font-medium tabular-nums">{Math.min((cat / 6) * 100, 100).toFixed(0)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-[hsl(var(--chart-accent))] transition-all"
            style={{ width: `${Math.min((cat / 6) * 100, 100)}%` }}
            role="progressbar"
            aria-valuenow={cat}
            aria-valuemin={1}
            aria-valuemax={6}
          />
        </div>
        {d && (
          <p className="text-[11px] text-muted-foreground pt-1">
            {d.n_posts_evaluados} posts evaluados · {pct.toFixed(1)}% views breakout
          </p>
        )}
      </div>
    </CardShell>
  );
}

// ========================================================================
// B03 — Matriz 2x2 de contenido
// ========================================================================
const CUADRANTE_COLORS: Record<string, string> = {
  INSIGNIA: "hsl(var(--chart-positive))",
  CRISIS: "hsl(var(--chart-negative))",
  VANIDAD: "hsl(var(--chart-accent))",
  MUERTA: "hsl(var(--chart-neutral))",
};

export function CardB03({ bloque }: { bloque: BloqueBase & { data?: B03Data } }) {
  const d = bloque.data;
  const conteo = d?.conteo_cuadrantes ?? {};
  // sample max 60 posts para scatter
  const scatterData = (d?.posts ?? []).slice(0, 60).map((p) => ({
    x: p.engagement_rate,
    y: p.sentiment_score,
    cuadrante: p.cuadrante,
  }));

  return (
    <CardShell
      code="B03"
      title="Matriz 2×2 de contenido"
      pregunta="¿Qué posts amplificar (Insignia) y cuáles evitar (Crisis/Muerta)?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b03"
    >
      <div className="grid grid-cols-2 gap-1.5 text-[11px]" data-testid="b03-headline">
        {(["INSIGNIA", "CRISIS", "VANIDAD", "MUERTA"] as const).map((k) => (
          <div
            key={k}
            className="rounded-md border border-border/50 bg-card px-2 py-1.5"
            style={{ borderLeft: `3px solid ${CUADRANTE_COLORS[k]}` }}
          >
            <div className="font-heading text-lg font-bold tabular-nums leading-none">
              {conteo[k] ?? 0}
            </div>
            <div className="text-[9px] uppercase tracking-wider text-muted-foreground">
              {k}
            </div>
          </div>
        ))}
      </div>
      {scatterData.length > 0 && (
        <div className="h-24 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="x"
                tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="number"
                dataKey="y"
                domain={[-1, 1]}
                tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
                width={28}
              />
              <ReferenceLine x={d?.umbral_engagement ?? 0} stroke="hsl(var(--border))" strokeDasharray="2 2" />
              <ReferenceLine y={0} stroke="hsl(var(--border))" strokeDasharray="2 2" />
              <Scatter data={scatterData}>
                {scatterData.map((p, i) => (
                  <Cell key={i} fill={CUADRANTE_COLORS[p.cuadrante] || "hsl(var(--chart-neutral))"} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </CardShell>
  );
}

// ========================================================================
// B04 — Benchmark vs competidores
// ========================================================================
export function CardB04({ bloque }: { bloque: BloqueBase & { data?: B04Data } }) {
  const d = bloque.data;
  const self = d?.self;
  const rivales = d?.rivales ?? [];
  const rows = self
    ? [
        { name: "Tú", er: self.er_avg_pct ?? 0, isSelf: true },
        ...rivales.slice(0, 4).map((r) => ({
          name: r.full_name?.split(" ")[0] ?? `Rival ${r.dirigente_id}`,
          er: r.er_avg_pct ?? 0,
          isSelf: false,
        })),
      ]
    : [];

  return (
    <CardShell
      code="B04"
      title="Benchmark vs competidores"
      pregunta="¿Cómo me comparo con mis rivales directos en ER?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b04"
    >
      <div className="flex items-baseline gap-3" data-testid="b04-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {self ? fmtPct(self.er_avg_pct) : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">ER tuyo · últimos {d?.ventana_dias ?? 28}d</span>
      </div>
      <div className="h-28 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ top: 2, right: 24, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <RTooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v.toFixed(2)}%`} />
            <Bar dataKey="er" radius={[0, 3, 3, 0]}>
              {rows.map((r, i) => (
                <Cell
                  key={i}
                  fill={r.isSelf ? "hsl(var(--chart-accent))" : "hsl(var(--chart-neutral))"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CardShell>
  );
}

// ========================================================================
// B05 — Sentiment Plutchik
// ========================================================================
const PLUTCHIK_ORDER = ["trust", "joy", "anticipation", "anger", "sadness", "fear"] as const;

export function CardB05({ bloque }: { bloque: BloqueBase & { data?: B05Data } }) {
  const d = bloque.data;
  const em = d?.emociones_promedio ?? {};
  const chart = PLUTCHIK_ORDER.map((k) => ({
    emocion: k.charAt(0).toUpperCase() + k.slice(1),
    valor: Number(em[k] ?? 0),
  }));

  const ratio = d?.ratio_trust_anger;
  const positivo = (ratio ?? 0) >= 1;

  return (
    <CardShell
      code="B05"
      title="Sentiment Plutchik (6 emociones)"
      pregunta="¿Qué siente mi audiencia — confianza o enojo predominante?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      warnings={bloque.warnings}
      testId="card-b05"
    >
      <div className="flex items-baseline gap-3" data-testid="b05-headline">
        <span
          className={cn(
            "font-heading text-3xl font-bold tabular-nums",
            ratio != null && (positivo ? "text-[hsl(var(--chart-positive))]" : "text-[hsl(var(--chart-negative))]"),
          )}
        >
          {ratio != null ? fmtNum(ratio, 2) : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">trust / anger</span>
      </div>
      <div className="h-32 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="82%" data={chart}>
            <PolarGrid stroke="hsl(var(--border))" />
            <PolarAngleAxis
              dataKey="emocion"
              tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
            />
            <PolarRadiusAxis angle={90} tick={false} axisLine={false} />
            <Radar
              dataKey="valor"
              stroke="hsl(var(--chart-accent))"
              fill="hsl(var(--chart-accent))"
              fillOpacity={0.35}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </CardShell>
  );
}

// ========================================================================
// B06 — Crisis Spike detector
// ========================================================================
export function CardB06({ bloque }: { bloque: BloqueBase & { data?: B06Data } }) {
  const d = bloque.data;
  const spike = d?.spike_detected ?? false;
  const severity = d?.severity ?? 0;

  const level =
    !spike ? "verde" : severity >= 0.7 ? "rojo" : severity >= 0.4 ? "amarillo" : "verde";
  const styles = {
    verde: {
      bg: "bg-[hsl(var(--chart-positive))]/10",
      border: "border-[hsl(var(--chart-positive))]/40",
      text: "text-[hsl(var(--chart-positive))]",
      Icon: CheckCircle2,
      label: "Estable",
    },
    amarillo: {
      bg: "bg-amber-500/10",
      border: "border-amber-500/40",
      text: "text-amber-600",
      Icon: AlertCircle,
      label: "Vigilar",
    },
    rojo: {
      bg: "bg-[hsl(var(--chart-negative))]/10",
      border: "border-[hsl(var(--chart-negative))]/40",
      text: "text-[hsl(var(--chart-negative))]",
      Icon: Flame,
      label: "Crisis detectada",
    },
  }[level];
  const Icon = styles.Icon;

  return (
    <CardShell
      code="B06"
      title="Crisis Spike detector"
      pregunta="¿Hay picos anómalos de toxicidad/enojo en ventana de 2h?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b06"
    >
      <div
        className={cn(
          "flex items-center gap-3 rounded-md border p-3",
          styles.bg,
          styles.border,
        )}
        data-testid="b06-headline"
      >
        <Icon className={cn("h-6 w-6 shrink-0", styles.text)} aria-hidden="true" />
        <div className="flex flex-col">
          <span className={cn("font-heading text-base font-bold leading-tight", styles.text)}>
            {styles.label}
          </span>
          <span className="text-[11px] text-muted-foreground">
            Severity {fmtNum(severity)} · {d?.posts_toxicos_2h ?? 0} post(s) tóxicos 2h
          </span>
        </div>
      </div>
      <p className="text-[11px] text-muted-foreground">
        Baseline: {fmtNum(d?.posts_toxicos_baseline_hora, 3)}/h · actual {fmtNum(d?.tasa_actual_hora, 3)}/h
      </p>
    </CardShell>
  );
}

// ========================================================================
// B07 — Growth attribution
// ========================================================================
export function CardB07({ bloque }: { bloque: BloqueBase & { data?: B07Data } }) {
  const d = bloque.data;
  const top = d?.top_posts ?? [];

  return (
    <CardShell
      code="B07"
      title="Growth attribution (Time-Decay)"
      pregunta="¿Qué posts generaron el crecimiento de mis seguidores?"
      fidelity="T3"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b07"
    >
      <div className="flex items-baseline gap-3" data-testid="b07-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {d?.delta_followers != null ? (d.delta_followers >= 0 ? "+" : "") + d.delta_followers : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">
          <Users2 className="inline h-3 w-3 mr-0.5" aria-hidden="true" />
          followers 14d
        </span>
      </div>
      {top.length > 0 ? (
        <ol className="space-y-1.5 text-[11px]">
          {top.slice(0, 3).map((p, i) => (
            <li key={p.post_id} className="flex items-center gap-2">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted font-heading text-[10px] font-bold">
                {i + 1}
              </span>
              <span className="flex-1 truncate text-muted-foreground">
                {p.platform} #{p.post_id}
              </span>
              <span className="font-medium tabular-nums">{fmtPct(p.contribution_pct, 0)}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-[11px] text-muted-foreground">Sin posts con contribución registrada</p>
      )}
    </CardShell>
  );
}

// ========================================================================
// B08 — Share of Voice
// ========================================================================
export function CardB08({ bloque }: { bloque: BloqueBase & { data?: B08Data } }) {
  const d = bloque.data;
  const self = d?.self_pct ?? null;
  const rivales = d?.rivales_pct ?? {};
  const data = self != null
    ? [
        { name: "Tú", value: self, fill: "hsl(var(--chart-accent))" },
        ...Object.entries(rivales)
          .slice(0, 4)
          .map(([name, value]) => ({
            name,
            value: Number(value),
            fill: "hsl(var(--chart-neutral))",
          })),
      ]
    : [];

  return (
    <CardShell
      code="B08"
      title="Share of Voice"
      pregunta="¿Qué % del espacio ocupo en mis temas clave vs rivales?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b08"
    >
      <div className="flex items-baseline gap-3" data-testid="b08-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {self != null ? fmtPct(self, 0) : <EmptyMetric />}
        </span>
        <span className="text-xs text-muted-foreground">
          {d?.topic_principal ? `en "${d.topic_principal}"` : "del topic principal"}
        </span>
      </div>
      {data.length > 0 && (
        <div className="h-24 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                innerRadius={24}
                outerRadius={40}
                paddingAngle={2}
                strokeWidth={0}
              >
                {data.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <RTooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v.toFixed(1)}%`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </CardShell>
  );
}

// ========================================================================
// B09 — Share/Like Ratio
// ========================================================================
const SEMAFORO_COLORS = {
  VERDE: { text: "text-[hsl(var(--chart-positive))]", bg: "bg-[hsl(var(--chart-positive))]", label: "Alta movilización" },
  AMARILLO: { text: "text-amber-600", bg: "bg-amber-500", label: "Moderada" },
  ROJO: { text: "text-[hsl(var(--chart-negative))]", bg: "bg-[hsl(var(--chart-negative))]", label: "Pasiva" },
} as const;

export function CardB09({ bloque }: { bloque: BloqueBase & { data?: B09Data } }) {
  const d = bloque.data;
  const semaforo = d?.semaforo;
  const cfg = semaforo ? SEMAFORO_COLORS[semaforo] : null;
  const ratio = d?.ratio_promedio;

  // gauge: normalize ratio to 0-1 where 0.1 = viral = 100%
  const pct = ratio != null ? Math.min((ratio / 0.1) * 100, 100) : 0;

  return (
    <CardShell
      code="B09"
      title="Share / Like Ratio"
      pregunta="¿Mi contenido se propaga o solo recibe likes pasivos?"
      fidelity={d?.nota_fidelity?.includes("parcial") ? "T2" : "T1"}
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b09"
    >
      <div className="flex items-baseline gap-3" data-testid="b09-headline">
        <span className={cn("font-heading text-3xl font-bold tabular-nums", cfg?.text)}>
          {ratio != null ? ratio.toFixed(4) : <EmptyMetric />}
        </span>
        {cfg && (
          <span className={cn("text-xs font-medium", cfg.text)}>
            {cfg.label}
          </span>
        )}
      </div>
      <div className="space-y-1">
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full transition-all", cfg?.bg || "bg-muted-foreground/30")}
            style={{ width: `${pct}%` }}
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Semáforo share/like"
          />
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
          <span>0</span>
          <span>0.05</span>
          <span>0.1 viral</span>
        </div>
      </div>
      {d?.n_posts != null && (
        <p className="text-[11px] text-muted-foreground">
          {d.n_posts} posts · {d.posts_virales?.length ?? 0} virales · estrato {d.estrato ?? "—"}
        </p>
      )}
    </CardShell>
  );
}

// ========================================================================
// B10 — Humanización Score — con drill-down drawer (T0.5)
// ========================================================================

interface HumanizacionDrawerProps {
  dirigenteId: number | string;
}

function HumanizacionDrawer({ dirigenteId }: HumanizacionDrawerProps) {
  const { data, isLoading, isError } = useHumanizacionExamples(dirigenteId, 5);

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="b10-drawer-loading">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 w-full animate-pulse rounded-md bg-muted" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div
        className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-destructive text-[12px]"
        role="alert"
        data-testid="b10-drawer-error"
      >
        <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
        <span>No se pudieron cargar los ejemplos. Intenta de nuevo más tarde.</span>
      </div>
    );
  }

  if (data.status === "insufficient_data") {
    return (
      <p className="text-[12px] text-muted-foreground py-4 text-center" data-testid="b10-drawer-empty">
        Datos insuficientes para mostrar ejemplos.
        {data.missing && data.missing.length > 0 && (
          <span className="block text-[11px] mt-1 font-mono">{data.missing.join(" · ")}</span>
        )}
      </p>
    );
  }

  return (
    <div className="space-y-5" data-testid="b10-drawer-content">
      {/* Two columns: institucional | humanizante */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Institucional */}
        <div className="space-y-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Mas institucional (penaliza)
          </h3>
          {data.top_institucional.length === 0 ? (
            <p className="text-[11px] text-muted-foreground">Sin posts institucionales detectados</p>
          ) : (
            data.top_institucional.map((post) => (
              <div
                key={post.post_id}
                className="rounded-md border border-border/60 bg-card p-2.5 space-y-1.5"
                data-testid="b10-post-institucional"
              >
                <p className="text-[11px] leading-snug text-foreground line-clamp-3">
                  {post.content_preview}
                </p>
                <div className="flex flex-wrap items-center gap-1">
                  <span className="font-heading text-[11px] font-bold text-muted-foreground tabular-nums">
                    Score: {post.score}
                  </span>
                  {post.factores.map((f, i) => (
                    <Badge key={i} variant="outline" className="text-[9px] px-1 py-0 h-4">
                      {f}
                    </Badge>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Humanizante */}
        <div className="space-y-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Mas humanizante (potenciar)
          </h3>
          {data.top_humanizante.length === 0 ? (
            <p className="text-[11px] text-muted-foreground">Sin posts humanizantes detectados</p>
          ) : (
            data.top_humanizante.map((post) => (
              <div
                key={post.post_id}
                className="rounded-md border border-[hsl(var(--chart-positive))]/30 bg-[hsl(var(--chart-positive))]/5 p-2.5 space-y-1.5"
                data-testid="b10-post-humanizante"
              >
                <p className="text-[11px] leading-snug text-foreground line-clamp-3">
                  {post.content_preview}
                </p>
                <div className="flex flex-wrap items-center gap-1">
                  <span className="font-heading text-[11px] font-bold text-[hsl(var(--chart-positive))] tabular-nums">
                    Score: {post.score}
                  </span>
                  {post.factores.map((f, i) => (
                    <Badge key={i} variant="outline" className="text-[9px] px-1 py-0 h-4 border-[hsl(var(--chart-positive))]/40 text-[hsl(var(--chart-positive))]">
                      {f}
                    </Badge>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Keywords usadas por el heurístico */}
      {data.keywords_usadas && (
        <div
          className="rounded-md border border-border/40 bg-muted/20 p-3 space-y-2"
          data-testid="b10-keywords"
        >
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Keywords del heurístico (transparencia metodológica)
          </h3>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 text-[11px]">
            <div>
              <p className="font-medium text-foreground mb-1">1ra persona (+)</p>
              <p className="text-muted-foreground font-mono leading-relaxed">
                {data.keywords_usadas.primera_persona.join(", ")}
              </p>
            </div>
            <div>
              <p className="font-medium text-foreground mb-1">Emojis humanos (+)</p>
              <p className="text-muted-foreground leading-relaxed">
                {data.keywords_usadas.emojis_humanos.join(" ")}
              </p>
            </div>
            <div>
              <p className="font-medium text-foreground mb-1">Institucional (−)</p>
              <p className="text-muted-foreground font-mono leading-relaxed">
                {data.keywords_usadas.institucional.slice(0, 8).join(", ")}...
              </p>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground">
            {data.n_posts_analizados} posts analizados · ventana {data.ventana_dias}d
          </p>
        </div>
      )}
    </div>
  );
}

export function CardB10({ bloque }: { bloque: BloqueBase & { data?: B10Data } }) {
  const d = bloque.data;
  const score = d?.score_0_100;
  const interp = d?.interpretacion ?? "—";

  const tone =
    interp === "Humano"
      ? "text-[hsl(var(--chart-positive))]"
      : interp === "Institucional"
        ? "text-muted-foreground"
        : "text-[hsl(var(--chart-accent))]";

  // Derive a numeric dirigente_id from bloque if possible — we pass it via the card prop
  // The drawer needs it; we use a data attribute set on the card shell.
  // Since BloqueBase does not include dirigente_id, CardB10 receives it separately.
  // We expose a separate export that accepts dirigenteId for the drill-down.
  // This base component is kept for backward compat without drill-down.

  return (
    <CardShell
      code="B10"
      title="Humanización Score"
      pregunta="¿Mi perfil se percibe humano o corporativo/institucional?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b10"
    >
      <div className="flex items-baseline gap-3" data-testid="b10-headline">
        <span className={cn("font-heading text-5xl font-bold tabular-nums leading-none", tone)}>
          {score != null ? score.toFixed(0) : <EmptyMetric />}
        </span>
        <div className="flex flex-col">
          <span className="text-xs text-muted-foreground">/100</span>
          <span className={cn("text-xs font-medium", tone)}>{interp}</span>
        </div>
      </div>
      {d?.factores && (
        <div className="space-y-1 text-[11px]">
          <div className="flex justify-between">
            <span className="text-muted-foreground">1ra persona</span>
            <span className="font-medium tabular-nums">{fmtPct(d.factores.primera_persona_pct ?? 0, 0)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Emojis</span>
            <span className="font-medium tabular-nums">{fmtPct(d.factores.emojis_pct ?? 0, 0)}</span>
          </div>
        </div>
      )}
    </CardShell>
  );
}

/**
 * CardB10WithDrilldown — versión con botón "Ver ejemplos" y Dialog.
 * Usar esta en la página de diagnóstico cuando se disponga del dirigenteId.
 */
export function CardB10WithDrilldown({
  bloque,
  dirigenteId,
}: {
  bloque: BloqueBase & { data?: B10Data };
  dirigenteId: number | string;
}) {
  const d = bloque.data;
  const score = d?.score_0_100;
  const interp = d?.interpretacion ?? "—";
  const [open, setOpen] = useState(false);

  const tone =
    interp === "Humano"
      ? "text-[hsl(var(--chart-positive))]"
      : interp === "Institucional"
        ? "text-muted-foreground"
        : "text-[hsl(var(--chart-accent))]";

  return (
    <CardShell
      code="B10"
      title="Humanización Score"
      pregunta="¿Mi perfil se percibe humano o corporativo/institucional?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b10"
    >
      <div className="flex items-baseline gap-3" data-testid="b10-headline">
        <span className={cn("font-heading text-5xl font-bold tabular-nums leading-none", tone)}>
          {score != null ? score.toFixed(0) : <EmptyMetric />}
        </span>
        <div className="flex flex-col">
          <span className="text-xs text-muted-foreground">/100</span>
          <span className={cn("text-xs font-medium", tone)}>{interp}</span>
        </div>
      </div>
      {d?.factores && (
        <div className="space-y-1 text-[11px]">
          <div className="flex justify-between">
            <span className="text-muted-foreground">1ra persona</span>
            <span className="font-medium tabular-nums">{fmtPct(d.factores.primera_persona_pct ?? 0, 0)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Emojis</span>
            <span className="font-medium tabular-nums">{fmtPct(d.factores.emojis_pct ?? 0, 0)}</span>
          </div>
        </div>
      )}

      {/* Drill-down trigger */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <button
            type="button"
            className="mt-1 w-full rounded-md border border-border/60 bg-muted/30 py-1.5 text-[11px] font-medium text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            data-testid="b10-ver-ejemplos-btn"
          >
            Ver ejemplos
          </button>
        </DialogTrigger>
        <DialogContent
          className="max-w-2xl max-h-[85vh] overflow-y-auto"
          data-testid="b10-drawer"
        >
          <DialogHeader>
            <DialogTitle className="font-heading text-base">
              B10 Humanización — ejemplos de posts
              {score != null && (
                <span className={cn("ml-2 text-sm font-normal", tone)}>
                  Score global: {score.toFixed(0)} · {interp}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          <HumanizacionDrawer dirigenteId={dirigenteId} />
        </DialogContent>
      </Dialog>
    </CardShell>
  );
}

// ========================================================================
// Skeleton para loading state (replica card shell)
// ========================================================================
export function CardSkeleton() {
  return (
    <div className="card-elevated flex h-[240px] flex-col gap-3 rounded-lg border border-border/60 bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="space-y-1.5">
          <div className="h-3 w-8 animate-pulse rounded bg-muted" />
          <div className="h-4 w-40 animate-pulse rounded bg-muted" />
        </div>
        <div className="h-6 w-6 animate-pulse rounded bg-muted" />
      </div>
      <div className="h-10 w-32 animate-pulse rounded bg-muted" />
      <div className="mt-auto h-24 w-full animate-pulse rounded bg-muted" />
    </div>
  );
}
