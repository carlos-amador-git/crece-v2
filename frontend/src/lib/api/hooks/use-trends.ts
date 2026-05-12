import { useQuery } from "@tanstack/react-query";
import { api } from "../client";

export type TrendsPeriod = "24h" | "7d" | "30d";

export interface Alcaldia {
  id: number;
  nombre: string;
  cvegeo: string;
}

export interface TopicTrend {
  id: number;
  alcaldia_id: number | null;
  alcaldia_nombre: string | null;
  topic_label: string | null;
  time_bucket: string;
  post_count: number;
  sentiment_avg: number | null;
  growth_rate_24h: number | null;
  sample_post_ids: number[];
}

export interface TrendsGeoResponse {
  alcaldia_id: number | null;
  period: TrendsPeriod;
  trends: TopicTrend[];
}

export function useAlcaldias() {
  return useQuery({
    queryKey: ["alcaldias"],
    queryFn: () => api.get<Alcaldia[]>("/trends/alcaldias"),
    staleTime: 1000 * 60 * 60, // 1h — el catálogo INEGI es estático
  });
}

export function useGeoTrends(params: {
  alcaldia_id?: number | null;
  period?: TrendsPeriod;
  limit?: number;
}) {
  const period = params.period ?? "7d";
  const limit = params.limit ?? 5;
  const alcaldiaQS =
    params.alcaldia_id != null ? `&alcaldia_id=${params.alcaldia_id}` : "";
  return useQuery({
    queryKey: ["trends-geo", period, params.alcaldia_id, limit],
    queryFn: () =>
      api.get<TrendsGeoResponse>(
        `/trends/geo?period=${period}&limit=${limit}${alcaldiaQS}`,
      ),
    refetchInterval: 60_000 * 5, // 5 min — el worker corre cada hora
  });
}
