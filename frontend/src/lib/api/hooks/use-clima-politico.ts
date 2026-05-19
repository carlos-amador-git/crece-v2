import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export interface ClimaPoliticoPoint {
  fecha: string;
  valor_pct: number;
  metrica: string;
}

export interface ClimaPoliticoSerie {
  actor_nombre: string;
  actor_tipo: string;
  ambito: string;
  entidad: string | null;
  municipio: string | null; // solo para alcaldes
  puntos: ClimaPoliticoPoint[];
}

export function useClimaPolitico(metrica: "aprobacion" | "desaprobacion" | "ambas" = "ambas") {
  return useQuery({
    queryKey: ["clima-politico", metrica],
    queryFn: () =>
      api.get<ClimaPoliticoSerie[]>(`/social/clima-politico?metrica=${metrica}`),
    staleTime: 5 * 60_000,
  });
}
