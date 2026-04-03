import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { ProgramaSocial } from "../types";

export function useProgramas() {
  return useQuery({
    queryKey: ["programas"],
    queryFn: () => api.get<ProgramaSocial[]>("/programas"),
  });
}
