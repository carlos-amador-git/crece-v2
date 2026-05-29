"use client";

/**
 * War Room Personal · W5
 *
 * Vista admin · ranking cross-dirigente de competidores light.
 * Solo accesible para roles admin/analyst. RBAC en el endpoint + filtro en sidebar.
 */

import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BarChart3, Search, Users, TrendingUp } from "lucide-react";
import { useAdminCompetitorRankings } from "@/lib/api/hooks/use-competitors";
import { formatNumber } from "@/lib/utils";

const PLATFORM_LABEL: Record<string, string> = {
  FACEBOOK: "FB",
  INSTAGRAM: "IG",
  TWITTER: "X",
  TIKTOK: "TT",
  YOUTUBE: "YT",
};

export default function AdminRankingPage() {
  const { data: rows, isLoading, error } = useAdminCompetitorRankings(100);
  const [q, setQ] = useState("");
  const [partidoFilter, setPartidoFilter] = useState<string>("__all");

  const partidos = useMemo(() => {
    const set = new Set<string>();
    rows?.forEach((r) => {
      if (r.partido) set.add(r.partido);
    });
    return Array.from(set).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    return (rows ?? []).filter((r) => {
      if (partidoFilter !== "__all" && r.partido !== partidoFilter) return false;
      if (q) {
        const needle = q.toLowerCase();
        return (
          r.display_name.toLowerCase().includes(needle) ||
          r.dirigente_objetivo_name.toLowerCase().includes(needle)
        );
      }
      return true;
    });
  }, [rows, q, partidoFilter]);

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-rose-500">
            Sin permiso para ver esta sección o error de carga.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start gap-3">
        <BarChart3 className="mt-1 h-6 w-6 text-amber-500" />
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight">
            Ranking de competidores
          </h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Vista cross-org · solo administradores. Métricas externas mensuales
            de los referentes declarados por cada dirigente.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filtros</CardTitle>
          <CardDescription>
            {filtered.length} de {rows?.length ?? 0} competidores
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[240px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Buscar competidor o dirigente…"
                className="pl-9"
              />
            </div>
            <Select value={partidoFilter} onValueChange={setPartidoFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">Todos los partidos</SelectItem>
                {partidos.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">#</th>
                  <th className="px-4 py-2 text-left font-medium">Competidor</th>
                  <th className="px-4 py-2 text-left font-medium">Partido</th>
                  <th className="px-4 py-2 text-left font-medium">Red</th>
                  <th className="px-4 py-2 text-left font-medium">Rival de</th>
                  <th className="px-4 py-2 text-right font-medium">
                    <Users className="ml-auto h-3 w-3" />
                  </th>
                  <th className="px-4 py-2 text-right font-medium">
                    <TrendingUp className="ml-auto h-3 w-3" />
                  </th>
                  <th className="px-4 py-2 text-right font-medium">Posts/mes</th>
                  <th className="px-4 py-2 text-right font-medium">Último mes</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-muted-foreground">
                      Sin resultados con los filtros actuales.
                    </td>
                  </tr>
                ) : (
                  filtered.map((r, i) => (
                    <tr
                      key={r.competitor_id}
                      className="border-b last:border-0 hover:bg-muted/40"
                    >
                      <td className="px-4 py-3 text-muted-foreground tabular-nums">
                        {i + 1}
                      </td>
                      <td className="px-4 py-3 font-medium">{r.display_name}</td>
                      <td className="px-4 py-3">
                        {r.partido ? (
                          <Badge variant="outline">{r.partido}</Badge>
                        ) : (
                          <span className="text-muted-foreground/40">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="secondary">
                          {PLATFORM_LABEL[r.platform] ?? r.platform}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {r.dirigente_objetivo_name}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {r.followers_total != null
                          ? formatNumber(r.followers_total)
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {r.engagement_rate != null
                          ? `${(r.engagement_rate * 100).toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {r.posts_count ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                        {r.last_month ? r.last_month.slice(0, 7) : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Datos del scraper light de competidores · captura mensual. Sin NLP por diseño.
      </p>
    </div>
  );
}
