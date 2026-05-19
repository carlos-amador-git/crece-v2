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

interface SentimentPieChartProps {
  data: SentimentDistribution;
}

const COLORS = {
  positive: "hsl(var(--chart-positive))",
  negative: "hsl(var(--chart-negative))",
  neutral: "hsl(var(--chart-neutral))",
};

export function SentimentPieChart({ data }: SentimentPieChartProps) {
  // D-23-G scope: distribución por categoría se mantiene cruda · el flip
  // aplica solo a KPI agregado "Sentimiento Prom." (no a charts de conteo).
  //
  // P0 #2+#7 (2026-05-19): el donut usa SOLO posts clasificados (positive +
  // negative + neutral real). Posts con sentiment_label NULL viven en
  // data.unclassified y se reportan en el Alert encima del donut, no como
  // un slice neutral falso.
  const classifiedTotal = data.positive + data.negative + data.neutral;
  const unclassified = data.unclassified ?? 0;

  if (!classifiedTotal) {
    return (
      <div className="flex h-[260px] flex-col items-center justify-center text-center">
        <div className="mb-2 text-3xl">📊</div>
        <p className="text-sm font-medium text-muted-foreground">Sin datos clasificados</p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          {unclassified > 0
            ? `${unclassified} posts sin clasificación NLP`
            : "Los datos se calculan al ejecutar el pipeline NLP"}
        </p>
      </div>
    );
  }

  const chartData = [
    { name: "Positivo", value: data.positive, color: COLORS.positive },
    { name: "Negativo", value: data.negative, color: COLORS.negative },
    { name: "Neutral", value: data.neutral, color: COLORS.neutral },
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
            `${value} (${((value / classifiedTotal) * 100).toFixed(1)}%)`,
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
