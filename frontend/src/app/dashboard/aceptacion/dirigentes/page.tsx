"use client";

import { useAceptacionOverview } from "@/lib/api/hooks/use-aceptacion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { IASummaryCard } from "@/components/dashboard/ia-summary-card";
import { UserSquare2 } from "lucide-react";

export default function AceptacionDirigentesPage() {
  const { data, isLoading, error } = useAceptacionOverview();

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-48" />)}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No se pudo cargar los dirigentes.
          </CardContent>
        </Card>
      </div>
    );
  }

  const rows = data.dirigentes;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-2">
        <UserSquare2 className="h-6 w-6 text-accent" />
        <h1 className="font-heading text-2xl font-bold tracking-tight">
          Por dirigente
        </h1>
      </div>

      <div className={`grid grid-cols-1 gap-4 ${rows.length === 1 ? "" : "md:grid-cols-2 xl:grid-cols-3"}`}>
        {rows.map((d) => (
          <IASummaryCard key={d.dirigente_id} dirigenteId={d.dirigente_id} />
        ))}
      </div>
    </div>
  );
}
