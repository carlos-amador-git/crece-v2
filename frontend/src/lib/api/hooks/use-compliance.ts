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
    queryFn: async () => {
      const res = await api.get<{ items: Gasto[] } | Gasto[]>("/blindaje/gastos");
      return Array.isArray(res) ? res : res.items;
    },
  });
}

export function useAlertas() {
  return useQuery({
    queryKey: ["compliance-alertas"],
    queryFn: async () => {
      const res = await api.get<{ items: AlertaBlindaje[] } | AlertaBlindaje[]>("/blindaje/alertas");
      return Array.isArray(res) ? res : res.items;
    },
    refetchInterval: 60_000,
  });
}

export function useComplianceReport(orgId?: number) {
  const id = orgId ?? 1;
  return useQuery({
    queryKey: ["compliance-report", id],
    queryFn: async () => {
      const raw = await api.get<Record<string, unknown>>(`/blindaje/reporte/${id}`);
      // Normalize backend shape to frontend interface
      const alertas = raw.alertas_activas;
      const alertasCount = typeof alertas === "number"
        ? alertas
        : typeof alertas === "object" && alertas !== null
          ? Object.values(alertas as Record<string, number>).reduce((a, b) => a + b, 0)
          : 0;
      return {
        total_gastos: (raw.total_gastos as number) ?? 0,
        porcentaje_tope: (raw.porcentaje_tope ?? raw.porcentaje_tope_utilizado ?? 0) as number,
        alertas_activas: alertasCount,
        bot_posts_detected: (raw.bot_posts_detected ?? raw.bot_posts_detectados ?? 0) as number,
      } satisfies ComplianceReport;
    },
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
