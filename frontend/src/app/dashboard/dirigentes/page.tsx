"use client";

import { useState } from "react";
import Link from "next/link";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { IpdScoreBadge } from "@/components/dirigentes/ipd-score-badge";
import { PlatformIcon } from "@/components/social/platform-icon";
import { formatRelativeTime, formatDate } from "@/lib/utils";
import type { DirigenteFilters } from "@/lib/api/types";
import {
  Search,
  Plus,
  Eye,
  Users,
} from "lucide-react";

// TODO: Fetch partido/estado options from API if a dedicated endpoint becomes available
const PARTIDOS = ["MORENA", "PAN", "PRI", "MC", "PVEM", "PT"];
const ESTADOS = ["CDMX", "Jalisco", "Estado de Mexico", "Nuevo Leon", "Puebla", "Veracruz", "Guanajuato", "Oaxaca", "Sonora"];

export default function DirigentesPage() {
  const [filters, setFilters] = useState<DirigenteFilters>({
    page: 1,
    per_page: 20,
  });
  const [addOpen, setAddOpen] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading, isError } = useDirigentes(filters);

  const dirigentes = data?.items ?? [];
  const total = data?.total ?? 0;

  const filtered = search
    ? dirigentes.filter(
        (d) =>
          d.full_name
            .toLowerCase()
            .includes(search.toLowerCase()) ||
          d.cargo.toLowerCase().includes(search.toLowerCase())
      )
    : dirigentes;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">Dirigentes</h1>
          <p className="text-sm text-muted-foreground">
            {total} dirigentes registrados
          </p>
        </div>
        <Button
          onClick={() => setAddOpen(true)}
          className="bg-cta text-cta-foreground hover:bg-cta/90"
        >
          <Plus className="h-4 w-4" />
          Agregar Dirigente
        </Button>
      </div>

      {/* Filters */}
      <Card className="card-elevated">
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por nombre o cargo..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              value={filters.partido ?? "all"}
              onValueChange={(v) =>
                setFilters((prev) => ({
                  ...prev,
                  partido: v === "all" ? undefined : v,
                }))
              }
            >
              <SelectTrigger className="w-full sm:w-[160px]">
                <SelectValue placeholder="Partido" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los partidos</SelectItem>
                {PARTIDOS.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={filters.estado ?? "all"}
              onValueChange={(v) =>
                setFilters((prev) => ({
                  ...prev,
                  estado: v === "all" ? undefined : v,
                }))
              }
            >
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los estados</SelectItem>
                {ESTADOS.map((e) => (
                  <SelectItem key={e} value={e}>
                    {e}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Users className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                Error al cargar dirigentes. Intenta de nuevo.
              </p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Users className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                No se encontraron dirigentes
              </p>
            </div>
          ) : (
            <>
              {/* Mobile: card list */}
              <div className="space-y-3 p-4 md:hidden">
                {filtered.map((d) => (
                  <Link key={d.id} href={`/dashboard/dirigentes/${d.id}`}>
                    <div className="rounded-lg border p-4 transition-colors hover:bg-muted/50">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium">{d.full_name}</p>
                          <p className="text-sm text-muted-foreground">{d.cargo}</p>
                        </div>
                        <IpdScoreBadge score={d.ipd_score ?? 0} size="sm" />
                      </div>
                      <div className="mt-3 flex items-center gap-3">
                        <Badge variant="secondary">{d.partido}</Badge>
                        <div className="flex gap-1.5">
                          {d.social_profiles?.map((sp) => (
                            <PlatformIcon key={sp.platform} platform={sp.platform} size={14} />
                          ))}
                        </div>
                        <span className="ml-auto text-xs text-muted-foreground">
                          {d.updated_at ? formatRelativeTime(d.updated_at) : "Sin actividad"}
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>

              {/* Desktop: table */}
              <Table className="hidden md:table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Cargo</TableHead>
                    <TableHead>Partido</TableHead>
                    <TableHead className="text-center">IPD</TableHead>
                    <TableHead>Plataformas</TableHead>
                    <TableHead>Ultima Actividad</TableHead>
                    <TableHead className="w-[50px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((d) => (
                    <TableRow key={d.id}>
                      <TableCell className="font-medium">
                        {d.full_name}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {d.cargo}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{d.partido}</Badge>
                      </TableCell>
                      <TableCell className="text-center tabular-nums">
                        <IpdScoreBadge score={d.ipd_score ?? 0} size="sm" />
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1.5">
                          {d.social_profiles?.map((sp) => (
                            <PlatformIcon key={sp.platform} platform={sp.platform} size={14} />
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {d.updated_at
                          ? formatRelativeTime(d.updated_at)
                          : "Sin actividad"}
                      </TableCell>
                      <TableCell>
                        <Link href={`/dashboard/dirigentes/${d.id}`}>
                          <Button variant="ghost" size="icon" aria-label="Ver detalle">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          )}
        </CardContent>
      </Card>

      {/* Add Dirigente Sheet */}
      <Sheet open={addOpen} onOpenChange={setAddOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Agregar Dirigente</SheetTitle>
            <SheetDescription>
              Registra un nuevo dirigente para monitoreo
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Nombre</label>
              <Input placeholder="Nombre completo" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Cargo</label>
              <Input placeholder="Cargo politico" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Partido</label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar partido" />
                </SelectTrigger>
                <SelectContent>
                  {PARTIDOS.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Estado</label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar estado" />
                </SelectTrigger>
                <SelectContent>
                  {ESTADOS.map((e) => (
                    <SelectItem key={e} value={e}>
                      {e}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="pt-4">
              <Button className="w-full bg-cta text-cta-foreground hover:bg-cta/90">Guardar Dirigente</Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
