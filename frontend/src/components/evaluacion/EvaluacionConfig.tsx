"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  RadioGroup,
  RadioGroupItem,
} from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import type {
  SamplePlatform,
  SampleScope,
} from "@/lib/api/hitl";

export interface EvaluacionConfigState {
  days: number;
  platform: SamplePlatform;
  scope: SampleScope;
  onlyPending: boolean;
}

interface Props {
  value: EvaluacionConfigState;
  onChange: (next: EvaluacionConfigState) => void;
}

const DAYS_OPTIONS = [7, 14, 30, 90] as const;

const PLATFORM_OPTIONS: { value: SamplePlatform; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "x", label: "Twitter / X" },
  { value: "ig", label: "Instagram" },
  { value: "fb", label: "Facebook" },
  { value: "tt", label: "TikTok" },
  { value: "yt", label: "YouTube" },
];

export function EvaluacionConfig({ value, onChange }: Props) {
  return (
    <Card>
      <CardContent className="grid gap-5 p-5 md:grid-cols-3">
        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">
            Rango temporal
          </Label>
          <Select
            value={String(value.days)}
            onValueChange={(v) =>
              onChange({ ...value, days: Number(v) })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DAYS_OPTIONS.map((d) => (
                <SelectItem key={d} value={String(d)}>
                  Últimos {d} días
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">
            Plataforma
          </Label>
          <Select
            value={value.platform}
            onValueChange={(v) =>
              onChange({ ...value, platform: v as SamplePlatform })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PLATFORM_OPTIONS.map((p) => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">
            Modo de muestreo
          </Label>
          <RadioGroup
            value={value.scope}
            onValueChange={(v) =>
              onChange({ ...value, scope: v as SampleScope })
            }
            className="flex items-center gap-4 pt-1"
          >
            <div className="flex items-center gap-2">
              <RadioGroupItem value="cronologico" id="scope-crono" />
              <Label
                htmlFor="scope-crono"
                className="text-sm font-normal cursor-pointer"
              >
                Cronológico
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="estratificado" id="scope-estrat" />
              <Label
                htmlFor="scope-estrat"
                className="text-sm font-normal cursor-pointer"
              >
                Estratificado
              </Label>
            </div>
          </RadioGroup>
        </div>

        <div className="md:col-span-3 flex items-center gap-2 pt-1">
          <Checkbox
            id="only-pending"
            checked={value.onlyPending}
            onCheckedChange={(checked) =>
              onChange({ ...value, onlyPending: checked === true })
            }
          />
          <Label
            htmlFor="only-pending"
            className="text-sm font-normal cursor-pointer"
          >
            Solo pendientes (oculta confirmados y editados)
          </Label>
        </div>
      </CardContent>
    </Card>
  );
}
