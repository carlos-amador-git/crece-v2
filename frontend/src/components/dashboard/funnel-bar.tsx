import { formatNumber } from "@/lib/utils";

export interface FunnelData {
  enviados: number;
  entregados: number;
  leidos: number;
  respondidos: number;
}

const STEPS = [
  { key: "enviados" as const, label: "Enviados", color: "bg-primary" },
  { key: "entregados" as const, label: "Entregados", color: "bg-blue-500" },
  { key: "leidos" as const, label: "Leidos", color: "bg-amber-500" },
  { key: "respondidos" as const, label: "Respondidos", color: "bg-emerald-500" },
];

export function FunnelBar({ funnel }: { funnel: FunnelData }) {
  const max = Math.max(funnel.enviados, 1);

  return (
    <div className="space-y-2">
      {STEPS.map((step) => {
        const value = funnel[step.key];
        const pct = Math.round((value / max) * 100);
        return (
          <div key={step.key} className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-xs text-muted-foreground">{step.label}</span>
            <div className="relative h-4 flex-1 overflow-hidden rounded-full bg-muted">
              <div
                className={`absolute inset-y-0 left-0 rounded-full ${step.color} transition-all duration-300`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-12 text-right text-xs font-medium tabular-nums">{formatNumber(value)}</span>
          </div>
        );
      })}
    </div>
  );
}
