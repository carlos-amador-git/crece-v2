"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { FilterSelect } from "@/components/dashboard/filter-select";
import { ContentCard } from "@/components/dashboard/content-card";
import {
  useContenidos, useGenerateContent, useUpdateContenidoEstado,
  type ContenidoFormato, type ContenidoEstado, type ContenidoFilters,
} from "@/lib/api/hooks/use-contenido";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { FileText, Plus, Loader2, Sparkles } from "lucide-react";

const FORMATOS: ContenidoFormato[] = ["post", "reel", "story", "carrusel", "video", "infografia"];
const ESTADOS: ContenidoEstado[] = ["borrador", "revisado", "aprobado", "publicado"];
const TONOS = ["formal", "cercano", "energico", "informativo", "motivacional"];

const toOpts = (arr: string[]) => arr.map((v) => ({ value: v, label: v }));

export default function ContenidoPage() {
  const [filters, setFilters] = useState<ContenidoFilters>({});
  const [dialogOpen, setDialogOpen] = useState(false);
  const [genForm, setGenForm] = useState({ dirigente_id: "", formato: "", tema: "", tono: "" });

  const { data, isLoading } = useContenidos(filters);
  const { data: dirigentesData } = useDirigentes({ per_page: 50 });
  const generateContent = useGenerateContent();
  const updateEstado = useUpdateContenidoEstado();
  const items = data?.items ?? [];
  const dirigentesForSelect = dirigentesData?.items ?? [];

  const handleGenerate = async () => {
    if (!genForm.dirigente_id || !genForm.formato || !genForm.tema || !genForm.tono) return;
    await generateContent.mutateAsync({
      dirigente_id: Number(genForm.dirigente_id),
      formato: genForm.formato as ContenidoFormato,
      tema: genForm.tema,
      tono: genForm.tono,
    });
    setDialogOpen(false);
    setGenForm({ dirigente_id: "", formato: "", tema: "", tono: "" });
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Content Factory</h1>
          <p className="text-sm text-muted-foreground">Generacion y gestion de contenido con IA</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2"><Plus className="h-4 w-4" />Generar</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Generar Contenido</DialogTitle>
              <DialogDescription>Configura los parametros para generar contenido con IA.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label className="text-sm font-medium">Dirigente</label>
                <Select value={genForm.dirigente_id} onValueChange={(v) => setGenForm((f) => ({ ...f, dirigente_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Seleccionar dirigente" /></SelectTrigger>
                  <SelectContent>{dirigentesForSelect.map((d) => <SelectItem key={d.id} value={String(d.id)}>{d.full_name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium">Formato</label>
                <Select value={genForm.formato} onValueChange={(v) => setGenForm((f) => ({ ...f, formato: v }))}>
                  <SelectTrigger><SelectValue placeholder="Seleccionar formato" /></SelectTrigger>
                  <SelectContent>{FORMATOS.map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <label htmlFor="gen-tema" className="text-sm font-medium">Tema</label>
                <Input id="gen-tema" placeholder="Tema del contenido" value={genForm.tema} onChange={(e) => setGenForm((f) => ({ ...f, tema: e.target.value }))} />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium">Tono</label>
                <Select value={genForm.tono} onValueChange={(v) => setGenForm((f) => ({ ...f, tono: v }))}>
                  <SelectTrigger><SelectValue placeholder="Seleccionar tono" /></SelectTrigger>
                  <SelectContent>{TONOS.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleGenerate} disabled={generateContent.isPending} className="gap-2">
                {generateContent.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Generar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </header>

      <div className="flex flex-wrap gap-3">
        <FilterSelect value={filters.formato} onValueChange={(v) => setFilters((f) => ({ ...f, formato: v as ContenidoFormato | undefined }))} placeholder="Formato" options={toOpts(FORMATOS)} allLabel="Todos los formatos" />
        <FilterSelect value={filters.estado} onValueChange={(v) => setFilters((f) => ({ ...f, estado: v as ContenidoEstado | undefined }))} placeholder="Estado" options={toOpts(ESTADOS)} allLabel="Todos los estados" />
      </div>

      <section className="space-y-3" aria-label="Lista de contenidos">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="card-elevated"><CardContent className="p-5"><Skeleton className="mb-2 h-5 w-48" /><Skeleton className="mb-1 h-4 w-full" /><Skeleton className="h-4 w-3/4" /></CardContent></Card>
          ))
        ) : items.length === 0 ? (
          <Card><CardContent className="flex flex-col items-center justify-center py-12 text-center"><FileText className="mb-3 h-10 w-10 text-muted-foreground/50" /><p className="text-sm text-muted-foreground">No hay contenidos. Genera el primero.</p></CardContent></Card>
        ) : (
          items.map((item) => (
            <ContentCard key={item.id} item={item} onAdvance={(id, estado) => updateEstado.mutate({ id, estado })} advancing={updateEstado.isPending} />
          ))
        )}
      </section>
    </div>
  );
}
