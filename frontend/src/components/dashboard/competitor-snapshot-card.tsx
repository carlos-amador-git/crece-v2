"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";
import { formatNumber } from "@/lib/utils";
import { Swords, TrendingUp, Heart, Users } from "lucide-react";

/**
 * Static demo data for MC-CDMX org.
 * Matches seeded competitors: Marti Batres (MORENA) and Santiago Taboada (PAN).
 * Will be replaced by /benchmark/comparison API call in a future sprint.
 */
const MC_CDMX_SLUG = "mc-cdmx";

interface CompetitorProfile {
  nombre: string;
  partido: string;
  followers: number;
  engagement: number; // percentage 0-100
  sentiment: number;  // -1 to 1 scale
}

const DEMO_DIRIGENTE: CompetitorProfile = {
  nombre: "Alejandro Pina",
  partido: "MC",
  followers: 8_764,
  engagement: 3.2,
  sentiment: 0.42,
};

const DEMO_COMPETITORS: CompetitorProfile[] = [
  {
    nombre: "Marti Batres",
    partido: "MORENA",
    followers: 285_000,
    engagement: 1.8,
    sentiment: -0.12,
  },
  {
    nombre: "Santiago Taboada",
    partido: "PAN",
    followers: 142_000,
    engagement: 2.4,
    sentiment: 0.18,
  },
];

function SentimentDot({ value }: { value: number }) {
  const color =
    value > 0.2
      ? "bg-emerald-500"
      : value < -0.1
        ? "bg-red-500"
        : "bg-amber-500";
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${color}`}
      aria-label={`Sentimiento ${value > 0.2 ? "positivo" : value < -0.1 ? "negativo" : "neutro"}`}
    />
  );
}

function FollowerBar({
  label,
  value,
  max,
  color,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
}) {
  const pct = Math.max((value / max) * 100, 2);
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between text-xs">
        <span className="truncate font-medium text-foreground/80">{label}</span>
        <span className="tabular-nums text-muted-foreground" data-numeric="true">
          {formatNumber(value)}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function StatRow({
  icon: Icon,
  label,
  ours,
  theirs,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  ours: string;
  theirs: string;
}) {
  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-sm">
      <span className="text-right tabular-nums font-medium" data-numeric="true">
        {ours}
      </span>
      <span className="flex items-center gap-1 text-xs text-muted-foreground" title={label}>
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      </span>
      <span className="tabular-nums text-muted-foreground" data-numeric="true">
        {theirs}
      </span>
    </div>
  );
}

export function CompetitorSnapshotCard() {
  const { activeOrg } = useAuth();
  const isMcCdmx = activeOrg?.slug === MC_CDMX_SLUG;

  if (!isMcCdmx) {
    return (
      <Card className="card-elevated">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Swords className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Competidores
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Sin competidores configurados
          </p>
        </CardContent>
      </Card>
    );
  }

  // Pick the top competitor for the side-by-side view
  const competitor = DEMO_COMPETITORS[0];
  const maxFollowers = Math.max(DEMO_DIRIGENTE.followers, competitor.followers);

  return (
    <Card className="card-elevated">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Swords className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          vs Competidor Principal
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Names header */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
          <div className="text-right">
            <p className="text-sm font-semibold leading-tight">{DEMO_DIRIGENTE.nombre}</p>
            <span className="inline-block mt-0.5 rounded-full bg-[hsl(var(--chart-1)/0.15)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--chart-1))]">
              {DEMO_DIRIGENTE.partido}
            </span>
          </div>
          <span className="text-xs font-bold text-muted-foreground/60">vs</span>
          <div>
            <p className="text-sm font-semibold leading-tight">{competitor.nombre}</p>
            <span className="inline-block mt-0.5 rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-red-600 dark:text-red-400">
              {competitor.partido}
            </span>
          </div>
        </div>

        {/* Stats comparison */}
        <div className="space-y-1.5">
          <StatRow
            icon={Users}
            label="Seguidores"
            ours={formatNumber(DEMO_DIRIGENTE.followers)}
            theirs={formatNumber(competitor.followers)}
          />
          <StatRow
            icon={TrendingUp}
            label="Engagement"
            ours={`${DEMO_DIRIGENTE.engagement.toFixed(1)}%`}
            theirs={`${competitor.engagement.toFixed(1)}%`}
          />
          <StatRow
            icon={Heart}
            label="Sentimiento"
            ours={DEMO_DIRIGENTE.sentiment > 0 ? `+${DEMO_DIRIGENTE.sentiment.toFixed(2)}` : DEMO_DIRIGENTE.sentiment.toFixed(2)}
            theirs={competitor.sentiment > 0 ? `+${competitor.sentiment.toFixed(2)}` : competitor.sentiment.toFixed(2)}
          />
        </div>

        {/* Follower bars */}
        <div className="space-y-2 pt-1 border-t border-border/50">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
            Seguidores totales
          </p>
          <FollowerBar
            label={DEMO_DIRIGENTE.nombre}
            value={DEMO_DIRIGENTE.followers}
            max={maxFollowers}
            color="hsl(var(--chart-1))"
          />
          {DEMO_COMPETITORS.map((c) => (
            <FollowerBar
              key={c.nombre}
              label={c.nombre}
              value={c.followers}
              max={maxFollowers}
              color="hsl(var(--muted-foreground) / 0.4)"
            />
          ))}
        </div>

        {/* Sentiment dots legend */}
        <div className="flex items-center gap-3 pt-1 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <SentimentDot value={DEMO_DIRIGENTE.sentiment} />
            {DEMO_DIRIGENTE.nombre.split(" ")[0]}
          </span>
          <span className="flex items-center gap-1">
            <SentimentDot value={competitor.sentiment} />
            {competitor.nombre.split(" ")[0]}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
