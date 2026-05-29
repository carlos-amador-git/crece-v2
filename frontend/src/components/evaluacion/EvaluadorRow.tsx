"use client";

/**
 * Componente compartido entre CommentEvaluator y PostEvaluator.
 * Mantiene la lógica de estado, dropdowns y botones — solo cambia el slot
 * de cabecera (texto + meta) que recibe como children.
 */

import { useState, type ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Check,
  Pencil,
  Loader2,
  Bot,
  CircleDashed,
  AlertTriangle,
} from "lucide-react";
import {
  TONO_V2_OPTIONS,
  TARGET_V2_OPTIONS,
  type HitlEditPayload,
  type ReviewStatus,
  type TargetV2,
  type TonoV2,
} from "@/lib/api/hitl";
import { cn } from "@/lib/utils";

export interface EvaluadorRowProps {
  reviewStatus: ReviewStatus | null;
  systemTono: string | null;
  systemTarget: string | null;
  systemOffTopic: boolean | null;
  saving?: boolean;
  error?: string | null;
  onSave: (payload: HitlEditPayload) => Promise<void> | void;
  onConfirm: () => Promise<void> | void;
  children: ReactNode;
}

export function EvaluadorRow({
  reviewStatus,
  systemTono,
  systemTarget,
  systemOffTopic,
  saving = false,
  error,
  onSave,
  onConfirm,
  children,
}: EvaluadorRowProps) {
  // Initialize current values from the system proposal (or null if absent)
  const [tono, setTono] = useState<TonoV2 | null>(
    (systemTono as TonoV2 | null) ?? null
  );
  const [target, setTarget] = useState<TargetV2 | null>(
    (systemTarget as TargetV2 | null) ?? null
  );
  const [offTopic, setOffTopic] = useState<boolean>(systemOffTopic ?? false);
  const [reason, setReason] = useState<string>("");

  const status = reviewStatus ?? "unreviewed";
  const isDirty =
    tono !== (systemTono as TonoV2 | null) ||
    target !== (systemTarget as TargetV2 | null) ||
    offTopic !== (systemOffTopic ?? false);

  const cardCls = cn(
    "transition-shadow",
    status === "confirmed" && "border-emerald-500/40 ring-1 ring-emerald-500/15",
    status === "edited" && "border-blue-500/40 ring-1 ring-blue-500/15",
    status === "unreviewed" && "border-border"
  );

  const handleSave = async () => {
    const payload: HitlEditPayload = {};
    if (tono !== (systemTono as TonoV2 | null)) payload.tono = tono;
    if (target !== (systemTarget as TargetV2 | null)) payload.target = target;
    if (offTopic !== (systemOffTopic ?? false)) payload.off_topic = offTopic;
    if (reason.trim()) payload.reason = reason.trim();
    await onSave(payload);
  };

  return (
    <Card className={cardCls}>
      <CardContent className="space-y-4 p-4">
        {/* Header slot: provided by parent (post or comment specific meta) */}
        {children}

        {/* Status row */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <StatusBadge status={status} />
          <Badge
            variant="outline"
            className="border-muted-foreground/30 text-muted-foreground"
          >
            <Bot className="mr-1 h-3 w-3" />
            Sistema: {systemTono ?? "—"} / {systemTarget ?? "—"}
            {systemOffTopic ? " · off-topic" : ""}
          </Badge>
        </div>

        {/* Editor controls */}
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">
              Tono
            </Label>
            <Select
              value={tono ?? ""}
              onValueChange={(v) => setTono(v as TonoV2)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecciona tono" />
              </SelectTrigger>
              <SelectContent>
                {TONO_V2_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">
              Target
            </Label>
            <Select
              value={target ?? ""}
              onValueChange={(v) => setTarget(v as TargetV2)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecciona target" />
              </SelectTrigger>
              <SelectContent>
                {TARGET_V2_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Checkbox
            id={`off-topic-${Math.random().toString(36).slice(2, 8)}`}
            checked={offTopic}
            onCheckedChange={(c) => setOffTopic(c === true)}
          />
          <Label className="text-sm font-normal cursor-pointer">
            Off-topic / ruido (no aplica al análisis político)
          </Label>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">
            Razón (opcional)
          </Label>
          <Textarea
            placeholder="Por qué cambias la clasificación — queda en audit log"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
          />
        </div>

        {error && (
          <div
            role="alert"
            className="flex items-center gap-2 rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-600 dark:text-rose-400"
          >
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={onConfirm}
            disabled={saving}
            className="gap-1.5"
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Check className="h-3.5 w-3.5" />
            )}
            Confirmar como está
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving || !isDirty}
            className="gap-1.5"
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Pencil className="h-3.5 w-3.5" />
            )}
            Guardar cambio
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: ReviewStatus }) {
  if (status === "confirmed") {
    return (
      <Badge
        variant="outline"
        className="border-emerald-500/40 text-emerald-600 dark:text-emerald-400"
      >
        <Check className="mr-1 h-3 w-3" />
        Confirmado
      </Badge>
    );
  }
  if (status === "edited") {
    return (
      <Badge
        variant="outline"
        className="border-blue-500/40 text-blue-600 dark:text-blue-400"
      >
        <Pencil className="mr-1 h-3 w-3" />
        Editado
      </Badge>
    );
  }
  return (
    <Badge
      variant="outline"
      className="border-muted-foreground/30 text-muted-foreground"
    >
      <CircleDashed className="mr-1 h-3 w-3" />
      Pendiente
    </Badge>
  );
}
