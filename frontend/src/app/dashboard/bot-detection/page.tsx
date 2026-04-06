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
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import {
  Bot,
  Shield,
  AlertTriangle,
  CheckCircle2,
  Play,
  Loader2,
  Users,
} from "lucide-react";

interface BotSignal {
  name: string;
  score: number;
  detail: string;
}

interface BotResult {
  handle: string;
  platform: string;
  bot_probability: number;
  classification: "human" | "suspicious" | "likely_bot";
  signals: BotSignal[];
  analyzed_at: string;
}

interface BotAnalysisSummary {
  total_analyzed: number;
  likely_bots: number;
  suspicious: number;
  humans: number;
  bot_percentage: number;
  suspicious_percentage: number;
  results: BotResult[];
}

function classificationBadge(c: string) {
  switch (c) {
    case "likely_bot":
      return <Badge variant="danger">Bot</Badge>;
    case "suspicious":
      return <Badge variant="warning">Sospechoso</Badge>;
    default:
      return <Badge variant="success">Humano</Badge>;
  }
}

function probabilityColor(p: number) {
  if (p >= 0.7) return "text-red-600 dark:text-red-400";
  if (p >= 0.4) return "text-amber-600 dark:text-amber-400";
  return "text-emerald-600 dark:text-emerald-400";
}

