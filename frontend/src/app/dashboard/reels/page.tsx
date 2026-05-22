"use client";

/**
 * Reels generator UI · D-REELS-GROQ-1 (2026-05-15)
 *
 * Genera guiones para reels (Instagram / TikTok / Facebook) usando
 * Groq Llama 3.3 70B Versatile (tier gratuito · 30 req/min).
 *
 * Diseño:
 * - Form: dirigente · tema (opcional) · duración (15/30/60s) · tono (4 chips)
 *   · checkbox CTA · textarea contexto
 * - Submit → spinner 1-2s → render guión en 3 secciones
 * - Botón "Copiar al portapapeles" por sección
 * - Historial: últimos 10 guiones del dirigente seleccionado
 */
import { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Sparkles, Copy, Check, Film, Clock, Hash } from "lucide-react";
import { useDirigentes } from "@/lib/api/hooks/use-dirigentes";
import {
  useGenerateReelScript,
  useRecentReelScripts,
  type Duracion,
  type Tono,
  type ReelScript,
} from "@/lib/api/hooks/use-reels";

const TONO_OPTIONS: { value: Tono; label: string; help: string }[] = [
  { value: "informativo", label: "Informativo", help: "Datos, claridad" },
  { value: "emocional", label: "Emocional", help: "Conexión personal" },
  { value: "urgente", label: "Urgente", help: "Llamada inmediata" },
  { value: "inspiracional", label: "Inspiracional", help: "Visión, motivación" },
];

const DURACIONES: Duracion[] = [15, 30, 60];

