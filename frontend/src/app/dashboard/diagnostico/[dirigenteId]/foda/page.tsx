"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ArrowLeft, ArrowRight, AlertTriangle, Lightbulb, Shield, Zap } from "lucide-react";
import { detechnicalize } from "@/lib/labels";
import { renderRichText } from "@/components/render-rich";

interface FodaResponse {
  dirigente_id: number;
  fortalezas: string[];
  oportunidades: string[];
  debilidades: string[];
  amenazas: string[];
  diagnostico_id: number | null;
  generado_at: string | null;
  plan_derivado_id: number | null;
}

function useFoda(dirigenteId: number) {
  return useQuery<FodaResponse>({
    queryKey: ["diagnostico-foda", dirigenteId],
    queryFn: () => api.get<FodaResponse>(`/diagnostico/foda/${dirigenteId}`),
    enabled: dirigenteId > 0,
    staleTime: 1000 * 60 * 5,
  });
}

function Quadrant({
  title,
  icon: Icon,
  items,
  tone,
  emptyHint,
}: {
  title: string;
  icon: typeof Zap;
  items: string[];
  tone: "positive" | "negative";
  emptyHint: string;
}) {
  const cls =
    tone === "positive"
      ? "border-emerald-200 dark:border-emerald-800 bg-emerald-50/40 dark:bg-emerald-950/20"
      : "border-amber-200 dark:border-amber-800 bg-amber-50/40 dark:bg-amber-950/20";
  const titleCls =
    tone === "positive"
      ? "text-emerald-800 dark:text-emerald-200"
      : "text-amber-900 dark:text-amber-200";

  return (
    <Card className={`${cls} flex h-full flex-col`}>
      <CardHeader className="pb-2">
        <CardTitle className={`flex items-center gap-2 text-base ${titleCls}`}>
          <Icon className="h-4 w-4" aria-hidden="true" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1">
        {items.length === 0 ? (
          <p className="text-xs italic text-muted-foreground">{emptyHint}</p>
        ) : (
          <ul className="space-y-2">
            {items.map((it, i) => (
              <li key={i} className="flex gap-2 text-sm leading-relaxed text-foreground/90">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-current opacity-70" />
                <span>{renderRichText(detechnicalize(it))}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export default function FodaPage() {
  const params = useParams<{ dirigenteId: string }>();
  const did = Number(params?.dirigenteId ?? 0);
  const { data, isLoading, error } = useFoda(did);

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-9 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 rounded-md" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <p className="text-sm text-destructive">No fue posible cargar tu FODA. Vuelve a intentar más tarde.</p>
      </div>
    );
  }

  const fechaTxt = data.generado_at
    ? new Date(data.generado_at).toLocaleDateString("es-MX", { day: "numeric", month: "long", year: "numeric" })
    : null;

  return (
    <div className="mx-auto max-w-5xl space-y-6 py-4">
      <header className="space-y-2">
        <Button variant="ghost" size="sm" asChild className="-ml-2 h-7 w-fit px-2">
          <Link href={`/dashboard/diagnostico/${did}`} className="flex items-center gap-1 text-xs text-muted-foreground">
            <ArrowLeft className="h-3 w-3" aria-hidden="true" />
            Volver al diagnóstico
          </Link>
        </Button>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">Tu FODA</h1>
          {fechaTxt && (
            <p className="text-xs text-muted-foreground">Generado el {fechaTxt}</p>
          )}
        </div>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Diagnóstico estratégico de tu presencia digital. Las <span className="font-medium text-foreground">Fortalezas</span> y{" "}
          <span className="font-medium text-foreground">Oportunidades</span> son palancas de crecimiento; las{" "}
          <span className="font-medium text-foreground">Debilidades</span> y{" "}
          <span className="font-medium text-foreground">Amenazas</span> son focos de atención.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Quadrant
          title="Fortalezas"
          icon={Zap}
          items={data.fortalezas}
          tone="positive"
          emptyHint="Aún no se identifican fortalezas con la información disponible."
        />
        <Quadrant
          title="Oportunidades"
          icon={Lightbulb}
          items={data.oportunidades}
          tone="positive"
          emptyHint="Aún no se identifican oportunidades con la información disponible."
        />
        <Quadrant
          title="Debilidades"
          icon={AlertTriangle}
          items={data.debilidades}
          tone="negative"
          emptyHint="No se detectan debilidades en este momento."
        />
        <Quadrant
          title="Amenazas"
          icon={Shield}
          items={data.amenazas}
          tone="negative"
          emptyHint="No se detectan amenazas con la información disponible."
        />
      </div>

      {data.plan_derivado_id && (
        <Card>
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div>
              <p className="text-sm font-medium">Tu plan de acción derivado de este FODA</p>
              <p className="text-xs text-muted-foreground">
                Tareas medibles para apalancar fortalezas, atender debilidades y aprovechar oportunidades.
              </p>
            </div>
            <Button asChild size="sm">
              <Link href={`/dashboard/planes?dirigente=${did}&tab=estrategia`} className="inline-flex items-center gap-2">
                Ver mi plan
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
