"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { SentimentTrend } from "@/lib/api/types";

interface SentimentLineChartProps {
  data: SentimentTrend[];
}

export function SentimentLineChart({ data }: SentimentLineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="hsl(var(--border))"
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => {
            const d = new Date(value);
            return `${d.getDate()}/${d.getMonth() + 1}`;
          }}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
          width={40}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--popover))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "var(--radius)",
            color: "hsl(var(--popover-foreground))",
            fontSize: 12,
          }}
          labelFormatter={(label) => {
            const d = new Date(label);
            return d.toLocaleDateString("es-MX", {
              month: "short",
              day: "numeric",
            });
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12 }}
          iconType="circle"
          iconSize={8}
        />
        <Line
          type="monotone"
          dataKey="positive_pct"
          name="Positivo"
          stroke="hsl(var(--chart-positive))"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="negative_pct"
          name="Negativo"
          stroke="hsl(var(--chart-negative))"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="neutral_pct"
          name="Neutral"
          stroke="hsl(var(--chart-neutral))"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
