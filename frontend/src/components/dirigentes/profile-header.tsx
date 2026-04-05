import type { DirigenteDetail } from "@/lib/api/types";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { IpdScoreBadge } from "./ipd-score-badge";
import { PlatformIcon } from "@/components/social/platform-icon";
import { MapPin, Building2, Users } from "lucide-react";

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

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
        <Avatar className="h-20 w-20 border-2 border-border">
          <AvatarImage src={dirigente.avatar_url} alt={fullName} />
          <AvatarFallback className="text-xl font-heading">
            {initials}
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="font-heading text-2xl font-bold">{fullName}</h1>
              <p className="text-muted-foreground">{dirigente.cargo}</p>
            </div>
            <IpdScoreBadge score={dirigente.ipd_score ?? 0} size="lg" />
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
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
              {dirigente.secciones.length} secciones
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {dirigente.social_accounts.map((account) => (
              <a
                key={account.platform}
                href={account.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 rounded-md border bg-background px-2.5 py-1 text-xs transition-colors hover:bg-muted"
                aria-label={`${account.platform}: @${account.username}`}
              >
                <PlatformIcon platform={account.platform} size={14} />
                <span className="font-medium">@{account.username}</span>
                {account.verified && (
                  <Badge variant="secondary" className="ml-1 px-1 py-0 text-[10px]">
                    Verificado
                  </Badge>
                )}
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
