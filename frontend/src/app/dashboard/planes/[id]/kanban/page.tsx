"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { KanbanBoard } from "@/components/planes/kanban-board";
import { usePlan } from "@/lib/api/hooks/use-planes";

export default function PlanKanbanPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const noRedirect = searchParams?.get("noRedirect") === "true";
  const id = params?.id as string;
  const { data: plan, isError } = usePlan(id);

  useEffect(() => {
    if (noRedirect) return;
    if (plan) {
      if (plan.tipo === "CONSOLIDACION") {
        router.replace(`/dashboard/planes?dirigente=${plan.dirigente_id}&tab=estrategia`);
      } else if (plan.tipo === "CONTENIDO") {
        router.replace(`/dashboard/planes?dirigente=${plan.dirigente_id}&tab=contenido`);
      } else if (plan.tipo === "DIAGNOSTICO") {
        router.replace(`/dashboard/diagnostico/${plan.dirigente_id}/foda`);
      } else {
        router.replace(`/dashboard/planes?dirigente=${plan.dirigente_id}`);
      }
    } else if (isError) {
      router.replace(`/dashboard/planes`);
    }
  }, [plan, isError, noRedirect, router]);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={
            plan?.tipo === "CONSOLIDACION"
              ? `/dashboard/planes?dirigente=${plan.dirigente_id}&tab=estrategia`
              : plan?.tipo === "CONTENIDO"
              ? `/dashboard/planes?dirigente=${plan.dirigente_id}&tab=contenido`
              : plan?.tipo === "DIAGNOSTICO"
              ? `/dashboard/diagnostico/${plan.dirigente_id}/foda`
              : `/dashboard/planes`
          }>
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
