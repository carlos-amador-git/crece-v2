import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { LucideIcon } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  className?: string;
}

export function KpiCard({ title, value, icon: Icon, className }: KpiCardProps) {
  return (
    <Card className={`card-elevated ${className ?? ""}`}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <Icon className="h-4.5 w-4.5 text-muted-foreground" />
        </div>
        <p className="mt-2 font-heading text-2xl font-bold tabular-nums">
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

export function KpiCardSkeleton() {
  return (
    <Card className="card-elevated">
      <CardContent className="p-5">
        <Skeleton className="mb-3 h-4 w-24" />
        <Skeleton className="h-8 w-16" />
      </CardContent>
    </Card>
  );
}
