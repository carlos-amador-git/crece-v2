"use client";

/**
 * /dashboard/aceptacion/fans · Fans y Perfiles
 *
 * Ruta dedicada (sidebar entry "Fans y Perfiles") que reusa el componente
 * `WatchedProfilesTab` — antes embebido como 3er tab dentro de
 * /dashboard/aceptacion/fantasmas. CEO 2026-05-19: subir de tab a entrada
 * propia para mejor descubribilidad (request cliente Misael).
 *
 * El tab original en /aceptacion/fantasmas queda como espejo (mismo
 * componente · cero refactor del flujo existente · sin romper bookmarks).
 */
import { useAuth } from "@/lib/auth";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Eye } from "lucide-react";
import WatchedProfilesTab from "@/components/aceptacion/watched-profiles-tab";

export default function FansPage() {
  const { user } = useAuth();
  const userWithDirigente = user as { dirigente_id?: number; full_name?: string } | null;
  const dirigenteId = userWithDirigente?.dirigente_id ?? null;

  // Si el user es un dirigente, su nombre lo usamos directo. Si es admin/consultor
  // sin dirigente_id, mostramos empty state pidiendo selección.
  const { data: dirigentesData } = useDirigentes(
    dirigenteId ? { per_page: 50 } : undefined
  );
  const dirigenteName =
    dirigentesData?.items?.find((d) => d.id === dirigenteId)?.full_name ??
    userWithDirigente?.full_name ??
    "Dirigente";

  if (!dirigenteId) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Fans y Perfiles
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Selecciona un dirigente desde el menú lateral para ver su lista
              nominada de fans y perfiles observados.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <WatchedProfilesTab dirigenteId={dirigenteId} dirigenteName={dirigenteName} />
    </div>
  );
}
