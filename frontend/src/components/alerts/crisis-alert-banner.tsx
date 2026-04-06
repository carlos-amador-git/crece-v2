"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertTriangle,
  AlertOctagon,
  ShieldAlert,
  X,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { CrisisSeverity } from "@/hooks/use-crisis-alerts";

/* ────────────────────────────────────────────────────────────
 * CrisisAlertBanner
 *
 * Inline alert banner for the dashboard. Shows when a
 * dirigente's sentiment drops below threshold.
 *
 * Severity mapping:
 *   crisis  (<= -0.5) — red background, urgent
 *   warning (-0.5 to -0.2) — amber background, attention
 *   ok      (> -0.2) — not rendered
 * ──────────────────────────────────────────────────────────── */

interface CrisisAlertBannerProps {
  dirigente_name: string;
  sentiment_score: number;
  platform: string;
  post_content_preview: string;
  severity: CrisisSeverity;
  post_url?: string;
  onViewDetail?: () => void;
  onDismiss?: () => void;
}

const severityConfig = {
  crisis: {
    icon: AlertOctagon,
    label: "Crisis",
    badgeVariant: "danger" as const,
    containerClass:
      "border-red-500/30 bg-red-50/80 dark:border-red-500/20 dark:bg-red-950/30",
    iconClass: "text-red-600 dark:text-red-400",
    barClass: "bg-red-500",
  },
  warning: {
    icon: ShieldAlert,
    label: "Advertencia",
    badgeVariant: "warning" as const,
    containerClass:
      "border-amber-500/30 bg-amber-50/80 dark:border-amber-500/20 dark:bg-amber-950/30",
    iconClass: "text-amber-600 dark:text-amber-400",
    barClass: "bg-amber-500",
  },
  ok: {
    icon: AlertTriangle,
    label: "Normal",
    badgeVariant: "success" as const,
    containerClass:
      "border-emerald-500/30 bg-emerald-50/80 dark:border-emerald-500/20 dark:bg-emerald-950/30",
    iconClass: "text-emerald-600 dark:text-emerald-400",
    barClass: "bg-emerald-500",
  },
} as const;

export function CrisisAlertBanner({
  dirigente_name,
  sentiment_score,
  platform,
  post_content_preview,
  severity,
  post_url,
  onViewDetail,
  onDismiss,
}: CrisisAlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || severity === "ok") return null;

  const config = severityConfig[severity];
  const Icon = config.icon;

  function handleDismiss() {
    setDismissed(true);
    onDismiss?.();
  }

  return (
    <Card
      className={cn(
        "relative overflow-hidden border transition-all duration-300",
        "animate-in fade-in-0 slide-in-from-top-2",
        config.containerClass
      )}
      role="alert"
      aria-live="assertive"
    >
      {/* Severity indicator bar */}
      <div
        className={cn("absolute inset-y-0 left-0 w-1", config.barClass)}
        aria-hidden="true"
      />

      <CardContent className="flex items-start gap-3 p-4 pl-5">
        {/* Icon */}
        <div className={cn("mt-0.5 shrink-0", config.iconClass)}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1 space-y-1.5">
          {/* Header row */}
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={config.badgeVariant}>{config.label}</Badge>
            <span className="text-sm font-semibold text-foreground">
              {dirigente_name}
            </span>
            <Badge variant="outline" className="capitalize">
              {platform}
            </Badge>
            <span
              className="tabular-nums text-xs font-medium text-muted-foreground"
              data-numeric="true"
            >
              Score: {sentiment_score.toFixed(2)}
            </span>
          </div>

          {/* Post preview */}
          <p className="line-clamp-2 text-sm text-foreground/80">
            {post_content_preview}
          </p>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            {onViewDetail && (
              <Button
                variant="outline"
                size="sm"
                onClick={onViewDetail}
                className="h-7 text-xs"
              >
                Ver detalle
              </Button>
            )}
            {post_url && (
              <Button
                variant="ghost"
                size="sm"
                asChild
                className="h-7 text-xs"
              >
                <a
                  href={post_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="mr-1 h-3 w-3" />
                  Ver publicacion
                </a>
              </Button>
            )}
          </div>
        </div>

        {/* Dismiss button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={handleDismiss}
          className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground"
          aria-label="Descartar alerta"
        >
          <X className="h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  );
}
