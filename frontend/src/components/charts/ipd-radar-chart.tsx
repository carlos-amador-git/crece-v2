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
}

export function IpdRadarChart({ data, compareTo }: IpdRadarChartProps) {
  const chartData = [
    { axis: "Twitter", value: data.twitter, compare: compareTo?.twitter },
    { axis: "Instagram", value: data.instagram, compare: compareTo?.instagram },
    { axis: "Facebook", value: data.facebook, compare: compareTo?.facebook },
    { axis: "TikTok", value: data.tiktok, compare: compareTo?.tiktok },
    { axis: "YouTube", value: data.youtube, compare: compareTo?.youtube },
    { axis: "Engagement", value: data.engagement, compare: compareTo?.engagement },
  ];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chartData}>
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
          name="IPD"
          dataKey="value"
          stroke="hsl(var(--chart-accent))"
          fill="hsl(var(--chart-accent))"
          fillOpacity={0.25}
          strokeWidth={2}
        />
        {compareTo && (
          <Radar
            name="Competidor"
            dataKey="compare"
            stroke="hsl(var(--chart-negative))"
            fill="hsl(var(--chart-negative))"
            fillOpacity={0.1}
            strokeWidth={2}
            strokeDasharray="4 4"
          />
        )}
      </RadarChart>
    </ResponsiveContainer>
  );
}
