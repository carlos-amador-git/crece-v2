/**
 * Competitor profiles — modelo ligero benchmark-oriented.
 * Endpoint: /api/v1/aceptacion/competitors/
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export interface Competitor {
  id: number;
  dirigente_objetivo_id: number;
  display_name: string;
  partido: string | null;
  cargo: string | null;
  platform: string;
  profile_handle: string | null;
  profile_url: string | null;
  notes: string | null;
  tags: string[];
  is_active: boolean;
  verified: boolean;
  last_scraped_at: string | null;
  created_at: string;
}

export function useCompetitors(dirigente_objetivo_id: number | null) {
  return useQuery({
    queryKey: ["competitors", "list", dirigente_objetivo_id],
    queryFn: () =>
      api.get<Competitor[]>(
        `/aceptacion/competitors/?dirigente_objetivo_id=${dirigente_objetivo_id}`,
      ),
    enabled: !!dirigente_objetivo_id,
    staleTime: 60_000,
  });
}

export interface CompetitorMonthlyMetric {
  month_start: string;
  posts_count: number;
  total_reactions: number;
  total_comments: number;
  engagement_rate: number | null;
  followers_total: number | null;
}

export interface CompetitorDetail extends Competitor {
  last_6_months: CompetitorMonthlyMetric[];
}

export function useCompetitorDetail(competitor_id: number | null) {
  return useQuery({
    queryKey: ["competitors", "detail", competitor_id],
    queryFn: () =>
      api.get<CompetitorDetail>(`/aceptacion/competitors/${competitor_id}`),
    enabled: !!competitor_id,
    staleTime: 60_000,
  });
}

// A8 fix (2026-05-15) — competidores agrupados por persona en la capa de
// presentación. El backend agrega los profiles de la misma persona en
// .profiles[]. Resuelve "Taboada duplicado" sin tocar BD.

export interface CompetitorProfileItem {
  id: number;
  platform: string;
  profile_handle: string | null;
  profile_url: string | null;
  last_scraped_at: string | null;
}

export interface CompetitorGrouped {
  display_name: string;
  partido: string | null;
  cargo: string | null;
  dirigente_objetivo_id: number;
  verified: boolean;
  tags: string[];
  notes: string | null;
  profiles: CompetitorProfileItem[];
}

export function useCompetitorsGrouped(dirigente_objetivo_id: number | null) {
  return useQuery({
    queryKey: ["competitors", "grouped", dirigente_objetivo_id],
    queryFn: () =>
      api.get<CompetitorGrouped[]>(
        `/aceptacion/competitors/grouped?dirigente_objetivo_id=${dirigente_objetivo_id}`,
      ),
    enabled: !!dirigente_objetivo_id,
    staleTime: 60_000,
  });
}

export interface AdminRankingRow {
  competitor_id: number;
  display_name: string;
  partido: string | null;
  platform: string;
  dirigente_objetivo_id: number;
  dirigente_objetivo_name: string;
  org_id: number;
  followers_total: number | null;
  engagement_rate: number | null;
  posts_count: number | null;
  last_month: string | null;
}

export function useAdminCompetitorRankings(limit = 100) {
  return useQuery({
    queryKey: ["competitors", "admin-rankings", limit],
    queryFn: () =>
      api.get<AdminRankingRow[]>(
        `/aceptacion/competitors/admin/rankings?limit=${limit}`,
      ),
    staleTime: 60_000,
  });
}
