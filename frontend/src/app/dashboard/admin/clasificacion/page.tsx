"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { Copy, Upload, ClipboardList, CheckCircle2, AlertTriangle } from "lucide-react";

/**
 * Panel interno MD Consultoría — Clasificación manual de posts.
 *
 * Flujo operacional (cadencia semanal):
 * 1. Admin MD elige org y genera prompt con posts pendientes top engagement
 * 2. Copia prompt y lo pega en Claude Code / Gemini CLI (externo)
 * 3. Obtiene JSON con clasificaciones + razones
 * 4. Pega el JSON acá y envía
 * 5. Sistema aplica framework y persiste scores
 *
 * Solo visible para role=admin (MD Consultoría).
 */

interface Stats {
  org_id: number;
  total_posts: number;
  classified: number;
  pending: number;
  coverage_pct: number;
  last_classification_at: string | null;
}

interface PromptResponse {
  org_id: number;
  pending_count: number;
  prompt: string;
  prompt_length: number;
  post_ids: number[];
}

interface BatchResponse {
  org_id: number;
  processed: number;
  failed: number;
  errors: { post_id: number; error: string }[];
}

export default function AdminClassificationPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<Stats[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<number>(1);
  const [limit, setLimit] = useState<number>(30);
  const [promptData, setPromptData] = useState<PromptResponse | null>(null);
  const [llmSource, setLlmSource] = useState<"claude" | "gemini" | "perplexity" | "ensamble">("claude");
  const [jsonPaste, setJsonPaste] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [batchResult, setBatchResult] = useState<BatchResponse | null>(null);
  const [error, setError] = useState<string>("");

  const isAdmin = user?.role === "admin";

  async function loadStats() {
    setLoading(true);
    try {
      const data = await api.get<Stats[]>("/admin/classification/stats");
      setStats(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function generatePrompt() {
    setLoading(true);
    setError("");
    setPromptData(null);
    try {
      const data = await api.get<PromptResponse>(
        `/admin/classification/prompt?org_id=${selectedOrg}&limit=${limit}`,
      );
      setPromptData(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function copyPrompt() {
    if (!promptData) return;
    await navigator.clipboard.writeText(promptData.prompt);
    alert("Prompt copiado. Pégalo en Claude Code o Gemini CLI.");
  }

  async function submitClassifications() {
    setLoading(true);
    setError("");
    setBatchResult(null);
    try {
      const parsed = JSON.parse(jsonPaste);
      if (!Array.isArray(parsed)) {
        throw new Error("El JSON debe ser un array");
      }
      const classifications = parsed.map((c: Record<string, unknown>) => ({
        post_id: c.post_id as number,
        tono: c.tono as string,
        target: c.target as string,
        es_rt: (c.es_rt as boolean) ?? false,
        razon: (c.razon as string) ?? "",
        ia_fuente: llmSource,
      }));
      const res = await api.post<BatchResponse>("/admin/classification/batch", {
        org_id: selectedOrg,
        classifications,
        notas: `Cargado desde panel admin · fuente: ${llmSource}`,
      });
      setBatchResult(res);
      setJsonPaste("");
      await loadStats();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-md p-12 text-center">
        <AlertTriangle className="mx-auto mb-3 h-12 w-12 text-amber-500" />
        <h1 className="font-heading text-xl font-bold">Acceso restringido</h1>
        <p className="text-sm text-muted-foreground">
          Esta sección solo es visible para administradores de MD Consultoría.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6">
      <header>
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <ClipboardList className="h-4 w-4" />
          Panel MD Consultoría
        </div>
        <h1 className="mt-1 font-heading text-2xl font-bold">Clasificación manual de posts</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Cadencia semanal · Flujo: genera prompt → ejecuta en Claude/Gemini → pega JSON → aplica
          framework del tenant.
        </p>
      </header>

      {/* Stats */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Cobertura por organización</CardTitle>
          <button
            onClick={loadStats}
            disabled={loading}
            className="rounded-md border border-border px-3 py-1 text-xs hover:bg-muted"
          >
            Recargar
          </button>
        </CardHeader>
        <CardContent>
          {stats.length === 0 ? (
            <p className="text-sm text-muted-foreground">Click "Recargar" para ver stats.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                    <th className="py-2">Org</th>
                    <th className="py-2 text-right">Total</th>
                    <th className="py-2 text-right">Clasificados</th>
                    <th className="py-2 text-right">Pendientes</th>
                    <th className="py-2 text-right">Cobertura</th>
                    <th className="py-2">Última</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.map((s) => (
                    <tr key={s.org_id} className="border-b last:border-0">
                      <td className="py-2 font-medium">#{s.org_id}</td>
                      <td className="py-2 text-right tabular-nums">{s.total_posts}</td>
                      <td className="py-2 text-right tabular-nums text-emerald-600">
                        {s.classified}
                      </td>
                      <td className="py-2 text-right tabular-nums text-amber-600">
                        {s.pending}
                      </td>
                      <td className="py-2 text-right tabular-nums">
                        <span
                          className={
                            s.coverage_pct >= 80
                              ? "text-emerald-600"
                              : s.coverage_pct >= 30
                                ? "text-amber-600"
                                : "text-red-600"
                          }
                        >
                          {s.coverage_pct}%
                        </span>
                      </td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {s.last_classification_at
                          ? new Date(s.last_classification_at).toLocaleDateString("es-MX")
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 1: Generate prompt */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent">
              1
            </span>
            Generar prompt
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-3">
            <label className="text-sm">
              Org:{" "}
              <select
                value={selectedOrg}
                onChange={(e) => setSelectedOrg(Number(e.target.value))}
                className="ml-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
              >
                <option value={1}>MC-CDMX (1)</option>
                <option value={2}>GOB-OAXACA (2)</option>
                <option value={3}>CDMX-IND (3)</option>
              </select>
            </label>
            <label className="text-sm">
              Límite:{" "}
              <input
                type="number"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                min={5}
                max={100}
                className="ml-1 w-20 rounded-md border border-border bg-background px-2 py-1 text-sm"
              />
            </label>
            <button
              onClick={generatePrompt}
              disabled={loading}
              className="rounded-md bg-accent px-4 py-1.5 text-sm font-medium text-accent-foreground hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Generando..." : "Generar prompt"}
            </button>
          </div>

          {promptData && (
            <div className="rounded-md border border-border bg-muted/30 p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-xs text-muted-foreground">
                  {promptData.pending_count} posts · {promptData.prompt_length} chars · IDs:{" "}
                  {promptData.post_ids.slice(0, 5).join(", ")}
                  {promptData.post_ids.length > 5 && "..."}
                </div>
                <button
                  onClick={copyPrompt}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-xs hover:bg-muted"
                >
                  <Copy className="h-3 w-3" /> Copiar
                </button>
              </div>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs">
                {promptData.prompt.slice(0, 800)}
                {promptData.prompt.length > 800 && "\n... (truncado en UI, cópialo completo)"}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2: Paste JSON */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent">
              2
            </span>
            Pegar JSON con clasificaciones
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-3">
            <label className="text-sm">
              Fuente IA:{" "}
              <select
                value={llmSource}
                onChange={(e) => setLlmSource(e.target.value as typeof llmSource)}
                className="ml-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
              >
                <option value="claude">Claude</option>
                <option value="gemini">Gemini</option>
                <option value="perplexity">Perplexity</option>
                <option value="ensamble">Ensamble (3 IAs deliberaron)</option>
              </select>
            </label>
          </div>
          <Textarea
            value={jsonPaste}
            onChange={(e) => setJsonPaste(e.target.value)}
            placeholder='[{"post_id": 728, "tono": "personal", "target": "autopromocion", "es_rt": false, "razon": "..."}, ...]'
            rows={12}
            className="font-mono text-xs"
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {jsonPaste.length} chars. Debe ser un array JSON válido.
            </p>
            <button
              onClick={submitClassifications}
              disabled={loading || !jsonPaste.trim()}
              className="inline-flex items-center gap-1 rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:opacity-90 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {loading ? "Procesando..." : "Aplicar clasificaciones"}
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Result */}
      {batchResult && (
        <Card className="border-emerald-200 bg-emerald-50/50 dark:border-emerald-900 dark:bg-emerald-900/10">
          <CardContent className="flex items-start gap-3 p-5">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
            <div className="text-sm">
              <strong>
                {batchResult.processed} posts clasificados exitosamente.
              </strong>{" "}
              {batchResult.failed > 0 && (
                <span className="text-red-600">{batchResult.failed} con error.</span>
              )}
              {batchResult.errors.length > 0 && (
                <details className="mt-2 text-xs">
                  <summary>Ver errores</summary>
                  <ul className="mt-1 space-y-1 text-muted-foreground">
                    {batchResult.errors.map((e, i) => (
                      <li key={i}>
                        Post {e.post_id}: {e.error}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-900/10">
          <CardContent className="flex items-start gap-3 p-5">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
            <div className="text-sm text-red-700 dark:text-red-400">{error}</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
