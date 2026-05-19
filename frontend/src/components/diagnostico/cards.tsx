"use client";

import { useState } from "react";
import Link from "next/link";
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
import { CheckCircle2, AlertCircle, Flame, Minus, TrendingUp, Users2 } from "lucide-react";
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

// Benchmark empírico MX D-19 · Zenodo v1 (p25-p75 política mexicana)
const BENCHMARK_MX_RANGE_LABEL = "0.01%–1.1%";

type SignalVariant = "positive" | "negative" | "warning" | "neutral";

// ========================================================================
// B01 — Conexión con tu audiencia
// ========================================================================
export function CardB01({ bloque }: { bloque: BloqueBase & { data?: B01Data } }) {
  const d = bloque.data;
  const platforms = d?.er_por_plataforma ? Object.entries(d.er_por_plataforma) : [];

  const chartData = platforms.map(([platform, p]) => ({
    platform: platform.toUpperCase(),
    actual: Number(p.er_actual_pct ?? 0),
    min: Number(p.er_esperado_rango_pct?.[0] ?? 0),
  }));

  const avgActual = platforms.length
    ? platforms.reduce((acc, [, p]) => acc + (p.er_actual_pct ?? 0), 0) / platforms.length
    : null;
  const avgMin = platforms.length
    ? platforms.reduce((acc, [, p]) => acc + (p.er_esperado_rango_pct?.[0] ?? 0), 0) /
      platforms.length
    : null;

  let signal: { label: string; variant: SignalVariant } | undefined;
  if (avgActual != null && avgMin != null) {
    const ratio = avgActual / avgMin;
    if (ratio >= 1.5) signal = { label: "Sobresaliente", variant: "positive" };
    else if (ratio >= 1.0) signal = { label: "Saludable", variant: "positive" };
    else if (ratio >= 0.7) signal = { label: "Bajo", variant: "warning" };
    else signal = { label: "Crítico", variant: "negative" };
  }

  return (
    <CardShell
      code="B01"
      title="Conexión con tu audiencia"
      pregunta="¿Qué tanto interactúa la gente con tus publicaciones comparado con otros políticos de tu tamaño?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b01"
      signal={signal}
    >
      <div className="flex items-baseline gap-3" data-testid="b01-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {avgActual != null ? fmtPct(avgActual) : <EmptyMetric />}
        </span>
        {avgMin != null && (
          <span className="text-xs text-muted-foreground">
            vs {fmtPct(avgMin)} promedio
          </span>
        )}
      </div>
      <p className="text-[11px] text-muted-foreground leading-tight">
        {avgActual != null && avgMin != null && avgMin > 0 ? (
          <>
            Generas{" "}
            <span className="font-medium text-foreground">
              {(avgActual / avgMin).toFixed(1)} veces
            </span>{" "}
            más interacción que otros políticos con tu mismo alcance.
          </>
        ) : (
          <>Aún no hay suficientes posts para comparar contra el promedio político.</>
        )}
      </p>

      <div className="h-28 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis
              dataKey="platform"
              tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <RTooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v.toFixed(2)}%`} />
            <Bar dataKey="actual" fill="hsl(var(--chart-accent))" name="Tu conexión" radius={[3, 3, 0, 0]} />
            <Bar dataKey="min" fill="hsl(var(--chart-neutral))" name="Promedio" radius={[3, 3, 0, 0]} opacity={0.5} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CardShell>
  );
}

// ========================================================================
// B02 — Alcance fuera de tu red
// ========================================================================
const CAT_LABELS = ["Inactivo", "Base", "Creciendo", "Viral", "Tendencia", "Nacional", "Global"];

export function CardB02({ bloque }: { bloque: BloqueBase & { data?: B02Data } }) {
  const d = bloque.data;
  const cat = d?.max_categoria ?? 0;
  const label = CAT_LABELS[Math.min(cat, 6)] ?? "—";
  const pct = d?.views_breakout_pct ?? 0;

  let signal: { label: string; variant: SignalVariant } | undefined;
  if (cat >= 4) signal = { label: "Alta Viralidad", variant: "positive" };
  else if (cat >= 2) signal = { label: "Creciendo", variant: "positive" };
  else signal = { label: "Limitado", variant: "neutral" };

  return (
    <CardShell
      code="B02"
      title="Alcance fuera de tu red"
      pregunta="¿Tus publicaciones están llegando a personas que aún no te siguen?"
      fidelity={d?.fidelity || "T1"}
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b02"
      signal={signal}
    >
      <div className="flex flex-col gap-1" data-testid="b02-headline">
        <span className="font-heading text-3xl font-bold leading-tight">
          {label}
        </span>
        <span className="text-xs font-medium text-muted-foreground">Nivel {cat} de 6</span>
      </div>
      <div className="space-y-1.5">
        <div className="flex justify-between text-[11px]">
          <span className="text-muted-foreground">Progreso hacia impacto nacional</span>
          <span className="font-medium tabular-nums">{Math.min((cat / 5) * 100, 100).toFixed(0)}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-[hsl(var(--chart-accent))] transition-all"
            style={{ width: `${Math.min((cat / 5) * 100, 100)}%` }}
            role="progressbar"
          />
        </div>
        <p className="text-[11px] text-muted-foreground pt-1 leading-snug">
          El <span className="font-medium text-foreground">{pct.toFixed(1)}%</span> de tus visualizaciones vienen de personas que <span className="underline decoration-dotted underline-offset-2">no son tus seguidores</span>.
        </p>
      </div>
    </CardShell>
  );
}

// ========================================================================
// B03 — Salud de tus publicaciones
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
  
  let signal: { label: string; variant: SignalVariant } | undefined;
  const insignia = conteo.INSIGNIA ?? 0;
  const crisis = conteo.CRISIS ?? 0;
  const muerta = conteo.MUERTA ?? 0;
  const total = insignia + crisis + (conteo.VANIDAD ?? 0) + muerta;
  if (crisis > insignia) signal = { label: "Riesgo Alto", variant: "negative" };
  else if (total > 0 && muerta / total > 0.5) signal = { label: "Esfuerzo Sin Retorno", variant: "warning" };
  else if (insignia > crisis * 2) signal = { label: "Contenido Fuerte", variant: "positive" };
  else signal = { label: "Mezclado", variant: "warning" };

  const scatterData = (d?.posts ?? []).slice(0, 60).map((p) => ({
    x: p.engagement_rate,
    y: p.sentiment_score,
    cuadrante: p.cuadrante,
  }));

  return (
    <CardShell
      code="B03"
      title="Salud de tus publicaciones"
      pregunta="Clasificación de tus posts según su impacto y el sentimiento de la gente."
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b03"
      signal={signal}
    >
      <div className="grid grid-cols-2 gap-1.5 text-[11px]" data-testid="b03-headline">
        {[
          { key: "INSIGNIA", label: "Éxitos" },
          { key: "CRISIS", label: "Riesgos" },
          { key: "VANIDAD", label: "Neutros" },
          { key: "MUERTA", label: "Sin Eco" }
        ].map((item) => (
          <div
            key={item.key}
            className="rounded-md border border-border/50 bg-card px-2 py-1.5"
            style={{ borderLeft: `3px solid ${CUADRANTE_COLORS[item.key]}` }}
          >
            <div className="font-heading text-lg font-bold tabular-nums leading-none">
              {conteo[item.key] ?? 0}
            </div>
            <div className="text-[9px] uppercase tracking-wider text-muted-foreground font-semibold">
              {item.label}
            </div>
          </div>
        ))}
      </div>
      <div className="h-20 w-full opacity-60">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
            <XAxis type="number" dataKey="x" hide />
            <YAxis type="number" dataKey="y" domain={[-1, 1]} hide />
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
    </CardShell>
  );
}

// ========================================================================
// B04 — ¿Cómo vas frente a la competencia?
// ========================================================================
export function CardB04({ bloque }: { bloque: BloqueBase & { data?: B04Data } }) {
  const d = bloque.data;
  const self = d?.self;
  const rivales = d?.rivales ?? [];
  const isProxiesDemo = d?.origen_competidores === "proxies_s2";
  const rivalesSinData = rivales.length > 0 && rivales.every((r) => r.status !== "ok");
  const isDemo = isProxiesDemo || rivalesSinData;

  const rows = self
    ? [
        { name: "Tú", er: self.er_avg_pct ?? 0, isSelf: true },
        ...rivales.slice(0, 4).map((r) => ({
          name: r.full_name?.split(" ")[0] ?? `Rival ${r.dirigente_id}`,
          er: r.er_avg_pct ?? 0,
          isSelf: false,
        })),
      ].sort((a, b) => b.er - a.er)
    : [];

  const myRank = rows.findIndex(r => r.isSelf) + 1;
  const allZeroEr = rows.length > 0 && rows.every((r) => !r.er);
  let signal: { label: string; variant: SignalVariant } | undefined;
  if (allZeroEr || rivalesSinData) {
    signal = { label: "Sin datos suficientes", variant: "warning" };
  } else if (myRank === 1) {
    signal = { label: "Líder", variant: "positive" };
  } else if (myRank <= 3) {
    signal = { label: "Top 3", variant: "positive" };
  } else {
    signal = { label: "Rezagado", variant: "warning" };
  }

  const demoBanner = isDemo ? (
    <div className="rounded-md border border-amber-300/60 bg-amber-50/60 px-3 py-1.5 text-[10px] text-amber-800 leading-tight">
      <span className="font-bold uppercase tracking-wider">Modo Demo:</span> Rivalidades de ejemplo.
    </div>
  ) : null;

  return (
    <CardShell
      code="B04"
      title="Frente a la competencia"
      pregunta="Comparativa directa de tu nivel de conexión contra tus rivales."
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b04"
      persistentBanner={demoBanner}
      signal={signal}
    >
      <div className="flex items-baseline gap-2" data-testid="b04-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          #{myRank}
        </span>
        <span className="text-sm font-medium text-muted-foreground">
          entre tus {rows.length - 1} competidores directos
        </span>
      </div>
      <div className="h-28 w-full mt-1">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))", fontWeight: 500 }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Bar dataKey="er" radius={[0, 2, 2, 0]} barSize={12}>
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
// B05 — Sentimiento de la audiencia
// ========================================================================
// Ekman-6 alineado a lo que el NLP (pysentimiento) realmente emite.
// Antes el frontend pedía `trust` y `anticipation` que el modelo nunca pobla → radar
// colapsaba al centro y la señal "Hostilidad" venía de ratio_trust_anger=0/anger.
// D-EKMAN-1 (2026-05-12).
const PLUTCHIK_ORDER = ["joy", "anger", "sadness", "fear", "disgust", "surprise"] as const;

// Diccionario defensivo case-insensitive con fallback al label original
const EMOCION_ES: Record<string, string> = {
  joy: "Alegría",
  anger: "Enojo",
  sadness: "Tristeza",
  fear: "Miedo",
  disgust: "Asco",
  surprise: "Sorpresa",
};
function emocionLabel(k: string): string {
  const lower = String(k ?? "").toLowerCase();
  return EMOCION_ES[lower] ?? (k.charAt(0).toUpperCase() + k.slice(1).toLowerCase());
}

export function CardB05({ bloque }: { bloque: BloqueBase & { data?: B05Data } }) {
  const d = bloque.data;
  const em = d?.emociones_promedio ?? {};
  const chart = PLUTCHIK_ORDER.map((k) => ({
    emocion: emocionLabel(k),
    valor: Number(em[k] ?? 0),
  }));

  // D-EKMAN-1: ratio joy/anger (antes trust/anger; trust no se emite por el NLP).
  // Backend devuelve ambos campos como alias durante migración.
  const ratio = (d as { ratio_joy_anger?: number | null })?.ratio_joy_anger ?? d?.ratio_trust_anger;
  let signal: { label: string; variant: SignalVariant } | undefined;
  if (ratio != null) {
    if (ratio >= 2) signal = { label: "Gran Alegría", variant: "positive" };
    else if (ratio >= 1) signal = { label: "Positivo", variant: "positive" };
    else if (ratio >= 0.5) signal = { label: "Tenso", variant: "warning" };
    else signal = { label: "Hostilidad", variant: "negative" };
  }

  return (
    <CardShell
      code="B05"
      title="Sentimiento de la audiencia"
      pregunta="¿Qué emociones predominan en los comentarios de tu gente?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b05"
      signal={signal}
    >
      <div className="flex items-baseline gap-2" data-testid="b05-headline">
        {ratio != null ? (
          <p className="text-sm leading-snug text-foreground">
            La <span className="font-semibold">Alegría</span> supera al{" "}
            <span className="font-semibold">Enojo</span>{" "}
            <span className="font-heading text-xl font-bold tabular-nums">{ratio.toFixed(1)}</span> a 1.
          </p>
        ) : (
          <EmptyMetric />
        )}
      </div>
      <div className="h-28 w-full mt-1">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chart}>
            <PolarGrid stroke="hsl(var(--border))" />
            <PolarAngleAxis dataKey="emocion" tick={{ fontSize: 8, fill: "hsl(var(--muted-foreground))" }} />
            <Radar dataKey="valor" stroke="hsl(var(--chart-accent))" fill="hsl(var(--chart-accent))" fillOpacity={0.4} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </CardShell>
  );
}

// ========================================================================
// B06 — Semáforo de crisis
// ========================================================================
export function CardB06({ bloque }: { bloque: BloqueBase & { data?: B06Data } }) {
  const d = bloque.data;
  const spike = d?.spike_detected ?? false;
  const severity = d?.severity ?? 0;

  const level = !spike ? "verde" : severity >= 0.7 ? "rojo" : severity >= 0.4 ? "amarillo" : "verde";
  const styles = {
    verde: { variant: "positive" as const, label: "Todo en orden", text: "text-[hsl(var(--chart-positive))]" },
    amarillo: { variant: "warning" as const, label: "Vigilancia", text: "text-amber-600" },
    rojo: { variant: "negative" as const, label: "CRISIS ACTIVA", text: "text-[hsl(var(--chart-negative))]" },
  }[level];

  return (
    <CardShell
      code="B06"
      title="Semáforo de crisis"
      pregunta="Detección automática de ataques o picos de toxicidad en tiempo real."
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b06"
      signal={{ label: styles.label, variant: styles.variant }}
    >
      <div className="flex flex-col gap-2 rounded-md border border-border/50 bg-muted/20 p-3 mt-1">
        <div className="flex items-center gap-2">
          {spike ? <Flame className={cn("h-5 w-5", styles.text)} /> : <CheckCircle2 className={cn("h-5 w-5", styles.text)} />}
          <span className={cn("font-heading text-lg font-bold", styles.text)}>
            {level === "verde" ? "Estable" : level === "amarillo" ? "Alerta Leve" : "Impacto Alto"}
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground leading-tight">
          {spike
            ? `Alerta: ${d?.posts_toxicos_2h ?? 0} comentarios negativos inusuales en las últimas 2 horas.`
            : "No se detectan ataques organizados ni comentarios negativos fuera de lo normal."}
        </p>
      </div>
    </CardShell>
  );
}

// ========================================================================
// B07 — De dónde viene tu crecimiento
// ========================================================================
export function CardB07({ bloque }: { bloque: BloqueBase & { data?: B07Data } }) {
  const d = bloque.data;
  const top = d?.top_posts ?? [];
  const delta = d?.delta_followers ?? 0;

  return (
    <CardShell
      code="B07"
      title="Nuevos seguidores"
      pregunta="¿Qué publicaciones están atrayendo a más personas a seguirte?"
      fidelity="T3"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b07"
      signal={delta > 0 ? { label: "Creciendo", variant: "positive" } : { label: "Estancado", variant: "neutral" }}
    >
      <div className="flex items-baseline gap-2" data-testid="b07-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {delta >= 0 ? "+" : ""}{delta}
        </span>
        <span className="text-xs text-muted-foreground">seguidores en 14 días</span>
      </div>
      {top.length > 0 ? (
        <div className="space-y-2 mt-2">
          <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Posts con más impacto:</p>
          <ol className="space-y-1.5 text-[11px]">
            {top.slice(0, 3).map((p, i) => {
              const platformLabel = p.platform
                ? p.platform.charAt(0).toUpperCase() + p.platform.slice(1).toLowerCase()
                : "—";
              const fecha = p.published_at
                ? new Date(p.published_at).toLocaleDateString("es-MX", {
                    day: "numeric",
                    month: "short",
                  })
                : "";
              return (
                <li key={p.post_id} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-muted font-heading text-[10px] font-bold">
                    {i + 1}
                  </span>
                  <span className="flex-1 truncate text-muted-foreground">
                    Post en <span className="font-medium text-foreground">{platformLabel}</span>
                    {fecha && <span className="text-muted-foreground/70"> · {fecha}</span>}
                  </span>
                  <span className="font-bold text-[hsl(var(--chart-positive))]">{fmtPct(p.contribution_pct, 0)}</span>
                </li>
              );
            })}
          </ol>
        </div>
      ) : (
        <p className="text-[11px] text-muted-foreground italic">Sin datos de publicaciones individuales.</p>
      )}
    </CardShell>
  );
}

// ========================================================================
// B08 — Tu peso en la conversación
// ========================================================================
export function CardB08({ bloque }: { bloque: BloqueBase & { data?: B08Data } }) {
  const d = bloque.data;
  const self = d?.self_pct ?? null;
  const data = self != null
    ? [
        { name: "Tú", value: self, fill: "hsl(var(--chart-accent))" },
        { name: "Otros", value: 100 - self, fill: "hsl(var(--chart-neutral))" }
      ]
    : [];

  return (
    <CardShell
      code="B08"
      title="Tu peso en la charla"
      pregunta="¿Qué porcentaje de la conversación sobre tus temas clave te pertenece?"
      fidelity="T2"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b08"
      signal={self && self > 20 ? { label: "Relevante", variant: "positive" } : { label: "Baja Voz", variant: "neutral" }}
    >
      <div className="flex items-baseline gap-2" data-testid="b08-headline">
        <span className="font-heading text-3xl font-bold tabular-nums">
          {self != null ? fmtPct(self, 0) : <EmptyMetric />}
        </span>
        <span className="text-[11px] text-muted-foreground leading-snug">
          de toda la conversación sobre{" "}
          <span className="font-medium text-foreground">"{d?.topic_principal ?? "tu tema principal"}"</span>.
        </span>
      </div>
      {data.length > 0 && (
        <div className="h-24 w-full flex justify-center mt-1">
          <ResponsiveContainer width="60%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" innerRadius={20} outerRadius={35} strokeWidth={0}>
                {data.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </CardShell>
  );
}

// ========================================================================
// B09 — Poder de movilización
// ========================================================================
const SEMAFORO_MOVL = {
  VERDE: { variant: "positive" as const, label: "Viralizador" },
  AMARILLO: { variant: "warning" as const, label: "Activo" },
  ROJO: { variant: "negative" as const, label: "Pasivo" },
} as const;

export function CardB09({ bloque }: { bloque: BloqueBase & { data?: B09Data } }) {
  const d = bloque.data;
  const semaforo = d?.semaforo;
  const cfg = semaforo ? SEMAFORO_MOVL[semaforo] : null;
  const ratio = d?.ratio_promedio;
  const pct = ratio != null ? Math.min((ratio / 0.1) * 100, 100) : 0;

  return (
    <CardShell
      code="B09"
      title="Poder de movilización"
      pregunta="¿Tu gente solo da 'likes' o realmente comparte tu mensaje?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b09"
      signal={cfg ? { label: cfg.label, variant: cfg.variant } : undefined}
    >
      <div className="flex items-baseline gap-2 mt-1" data-testid="b09-headline">
        {ratio != null ? (
          <>
            <span className="font-heading text-3xl font-bold tabular-nums">
              {Math.max(1, Math.min(10, Math.round(pct / 10)))}
            </span>
            <span className="text-sm font-medium text-muted-foreground">/ 10 Poder Viral</span>
          </>
        ) : (
          <EmptyMetric />
        )}
      </div>
      <div className="space-y-1.5 mt-2">
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-[hsl(var(--chart-accent))] transition-all" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-[10px] text-muted-foreground leading-tight italic">
          Mide qué tanto tu gente comparte tu contenido, no solo lo lee. Alto = crecimiento orgánico sin pagar publicidad.
        </p>
      </div>
    </CardShell>
  );
}

// ========================================================================
// B10 — Tu toque humano
// ========================================================================
export function CardB10({ bloque }: { bloque: BloqueBase & { data?: B10Data } }) {
  const d = bloque.data;
  const score = d?.score_0_100;
  const interp = d?.interpretacion ?? "—";
  // D-HUMANIZ-NEUTRO-1: posts sin marcador detectable se reportan aparte
  const nConMarcador = (d as { n_posts_con_marcador?: number })?.n_posts_con_marcador;
  const nSinMarcador = (d as { n_posts_sin_marcador?: number })?.n_posts_sin_marcador;
  const nTotal = d?.n_posts;

  let signal: { label: string; variant: SignalVariant } | undefined;
  let benchmarkText: string | undefined;
  if (score != null) {
    if (score >= 70) {
      signal = { label: "Muy Humano", variant: "positive" };
      benchmarkText = "muy por encima del promedio";
    } else if (score >= 40) {
      signal = { label: "Equilibrado", variant: "positive" };
      benchmarkText = "por encima del promedio institucional";
    } else {
      signal = { label: "Distante", variant: "warning" };
      benchmarkText = "por debajo del promedio · se percibe acartonado";
    }
  }

  return (
    <CardShell
      code="B10"
      title="Tu toque humano"
      pregunta="¿Qué tan 'político tradicional' o 'persona real' se percibe tu cuenta?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b10"
      signal={signal}
    >
      <div className="space-y-1" data-testid="b10-headline">
        <p className="text-sm leading-snug text-foreground">
          Tu audiencia te percibe como{" "}
          <span className="font-semibold italic">{interp}</span>.
        </p>
        {benchmarkText && (
          <p className="text-[11px] text-muted-foreground leading-tight">
            {benchmarkText}.
          </p>
        )}
        {nConMarcador != null && nSinMarcador != null && nTotal != null && nSinMarcador > 0 && (
          <p className="text-[10px] text-muted-foreground/80 leading-tight italic">
            Calculado sobre {nConMarcador} de {nTotal} posts con marcador detectable
            {" "}({nSinMarcador} neutros sin clasificar).
          </p>
        )}
      </div>
    </CardShell>
  );
}

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
      <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-destructive text-[12px]">
        <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
        <span>No se pudieron cargar los ejemplos.</span>
      </div>
    );
  }

  if (data.status === "insufficient_data") {
    return (
      <p className="text-[12px] text-muted-foreground py-4 text-center">
        Datos insuficientes para mostrar ejemplos.
      </p>
    );
  }

  return (
    <div className="space-y-5" data-testid="b10-drawer-content">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">Más Institucional</h3>
          {data.top_institucional.map((post) => (
            <div key={post.post_id} className="rounded-md border border-border/60 bg-card p-2.5 text-[11px]">
              {post.content_preview}
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-[hsl(var(--chart-positive))]">Más Humano</h3>
          {data.top_humanizante.map((post) => (
            <div key={post.post_id} className="rounded-md border border-[hsl(var(--chart-positive))]/30 bg-[hsl(var(--chart-positive))]/5 p-2.5 text-[11px]">
              {post.content_preview}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

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

  let signal: { label: string; variant: SignalVariant } | undefined;
  if (score != null) {
    if (score >= 70) signal = { label: "Muy Humano", variant: "positive" };
    else if (score >= 40) signal = { label: "Equilibrado", variant: "positive" };
    else signal = { label: "Institucional", variant: "warning" };
  }

  return (
    <CardShell
      code="B10"
      title="Tu toque humano"
      pregunta="¿Qué tan 'político tradicional' o 'persona real' se percibe tu cuenta?"
      fidelity="T1"
      status={bloque.status}
      missing={bloque.missing}
      testId="card-b10"
      signal={signal}
    >
      <div className="flex items-baseline gap-2" data-testid="b10-headline">
        <span className="font-heading text-4xl font-bold tabular-nums leading-none">
          {score != null ? score.toFixed(0) : <EmptyMetric />}
        </span>
        <span className="text-sm font-medium text-muted-foreground">/ 100</span>
      </div>
      <p className="text-[11px] text-muted-foreground leading-snug mt-1">
        Tu perfil se percibe principalmente como <span className="font-bold text-foreground italic">{interp}</span>.
      </p>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <button type="button" className="mt-2 w-full rounded border border-border/60 bg-muted/30 py-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground hover:bg-muted/60 transition-colors">
            Ver ejemplos reales
          </button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading">Ejemplos de Humanización</DialogTitle>
          </DialogHeader>
          <HumanizacionDrawer dirigenteId={dirigenteId} />
        </DialogContent>
      </Dialog>
    </CardShell>
  );
}

export function CardSkeleton() {
  return (
    <div className="flex h-[240px] flex-col gap-3 rounded-lg border border-border/60 bg-card p-4 animate-pulse">
      <div className="h-4 w-1/3 bg-muted rounded" />
      <div className="h-8 w-1/2 bg-muted rounded" />
      <div className="flex-1 bg-muted/50 rounded" />
    </div>
  );
}
