import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { Evento, EventoFilters, PaginatedResponse } from "../types";

export function useEventos(filters: EventoFilters = {}) {
  const params = new URLSearchParams();
  if (filters.estado) params.set("estado", filters.estado);
  if (filters.tipo) params.set("tipo", filters.tipo);
  if (filters.org_id != null) params.set("org_id", String(filters.org_id));
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));

  const qs = params.toString();
  const endpoint = `/eventos${qs ? `?${qs}` : ""}`;

  return useQuery({
    queryKey: ["eventos", filters],
    queryFn: () => api.get<PaginatedResponse<Evento>>(endpoint),
  });
}
