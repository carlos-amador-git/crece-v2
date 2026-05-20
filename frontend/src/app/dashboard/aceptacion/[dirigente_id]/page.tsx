"use client";

/**
 * Detail page por dirigente. Reusa `DirigenteDetailContent`.
 *
 * Pagina pensada para drill-down desde Battle Card admin N>1 ·
 * conserva botón "← Resumen" para volver a la vista comparativa.
 *
 * Refactor 2026-05-20 (D-ACEPTACION-DEDUPE-2026-05-20) · CEO clarificó
 * que las páginas de Aceptación tenían duplicación masiva. Esta es ahora
 * un wrapper delgado del componente compartido.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useAceptacionOverview } from "@/lib/api/hooks/use-aceptacion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DirigenteDetailContent } from "@/components/aceptacion/dirigente-detail-content";
import { ArrowLeft } from "lucide-react";

export default function AceptacionDirigentePage() {
  const params = useParams();
  const id = parseInt(params.dirigente_id as string, 10);

  const { data: overview, isLoading } = useAceptacionOverview();
  const row = overview?.dirigentes.find((d) => d.dirigente_id === id);

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-12 w-72" />
        <Skeleton className="h-[60vh]" />
      </div>
    );
  }

  if (!row) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            Dirigente no encontrado o sin acceso.{" "}
            <Link href="/dashboard/aceptacion" className="underline">
              Volver al resumen
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start gap-3">
        <Link href="/dashboard/aceptacion">
          <Button variant="ghost" size="sm" className="mt-1 gap-1">
            <ArrowLeft className="h-4 w-4" /> Resumen
          </Button>
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-2xl font-bold tracking-tight">{row.full_name}</h1>
            {row.rol_politico && (
              <Badge
                variant="outline"
                className={
                  row.rol_politico === "oposicion"
                    ? "border-amber-500/40 text-amber-500"
                    : "border-emerald-500/40 text-emerald-500"
                }
              >
                {row.rol_politico === "oficialismo" ? "Gobierno" : row.rol_politico}
              </Badge>
            )}
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Índice de Aceptación — vista detallada
          </p>
        </div>
      </div>

      <DirigenteDetailContent dirigenteId={id} />
    </div>
  );
}
