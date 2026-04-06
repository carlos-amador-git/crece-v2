"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useSegments,
  useSeccionScores,
  useRunScoring,
  type ScoringSegment,
} from "@/lib/api/hooks/use-scoring";
import { formatNumber } from "@/lib/utils";
import { BarChart3, Users, Target, Play, Loader2 } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

const SEGMENT_COLORS: Record<string, string> = {
  promotable: "hsl(160, 84%, 39%)",
  persuadible: "hsl(40, 62%, 58%)",
  indeciso: "hsl(212, 52%, 50%)",
  opositor: "hsl(0, 84%, 60%)",
};

const SEGMENT_LABELS: Record<string, string> = {
  promotable: "Promotable",
  persuadible: "Persuadible",
  indeciso: "Indeciso",
  opositor: "Opositor",
};

function segmentVariant(seg: string) {
  switch (seg) {
    case "promotable":
      return "success" as const;
    case "persuadible":
      return "warning" as const;
    case "opositor":
      return "danger" as const;
    default:
      return "secondary" as const;
  }
}

export default function ScoringPage() {
  const { data: kpi, isLoading: kpiLoading } = useSegments();
  const { data: secciones, isLoading: seccionesLoading } = useSeccionScores();
  const runScoring = useRunScoring();
  const [running, setRunning] = useState(false);

  const handleRunScoring = async () => {
    setRunning(true);
    try {
      await runScoring.mutateAsync();
    } finally {
      setRunning(false);
    }
  };

  const segments = kpi?.segments ?? [];
  const pieData = segments.map((s: ScoringSegment) => ({
    name: `${SEGMENT_LABELS[s.segment] ?? s.segment} (${s.percentage.toFixed(1)}%)`,
    value: s.count,
    percentage: s.percentage,
    color: SEGMENT_COLORS[s.segment] ?? "hsl(212, 18%, 70%)",
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Voter Scoring</h1>
          <p className="text-sm text-muted-foreground">
            Segmentacion y puntuacion de votantes por seccion electoral
          </p>
        </div>
        <Button
          onClick={handleRunScoring}
          disabled={running}
          className="gap-2"
        >
          {running ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          Run Scoring
        </Button>
      </header>

      {/* Data source notice */}
      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
        <p className="font-medium">Datos sinteticos — INEGI Censo 2020 CDMX</p>
        <p className="mt-0.5 text-xs text-amber-700 dark:text-amber-300">
          606 ciudadanos generados con distribuciones demograficas verificables (edad, genero, escolaridad por alcaldia).
          En produccion, cada dirigente vera solo los ciudadanos de sus secciones electorales asignadas.
        </p>
      </div>

      {/* KPI Cards */}
      <section
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Metricas de scoring"
      >
        {kpiLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="card-elevated">
              <CardContent className="p-5">
                <Skeleton className="mb-3 h-4 w-24" />
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <Card className="card-elevated">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    Total Scored
                  </p>
                  <Users className="h-4.5 w-4.5 text-muted-foreground" />
                </div>
                <p className="mt-2 font-heading text-2xl font-bold tabular-nums">
                  {formatNumber(kpi?.total_scored ?? 0)}
                </p>
              </CardContent>
            </Card>
            <Card className="card-elevated">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    Avg Score
                  </p>
                  <Target className="h-4.5 w-4.5 text-muted-foreground" />
                </div>
                <p className="mt-2 font-heading text-2xl font-bold tabular-nums">
                  {(kpi?.avg_score ?? 0).toFixed(1)}
                </p>
              </CardContent>
            </Card>
            {segments.slice(0, 2).map((seg: ScoringSegment) => (
              <Card key={seg.segment} className="card-elevated">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-muted-foreground">
                      {SEGMENT_LABELS[seg.segment]}
                    </p>
                    <BarChart3 className="h-4.5 w-4.5 text-muted-foreground" />
                  </div>
                  <div className="mt-2 flex items-end justify-between">
                    <p className="font-heading text-2xl font-bold tabular-nums">
                      {formatNumber(seg.count)}
                    </p>
                    <Badge variant={segmentVariant(seg.segment)}>
                      {seg.percentage.toFixed(1)}%
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </>
        )}
      </section>

      {/* Charts + Table */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Pie Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Distribucion por Segmento</CardTitle>
            <CardDescription>Proporcion de votantes por clasificacion</CardDescription>
          </CardHeader>
          <CardContent>
            {kpiLoading ? (
              <Skeleton className="mx-auto h-[280px] w-[280px] rounded-full" />
            ) : pieData.length === 0 ? (
              <div className="flex h-[280px] items-center justify-center text-sm text-muted-foreground">
                Sin datos de segmentacion
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    innerRadius={50}
                    paddingAngle={2}
                    strokeWidth={0}
                  >
                    {pieData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number, name: string) => [
                      `${formatNumber(value)} ciudadanos`,
                      name,
                    ]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Heatmap Table */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Scoring por Seccion</CardTitle>
            <CardDescription>
              Desglose de segmentos por seccion electoral
            </CardDescription>
          </CardHeader>
          <CardContent>
            {seccionesLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : !secciones || secciones.length === 0 ? (
              <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
                Sin datos por seccion
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Seccion</TableHead>
                    <TableHead className="text-right">Avg Score</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Promotable</TableHead>
                    <TableHead className="text-right">Persuadible</TableHead>
                    <TableHead className="text-right">Indeciso</TableHead>
                    <TableHead className="text-right">Opositor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {secciones.map((s) => (
                    <TableRow key={s.seccion_id}>
                      <TableCell className="font-medium">
                        {s.seccion_id}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        <span
                          className={`inline-flex rounded-sm px-1.5 py-0.5 text-xs font-semibold ${
                            s.avg_score >= 7
                              ? "bg-emerald-500/10 text-emerald-600"
                              : s.avg_score >= 4
                              ? "bg-amber-500/10 text-amber-600"
                              : "bg-red-500/10 text-red-600"
                          }`}
                        >
                          {s.avg_score.toFixed(1)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {s.total}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {s.promotable}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {s.persuadible}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {s.indeciso}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {s.opositor}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
