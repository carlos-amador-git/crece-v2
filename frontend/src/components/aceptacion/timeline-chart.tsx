"use client";

/**
 * Sprint B · PLAN-2026-05-17-fans-dashboard.md
 *
 * ComposedChart con doble eje Y:
 * - Eje izquierdo: barras de reactions por día
 * - Eje derecho: línea de comments por día
 *
 * Ventana confiable (window_quality === 'complete') = banda visual; los últimos
 * 3d aparecen con punto/línea punteados y tooltip "datos acumulando".
 *
 * Mobile fallback (<640px): vista stacked area sin dual axis para no romper.
 */

import { useMemo, useEffect, useState } from "react";
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Legend,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  AreaChart,
  Area,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useWatchedTimeline,
  type TimelinePoint,
} from "@/lib/api/hooks/use-watched-profiles";
import { formatNumber } from "@/lib/utils";

interface TimelineChartProps {
  dirigenteId: number;
  days?: number;
  /** D-PLATFORM-SELECTOR-2026-05-21 · None=cross */
  platform?: string;
}

function useIsMobile(breakpoint = 640) {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, [breakpoint]);
  return isMobile;
}

function formatTickDate(d: string) {
  // d = "YYYY-MM-DD"
  const [, m, day] = d.split("-");
  return `${day}/${m}`;
}

