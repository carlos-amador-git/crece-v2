import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

export type AlertaSeveridad = "critica" | "alta" | "media" | "baja";

export interface Gasto {
  id: number;
  concepto: string;
  categoria: string;
  monto: number;
  fecha: string;
  aprobado: boolean;
}

export interface AlertaBlindaje {
  id: number;
  tipo: string;
  mensaje: string;
  severidad: AlertaSeveridad;
  resuelta: boolean;
  created_at: string;
}

export interface ComplianceReport {
  total_gastos: number;
  porcentaje_tope: number;
  alertas_activas: number;
  bot_posts_detected: number;
}

export function useGastos() {
  return useQuery({
    queryKey: ["compliance-gastos"],
    queryFn: () => api.get<Gasto[]>("/blindaje/gastos"),
  });
}

export function useAlertas() {
  return useQuery({
    queryKey: ["compliance-alertas"],
    queryFn: () => api.get<AlertaBlindaje[]>("/blindaje/alertas"),
    refetchInterval: 60_000,
  });
}

export function useComplianceReport(orgId?: number) {
  return useQuery({
    queryKey: ["compliance-report", orgId],
    queryFn: () =>
      api.get<ComplianceReport>(
        `/blindaje/reporte/${orgId ?? "default"}`
      ),
  });
}

export function useRunAudit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ status: string }>("/blindaje/audit"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance-gastos"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-alertas"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-report"] });
    },
  });
}
