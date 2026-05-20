"use client";

/**
 * F4 Content Hub · /dashboard/hub · 2026-05-19
 *
 * Posts Workspace unificado. Reemplaza progresivamente las 4 rutas viejas:
 *  - /dashboard/social (Monitoreo)        → ?tab=feed
 *  - /dashboard/social/comentarios        → ?tab=comentarios
 *  - /dashboard/content/top (Top Posts)   → ?tab=top
 *  - /dashboard/aceptacion/fans           → ?tab=fans
 *
 * Implementa decisiones aprobadas CEO:
 *  - D13.2: ruta /dashboard/hub (ajuste · /dashboard/contenido ya tomado por
 *    Content Factory existente)
 *  - D13.3: endpoint unificado /api/v1/posts/unified?view=
 *  - D13.4: tabs internos con ?tab= deep-linking
 *  - D13.5: single ítem sidebar (sidebar update aparte)
 *
 * Per Gemini cross-audit non-blocking #2: Suspense boundary específico
 * envuelve la grid central para evitar re-renders bloqueantes al cambiar tab.
 */

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ErrorBoundary } from "@/components/error-boundary";
import {
  UnifiedPostCard,
  UnifiedPostCardSkeleton,
} from "@/components/posts/unified-post-card";
import {
  useUnifiedPosts,
  unifiedItemToPostUnified,
  type UnifiedView,
} from "@/lib/api/hooks/use-unified-posts";
import { MessageSquare, Newspaper, Trophy, Users, X } from "lucide-react";

const PLATFORM_OPTIONS = [
  { value: "all", label: "Todas las plataformas" },
  { value: "FACEBOOK", label: "Facebook" },
  { value: "INSTAGRAM", label: "Instagram" },
  { value: "TWITTER", label: "X (Twitter)" },
  { value: "TIKTOK", label: "TikTok" },
  { value: "YOUTUBE", label: "YouTube" },
] as const;

const TAB_CONFIG: Array<{
  value: UnifiedView;
  label: string;
  icon: typeof Newspaper;
  description: string;
}> = [
  {
    value: "feed",
    label: "Feed",
    icon: Newspaper,
    description: "Publicaciones recientes del dirigente",
  },
  {
    value: "comentarios",
    label: "Comentarios",
    icon: MessageSquare,
    description: "Posts con comments + polaridad NLP",
  },
  {
    value: "top",
    label: "Top",
    icon: Trophy,
    description: "Ranking por engagement",
  },
  {
    value: "fans",
    label: "Fans",
    icon: Users,
    description: "Posts con reactors individuales capturados",
  },
];

interface HubFilters {
  platform?: string;
  date_from?: string;
  date_to?: string;
}

function ContenidoGrid({
  dirigenteId,
  view,
  filters,
}: {
  dirigenteId: number;
  view: UnifiedView;
  filters: HubFilters;
}) {
  const { data, isLoading, isError } = useUnifiedPosts({
    dirigente_id: dirigenteId,
    view,
    platform: filters.platform,
    date_from: filters.date_from,
    date_to: filters.date_to,
    per_page: 20,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <UnifiedPostCardSkeleton key={i} variant="feed" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-rose-600">
          No se pudo cargar los posts. Intenta de nuevo.
        </CardContent>
      </Card>
    );
  }

  if (data.items.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <p className="text-sm text-muted-foreground">
            Sin posts en esta vista para el período seleccionado.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Mostrando {data.items.length} de {data.total} posts
      </p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.items.map((item, idx) => (
          <UnifiedPostCard
            key={item.id}
            post={unifiedItemToPostUnified(item)}
            variant={view === "top" ? "ranking" : "feed"}
            rank={view === "top" ? idx + 1 : undefined}
          />
        ))}
      </div>
    </div>
  );
}

function HubInner() {
  const { user } = useAuth();
  const userWithDirigente = user as { dirigente_id?: number } | null;
  const dirigenteId = userWithDirigente?.dirigente_id ?? null;

  const searchParams = useSearchParams();
  const router = useRouter();
  const tabParam = searchParams.get("tab") as UnifiedView | null;
  const [internalTab, setInternalTab] = useState<UnifiedView>(
    tabParam && ["feed", "comentarios", "top", "fans"].includes(tabParam)
      ? tabParam
      : "feed"
  );

  // B3 Filtros · platform + date range
  const [platform, setPlatform] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const filters: HubFilters = {
    platform: platform === "all" ? undefined : platform,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };
  const filtersActive =
    platform !== "all" || Boolean(dateFrom) || Boolean(dateTo);
  const clearFilters = () => {
    setPlatform("all");
    setDateFrom("");
    setDateTo("");
  };

  const handleTabChange = (next: string) => {
    const v = next as UnifiedView;
    setInternalTab(v);
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", v);
    router.replace(`/dashboard/hub?${params.toString()}`, { scroll: false });
  };

  if (!dirigenteId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Contenido</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Selecciona un dirigente desde la lista para ver su contenido.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-heading text-2xl font-bold">Contenido</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Workspace unificado · feed, comentarios, top y fans en una sola vista.
        </p>
      </div>

      {/* B3 Filtros · platform + date range */}
      <Card>
        <CardContent className="p-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="hub-platform" className="text-xs">
                Plataforma
              </Label>
              <Select value={platform} onValueChange={setPlatform}>
                <SelectTrigger id="hub-platform" className="h-9 w-full md:w-48 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PLATFORM_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="hub-date-from" className="text-xs">
                Desde
              </Label>
              <Input
                id="hub-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="h-9 w-full md:w-40 text-sm"
                max={dateTo || undefined}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="hub-date-to" className="text-xs">
                Hasta
              </Label>
              <Input
                id="hub-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="h-9 w-full md:w-40 text-sm"
                min={dateFrom || undefined}
              />
            </div>
            {filtersActive && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="gap-1.5 text-xs"
              >
                <X className="h-3.5 w-3.5" />
                Limpiar
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Tabs value={internalTab} onValueChange={handleTabChange}>
        <TabsList className="grid w-full grid-cols-4">
          {TAB_CONFIG.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value} className="gap-2">
              <tab.icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        {TAB_CONFIG.map((tab) => (
          <TabsContent key={tab.value} value={tab.value} className="space-y-4">
            <p className="text-xs text-muted-foreground">{tab.description}</p>
            <ErrorBoundary
              fallbackMessage={`No pudimos cargar la vista "${tab.label}". El resto del workspace sigue disponible.`}
            >
              <Suspense
                fallback={
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <UnifiedPostCardSkeleton key={i} variant="feed" />
                    ))}
                  </div>
                }
              >
                <ContenidoGrid
                  dirigenteId={dirigenteId}
                  view={tab.value}
                  filters={filters}
                />
              </Suspense>
            </ErrorBoundary>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

export default function HubPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[60vh] w-full" />}>
      <HubInner />
    </Suspense>
  );
}
