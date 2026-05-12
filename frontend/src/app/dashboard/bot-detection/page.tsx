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
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { formatNumber } from "@/lib/utils";
import {
  PieChart,
  Pie,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  Play,
  Loader2,
  Heart,
  MessageCircle,
  Users,
  TrendingUp,
  Gauge,
} from "lucide-react";

interface ProfileAnalysis {
  platform: string;
  handle: string;
  followers: number;
  following: number;
  posts_analyzed: number;
  engagement_rate: number;
  avg_engagement: number;
  comment_like_ratio: number;
  zero_engagement_pct: number;
  engagement_cv: number;
  ff_ratio: number;
  health_score: number;
  health_level: "green" | "yellow" | "red";
  signals: string[];
}

interface Anomaly {
  platform: string;
  handle: string;
  type: string;
  description: string;
  content_preview: string;
  published_at: string | null;
}

interface HealthAnalysis {
  dirigente: string;
  profiles: ProfileAnalysis[];
  anomalies: Anomaly[];
  overall_health: number;
  overall_level: "green" | "yellow" | "red";
}

const LEVEL_STYLES = {
  green: {
    bg: "bg-emerald-50 dark:bg-emerald-950/30",
    border: "border-emerald-200 dark:border-emerald-900/50",
    text: "text-emerald-700 dark:text-emerald-300",
    badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200",
    label: "Saludable",
  },
  yellow: {
    bg: "bg-amber-50 dark:bg-amber-950/30",
    border: "border-amber-200 dark:border-amber-900/50",
    text: "text-amber-700 dark:text-amber-300",
    badge: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200",
    label: "Atencion",
  },
  red: {
    bg: "bg-red-50 dark:bg-red-950/30",
    border: "border-red-200 dark:border-red-900/50",
    text: "text-red-700 dark:text-red-300",
    badge: "bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-200",
    label: "Alerta",
  },
};

const PLATFORM_LABELS: Record<string, string> = {
  twitter: "Twitter / X",
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  youtube: "YouTube",
};

