"use client";

/**
 * /dashboard/seguidores — lista granular de seguidores del dirigente.
 *
 * S4 PLAN-2026-05-13. Empty states honestos (D-ANTI-MOCK-1):
 * - Sin OAuth conectado → CTA "Conectar plataforma"
 * - OAuth conectado pero BD vacía → "Esperando primer scrape"
 * - Skeleton mientras carga
 *
 * CERO hardcoded numbers en este file. `frontend/scripts/check-no-mocks.sh`
 * debe pasar verde.
 */
import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CheckCircle2,
  MessageCircle,
  PlugZap,
  Users,
} from "lucide-react";

import { useAuth } from "@/lib/auth";
import {
  useFollowers,
  useOAuthStatus,
  type FollowerPlatform,
} from "@/lib/api/hooks/use-followers";

const PLATFORM_LABEL: Record<FollowerPlatform, string> = {
  twitter: "Twitter / X",
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  youtube: "YouTube",
  bluesky: "Bluesky",
  threads: "Threads",
  telegram: "Telegram",
};

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  const seconds = (Date.now() - date.getTime()) / 1000;
  if (seconds < 60) return "hace segundos";
  if (seconds < 3600) return `hace ${Math.floor(seconds / 60)} min`;
  if (seconds < 86400) return `hace ${Math.floor(seconds / 3600)} h`;
  const days = Math.floor(seconds / 86400);
  if (days < 30) return `hace ${days} días`;
  return date.toLocaleDateString("es-MX");
}

export default function SeguidoresPage() {
  const { user } = useAuth();
  const dirigenteId = user?.dirigente_id ?? null;

  const [platform, setPlatform] = useState<FollowerPlatform | "all">("all");
  const [onlyWithComments, setOnlyWithComments] = useState(false);
  const [onlyVerified, setOnlyVerified] = useState(false);

  const filters = useMemo(
    () => ({
      platform: platform === "all" ? undefined : platform,
      onlyWithComments,
      onlyVerified,
    }),
    [platform, onlyWithComments, onlyVerified],
  );

  const oauth = useOAuthStatus(dirigenteId);
  const followers = useFollowers(dirigenteId, filters);

  const oauthConnected = useMemo(() => {
    if (!oauth.data) return false;
    return Object.values(oauth.data.platforms).some(
      (p) => p.connected && p.is_stub === false,
    );
  }, [oauth.data]);

  if (!dirigenteId) {
    return (
      <div className="container py-10">
        <Card>
          <CardHeader>
            <CardTitle>Mis seguidores</CardTitle>
            <CardDescription>
              Tu usuario no tiene un dirigente asignado. Pide a un administrador
              que vincule tu cuenta.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container space-y-6 py-8">
      <header>
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold tracking-tight">
            Mis seguidores
          </h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Lista granular por plataforma. Sólo aparecen los seguidores que tu
          plataforma expone públicamente o vía OAuth conectado.
        </p>
      </header>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4">
          <div className="min-w-[180px]">
            <Select
              value={platform}
              onValueChange={(v) => setPlatform(v as FollowerPlatform | "all")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Plataforma" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las plataformas</SelectItem>
                {(Object.keys(PLATFORM_LABEL) as FollowerPlatform[]).map((p) => (
                  <SelectItem key={p} value={p}>
                    {PLATFORM_LABEL[p]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={onlyWithComments}
              onCheckedChange={(v) => setOnlyWithComments(v === true)}
            />
            Solo con comentarios
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={onlyVerified}
              onCheckedChange={(v) => setOnlyVerified(v === true)}
            />
            Solo verificados
          </label>
        </CardContent>
      </Card>

      {!oauthConnected && oauth.isSuccess && (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <PlugZap className="h-5 w-5 text-amber-500" />
              Conecta una plataforma para ver tus seguidores
            </CardTitle>
            <CardDescription>
              Esta vista necesita un permiso explícito del dirigente sobre su
              cuenta. Hoy puedes conectar tu canal de YouTube; Instagram y
              Facebook llegan cuando completemos el proceso de Meta Business.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/dashboard/onboarding">Configurar integraciones</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {followers.isSuccess
              ? `${followers.data.total} seguidores`
              : "Seguidores"}
          </CardTitle>
          <CardDescription>
            Última actividad ordenada por más reciente.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {followers.isLoading || !followers.data ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : followers.isError ? (
            <p className="text-sm text-destructive">
              No pudimos cargar tus seguidores. Vuelve a intentar en un minuto.
            </p>
          ) : followers.data.total === 0 ? (
            <div className="rounded-md border border-dashed py-10 text-center text-sm text-muted-foreground">
              {oauthConnected
                ? "Aún no recibimos seguidores desde la plataforma conectada. El primer scrape puede tardar hasta una hora."
                : "Sin seguidores registrados todavía. Conecta una plataforma para empezar."}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Seguidor</TableHead>
                  <TableHead>Plataforma</TableHead>
                  <TableHead className="text-right">Comentarios</TableHead>
                  <TableHead>Última actividad</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {followers.data.items.map((f) => {
                  const initials = (f.follower_display_name ?? f.follower_handle ?? "?")
                    .split(" ")
                    .map((s) => s[0] ?? "")
                    .join("")
                    .slice(0, 2)
                    .toUpperCase();
                  return (
                    <TableRow key={f.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Avatar className="h-8 w-8">
                            {f.follower_avatar_url ? (
                              <AvatarImage src={f.follower_avatar_url} />
                            ) : null}
                            <AvatarFallback>{initials}</AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="flex items-center gap-1.5 text-sm font-medium">
                              {f.follower_display_name ?? f.follower_handle ?? "Sin nombre"}
                              {f.follower_is_verified && (
                                <CheckCircle2 className="h-3.5 w-3.5 text-sky-500" />
                              )}
                            </div>
                            {f.follower_handle && (
                              <div className="text-xs text-muted-foreground">
                                {f.follower_handle}
                              </div>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {PLATFORM_LABEL[f.platform]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {(f.engagement_summary.by_type?.comment ?? 0) > 0 ? (
                          <span className="inline-flex items-center gap-1 text-sm">
                            <MessageCircle className="h-3.5 w-3.5 text-muted-foreground" />
                            {f.engagement_summary.by_type.comment}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {relativeTime(f.last_active_at ?? f.last_seen_at)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
