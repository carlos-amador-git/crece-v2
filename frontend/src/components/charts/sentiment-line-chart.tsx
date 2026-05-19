"use client";

import { useState } from "react";
import {
  LineChart, Line,
  BarChart, Bar,
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { SentimentTrend } from "@/lib/api/types";

type ChartType = "line" | "bar" | "area";
type ChartMode = "pct" | "abs";

interface SentimentLineChartProps {
  data: SentimentTrend[];
  onIncludeRtsChange?: (value: boolean) => void;
  showRtsToggle?: boolean;
}

const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: "line", label: "Línea" },
  { value: "bar", label: "Barras" },
  { value: "area", label: "Área apilada" },
];

const CHART_MODES: { value: ChartMode; label: string }[] = [
  { value: "pct", label: "%" },
  { value: "abs", label: "N" },
];

const SERIES_PCT = [
  { key: "positive_pct", name: "Positivo", color: "hsl(var(--chart-positive))" },
  { key: "negative_pct", name: "Negativo", color: "hsl(var(--chart-negative))" },
  { key: "neutral_pct",  name: "Neutral",  color: "hsl(var(--chart-neutral))" },
];

const SERIES_ABS = [
  { key: "positive", name: "Positivo", color: "hsl(var(--chart-positive))" },
  { key: "negative", name: "Negativo", color: "hsl(var(--chart-negative))" },
  { key: "neutral",  name: "Neutral",  color: "hsl(var(--chart-neutral))" },
];

export function SentimentLineChart({ data, onIncludeRtsChange, showRtsToggle = false }: SentimentLineChartProps) {
  // Persistir preferencia en localStorage (cross-audit Gemini · stacked area opcional)
  const [chartType, setChartType] = useState<ChartType>(() => {
    if (typeof window === "undefined") return "line";
    const saved = window.localStorage.getItem("sentiment-chart-kind");
    return (saved === "bar" || saved === "area" || saved === "line") ? saved : "line";
  });
  const [chartMode, setChartMode] = useState<ChartMode>("pct");
  const [includeRts, setIncludeRts] = useState(false);

  const handleChartTypeChange = (t: ChartType) => {
    setChartType(t);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("sentiment-chart-kind", t);
    }
  };

  const series = chartMode === "pct" ? SERIES_PCT : SERIES_ABS;

  // Compute absolute counts from post_count × pct when in abs mode
  const chartData = chartMode === "abs"
    ? data.map((d) => ({
        ...d,
        positive: Math.round(d.post_count * d.positive_pct / 100),
        negative: Math.round(d.post_count * d.negative_pct / 100),
        neutral:  Math.round(d.post_count * d.neutral_pct  / 100),
      }))
    : data;

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {CHART_TYPES.map((ct) => (
            <button
              key={ct.value}
              type="button"
              onClick={() => handleChartTypeChange(ct.value)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                chartType === ct.value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {ct.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {showRtsToggle && (
            <button
              type="button"
              onClick={() => {
                const next = !includeRts;
                setIncludeRts(next);
                onIncludeRtsChange?.(next);
              }}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                includeRts
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
              title={includeRts ? "Ocultando RTs" : "Mostrando sin RTs"}
            >
              RT
            </button>
          )}
          {CHART_MODES.map((cm) => (
            <button
              key={cm.value}
              type="button"
              onClick={() => setChartMode(cm.value)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                chartMode === cm.value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {cm.label}
            </button>
          ))}
        </div>
      </div>

      <div className="w-full h-[300px] min-w-0">
        <ResponsiveContainer width="100%" height="100%">
        {chartType === "bar" ? (
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} tickFormatter={(v) => { const d = new Date(v); return `${d.getDate()}/${d.getMonth()+1}`; }} />
            <YAxis tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} width={40} />
            <Tooltip contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "var(--radius)", color: "hsl(var(--popover-foreground))", fontSize: 12 }} labelFormatter={(l) => new Date(l).toLocaleDateString("es-MX", { month: "short", day: "numeric" })} />
            <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} />
            {series.map((s) => (
              <Bar key={s.key} dataKey={s.key} name={s.name} fill={s.color} stackId="a" radius={[2, 2, 0, 0]} />
            ))}
          </BarChart>
        ) : chartType === "area" ? (
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <defs>
              {series.map((s) => (
                <linearGradient key={`grad-${s.key}`} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={s.color} stopOpacity={0.85} />
                  <stop offset="95%" stopColor={s.color} stopOpacity={0.35} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} tickFormatter={(v) => { const d = new Date(v); return `${d.getDate()}/${d.getMonth()+1}`; }} />
            <YAxis tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} width={40} />
            <Tooltip contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "var(--radius)", color: "hsl(var(--popover-foreground))", fontSize: 12 }} labelFormatter={(l) => new Date(l).toLocaleDateString("es-MX", { month: "short", day: "numeric" })} />
            <Legend wrapperStyle={{ fontSize: 12 }} iconType="square" iconSize={10} />
            {series.map((s) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                stroke={s.color}
                strokeWidth={1.5}
                fill={`url(#grad-${s.key})`}
                stackId="a"
                fillOpacity={1}
              />
            ))}
          </AreaChart>
        ) : (
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} tickFormatter={(v) => { const d = new Date(v); return `${d.getDate()}/${d.getMonth()+1}`; }} />
            <YAxis tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} tickLine={false} axisLine={false} width={40} />
            <Tooltip contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "var(--radius)", color: "hsl(var(--popover-foreground))", fontSize: 12 }} labelFormatter={(l) => new Date(l).toLocaleDateString("es-MX", { month: "short", day: "numeric" })} />
            <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} />
            {series.map((s) => (
              <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={s.color} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            ))}
          </LineChart>
        )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
