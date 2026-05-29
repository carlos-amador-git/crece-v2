"use client";

/**
 * S5 — Dual labels badge para mostrar el origen de la clasificación NLP en
 * dashboards existentes. Renderiza:
 *   - "Sistema" si review_status === 'unreviewed' o null
 *   - "Confirmado" si review_status === 'confirmed'
 *   - "Editado por <actor>" si review_status === 'edited' (con tooltip from→to si se proporciona)
 */

import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Bot, Check, UserCheck } from "lucide-react";
import type { ReviewStatus } from "@/lib/api/hitl";

export interface ReviewStatusBadgeProps {
  status: ReviewStatus | null | undefined;
  /** Nombre del actor que editó (si edited). */
  actorName?: string | null;
  /** Optional from/to para tooltip de edits. */
  fromTono?: string | null;
  toTono?: string | null;
  fromTarget?: string | null;
  toTarget?: string | null;
  className?: string;
}

export function ReviewStatusBadge({
  status,
  actorName,
  fromTono,
  toTono,
  fromTarget,
  toTarget,
  className,
}: ReviewStatusBadgeProps) {
  const effective = status ?? "unreviewed";

  if (effective === "confirmed") {
    return (
      <Badge
        variant="outline"
        className={`px-1.5 py-0 text-[10px] gap-1 border-emerald-500/40 text-emerald-600 dark:text-emerald-400 ${className ?? ""}`}
      >
        <Check className="h-2.5 w-2.5" />
        Confirmado
      </Badge>
    );
  }

  if (effective === "edited") {
    const label = actorName ? `Editado por ${actorName}` : "Editado";
    const hasTooltip = Boolean(
      (fromTono && toTono && fromTono !== toTono) ||
        (fromTarget && toTarget && fromTarget !== toTarget)
    );
    const badge = (
      <Badge
        variant="outline"
        className={`px-1.5 py-0 text-[10px] gap-1 border-blue-500/40 text-blue-600 dark:text-blue-400 ${className ?? ""}`}
      >
        <UserCheck className="h-2.5 w-2.5" />
        {label}
      </Badge>
    );
    if (!hasTooltip) return badge;
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <span>{badge}</span>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs text-xs">
            <div className="space-y-0.5">
              {fromTono && toTono && fromTono !== toTono && (
                <div>
                  <span className="text-muted-foreground">Tono: </span>
                  <span className="line-through opacity-70">{fromTono}</span>
                  <span className="mx-1">→</span>
                  <span className="font-medium">{toTono}</span>
                </div>
              )}
              {fromTarget && toTarget && fromTarget !== toTarget && (
                <div>
                  <span className="text-muted-foreground">Target: </span>
                  <span className="line-through opacity-70">{fromTarget}</span>
                  <span className="mx-1">→</span>
                  <span className="font-medium">{toTarget}</span>
                </div>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // unreviewed
  return (
    <Badge
      variant="outline"
      className={`px-1.5 py-0 text-[10px] gap-1 border-muted-foreground/30 text-muted-foreground ${className ?? ""}`}
    >
      <Bot className="h-2.5 w-2.5" />
      Sistema
    </Badge>
  );
}
