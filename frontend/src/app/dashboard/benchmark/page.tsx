"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { IpdRadarChart } from "@/components/charts/ipd-radar-chart";
import { EngagementBarChart } from "@/components/charts/engagement-bar-chart";
import { SentimentLineChart } from "@/components/charts/sentiment-line-chart";
import { IpdScoreBadge } from "@/components/dirigentes/ipd-score-badge";
import { useBenchmarkDirigentes, useBenchmarkComparison } from "@/lib/api/hooks/use-benchmark";
import { useDirigente } from "@/lib/api/hooks/use-dirigentes";
import { useSentimentTrend } from "@/lib/api/hooks/use-social";
import type { IpdBreakdown } from "@/lib/api/types";
import { BarChart3 } from "lucide-react";

const EMPTY_IPD: IpdBreakdown = {
  twitter: 0,
  instagram: 0,
  facebook: 0,
  tiktok: 0,
  youtube: 0,
  engagement: 0,
};

export default function BenchmarkPage() {
  const [selectedA, setSelectedA] = useState("");
  const [selectedB, setSelectedB] = useState("");

  const { data: dirigentesData, isLoading: dirigentesLoading } =
    useBenchmarkDirigentes();
  const dirigentesList = dirigentesData?.items ?? [];

  const { data: detailA } = useDirigente(selectedA);
  const { data: detailB } = useDirigente(selectedB);
  const { data: benchmarkData } = useBenchmarkComparison(selectedA, selectedB);
  const { data: sentimentA } = useSentimentTrend(30, detailA?.id);

  const ipdA = detailA?.ipd_breakdown ?? EMPTY_IPD;
  const ipdB = detailB?.ipd_breakdown ?? EMPTY_IPD;

  // Build growth + engagement data from benchmark comparison if available
  const growthData =
    benchmarkData?.comparison
      .filter((c) => c.metric === "follower_growth")
      .flatMap((c) => [
        { name: benchmarkData.dirigente.nombre, value: c.dirigente_value },
        ...c.competidor_values.map((cv) => ({
          name: cv.nombre,
          value: cv.value,
        })),
      ]) ?? [];

  const engagementData =
    benchmarkData?.comparison
      .filter((c) => c.metric === "engagement_rate")
      .flatMap((c) => [
        { name: benchmarkData.dirigente.nombre, value: c.dirigente_value },
        ...c.competidor_values.map((cv) => ({
          name: cv.nombre,
          value: cv.value,
        })),
      ]) ?? [];

  const sentimentTrend = sentimentA ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold">
          Benchmarking Competitivo
        </h1>
        <p className="text-sm text-muted-foreground">
          Comparacion directa entre dirigentes y competidores
        </p>
      </div>

      {/* Selectors */}
      <Card>
        <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
          <div className="flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Dirigente
            </label>
            {dirigentesLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select value={selectedA} onValueChange={setSelectedA}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar dirigente" />
                </SelectTrigger>
                <SelectContent>
                  {dirigentesList.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.nombre} {d.apellido_paterno} ({d.partido})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          <div className="flex items-center justify-center">
            <span className="rounded-full border px-3 py-1 text-xs font-semibold text-muted-foreground">
              VS
            </span>
          </div>
          <div className="flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Competidor
            </label>
            {dirigentesLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select value={selectedB} onValueChange={setSelectedB}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar competidor" />
                </SelectTrigger>
                <SelectContent>
                  {dirigentesList.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.nombre} {d.apellido_paterno} ({d.partido})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Show comparison only when both are selected */}
      {!selectedA || !selectedB ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <BarChart3 className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              Selecciona un dirigente y un competidor para comparar
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Comparison cards */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardContent className="p-5">
                {detailA ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-heading text-lg font-semibold">
                        {detailA.nombre} {detailA.apellido_paterno}
                      </p>
                      <Badge variant="secondary">{detailA.partido}</Badge>
                    </div>
                    <IpdScoreBadge score={detailA.ipd_score} size="lg" />
                  </div>
                ) : (
                  <Skeleton className="h-16 w-full" />
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                {detailB ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-heading text-lg font-semibold">
                        {detailB.nombre} {detailB.apellido_paterno}
                      </p>
                      <Badge variant="secondary">{detailB.partido}</Badge>
                    </div>
                    <IpdScoreBadge score={detailB.ipd_score} size="lg" />
                  </div>
                ) : (
                  <Skeleton className="h-16 w-full" />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Radar comparison */}
          <Card>
            <CardHeader>
              <CardTitle>Comparacion IPD</CardTitle>
            </CardHeader>
            <CardContent>
              <IpdRadarChart data={ipdA} compareTo={ipdB} />
              <div className="mt-4 flex justify-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full bg-sky-500" />
                  {detailA?.nombre ?? "Dirigente A"}
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full border-2 border-red-500 bg-transparent" />
                  {detailB?.nombre ?? "Dirigente B"}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Growth + Engagement */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Crecimiento de Seguidores (30d)</CardTitle>
              </CardHeader>
              <CardContent>
                {growthData.length > 0 ? (
                  <EngagementBarChart data={growthData} layout="vertical" />
                ) : (
                  <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
                    Sin datos de crecimiento disponibles
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Tasa de Engagement (%)</CardTitle>
              </CardHeader>
              <CardContent>
                {engagementData.length > 0 ? (
                  <EngagementBarChart
                    data={engagementData}
                    layout="vertical"
                  />
                ) : (
                  <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
                    Sin datos de engagement disponibles
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sentiment trend comparison */}
          <Card>
            <CardHeader>
              <CardTitle>Tendencia de Sentimiento Comparada</CardTitle>
            </CardHeader>
            <CardContent>
              {sentimentTrend.length > 0 ? (
                <SentimentLineChart data={sentimentTrend} />
              ) : (
                <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                  Sin datos de sentimiento disponibles
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
