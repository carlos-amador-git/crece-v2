"use client";

import { Briefcase, Crown, Megaphone, UserCircle2 } from "lucide-react";

import { Card } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useWizardStore, type PerfilTipo } from "@/lib/api/hooks/use-onboarding";

interface Option {
  id: PerfilTipo;
  title: string;
  description: string;
  icon: typeof Crown;
}

const OPTIONS: Option[] = [
  {
    id: "politico_activo",
    title: "Político activo",
    description: "Dirigente en funciones públicas o con cargo vigente",
    icon: Crown,
  },
  {
    id: "funcionario",
    title: "Funcionario",
    description: "Servidor público en un puesto administrativo",
    icon: Briefcase,
  },
  {
    id: "precampana",
    title: "Precampaña",
    description: "Aspirante en búsqueda de candidatura o posicionamiento",
    icon: Megaphone,
  },
  {
    id: "empresario",
    title: "Empresario",
    description: "Líder con marca personal y relevancia pública",
    icon: UserCircle2,
  },
];

export function Step1Perfil() {
  const { perfil, setPerfil } = useWizardStore();

  return (
    <div className="space-y-6" data-testid="step-1-perfil">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">
          Paso 1 de 9
        </p>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          ¿Cuál describe mejor a este dirigente?
        </h2>
        <p className="text-sm text-muted-foreground">
          Define el tono y las recomendaciones que generará la IA. Puedes cambiarlo
          más adelante en configuración.
        </p>
      </header>

      <RadioGroup
        value={perfil ?? ""}
        onValueChange={(v) => setPerfil(v as PerfilTipo)}
        className="grid grid-cols-1 gap-3 sm:grid-cols-2"
      >
        {OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const active = perfil === opt.id;
          return (
            <Card
              key={opt.id}
              className={cn(
                "relative cursor-pointer p-5 transition-all duration-150",
                "hover:border-accent/40 hover:shadow-md",
                active
                  ? "border-accent bg-accent/5 shadow-md"
                  : "border-border",
              )}
              onClick={() => setPerfil(opt.id)}
            >
              <Label
                htmlFor={`perfil-${opt.id}`}
                className="flex cursor-pointer items-start gap-4"
              >
                <RadioGroupItem
                  value={opt.id}
                  id={`perfil-${opt.id}`}
                  data-testid={`radio-perfil-${opt.id}`}
                  className="mt-1"
                />
                <Icon
                  className={cn(
                    "h-8 w-8 shrink-0 transition-colors",
                    active ? "text-accent" : "text-muted-foreground",
                  )}
                />
                <div className="flex-1 space-y-1">
                  <p className="font-heading text-base font-semibold tracking-tight">
                    {opt.title}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {opt.description}
                  </p>
                </div>
              </Label>
            </Card>
          );
        })}
      </RadioGroup>
    </div>
  );
}
