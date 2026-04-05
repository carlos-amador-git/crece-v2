import type { SentimentType } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SentimentBadgeProps {
  sentiment: SentimentType;
  score?: number;
  showIcon?: boolean;
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
}: SentimentBadgeProps) {
  const key = sentiment?.toLowerCase() as SentimentType;
  const config = sentimentConfig[key] ?? sentimentConfig.neutral;
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className="gap-1">
      {showIcon && <Icon className="h-3 w-3" />}
      {config.label}
      {score != null && (
        <span className="ml-0.5 tabular-nums opacity-70">{(score * 100).toFixed(0)}%</span>
      )}
    </Badge>
  );
}
