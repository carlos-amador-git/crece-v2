import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { Ciudadano, CiudadanoFilters, PaginatedResponse } from "../types";

export function useCiudadanos(filters: CiudadanoFilters = {}) {
  const params = new URLSearchParams();
  if (filters.intencion_voto) params.set("intencion_voto", filters.intencion_voto);
  if (filters.colonia) params.set("colonia", filters.colonia);
  if (filters.codigo_postal) params.set("codigo_postal", filters.codigo_postal);
  if (filters.escolaridad) params.set("escolaridad", filters.escolaridad);
  if (filters.org_id != null) params.set("org_id", String(filters.org_id));
  if (filters.search) params.set("search", filters.search);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));

  const qs = params.toString();
  const endpoint = `/ciudadanos${qs ? `?${qs}` : ""}`;

  return useQuery({
    queryKey: ["ciudadanos", filters],
    queryFn: () => api.get<PaginatedResponse<Ciudadano>>(endpoint),
  });
}
