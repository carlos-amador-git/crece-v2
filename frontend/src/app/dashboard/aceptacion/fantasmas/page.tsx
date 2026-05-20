"use client";

import { Suspense } from "react";
import { useAceptacionOverview, useFantasmasPorPlataforma } from "@/lib/api/hooks/use-aceptacion";
import type { DirigentePlatformFantasmas } from "@/lib/api/hooks/use-aceptacion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatNumber } from "@/lib/utils";
import { Ghost, ChevronRight } from "lucide-react";
import Link from "next/link";

const PLATFORM_LABELS: Record<string, string> = {
  twitter: "Twitter",
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  youtube: "YouTube",
};

const PLATFORM_COLOR: Record<string, string> = {
  twitter: "bg-sky-500",
  instagram: "bg-pink-500",
  facebook: "bg-blue-600",
  tiktok: "bg-neutral-800",
  youtube: "bg-red-500",
};

function FantasmaBar({ pct }: { pct: number }) {
  const isCritical = pct > 99;
  const isWarn = !isCritical && pct > 95;
  const color = isCritical ? "bg-rose-500" : isWarn ? "bg-amber-500" : "bg-emerald-500";
  const activados = Math.max(0, 100 - pct);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
        <div className={`h-full ${color} transition-all`} style={{ width: `${activados}%` }} />
      </div>
      <span className={`text-xs tabular-nums font-medium ${isCritical ? "text-rose-500" : isWarn ? "text-amber-500" : "text-emerald-500"}`}>
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

function PlatformBreakdown({ data }: { data: DirigentePlatformFantasmas }) {
  return (
    <div className="mt-3 divide-y divide-border/50">
      {data.platforms.map((p) => (
        <div key={p.platform} className="flex items-center gap-3 py-2">
          <div className={`h-2 w-2 rounded-full ${PLATFORM_COLOR[p.platform] ?? "bg-muted-foreground"}`} />
          <span className="w-20 text-xs text-muted-foreground">
            {PLATFORM_LABELS[p.platform] ?? p.platform}
          </span>
          <span className="w-20 text-right text-xs tabular-nums text-muted-foreground">
            {formatNumber(p.followers)} seg.
          </span>
          <span className="w-20 text-right text-xs tabular-nums text-muted-foreground">
            {formatNumber(p.unique_commenters)} act.
          </span>
          <div className="flex-1" />
          <FantasmaBar pct={p.pct_fantasma} />
        </div>
      ))}
    </div>
  );
}

function FantasmasInner() {
  const { data: overview, isLoading: overviewLoading, error } = useAceptacionOverview();
  const { data: plataformas, isLoading: platLoading } = useFantasmasPorPlataforma();

  const isLoading = overviewLoading || platLoading;

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-52" />)}
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No se pudo cargar el análisis de fantasmas.
          </CardContent>
        </Card>
      </div>
    );
  }

  const rows = [...overview.dirigentes].sort((a, b) => b.pct_fantasma - a.pct_fantasma);
  const platMap = new Map(plataformas?.map((p) => [p.dirigente_id, p]) ?? []);

  return (
    <div className="space-y-6 p-6">
      <div>
        <div className="flex items-center gap-2">
          <Ghost className="h-6 w-6 text-accent" />
          <h1 className="font-heading text-2xl font-bold tracking-tight">
            Fantasmas
          </h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Vista agregada de followers que NO interactúan con el contenido del dirigente.
        </p>
      </div>

      <Tabs defaultValue="resumen" className="w-full">
        <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
          <TabsTrigger value="resumen">
            <Ghost className="mr-1.5 h-3.5 w-3.5" /> Resumen agregado
          </TabsTrigger>
          <TabsTrigger value="por-plataforma">
            Por plataforma
          </TabsTrigger>
        </TabsList>

        {/* TAB 1 — Resumen */}
        <TabsContent value="resumen" className="mt-4 space-y-4">
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium">Dirigente</th>
                      <th className="px-4 py-2 text-right font-medium">Followers</th>
                      <th className="px-4 py-2 text-right font-medium">Activos</th>
                      <th className="px-4 py-2 text-right font-medium">Fantasmas</th>
                      <th className="px-4 py-2 text-right font-medium">% Fantasma</th>
                      <th className="px-4 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((d) => {
                      const isCritical = d.pct_fantasma > 99;
                      const isWarn = !isCritical && d.pct_fantasma > 95;
                      return (
                        <tr key={d.dirigente_id} className="border-b last:border-0">
                          <td className="px-4 py-3 font-medium">{d.full_name}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{formatNumber(d.total_followers)}</td>
                          <td className="px-4 py-3 text-right tabular-nums text-emerald-500">{formatNumber(d.unique_commenters)}</td>
                          <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                            {formatNumber(Math.max(0, d.total_followers - d.unique_commenters))}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums font-semibold">
                            <span className={isCritical ? "text-rose-500" : isWarn ? "text-amber-500" : "text-emerald-500"}>
                              {d.pct_fantasma.toFixed(2)}%
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <Link href={`/dashboard/aceptacion/${d.dirigente_id}`}>
                              <ChevronRight className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2 — Por plataforma */}
        <TabsContent value="por-plataforma" className="mt-4 space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {rows.map((d) => {
              const isCritical = d.pct_fantasma > 99;
              const isWarn = !isCritical && d.pct_fantasma > 95;
              const platData = platMap.get(d.dirigente_id);
              return (
                <Card key={d.dirigente_id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <CardTitle className="text-base">{d.full_name}</CardTitle>
                        <div className="mt-0.5 flex items-center gap-2">
                          {d.rol_politico && (
                            <Badge
                              variant="outline"
                              className={
                                d.rol_politico === "oposicion"
                                  ? "border-amber-500/40 text-amber-500"
                                  : "border-emerald-500/40 text-emerald-500"
                              }
                            >
                              {d.rol_politico === "oficialismo" ? "Gobierno" : d.rol_politico}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <Link href={`/dashboard/aceptacion/${d.dirigente_id}`} className="shrink-0">
                        <ChevronRight className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                      </Link>
                    </div>
                  </CardHeader>
                  <CardContent className="pb-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <div className="text-xs text-muted-foreground">
                          {formatNumber(d.total_followers)} followers · {formatNumber(d.unique_commenters)} activos
                        </div>
                        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                          <div
                            className={`h-full transition-all ${isCritical ? "bg-rose-500" : isWarn ? "bg-amber-500" : "bg-emerald-500"}`}
                            style={{ width: `${Math.min(100, d.pct_activados)}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>Activos {d.pct_activados.toFixed(2)}%</span>
                          <span className={isCritical ? "text-rose-500 font-semibold" : isWarn ? "text-amber-500 font-semibold" : "text-emerald-500"}>
                            Fantasmas {d.pct_fantasma.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {platData && platData.platforms.length > 0 && (
                      <>
                        <div className="mt-3 mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Por red social
                        </div>
                        <PlatformBreakdown data={platData} />
                      </>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

      </Tabs>
    </div>
  );
}

export default function FantasmasPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[60vh] w-full" />}>
      <FantasmasInner />
    </Suspense>
  );
}
