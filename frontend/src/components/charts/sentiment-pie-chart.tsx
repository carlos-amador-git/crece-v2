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
  const chartData = [
    { name: "Positivo", value: data.positive, color: COLORS.positive },
    { name: "Negativo", value: data.negative, color: COLORS.negative },
    { name: "Neutral", value: data.neutral, color: COLORS.neutral },
  ];

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
            `${value} (${((value / data.total) * 100).toFixed(1)}%)`,
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
