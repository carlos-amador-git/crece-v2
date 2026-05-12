"use client";

import Link from "next/link";
import { useAceptacionOverview } from "@/lib/api/hooks/use-aceptacion";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber } from "@/lib/utils";
import { Ghost } from "lucide-react";

export default function FantasmasPage() {
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
            No se pudo cargar el detalle de fantasmas.
          </CardContent>
        </Card>
      </div>
    );
  }

  const rows = [...data.dirigentes].sort((a, b) => b.pct_fantasma - a.pct_fantasma);
  const totalFollowers = rows.reduce((s, r) => s + r.total_followers, 0);
  const totalCommenters = rows.reduce((s, r) => s + r.unique_commenters, 0);
  const totalFantasmas = totalFollowers - totalCommenters;

  return (
    <div className="space-y-6 p-6">
      <div>
        <div className="flex items-center gap-2">
          <Ghost className="h-6 w-6 text-accent" />
          <h1 className="font-heading text-2xl font-bold tracking-tight">Fantasmas</h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Followers sin señales de vida — no comentan, no interactúan. Estimado:{" "}
          {formatNumber(totalFantasmas)} fantasmas en una audiencia de {formatNumber(totalFollowers)} followers.
        </p>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Dirigente</th>
                  <th className="px-4 py-2 text-right font-medium">Followers</th>
                  <th className="px-4 py-2 text-right font-medium">Comentaristas únicos</th>
                  <th className="px-4 py-2 text-right font-medium">Fantasmas est.</th>
                  <th className="px-4 py-2 text-right font-medium">% Fantasma</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => {
                  const fantasmas = Math.max(d.total_followers - d.unique_commenters, 0);
                  return (
                    <tr key={d.dirigente_id} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="px-4 py-3 font-medium">
                        <Link href={`/dashboard/diagnostico/${d.dirigente_id}`} className="hover:underline">
                          {d.full_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{formatNumber(d.total_followers)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{formatNumber(d.unique_commenters)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{formatNumber(fantasmas)}</td>
                      <td
                        className={
                          "px-4 py-3 text-right tabular-nums font-medium " +
                          (d.pct_fantasma > 99
                            ? "text-rose-500"
                            : d.pct_fantasma > 95
                              ? "text-amber-500"
                              : "text-emerald-500")
                        }
                      >
                        {d.pct_fantasma.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
