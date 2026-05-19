"use client";

import { useState } from "react";
import { useSocialComments } from "@/lib/api/hooks/use-social-comments";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { MessageSquare, ThumbsUp, User, ChevronLeft, ChevronRight } from "lucide-react";
import { ReviewStatusBadge } from "@/components/evaluacion/ReviewStatusBadge";

const TONO_COLORS: Record<string, string> = {
  ataque:       "bg-rose-500/15 text-rose-400 border-rose-500/30",
  critico:      "bg-orange-500/15 text-orange-400 border-orange-500/30",
  personal:     "bg-slate-500/15 text-slate-400 border-slate-500/30",
  solidario:    "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  celebratorio: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  propositivo:  "bg-blue-500/15 text-blue-400 border-blue-500/30",
  informativo:  "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
};

const POLARIDAD_LABEL: Record<number, { label: string; cls: string }> = {
  1:  { label: "Positivo", cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  0:  { label: "Neutro",   cls: "bg-slate-500/15 text-slate-400 border-slate-500/30" },
  [-1 as number]: { label: "Negativo", cls: "bg-rose-500/15 text-rose-400 border-rose-500/30" },
};

const PLATFORM_COLORS: Record<string, string> = {
  TWITTER: "text-sky-400", INSTAGRAM: "text-pink-400",
  FACEBOOK: "text-blue-400", TIKTOK: "text-foreground",
};

const TONOS = ["ataque", "critico", "personal", "solidario", "celebratorio", "propositivo", "informativo"];
const PLATFORMS = ["TWITTER", "INSTAGRAM", "FACEBOOK", "TIKTOK"];

export default function ComentariosPage() {
  const [page, setPage] = useState(1);
  const [tono, setTono] = useState<string | undefined>();
  const [polaridad, setPolaridad] = useState<number | undefined>();
  const [platform, setPlatform] = useState<string | undefined>();
  const [onlyHumanValidated, setOnlyHumanValidated] = useState(false);

  const { data, isLoading } = useSocialComments({
    page, page_size: 30, tono, polaridad, platform,
  });

  const allItems = data?.items ?? [];
  const comments = onlyHumanValidated
    ? allItems.filter((c) => c.review_status === "confirmed" || c.review_status === "edited")
    : allItems;
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 0;

  const resetFilters = () => {
    setTono(undefined);
    setPolaridad(undefined);
    setPlatform(undefined);
    setOnlyHumanValidated(false);
    setPage(1);
  };

  return (
    <div className="space-y-5 p-6">
      {/* Header */}
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight">Comentarios</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Reacciones del público en publicaciones de tus dirigentes
          {total > 0 && <span className="ml-2 tabular-nums text-muted-foreground/60">{total.toLocaleString()} total</span>}
        </p>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-2">
        <Select value={tono ?? "all"} onValueChange={(v) => { setTono(v === "all" ? undefined : v); setPage(1); }}>
          <SelectTrigger className="h-8 w-36 text-xs">
            <SelectValue placeholder="Tono" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los tonos</SelectItem>
            {TONOS.map((t) => <SelectItem key={t} value={t} className="capitalize">{t}</SelectItem>)}
          </SelectContent>
        </Select>

        <Select value={polaridad !== undefined ? String(polaridad) : "all"} onValueChange={(v) => { setPolaridad(v === "all" ? undefined : Number(v)); setPage(1); }}>
          <SelectTrigger className="h-8 w-36 text-xs">
            <SelectValue placeholder="Polaridad" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toda polaridad</SelectItem>
            <SelectItem value="1">Positivo</SelectItem>
            <SelectItem value="0">Neutro</SelectItem>
            <SelectItem value="-1">Negativo</SelectItem>
          </SelectContent>
        </Select>

        <Select value={platform ?? "all"} onValueChange={(v) => { setPlatform(v === "all" ? undefined : v); setPage(1); }}>
          <SelectTrigger className="h-8 w-36 text-xs">
            <SelectValue placeholder="Plataforma" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {PLATFORMS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
          </SelectContent>
        </Select>

        <Button
          variant={onlyHumanValidated ? "default" : "outline"}
          size="sm"
          className="h-8 text-xs"
          onClick={() => { setOnlyHumanValidated((v) => !v); setPage(1); }}
          aria-pressed={onlyHumanValidated}
        >
          Solo validados por humano
        </Button>

        {(tono || polaridad !== undefined || platform || onlyHumanValidated) && (
          <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground" onClick={resetFilters}>
            Limpiar
          </Button>
        )}
      </div>

      {/* Lista */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-lg" />)}
        </div>
      ) : comments.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <MessageSquare className="mb-3 h-10 w-10 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">Sin comentarios con los filtros seleccionados</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {comments.map((c) => {
            const pol = c.nlp_polaridad !== null ? POLARIDAD_LABEL[c.nlp_polaridad as -1 | 0 | 1] : null;
            const tonoClass = c.nlp_tono ? (TONO_COLORS[c.nlp_tono] ?? "bg-muted/30 text-muted-foreground") : null;
            const platColor = c.platform ? (PLATFORM_COLORS[c.platform] ?? "text-muted-foreground") : "text-muted-foreground";

            return (
              <div key={c.id} className="flex gap-3 rounded-lg border bg-card px-4 py-3 transition-colors hover:bg-muted/30">
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
                  <User className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {c.dirigente_nombre && (
                      <span className="text-xs font-medium text-foreground/70">→ {c.dirigente_nombre}</span>
                    )}
                    {c.platform && (
                      <span className={`text-[11px] font-semibold ${platColor}`}>{c.platform}</span>
                    )}
                    {c.nlp_tono && tonoClass && (
                      <Badge variant="outline" className={`px-1.5 py-0 text-[10px] capitalize ${tonoClass}`}>{c.nlp_tono}</Badge>
                    )}
                    {pol && (
                      <Badge variant="outline" className={`px-1.5 py-0 text-[10px] ${pol.cls}`}>{pol.label}</Badge>
                    )}
                    <ReviewStatusBadge
                      status={c.review_status}
                      actorName={c.last_reviewed_by_name}
                    />
                    {c.es_follower && (
                      <Badge variant="outline" className="px-1.5 py-0 text-[10px] text-muted-foreground">Seguidor</Badge>
                    )}
                    <span className="ml-auto text-[10px] text-muted-foreground/50">
                      {c.published_at ? new Date(c.published_at).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "2-digit" }) : ""}
                    </span>
                  </div>
                  {c.content && (
                    <p className="line-clamp-2 text-sm text-foreground/80">{c.content}</p>
                  )}
                  {(c.likes ?? 0) > 0 && (
                    <div className="flex items-center gap-1 text-[11px] text-muted-foreground/60">
                      <ThumbsUp className="h-3 w-3" />
                      {c.likes}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Paginación */}
      {pages > 1 && (
        <div className="flex items-center justify-between pt-1">
          <p className="text-xs text-muted-foreground">
            Página {page} de {pages}
          </p>
          <div className="flex gap-1">
            <Button variant="outline" size="sm" className="h-7 w-7 p-0" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft className="h-3.5 w-3.5" />
            </Button>
            <Button variant="outline" size="sm" className="h-7 w-7 p-0" disabled={page >= pages} onClick={() => setPage(p => p + 1)}>
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
