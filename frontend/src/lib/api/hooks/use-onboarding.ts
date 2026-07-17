"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { api } from "../client";

// ---------------------------------------------------------------------------
// Tipos del contrato API (espejados con SPRINT-S5-SCOPING.md §T1-T9)
// ---------------------------------------------------------------------------

export type OnboardingPlatform =
  | "TWITTER"
  | "INSTAGRAM"
  | "FACEBOOK"
  | "TIKTOK"
  | "YOUTUBE";

export type PerfilTipo =
  | "politico_activo"
  | "funcionario"
  | "precampana"
  | "empresario";

export interface ManualAccountInput {
  platform: OnboardingPlatform;
  url: string;
}

export interface ManualAccountParsed extends ManualAccountInput {
  handle?: string;
}

export interface SerpCandidate {
  platform: OnboardingPlatform;
  url: string;
  handle: string;
  full_name: string | null;
  score: number;
  verified: boolean;
  followers: number | null;
}

export interface SerpSearchResponse {
  candidates: SerpCandidate[];
  provider: "brightdata" | "apify";
}

export interface ProfileValidation {
  platform: OnboardingPlatform;
  url: string;
  handle: string;
  full_name: string | null;
  verified: boolean;
  followers: number | null;
  posts_count: number | null;
  score: number;
  signals: {
    full_name_match: boolean;
    verified: boolean;
    followers_above_50k: boolean;
    posts_above_20: boolean;
  };
}

export interface ConfirmedAccount {
  platform: OnboardingPlatform;
  url: string;
  handle: string;
  confirmed: true;
}

export interface OAuthInitResponse {
  platform: OnboardingPlatform;
  redirect_url: string;
  status: "stub" | "live";
  message?: string;
}

export interface CompetidorInput {
  full_name: string;
  cargo: string;
  url_ref: string;
}

export interface PromesaInput {
  texto_promesa: string;
  fecha_compromiso: string; // ISO
  evidencia_url?: string | null;
}

export interface ActivationResponse {
  dirigente_id: number;
  sync_status: string;
  task_id: string | null;
  data_fidelity_tier_by_platform: Partial<Record<OnboardingPlatform, string>>;
  message: string;
}

// ---------------------------------------------------------------------------
// Zustand store — state del wizard persistido en localStorage por dirigente
// ---------------------------------------------------------------------------

export interface WizardState {
  dirigenteId: number | null;
  currentStep: number; // 1..9
  perfil: PerfilTipo | null;
  manualAccounts: ManualAccountInput[];
  serpEnabled: boolean;
  serpResults: SerpCandidate[];
  validations: ProfileValidation[];
  confirmations: Record<string, boolean>; // key = `${platform}:${handle}`
  oauthStatuses: Partial<Record<OnboardingPlatform, "stub" | "live" | "pending" | "grayed">>;
  competidores: CompetidorInput[];
  promesas: PromesaInput[];
  activated: boolean;
}

interface WizardStore extends WizardState {
  setDirigente: (id: number) => void;
  setStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  setPerfil: (p: PerfilTipo) => void;
  setManualAccounts: (a: ManualAccountInput[]) => void;
  addManualAccount: (a: ManualAccountInput) => void;
  removeManualAccount: (idx: number) => void;
  setSerpEnabled: (v: boolean) => void;
  setSerpResults: (r: SerpCandidate[]) => void;
  setValidations: (v: ProfileValidation[]) => void;
  toggleConfirmation: (key: string) => void;
  setOAuthStatus: (p: OnboardingPlatform, s: "stub" | "live" | "pending" | "grayed") => void;
  setCompetidores: (c: CompetidorInput[]) => void;
  setPromesas: (p: PromesaInput[]) => void;
  setActivated: (v: boolean) => void;
  reset: () => void;
}

const INITIAL_STATE: WizardState = {
  dirigenteId: null,
  currentStep: 1,
  perfil: null,
  manualAccounts: [],
  serpEnabled: false,
  serpResults: [],
  validations: [],
  confirmations: {},
  oauthStatuses: {
    INSTAGRAM: "pending",
    FACEBOOK: "pending",
    TIKTOK: "pending",
    YOUTUBE: "pending",
    TWITTER: "grayed",
  },
  competidores: [],
  promesas: [],
  activated: false,
};

