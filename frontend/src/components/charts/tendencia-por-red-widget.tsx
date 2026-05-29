"use client";

import React, { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  Treemap,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

// Tipos que llegan del endpoint GET /dirigentes/{id}/crecimiento
export interface CrecimientoSeriesPoint {
  taken_at: string;
  platform: string;
  followers: number;
  posts: number;
}

interface Props {
  series: CrecimientoSeriesPoint[];
}

type ChartKind = "treemap" | "stream" | "sunburst";

const PLATFORM_COLORS: Record<string, string> = {
  TWITTER: "#1DA1F2",
  INSTAGRAM: "#E1306C",
  FACEBOOK: "#1877F2",
  TIKTOK: "#00F2EA",
  YOUTUBE: "#FF0000",
  BLUESKY: "#0085FF",
  THREADS: "#0F0F0F",
  TELEGRAM: "#26A5E4",
  NEWS: "#6B7280",
};

// Charts-lab decision registrada en docs/CHARTS-LAB-DECISIONES.md:
// Treemap > Stream > Sunburst. No reemplazar sin re-deliberar con el CEO.
const CHART_KIND_LABELS: Record<ChartKind, string> = {
  treemap: "Treemap",
  stream: "Stream",
  sunburst: "Sunburst",
};

function aggregateByPlatform(series: CrecimientoSeriesPoint[]) {
  // Último valor conocido por plataforma (followers + posts).
  const latest = new Map<string, CrecimientoSeriesPoint>();
  for (const point of series) {
    const prev = latest.get(point.platform);
    if (!prev || new Date(point.taken_at) > new Date(prev.taken_at)) {
      latest.set(point.platform, point);
    }
  }
  return Array.from(latest.values()).map((p) => ({
    platform: p.platform,
    followers: p.followers,
    posts: p.posts,
    fill: PLATFORM_COLORS[p.platform] ?? "#94A3B8",
  }));
}

function buildStreamData(series: CrecimientoSeriesPoint[]) {
  // Pivot a un array con clave día + columna por plataforma.
  const byDay = new Map<string, Record<string, number | string>>();
  const platforms = new Set<string>();
  for (const point of series) {
    const day = point.taken_at.slice(0, 10);
    platforms.add(point.platform);
    const row = byDay.get(day) ?? { day };
    row[point.platform] = point.followers;
    byDay.set(day, row);
  }
  const sorted = Array.from(byDay.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, row]) => row);
  // connectNulls (Gemini): gaps por fallo del scraper no deben verse como caídas a cero.
  // Reemplazo ausentes por null (recharts con connectNulls interpola).
  return { data: sorted, platforms: Array.from(platforms) };
}

export function TendenciaPorRedWidget({ series }: Props) {
  const [kind, setKind] = useState<ChartKind>("treemap");

  const aggregate = useMemo(() => aggregateByPlatform(series), [series]);
  const stream = useMemo(() => buildStreamData(series), [series]);

  // Sunburst: anillo interno por plataforma (followers), anillo externo por posts.
  // Recharts no tiene sunburst nativo — se aproxima con doble Pie concéntrico.

  const hasData = series.length > 0;

  return (
    <Card className="card-elevated">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="font-heading text-base">Tendencia por red</CardTitle>
        <div className="flex gap-1">
          {(Object.keys(CHART_KIND_LABELS) as ChartKind[]).map((k) => (
            <Button
              key={k}
              size="sm"
              variant={kind === k ? "default" : "outline"}
              onClick={() => setKind(k)}
              aria-pressed={kind === k}
            >
              {CHART_KIND_LABELS[k]}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="flex h-[280px] items-center justify-center text-sm text-muted-foreground">
            Sin snapshots todavía — la tendencia se construye tras el primer día de captura.
          </div>
        ) : kind === "treemap" ? (
          <ResponsiveContainer width="100%" height={280}>
            <Treemap
              data={aggregate.map((a) => ({
                name: a.platform,
                size: a.followers,
                posts: a.posts,
                fill: a.fill,
              }))}
              dataKey="size"
              nameKey="name"
              stroke="hsl(var(--background))"
              aspectRatio={4 / 3}
              content={((props: Record<string, unknown>) => {
                const x = (props.x as number) ?? 0;
                const y = (props.y as number) ?? 0;
                const width = (props.width as number) ?? 0;
                const height = (props.height as number) ?? 0;
                const name = (props.name as string) ?? "";
                const fill = (props.fill as string) ?? "hsl(var(--muted))";
                const followers = (props.size as number) ?? 0;
                // Fit-text: ajusta tamaño según celda
                const minSide = Math.min(width, height);
                const showLabel = minSide >= 36;
                const showCount = minSide >= 60;
                const labelSize = Math.min(16, Math.max(11, minSide / 7));
                const countSize = Math.min(12, Math.max(9, minSide / 11));
                return (
                  <g>
                    <rect
                      x={x}
                      y={y}
                      width={width}
                      height={height}
                      fill={fill}
                      stroke="hsl(var(--background))"
                      strokeWidth={2}
                    />
                    {showLabel && (
                      <text
                        x={x + width / 2}
                        y={y + height / 2 - (showCount ? 8 : 0)}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="#fff"
                        fontSize={labelSize}
                        fontWeight={700}
                        style={{ paintOrder: "stroke", stroke: "rgba(0,0,0,0.35)", strokeWidth: 2 }}
                      >
                        {name}
                      </text>
                    )}
                    {showCount && followers > 0 && (
                      <text
                        x={x + width / 2}
                        y={y + height / 2 + 10}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="rgba(255,255,255,0.92)"
                        fontSize={countSize}
                        style={{ paintOrder: "stroke", stroke: "rgba(0,0,0,0.35)", strokeWidth: 1.5 }}
                      >
                        {followers.toLocaleString("es-MX")}
                      </text>
                    )}
                  </g>
                );
              }) as unknown as React.ReactElement}
            />
          </ResponsiveContainer>
        ) : kind === "stream" ? (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={stream.data} stackOffset="silhouette">
              <XAxis
                dataKey="day"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              />
              <YAxis hide />
              <Tooltip />
              <Legend />
              {stream.platforms.map((p) => (
                <Area
                  key={p}
                  type="monotone"
                  dataKey={p}
                  stackId="1"
                  stroke={PLATFORM_COLORS[p] ?? "#94A3B8"}
                  fill={PLATFORM_COLORS[p] ?? "#94A3B8"}
                  fillOpacity={0.7}
                  connectNulls
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Tooltip />
              <Legend />
              <Pie
                data={aggregate}
                dataKey="followers"
                nameKey="platform"
                innerRadius={40}
                outerRadius={80}
              >
                {aggregate.map((a) => (
                  <Cell key={a.platform} fill={a.fill} />
                ))}
              </Pie>
              <Pie
                data={aggregate}
                dataKey="posts"
                nameKey="platform"
                innerRadius={90}
                outerRadius={120}
                label={false}
              >
                {aggregate.map((a) => (
                  <Cell key={`${a.platform}-outer`} fill={a.fill} fillOpacity={0.5} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
