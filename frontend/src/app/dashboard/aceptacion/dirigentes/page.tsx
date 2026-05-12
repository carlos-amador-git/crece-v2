"use client";

import Link from "next/link";
import { useAceptacionOverview } from "@/lib/api/hooks/use-aceptacion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber } from "@/lib/utils";
import { UserSquare2 } from "lucide-react";

export default function AceptacionDirigentesPage() {
  const { data, isLoading, error } = useAceptacionOverview();

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-16" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No se pudo cargar el detalle por dirigente.
          </CardContent>
        </Card>
      </div>
    );
  }

  const rows = [...data.dirigentes].sort((a, b) => b.pct_aprobacion - a.pct_aprobacion);

  return (
    <div className="space-y-6 p-6">
      <div>
        <div className="flex items-center gap-2">
          <UserSquare2 className="h-6 w-6 text-accent" />
          <h1 className="font-heading text-2xl font-bold tracking-tight">
            Aceptación por dirigente
          </h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Ranking de dirigentes por % de aprobación sobre {formatNumber(data.total_corpus_comments)} comentarios clasificados.
        </p>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">#</th>
                  <th className="px-4 py-2 text-left font-medium">Dirigente</th>
                  <th className="px-4 py-2 text-left font-medium">Rol</th>
                  <th className="px-4 py-2 text-right font-medium">Followers</th>
                  <th className="px-4 py-2 text-right font-medium">Comments</th>
                  <th className="px-4 py-2 text-right font-medium">Activ. %</th>
                  <th className="px-4 py-2 text-right font-medium">Aprob. %</th>
                  <th className="px-4 py-2 text-right font-medium">Rech. %</th>
                  <th className="px-4 py-2 text-right font-medium">Neutral %</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d, i) => (
                  <tr key={d.dirigente_id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3 text-muted-foreground tabular-nums">{i + 1}</td>
                    <td className="px-4 py-3 font-medium">
                      <Link href={`/dashboard/diagnostico/${d.dirigente_id}`} className="hover:underline">
                        {d.full_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      {d.rol_politico ? (
                        <Badge
                          variant="outline"
                          className={
                            d.rol_politico === "oposicion"
                              ? "border-amber-500/40 text-amber-500"
                              : "border-emerald-500/40 text-emerald-500"
                          }
                        >
                          {d.rol_politico}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{formatNumber(d.total_followers)}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{formatNumber(d.total_comments)}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-medium">{d.pct_activados.toFixed(2)}%</td>
                    <td className="px-4 py-3 text-right tabular-nums text-emerald-500">{d.pct_aprobacion.toFixed(1)}%</td>
                    <td className="px-4 py-3 text-right tabular-nums text-rose-500">{d.pct_rechazo.toFixed(1)}%</td>
                    <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">{d.pct_neutral.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
