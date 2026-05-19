"use client";

/**
 * P1 #1 · 2026-05-19 · Tono Discursivo chart (matriz polaridad v2)
 *
 * Reemplaza SentimentLineChart en Overview + Dirigentes/[id]. Lee del
 * endpoint nuevo /tono-discurso-timeline en lugar del sentiment-timeline
 * legacy (que devolvía sentiment_label que está 100% NULL en datos Saymi).
 *
 * Hoy en BD el campo tono_discurso solo tiene 2 valores reales:
 *   - positivo (azul · WCAG AA 4.5:1)
 *   - neutral (gris · WCAG AA 4.5:1)
 *
 * Cuando el pipeline NLP enriquezca posts con los 5 valores granulares
 * (celebratorio/solidario/propositivo/critico/personal) este componente
 * los renderiza automáticamente leyendo el dict `tonos` del hook.
 * NO hay valores hardcoded — el chart adapta al shape real de los datos.
 */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { TonoDiscursoTimelinePoint } from "@/lib/api/hooks/use-social";

interface TonoDiscursoChartProps {
  data: TonoDiscursoTimelinePoint[];
}

// Paleta WCAG AA 4.5:1 contra fondo blanco/oscuro
// Gemini cross-audit non-blocking: accesibilidad visual + distinción
const TONO_COLORS: Record<string, string> = {
  // 5 granulares (futuro · cuando NLP enriquezca posts)
  celebratorio: "#16a34a", // green-600
  solidario: "#0891b2", // cyan-600
  propositivo: "#7c3aed", // violet-600
  critico: "#dc2626", // red-600
  personal: "#ea580c", // orange-600
  // 2 actuales en BD
  positivo: "#2563eb", // blue-600
  neutral: "#64748b", // slate-500
  // fallback
  informativo: "#0d9488", // teal-600
  ataque: "#b91c1c", // red-700
};

const TONO_LABELS: Record<string, string> = {
  celebratorio: "Celebratorio",
  solidario: "Solidario",
  propositivo: "Propositivo",
  critico: "Crítico",
  personal: "Personal",
  positivo: "Positivo",
  neutral: "Neutral",
  informativo: "Informativo",
  ataque: "Ataque",
};

export function TonoDiscursoChart({ data }: TonoDiscursoChartProps) {
  if (data.length === 0) {
    return (
      <div
        className="flex h-[300px] flex-col items-center justify-center text-center"
        role="status"
      >
        <div className="mb-2 text-3xl">📊</div>
        <p className="text-sm font-medium text-muted-foreground">
          Sin posts clasificados con tono_discurso
        </p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          El pipeline NLP de matriz polaridad v2 aún no ha procesado posts en
          este período.
        </p>
      </div>
    );
  }

  // Detectar todos los tonos presentes en la serie (data-driven)
  const allTonos = new Set<string>();
  for (const point of data) {
    for (const t of Object.keys(point.tonos)) {
      allTonos.add(t);
    }
  }
  const tonoKeys = Array.from(allTonos).sort();

  // Transformar a shape recharts-friendly
  const chartData = data.map((p) => {
    const row: Record<string, string | number> = { date: p.date.slice(5) }; // MM-DD
    for (const tono of tonoKeys) {
      row[tono] = p.tonos[tono] ?? 0;
    }
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
        <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--popover))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "var(--radius)",
            color: "hsl(var(--popover-foreground))",
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} />
        {tonoKeys.map((tono) => (
          <Area
            key={tono}
            type="monotone"
            dataKey={tono}
            name={TONO_LABELS[tono] ?? tono.charAt(0).toUpperCase() + tono.slice(1)}
            stackId="1"
            stroke={TONO_COLORS[tono] ?? "#94a3b8"}
            fill={TONO_COLORS[tono] ?? "#94a3b8"}
            fillOpacity={0.6}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
