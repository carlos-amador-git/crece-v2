/* ============================================
 * CRECE v2.0 — HITL (Human-In-The-Loop) API client
 * Editor evaluación NLP — Sprint S4 (PLAN 2026-05-09)
 *
 * Vocabulario v2:
 *   tono:   critico · propositivo · celebratorio · informativo · solidario · ataque · personal
 *   target: gobierno · oposicion · ciudadania · medios · autopromocion · tema_especifico · dirigente
 * ============================================ */

import { api } from "./client";

export type ReviewStatus = "unreviewed" | "confirmed" | "edited";

export type TonoV2 =
  | "critico"
  | "propositivo"
  | "celebratorio"
  | "informativo"
  | "solidario"
  | "ataque"
  | "personal";

export type TargetV2 =
  | "gobierno"
  | "oposicion"
  | "ciudadania"
  | "medios"
  | "autopromocion"
  | "tema_especifico"
  | "dirigente";

export type SampleScope = "cronologico" | "estratificado";
export type SamplePlatform = "all" | "x" | "ig" | "fb" | "tt" | "yt";

export const TONO_V2_OPTIONS: { value: TonoV2; label: string }[] = [
  { value: "critico", label: "Crítico" },
  { value: "propositivo", label: "Propositivo" },
  { value: "celebratorio", label: "Celebratorio" },
  { value: "informativo", label: "Informativo" },
  { value: "solidario", label: "Solidario" },
  { value: "ataque", label: "Ataque" },
  { value: "personal", label: "Personal" },
];

export const TARGET_V2_OPTIONS: { value: TargetV2; label: string }[] = [
  { value: "gobierno", label: "Gobierno" },
  { value: "oposicion", label: "Oposición" },
  { value: "ciudadania", label: "Ciudadanía" },
  { value: "medios", label: "Medios" },
  { value: "autopromocion", label: "Autopromoción" },
  { value: "tema_especifico", label: "Tema específico" },
  { value: "dirigente", label: "Dirigente" },
];

export interface HitlComment {
  id: number;
  parent_post_id: number | null;
  content: string | null;
  author_username: string | null;
  platform: string | null;
  published_at: string | null;
  nlp_tono: string | null;
  nlp_target: string | null;
  nlp_polaridad: number | null;
  off_topic: boolean | null;
  review_status: ReviewStatus | null;
  last_reviewed_by: number | null;
  last_reviewed_at: string | null;
  score: number | null;
  parent_post_snippet?: string | null;
  parent_post_url?: string | null;
}

export interface HitlPost {
  id: number;
  content: string | null;
  platform: string | null;
  url: string | null;
  published_at: string | null;
  nlp_tono: string | null;
  nlp_target: string | null;
  nlp_polaridad: number | null;
  off_topic: boolean | null;
  review_status: ReviewStatus | null;
  last_reviewed_by: number | null;
  last_reviewed_at: string | null;
  score: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
}

export interface HitlSampleResponse {
  posts: HitlPost[];
  comments: HitlComment[];
  progress: {
    reviewed_total: number;
    pending_total: number;
  };
  system_proposal_summary?: {
    tono_dist: Record<string, number>;
    target_dist: Record<string, number>;
  };
  dirigente?: {
    id: number;
    full_name: string;
  };
}

export interface HitlEditPayload {
  tono?: TonoV2 | null;
  target?: TargetV2 | null;
  off_topic?: boolean;
  reason?: string;
}

export interface HitlEditResponse {
  id: number;
  nlp_tono: string | null;
  nlp_target: string | null;
  off_topic: boolean | null;
  review_status: ReviewStatus;
  score: number | null;
  last_reviewed_at: string | null;
  last_reviewed_by: number | null;
}

export interface HitlAuditEntry {
  id: number;
  entity_type: "post" | "comment";
  entity_id: number;
  dirigente_id: number;
  from_tono: string | null;
  to_tono: string | null;
  from_target: string | null;
  to_target: string | null;
  off_topic: boolean;
  actor_id: number;
  actor_name: string | null;
  source: string;
  reason: string | null;
  edited_at: string;
}

export interface HitlSampleParams {
  dirigente_id: number;
  scope?: SampleScope;
  days?: number;
  platform?: SamplePlatform;
  include_reviewed?: boolean;
  n_comments?: number;
  n_posts?: number;
}

function buildSampleQuery(p: HitlSampleParams): string {
  const q = new URLSearchParams();
  q.set("dirigente_id", String(p.dirigente_id));
  if (p.scope) q.set("scope", p.scope);
  if (p.days != null) q.set("days", String(p.days));
  if (p.platform) q.set("platform", p.platform);
  if (p.include_reviewed != null) q.set("include_reviewed", String(p.include_reviewed));
  if (p.n_comments != null) q.set("n_comments", String(p.n_comments));
  if (p.n_posts != null) q.set("n_posts", String(p.n_posts));
  return q.toString();
}

export const hitlApi = {
  getSample: (params: HitlSampleParams) =>
    api.get<HitlSampleResponse>(`/hitl/sample?${buildSampleQuery(params)}`),

  patchComment: (id: number, payload: HitlEditPayload) =>
    api.patch<HitlEditResponse>(`/hitl/comments/${id}`, payload),

  confirmComment: (id: number) =>
    api.post<HitlEditResponse>(`/hitl/comments/${id}/confirm`),

  patchPost: (id: number, payload: HitlEditPayload) =>
    api.patch<HitlEditResponse>(`/hitl/posts/${id}`, payload),

  confirmPost: (id: number) =>
    api.post<HitlEditResponse>(`/hitl/posts/${id}/confirm`),

  getAudit: (dirigenteId: number, since?: string) => {
    const q = new URLSearchParams();
    if (since) q.set("since", since);
    const qs = q.toString();
    return api.get<HitlAuditEntry[]>(
      `/hitl/audit/${dirigenteId}${qs ? `?${qs}` : ""}`
    );
  },
};
