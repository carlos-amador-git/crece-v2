import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";

export interface SyncStatus {
  id: number;
  task_uuid: string;
  status: "RECEIVED" | "RUNNING" | "COMPLETED" | "PARTIAL" | "TAINTED" | "FAILED";
  slug: string;
  dirigente_id: number;
  counts: {
    steps: string[];
    db_delta: Record<string, number>;
    coverage_gaps: any[];
  } | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface SyncTriggerResponse {
  id?: number;
  task_uuid?: string;
  status?: string;
  sin_novedades?: boolean;
  reason?: string;
}

export function useSyncStatus(dirigenteId: number | string) {
  return useQuery({
    queryKey: ["sync-status", dirigenteId],
    queryFn: () => api.get<SyncStatus>(`/ingest/sync/status/${dirigenteId}`),
    enabled: !!dirigenteId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "RUNNING" || data?.status === "RECEIVED") {
        return 3000; // Poll every 3s if active
      }
      return false;
    },
    retry: false, // Don't retry 404s
  });
}

export function useTriggerSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dirigenteId: number | string) =>
      api.post<SyncTriggerResponse>(`/ingest/sync/${dirigenteId}`, {}),
    onSuccess: (data, dirigenteId) => {
      queryClient.invalidateQueries({ queryKey: ["sync-status", dirigenteId] });
      // If it's running, the useSyncStatus hook will pick it up and start polling.
    },
  });
}
