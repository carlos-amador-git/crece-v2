"use client";

import { useParams, useRouter } from "next/navigation";
import { usePlan } from "@/lib/api/hooks/use-planes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Brain, CheckCircle, XCircle, Clock, Cpu } from "lucide-react";
import Link from "next/link";

const TIPO_LABELS: Record<string, { label: string; color: string; description: string }> = {
  DIAGNOSTICO: {
    label: "Diagnostico",
    color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    description: "Analisis completo de presencia digital con FODA, KPIs y recomendaciones.",
  },
  CONSOLIDACION: {
    label: "Consolidacion",
    color: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
    description: "Plan de 90 dias para consolidar y expandir presencia digital.",
  },
  CRISIS: {
    label: "Crisis",
    color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    description: "Protocolo de manejo de crisis digital con respuestas predefinidas.",
  },
  CONTENIDO: {
    label: "Contenido",
    color: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
    description: "Calendario editorial de 30 dias con ejemplos de posts listos.",
  },
};

function MarkdownRenderer({ content }: { content: string }) {
  // Simple markdown to HTML (tables, headers, bold, lists)
  const html = content
    // Headers
    .replace(/^### (.+)$/gm, '<h3 class="mt-6 mb-3 font-heading text-lg font-semibold text-foreground">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="mt-8 mb-4 font-heading text-xl font-bold text-foreground border-b border-border pb-2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="mt-8 mb-4 font-heading text-2xl font-extrabold text-foreground">$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-foreground">$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Tables - handle pipes
    .replace(/^\|(.+)\|$/gm, (match) => {
      const cells = match.split('|').filter(c => c.trim());
      const isHeader = cells.every(c => c.trim().match(/^-+$/));
      if (isHeader) return '<tr class="border-b border-border"></tr>';
      const tag = 'td';
      const cellHtml = cells.map(c =>
        `<${tag} class="px-3 py-2 text-sm border-r border-border last:border-r-0">${c.trim()}</${tag}>`
      ).join('');
      return `<tr class="border-b border-border/50 hover:bg-muted/30">${cellHtml}</tr>`;
    })
    // Wrap consecutive table rows
    .replace(/((?:<tr[^>]*>.*<\/tr>\n?){2,})/g,
      '<div class="my-4 overflow-x-auto rounded-lg border border-border"><table class="w-full text-left">$1</table></div>'
    )
    // Bullet lists
    .replace(/^\* (.+)$/gm, '<li class="ml-4 text-sm text-muted-foreground list-disc">$1</li>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 text-sm text-muted-foreground list-disc">$1</li>')
    // Numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 text-sm text-muted-foreground list-decimal">$1</li>')
    // Paragraphs (lines that aren't already wrapped)
    .replace(/^(?!<[hltud]|<strong|<em)(.+)$/gm, '<p class="text-sm text-muted-foreground leading-relaxed mb-2">$1</p>')
    // Clean up empty paragraphs
    .replace(/<p[^>]*>\s*<\/p>/g, '');

  return (
    <div
      className="prose-crece"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export default function PlanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { data: plan, isLoading, isError } = usePlan(id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-[600px] w-full" />
      </div>
    );
  }

  if (isError || !plan) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
          Volver
        </Button>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Brain className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="font-medium">No se pudo cargar el plan</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const tipoInfo = TIPO_LABELS[plan.tipo] ?? {
    label: plan.tipo,
    color: "bg-muted text-muted-foreground",
    description: "",
  };

  const createdDate = new Date(plan.created_at).toLocaleDateString("es-MX", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="space-y-6">
      {/* Back */}
      <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => router.back()}>
        <ArrowLeft className="h-4 w-4" />
        Volver
      </Button>

      {/* Header card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Badge className={tipoInfo.color}>{tipoInfo.label}</Badge>
                <Badge variant={plan.aprobado ? "default" : "secondary"}>
                  {plan.aprobado ? (
                    <><CheckCircle className="mr-1 h-3 w-3" /> Aprobado</>
                  ) : (
                    <><Clock className="mr-1 h-3 w-3" /> Borrador</>
                  )}
                </Badge>
              </div>
              <h1 className="font-heading text-2xl font-bold text-foreground">
                Plan de {tipoInfo.label}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">{tipoInfo.description}</p>
            </div>
            <div className="flex flex-col gap-2 text-right text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5 justify-end">
                <Cpu className="h-3.5 w-3.5" />
                {plan.modelo_ia}
              </div>
              <div>{createdDate}</div>
              <div>{plan.contenido.length.toLocaleString()} caracteres</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Plan content */}
      <Card>
        <CardHeader>
          <CardTitle>Contenido del Plan</CardTitle>
        </CardHeader>
        <CardContent>
          <MarkdownRenderer content={plan.contenido} />
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3 justify-end">
        {!plan.aprobado && (
          <>
            <Button
              variant="outline"
              className="gap-1.5 border-red-200 text-red-600 hover:bg-red-50"
            >
              <XCircle className="h-4 w-4" />
              Rechazar
            </Button>
            <Button className="gap-1.5 bg-cta text-cta-foreground hover:bg-cta/90">
              <CheckCircle className="h-4 w-4" />
              Aprobar Plan
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