export default function HealthDigitalPage() {
  const [selectedDirigente, setSelectedDirigente] = useState("");
  const [showAnomalies, setShowAnomalies] = useState(false);
  const { data: dirigentesData } = useDirigentes();
  const dirigentes = dirigentesData?.items ?? [];

  // Auto-select first dirigente (user's own if they have one)
  const firstDirigenteId = dirigentes.length > 0 ? String(dirigentes[0].id) : "";
  const effectiveDirigente = selectedDirigente || firstDirigenteId;

  const { data: analysis, isLoading, refetch } = useQuery({
    queryKey: ["health-analysis", effectiveDirigente],
    queryFn: () =>
      api.get<HealthAnalysis>(`/bot-detection/analyze/${effectiveDirigente}`),
    enabled: !!effectiveDirigente,
  });

  const hasData = analysis && analysis.profiles.length > 0;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Salud Digital</h1>
          <p className="text-sm text-muted-foreground">
            Auditoria de autenticidad y engagement real por perfil
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={effectiveDirigente} onValueChange={setSelectedDirigente}>
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
            disabled={!effectiveDirigente || isLoading}
            onClick={() => refetch()}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Analizar
          </Button>
        </div>
      </header>

      {/* Methodology notice */}
      <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-200">
        <p className="font-medium">Analisis de engagement real</p>
        <p className="mt-0.5 text-xs text-blue-700 dark:text-blue-300">
          Se evalua: tasa de engagement, ratio comentarios/likes, % de posts sin interaccion,
          variacion de engagement, y anomalias de amplificacion. Semaforo: verde = organico saludable,
          amarillo = audiencia inactiva, rojo = patrones de manipulacion.
        </p>
      </div>

      {/* Overall health score */}
      {hasData && (
        <Card className={`${LEVEL_STYLES[analysis.overall_level].bg} ${LEVEL_STYLES[analysis.overall_level].border} border`}>
          <CardContent className="p-6">
            <div className="flex flex-col items-center gap-6 md:flex-row md:items-center">
              {/* Semicircular donut gauge */}
              <div className="relative flex shrink-0 flex-col items-center">
                <PieChart width={200} height={120}>
                  <Pie
                    data={[
                      {
                        value: analysis.overall_health,
                        fill: analysis.overall_level === "green"
                          ? "#059669"
                          : analysis.overall_level === "yellow"
                            ? "#d97706"
                            : "#dc2626",
                      },
                      {
                        value: 100 - analysis.overall_health,
                        fill: "hsl(var(--muted))",
                      },
                    ]}
                    startAngle={180}
                    endAngle={0}
                    innerRadius={60}
                    outerRadius={80}
                    dataKey="value"
                    stroke="none"
                  />
                </PieChart>
                <span className="absolute left-1/2 top-[62px] -translate-x-1/2 font-heading text-2xl font-bold tabular-nums">
                  {analysis.overall_health}
                </span>
                <span className={`-mt-4 text-xs font-medium ${
                  analysis.overall_level === "green"
                    ? "text-emerald-600 dark:text-emerald-400"
                    : analysis.overall_level === "yellow"
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-red-600 dark:text-red-400"
                }`}>
                  {analysis.overall_health >= 70
                    ? "Saludable"
                    : analysis.overall_health >= 40
                      ? "En riesgo"
                      : "Critico"}
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="font-heading text-lg font-bold">{analysis.dirigente}</h2>
                  <Badge className={LEVEL_STYLES[analysis.overall_level].badge}>
                    {LEVEL_STYLES[analysis.overall_level].label}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Puntuacion global de salud digital — {analysis.profiles.length} perfiles analizados
                </p>
              </div>
              <div className="ml-auto flex flex-col items-center">
                <button
                  onClick={() => analysis.anomalies.length > 0 && setShowAnomalies(!showAnomalies)}
                  className={`flex flex-col items-center rounded-lg px-4 py-2 transition-colors ${
                    analysis.anomalies.length > 0
                      ? "cursor-pointer hover:bg-black/5 dark:hover:bg-white/5"
                      : ""
                  }`}
                >
                  <span className={`font-heading text-2xl font-bold tabular-nums ${
                    analysis.anomalies.length > 0 ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"
                  }`}>
                    {analysis.anomalies.length}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {analysis.anomalies.length === 1 ? "anomalia" : "anomalias"}
                  </span>
                </button>
              </div>
            </div>
            {showAnomalies && analysis.anomalies.length > 0 && (
              <div className="mt-4 space-y-2 border-t pt-4">
                <p className="text-xs font-medium text-muted-foreground mb-2">Anomalias detectadas:</p>
                {analysis.anomalies.map((a, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-md bg-red-50 dark:bg-red-950/20 p-3 text-sm">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-red-500 mt-0.5" />
                    <div>
                      <p className="font-medium text-red-800 dark:text-red-200">
                        @{a.handle} ({a.platform})
                      </p>
                      <p className="text-red-700 dark:text-red-300 text-xs">{a.description}</p>
                      {a.content_preview && (
                        <p className="text-red-600/70 dark:text-red-400/70 text-xs mt-1 italic truncate">
                          {a.content_preview}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Profile cards */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}><CardContent className="p-5"><Skeleton className="mb-3 h-5 w-32" /><Skeleton className="h-20 w-full" /></CardContent></Card>
          ))}
        </div>
      ) : !hasData && selectedDirigente ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Activity className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">No hay perfiles sociales para este dirigente</p>
          </CardContent>
        </Card>
      ) : hasData ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {analysis.profiles.map((profile) => {
            const level = LEVEL_STYLES[profile.health_level];
            return (
              <Card key={`${profile.platform}-${profile.handle}`} className="overflow-hidden">
                <div className={`h-1.5 ${profile.health_level === "green" ? "bg-emerald-500" : profile.health_level === "yellow" ? "bg-amber-500" : "bg-red-500"}`} />
                <CardContent className="p-5">
                  {/* Header */}
                  <div className="flex items-start justify-between gap-2 mb-4">
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        {PLATFORM_LABELS[profile.platform] ?? profile.platform}
                      </p>
                      <p className="font-heading text-base font-semibold">@{profile.handle}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="font-heading text-2xl font-bold tabular-nums">{profile.health_score}</span>
                      <Badge className={level.badge}>{level.label}</Badge>
                    </div>
                  </div>

                  {/* Metrics grid */}
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="rounded-md bg-muted/50 p-2.5">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-0.5">
                        <TrendingUp className="h-3 w-3" />
                        Engagement
                      </div>
                      <p className="font-heading text-sm font-bold tabular-nums">{profile.engagement_rate}%</p>
                    </div>
                    <div className="rounded-md bg-muted/50 p-2.5">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-0.5">
                        <Users className="h-3 w-3" />
                        Seguidores
                      </div>
                      <p className="font-heading text-sm font-bold tabular-nums">{formatNumber(profile.followers)}</p>
                    </div>
                    <div className="rounded-md bg-muted/50 p-2.5">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-0.5">
                        <Heart className="h-3 w-3" />
                        Avg Eng.
                      </div>
                      <p className="font-heading text-sm font-bold tabular-nums">{formatNumber(profile.avg_engagement)}</p>
                    </div>
                    <div className="rounded-md bg-muted/50 p-2.5">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-0.5">
                        <MessageCircle className="h-3 w-3" />
                        Posts
                      </div>
                      <p className="font-heading text-sm font-bold tabular-nums">{profile.posts_analyzed}</p>
                    </div>
                  </div>

                  {/* Signals */}
                  {profile.signals.length > 0 && (
                    <div className="space-y-1.5">
                      {profile.signals.map((signal, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs">
                          <span className={`mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
                            profile.health_level === "green" ? "bg-emerald-500" : profile.health_level === "yellow" ? "bg-amber-500" : "bg-red-500"
                          }`} />
                          <span className="text-muted-foreground">{signal}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Gauge className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="font-medium">Selecciona un dirigente</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Elige un dirigente y presiona Analizar para ver la auditoria de salud digital
            </p>
          </CardContent>
        </Card>
      )}

      {/* Anomalies */}
      {hasData && analysis.anomalies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Anomalias Detectadas
            </CardTitle>
            <CardDescription>
              Posts con patrones de amplificacion artificial
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {analysis.anomalies.map((anomaly, i) => (
              <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
                <div className="flex items-center gap-2 mb-1.5">
                  <Badge variant="outline">{anomaly.platform}</Badge>
                  <span className="text-xs font-medium">@{anomaly.handle}</span>
                </div>
                <p className="text-sm font-medium text-amber-800 dark:text-amber-200">{anomaly.description}</p>
                {anomaly.content_preview && (
                  <p className="mt-1 text-xs text-amber-700/70 dark:text-amber-300/70 line-clamp-2">
                    {anomaly.content_preview}
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
