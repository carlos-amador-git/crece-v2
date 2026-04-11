"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FilterSelect } from "@/components/dashboard/filter-select";
import {
  Vote,
  Plus,
  ThumbsUp,
  MessageCircle,
  Clock,
  CheckCircle2,
  XCircle,
  Users,
  Trophy,
  CalendarClock,
  Filter,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

type CategoriaId =
  | "movilidad"
  | "seguridad"
  | "agua"
  | "empleo"
  | "servicios";

type EstadoPropuesta =
  | "en_deliberacion"
  | "en_votacion"
  | "aprobada"
  | "rechazada";

type OpcionVoto = "si" | "no" | "abstencion";

interface Propuesta {
  id: string;
  titulo: string;
  descripcion: string;
  autor: string;
  fecha: string;
  categoria: CategoriaId;
  estado: EstadoPropuesta;
  apoyos: number;
  comentarios: number;
  apoyada: boolean;
}

interface Votacion {
  id: string;
  pregunta: string;
  descripcion: string;
  propuesta_id: string;
  fecha_limite: string;
  opciones: { id: OpcionVoto; label: string; votos: number }[];
  total_votos: number;
  meta_participacion: number;
  votado: OpcionVoto | null;
}

interface Resultado {
  id: string;
  titulo: string;
  categoria: CategoriaId;
  porcentaje_apoyo: number;
  total_votos: number;
  fecha_cierre: string;
  estado: "aprobada" | "rechazada";
}

// ── Constants ──────────────────────────────────────────────────────

const CATEGORIAS: { value: CategoriaId; label: string; color: string }[] = [
  { value: "movilidad", label: "Movilidad", color: "bg-blue-500/10 text-blue-600 dark:text-blue-400" },
  { value: "seguridad", label: "Seguridad", color: "bg-red-500/10 text-red-600 dark:text-red-400" },
  { value: "agua", label: "Agua", color: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400" },
  { value: "empleo", label: "Empleo", color: "bg-amber-500/10 text-amber-600 dark:text-amber-400" },
  { value: "servicios", label: "Servicios", color: "bg-purple-500/10 text-purple-600 dark:text-purple-400" },
];

const ESTADO_CONFIG: Record<
  EstadoPropuesta,
  { label: string; variant: "default" | "warning" | "success" | "danger" }
> = {
  en_deliberacion: { label: "En deliberacion", variant: "default" },
  en_votacion: { label: "En votacion", variant: "warning" },
  aprobada: { label: "Aprobada", variant: "success" },
  rechazada: { label: "Rechazada", variant: "danger" },
};

// ── Mock data ──────────────────────────────────────────────────────

const PROPUESTAS_MOCK: Propuesta[] = [
  {
    id: "p1",
    titulo: "Ciclovias protegidas en Av. Insurgentes Sur",
    descripcion:
      "Implementar ciclovias protegidas con bolardos y senalizacion en Av. Insurgentes Sur, tramo Mixcoac a CU. Incluye estaciones de bicicleta publica y senaletica bilingue.",
    autor: "Maria Gonzalez",
    fecha: "2026-03-28",
    categoria: "movilidad",
    estado: "en_deliberacion",
    apoyos: 342,
    comentarios: 47,
    apoyada: false,
  },
  {
    id: "p2",
    titulo: "Camaras de videovigilancia en Col. Roma Norte",
    descripcion:
      "Instalar 120 camaras de videovigilancia conectadas al C5 en puntos criticos de la Col. Roma Norte y Condesa, con monitoreo 24/7 y respuesta rapida.",
    autor: "Carlos Mendez",
    fecha: "2026-03-25",
    categoria: "seguridad",
    estado: "en_votacion",
    apoyos: 589,
    comentarios: 92,
    apoyada: true,
  },
  {
    id: "p3",
    titulo: "Sistema de captacion pluvial en escuelas publicas",
    descripcion:
      "Instalar sistemas de captacion de agua de lluvia en 50 escuelas publicas de la alcaldia, con filtrado y almacenamiento para riego de areas verdes y sanitarios.",
    autor: "Ana Lopez",
    fecha: "2026-03-20",
    categoria: "agua",
    estado: "en_deliberacion",
    apoyos: 215,
    comentarios: 31,
    apoyada: false,
  },
  {
    id: "p4",
    titulo: "Incubadora de emprendimientos juveniles en Coyoacan",
    descripcion:
      "Crear un espacio de coworking y mentoria para jovenes emprendedores de 18-35 anos, con acceso a financiamiento y capacitacion en tecnologia y negocios.",
    autor: "Roberto Diaz",
    fecha: "2026-03-15",
    categoria: "empleo",
    estado: "aprobada",
    apoyos: 723,
    comentarios: 156,
    apoyada: true,
  },
  {
    id: "p5",
    titulo: "Rehabilitacion de luminarias en Tlalpan Centro",
    descripcion:
      "Sustituir 800 luminarias por tecnologia LED de bajo consumo en el centro historico de Tlalpan, mejorando visibilidad nocturna y reduciendo consumo energetico.",
    autor: "Laura Torres",
    fecha: "2026-03-10",
    categoria: "servicios",
    estado: "rechazada",
    apoyos: 98,
    comentarios: 23,
    apoyada: false,
  },
  {
    id: "p6",
    titulo: "Ampliacion de ruta de Metrobus Linea 7",
    descripcion:
      "Extender la Linea 7 del Metrobus desde Indios Verdes hasta Cuautepec, conectando comunidades del norte con la red de transporte publico masivo.",
    autor: "Fernando Ruiz",
    fecha: "2026-03-08",
    categoria: "movilidad",
    estado: "en_deliberacion",
    apoyos: 456,
    comentarios: 78,
    apoyada: false,
  },
];

const VOTACIONES_MOCK: Votacion[] = [
  {
    id: "v1",
    pregunta: "Aprueba la instalacion de camaras de videovigilancia en Col. Roma Norte?",
    descripcion: "120 camaras conectadas al C5 con monitoreo 24/7. Presupuesto estimado: $4.2M MXN.",
    propuesta_id: "p2",
    fecha_limite: "2026-04-15",
    opciones: [
      { id: "si", label: "A favor", votos: 1234 },
      { id: "no", label: "En contra", votos: 456 },
      { id: "abstencion", label: "Abstencion", votos: 89 },
    ],
    total_votos: 1779,
    meta_participacion: 3000,
    votado: null,
  },
  {
    id: "v2",
    pregunta: "Priorizar presupuesto para captacion pluvial sobre reparacion de fugas?",
    descripcion: "Reasignar $1.8M del presupuesto de reparacion de fugas al programa de captacion pluvial en escuelas.",
    propuesta_id: "p3",
    fecha_limite: "2026-04-20",
    opciones: [
      { id: "si", label: "A favor", votos: 890 },
      { id: "no", label: "En contra", votos: 678 },
      { id: "abstencion", label: "Abstencion", votos: 123 },
    ],
    total_votos: 1691,
    meta_participacion: 2500,
    votado: null,
  },
  {
    id: "v3",
    pregunta: "Extender horario de Metrobus a servicio nocturno los fines de semana?",
    descripcion: "Servicio de 00:00 a 05:00 viernes y sabados en lineas principales. Costo operativo adicional: $800K/mes.",
    propuesta_id: "p6",
    fecha_limite: "2026-04-10",
    opciones: [
      { id: "si", label: "A favor", votos: 2100 },
      { id: "no", label: "En contra", votos: 340 },
      { id: "abstencion", label: "Abstencion", votos: 67 },
    ],
    total_votos: 2507,
    meta_participacion: 3000,
    votado: null,
  },
];

const RESULTADOS_MOCK: Resultado[] = [
  {
    id: "r1",
    titulo: "Incubadora de emprendimientos juveniles en Coyoacan",
    categoria: "empleo",
    porcentaje_apoyo: 78.4,
    total_votos: 2890,
    fecha_cierre: "2026-03-01",
    estado: "aprobada",
  },
  {
    id: "r2",
    titulo: "Peatonalizacion de calle Madero los domingos",
    categoria: "movilidad",
    porcentaje_apoyo: 65.2,
    total_votos: 3456,
    fecha_cierre: "2026-02-15",
    estado: "aprobada",
  },
  {
    id: "r3",
    titulo: "Rehabilitacion de luminarias en Tlalpan Centro",
    categoria: "servicios",
    porcentaje_apoyo: 34.7,
    total_votos: 1230,
    fecha_cierre: "2026-02-01",
    estado: "rechazada",
  },
  {
    id: "r4",
    titulo: "Programa de cisternas comunitarias en Iztapalapa",
    categoria: "agua",
    porcentaje_apoyo: 89.1,
    total_votos: 4120,
    fecha_cierre: "2026-01-20",
    estado: "aprobada",
  },
  {
    id: "r5",
    titulo: "Centro de mediacion vecinal en Benito Juarez",
    categoria: "seguridad",
    porcentaje_apoyo: 71.8,
    total_votos: 1890,
    fecha_cierre: "2026-01-10",
    estado: "aprobada",
  },
];

// ── Helpers ────────────────────────────────────────────────────────

function getCategoriaInfo(id: CategoriaId) {
  return CATEGORIAS.find((c) => c.value === id) ?? CATEGORIAS[0];
}

function formatDateShort(iso: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(iso));
}

function daysUntil(iso: string): number {
  const diff = new Date(iso).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

// ── Components ─────────────────────────────────────────────────────

function PropuestaCard({
  propuesta,
  onApoyar,
}: {
  propuesta: Propuesta;
  onApoyar: (id: string) => void;
}) {
  const cat = getCategoriaInfo(propuesta.categoria);
  const estado = ESTADO_CONFIG[propuesta.estado];

  return (
    <Card className="group transition-shadow duration-150 hover:shadow-md">
      <CardContent className="p-5">
        <div className="flex flex-col gap-3">
          {/* Top row: badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${cat.color}`}
            >
              {cat.label}
            </span>
            <Badge variant={estado.variant}>{estado.label}</Badge>
          </div>

          {/* Title + description */}
          <div>
            <h3 className="font-heading text-base font-semibold leading-snug">
              {propuesta.titulo}
            </h3>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground line-clamp-2">
              {propuesta.descripcion}
            </p>
          </div>

          {/* Author + date */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Users className="h-3 w-3" />
              {propuesta.autor}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDateShort(propuesta.fecha)}
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 border-t pt-3">
            <Button
              variant={propuesta.apoyada ? "default" : "outline"}
              size="sm"
              className={`gap-1.5 ${
                propuesta.apoyada
                  ? "bg-[#FF6B00] text-white hover:bg-[#FF6B00]/90"
                  : "hover:border-[#FF6B00] hover:text-[#FF6B00]"
              }`}
              onClick={() => onApoyar(propuesta.id)}
            >
              <ThumbsUp className="h-3.5 w-3.5" />
              <span className="tabular-nums">{propuesta.apoyos}</span>
              Apoyar
            </Button>
            <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
              <MessageCircle className="h-3.5 w-3.5" />
              <span className="tabular-nums">{propuesta.comentarios}</span>
              Comentar
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function VotacionCard({
  votacion,
  onVotar,
}: {
  votacion: Votacion;
  onVotar: (votacionId: string, opcion: OpcionVoto) => void;
}) {
  const participacion = Math.round(
    (votacion.total_votos / votacion.meta_participacion) * 100
  );
  const dias = daysUntil(votacion.fecha_limite);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base leading-snug">
              {votacion.pregunta}
            </CardTitle>
            <CardDescription className="mt-1">
              {votacion.descripcion}
            </CardDescription>
          </div>
          <Badge
            variant={dias <= 3 ? "danger" : "warning"}
            className="shrink-0"
          >
            <CalendarClock className="mr-1 h-3 w-3" />
            {dias === 0 ? "Ultimo dia" : `${dias} dias`}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Participacion</span>
            <span className="font-medium tabular-nums">
              {votacion.total_votos.toLocaleString("es-MX")} /{" "}
              {votacion.meta_participacion.toLocaleString("es-MX")}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-[#FF6B00] transition-all duration-500"
              style={{ width: `${Math.min(participacion, 100)}%` }}
            />
          </div>
          <p className="mt-1 text-right text-xs tabular-nums text-muted-foreground">
            {participacion}% de la meta
          </p>
        </div>

        {/* Vote options */}
        <div className="grid gap-2 sm:grid-cols-3">
          {votacion.opciones.map((op) => {
            const pct =
              votacion.total_votos > 0
                ? Math.round((op.votos / votacion.total_votos) * 100)
                : 0;
            const isVoted = votacion.votado === op.id;

            return (
              <button
                key={op.id}
                type="button"
                onClick={() => onVotar(votacion.id, op.id)}
                disabled={votacion.votado !== null}
                className={`relative flex flex-col items-center gap-1 overflow-hidden rounded-lg border px-4 py-3 text-sm font-medium transition-all duration-150
                  ${
                    isVoted
                      ? "border-[#FF6B00] bg-[#FF6B00]/5 text-[#FF6B00]"
                      : votacion.votado !== null
                        ? "cursor-not-allowed border-border bg-muted/30 text-muted-foreground"
                        : "cursor-pointer border-border hover:border-[#FF6B00]/50 hover:bg-[#FF6B00]/5"
                  }
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`}
              >
                {/* Background fill for results */}
                <div
                  className="absolute inset-0 bg-current opacity-[0.04] transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
                <span className="relative z-10">{op.label}</span>
                <span className="relative z-10 tabular-nums text-xs text-muted-foreground">
                  {op.votos.toLocaleString("es-MX")} ({pct}%)
                </span>
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function ResultadoCard({ resultado }: { resultado: Resultado }) {
  const cat = getCategoriaInfo(resultado.categoria);
  const aprobada = resultado.estado === "aprobada";

  return (
    <Card
      className={`border-l-4 ${
        aprobada ? "border-l-emerald-500" : "border-l-red-400"
      }`}
    >
      <CardContent className="flex items-center gap-4 p-4">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
            aprobada
              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
              : "bg-red-500/10 text-red-600 dark:text-red-400"
          }`}
        >
          {aprobada ? (
            <CheckCircle2 className="h-5 w-5" />
          ) : (
            <XCircle className="h-5 w-5" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-heading text-sm font-semibold">
            {resultado.titulo}
          </h3>
          <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${cat.color}`}>
              {cat.label}
            </span>
            <span className="tabular-nums">
              {resultado.total_votos.toLocaleString("es-MX")} votos
            </span>
            <span>{formatDateShort(resultado.fecha_cierre)}</span>
          </div>
        </div>
        <div className="text-right">
          <p
            className={`tabular-nums text-lg font-bold ${
              aprobada
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            {resultado.porcentaje_apoyo}%
          </p>
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
            apoyo
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function ParticipacionChart({
  resultados,
}: {
  resultados: Resultado[];
}) {
  const maxVotos = Math.max(...resultados.map((r) => r.total_votos));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Trophy className="h-4.5 w-4.5 text-[#FF6B00]" />
          Participacion por propuesta
        </CardTitle>
        <CardDescription>
          Total de votos emitidos en cada consulta cerrada
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {resultados.map((r) => {
            const width = maxVotos > 0 ? (r.total_votos / maxVotos) * 100 : 0;
            const cat = getCategoriaInfo(r.categoria);

            return (
              <div key={r.id} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="max-w-[70%] truncate font-medium">
                    {r.titulo}
                  </span>
                  <span className="tabular-nums text-xs text-muted-foreground">
                    {r.total_votos.toLocaleString("es-MX")}
                  </span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      r.estado === "aprobada"
                        ? "bg-emerald-500"
                        : "bg-red-400"
                    }`}
                    style={{ width: `${width}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Stats summary ──────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#FF6B00]/10 text-[#FF6B00]">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="tabular-nums font-heading text-xl font-bold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main page ──────────────────────────────────────────────────────

export default function ParticipacionPage() {
  const [propuestas, setPropuestas] = useState(PROPUESTAS_MOCK);
  const [votaciones, setVotaciones] = useState(VOTACIONES_MOCK);
  const [filtroCategoria, setFiltroCategoria] = useState<string | undefined>(
    undefined
  );
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    titulo: "",
    descripcion: "",
    categoria: "",
  });

  // ── Handlers ───────────────────────────────────────

  const handleApoyar = (id: string) => {
    setPropuestas((prev) =>
      prev.map((p) =>
        p.id === id
          ? {
              ...p,
              apoyada: !p.apoyada,
              apoyos: p.apoyada ? p.apoyos - 1 : p.apoyos + 1,
            }
          : p
      )
    );
  };

  const handleVotar = (votacionId: string, opcion: OpcionVoto) => {
    setVotaciones((prev) =>
      prev.map((v) =>
        v.id === votacionId
          ? {
              ...v,
              votado: opcion,
              total_votos: v.total_votos + 1,
              opciones: v.opciones.map((o) =>
                o.id === opcion ? { ...o, votos: o.votos + 1 } : o
              ),
            }
          : v
      )
    );
  };

  const handleCrearPropuesta = () => {
    if (!form.titulo || !form.descripcion || !form.categoria) return;

    const nueva: Propuesta = {
      id: `p${Date.now()}`,
      titulo: form.titulo,
      descripcion: form.descripcion,
      autor: "Admin",
      fecha: new Date().toISOString().slice(0, 10),
      categoria: form.categoria as CategoriaId,
      estado: "en_deliberacion",
      apoyos: 0,
      comentarios: 0,
      apoyada: false,
    };

    setPropuestas((prev) => [nueva, ...prev]);
    setDialogOpen(false);
    setForm({ titulo: "", descripcion: "", categoria: "" });
  };

  // ── Filtered propuestas ────────────────────────────

  const propuestasFiltradas = filtroCategoria
    ? propuestas.filter((p) => p.categoria === filtroCategoria)
    : propuestas;

  // ── Stats ──────────────────────────────────────────

  const totalPropuestas = propuestas.length;
  const enDeliberacion = propuestas.filter(
    (p) => p.estado === "en_deliberacion"
  ).length;
  const votacionesAbiertas = votaciones.length;
  const totalVotos = RESULTADOS_MOCK.reduce((s, r) => s + r.total_votos, 0);

  return (
    <div className="space-y-6">
      {/* ── Demo disclosure banner ──────────────────────── */}
      <div
        role="note"
        className="flex items-start gap-3 rounded-md border border-amber-300/40 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800/50 dark:bg-amber-950/40 dark:text-amber-200"
      >
        <Filter className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-semibold">Módulo demo — datos no conectados al backend</p>
          <p className="text-xs opacity-90">
            Las propuestas, votaciones y resultados son un ejemplo estático estilo Decidim.
            El módulo de Decidim fue excluido del scope de CRECE — el backend real
            (<code>/api/v1/participacion</code>) gestiona solicitudes ciudadanas vía Chatwoot, no propuestas.
          </p>
        </div>
      </div>

      {/* ── Header ──────────────────────────────────────── */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold">
            Participacion Ciudadana
          </h1>
          <p className="text-sm text-muted-foreground">
            Deliberacion, votacion y seguimiento de propuestas ciudadanas — estilo Decidim (demo)
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2 bg-[#FF6B00] text-white hover:bg-[#FF6B00]/90">
              <Plus className="h-4 w-4" />
              Nueva Propuesta
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nueva Propuesta</DialogTitle>
              <DialogDescription>
                Publica una propuesta para que la ciudadania delibere y vote.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label htmlFor="prop-titulo" className="text-sm font-medium">
                  Titulo
                </label>
                <Input
                  id="prop-titulo"
                  placeholder="Titulo claro y conciso"
                  value={form.titulo}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, titulo: e.target.value }))
                  }
                />
              </div>
              <div className="grid gap-2">
                <label htmlFor="prop-desc" className="text-sm font-medium">
                  Descripcion
                </label>
                <textarea
                  id="prop-desc"
                  rows={4}
                  placeholder="Describe la propuesta, su justificacion y el impacto esperado..."
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  value={form.descripcion}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, descripcion: e.target.value }))
                  }
                />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium">Categoria</label>
                <FilterSelect
                  value={form.categoria || undefined}
                  onValueChange={(v) =>
                    setForm((f) => ({ ...f, categoria: v ?? "" }))
                  }
                  placeholder="Categoria"
                  options={CATEGORIAS.map((c) => ({
                    value: c.value,
                    label: c.label,
                  }))}
                  allLabel="Seleccionar categoria"
                  className="w-full"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                onClick={handleCrearPropuesta}
                className="gap-2 bg-[#FF6B00] text-white hover:bg-[#FF6B00]/90"
                disabled={!form.titulo || !form.descripcion || !form.categoria}
              >
                <Vote className="h-4 w-4" />
                Publicar Propuesta
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </header>

      {/* ── Stats ───────────────────────────────────────── */}
      <section
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Estadisticas de participacion"
      >
        <StatCard
          label="Propuestas Activas"
          value={totalPropuestas}
          icon={MessageCircle}
        />
        <StatCard
          label="En Deliberacion"
          value={enDeliberacion}
          icon={Users}
        />
        <StatCard
          label="Votaciones Abiertas"
          value={votacionesAbiertas}
          icon={Vote}
        />
        <StatCard
          label="Total Votos Emitidos"
          value={totalVotos.toLocaleString("es-MX")}
          icon={Trophy}
        />
      </section>

      {/* ── Tabs ────────────────────────────────────────── */}
      <Tabs defaultValue="propuestas">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="propuestas" className="gap-1.5">
            <MessageCircle className="h-3.5 w-3.5" />
            Propuestas Activas
          </TabsTrigger>
          <TabsTrigger value="votaciones" className="gap-1.5">
            <Vote className="h-3.5 w-3.5" />
            Votaciones
          </TabsTrigger>
          <TabsTrigger value="resultados" className="gap-1.5">
            <Trophy className="h-3.5 w-3.5" />
            Resultados
          </TabsTrigger>
        </TabsList>

        {/* ── Tab: Propuestas Activas ───────────────────── */}
        <TabsContent value="propuestas" className="space-y-4">
          {/* Category filters */}
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <button
              type="button"
              onClick={() => setFiltroCategoria(undefined)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors duration-150 ${
                !filtroCategoria
                  ? "bg-[#FF6B00] text-white"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              Todas
            </button>
            {CATEGORIAS.map((cat) => (
              <button
                key={cat.value}
                type="button"
                onClick={() => setFiltroCategoria(cat.value)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors duration-150 ${
                  filtroCategoria === cat.value
                    ? "bg-[#FF6B00] text-white"
                    : "bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Propuestas grid */}
          {propuestasFiltradas.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <MessageCircle className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No hay propuestas en esta categoria
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {propuestasFiltradas.map((p) => (
                <PropuestaCard
                  key={p.id}
                  propuesta={p}
                  onApoyar={handleApoyar}
                />
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── Tab: Votaciones ──────────────────────────── */}
        <TabsContent value="votaciones" className="space-y-4">
          {votaciones.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <Vote className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No hay votaciones abiertas en este momento
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {votaciones.map((v) => (
                <VotacionCard
                  key={v.id}
                  votacion={v}
                  onVotar={handleVotar}
                />
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── Tab: Resultados ─────────────────────────── */}
        <TabsContent value="resultados" className="space-y-6">
          {/* Participation chart */}
          <ParticipacionChart resultados={RESULTADOS_MOCK} />

          {/* Results list */}
          <div>
            <h2 className="mb-3 font-heading text-lg font-semibold">
              Propuestas Cerradas
            </h2>
            <div className="space-y-3">
              {RESULTADOS_MOCK.map((r) => (
                <ResultadoCard key={r.id} resultado={r} />
              ))}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
