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
import { useAlcaldias, useGeoTrends, type TrendsPeriod } from "@/lib/api/hooks/use-trends";

function SentimentDot({ avg }: { avg: number | null }) {
  if (avg == null) return <span className="text-muted-foreground">—</span>;
  const color =
    avg > 0.2 ? "bg-emerald-500" : avg < -0.2 ? "bg-rose-500" : "bg-amber-400";
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

export function TrendingAlcaldiaCard() {
  const [alcaldiaId, setAlcaldiaId] = useState<number | null>(null);
  const [period, setPeriod] = useState<TrendsPeriod>("7d");

  const { data: alcaldias } = useAlcaldias();
  const { data, isLoading } = useGeoTrends({
    alcaldia_id: alcaldiaId,
    period,
    limit: 5,
  });

  const trends = data?.trends ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
        <div>
          <CardTitle className="text-base">Trending ahora en CDMX</CardTitle>
          <p className="text-xs text-muted-foreground">
            Clusters detectados por el motor de trends cada 1h
          </p>
        </div>
        <div className="flex gap-2">
          <Select
            value={alcaldiaId?.toString() ?? "all"}
            onValueChange={(v) => setAlcaldiaId(v === "all" ? null : Number(v))}
          >
            <SelectTrigger className="h-8 w-[160px] text-xs">
              <SelectValue placeholder="Alcaldía" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas</SelectItem>
              {alcaldias?.map((a) => (
                <SelectItem key={a.id} value={a.id.toString()}>
                  {a.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={period} onValueChange={(v) => setPeriod(v as TrendsPeriod)}>
            <SelectTrigger className="h-8 w-[80px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">24h</SelectItem>
              <SelectItem value="7d">7d</SelectItem>
              <SelectItem value="30d">30d</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : trends.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Sin trends en este periodo. El worker corre cada hora y necesita
            posts recientes con mención de alcaldía o coordenadas.
          </p>
        ) : (
          <ul className="space-y-2">
            {trends.map((trend) => (
              <li
                key={trend.id}
                className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {trend.topic_label ?? (
                      <span className="italic text-muted-foreground">
                        (sin etiqueta)
                      </span>
                    )}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    {trend.alcaldia_nombre && (
                      <Badge variant="outline" className="h-5 px-1.5 text-[10px]">
                        {trend.alcaldia_nombre}
                      </Badge>
                    )}
                    <span>{trend.post_count} posts</span>
                    <SentimentDot avg={trend.sentiment_avg} />
                  </div>
                </div>
                {trend.growth_rate_24h != null && (
                  <span
                    className={`text-xs font-semibold ${
                      trend.growth_rate_24h > 0
                        ? "text-emerald-600"
                        : "text-rose-600"
                    }`}
                  >
                    {trend.growth_rate_24h > 0 ? "+" : ""}
                    {(trend.growth_rate_24h * 100).toFixed(0)}%
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
