import { cn, getIpdColor } from "@/lib/utils";

interface IpdScoreBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

export function IpdScoreBadge({ score, size = "md" }: IpdScoreBadgeProps) {
  const sizeClasses = {
    sm: "h-6 w-6 text-xs",
    md: "h-8 w-8 text-sm",
    lg: "h-10 w-10 text-base",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded-md border font-semibold tabular-nums",
        getIpdColor(score),
        sizeClasses[size]
      )}
      aria-label={`Indice de Penetracion Digital: ${score.toFixed(1)}`}
    >
      {score.toFixed(1)}
    </div>
  );
}
