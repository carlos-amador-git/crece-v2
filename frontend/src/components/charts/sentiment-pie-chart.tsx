"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import type { SentimentDistribution } from "@/lib/api/types";
import { adjustSentimentDistributionForRole } from "@/lib/politica/sentiment";

interface SentimentPieChartProps {
  data: SentimentDistribution;
  /** Partido del dirigente · activa ajuste D-23-G (swap positive ↔ negative para oposición). */
  partido?: string | null;
}

const COLORS = {
  positive: "hsl(var(--chart-positive))",
  negative: "hsl(var(--chart-negative))",
  neutral: "hsl(var(--chart-neutral))",
};

export function SentimentPieChart({ data, partido }: SentimentPieChartProps) {
  // D-23-G · swap positive/negative counts si rol=oposición.
  const adjusted = adjustSentimentDistributionForRole(data, partido);
  const total = adjusted.total || (adjusted.positive + adjusted.negative + adjusted.neutral);

  if (!total) {
    return (
      <div className="flex h-[260px] flex-col items-center justify-center text-center">
        <div className="mb-2 text-3xl">📊</div>
        <p className="text-sm font-medium text-muted-foreground">Sin datos de sentimiento</p>
        <p className="mt-1 text-xs text-muted-foreground/70">Los datos se calculan al ejecutar el pipeline NLP</p>
      </div>
    );
  }

  const chartData = [
    { name: "Positivo", value: adjusted.positive, color: COLORS.positive },
    { name: "Negativo", value: adjusted.negative, color: COLORS.negative },
    { name: "Neutral", value: adjusted.neutral, color: COLORS.neutral },
  ].filter((d) => d.value > 0);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={3}
          dataKey="value"
          strokeWidth={0}
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--popover))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "var(--radius)",
            color: "hsl(var(--popover-foreground))",
            fontSize: 12,
          }}
          formatter={(value: number) => [
            `${value} (${((value / total) * 100).toFixed(1)}%)`,
          ]}
        />
        <Legend
          wrapperStyle={{ fontSize: 12 }}
          iconType="circle"
          iconSize={8}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