export function TimelineChart({ dirigenteId, days = 44, platform }: TimelineChartProps) {
  const { data, isLoading, isError } = useWatchedTimeline(dirigenteId, days, platform);
  const isMobile = useIsMobile();

  const { points, partialBandStart, partialBandEnd, yCap, hasOutliers } = useMemo(() => {
    const list: TimelinePoint[] = data ?? [];
    const firstPartial = list.find((p) => p.window_quality === "partial");
    const lastPartial = [...list].reverse().find((p) => p.window_quality === "partial");

    // CEO 2026-05-21 · outlier truncation N2 · techo Y = p95 × 1.05.
    // Barras con n_reactions > cap se truncan visualmente y se colorean ámbar.
    // Badge "↑ N" sobre cada barra outlier muestra el valor real.
    const reactions = list.map((p) => p.n_reactions).filter((n) => n > 0).sort((a, b) => a - b);
    let yCapValue: number | null = null;
    let outliersExist = false;
    if (reactions.length >= 5) {
      // P95 lineal interpolation (igual a PERCENTILE_CONT 0.95 de PostgreSQL).
      const idx = (reactions.length - 1) * 0.95;
      const lo = Math.floor(idx);
      const hi = Math.ceil(idx);
      const p95 = lo === hi ? reactions[lo] : reactions[lo] + (reactions[hi] - reactions[lo]) * (idx - lo);
      yCapValue = Math.ceil(p95 * 1.05);
      outliersExist = reactions.some((r) => r > yCapValue!);
    }

    return {
      points: list,
      partialBandStart: firstPartial?.date ?? null,
      partialBandEnd: lastPartial?.date ?? null,
      yCap: yCapValue,
      hasOutliers: outliersExist,
    };
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Engagement diario</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-72 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Engagement diario</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">No se pudo cargar el timeline.</p>
        </CardContent>
      </Card>
    );
  }

  if (!points.length) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Engagement diario</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No hay actividad registrada en los últimos {days} días.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-baseline justify-between">
          <CardTitle className="text-base font-semibold">Engagement diario</CardTitle>
          <span
            className="text-xs text-muted-foreground"
            title="Banda gris derecha (últimos 3d): posts publicados recientemente que aún están acumulando reactions. Zonas vacías a la izquierda: días fuera de la cobertura RADAR (sin reactors individuales capturados aunque haya posts publicados con likes públicos en BD). Barras ámbar: días con engagement excepcional (>p95) truncadas para mejorar legibilidad — el valor real aparece sobre la barra."
          >
            últimos {days}d · banda gris = acumulando · zonas vacías = sin cobertura RADAR
            {hasOutliers ? " · barras ámbar = picos virales (>p95)" : ""}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={isMobile ? 240 : 300}>
          {isMobile ? (
            <AreaChart
              data={points}
              margin={{ top: 10, right: 12, left: 0, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                tickFormatter={formatTickDate}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatNumber(v)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                  fontSize: 12,
                }}
                labelFormatter={(d: string) => `Día ${formatTickDate(d)}`}
              />
              <Area
                type="monotone"
                dataKey="n_reactions"
                stackId="1"
                stroke="hsl(var(--primary))"
                fill="hsl(var(--primary) / 0.25)"
                name="Reactions"
              />
              <Area
                type="monotone"
                dataKey="n_comments"
                stackId="1"
                stroke="hsl(var(--chart-2, 200 90% 50%))"
                fill="hsl(var(--chart-2, 200 90% 50%) / 0.3)"
                name="Comments"
              />
            </AreaChart>
          ) : (
            <ComposedChart
              data={points}
              margin={{ top: hasOutliers ? 28 : 10, right: 16, left: 0, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              {partialBandStart && partialBandEnd && (
                <ReferenceArea
                  x1={partialBandStart}
                  x2={partialBandEnd}
                  yAxisId="left"
                  fill="hsl(var(--muted))"
                  fillOpacity={0.4}
                  ifOverflow="extendDomain"
                  label={{
                    value: "acumulando",
                    position: "insideTopRight",
                    fontSize: 10,
                    fill: "hsl(var(--muted-foreground))",
                  }}
                />
              )}
              <XAxis
                dataKey="date"
                tickFormatter={formatTickDate}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatNumber(v)}
                domain={yCap != null ? [0, yCap] : ["auto", "auto"]}
                allowDataOverflow={yCap != null}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatNumber(v)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                  fontSize: 12,
                }}
                labelFormatter={(d: string, payload) => {
                  const q = payload?.[0]?.payload?.window_quality;
                  return `${formatTickDate(d)}${q === "partial" ? " · acumulando" : ""}`;
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
              <Bar
                yAxisId="left"
                dataKey="n_reactions"
                name="Reactions"
                fill="hsl(var(--primary))"
                radius={[3, 3, 0, 0]}
                fillOpacity={0.9}
              >
                {points.map((p, i) => {
                  const isOutlier = yCap != null && p.n_reactions > yCap;
                  return (
                    <Cell
                      key={`cell-${i}`}
                      fill={isOutlier ? "#f59e0b" : "hsl(var(--primary))"}
                    />
                  );
                })}
                <LabelList
                  dataKey="n_reactions"
                  position="top"
                  offset={6}
                  content={(props) => {
                    const { x, y, width, value } = props as {
                      x?: number;
                      y?: number;
                      width?: number;
                      value?: number;
                    };
                    if (value == null || yCap == null || value <= yCap) return null;
                    if (x == null || y == null || width == null) return null;
                    return (
                      <text
                        x={x + width / 2}
                        y={Math.max(y - 8, 12)}
                        textAnchor="middle"
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          fill: "#b45309",
                        }}
                      >
                        {`↑ ${formatNumber(value)}`}
                      </text>
                    );
                  }}
                />
              </Bar>
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="n_comments"
                name="Comments"
                stroke="hsl(var(--chart-2, 200 90% 50%))"
                strokeWidth={2}
                dot={(props) => {
                  const { cx, cy, payload } = props as {
                    cx?: number;
                    cy?: number;
                    payload?: TimelinePoint;
                  };
                  if (cx == null || cy == null) return <g />;
                  const partial = payload?.window_quality === "partial";
                  return (
                    <circle
                      cx={cx}
                      cy={cy}
                      r={3}
                      fill={
                        partial ? "transparent" : "hsl(var(--chart-2, 200 90% 50%))"
                      }
                      stroke="hsl(var(--chart-2, 200 90% 50%))"
                      strokeWidth={2}
                    />
                  );
                }}
              />
            </ComposedChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
