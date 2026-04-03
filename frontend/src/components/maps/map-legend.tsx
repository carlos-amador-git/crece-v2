interface MapLegendProps {
  title: string;
  items: { color: string; label: string }[];
}

export function MapLegend({ title, items }: MapLegendProps) {
  return (
    <div className="rounded-lg border bg-card p-3 shadow-sm">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h4>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <span
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: item.color }}
              aria-hidden="true"
            />
            <span className="text-xs text-foreground">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export const INTENTION_LEGEND = [
  { color: "#22c55e", label: "A favor (>60%)" },
  { color: "#84cc16", label: "A favor (50-60%)" },
  { color: "#eab308", label: "Indeciso" },
  { color: "#f97316", label: "En contra (50-60%)" },
  { color: "#ef4444", label: "En contra (>60%)" },
];
