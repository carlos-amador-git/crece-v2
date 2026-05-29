import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export interface AceptacionRow {
  dirigente_id: number;
  full_name: string;
  rol_politico: string | null;
  total_followers: number;
  unique_commenters: number;
  total_comments: number;
  pct_activados: number;
  pct_fantasma: number;
  pct_aprobacion: number;
  pct_rechazo: number;
  pct_neutral: number;
}

export interface AceptacionOverview {
  dirigentes: AceptacionRow[];
  total_corpus_comments: number;
  metodologia: string;
}

export function useAceptacionOverview() {
  return useQuery({
    queryKey: ["aceptacion", "overview"],
    queryFn: () => api.get<AceptacionOverview>("/social/aceptacion/overview"),
    staleTime: 60_000,
  });
}

export interface PlatformFantasmaRow {
  platform: string;
  followers: number;
  unique_commenters: number;
  pct_activados: number;
  pct_fantasma: number;
}

export interface DirigentePlatformFantasmas {
  dirigente_id: number;
  full_name: string;
  platforms: PlatformFantasmaRow[];
}

export function useFantasmasPorPlataforma() {
  return useQuery({
    queryKey: ["aceptacion", "fantasmas-plataforma"],
    queryFn: () => api.get<DirigentePlatformFantasmas[]>("/social/aceptacion/fantasmas-por-plataforma"),
    staleTime: 60_000,
  });
}
