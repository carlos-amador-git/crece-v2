import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../client";

export type OnboardingPlatform =
  | "TWITTER"
  | "INSTAGRAM"
  | "FACEBOOK"
  | "TIKTOK"
  | "YOUTUBE";

export interface OnboardingHandle {
  platform: OnboardingPlatform;
  handle: string;
  url?: string | null;
}

export interface OnboardingRequest {
  full_name: string;
  cargo: string;
  partido?: string;
  estado?: string;
  municipio?: string | null;
  seccion_electoral?: string | null;
  email: string;
  password: string;
  handles: OnboardingHandle[];
}

export interface OnboardingResponse {
  dirigente_id: number;
  user_id: number;
  sync_status: string;
  task_id: string | null;
  profiles_created: number;
  message: string;
}

export interface OnboardingProgressStep {
  name: "scraping" | "analyzing" | "calculating_ipd" | "ready";
  status: "pending" | "running" | "done" | "error";
  started_at: string | null;
  finished_at: string | null;
  detail: string | null;
}

export interface OnboardingProgressResponse {
  dirigente_id: number;
  sync_status: string;
  task_id: string | null;
  error: string | null;
  progress_pct: number;
  steps: OnboardingProgressStep[];
  updated_at: string | null;
}

export function useOnboardDirigente() {
  return useMutation({
    mutationFn: (payload: OnboardingRequest) =>
      api.post<OnboardingResponse>("/dirigentes/onboard", payload),
  });
}

export function useOnboardingProgress(
  dirigenteId: number | null,
  enabled = true,
) {
  return useQuery({
    queryKey: ["onboarding-progress", dirigenteId],
    queryFn: () =>
      api.get<OnboardingProgressResponse>(
        `/dirigentes/${dirigenteId}/onboarding-progress`,
      ),
    enabled: enabled && dirigenteId != null,
    // Poll every 2s while not ready
    refetchInterval: (query) => {
      const data = query.state.data as OnboardingProgressResponse | undefined;
      if (!data) return 2000;
      if (data.sync_status === "ready" || data.sync_status === "error") {
        return false;
      }
      return 2000;
    },
  });
}
