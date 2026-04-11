"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";
import { useSystemStatus, useKpiOverview } from "@/lib/api/hooks/use-overview";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber, formatRelativeTime } from "@/lib/utils";
import { Shield, User, Cpu, Globe, Activity } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();
  const { data: status } = useSystemStatus();
  const { data: kpi } = useKpiOverview("30d");

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "—";
  const userWithDirigente = user as {
    full_name?: string;
    email?: string;
    role?: string;
    dirigente_id?: number;
  } | null;
  const isDirigente = !!userWithDirigente?.dirigente_id;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-2xl font-bold">Configuracion</h1>
        <p className="text-sm text-muted-foreground">
          Informacion de tu cuenta y del sistema
        </p>
      </header>

      {/* ── User card ──────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <User className="h-4 w-4" />
            Mi cuenta
          </CardTitle>
          <CardDescription>Datos del usuario autenticado</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Row label="Nombre" value={userWithDirigente?.full_name ?? "—"} />
          <Row label="Correo" value={userWithDirigente?.email ?? "—"} />
          <Row
            label="Rol"
            value={
              <Badge variant="secondary">
                {userWithDirigente?.role ?? "—"}
              </Badge>
            }
          />
          <Row
            label="Dirigente asociado"
            value={
              isDirigente ? `#${userWithDirigente?.dirigente_id}` : "Sin asociacion (acceso global)"
            }
          />
          {isDirigente && kpi && (
            <>
              <Row label="IPD actual" value={`${kpi.avg_ipd_score.toFixed(1)} / 10`} />
              <Row
                label="Audiencia total"
                value={formatNumber(kpi.total_audiencia ?? 0)}
              />
            </>
          )}
        </CardContent>
      </Card>

      {/* ── System card ────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Cpu className="h-4 w-4" />
            Sistema
          </CardTitle>
          <CardDescription>Estado de workers y conexion al backend</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Row
            label="API URL"
            value={
              <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                {apiBaseUrl}
              </code>
            }
          />
          <Row
            label="Ultima sincronizacion"
            value={
              status?.last_sync ? (
                formatRelativeTime(status.last_sync)
              ) : (
                <Skeleton className="h-4 w-20" />
              )
            }
          />
          <Row
            label="Workers"
            value={
              status ? `${status.workers_active}/${status.workers_total} activos` : <Skeleton className="h-4 w-20" />
            }
          />
          <Row
            label="Scrapers"
            value={
              status ? `${status.scrapers_running} en ejecucion` : <Skeleton className="h-4 w-20" />
            }
          />
        </CardContent>
      </Card>

      {/* ── Compliance card ────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield className="h-4 w-4" />
            Cumplimiento INE
          </CardTitle>
          <CardDescription>
            CRECE v2.0 cumple con las regulaciones electorales mexicanas
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ComplianceItem
            ok
            label="Etiquetado obligatorio de contenido generado con IA"
          />
          <ComplianceItem
            ok
            label="Trazabilidad de gastos electorales (ver Compliance)"
          />
          <ComplianceItem
            ok
            label="Middleware de veda electoral activo"
          />
          <ComplianceItem
            ok
            label="Scoping de datos por dirigente (RLS)"
          />
        </CardContent>
      </Card>

      {/* ── Version card ───────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="h-4 w-4" />
            Version
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <Row label="CRECE" value="v2.0.0" />
          <Row label="Backend" value="FastAPI + PostgreSQL 16 + PostGIS + pgvector" />
          <Row label="Frontend" value="Next.js 14 App Router" />
          <Row label="IA" value="Claude API + Ollama gemma3:12b" />
        </CardContent>
      </Card>
    </div>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/40 pb-2 last:border-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}

function ComplianceItem({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-start gap-2">
      <Activity
        className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
          ok ? "text-emerald-600" : "text-muted-foreground"
        }`}
      />
      <span className={ok ? "text-foreground/90" : ""}>{label}</span>
    </div>
  );
}
