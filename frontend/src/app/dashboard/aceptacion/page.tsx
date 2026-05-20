"use client";

/**
 * Aceptación · página adaptive según rol y N (cantidad de dirigentes).
 *
 * Comportamiento (D-ACEPTACION-DEDUPE-2026-05-20):
 *  - viewer / field_operator con `user.dirigente_id` asignado → vista perfil
 *    del PROPIO dirigente (DirigenteDetailContent).
 *  - admin / analyst con N=1 → vista perfil del único dirigente.
 *  - admin / analyst con N>1 → Battle Card comparativa: KPIs agregados +
 *    tabla 9 columnas con drill-down a `/aceptacion/[id]`.
 *
 * CEO clarificó: "Por dirigente" como página separada nunca tuvo sentido
 * — la navegación entre dirigentes vive como drill-down de esta página
 * cuando hay N>1, y nunca aplica para viewer (solo ve lo suyo).
 *
 * Reemplaza estructura previa que duplicaba grid IASummaryCard +
 * tabla detalle + IA summary del único dirigente.
 */

import { useAuth } from "@/lib/auth";
import { useAceptacionOverview } from "@/lib/api/hooks/use-aceptacion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DirigenteDetailContent } from "@/components/aceptacion/dirigente-detail-content";
import { formatNumber } from "@/lib/utils";
import { Gauge, Users, Ghost, TrendingUp, TrendingDown, ChevronRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

type Role = "admin" | "analyst" | "field_operator" | "viewer";

function isAdminRole(role: string | undefined): boolean {
  return role === "admin" || role === "analyst";
}

export default function AceptacionPage() {
  const { user } = useAuth();
  const { data, isLoading, error } = useAceptacionOverview();

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-12 w-72" />
        <Skeleton className="h-[60vh]" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No se pudo cargar el Índice de Aceptación.
          </CardContent>
        </Card>
      </div>
    );
  }

  const rows = data.dirigentes;
  const N = rows.length;
  const userRole = (user as { role?: string } | null)?.role;
  const userDirigenteId = (user as { dirigente_id?: number } | null)?.dirigente_id;

  // Si viewer/field_operator con dirigente_id asignado → vista perfil propia.
  // Esto es robusto incluso si el backend devolviera otros dirigentes; mostramos
  // SOLO el del usuario (defense in depth con guard backend).
  if (!isAdminRole(userRole) && userDirigenteId) {
    const propio = rows.find((d) => d.dirigente_id === userDirigenteId) ?? rows[0];
    if (!propio) {
      return (
        <div className="p-6">
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">
              No se encontró tu dirigente. Contacta al administrador.
            </CardContent>
          </Card>
        </div>
      );
    }
    return (
      <div className="space-y-6 p-6">
        <DirigenteHeader fullName={propio.full_name} rolPolitico={propio.rol_politico} subtitle="Índice de Aceptación" />
        <DirigenteDetailContent dirigenteId={propio.dirigente_id} />
      </div>
    );
  }

  // Admin con N=1 → mismo render perfil sin Battle Card.
  if (isAdminRole(userRole) && N === 1) {
    const propio = rows[0];
    return (
      <div className="space-y-6 p-6">
        <DirigenteHeader fullName={propio.full_name} rolPolitico={propio.rol_politico} subtitle="Índice de Aceptación" />
        <DirigenteDetailContent dirigenteId={propio.dirigente_id} />
      </div>
    );
  }

  // Admin con N>1 → vista comparativa (Battle Card).
  return <BattleCardView data={data} rows={rows} />;
}

