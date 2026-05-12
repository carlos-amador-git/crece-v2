"use client";

import { useState } from "react";
import { useCiudadanos } from "@/lib/api/hooks/use-ciudadanos";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { formatNumber } from "@/lib/utils";
import type { CiudadanoFilters } from "@/lib/api/types";
import { Users, Search, Plus, Phone, Mail, UserCheck, ChevronLeft, ChevronRight } from "lucide-react";

const ESCOLARIDAD_LABELS: Record<string, string> = {
  sin_estudios: "Sin estudios",
  primaria: "Primaria",
  secundaria: "Secundaria",
  preparatoria: "Preparatoria",
  licenciatura: "Licenciatura",
  posgrado: "Posgrado",
};

const EDAD_LABELS: Record<string, string> = {
  "18_24": "18-24",
  "25_34": "25-34",
  "35_44": "35-44",
  "45_54": "45-54",
  "55_64": "55-64",
  "65_plus": "65+",
};

export default function CiudadanosPage() {
  const [filters, setFilters] = useState<CiudadanoFilters>({ page: 1, per_page: 20 });
  const [search, setSearch] = useState("");
  const [addOpen, setAddOpen] = useState(false);

  const { data, isLoading, isError } = useCiudadanos({
    ...filters,
    search: search || undefined,
  });

  const ciudadanos = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;
  const currentPage = filters.page ?? 1;

  // Compute KPI counters from current page (approximation — full count would need backend aggregation)
  const withPhone = ciudadanos.filter((c) => c.telefono).length;
  const withEmail = ciudadanos.filter((c) => c.email).length;
  const simpatizantes = ciudadanos.filter((c) => c.es_simpatizante_mc).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">CRM Ciudadanos</h1>
          <p className="text-sm text-muted-foreground">
            {formatNumber(total)} ciudadanos registrados
          </p>
        </div>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4" />Agregar Ciudadano</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Agregar Ciudadano</DialogTitle>
              <DialogDescription>Registra un nuevo ciudadano en el CRM</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Nombre</label>
                  <Input placeholder="Nombre" />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Apellido Paterno</label>
                  <Input placeholder="Apellido paterno" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Telefono</label>
                  <Input placeholder="55 1234 5678" />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Email</label>
                  <Input placeholder="correo@ejemplo.com" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Seccion Electoral</label>
                  <Input placeholder="Seccion ID" />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Colonia</label>
                  <Input placeholder="Colonia" />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={() => setAddOpen(false)}>Guardar</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">Total Ciudadanos</p>
              <Users className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-1 font-heading text-2xl font-bold tabular-nums">{formatNumber(total)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">Con Telefono</p>
              <Phone className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-1 font-heading text-2xl font-bold tabular-nums">{withPhone}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">Con Email</p>
              <Mail className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-1 font-heading text-2xl font-bold tabular-nums">{withEmail}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">Simpatizantes MC</p>
              <UserCheck className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-1 font-heading text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{simpatizantes}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por nombre..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setFilters((f) => ({ ...f, page: 1 })); }}
                className="pl-9"
              />
            </div>
            <Select
              value={filters.intencion_voto ?? "all"}
              onValueChange={(v) => setFilters((f) => ({ ...f, intencion_voto: v === "all" ? undefined : v as any, page: 1 }))}
            >
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Simpatizante" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="mc">Simpatizante MC</SelectItem>
                <SelectItem value="indeciso">Indeciso</SelectItem>
                <SelectItem value="morena">Morena</SelectItem>
                <SelectItem value="pan">PAN</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={filters.escolaridad ?? "all"}
              onValueChange={(v) => setFilters((f) => ({ ...f, escolaridad: v === "all" ? undefined : v as any, page: 1 }))}
            >
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Escolaridad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {Object.entries(ESCOLARIDAD_LABELS).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v}</SelectItem>
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
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Users className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">Error al cargar ciudadanos</p>
            </div>
          ) : ciudadanos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Users className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">No se encontraron ciudadanos</p>
            </div>
          ) : (
            <>
              {/* Mobile: card list */}
              <div className="space-y-3 p-4 md:hidden">
                {ciudadanos.map((c) => (
                  <div key={c.id} className="rounded-lg border p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">
                          {c.nombre} {c.apellido_paterno} {c.apellido_materno ?? ""}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {c.telefono ?? "Sin tel."} {c.email ? `| ${c.email}` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {(c as any).data_source === "synthetic_census_2020" && (
                          <Badge variant="outline" className="bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 text-[10px]">Sintetico</Badge>
                        )}
                        <Badge variant={c.es_simpatizante_mc ? "default" : "secondary"} className={c.es_simpatizante_mc ? "bg-emerald-600" : ""}>
                          {c.es_simpatizante_mc ? "MC" : "No"}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                      <span>{EDAD_LABELS[c.edad_rango] ?? c.edad_rango}</span>
                      <span>{ESCOLARIDAD_LABELS[c.escolaridad ?? ""] ?? c.escolaridad ?? "-"}</span>
                      <span>Sec. {c.seccion_id}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Desktop: table */}
              <Table className="hidden md:table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Telefono</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Edad</TableHead>
                    <TableHead>Escolaridad</TableHead>
                    <TableHead>Seccion</TableHead>
                    <TableHead className="text-center">MC</TableHead>
                    <TableHead>Fuente</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ciudadanos.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium">
                        {c.nombre} {c.apellido_paterno} {c.apellido_materno ?? ""}
                      </TableCell>
                      <TableCell className="text-muted-foreground tabular-nums">
                        {c.telefono ?? "-"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {c.email ?? "-"}
                      </TableCell>
                      <TableCell>{EDAD_LABELS[c.edad_rango] ?? c.edad_rango}</TableCell>
                      <TableCell>{ESCOLARIDAD_LABELS[c.escolaridad ?? ""] ?? c.escolaridad ?? "-"}</TableCell>
                      <TableCell className="tabular-nums">{c.seccion_id}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant={c.es_simpatizante_mc ? "default" : "secondary"} className={c.es_simpatizante_mc ? "bg-emerald-600" : ""}>
                          {c.es_simpatizante_mc ? "Si" : "No"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {(c as any).data_source === "synthetic_census_2020" ? (
                          <Badge variant="outline" className="bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 text-[10px]">Sintetico</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">Real</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {pages > 1 && (
                <div className="flex items-center justify-between border-t px-4 py-3">
                  <p className="text-xs text-muted-foreground">
                    Pagina {currentPage} de {pages} ({formatNumber(total)} registros)
                  </p>
                  <div className="flex gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage <= 1}
                      onClick={() => setFilters((f) => ({ ...f, page: currentPage - 1 }))}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage >= pages}
                      onClick={() => setFilters((f) => ({ ...f, page: currentPage + 1 }))}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
