import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { Sparkles } from "lucide-react";
import type {
  Contenido,
  ContenidoFormato,
  ContenidoEstado,
} from "@/lib/api/hooks/use-contenido";

const ESTADO_NEXT: Record<ContenidoEstado, ContenidoEstado | null> = {
  borrador: "revisado",
  revisado: "aprobado",
  aprobado: "publicado",
  publicado: null,
};

function estadoVariant(e: ContenidoEstado) {
  const m: Record<string, "secondary" | "warning" | "success" | "default"> = {
    borrador: "secondary", revisado: "warning", aprobado: "success", publicado: "default",
  };
  return m[e] ?? "secondary";
}

function formatoVariant(f: ContenidoFormato) {
  if (f === "reel" || f === "video") return "default" as const;
  if (f === "story") return "warning" as const;
  return "outline" as const;
}

interface ContentCardProps {
  item: Contenido;
  onAdvance: (id: number, estado: ContenidoEstado) => void;
  advancing: boolean;
}

export function ContentCard({ item, onAdvance, advancing }: ContentCardProps) {
  const next = ESTADO_NEXT[item.estado];

  return (
    <Card className="card-elevated">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant={formatoVariant(item.formato)}>{item.formato}</Badge>
              <Badge variant={estadoVariant(item.estado)}>{item.estado}</Badge>
              {item.dirigente_nombre && (
                <span className="text-xs text-muted-foreground">{item.dirigente_nombre}</span>
              )}
            </div>
            <h3 className="font-heading text-base font-semibold leading-tight">{item.tema}</h3>
            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{item.contenido}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              {formatDate(item.created_at)}
              {item.modelo_ia && (
                <span className="ml-2 inline-flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />{item.modelo_ia}
                </span>
              )}
            </p>
          </div>
          {next && (
            <Button size="sm" variant="outline" disabled={advancing} onClick={() => onAdvance(item.id, next)} className="shrink-0">
              {next}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
