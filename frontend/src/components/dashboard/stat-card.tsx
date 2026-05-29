import { type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type StatCardAccent = "default" | "good" | "warn" | "bad";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: number; label?: string };
  description?: string;
  hint?: string;
  accent?: StatCardAccent;
  variant?: "default" | "compact" | "hero";
  className?: string;
}

const ACCENT_CLASS: Record<StatCardAccent, string> = {
  default: "text-foreground",
  good: "text-emerald-600 dark:text-emerald-400",
  warn: "text-amber-600 dark:text-amber-400",
  bad: "text-rose-600 dark:text-rose-400",
};

/**
 * KPI / stat card canónico de CRECE v2.
 *
 * Reemplazó (2026-05-16 · Sprint C):
 * - `KpiCard` (dead code)
 * - `StatCard` local en `aceptacion/watched-profiles-tab.tsx`
 * - `StatCardSkeleton` ad-hoc en `participacion/page.tsx`
 *
 * NO reemplaza el `StatCard` de `landing/stats.tsx` — ese es un counter
 * animado específico de marketing y se mantiene separado por diseño.
 *
 * Variants:
 * - `default` · uso típico en dashboards
 * - `compact` · padding reducido, fila densa
 * - `hero` · col-span-2, padding amplio
 *
 * Accents (color del value):
 * - `default` · color base
 * - `good` · verde (positivo, completado, alineado)
 * - `warn` · ámbar (atención, en proceso)
 * - `bad` · rojo (negativo, contradicho, riesgo)
 */
export function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  description,
  hint,
  accent = "default",
  variant = "default",
  className,
}: StatCardProps) {
  const isHero = variant === "hero";
  const isCompact = variant === "compact";

  return (
    <Card
      className={cn(
        "card-elevated overflow-hidden border-border/60 shadow-sm",
        className,
      )}
    >
      <CardContent
        className={cn(
          "flex items-center gap-3",
          isHero && "col-span-2 flex-col items-start p-6",
          isCompact && "p-2.5 gap-2",
          !isHero && !isCompact && "p-4",
        )}
      >
        {Icon && (
          <div
            className={cn(
              "flex shrink-0 items-center justify-center rounded-md bg-muted",
              isHero ? "h-10 w-10" : isCompact ? "h-6 w-6" : "h-8 w-8",
            )}
          >
            <Icon
              className={cn(
                "text-muted-foreground",
                isHero ? "h-5 w-5" : isCompact ? "h-3.5 w-3.5" : "h-4 w-4",
              )}
              aria-hidden="true"
            />
          </div>
        )}
        <div className={isHero ? "mt-4 w-full" : "flex-1 min-w-0"}>
          <div
            className={cn(
              "flex items-center justify-between text-xs text-muted-foreground",
              isHero && "text-sm",
            )}
          >
            <span className={cn(!isHero && "uppercase tracking-wider")}>{label}</span>
          </div>
          <p
            className={cn(
              "font-bold tabular-nums tracking-tight mt-0.5",
              isHero ? "text-3xl" : isCompact ? "text-base" : "text-2xl",
              ACCENT_CLASS[accent],
            )}
          >
            {value}
          </p>
          {trend && (
            <p
              className={cn(
                "text-xs mt-1",
                trend.value >= 0
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-rose-600 dark:text-rose-400",
              )}
            >
              {trend.value >= 0 ? "↑" : "↓"} {Math.abs(trend.value)}%
              {trend.label && (
                <span className="text-muted-foreground ml-1">{trend.label}</span>
              )}
            </p>
          )}
          {(hint || description) && (
            <p className="text-xs text-muted-foreground mt-1">
              {hint ?? description}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function StatCardSkeleton({
  variant = "default",
}: {
  variant?: "default" | "compact" | "hero";
}) {
  const heightClass =
    variant === "hero" ? "h-[120px]" : variant === "compact" ? "h-[48px]" : "h-[72px]";
  return <Skeleton className={cn("rounded-lg", heightClass)} />;
}
