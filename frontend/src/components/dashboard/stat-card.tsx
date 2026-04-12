import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: number; label?: string };
  description?: string;
  variant?: "default" | "compact" | "hero";
  className?: string;
}

export function StatCard({
  label, value, icon: Icon, trend, description, variant = "default", className,
}: StatCardProps) {
  const isHero = variant === "hero";
  const isCompact = variant === "compact";

  return (
    <div className={cn(
      "card-elevated flex items-center gap-3 rounded-lg bg-card",
      isHero && "col-span-2 flex-col items-start p-6",
      isCompact && "p-2.5 gap-2",
      !isHero && !isCompact && "p-3",
      className,
    )}>
      {Icon && (
        <div className={cn(
          "flex shrink-0 items-center justify-center rounded-md bg-muted",
          isHero ? "h-10 w-10" : isCompact ? "h-6 w-6" : "h-8 w-8",
        )}>
          <Icon className={cn(
            "text-muted-foreground",
            isHero ? "h-5 w-5" : isCompact ? "h-3.5 w-3.5" : "h-4 w-4",
          )} />
        </div>
      )}
      <div className={isHero ? "mt-4 w-full" : ""}>
        <p className={cn(
          "font-bold tabular-nums",
          isHero ? "text-3xl" : isCompact ? "text-base" : "text-lg",
        )}>{value}</p>
        <p className={cn(
          "text-muted-foreground",
          isHero ? "text-sm" : "text-xs",
        )}>{label}</p>
        {trend && (
          <p className={cn(
            "text-xs mt-1",
            trend.value >= 0 ? "text-emerald-600" : "text-red-600",
          )}>
            {trend.value >= 0 ? "\u2191" : "\u2193"} {Math.abs(trend.value)}%
            {trend.label && <span className="text-muted-foreground ml-1">{trend.label}</span>}
          </p>
        )}
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </div>
    </div>
  );
}
