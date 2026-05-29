"use client";

import { useMemo, useState } from "react";
import { useClimaPolitico } from "@/lib/api/hooks/use-clima-politico";
import type { ClimaPoliticoSerie } from "@/lib/api/hooks/use-clima-politico";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  TrendingUp, TrendingDown, LayoutGrid, LineChart as LineChartIcon,
  ChevronDown, Crown, Users2, MapPin, BarChart3, Search,
  CheckCircle2, Clock,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const AMBITO_LABELS: Record<string, string> = {
  federal: "Federal",
  estatal: "Estatal",
  municipal: "Municipal",
};

const ACTOR_COLOR: Record<string, string> = {
  "Claudia Sheinbaum Pardo": "hsl(142, 70%, 45%)",
  "Clara Brugada": "hsl(212, 70%, 55%)",
  "Salomón Jara": "hsl(40, 70%, 52%)",
};

const PALETTE = [
  "hsl(212, 70%, 55%)", "hsl(280, 65%, 55%)", "hsl(20, 75%, 55%)",
  "hsl(160, 65%, 45%)", "hsl(340, 70%, 55%)", "hsl(45, 75%, 50%)",
  "hsl(190, 70%, 50%)", "hsl(260, 60%, 60%)",
];

function getColor(nombre: string, idx = 0) {
  return ACTOR_COLOR[nombre] ?? PALETTE[idx % PALETTE.length];
}

const EXPRESIDENTES = new Set([
  "Andrés Manuel López Obrador",
  "Enrique Peña Nieto",
  "Felipe Calderón Hinojosa",
  "Vicente Fox Quesada",
  "Ernesto Zedillo Ponce de León",
]);

type Bucket = "presidenta_actual" | "expresidente" | "gobernador" | "alcalde" | "promedio" | "otro";

function bucketOf(s: ClimaPoliticoSerie): Bucket {
  if (s.actor_tipo?.startsWith("promedio") || s.actor_tipo === "presidente_aprobacion_estatal") return "promedio";
  if (s.ambito === "federal") {
    if (EXPRESIDENTES.has(s.actor_nombre)) return "expresidente";
    if (s.actor_nombre.includes("Sheinbaum") && s.actor_nombre.includes("Pardo")) return "presidenta_actual";
    if (s.actor_tipo === "presidenta") return "presidenta_actual";
    if (s.actor_tipo === "presidente") return "expresidente";
  }
  if (s.actor_tipo === "gobernador") return "gobernador";
  if (s.actor_tipo === "alcalde") return "alcalde";
  return "otro";
}

/** Heurística: si el último punto tiene fecha dentro de los 18 meses pasados, la serie está activa */
const ACTIVE_MONTHS = 18;
function isActive(serie: ClimaPoliticoSerie): boolean {
  if (serie.puntos.length === 0) return false;
  const sorted = serie.puntos.slice().sort((a, b) => a.fecha.localeCompare(b.fecha));
  const lastFecha = sorted[sorted.length - 1].fecha;
  const cutoff = new Date();
  cutoff.setMonth(cutoff.getMonth() - ACTIVE_MONTHS);
  return new Date(lastFecha) >= cutoff;
}

function deltaLabel(puntos: ClimaPoliticoSerie["puntos"], metrica: string) {
  const filtered = puntos.filter((p) => p.metrica === metrica).sort((a, b) => a.fecha.localeCompare(b.fecha));
  if (filtered.length < 1) return null;
  const last = filtered[filtered.length - 1];
  const prev = filtered.length >= 2 ? filtered[filtered.length - 2] : null;
  const delta = prev ? last.valor_pct - prev.valor_pct : null;
  return { current: last.valor_pct, delta };
}

function pivotChartData(puntos: ClimaPoliticoSerie["puntos"]) {
  const byFecha: Record<string, Record<string, number>> = {};
  for (const p of puntos) {
    if (!byFecha[p.fecha]) byFecha[p.fecha] = {};
    byFecha[p.fecha][p.metrica] = p.valor_pct;
  }
  return Object.entries(byFecha)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([fecha, vals]) => ({ fecha, ...vals }));
}

