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
