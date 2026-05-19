import type { SentimentType } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  adjustSentimentLabelForRole,
  adjustSentimentScoreForRole,
  deriveSentimentLabelFromScore,
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
  const adjustedScore = adjustSentimentScoreForRole(score ?? null, partido);

  // Label deriva del score flipado cuando hay score (evita inconsistencia
  // del tipo "Neutral -50%" que surgía de thresholds 0.4/0.6 aplicados al
  // raw score en rango -1..+1 antes del flip). Sin score, fallback al
  // label prop ajustado por rol.
  const labelFromScore = deriveSentimentLabelFromScore(adjustedScore);
  const labelFromProp = adjustSentimentLabelForRole(sentiment, partido);
  const finalLabel = labelFromScore ?? labelFromProp;

  const key = (finalLabel ?? "").toLowerCase() as SentimentType;
  const config = sentimentConfig[key as SentimentType];

  // P0 #2: si no hay clasificación real (sentiment NULL + score NULL), no
  // inventamos un fallback "Neutral". Mostrar badge muted "Sin clasificar"
  // para que el usuario sepa que el dato falta, no que es neutral.
  if (!config) {
    return (
      <Badge
        variant="outline"
        className="gap-1 border-dashed text-muted-foreground"
        title="Post sin clasificación NLP"
      >
        {showIcon && <Minus className="h-3 w-3" aria-hidden="true" />}
        Sin clasificar
      </Badge>
    );
  }

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