const tickFmt = (v: string) => {
  const d = new Date(v);
  return `${d.toLocaleString("es-MX", { month: "short" })} ${d.getFullYear().toString().slice(2)}`;
};

/** Devuelve la clase CSS de borde izquierdo según nivel de aprobación */
function semaphoreClass(aprobPct: number | null): string {
  if (aprobPct === null) return "border-l-4 border-l-muted";
  if (aprobPct >= 60) return "border-l-4 border-l-emerald-500";
  if (aprobPct >= 40) return "border-l-4 border-l-amber-400";
  return "border-l-4 border-l-rose-500";
}

function AprobacionCard({
  serie,
  color,
  hero = false,
  vigente,
  rank,
}: {
  serie: ClimaPoliticoSerie;
  color?: string;
  hero?: boolean;
  vigente?: boolean;
  rank?: number;
}) {
  const aprob = deltaLabel(serie.puntos, "aprobacion");
  const desaprob = deltaLabel(serie.puntos, "desaprobacion");
  const chartData = pivotChartData(serie.puntos);
  const entidadLabel = serie.actor_tipo === "alcalde" && serie.municipio
    ? `${serie.municipio}, ${serie.entidad ?? ""}`.replace(/, $/, "")
    : serie.entidad ?? "México";
  const lineColor = color ?? getColor(serie.actor_nombre);
  const borderClass = semaphoreClass(aprob?.current ?? null);

  return (
    <Card className={`flex flex-col ${borderClass} ${hero ? "bg-emerald-50/30 dark:bg-emerald-950/10" : ""}`}>
      <CardHeader className="pb-1 pt-4 px-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-1.5">
              {rank != null && (
                <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-bold tabular-nums text-muted-foreground">
                  #{rank}
                </span>
              )}
              {vigente !== undefined && (
                vigente ? (
                  <Badge variant="outline" className="gap-1 border-emerald-400/60 bg-emerald-50 px-1.5 py-0 text-[10px] text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-400">
                    <CheckCircle2 className="h-2.5 w-2.5" aria-hidden="true" />
                    En cargo
                  </Badge>
                ) : (
                  <Badge variant="outline" className="gap-1 px-1.5 py-0 text-[10px] text-muted-foreground">
                    <Clock className="h-2.5 w-2.5" aria-hidden="true" />
                    Ex-
                  </Badge>
                )
              )}
            </div>
            <CardTitle className={`leading-tight truncate ${hero ? "text-base font-bold" : "text-sm font-semibold"}`}>
              {serie.actor_nombre}
            </CardTitle>
            <CardDescription className="mt-0.5 text-[11px]">
              {AMBITO_LABELS[serie.ambito] ?? serie.ambito} — {entidadLabel}
              <span className="ml-2 text-muted-foreground/60">{chartData.length} mediciones</span>
            </CardDescription>
          </div>
          {aprob && (
            <div className="shrink-0 text-right">
              <div className={`font-heading font-bold tabular-nums text-emerald-500 ${hero ? "text-3xl" : "text-xl"}`}>
                {aprob.current.toFixed(1)}%
              </div>
              {aprob.delta != null && (
                <div className={`flex items-center justify-end gap-0.5 text-[11px] ${aprob.delta >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                  {aprob.delta >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {aprob.delta >= 0 ? "+" : ""}{aprob.delta.toFixed(1)}pp
                </div>
              )}
              {desaprob && (
                <div className="text-[11px] text-rose-400 tabular-nums">{desaprob.current.toFixed(1)}% desaprueba</div>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-3 flex-1">
        {chartData.length < 2 ? (
          <div className="flex h-20 flex-col items-center justify-center gap-1">
            <div className="font-heading text-3xl font-bold tabular-nums text-emerald-500">
              {aprob?.current.toFixed(1)}%
            </div>
            <div className="text-[10px] text-muted-foreground/50">Serie en construcción</div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={hero ? 220 : 180}>
            <LineChart data={chartData} margin={{ top: 2, right: 2, left: -24, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis
                dataKey="fecha"
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false} axisLine={false}
                tickFormatter={tickFmt}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false} axisLine={false}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "var(--radius)", fontSize: 11 }}
                labelFormatter={(l) => new Date(l).toLocaleDateString("es-MX", { month: "long", year: "numeric" })}
                formatter={(val: number, name: string) => [`${val.toFixed(1)}%`, name === "aprobacion" ? "Aprobación" : "Desaprobación"]}
              />
              <Line type="monotone" dataKey="aprobacion" stroke={lineColor} strokeWidth={2} dot={false} activeDot={{ r: 3 }} name="aprobacion" />
              {desaprob && (
                <Line type="monotone" dataKey="desaprobacion" stroke="hsl(var(--chart-negative))" strokeWidth={1.5} dot={false} strokeDasharray="4 2" activeDot={{ r: 3 }} name="desaprobacion" />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

function serieKey(s: ClimaPoliticoSerie): string {
  return s.actor_tipo === "alcalde" && s.municipio
    ? `${s.actor_nombre} (${s.municipio})`
    : s.actor_nombre;
}

function ComparativaChart({ data, metrica }: { data: ClimaPoliticoSerie[]; metrica: "aprobacion" | "desaprobacion" }) {
  const labelByKey = useMemo(() => {
    const m = new Map<string, string>();
    data.forEach((s) => m.set(serieKey(s), s.actor_nombre));
    return m;
  }, [data]);

  const byFecha: Record<string, Record<string, number>> = {};
  for (const serie of data) {
    const key = serieKey(serie);
    for (const p of serie.puntos) {
      if (p.metrica !== metrica) continue;
      if (!byFecha[p.fecha]) byFecha[p.fecha] = {};
      byFecha[p.fecha][key] = p.valor_pct;
    }
  }
  const chartData = Object.entries(byFecha)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([fecha, vals]) => ({ fecha, ...vals }));

  return (
    <Card>
      <CardContent className="pt-5 pb-4 px-4">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis
              dataKey="fecha"
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              tickLine={false} axisLine={false}
              tickFormatter={tickFmt}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              tickLine={false} axisLine={false}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: "var(--radius)", fontSize: 11 }}
              labelFormatter={(l) => new Date(l).toLocaleDateString("es-MX", { month: "long", year: "numeric" })}
              formatter={(val: number, name: string) => [`${(val as number).toFixed(1)}%`, labelByKey.get(name) ?? name]}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              formatter={(value) => <span className="text-foreground">{labelByKey.get(value as string) ?? value}</span>}
            />
            {data.map((serie, idx) => {
              const key = serieKey(serie);
              return (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={getColor(serie.actor_nombre, idx)}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  connectNulls
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function FederalTab({ buckets }: { buckets: Record<Bucket, ClimaPoliticoSerie[]> }) {
  const [showExpres, setShowExpres] = useState(true);
  const presidenta = buckets.presidenta_actual[0];
  const exps = buckets.expresidente.slice().sort((a, b) => a.actor_nombre.localeCompare(b.actor_nombre));

  return (
    <div className="space-y-5">
      {presidenta ? (
        <section>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Crown className="h-3.5 w-3.5" />
            Presidenta actual
          </div>
          <AprobacionCard serie={presidenta} color="hsl(142, 70%, 45%)" hero vigente />
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">No hay serie disponible para la presidencia actual.</p>
      )}

      {exps.length > 0 && (
        <section>
          <button
            type="button"
            onClick={() => setShowExpres(!showExpres)}
            className="mb-2 flex w-full items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground"
          >
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showExpres ? "" : "-rotate-90"}`} />
            Expresidentes ({exps.length})
          </button>
          {showExpres && (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {exps.map((s, idx) => (
                <AprobacionCard key={s.actor_nombre} serie={s} color={getColor(s.actor_nombre, idx)} vigente={false} />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

/** Sub-tabs Actuales / Histórico dentro de Gobernadores */
function GobernadoresTab({ series }: { series: ClimaPoliticoSerie[] }) {
  const { activos, historico } = useMemo(() => {
    const a: ClimaPoliticoSerie[] = [];
    const h: ClimaPoliticoSerie[] = [];
    for (const s of series) {
      (isActive(s) ? a : h).push(s);
    }
    return { activos: a, historico: h };
  }, [series]);

  const estados = useMemo(() => {
    const set = new Set(series.map((s) => s.entidad).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [series]);

  const [estado, setEstado] = useState<string>("__todos__");
  const [subTab, setSubTab] = useState<"actuales" | "historico">("actuales");

  const sourceList = subTab === "actuales" ? activos : historico;
  const filtered = estado === "__todos__" ? sourceList : sourceList.filter((s) => s.entidad === estado);

  const byEstado = useMemo(() => {
    const m: Record<string, ClimaPoliticoSerie[]> = {};
    for (const s of filtered) {
      const k = s.entidad ?? "Sin estado";
      (m[k] = m[k] ?? []).push(s);
    }
    return m;
  }, [filtered]);

  if (series.length === 0) {
    return <p className="text-sm text-muted-foreground">No hay gobernadores disponibles para tu organización.</p>;
  }

  return (
    <div className="space-y-4">
      {/* Sub-tabs Actuales / Histórico */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1 rounded-lg border bg-muted/40 p-1 w-fit">
          <button
            type="button"
            onClick={() => { setSubTab("actuales"); setEstado("__todos__"); }}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${subTab === "actuales" ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Actuales
            <span className="text-[10px] text-muted-foreground/70">{activos.length}</span>
          </button>
          <button
            type="button"
            onClick={() => { setSubTab("historico"); setEstado("__todos__"); }}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${subTab === "historico" ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            Histórico
            <span className="text-[10px] text-muted-foreground/70">{historico.length}</span>
          </button>
        </div>

        {estados.length > 1 && (
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <Select value={estado} onValueChange={setEstado}>
              <SelectTrigger className="h-8 w-[220px] text-xs">
                <SelectValue placeholder="Todos los estados" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__todos__">Todos los estados ({sourceList.length})</SelectItem>
                {estados.map((e) => (
                  <SelectItem key={e} value={e}>{e}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {Object.entries(byEstado)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([est, items]) => (
          <section key={est}>
            <div className="mb-2 sticky top-0 z-10 -mx-1 bg-background/95 px-1 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground backdrop-blur">
              {est} <span className="text-muted-foreground/50">· {items.length}</span>
            </div>
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {items
                .slice()
                .sort((a, b) => {
                  const av = deltaLabel(a.puntos, "aprobacion")?.current ?? 0;
                  const bv = deltaLabel(b.puntos, "aprobacion")?.current ?? 0;
                  return bv - av;
                })
                .map((s, idx) => (
                  <AprobacionCard
                    key={`${s.actor_nombre}-${s.entidad}`}
                    serie={s}
                    color={getColor(s.actor_nombre, idx)}
                    vigente={subTab === "actuales"}
                    rank={idx + 1}
                  />
                ))}
            </div>
          </section>
        ))}

      {filtered.length === 0 && (
        <p className="text-sm text-muted-foreground">No hay datos en esta categoría para el estado seleccionado.</p>
      )}
    </div>
  );
}

/** Sub-tabs Actuales / Histórico dentro de Alcaldes */
function AlcaldesTab({ series }: { series: ClimaPoliticoSerie[] }) {
  const { activos, historico } = useMemo(() => {
    const a: ClimaPoliticoSerie[] = [];
    const h: ClimaPoliticoSerie[] = [];
    for (const s of series) {
      (isActive(s) ? a : h).push(s);
    }
    return { activos: a, historico: h };
  }, [series]);

  const estados = useMemo(() => {
    const set = new Set(series.map((s) => s.entidad).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [series]);

  const [subTab, setSubTab] = useState<"actuales" | "historico">("actuales");
  const [estado, setEstado] = useState<string>("__todos__");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(20);

  const sourceList = subTab === "actuales" ? activos : historico;

  const filtered = useMemo(() => {
    let out = estado === "__todos__" ? sourceList : sourceList.filter((s) => s.entidad === estado);
    if (query.trim()) {
      const q = query.toLowerCase();
      out = out.filter((s) =>
        s.actor_nombre.toLowerCase().includes(q) ||
        (s.municipio ?? "").toLowerCase().includes(q)
      );
    }
    out = out.slice().sort((a, b) => {
      const ap = deltaLabel(a.puntos, "aprobacion")?.current ?? 0;
      const bp = deltaLabel(b.puntos, "aprobacion")?.current ?? 0;
      return bp - ap;
    });
    return out;
  }, [sourceList, estado, query]);

  if (series.length === 0) {
    return <p className="text-sm text-muted-foreground">No hay alcaldes disponibles para tu organización.</p>;
  }

  const visible = filtered.slice(0, limit);

  return (
    <div className="space-y-4">
      {/* Sub-tabs Actuales / Histórico */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 rounded-lg border bg-muted/40 p-1 w-fit">
          <button
            type="button"
            onClick={() => { setSubTab("actuales"); setEstado("__todos__"); setQuery(""); setLimit(20); }}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${subTab === "actuales" ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Actuales
            <span className="text-[10px] text-muted-foreground/70">{activos.length}</span>
          </button>
          <button
            type="button"
            onClick={() => { setSubTab("historico"); setEstado("__todos__"); setQuery(""); setLimit(20); }}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${subTab === "historico" ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            Histórico
            <span className="text-[10px] text-muted-foreground/70">{historico.length}</span>
          </button>
        </div>

        {estados.length > 1 && (
          <>
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <Select value={estado} onValueChange={(v) => { setEstado(v); setLimit(20); }}>
              <SelectTrigger className="h-8 w-[200px] text-xs">
                <SelectValue placeholder="Todos los estados" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__todos__">Todos ({sourceList.length})</SelectItem>
                {estados.map((e) => (
                  <SelectItem key={e} value={e}>{e}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        )}

        <div className="relative flex-1 min-w-[200px] max-w-[320px]">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => { setQuery(e.target.value); setLimit(20); }}
            placeholder="Buscar alcalde o municipio..."
            className="h-8 pl-8 text-xs"
          />
        </div>
        <span className="text-xs text-muted-foreground">
          {visible.length} de {filtered.length}
          {filtered.length > visible.length && " (orden por aprobación)"}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {visible.map((s, idx) => (
          <AprobacionCard
            key={`${s.actor_nombre}-${s.entidad}-${s.municipio ?? ""}`}
            serie={s}
            color={getColor(s.actor_nombre, idx)}
            vigente={subTab === "actuales"}
            rank={idx + 1}
          />
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="text-sm text-muted-foreground">No se encontraron alcaldes con esos filtros.</p>
      )}

      {filtered.length > visible.length && (
        <div className="flex justify-center pt-2">
          <Button variant="outline" size="sm" onClick={() => setLimit(limit + 20)}>
            Cargar 20 más ({filtered.length - visible.length} restantes)
          </Button>
        </div>
      )}
    </div>
  );
}

function PromediosTab({ series }: { series: ClimaPoliticoSerie[] }) {
  if (series.length === 0) {
    return <p className="text-sm text-muted-foreground">No hay series de promedios disponibles.</p>;
  }
  const sorted = series.slice().sort((a, b) => a.actor_nombre.localeCompare(b.actor_nombre));
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      {sorted.map((s, idx) => (
        <AprobacionCard key={`${s.actor_nombre}-${s.entidad}`} serie={s} color={getColor(s.actor_nombre, idx)} />
      ))}
    </div>
  );
}

export default function ClimaPage() {
  const { data, isLoading, error } = useClimaPolitico("ambas");
  const [view, setView] = useState<"cards" | "compare">("cards");
  const [comparaMetrica, setComparaMetrica] = useState<"aprobacion" | "desaprobacion">("aprobacion");
  const [compareScope, setCompareScope] = useState<"federal_gob" | "with_alcaldes" | "all">("federal_gob");

  const buckets = useMemo<Record<Bucket, ClimaPoliticoSerie[]>>(() => {
    const init: Record<Bucket, ClimaPoliticoSerie[]> = {
      presidenta_actual: [], expresidente: [], gobernador: [], alcalde: [], promedio: [], otro: [],
    };
    if (!data) return init;
    const merged = new Map<string, ClimaPoliticoSerie>();
    for (const s of data) {
      const key = `${s.actor_nombre}|${s.ambito}|${s.entidad ?? ""}`;
      const prev = merged.get(key);
      if (!prev || s.puntos.length > prev.puntos.length) merged.set(key, s);
    }
    for (const s of merged.values()) init[bucketOf(s)].push(s);
    return init;
  }, [data]);

  /** Top 10 alcaldes actuales ordenados por la métrica seleccionada — recalcula cuando cambia comparaMetrica */
  const alcaldesTop10 = useMemo(() => {
    const activosAlcaldes = buckets.alcalde.filter(isActive);
    return activosAlcaldes
      .slice()
      .sort((a, b) => {
        const av = deltaLabel(a.puntos, comparaMetrica)?.current ?? 0;
        const bv = deltaLabel(b.puntos, comparaMetrica)?.current ?? 0;
        return bv - av;
      })
      .slice(0, 10);
  }, [buckets.alcalde, comparaMetrica]);

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-56" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-48" />)}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return <div className="p-6 text-sm text-muted-foreground">No se pudo cargar el clima político.</div>;
  }

  const all = data;
  const federales = [...buckets.presidenta_actual, ...buckets.expresidente];
  const gobernadores = buckets.gobernador;

  return (
    <div className="space-y-5 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight">Clima Político</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Tendencias de aprobación gubernamental — Demoscopía Digital + Oraculus + Mitofsky
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1 rounded-lg border bg-muted/40 p-1">
          <Button
            variant={view === "cards" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 gap-1.5 px-2.5 text-xs"
            onClick={() => setView("cards")}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            Tarjetas
          </Button>
          <Button
            variant={view === "compare" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 gap-1.5 px-2.5 text-xs"
            onClick={() => setView("compare")}
          >
            <LineChartIcon className="h-3.5 w-3.5" />
            Comparar
          </Button>
        </div>
      </div>

      {view === "cards" && (
        <Tabs defaultValue="federal" className="w-full">
          <TabsList className="h-9 w-full justify-start gap-1 bg-muted/40">
            <TabsTrigger value="federal" className="gap-1.5 text-xs">
              <Crown className="h-3.5 w-3.5" />
              Federal
              <span className="ml-1 text-[10px] text-muted-foreground/70">
                {buckets.presidenta_actual.length + buckets.expresidente.length}
              </span>
            </TabsTrigger>
            <TabsTrigger value="gobernadores" className="gap-1.5 text-xs">
              <Users2 className="h-3.5 w-3.5" />
              Gobernadores
              <span className="ml-1 text-[10px] text-muted-foreground/70">{buckets.gobernador.length}</span>
            </TabsTrigger>
            <TabsTrigger value="alcaldes" className="gap-1.5 text-xs">
              <MapPin className="h-3.5 w-3.5" />
              Alcaldes
              <span className="ml-1 text-[10px] text-muted-foreground/70">{buckets.alcalde.length}</span>
            </TabsTrigger>
            <TabsTrigger value="promedios" className="gap-1.5 text-xs">
              <BarChart3 className="h-3.5 w-3.5" />
              Promedios
              <span className="ml-1 text-[10px] text-muted-foreground/70">{buckets.promedio.length}</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="federal" className="mt-4">
            <FederalTab buckets={buckets} />
          </TabsContent>
          <TabsContent value="gobernadores" className="mt-4">
            <GobernadoresTab series={buckets.gobernador} />
          </TabsContent>
          <TabsContent value="alcaldes" className="mt-4">
            <AlcaldesTab series={buckets.alcalde} />
          </TabsContent>
          <TabsContent value="promedios" className="mt-4">
            <PromediosTab series={buckets.promedio} />
          </TabsContent>
        </Tabs>
      )}

      {view === "compare" && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg border bg-muted/40 p-1 w-fit">
              <Button
                variant={comparaMetrica === "aprobacion" ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-3 text-xs"
                onClick={() => setComparaMetrica("aprobacion")}
              >
                Aprobación
              </Button>
              <Button
                variant={comparaMetrica === "desaprobacion" ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-3 text-xs"
                onClick={() => setComparaMetrica("desaprobacion")}
              >
                Desaprobación
              </Button>
            </div>
            <div className="flex items-center gap-1 rounded-lg border bg-muted/40 p-1 w-fit">
              <Button
                variant={compareScope === "federal_gob" ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-3 text-xs"
                onClick={() => setCompareScope("federal_gob")}
              >
                Federal + Gobernadores
                <span className="ml-1 text-[10px] text-muted-foreground/70">
                  {(federales.length + gobernadores.length)}
                </span>
              </Button>
              <Button
                variant={compareScope === "with_alcaldes" ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-3 text-xs"
                onClick={() => setCompareScope("with_alcaldes")}
              >
                + Top 10 alcaldes
                <span className="ml-1 text-[10px] text-muted-foreground/70">
                  {(federales.length + gobernadores.length + alcaldesTop10.length)}
                </span>
              </Button>
              <Button
                variant={compareScope === "all" ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-3 text-xs"
                onClick={() => setCompareScope("all")}
              >
                Todos
                <span className="ml-1 text-[10px] text-muted-foreground/70">{all.length}</span>
              </Button>
            </div>
          </div>
          {(() => {
            let scoped: ClimaPoliticoSerie[] = [];
            if (compareScope === "federal_gob") scoped = [...federales, ...gobernadores];
            else if (compareScope === "with_alcaldes") scoped = [...federales, ...gobernadores, ...alcaldesTop10];
            else scoped = all;
            return (
              <>
                <p className="text-xs text-muted-foreground">
                  {scoped.length} {scoped.length === 1 ? "serie" : "series"} en el chart
                  {compareScope === "all" && scoped.length > 30 && (
                    <span className="ml-2 text-amber-500">· Aviso: muchas líneas pueden amontonarse</span>
                  )}
                </p>
                <ComparativaChart data={scoped} metrica={comparaMetrica} />
                <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                  {scoped.map((serie, idx) => {
                    const stat = deltaLabel(serie.puntos, comparaMetrica);
                    if (!stat) return null;
                    const color = getColor(serie.actor_nombre, idx);
                    const sublabel = serie.actor_tipo === "alcalde" && serie.municipio
                      ? `${serie.municipio}, ${serie.entidad ?? ""}`.replace(/, $/, "")
                      : serie.entidad ?? "México";
                    const vigente = isActive(serie);
                    return (
                      <div key={`${serie.actor_nombre}-${serie.entidad}-${serie.municipio ?? ""}`} className="flex items-center gap-2.5 rounded-lg border bg-card px-3 py-2.5">
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1">
                            <div className="truncate text-[11px] font-medium">{serie.actor_nombre}</div>
                            {serie.ambito !== "federal" && (
                              vigente
                                ? <CheckCircle2 className="h-2.5 w-2.5 shrink-0 text-emerald-500" />
                                : <Clock className="h-2.5 w-2.5 shrink-0 text-muted-foreground/50" />
                            )}
                          </div>
                          <div className="text-[10px] text-muted-foreground truncate">{sublabel}</div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-sm font-bold tabular-nums" style={{ color }}>{stat.current.toFixed(1)}%</div>
                          {stat.delta != null && (
                            <div className={`text-[10px] tabular-nums ${stat.delta >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                              {stat.delta >= 0 ? "+" : ""}{stat.delta.toFixed(1)}pp
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            );
          })()}
        </section>
      )}
    </div>
  );
}
