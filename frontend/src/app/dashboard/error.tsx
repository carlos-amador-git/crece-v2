"use client";

import { useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center p-6">
      <Card className="max-w-md">
        <CardContent className="flex flex-col items-center py-10 text-center">
          <AlertTriangle className="mb-4 h-10 w-10 text-amber-500" />
          <h2 className="mb-2 font-heading text-lg font-semibold">
            Error al cargar esta seccion
          </h2>
          <p className="mb-6 text-sm text-muted-foreground">
            Es posible que el servidor no este disponible o los datos aun no esten configurados.
          </p>
          <Button onClick={reset} variant="outline">
            Reintentar
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
