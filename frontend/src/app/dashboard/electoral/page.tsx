"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Map } from "lucide-react";

export default function ElectoralPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-heading text-2xl font-bold">Mapa Electoral</h1>
        <p className="text-sm text-muted-foreground">
          Visualizacion geoespacial de intencion de voto por seccion electoral
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Map className="mb-4 h-12 w-12 text-muted-foreground/40" />
          <h2 className="mb-2 font-heading text-lg font-semibold">
            Mapa en desarrollo
          </h2>
          <p className="max-w-md text-sm text-muted-foreground">
            El mapa electoral estara disponible cuando se carguen los shapefiles
            de secciones electorales del INE. Los datos de encuestas y scoring
            ya estan listos para visualizarse.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