export const useWizardStore = create<WizardStore>()(
  persist(
    (set) => ({
      ...INITIAL_STATE,
      setDirigente: (id) => set({ dirigenteId: id }),
      setStep: (step) => set({ currentStep: Math.max(1, Math.min(9, step)) }),
      nextStep: () => set((s) => ({ currentStep: Math.min(9, s.currentStep + 1) })),
      prevStep: () => set((s) => ({ currentStep: Math.max(1, s.currentStep - 1) })),
      setPerfil: (perfil) => set({ perfil }),
      setManualAccounts: (manualAccounts) => set({ manualAccounts }),
      addManualAccount: (a) =>
        set((s) => ({ manualAccounts: [...s.manualAccounts, a] })),
      removeManualAccount: (idx) =>
        set((s) => ({
          manualAccounts: s.manualAccounts.filter((_, i) => i !== idx),
        })),
      setSerpEnabled: (serpEnabled) => set({ serpEnabled }),
      setSerpResults: (serpResults) => set({ serpResults }),
      setValidations: (validations) => set({ validations }),
      toggleConfirmation: (key) =>
        set((s) => ({
          confirmations: { ...s.confirmations, [key]: !s.confirmations[key] },
        })),
      setOAuthStatus: (p, status) =>
        set((s) => ({ oauthStatuses: { ...s.oauthStatuses, [p]: status } })),
      setCompetidores: (competidores) => set({ competidores }),
      setPromesas: (promesas) => set({ promesas }),
      setActivated: (activated) => set({ activated }),
      reset: () => set({ ...INITIAL_STATE }),
    }),
    {
      name: "crece_onboarding_wizard",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);

// Helper para derivar handle desde URL pública
export function parseHandleFromUrl(
  platform: OnboardingPlatform,
  url: string,
): string | null {
  if (!url) return null;
  try {
    const u = new URL(url.startsWith("http") ? url : `https://${url}`);
    const path = u.pathname.replace(/^\/+|\/+$/g, "");
    if (!path) return null;
    if (platform === "TWITTER") return path.split("/")[0].replace(/^@/, "");
    if (platform === "INSTAGRAM") return path.split("/")[0].replace(/^@/, "");
    if (platform === "FACEBOOK") return path.split("/")[0];
    if (platform === "TIKTOK") {
      const seg = path.split("/")[0];
      return seg.startsWith("@") ? seg.slice(1) : seg;
    }
    if (platform === "YOUTUBE") {
      const seg = path.split("/")[0];
      return seg.startsWith("@") ? seg.slice(1) : seg;
    }
  } catch {
    return null;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Hooks React Query — contrato API (T1-T9 del SPRINT-CURRENT)
// ---------------------------------------------------------------------------

export function useSaveProfile(dirigenteId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (perfil: PerfilTipo) =>
      api.post(`/onboarding/${dirigenteId}/profile`, { perfil }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["onboarding", dirigenteId] }),
  });
}

export function useSaveManualAccounts(dirigenteId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (accounts: ManualAccountInput[]) =>
      api.post(`/onboarding/${dirigenteId}/accounts-manual`, { accounts }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["onboarding", dirigenteId] }),
  });
}

export function useSerpSearch(dirigenteId: number | null) {
  return useMutation({
    mutationFn: (payload: { full_name: string; cargo: string }) =>
      api.post<SerpSearchResponse>(
        `/onboarding/${dirigenteId}/serp-search`,
        payload,
      ),
  });
}

export function useValidateAccount(dirigenteId: number | null) {
  return useMutation({
    mutationFn: (payload: ManualAccountInput) =>
      api.post<ProfileValidation>(
        `/onboarding/${dirigenteId}/validate-account`,
        payload,
      ),
  });
}

export function useConfirmAccounts(dirigenteId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (accounts: ConfirmedAccount[]) =>
      api.post(`/onboarding/${dirigenteId}/confirm-accounts`, { accounts }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["onboarding", dirigenteId] }),
  });
}

export function useInitOAuth(dirigenteId: number | null) {
  return useMutation({
    mutationFn: (platform: OnboardingPlatform) =>
      api.post<OAuthInitResponse>(
        `/onboarding/${dirigenteId}/oauth/init`,
        { platform },
      ),
  });
}

export function useSaveCompetidores(dirigenteId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (competidores: CompetidorInput[]) =>
      api.post(`/onboarding/${dirigenteId}/competidores`, { competidores }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["onboarding", dirigenteId] }),
  });
}

export function useSavePromesas(dirigenteId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (promesas: PromesaInput[]) =>
      api.post(`/onboarding/${dirigenteId}/promesas`, { promesas }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["onboarding", dirigenteId] }),
  });
}

export function useActivate(dirigenteId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post<ActivationResponse>(`/onboarding/activate/${dirigenteId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["onboarding", dirigenteId] });
      qc.invalidateQueries({ queryKey: ["dirigentes"] });
    },
  });
}

// ---------------------------------------------------------------------------
// Legacy hooks (compat con /dashboard/onboard existente) — NO tocar
// ---------------------------------------------------------------------------

export interface OnboardingHandle {
  platform: OnboardingPlatform;
  handle: string;
  url?: string | null;
}

export type RolPolitico = "oficialismo" | "oposicion" | "independiente";

export interface OnboardingRequest {
  full_name: string;
  cargo: string;
  partido?: string;
  estado?: string;
  municipio?: string | null;
  seccion_electoral?: string | null;
  org_id?: number | null;
  // DISENO-actores-politicos-2026-07-16: obligatorio — el KPI D-23-H y el NLP
  // dependen del rol; el backend rechaza el alta sin él (422).
  rol_politico: RolPolitico;
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
