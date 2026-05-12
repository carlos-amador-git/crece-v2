"use client";

import { Check, ExternalLink, Loader2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import {
  usePostsDirigente,
  type PostDirigente,
  type Recomendacion,
} from "@/lib/api/hooks/use-recomendaciones";

interface Props {
  recomendacion: Recomendacion | null;
  onClose: () => void;
  onConfirm: (post: PostDirigente) => void;
  isLoading?: boolean;
}

export function PostEjecutorDialog({
  recomendacion,
  onClose,
  onConfirm,
  isLoading,
}: Props) {
  const [seleccionado, setSeleccionado] = useState<PostDirigente | null>(null);
  const open = !!recomendacion;
  const { data: posts, isLoading: postsLoading } = usePostsDirigente(
    recomendacion?.dirigente_id,
    30,
  );

  const handleConfirm = () => {
    if (!seleccionado) return;
    onConfirm(seleccionado);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          setSeleccionado(null);
          onClose();
        }
      }}
    >
      <DialogContent data-testid="dialog-post-ejecutor" className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Vincular post ejecutor</DialogTitle>
          <DialogDescription>
            Selecciona el post con el que ejecutaste esta recomendación para iniciar el
            seguimiento de {recomendacion?.ventana_duracion_dias ?? 14} días.
          </DialogDescription>
        </DialogHeader>

        {postsLoading ? (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando últimos posts…
          </div>
        ) : !posts || posts.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No encontramos posts recientes del dirigente. Publica primero y vuelve a
            intentar.
          </p>
        ) : (
          <ScrollArea className="h-[320px] rounded-md border">
            <ul className="divide-y" data-testid="lista-posts-ejecutor">
              {posts.map((p) => {
                const selected = seleccionado?.id === p.id;
                return (
                  <li key={p.id}>
                    <button
                      type="button"
                      data-testid={`post-ejecutor-option-${p.id}`}
                      onClick={() => setSeleccionado(p)}
                      className={cn(
                        "flex w-full items-start gap-3 p-3 text-left transition-colors",
                        selected
                          ? "bg-accent/10"
                          : "hover:bg-muted/60",
                      )}
                    >
                      <div
                        className={cn(
                          "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border",
                          selected
                            ? "border-accent bg-accent text-accent-foreground"
                            : "border-muted-foreground/40",
                        )}
                      >
                        {selected && <Check className="h-3 w-3" />}
                      </div>
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant="outline" className="text-[10px] uppercase">
                            {p.platform}
                          </Badge>
                          <span>
                            {(() => {
                              try {
                                return new Intl.DateTimeFormat("es-MX", {
                                  day: "numeric",
                                  month: "short",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                }).format(new Date(p.published_at));
                              } catch {
                                return p.published_at;
                              }
                            })()}
                          </span>
                          {p.url && (
                            <a
                              href={p.url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex items-center gap-1 hover:text-accent"
                            >
                              Ver
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                        <p className="line-clamp-2 text-sm">{p.content}</p>
                        <div className="flex gap-3 text-[11px] text-muted-foreground">
                          <span>❤ {p.likes}</span>
                          <span>💬 {p.comments}</span>
                          <span>↗ {p.shares}</span>
                        </div>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </ScrollArea>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!seleccionado || isLoading}
            data-testid="btn-confirmar-post-ejecutor"
          >
            {isLoading ? "Vinculando…" : "Vincular y activar seguimiento"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
