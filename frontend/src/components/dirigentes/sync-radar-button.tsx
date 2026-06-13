"use client";

import { useState } from "react";
import { useTriggerSync, useSyncStatus } from "@/lib/api/hooks/use-radar-sync";
import { Button } from "@/components/ui/button";
import { RefreshCw, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";

export function SyncRadarButton({ dirigenteId }: { dirigenteId: number | string }) {
  const { user } = useAuth();
  const { mutate: trigger, isPending: isTriggering } = useTriggerSync();
  const { data: status } = useSyncStatus(dirigenteId);
  const [message, setMessage] = useState<string | null>(null);

  // Solo ADMIN y ANALYST pueden ver/disparar la sincronización (ADR-005)
  if (user?.role !== "admin" && user?.role !== "analyst") {
    return null;
  }

  const isActive = status?.status === "RUNNING" || status?.status === "RECEIVED";

  const handleSync = () => {
    setMessage(null);
    trigger(dirigenteId, {
      onSuccess: (data) => {
        if (data.sin_novedades) {
          setMessage("Sin novedades: datos ya al día");
          setTimeout(() => setMessage(null), 5000);
        } else {
          setMessage("Sincronización iniciada");
        }
      },
      onError: (error: any) => {
        setMessage(error?.response?.data?.detail || "Error al sincronizar");
        setTimeout(() => setMessage(null), 5000);
      },
    });
  };

  return (
    <div className="flex items-center gap-3">
      {isActive && (
        <Badge variant="secondary" className="gap-1.5 animate-pulse bg-blue-500/10 text-blue-600 border-blue-500/20">
          <Loader2 className="h-3 w-3 animate-spin" />
          Procesando bundle...
        </Badge>
      )}

      {message && (
        <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground animate-in fade-in duration-300">
          {message}
        </span>
      )}

      <Button
        variant="outline"
        size="sm"
        className="h-8 gap-2 text-[10px] uppercase font-bold tracking-widest border-primary/20 hover:bg-primary/5 hover:text-primary transition-all"
        onClick={handleSync}
        disabled={isActive || isTriggering}
      >
        {isTriggering ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <RefreshCw className={`h-3.5 w-3.5 ${isActive ? "animate-spin" : ""}`} />
        )}
        Sincronizar con RADAR
      </Button>
    </div>
  );
}