function DirigenteHeader({
  fullName,
  rolPolitico,
  subtitle,
}: {
  fullName: string;
  rolPolitico: string | null;
  subtitle: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <Gauge className="h-6 w-6 text-accent" />
        <h1 className="font-heading text-2xl font-bold tracking-tight">{fullName}</h1>
        {rolPolitico && (
          <Badge
            variant="outline"
            className={
              rolPolitico === "oposicion"
                ? "border-amber-500/40 text-amber-500"
                : "border-emerald-500/40 text-emerald-500"
            }
          >
            {rolPolitico === "oficialismo" ? "Gobierno" : rolPolitico}
          </Badge>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
    </div>
  );
}

/* ─────── Battle Card (admin N>1) ─────── */

interface OverviewData {
  total_corpus_comments: number;
  dirigentes: Array<{
    dirigente_id: number;
    full_name: string;
    rol_politico: string | null;
    total_followers: number;
    unique_commenters: number;
    total_comments: number;
    pct_activados: number;
    pct_fantasma: number;
    pct_aprobacion: number;
    pct_rechazo: number;
  }>;
}

function BattleCardView({ data, rows }: { data: OverviewData; rows: OverviewData["dirigentes"] }) {
  const totalFollowers = rows.reduce((s, r) => s + r.total_followers, 0);
  const totalCommenters = rows.reduce((s, r) => s + r.unique_commenters, 0);
  const avgActivacion = totalFollowers > 0 ? (100 * totalCommenters) / totalFollowers : 0;
  const avgFantasma = 100 - avgActivacion;
  const avgAprobacion =
    rows.length > 0 ? rows.reduce((s, r) => s + r.pct_aprobacion, 0) / rows.length : 0;
  const avgRechazo =
    rows.length > 0 ? rows.reduce((s, r) => s + r.pct_rechazo, 0) / rows.length : 0;

  return (
    <div className="space-y-6 p-6">
      <div>
        <div className="flex items-center gap-2">
          <Gauge className="h-6 w-6 text-accent" />
          <h1 className="font-heading text-2xl font-bold tracking-tight">Índice de Aceptación</h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Vista comparativa de {rows.length} dirigentes · corpus de{" "}
          {formatNumber(data.total_corpus_comments)} comentarios clasificados con matriz v2 (53 reglas).
        </p>
      </div>

      {/* KPI cards agregados */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          icon={<Users className="h-4 w-4" />}
          label="Activación promedio"
          value={`${avgActivacion.toFixed(2)}%`}
          subtitle={`${formatNumber(totalCommenters)} únicos / ${formatNumber(totalFollowers)} followers`}
          tone="info"
        />
        <KPICard
          icon={<Ghost className="h-4 w-4" />}
          label="Fantasmas"
          value={`${avgFantasma.toFixed(2)}%`}
          subtitle="Followers sin señales de vida"
          tone={avgFantasma > 98 ? "danger" : avgFantasma > 95 ? "warn" : "ok"}
        />
        <KPICard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Aprobación promedio"
          value={`${avgAprobacion.toFixed(1)}%`}
          subtitle="Comments con polaridad +1"
          tone="ok"
        />
        <KPICard
          icon={<TrendingDown className="h-4 w-4" />}
          label="Rechazo promedio"
          value={`${avgRechazo.toFixed(1)}%`}
          subtitle="Comments con polaridad -1"
          tone="danger"
        />
      </div>

      {/* Tabla comparativa ordenable (drill-down al detalle) */}
      <div>
        <h2 className="mb-3 font-heading text-lg font-semibold">Comparativa por dirigente</h2>
        <p className="mb-3 text-xs text-muted-foreground">
          Click en una fila para ver el detalle completo del dirigente.
        </p>
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Dirigente</th>
                    <th className="px-4 py-2 text-left font-medium">Rol</th>
                    <th className="px-4 py-2 text-right font-medium">Followers</th>
                    <th className="px-4 py-2 text-right font-medium">Comentaristas</th>
                    <th className="px-4 py-2 text-right font-medium">Comments</th>
                    <th className="px-4 py-2 text-right font-medium">Activ. %</th>
                    <th className="px-4 py-2 text-right font-medium">Fantasma %</th>
                    <th className="px-4 py-2 text-right font-medium">Aprob. %</th>
                    <th className="px-4 py-2 text-right font-medium">Rech. %</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {[...rows]
                    .sort((a, b) => b.pct_fantasma - a.pct_fantasma)
                    .map((d) => (
                      <tr
                        key={d.dirigente_id}
                        className="border-b last:border-0 transition-colors hover:bg-muted/30"
                      >
                        <td className="px-4 py-3 font-medium">
                          <Link
                            href={`/dashboard/aceptacion/${d.dirigente_id}`}
                            className="block w-full hover:underline"
                          >
                            {d.full_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3">
                          {d.rol_politico ? (
                            <Badge
                              variant="outline"
                              className={
                                d.rol_politico === "oposicion"
                                  ? "border-amber-500/40 text-amber-500"
                                  : "border-emerald-500/40 text-emerald-500"
                              }
                            >
                              {d.rol_politico === "oficialismo" ? "Gobierno" : d.rol_politico}
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          {formatNumber(d.total_followers)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          {formatNumber(d.unique_commenters)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          {formatNumber(d.total_comments)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums font-medium">
                          {d.pct_activados.toFixed(2)}%
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums">
                          <span
                            className={
                              d.pct_fantasma > 99
                                ? "text-rose-500"
                                : d.pct_fantasma > 95
                                  ? "text-amber-500"
                                  : "text-emerald-500"
                            }
                          >
                            {d.pct_fantasma.toFixed(2)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-emerald-500">
                          {d.pct_aprobacion.toFixed(1)}%
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-rose-500">
                          {d.pct_rechazo.toFixed(1)}%
                        </td>
                        <td className="px-4 py-3">
                          <Link href={`/dashboard/aceptacion/${d.dirigente_id}`}>
                            <ChevronRight className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Metodología compacta */}
      <Card className="border-dashed">
        <CardContent className="p-4 text-xs text-muted-foreground">
          <p>
            <strong>Cómo se calcula:</strong> Activación = comentaristas únicos / followers.
            Fantasma = 100 − Activación. Aprobación/Rechazo = % comments con polaridad NLP +1/−1.
            <Link href="/dashboard/sistema/metodologia" className="ml-2 underline">
              Ver metodología completa
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function KPICard({
  icon,
  label,
  value,
  subtitle,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  subtitle: string;
  tone: "ok" | "warn" | "danger" | "info";
}) {
  const toneBg = {
    ok: "bg-emerald-500/10 text-emerald-500",
    warn: "bg-amber-500/10 text-amber-500",
    danger: "bg-rose-500/10 text-rose-500",
    info: "bg-blue-500/10 text-blue-500",
  }[tone];
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </span>
          <span className={`rounded-md p-1.5 ${toneBg}`}>{icon}</span>
        </div>
        <div className="mt-2 font-heading text-2xl font-bold tabular-nums">{value}</div>
        <div className="mt-0.5 text-xs text-muted-foreground">{subtitle}</div>
      </CardContent>
    </Card>
  );
}