export default function ReelsPage() {
  const { data: dirigentesData } = useDirigentes({ page: 1, per_page: 50 });
  const dirigentes = useMemo(
    () => dirigentesData?.items ?? [],
    [dirigentesData],
  );

  const [dirigenteId, setDirigenteId] = useState<number | null>(null);
  const [tema, setTema] = useState("");
  const [duracion, setDuracion] = useState<Duracion>(30);
  const [tono, setTono] = useState<Tono>("informativo");
  const [incluirCta, setIncluirCta] = useState(true);
  const [contextoAdicional, setContextoAdicional] = useState("");

  // Auto-seleccionar el primer dirigente disponible
  useMemo(() => {
    if (!dirigenteId && dirigentes.length > 0) {
      setDirigenteId(dirigentes[0].id);
    }
  }, [dirigenteId, dirigentes]);

  const selectedDirigente = useMemo(
    () => dirigentes.find((d) => d.id === dirigenteId),
    [dirigentes, dirigenteId],
  );

  const placeholderName = useMemo(() => {
    if (!selectedDirigente) return "El dirigente";
    return selectedDirigente.full_name.split(" ")[0];
  }, [selectedDirigente]);

  const generate = useGenerateReelScript();
  const { data: recent, isLoading: recentLoading } = useRecentReelScripts(
    dirigenteId,
    10,
  );

  const handleGenerate = () => {
    if (!dirigenteId) return;
    generate.mutate({
      dirigente_id: dirigenteId,
      tema: tema.trim() || null,
      duracion_segundos: duracion,
      tono,
      incluir_cta: incluirCta,
      contexto_adicional: contextoAdicional.trim() || null,
    });
  };

  // Regenera con los mismos params de un item del historial · 1 click, sin
  // pasar por el form. Reemplaza el currentScript.
  // ReelScriptListItem no incluye incluir_cta/contexto_adicional (no se
  // persisten en el list) · asumimos defaults razonables: cta=true (mayoría
  // de reels lo lleva), contexto=null (no se reusa).
  const handleRegenerate = (item: { duracion_segundos: number; tono: string; tema: string | null }) => {
    if (!dirigenteId) return;
    generate.mutate({
      dirigente_id: dirigenteId,
      tema: item.tema,
      duracion_segundos: item.duracion_segundos as Duracion,
      tono: item.tono as Tono,
      incluir_cta: true,
      contexto_adicional: null,
    });
  };

  // Duplica · carga config del item al form sin enviar. Usuario puede editar.
  const handleDuplicate = (item: { duracion_segundos: number; tono: string; tema: string | null }) => {
    setTema(item.tema ?? "");
    setDuracion(item.duracion_segundos as Duracion);
    setTono(item.tono as Tono);
    setIncluirCta(true);
    setContextoAdicional("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const currentScript = generate.data?.script;
  const currentMeta = generate.data?.metadata;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 font-heading text-2xl font-bold">
          <Film className="h-6 w-6 text-primary" />
          Generador de guiones para reels
        </h1>
        <p className="text-sm text-muted-foreground">
          Guiones listos para grabar en segundos. Instagram · TikTok · Facebook.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
        {/* ── Form ───────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Configuración</CardTitle>
            <CardDescription>
              El dirigente y el tono · el resto opcional.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Dirigente</Label>
              <Select
                value={dirigenteId ? String(dirigenteId) : ""}
                onValueChange={(v) => setDirigenteId(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar dirigente" />
                </SelectTrigger>
                <SelectContent>
                  {dirigentes.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Tema del reel (opcional)</Label>
              <Input
                value={tema}
                onChange={(e) => setTema(e.target.value)}
                placeholder="ej. Promoción turística Sierra Norte Oaxaca"
                maxLength={500}
              />
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                Duración
              </Label>
              <div className="flex gap-2">
                {DURACIONES.map((d) => (
                  <Button
                    key={d}
                    type="button"
                    variant={duracion === d ? "default" : "outline"}
                    size="sm"
                    onClick={() => setDuracion(d)}
                    className="flex-1"
                  >
                    {d}s
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-1.5">
                <Hash className="h-3.5 w-3.5" />
                Tono
              </Label>
              <div className="grid grid-cols-2 gap-2">
                {TONO_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setTono(opt.value)}
                    className={`rounded-md border p-2 text-left text-xs transition ${
                      tono === opt.value
                        ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                        : "border-border hover:border-primary/40 hover:bg-muted/40"
                    }`}
                  >
                    <div className="font-medium">{opt.label}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {opt.help}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Checkbox
                id="cta"
                checked={incluirCta}
                onCheckedChange={(v) => setIncluirCta(Boolean(v))}
              />
              <Label
                htmlFor="cta"
                className="cursor-pointer text-sm font-normal leading-tight"
              >
                Incluir llamada a la acción (CTA) al final
              </Label>
            </div>

            <div className="space-y-2">
              <Label>Contexto adicional (opcional)</Label>
              <Textarea
                value={contextoAdicional}
                onChange={(e) => setContextoAdicional(e.target.value)}
                placeholder={`ej. ${placeholderName} acaba de regresar de gira en Ixtlán · post fue viral`}
                rows={3}
                maxLength={2000}
              />
              <p className="text-[10px] text-muted-foreground">
                {contextoAdicional.length}/2000
              </p>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={!dirigenteId || generate.isPending}
              className="w-full gap-2"
            >
              <Sparkles className="h-4 w-4" />
              {generate.isPending ? "Generando..." : "Generar guión"}
            </Button>

            {generate.isError && (
              <ErrorBanner
                error={generate.error}
              />
            )}
          </CardContent>
        </Card>

        {/* ── Output ──────────────────────────── */}
        <div className="space-y-4">
          {generate.isPending && <GeneratingSkeleton />}

          {!generate.isPending && currentScript && currentMeta && (
            <ScriptCard
              script={currentScript}
              wordCount={countWords(currentScript)}
              metadata={`${currentMeta.elapsed_ms}ms · ${currentMeta.completion_tokens ?? "?"} tokens`}
              header="Guión generado"
            />
          )}

          {/* Empty state · placeholder visual antes de generar */}
          {!generate.isPending && !currentScript && (
            <EmptyOutputPlaceholder />
          )}

          {/* Historial */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Historial reciente</CardTitle>
              <CardDescription className="text-xs">
                Últimos 10 guiones generados para este dirigente
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recentLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : !recent || recent.length === 0 ? (
                <p className="py-6 text-center text-xs text-muted-foreground">
                  Sin guiones generados todavía para este dirigente.
                </p>
              ) : (
                <div className="space-y-3">
                  {recent.map((r) => (
                    <details
                      key={r.id}
                      className="rounded-md border bg-muted/20 p-3"
                    >
                      <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-xs">
                        <Badge variant="outline" className="text-[10px]">
                          {r.duracion_segundos}s
                        </Badge>
                        <Badge variant="outline" className="text-[10px] capitalize">
                          {r.tono}
                        </Badge>
                        <span className="font-medium">
                          {r.tema ?? "(sin tema · libre)"}
                        </span>
                        <span className="ml-auto text-[10px] text-muted-foreground">
                          {new Date(r.created_at).toLocaleString("es-MX", {
                            day: "numeric",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </summary>
                      <div className="mt-3">
                        <ScriptSections script={r.script} compact />
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 border-t pt-3">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-7 gap-1.5 text-[10px]"
                          disabled={generate.isPending}
                          onClick={() => handleRegenerate(r)}
                        >
                          <Sparkles className="h-3 w-3" /> Regenerar
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-7 gap-1.5 text-[10px]"
                          onClick={() => handleDuplicate(r)}
                        >
                          <Copy className="h-3 w-3" /> Duplicar y editar
                        </Button>
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function countWords(script: ReelScript): number {
  const parts = [script.hook ?? "", script.desarrollo ?? "", script.cta ?? ""];
  return parts.join(" ").split(/\s+/).filter(Boolean).length;
}

function scriptToText(script: ReelScript): string {
  const lines: string[] = [];
  if (script.hook) lines.push(`HOOK (3-5s): ${script.hook}`);
  if (script.desarrollo) lines.push(`\nDESARROLLO: ${script.desarrollo}`);
  if (script.cta) lines.push(`\nCTA: ${script.cta}`);
  return lines.join("\n");
}

function ScriptCard({
  script,
  metadata,
  wordCount,
  header,
}: {
  script: ReelScript;
  metadata: string;
  wordCount: number;
  header: string;
}) {
  const [copiedAll, setCopiedAll] = useState(false);
  const handleCopyAll = async () => {
    await navigator.clipboard.writeText(scriptToText(script));
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 1500);
  };
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">{header}</CardTitle>
            <Badge variant="outline" className="text-[10px] tabular-nums">
              ~{wordCount} palabras
            </Badge>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 gap-1.5 text-[10px]"
            onClick={handleCopyAll}
          >
            {copiedAll ? (
              <>
                <Check className="h-3 w-3" /> copiado
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" /> Copiar todo
              </>
            )}
          </Button>
        </div>
        <span className="text-[10px] text-muted-foreground" title="Solo visible para administradores · vive en tooltip">
          {metadata}
        </span>
      </CardHeader>
      <CardContent>
        <ScriptSections script={script} />
      </CardContent>
    </Card>
  );
}

function EmptyOutputPlaceholder() {
  return (
    <Card className="border-dashed">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm text-muted-foreground">Tu guión aparecerá aquí</CardTitle>
        <CardDescription className="text-xs">
          Generaremos 3 bloques · gancho · desarrollo · CTA.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {[
          { label: "Hook · primeros 3-5 seg", text: "Apertura que captura atención en 3 segundos. Sin esto, el reel se pierde." },
          { label: "Desarrollo", text: "Contenido principal estructurado para mantener al espectador hasta el final." },
          { label: "CTA · cierre", text: "Llamada a la acción concreta · seguir, compartir, comentar." },
        ].map((s) => (
          <div key={s.label} className="rounded-md border border-dashed bg-muted/10 p-3">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
              {s.label}
            </span>
            <p className="mt-1 text-xs italic text-muted-foreground/50">{s.text}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ScriptSections({
  script,
  compact = false,
}: {
  script: ReelScript;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "space-y-2" : "space-y-4"}>
      <Section label="Hook · primeros 3-5 seg" text={script.hook} compact={compact} />
      <Section label="Desarrollo" text={script.desarrollo} compact={compact} />
      {script.cta && (
        <Section label="CTA · cierre" text={script.cta} compact={compact} />
      )}
    </div>
  );
}

function Section({
  label,
  text,
  compact,
}: {
  label: string;
  text: string;
  compact: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className={compact ? "" : "rounded-md border bg-muted/30 p-3"}>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <button
          onClick={handleCopy}
          className="text-[10px] text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
          type="button"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" /> copiado
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" /> copiar
            </>
          )}
        </button>
      </div>
      <p className={compact ? "text-xs leading-relaxed" : "text-sm leading-relaxed"}>
        {text}
      </p>
    </div>
  );
}

function GeneratingSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 animate-pulse text-primary" />
          Generando guión...
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </CardContent>
    </Card>
  );
}

function ErrorBanner({ error }: { error: unknown }) {
  const errAny = error as { response?: { status?: number; data?: { detail?: { error?: string; message?: string } } }; message?: string };
  const status = errAny?.response?.status;
  const detail = errAny?.response?.data?.detail;
  const isConfig = detail?.error === "groq_not_configured";
  return (
    <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
      <div className="font-medium text-amber-700 dark:text-amber-400">
        {isConfig ? "Groq no configurado" : `Error ${status ?? ""}`}
      </div>
      <p className="mt-1 text-muted-foreground">
        {detail?.message ?? errAny?.message ?? "Error desconocido"}
      </p>
      {isConfig && (
        <p className="mt-2 text-muted-foreground">
          Registrar GROQ_API_KEY en{" "}
          <a
            href="https://console.groq.com"
            target="_blank"
            rel="noreferrer"
            className="underline"
          >
            console.groq.com
          </a>{" "}
          (gratuito) y agregar al .env del backend.
        </p>
      )}
    </div>
  );
}
