"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { PlatformIcon } from "@/components/social/platform-icon";
import { formatNumber } from "@/lib/utils";
import type { IpdBreakdown, SentimentTrend } from "@/lib/api/types";
import { BarChart3, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

/* ---- Mock data ---- */
const DIRIGENTES_LIST = [
  { id: 1, name: "Ana Martinez", partido: "MORENA", ipd: 9.2 },
  { id: 2, name: "Carlos Ruiz", partido: "PAN", ipd: 8.7 },
  { id: 3, name: "Maria Lopez", partido: "PRI", ipd: 8.1 },
  { id: 4, name: "Jose Garcia", partido: "MC", ipd: 7.8 },
];

const MOCK_IPD_A: IpdBreakdown = { twitter: 9.5, instagram: 8.8, facebook: 9.0, tiktok: 0, youtube: 0, engagement: 9.4 };
const MOCK_IPD_B: IpdBreakdown = { twitter: 8.2, instagram: 6.5, facebook: 9.1, tiktok: 0, youtube: 7.8, engagement: 8.0 };

const MOCK_GROWTH = [
  { name: "Ana Martinez", value: 12400 },
  { name: "Carlos Ruiz", value: 8900 },
  { name: "Maria Lopez", value: 7200 },
  { name: "Jose Garcia", value: 5600 },
];

const MOCK_ENGAGEMENT_RATE = [
  { name: "Ana Martinez", value: 4.2 },
  { name: "Carlos Ruiz", value: 3.8 },
  { name: "Maria Lopez", value: 3.1 },
  { name: "Jose Garcia", value: 2.7 },
];

const MOCK_TREND: SentimentTrend[] = Array.from({ length: 30 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toISOString().slice(0, 10),
    positive: Math.floor(40 + Math.random() * 30),
    negative: Math.floor(10 + Math.random() * 20),
    neutral: Math.floor(20 + Math.random() * 15),
  };
});
/* ---- End mock data ---- */

export default function BenchmarkPage() {
  const [selectedA, setSelectedA] = useState("1");
  const [selectedB, setSelectedB] = useState("2");

  const dirigenteA = DIRIGENTES_LIST.find((d) => d.id === Number(selectedA));
  const dirigenteB = DIRIGENTES_LIST.find((d) => d.id === Number(selectedB));

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
            <Select value={selectedA} onValueChange={setSelectedA}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DIRIGENTES_LIST.map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>
                    {d.name} ({d.partido})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
            <Select value={selectedB} onValueChange={setSelectedB}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DIRIGENTES_LIST.map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>
                    {d.name} ({d.partido})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Comparison cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Dirigente A card */}
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-heading text-lg font-semibold">
                  {dirigenteA?.name}
                </p>
                <Badge variant="secondary">{dirigenteA?.partido}</Badge>
              </div>
              <IpdScoreBadge score={dirigenteA?.ipd ?? 0} size="lg" />
            </div>
          </CardContent>
        </Card>
        {/* Dirigente B card */}
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-heading text-lg font-semibold">
                  {dirigenteB?.name}
                </p>
                <Badge variant="secondary">{dirigenteB?.partido}</Badge>
              </div>
              <IpdScoreBadge score={dirigenteB?.ipd ?? 0} size="lg" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Radar comparison */}
      <Card>
        <CardHeader>
          <CardTitle>Comparacion IPD</CardTitle>
        </CardHeader>
        <CardContent>
          <IpdRadarChart data={MOCK_IPD_A} compareTo={MOCK_IPD_B} />
          <div className="mt-4 flex justify-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-sky-500" />
              {dirigenteA?.name}
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full border-2 border-red-500 bg-transparent" />
              {dirigenteB?.name}
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
            <EngagementBarChart data={MOCK_GROWTH} layout="vertical" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Tasa de Engagement (%)</CardTitle>
          </CardHeader>
          <CardContent>
            <EngagementBarChart data={MOCK_ENGAGEMENT_RATE} layout="vertical" />
          </CardContent>
        </Card>
      </div>

      {/* Sentiment trend comparison */}
      <Card>
        <CardHeader>
          <CardTitle>Tendencia de Sentimiento Comparada</CardTitle>
        </CardHeader>
        <CardContent>
          <SentimentLineChart data={MOCK_TREND} />
        </CardContent>
      </Card>
    </div>
  );
}
