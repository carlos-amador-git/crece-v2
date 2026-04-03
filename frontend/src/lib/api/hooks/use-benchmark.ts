import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type {
  BenchmarkData,
  Dirigente,
  PaginatedResponse,
} from "../types";

export function useBenchmarkComparison(
  dirigenteId: number | string,
  competidorId: number | string
) {
  return useQuery({
    queryKey: ["benchmark", dirigenteId, competidorId],
    queryFn: () =>
      api.get<BenchmarkData>(
        `/benchmark?dirigente_id=${dirigenteId}&competidor_id=${competidorId}`
      ),
    enabled: !!dirigenteId && !!competidorId,
  });
}

export function useBenchmarkDirigentes() {
  return useQuery({
    queryKey: ["benchmark-dirigentes"],
    queryFn: () =>
      api.get<PaginatedResponse<Dirigente>>(
        "/dirigentes?per_page=50&sort=ipd_score"
      ),
  });
}
