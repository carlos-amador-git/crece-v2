"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { KpiCard, KpiCardSkeleton } from "@/components/dashboard/kpi-card";
import { FilterSelect } from "@/components/dashboard/filter-select";
import {
  useSolicitudes, useParticipacionDashboard, useCreateSolicitud,
  type SolicitudTipo, type SolicitudEstado, type SolicitudPrioridad,
  type SolicitudCanal, type SolicitudFilters,
} from "@/lib/api/hooks/use-participacion";
import { formatNumber, formatDate } from "@/lib/utils";
import { Users, Plus, Loader2, MessageCircle, ClipboardList, Clock, Inbox } from "lucide-react";

const TIPOS: SolicitudTipo[] = ["queja", "peticion", "propuesta", "denuncia", "informacion"];
const ESTADOS: SolicitudEstado[] = ["nueva", "en_proceso", "resuelta", "cerrada", "rechazada"];
const PRIORIDADES: SolicitudPrioridad[] = ["alta", "media", "baja"];
const CANALES: SolicitudCanal[] = ["presencial", "telefono", "whatsapp", "web", "redes_sociales"];

function tipoVariant(t: SolicitudTipo) {
  const map: Record<string, "danger" | "warning" | "success" | "secondary"> = {
    queja: "danger", denuncia: "warning", propuesta: "success",
  };
  return map[t] ?? "secondary";
}
function estadoVariant(e: SolicitudEstado) {
  const map: Record<string, "default" | "warning" | "success" | "danger" | "secondary"> = {
    nueva: "default", en_proceso: "warning", resuelta: "success", rechazada: "danger",
  };
  return map[e] ?? "secondary";
}
function prioridadVariant(p: SolicitudPrioridad) {
  const map: Record<string, "danger" | "warning" | "secondary"> = {
    alta: "danger", media: "warning", baja: "secondary",
  };
  return map[p] ?? "secondary";
}

const toOpts = (arr: string[]) => arr.map((v) => ({ value: v, label: v }));

export default function ParticipacionPage() {
  const [filters, setFilters] = useState<SolicitudFilters>({});
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ tipo: "", titulo: "", descripcion: "", canal: "" });

  const { data: dashboard, isLoading: dashLoading } = useParticipacionDashboard();
  const { data, isLoading } = useSolicitudes(filters);
  const createSolicitud = useCreateSolicitud();
  const items = data?.items ?? [];

  const handleCreate = async () => {
    if (!form.tipo || !form.titulo || !form.descripcion || !form.canal) return;
    await createSolicitud.mutateAsync(form as { tipo: SolicitudTipo; titulo: string; descripcion: string; canal: SolicitudCanal });
    setDialogOpen(false);
    setForm({ tipo: "", titulo: "", descripcion: "", canal: "" });
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Participacion Ciudadana</h1>
          <p className="text-sm text-muted-foreground">Gestion de solicitudes y participacion de la ciudadania</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2"><Plus className="h-4 w-4" />Nueva Solicitud</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nueva Solicitud</DialogTitle>
              <DialogDescription>Registrar una nueva solicitud ciudadana.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label className="text-sm font-medium">Tipo</label>
                <FilterSelect value={form.tipo || undefined} onValueChange={(v) => setForm((f) => ({ ...f, tipo: v ?? "" }))} placeholder="Tipo" options={toOpts(TIPOS)} allLabel="Seleccionar tipo" className="w-full" />
              </div>
              <div className="grid gap-2">
                <label htmlFor="sol-titulo" className="text-sm font-medium">Titulo</label>
                <Input id="sol-titulo" placeholder="Titulo de la solicitud" value={form.titulo} onChange={(e) => setForm((f) => ({ ...f, titulo: e.target.value }))} />
              </div>
              <div className="grid gap-2">
                <label htmlFor="sol-desc" className="text-sm font-medium">Descripcion</label>
                <Input id="sol-desc" placeholder="Descripcion detallada" value={form.descripcion} onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))} />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium">Canal</label>
                <FilterSelect value={form.canal || undefined} onValueChange={(v) => setForm((f) => ({ ...f, canal: v ?? "" }))} placeholder="Canal" options={toOpts(CANALES)} allLabel="Seleccionar canal" className="w-full" />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleCreate} disabled={createSolicitud.isPending} className="gap-2">
                {createSolicitud.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageCircle className="h-4 w-4" />}
                Crear
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </header>

      {/* Stats */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Estadisticas">
        {dashLoading ? Array.from({ length: 4 }).map((_, i) => <KpiCardSkeleton key={i} />) : (
          <>
            <KpiCard title="Total Solicitudes" value={formatNumber(dashboard?.total ?? 0)} icon={Inbox} />
            <KpiCard title="Quejas" value={formatNumber(dashboard?.por_tipo?.queja ?? 0)} icon={ClipboardList} />
            <KpiCard title="Propuestas" value={formatNumber(dashboard?.por_tipo?.propuesta ?? 0)} icon={Users} />
            <KpiCard title="Resolucion Promedio" value={`${(dashboard?.avg_resolution_hours ?? 0).toFixed(0)}h`} icon={Clock} />
          </>
        )}
      </section>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <FilterSelect value={filters.tipo} onValueChange={(v) => setFilters((f) => ({ ...f, tipo: v as SolicitudTipo | undefined }))} placeholder="Tipo" options={toOpts(TIPOS)} allLabel="Todos los tipos" />
        <FilterSelect value={filters.estado} onValueChange={(v) => setFilters((f) => ({ ...f, estado: v as SolicitudEstado | undefined }))} placeholder="Estado" options={toOpts(ESTADOS)} allLabel="Todos los estados" />
        <FilterSelect value={filters.prioridad} onValueChange={(v) => setFilters((f) => ({ ...f, prioridad: v as SolicitudPrioridad | undefined }))} placeholder="Prioridad" options={toOpts(PRIORIDADES)} allLabel="Todas las prioridades" />
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>Solicitudes</CardTitle>
          <CardDescription>{data?.total ?? 0} solicitudes encontradas</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}</div>
          ) : items.length === 0 ? (
            <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">No hay solicitudes con estos filtros</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Titulo</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Prioridad</TableHead>
                  <TableHead>Canal</TableHead>
                  <TableHead>Fecha</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="max-w-[200px] truncate font-medium">{s.titulo}</TableCell>
                    <TableCell><Badge variant={tipoVariant(s.tipo)}>{s.tipo}</Badge></TableCell>
                    <TableCell><Badge variant={estadoVariant(s.estado)}>{s.estado}</Badge></TableCell>
                    <TableCell><Badge variant={prioridadVariant(s.prioridad)}>{s.prioridad}</Badge></TableCell>
                    <TableCell className="text-sm text-muted-foreground">{s.canal}</TableCell>
                    <TableCell className="text-sm text-muted-foreground tabular-nums">{formatDate(s.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