export default function BotDetectionPage() {
  const [selectedDirigente, setSelectedDirigente] = useState("");
  const { data: dirigentesData } = useDirigentes();
  const dirigentes = dirigentesData?.items ?? [];

  const { data: analysis, isLoading } = useQuery({
    queryKey: ["bot-analysis", selectedDirigente],
    queryFn: () =>
      api.get<BotAnalysisSummary>(
        `/bot-detection/analyze/${selectedDirigente}`
      ),
    enabled: !!selectedDirigente,
  });

  const runAnalysis = useMutation({
    mutationFn: (dirigenteId: string) =>
      api.post<BotAnalysisSummary>(`/bot-detection/analyze/${dirigenteId}`),
  });

  // Demo data when no backend endpoint exists yet
  const demoData: BotAnalysisSummary = {
    total_analyzed: 150,
    likely_bots: 12,
    suspicious: 23,
    humans: 115,
    bot_percentage: 8.0,
    suspicious_percentage: 23.3,
    results: [
      {
        handle: "user38291028374",
        platform: "twitter",
        bot_probability: 0.95,
        classification: "likely_bot",
        signals: [
          { name: "username_trailing_digits", score: 0.3, detail: "8+ trailing digits" },
          { name: "low_follower_ratio", score: 0.35, detail: "Ratio 0.001 (3/5000)" },
          { name: "zero_posts_many_following", score: 0.25, detail: "0 posts, 5000 following" },
        ],
        analyzed_at: new Date().toISOString(),
      },
      {
        handle: "bot_promocion_mx",
        platform: "twitter",
        bot_probability: 0.88,
        classification: "likely_bot",
        signals: [
          { name: "username_suspicious_prefix", score: 0.4, detail: "Prefix 'bot_'" },
          { name: "content_duplication", score: 0.4, detail: "80% posts duplicados" },
        ],
        analyzed_at: new Date().toISOString(),
      },
      {
        handle: "maria_gzz_2024",
        platform: "twitter",
        bot_probability: 0.45,
        classification: "suspicious",
        signals: [
          { name: "new_account_high_activity", score: 0.3, detail: "Cuenta de 15 dias con 200 posts" },
        ],
        analyzed_at: new Date().toISOString(),
      },
      {
        handle: "carlos.mendez.real",
        platform: "instagram",
        bot_probability: 0.08,
        classification: "human",
        signals: [],
        analyzed_at: new Date().toISOString(),
      },
      {
        handle: "fake_news_cdmx_",
        platform: "twitter",
        bot_probability: 0.92,
        classification: "likely_bot",
        signals: [
          { name: "regular_posting_interval", score: 0.35, detail: "Posts cada 120s exactos" },
          { name: "burst_posting", score: 0.25, detail: "50 posts en 1 hora" },
          { name: "no_avatar", score: 0.15, detail: "Sin foto de perfil" },
        ],
        analyzed_at: new Date().toISOString(),
      },
    ],
  };

  const displayData = analysis ?? demoData;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Deteccion de Bots</h1>
          <p className="text-sm text-muted-foreground">
            Analisis de seguidores sospechosos e interacciones inautenticas
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedDirigente} onValueChange={setSelectedDirigente}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Seleccionar dirigente" />
            </SelectTrigger>
            <SelectContent>
              {dirigentes.map((d: { id: number; full_name: string }) => (
                <SelectItem key={d.id} value={String(d.id)}>
                  {d.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            className="gap-2"
            disabled={!selectedDirigente || runAnalysis.isPending}
            onClick={() => runAnalysis.mutate(selectedDirigente)}
          >
            {runAnalysis.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Analizar
          </Button>
        </div>
      </header>

      {/* Data source notice */}
      <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-200">
        <p className="font-medium">Analisis basado en patrones</p>
        <p className="mt-0.5 text-xs text-blue-700 dark:text-blue-300">
          Se analizan: patrones de username, ratio seguidores/seguidos, frecuencia de publicacion,
          duplicacion de contenido, edad de cuenta vs actividad, y engagement rate.
          Datos de ejemplo mostrados — selecciona un dirigente y ejecuta el analisis para datos reales.
        </p>
      </div>

      {/* KPI Cards */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="card-elevated">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">Analizados</p>
              <Users className="h-4.5 w-4.5 text-muted-foreground" />
            </div>
            <p className="mt-2 font-heading text-2xl font-bold tabular-nums">
              {displayData.total_analyzed}
            </p>
          </CardContent>
        </Card>
        <Card className="card-elevated">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">Bots Detectados</p>
              <Bot className="h-4.5 w-4.5 text-red-500" />
            </div>
            <p className="mt-2 font-heading text-2xl font-bold tabular-nums text-red-600 dark:text-red-400">
              {displayData.likely_bots}
              <span className="ml-2 text-sm font-normal">({displayData.bot_percentage}%)</span>
            </p>
          </CardContent>
        </Card>
        <Card className="card-elevated">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">Sospechosos</p>
              <AlertTriangle className="h-4.5 w-4.5 text-amber-500" />
            </div>
            <p className="mt-2 font-heading text-2xl font-bold tabular-nums text-amber-600 dark:text-amber-400">
              {displayData.suspicious}
            </p>
          </CardContent>
        </Card>
        <Card className="card-elevated">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">Verificados Humanos</p>
              <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
            </div>
            <p className="mt-2 font-heading text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
              {displayData.humans}
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Results table */}
      <Card>
        <CardHeader>
          <CardTitle>Resultados del Analisis</CardTitle>
          <CardDescription>
            Cuentas analizadas ordenadas por probabilidad de bot
          </CardDescription>
        </CardHeader>
        <CardContent>
          {displayData.results.length === 0 ? (
            <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
              Ejecuta un analisis para ver resultados
            </div>
          ) : (
            <div className="space-y-3">
              {displayData.results
                .sort((a, b) => b.bot_probability - a.bot_probability)
                .map((result) => (
                  <div
                    key={result.handle}
                    className="flex items-start gap-4 rounded-lg border p-4"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-heading font-semibold">@{result.handle}</span>
                        {classificationBadge(result.classification)}
                        <Badge variant="outline">{result.platform}</Badge>
                        <span className={`text-sm font-bold tabular-nums ${probabilityColor(result.bot_probability)}`}>
                          {(result.bot_probability * 100).toFixed(0)}%
                        </span>
                      </div>
                      {result.signals.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {result.signals.map((signal) => (
                            <span
                              key={signal.name}
                              className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-[11px] text-muted-foreground"
                              title={signal.detail}
                            >
                              {signal.detail}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
