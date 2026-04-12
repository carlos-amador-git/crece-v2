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
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { FunnelBar } from "@/components/dashboard/funnel-bar";
import { Textarea } from "@/components/ui/textarea";
import {
  useCampanas, useCampanaAnalytics, useCreateCampana,
  type Campana, type CampanaEstado, type CampanaTipo,
} from "@/lib/api/hooks/use-campanas";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { useCiudadanos } from "@/lib/api/hooks/use-ciudadanos";
import { formatNumber, formatDate } from "@/lib/utils";
import { Send, Plus, Loader2, ArrowRight, Users } from "lucide-react";

const SEGMENTOS = [
  { value: "todos", label: "Todos los ciudadanos" },
  { value: "promotable", label: "Promotable (alta probabilidad MC)" },
  { value: "persuadible", label: "Persuadible (indecisos convertibles)" },
  { value: "indeciso", label: "Indeciso" },
];

const TIPOS: CampanaTipo[] = ["whatsapp", "sms", "email", "mixta"];

function estadoVariant(e: CampanaEstado) {
  const m: Record<string, "success" | "warning" | "secondary" | "danger" | "outline"> = {
    activa: "success", programada: "warning", finalizada: "secondary", pausada: "danger",
  };
  return m[e] ?? "outline";
}

function CampanaCard({ campana, onSelect }: { campana: Campana; onSelect: (id: number) => void }) {
  return (
    <Card className="card-elevated">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant={estadoVariant(campana.estado)}>{campana.estado}</Badge>
              <Badge variant="outline">{campana.tipo}</Badge>
              {campana.dirigente_nombre && <span className="text-xs text-muted-foreground">{campana.dirigente_nombre}</span>}
            </div>
            <h3 className="font-heading text-base font-semibold">{campana.nombre}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{formatNumber(campana.total_mensajes)} mensajes -- {formatDate(campana.created_at)}</p>
          </div>
          <Button size="sm" variant="ghost" onClick={() => onSelect(campana.id)} aria-label={`Ver detalle de ${campana.nombre}`}><ArrowRight className="h-4 w-4" /></Button>
        </div>
        <div className="mt-4"><FunnelBar funnel={campana.funnel} /></div>
      </CardContent>
    </Card>
  );
}

export default function CampanasPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [form, setForm] = useState({ nombre: "", tipo: "", plantilla: "", dirigente_id: "", mensaje: "", segmento: "todos" });

  const { data: campanas, isLoading } = useCampanas();
  const selectedCampana = campanas?.find((c) => c.id === selectedId);
  const isEnviando = selectedCampana?.estado === "activa" || selectedCampana?.estado === "programada";
  const { data: analytics } = useCampanaAnalytics(selectedId ?? undefined, isEnviando);
  const { data: dirigentesData } = useDirigentes({ per_page: 50 });
  const { data: ciudadanosData } = useCiudadanos({ per_page: 1 });
  const createCampana = useCreateCampana();

  const dirigentesForSelect = dirigentesData?.items ?? [];
  const totalCiudadanos = ciudadanosData?.total ?? 0;

  const handleCreate = async () => {
    if (!form.nombre || !form.tipo || !form.dirigente_id) return;
    await createCampana.mutateAsync({ nombre: form.nombre, tipo: form.tipo as CampanaTipo, plantilla: form.plantilla || form.mensaje, dirigente_id: Number(form.dirigente_id) });
    setDialogOpen(false);
    setForm({ nombre: "", tipo: "", plantilla: "", dirigente_id: "", mensaje: "", segmento: "todos" });
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Campaign Manager</h1>
          <p className="text-sm text-muted-foreground">Gestion de campanas de comunicacion directa</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild><Button className="gap-2"><Plus className="h-4 w-4" />Nueva Campana</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nueva Campana</DialogTitle>
              <DialogDescription>Configura una nueva campana de comunicacion.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label htmlFor="camp-nombre" className="text-sm font-medium">Nombre</label>
                <Input id="camp-nombre" placeholder="Nombre de la campana" value={form.nombre} onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Tipo</label>
                  <Select value={form.tipo} onValueChange={(v) => setForm((f) => ({ ...f, tipo: v }))}>
                    <SelectTrigger><SelectValue placeholder="Seleccionar tipo" /></SelectTrigger>
                    <SelectContent>{TIPOS.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Dirigente</label>
                  <Select value={form.dirigente_id} onValueChange={(v) => setForm((f) => ({ ...f, dirigente_id: v }))}>
                    <SelectTrigger><SelectValue placeholder="Seleccionar dirigente" /></SelectTrigger>
                    <SelectContent>
                      {dirigentesForSelect.map((d) => (
                        <SelectItem key={d.id} value={String(d.id)}>{d.full_name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium">Segmento Objetivo</label>
                <Select value={form.segmento} onValueChange={(v) => setForm((f) => ({ ...f, segmento: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {SEGMENTOS.map((s) => (
                      <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium">Mensaje</label>
                <Textarea
                  placeholder="Escribe el mensaje o selecciona una plantilla del Content Factory"
                  value={form.mensaje}
                  onChange={(e) => setForm((f) => ({ ...f, mensaje: e.target.value }))}
                  rows={4}
                />
              </div>
              <div className="rounded-md border border-border/50 bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-2 text-sm">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    Esta campana se enviara a <span className="font-semibold text-foreground">~{formatNumber(totalCiudadanos)}</span> ciudadanos con telefono registrado
                  </span>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleCreate} disabled={createCampana.isPending} className="gap-2">
                {createCampana.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Crear
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </header>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="space-y-3 lg:col-span-3" aria-label="Lista de campanas">
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Card key={i} className="card-elevated"><CardContent className="p-5"><Skeleton className="mb-2 h-5 w-48" /><Skeleton className="h-16 w-full" /></CardContent></Card>)
          ) : !campanas || campanas.length === 0 ? (
            <Card><CardContent className="flex flex-col items-center justify-center py-12 text-center"><Send className="mb-3 h-10 w-10 text-muted-foreground/50" /><p className="text-sm text-muted-foreground">No hay campanas. Crea la primera.</p></CardContent></Card>
          ) : campanas.map((c) => <CampanaCard key={c.id} campana={c} onSelect={setSelectedId} />)}
        </section>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Analytics</CardTitle>
            <CardDescription>{selectedId ? `Campana #${selectedId}` : "Selecciona una campana"}</CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedId ? (
              <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">Selecciona una campana para ver analytics</div>
            ) : !analytics ? (
              <div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-6 w-full" />)}</div>
            ) : (
              <div className="space-y-4">
                <FunnelBar funnel={analytics.funnel} />
                <div className="grid grid-cols-2 gap-3 pt-4 border-t">
                  <div><p className="text-xs text-muted-foreground">Tasa Apertura</p><p className="font-heading text-lg font-bold tabular-nums">{analytics.tasa_apertura.toFixed(1)}%</p></div>
                  <div><p className="text-xs text-muted-foreground">Tasa Respuesta</p><p className="font-heading text-lg font-bold tabular-nums">{analytics.tasa_respuesta.toFixed(1)}%</p></div>
                  <div><p className="text-xs text-muted-foreground">Costo Total</p><p className="font-heading text-lg font-bold tabular-nums">${formatNumber(analytics.costo_total)}</p></div>
                  <div><p className="text-xs text-muted-foreground">Costo/Mensaje</p><p className="font-heading text-lg font-bold tabular-nums">${analytics.costo_por_mensaje.toFixed(2)}</p></div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
