/**
 * Reels generator hooks · D-REELS-GROQ-1 (2026-05-15)
 * Endpoint: /api/v1/reels/*
 * Provider: Groq Llama 3.3 70B Versatile (tier gratuito)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export type Tono = "informativo" | "emocional" | "urgente" | "inspiracional";
export type Duracion = 15 | 30 | 60;

export interface ReelScript {
  hook: string;
  desarrollo: string;
  cta: string;
}

export interface ReelScriptMetadata {
  model: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  elapsed_ms: number;
}

export interface GenerateReelScriptRequest {
  dirigente_id: number;
  tema?: string | null;
  duracion_segundos: Duracion;
  tono: Tono;
  incluir_cta: boolean;
  contexto_adicional?: string | null;
}

export interface GenerateReelScriptResponse {
  id: string;
  dirigente_id: number;
  dirigente_nombre: string;
  tema: string | null;
  duracion_segundos: number;
  tono: string;
  incluir_cta: boolean;
  script: ReelScript;
  metadata: ReelScriptMetadata;
  created_at: string;
}

export interface ReelScriptListItem {
  id: string;
  tema: string | null;
  duracion_segundos: number;
  tono: string;
  script: ReelScript;
  modelo_ia: string;
  created_at: string;
}

export function useGenerateReelScript() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: GenerateReelScriptRequest) =>
      api.post<GenerateReelScriptResponse>("/reels/generate-script", req),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({
        queryKey: ["reels", "recent", vars.dirigente_id],
      });
    },
  });
}

export function useRecentReelScripts(
  dirigente_id: number | null,
  limit = 10,
) {
  return useQuery({
    queryKey: ["reels", "recent", dirigente_id, limit],
    queryFn: () =>
      api.get<ReelScriptListItem[]>(
        `/reels/recent?dirigente_id=${dirigente_id}&limit=${limit}`,
      ),
    enabled: !!dirigente_id,
    staleTime: 30_000,
  });
}
