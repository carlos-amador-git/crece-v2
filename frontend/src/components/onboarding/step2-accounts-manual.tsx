"use client";

import { Facebook, Instagram, Link2, Music2, Twitter, Youtube } from "lucide-react";
import { useMemo } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  useWizardStore,
  parseHandleFromUrl,
  type OnboardingPlatform,
} from "@/lib/api/hooks/use-onboarding";

const PLATFORMS: {
  id: OnboardingPlatform;
  label: string;
  icon: typeof Instagram;
  placeholder: string;
}[] = [
  {
    id: "INSTAGRAM",
    label: "Instagram",
    icon: Instagram,
    placeholder: "https://instagram.com/alejandro.pinha",
  },
  {
    id: "FACEBOOK",
    label: "Facebook",
    icon: Facebook,
    placeholder: "https://facebook.com/AlejandroPinhaMC",
  },
  {
    id: "TWITTER",
    label: "X / Twitter",
    icon: Twitter,
    placeholder: "https://x.com/Alejandro_Pinha",
  },
  {
    id: "TIKTOK",
    label: "TikTok",
    icon: Music2,
    placeholder: "https://tiktok.com/@alejandro.pinha",
  },
  {
    id: "YOUTUBE",
    label: "YouTube",
    icon: Youtube,
    placeholder: "https://youtube.com/@alejandropinha",
  },
];

export function Step2AccountsManual() {
  const { manualAccounts, setManualAccounts } = useWizardStore();

  const byPlatform = useMemo(() => {
    const map: Partial<Record<OnboardingPlatform, string>> = {};
    manualAccounts.forEach((a) => {
      map[a.platform] = a.url;
    });
    return map;
  }, [manualAccounts]);

  const setUrl = (platform: OnboardingPlatform, url: string) => {
    const filtered = manualAccounts.filter((a) => a.platform !== platform);
    if (url.trim()) {
      filtered.push({ platform, url: url.trim() });
    }
    setManualAccounts(filtered);
  };

  return (
    <div className="space-y-6" data-testid="step-2-accounts">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 2 de 9
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          Agrega los perfiles oficiales
        </h2>
        <p className="text-sm text-muted-foreground">
          Pega las URLs públicas por plataforma. Detectamos el handle y lo
          validamos en el siguiente paso.
        </p>
      </header>

      <div className="space-y-3">
        {PLATFORMS.map(({ id, label, icon: Icon, placeholder }) => {
          const url = byPlatform[id] ?? "";
          const handle = parseHandleFromUrl(id, url);
          return (
            <Card key={id}>
              <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
                <div className="flex min-w-[140px] items-center gap-2">
                  <Icon className="h-5 w-5 text-muted-foreground" />
                  <Label htmlFor={`account-${id}`} className="font-medium">
                    {label}
                  </Label>
                </div>
                <div className="flex-1 space-y-1">
                  <div className="relative">
                    <Link2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id={`account-${id}`}
                      data-testid={`input-account-${id}`}
                      type="url"
                      placeholder={placeholder}
                      value={url}
                      onChange={(e) => setUrl(id, e.target.value)}
                      className="pl-9"
                      inputMode="url"
                      autoComplete="off"
                    />
                  </div>
                  {handle && (
                    <Badge
                      variant="outline"
                      className="text-[10px]"
                      data-testid={`handle-preview-${id}`}
                    >
                      Handle detectado: <span className="ml-1 font-mono">@{handle}</span>
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
