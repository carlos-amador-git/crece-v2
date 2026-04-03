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
import type { DirigenteFilters, SocialPlatform } from "@/lib/api/types";
import {
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
  Eye,
  Users,
  Filter,
} from "lucide-react";

/* ---- Mock data ---- */
const MOCK_DIRIGENTES = [
  {
    id: 1, nombre: "Ana", apellido_paterno: "Martinez", apellido_materno: "Vega",
    cargo: "Diputada Federal", partido: "MORENA", estado: "CDMX",
    ipd_score: 9.2, platforms: ["twitter", "instagram", "facebook"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 1800000).toISOString(),
    created_at: "2024-01-15", updated_at: "2024-12-01",
  },
  {
    id: 2, nombre: "Carlos", apellido_paterno: "Ruiz", apellido_materno: "Lopez",
    cargo: "Senador", partido: "PAN", estado: "Jalisco",
    ipd_score: 8.7, platforms: ["twitter", "facebook", "youtube"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 7200000).toISOString(),
    created_at: "2024-02-10", updated_at: "2024-11-28",
  },
  {
    id: 3, nombre: "Maria", apellido_paterno: "Lopez", apellido_materno: "Gomez",
    cargo: "Gobernadora", partido: "PRI", estado: "Estado de Mexico",
    ipd_score: 8.1, platforms: ["twitter", "instagram", "tiktok", "facebook"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 3600000).toISOString(),
    created_at: "2024-03-05", updated_at: "2024-12-02",
  },
  {
    id: 4, nombre: "Jose", apellido_paterno: "Garcia", apellido_materno: "Hernandez",
    cargo: "Alcalde", partido: "MC", estado: "Nuevo Leon",
    ipd_score: 7.8, platforms: ["twitter", "instagram"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 14400000).toISOString(),
    created_at: "2024-01-20", updated_at: "2024-11-30",
  },
  {
    id: 5, nombre: "Laura", apellido_paterno: "Sanchez", apellido_materno: "Torres",
    cargo: "Diputada Local", partido: "MORENA", estado: "Puebla",
    ipd_score: 7.5, platforms: ["facebook", "tiktok"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 28800000).toISOString(),
    created_at: "2024-04-12", updated_at: "2024-11-25",
  },
  {
    id: 6, nombre: "Pedro", apellido_paterno: "Hernandez", apellido_materno: "Diaz",
    cargo: "Senador", partido: "PVEM", estado: "Veracruz",
    ipd_score: 7.2, platforms: ["twitter", "youtube"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 43200000).toISOString(),
    created_at: "2024-05-08", updated_at: "2024-11-20",
  },
  {
    id: 7, nombre: "Sofia", apellido_paterno: "Torres",
    cargo: "Presidenta Municipal", partido: "PAN", estado: "Guanajuato",
    ipd_score: 6.9, platforms: ["instagram", "facebook", "tiktok"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 86400000).toISOString(),
    created_at: "2024-06-01", updated_at: "2024-11-15",
  },
  {
    id: 8, nombre: "Roberto", apellido_paterno: "Diaz", apellido_materno: "Flores",
    cargo: "Diputado Federal", partido: "PT", estado: "Oaxaca",
    ipd_score: 6.5, platforms: ["twitter", "facebook"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 172800000).toISOString(),
    created_at: "2024-02-28", updated_at: "2024-11-10",
  },
  {
    id: 9, nombre: "Isabel", apellido_paterno: "Morales",
    cargo: "Regidora", partido: "PRI", estado: "Sonora",
    ipd_score: 3.1, platforms: ["facebook"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 604800000).toISOString(),
    created_at: "2024-07-15", updated_at: "2024-10-30",
  },
  {
    id: 10, nombre: "Miguel", apellido_paterno: "Flores", apellido_materno: "Reyes",
    cargo: "Delegado", partido: "MC", estado: "CDMX",
    ipd_score: 2.4, platforms: ["twitter"] as SocialPlatform[],
    last_activity: new Date(Date.now() - 1209600000).toISOString(),
    created_at: "2024-08-01", updated_at: "2024-10-15",
  },
];

const PARTIDOS = ["MORENA", "PAN", "PRI", "MC", "PVEM", "PT"];
const ESTADOS = ["CDMX", "Jalisco", "Estado de Mexico", "Nuevo Leon", "Puebla", "Veracruz", "Guanajuato", "Oaxaca", "Sonora"];

export default function DirigentesPage() {
  const [filters, setFilters] = useState<DirigenteFilters>({
    page: 1,
    per_page: 20,
  });
  const [addOpen, setAddOpen] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading } = useDirigentes(filters);

  const dirigentes = data?.items ?? MOCK_DIRIGENTES;
  const total = data?.total ?? MOCK_DIRIGENTES.length;

  const filtered = search
    ? dirigentes.filter(
        (d) =>
          `${d.nombre} ${d.apellido_paterno}`
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
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Users className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                No se encontraron dirigentes
              </p>
            </div>
          ) : (
            <Table>
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
                      {d.nombre} {d.apellido_paterno}
                      {d.apellido_materno ? ` ${d.apellido_materno}` : ""}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {d.cargo}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{d.partido}</Badge>
                    </TableCell>
                    <TableCell className="text-center tabular-nums">
                      <IpdScoreBadge score={d.ipd_score} size="sm" />
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1.5">
                        {d.platforms.map((p) => (
                          <PlatformIcon key={p} platform={p} size={14} />
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {d.last_activity
                        ? formatRelativeTime(d.last_activity)
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
