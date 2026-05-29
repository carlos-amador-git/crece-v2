"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { Eye } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useAceptacionOverview } from "@/lib/api/hooks/use-aceptacion";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import WatchedProfilesTab from "@/components/aceptacion/watched-profiles-tab";

function FansYPerfilesInner() {
  const { data: overview, isLoading, error } = useAceptacionOverview();
  const { user } = useAuth();
  const [observedDirigenteId, setObservedDirigenteId] = useState<number | null>(null);
  const [didAutoInit, setDidAutoInit] = useState(false);

  const dirigentesList = useMemo(
    () => overview?.dirigentes ?? [],
    [overview],
  );

  const userDirigenteId = (user as { dirigente_id?: number } | null)?.dirigente_id ?? null;
  const userOwnDirigenteHidden =
    userDirigenteId !== null &&
    dirigentesList.length > 0 &&
    !dirigentesList.some((d) => d.dirigente_id === userDirigenteId);

  useEffect(() => {
    if (didAutoInit) return;
    if (dirigentesList.length === 0) return;
    if (userDirigenteId !== null) {
      // Viewer logueado tiene un dirigente_id propio: solo lo seleccionamos si
      // está en la lista accesible. Si NO está (p.ej. el dirigente aún no tiene
      // data scrapeada y por eso el endpoint /overview lo excluye), dejamos
      // observedDirigenteId = null y el render muestra un empty-state explícito.
      // NO caemos al primer dirigente de la lista — eso sería un scope leak
      // donde el viewer vería data de OTRO dirigente como si fuera la suya
      // (anti-mock D-ANTI-MOCK-1: cero data inventada/cruzada visible).
      const selfMatch = dirigentesList.find((d) => d.dirigente_id === userDirigenteId);
      if (selfMatch) {
        setObservedDirigenteId(selfMatch.dirigente_id);
      }
    } else {
      // Staff (admin/analyst) sin dirigente_id propio: default al primero está
      // bien porque exploran transversalmente.
      setObservedDirigenteId(dirigentesList[0].dirigente_id);
    }
    setDidAutoInit(true);
  }, [user, dirigentesList, didAutoInit, userDirigenteId]);

  const observedName = useMemo(() => {
    if (observedDirigenteId === null) return "";
    const d = dirigentesList.find((x) => x.dirigente_id === observedDirigenteId);
    return d?.full_name ?? `Dirigente #${observedDirigenteId}`;
  }, [observedDirigenteId, dirigentesList]);

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-[60vh] w-full" />
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No se pudo cargar la lista de dirigentes.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <div className="flex items-center gap-2">
          <Eye className="h-6 w-6 text-accent" />
          <h1 className="font-heading text-2xl font-bold tracking-tight">
            Fans y Perfiles
          </h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Lista nominada de cuentas a monitorear. Engagement detectado automáticamente
          desde el scraping.
        </p>
      </div>

      {dirigentesList.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            Sin dirigentes accesibles en tu organización. Contacta al administrador.
          </CardContent>
        </Card>
      ) : userOwnDirigenteHidden ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            Tu perfil aún no tiene data scrapeada disponible. Cuando el monitoreo
            inicie para tu dirigente, aparecerá aquí.
          </CardContent>
        </Card>
      ) : observedDirigenteId === null ? (
        <Skeleton className="h-10 w-[280px]" />
      ) : (
        <>
          {dirigentesList.length > 1 ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">Dirigente:</span>
              <Select
                value={String(observedDirigenteId)}
                onValueChange={(v) => setObservedDirigenteId(Number(v))}
              >
                <SelectTrigger className="w-[280px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {dirigentesList.map((d) => (
                    <SelectItem key={d.dirigente_id} value={String(d.dirigente_id)}>
                      {d.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="flex items-center gap-3" data-testid="dirigente-readonly">
              <span className="text-sm text-muted-foreground">Dirigente:</span>
              <span className="text-sm font-semibold text-foreground">{observedName}</span>
            </div>
          )}

          <WatchedProfilesTab
            dirigenteId={observedDirigenteId}
            dirigenteName={observedName}
          />
        </>
      )}
    </div>
  );
}

export default function FansYPerfilesPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[60vh] w-full" />}>
      <FansYPerfilesInner />
    </Suspense>
  );
}
