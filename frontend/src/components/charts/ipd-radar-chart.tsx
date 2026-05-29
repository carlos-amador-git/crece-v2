"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { IpdBreakdown } from "@/lib/api/types";

interface IpdRadarChartProps {
  data: IpdBreakdown;
  compareTo?: IpdBreakdown;
  /** Display name for the primary candidate (shown in tooltip) */
  candidateName?: string;
  /** Display name for the comparison candidate (shown in tooltip) */
  compareName?: string;
}

export function IpdRadarChart({
  data,
  compareTo,
  candidateName = "Dirigente",
  compareName = "Competidor",
}: IpdRadarChartProps) {
  if (!data) {
    return <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">Sin datos de IPD disponibles</div>;
  }

  // B1 post-cross-audit Gemini: radar muestra sólo fuerza por plataforma (cada eje
  // ya integra alcance+engagement+frecuencia en el IPD 0-10). Engagement global se
  // muestra como KPI/bar aparte en EngagementBarChart. YouTube NO se oculta aunque
  // sea 0 — la carencia penaliza platform coverage y debe ser visible.
  const chartData = [
    { axis: "Twitter", value: data.twitter ?? 0, compare: compareTo?.twitter },
    { axis: "Instagram", value: data.instagram ?? 0, compare: compareTo?.instagram },
    { axis: "Facebook", value: data.facebook ?? 0, compare: compareTo?.facebook },
    { axis: "TikTok", value: data.tiktok ?? 0, compare: compareTo?.tiktok },
    { axis: "YouTube", value: data.youtube ?? 0, compare: compareTo?.youtube },
  ];

  return (
    <ResponsiveContainer width="100%" height={300}>
      {/* margin top/bottom para que la etiqueta "Twitter" (eje superior) no
          choque con el borde superior del card (Gemini A1.3). outerRadius
          reducido a 70% para compensar el espacio reservado a las labels. */}
      <RadarChart
        cx="50%"
        cy="50%"
        outerRadius="70%"
        data={chartData}
        margin={{ top: 20, right: 30, bottom: 16, left: 30 }}
      >
        <PolarGrid stroke="hsl(var(--border))" />
        <PolarAngleAxis
          dataKey="axis"
          tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 10]}
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--popover))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "var(--radius)",
            color: "hsl(var(--popover-foreground))",
            fontSize: 12,
          }}
        />
        <Radar
          name={candidateName}
          dataKey="value"
          stroke="hsl(var(--chart-accent))"
          fill="hsl(var(--chart-accent))"
          fillOpacity={0.25}
          strokeWidth={2}
        />
        {compareTo && (
          <Radar
            name={compareName}
            dataKey="compare"
            stroke="#F97316"
            fill="#F97316"
            fillOpacity={0.1}
            strokeWidth={2}
            strokeDasharray="5 5"
          />
        )}
      </RadarChart>
    </ResponsiveContainer>
  );
}
