"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { KanbanBoard } from "@/components/planes/kanban-board";
import { usePlan } from "@/lib/api/hooks/use-planes";

export default function PlanKanbanPage() {
  const params = useParams();
  const id = params?.id as string;
  const { data: plan } = usePlan(id);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/dashboard/planes/${id}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Volver al plan
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Kanban</h1>
            {plan && (
              <p className="text-sm text-muted-foreground">
                Plan #{plan.id} · {plan.tipo}
              </p>
            )}
          </div>
        </div>
      </div>
      <KanbanBoard planId={id} />
    </div>
  );
}
