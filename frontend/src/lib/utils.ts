import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString("es-MX");
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("es-MX", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(date));
}

export function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const then = new Date(date);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Ahora";
  if (diffMins < 60) return `hace ${diffMins}m`;
  if (diffHours < 24) return `hace ${diffHours}h`;
  if (diffDays < 7) return `hace ${diffDays}d`;
  return formatDate(date);
}

export function getSentimentColor(sentiment: string): string {
  switch (sentiment) {
    case "positive":
      return "text-emerald-500";
    case "negative":
      return "text-red-500";
    case "neutral":
      return "text-amber-500";
    default:
      return "text-muted-foreground";
  }
}

export function getSentimentBgColor(sentiment: string): string {
  switch (sentiment) {
    case "positive":
      return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
    case "negative":
      return "bg-red-500/10 text-red-600 dark:text-red-400";
    case "neutral":
      return "bg-amber-500/10 text-amber-600 dark:text-amber-400";
    default:
      return "bg-muted text-muted-foreground";
  }
}

export function getIpdColor(score: number): string {
  if (score >= 7) return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
  if (score >= 4) return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
  return "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20";
}

export function getIntentionColor(aFavor: number, enContra: number): string {
  if (aFavor > 60) return "#22c55e";
  if (enContra > 60) return "#ef4444";
  return "#eab308";
}
