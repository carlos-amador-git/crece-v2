import type { SentimentType } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  adjustSentimentLabelForRole,
  adjustSentimentScoreForRole,
} from "@/lib/politica/sentiment";

interface SentimentBadgeProps {
  sentiment: string | null | undefined;
  score?: number | null;
  showIcon?: boolean;
  /** Partido del dirigente · activa ajuste por rol D-23-G cuando se provee. */
  partido?: string | null | undefined;
}

const sentimentConfig: Record<
  SentimentType,
  { label: string; variant: "success" | "danger" | "warning"; icon: typeof TrendingUp }
> = {
  positive: { label: "Positivo", variant: "success", icon: TrendingUp },
  negative: { label: "Negativo", variant: "danger", icon: TrendingDown },
  neutral: { label: "Neutral", variant: "warning", icon: Minus },
};

export function SentimentBadge({
  sentiment,
  score,
  showIcon = true,
  partido,
}: SentimentBadgeProps) {
  // D-23-G · ajuste por rol si se conoce el partido (oposición → flip).
  const adjustedLabel = adjustSentimentLabelForRole(sentiment, partido);
  const adjustedScore = adjustSentimentScoreForRole(score ?? null, partido);

  const key = (adjustedLabel ?? "").toLowerCase() as SentimentType;
  const config = sentimentConfig[key] ?? sentimentConfig.neutral;
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className="gap-1">
      {showIcon && <Icon className="h-3 w-3" />}
      {config.label}
      {adjustedScore != null && (
        <span className="ml-0.5 tabular-nums opacity-70">
          {(adjustedScore * 100).toFixed(0)}%
        </span>
      )}
    </Badge>
  );
}
