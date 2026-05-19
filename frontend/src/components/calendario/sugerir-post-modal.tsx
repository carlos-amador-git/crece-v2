/**
 * SugerirPostModal — preview + editor + copy del draft generado por LLM.
 * D-CALENDARIO-1 (2026-05-12).
 */
"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Check, Copy, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

import {
  type Efemeride,
  type SugerirPostRequest,
  useSugerirPost,
} from "@/lib/api/hooks/use-calendario";

interface Props {
  efemeride: Efemeride;
  dirigenteId: number;
  onClose: () => void;
}

const PLATAFORMAS: { value: SugerirPostRequest["plataforma"]; label: string; max: number }[] = [
  { value: "FACEBOOK", label: "Facebook", max: 2000 },
  { value: "INSTAGRAM", label: "Instagram", max: 2200 },
  { value: "TWITTER", label: "Twitter / X", max: 280 },
  { value: "TIKTOK", label: "TikTok", max: 2200 },
];

export function SugerirPostModal({ efemeride, dirigenteId, onClose }: Props) {
  const [plataforma, setPlataforma] = useState<SugerirPostRequest["plataforma"]>("FACEBOOK");
  const [draft, setDraft] = useState("");
  const [copied, setCopied] = useState(false);
  const mutation = useSugerirPost();

  // Auto-generate on open + on plataforma change
  useEffect(() => {
    mutation.mutate(
      { efemeride_id: efemeride.id, dirigente_id: dirigenteId, plataforma },
      {
        onSuccess: (data) => setDraft(data.contenido),
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plataforma]);

  const platSpec = PLATAFORMAS.find((p) => p.value === plataforma)!;
  const charCount = draft.length;
  const charPct = (charCount / platSpec.max) * 100;
  const charClass = charPct > 90 ? "text-destructive" : charPct > 75 ? "text-amber-600" : "text-muted-foreground";

  const copy = async () => {
    const fullText = `${draft}\n\n${mutation.data?.hashtags?.join(" ") ?? ""}`.trim();
    await navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent" />
            Sugerir post · {efemeride.titulo}
          </DialogTitle>
          <DialogDescription className="text-xs">
            {efemeride.dia}/{efemeride.mes} · viralidad{" "}
            <Badge variant="outline" className="ml-1 text-[9px] uppercase">
              {efemeride.viralidad}
            </Badge>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Selector plataforma */}
          <div className="flex flex-wrap gap-1.5">
            {PLATAFORMAS.map((p) => (
              <Button
                key={p.value}
                type="button"
                size="sm"
                variant={p.value === plataforma ? "default" : "outline"}
                onClick={() => setPlataforma(p.value)}
                className="text-xs"
              >
                {p.label}
              </Button>
            ))}
          </div>

          {/* Aviso fallback */}
          {mutation.data?.fuente === "plantilla_fallback" && mutation.data.aviso && (
            <div className="flex items-start gap-2 rounded-md border border-amber-300/60 bg-amber-50/60 p-3 text-[11px] text-amber-800 leading-tight">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{mutation.data.aviso}</span>
            </div>
          )}

          {/* Loading */}
          {mutation.isPending && (
            <div className="rounded-md border border-border/60 bg-muted/40 p-4 text-center text-sm text-muted-foreground">
              Generando draft...
            </div>
          )}

          {/* Error */}
          {mutation.isError && (
            <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
              Error generando draft. Intenta de nuevo.
            </div>
          )}

          {/* Editor */}
          {!mutation.isPending && draft && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="draft" className="text-xs font-semibold">
                  Texto del post (editable)
                </Label>
                <span className={`text-[10px] tabular-nums ${charClass}`}>
                  {charCount} / {platSpec.max}
                </span>
              </div>
              <Textarea
                id="draft"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={8}
                className="text-sm"
              />
              {mutation.data?.hashtags && mutation.data.hashtags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {mutation.data.hashtags.map((h) => (
                    <Badge key={h} variant="secondary" className="text-[10px]">
                      {h}
                    </Badge>
                  ))}
                </div>
              )}
              <p className="text-[10px] text-muted-foreground italic">
                Fuente: {mutation.data?.fuente === "claude_api" ? "Claude API" : "Plantilla genérica"}
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cerrar
          </Button>
          <Button onClick={copy} disabled={!draft || mutation.isPending} className="gap-1.5">
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5" />
                Copiado
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                Copiar
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
