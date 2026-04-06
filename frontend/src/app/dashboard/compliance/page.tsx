"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useGastos,
  useAlertas,
  useComplianceReport,
  useRunAudit,
  type AlertaSeveridad,
} from "@/lib/api/hooks/use-compliance";
import { formatNumber, formatDate } from "@/lib/utils";
import { ImportGastosDialog } from "@/components/compliance/import-gastos-dialog";
import {
  Shield,
  DollarSign,
  AlertTriangle,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Upload,
} from "lucide-react";

function severityVariant(s: AlertaSeveridad) {
  switch (s) {
    case "critica":
      return "danger" as const;
    case "alta":
      return "warning" as const;
    case "media":
      return "secondary" as const;
    case "baja":
      return "outline" as const;
  }
}

function severityLabel(s: AlertaSeveridad) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default function CompliancePage() {
  const { data: report, isLoading: reportLoading } = useComplianceReport();
  const { data: gastos, isLoading: gastosLoading } = useGastos();
  const { data: alertas, isLoading: alertasLoading } = useAlertas();
  const runAudit = useRunAudit();
  const [running, setRunning] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  const handleRunAudit = async () => {
    setRunning(true);
    try {
      await runAudit.mutateAsync();
    } finally {
      setRunning(false);
    }
  };

  const topeColor =
    (report?.porcentaje_tope ?? 0) >= 90
      ? "text-red-600 dark:text-red-400"
      : (report?.porcentaje_tope ?? 0) >= 70
      ? "text-amber-600 dark:text-amber-400"
      : "text-emerald-600 dark:text-emerald-400";

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Blindaje Legal</h1>
          <p className="text-sm text-muted-foreground">
            Monitoreo de cumplimiento INE, gastos y deteccion de bots
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setImportOpen(true)} className="gap-2">
            <Upload className="h-4 w-4" />
            Importar Gastos
          </Button>
          <Button onClick={handleRunAudit} disabled={running} className="gap-2">
            {running ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Run Audit
          </Button>
        </div>
      </header>

      {/* KPI Cards */}
      <section
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Metricas de compliance"
      >
        {reportLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="card-elevated">
              <CardContent className="p-5">
                <Skeleton className="mb-3 h-4 w-24" />
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <Card className="card-elevated">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    Total Gastos
                  </p>
                  <DollarSign className="h-4.5 w-4.5 text-muted-foreground" />
                </div>
                <p className="mt-2 font-heading text-2xl font-bold tabular-nums">
                  ${formatNumber(report?.total_gastos ?? 0)}
                </p>
              </CardContent>
            </Card>
            <Card className="card-elevated accent-bar-left" data-active="true">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    % Tope
                  </p>
                  <Shield className="h-4.5 w-4.5 text-muted-foreground" />
                </div>
                <p
                  className={`mt-2 font-heading text-2xl font-bold tabular-nums ${topeColor}`}
                >
                  {(report?.porcentaje_tope ?? 0).toFixed(1)}%
                </p>
              </CardContent>
            </Card>
            <Card className="card-elevated">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    Alertas Activas
                  </p>
                  <AlertTriangle className="h-4.5 w-4.5 text-muted-foreground" />
                </div>
                <p className="mt-2 font-heading text-2xl font-bold tabular-nums">
                  {report?.alertas_activas ?? 0}
                </p>
              </CardContent>
            </Card>
            <Card className="card-elevated">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    Tope Campana INE
                  </p>
                  <DollarSign className="h-4.5 w-4.5 text-muted-foreground" />
                </div>
                <p className="mt-2 font-heading text-2xl font-bold tabular-nums">
                  $500K
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">CDMX 2024</p>
              </CardContent>
            </Card>
          </>
        )}
      </section>

      {/* Gastos Table + Alertas */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Gastos */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Gastos Registrados</CardTitle>
            <CardDescription>Trazabilidad de gastos de campana</CardDescription>
          </CardHeader>
          <CardContent>
            {gastosLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : !gastos || gastos.length === 0 ? (
              <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
                Sin gastos registrados
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Concepto</TableHead>
                    <TableHead>Categoria</TableHead>
                    <TableHead className="text-right">Monto</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-center">Aprobado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {gastos.map((g) => (
                    <TableRow key={g.id}>
                      <TableCell className="font-medium">
                        {g.concepto}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{g.categoria}</Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        ${formatNumber(g.monto)}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(g.fecha)}
                      </TableCell>
                      <TableCell className="text-center">
                        {g.aprobado ? (
                          <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                        ) : (
                          <XCircle className="mx-auto h-4 w-4 text-red-500" />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Alertas */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Alertas</CardTitle>
            <CardDescription>Alertas de cumplimiento activas</CardDescription>
          </CardHeader>
          <CardContent>
            {alertasLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : !alertas || alertas.length === 0 ? (
              <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
                Sin alertas activas
              </div>
            ) : (
              <ul className="space-y-3">
                {alertas.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-start gap-3 rounded-md border p-3"
                  >
                    <AlertTriangle
                      className={`mt-0.5 h-4 w-4 shrink-0 ${
                        a.severidad === "critica"
                          ? "text-red-500"
                          : a.severidad === "alta"
                          ? "text-amber-500"
                          : "text-muted-foreground"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={severityVariant(a.severidad)}>
                          {severityLabel(a.severidad)}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatDate(a.created_at)}
                        </span>
                      </div>
                      <p className="mt-1 text-sm">{a.mensaje}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Electoral Data 2024 */}
      <Card>
        <CardHeader>
          <CardTitle>Referencia Electoral CDMX 2024</CardTitle>
          <CardDescription>
            Topes de gasto y datos de referencia INE para cumplimiento
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground">Tope de Gastos de Campana</p>
              <p className="mt-1 font-heading text-xl font-bold">$500,000 MXN</p>
              <p className="mt-1 text-xs text-muted-foreground">Por candidato a diputado local CDMX</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground">Tope Precampana</p>
              <p className="mt-1 font-heading text-xl font-bold">$100,000 MXN</p>
              <p className="mt-1 text-xs text-muted-foreground">20% del tope de campana</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground">Financiamiento Privado</p>
              <p className="mt-1 font-heading text-xl font-bold">$50,000 MXN</p>
              <p className="mt-1 text-xs text-muted-foreground">Maximo por aportante individual</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground">Lista Nominal CDMX</p>
              <p className="mt-1 font-heading text-xl font-bold">7,459,827</p>
              <p className="mt-1 text-xs text-muted-foreground">Ciudadanos con credencial vigente</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground">Participacion 2024</p>
              <p className="mt-1 font-heading text-xl font-bold">62.3%</p>
              <p className="mt-1 text-xs text-muted-foreground">Eleccion federal + local</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground">MC Votacion CDMX 2024</p>
              <p className="mt-1 font-heading text-xl font-bold">8.7%</p>
              <p className="mt-1 text-xs text-muted-foreground">~410K votos en CDMX</p>
            </div>
          </div>

          <div className="mt-6 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
            <p className="font-medium">Categorias de gasto fiscalizables (INE)</p>
            <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-amber-700 dark:text-amber-300 sm:grid-cols-3">
              <span>Propaganda</span>
              <span>Operativos</span>
              <span>Produccion</span>
              <span>Transporte</span>
              <span>Alimentacion</span>
              <span>Alquiler inmuebles</span>
              <span>Servicios personales</span>
              <span>Publicidad en redes</span>
              <span>Otros</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <ImportGastosDialog open={importOpen} onOpenChange={setImportOpen} />
    </div>
  );
}
