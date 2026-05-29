import type { DirigenteDetail } from "@/lib/api/types";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { IpdScoreBadge } from "./ipd-score-badge";
import { PlatformIcon } from "@/components/social/platform-icon";
import { MapPin, Building2, Users } from "lucide-react";
import { formatNumber } from "@/lib/utils";

interface ProfileHeaderProps {
  dirigente: DirigenteDetail;
}

export function ProfileHeader({ dirigente }: ProfileHeaderProps) {
  const initials = dirigente.full_name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const fullName = dirigente.full_name;
  const accounts = ((dirigente.social_accounts ?? (dirigente as any).social_profiles) ?? []) as Array<{
    platform: string;
    username: string;
    url: string;
    followers?: number;
    followers_count?: number;
    verified?: boolean;
  }>;

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
        <Avatar className="h-20 w-20 shrink-0 border-2 border-border">
          <AvatarImage src={dirigente.avatar_url} alt={fullName} />
          <AvatarFallback className="text-xl font-heading">
            {initials}
          </AvatarFallback>
        </Avatar>

        <div className="flex flex-1 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          {/* Izquierda: identidad · max 60% en desktop */}
          <div className="min-w-0 space-y-3 sm:max-w-[60%]">
            <div>
              <h1 className="font-heading text-2xl font-bold leading-tight">{fullName}</h1>
              <p className="text-muted-foreground">{dirigente.cargo}</p>
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Building2 className="h-4 w-4" />
                {dirigente.partido}
              </span>
              <span className="flex items-center gap-1.5">
                <MapPin className="h-4 w-4" />
                {dirigente.estado}
                {dirigente.municipio && `, ${dirigente.municipio}`}
              </span>
              <span className="flex items-center gap-1.5">
                <Users className="h-4 w-4" />
                {(dirigente.secciones ?? []).length} secciones
              </span>
            </div>

            {(() => {
              // Filtrar handles vacíos: @ pelón da sensación de producto incompleto
              // (Gemini A2.2). Cuenta sin username válido se omite del chip.
              const validAccounts = accounts.filter(
                (a) => a.username && a.username !== "—" && a.username.trim() !== ""
              );
              if (validAccounts.length === 0) return null;
              return (
                <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/40 p-2">
                  {validAccounts.map((account) => {
                    const followers = account.followers ?? account.followers_count ?? 0;
                    const isEmpty = followers === 0;
                    const tooltip = isEmpty
                      ? `@${account.username} · sin seguidores registrados`
                      : `@${account.username} · ${formatNumber(followers)} seguidores`;
                    return (
                      <a
                        key={account.platform}
                        href={account.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={[
                          "group flex items-center gap-1.5 rounded-md border bg-background px-2.5 py-1 text-xs transition-all",
                          "hover:bg-card hover:shadow-sm",
                          isEmpty ? "opacity-50" : "",
                        ].join(" ")}
                        aria-label={tooltip}
                        title={tooltip}
                      >
                        <PlatformIcon platform={account.platform as any} size={14} />
                        <span className="font-medium">@{account.username}</span>
                        {!isEmpty && (
                          <span className="hidden text-[10px] tabular-nums text-muted-foreground group-hover:inline">
                            · {formatNumber(followers)}
                          </span>
                        )}
                        {account.verified && (
                          <Badge variant="secondary" className="ml-1 px-1 py-0 text-[10px]">
                            ✓
                          </Badge>
                        )}
                      </a>
                    );
                  })}
                </div>
              );
            })()}
          </div>

          {/* Derecha: IPD badge con etiqueta de escala (Gemini A1.1) */}
          <div className="flex shrink-0 flex-col items-center gap-1 sm:items-end">
            <IpdScoreBadge score={dirigente.ipd_score ?? 0} size="lg" />
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              IPD · 0–10
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
