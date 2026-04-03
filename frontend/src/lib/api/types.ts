/* ============================================
 * CRECE v2.0 — TypeScript interfaces
 * Maps to backend API schemas
 * ============================================ */

export interface User {
  id: number;
  email: string;
  nombre: string;
  rol: "admin" | "analista" | "consultor";
  avatar_url?: string;
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface Dirigente {
  id: number;
  nombre: string;
  apellido_paterno: string;
  apellido_materno?: string;
  cargo: string;
  partido: string;
  estado: string;
  municipio?: string;
  avatar_url?: string;
  ipd_score: number;
  platforms: SocialPlatform[];
  last_activity?: string;
  created_at: string;
  updated_at: string;
}

export interface DirigenteDetail extends Dirigente {
  bio?: string;
  social_accounts: SocialAccount[];
  ipd_breakdown: IpdBreakdown;
  secciones: SeccionElectoral[];
  recent_posts: SocialPost[];
  stats: DirigenteStats;
}

export interface DirigenteStats {
  total_posts_7d: number;
  total_engagement_7d: number;
  sentiment_avg_7d: number;
  follower_growth_30d: number;
}

export interface SocialAccount {
  platform: SocialPlatform;
  username: string;
  url: string;
  followers: number;
  verified: boolean;
}

export type SocialPlatform = "twitter" | "instagram" | "facebook" | "tiktok" | "youtube";

export interface IpdBreakdown {
  twitter: number;
  instagram: number;
  facebook: number;
  tiktok: number;
  youtube: number;
  engagement: number;
}

export interface SocialPost {
  id: number;
  dirigente_id: number;
  dirigente_nombre?: string;
  platform: SocialPlatform;
  content: string;
  url: string;
  sentiment: SentimentType;
  sentiment_score: number;
  likes: number;
  comments: number;
  shares: number;
  views?: number;
  published_at: string;
  collected_at: string;
}

export type SentimentType = "positive" | "negative" | "neutral";

export interface SentimentTrend {
  date: string;
  positive: number;
  negative: number;
  neutral: number;
}

export interface SentimentDistribution {
  positive: number;
  negative: number;
  neutral: number;
  total: number;
}

export interface SeccionElectoral {
  id: number;
  seccion_id: string;
  estado: string;
  municipio: string;
  a_favor: number;
  en_contra: number;
  indeciso: number;
  total_encuestas: number;
  geojson?: GeoJSON.Feature;
}

export interface ElectoralMapData {
  type: "FeatureCollection";
  features: ElectoralFeature[];
}

export interface ElectoralFeature {
  type: "Feature";
  geometry: GeoJSON.Geometry;
  properties: {
    seccion_id: string;
    estado: string;
    municipio: string;
    a_favor: number;
    en_contra: number;
    indeciso: number;
    dirigente_coverage: number;
    social_penetration: number;
  };
}

export interface PlanIA {
  id: number;
  dirigente_id: number;
  dirigente_nombre?: string;
  tipo: PlanType;
  titulo: string;
  contenido: string;
  status: PlanStatus;
  created_at: string;
  updated_at: string;
  approved_by?: string;
  approved_at?: string;
}

export type PlanType = "crecimiento" | "crisis" | "engagement" | "posicionamiento" | "contenido";
export type PlanStatus = "draft" | "approved" | "rejected" | "executed";

export interface Benchmark {
  dirigente: Dirigente;
  competidores: Dirigente[];
  comparison: BenchmarkComparison[];
}

export interface BenchmarkComparison {
  metric: string;
  dirigente_value: number;
  competidor_values: { nombre: string; value: number }[];
}

export interface Alert {
  id: number;
  type: "crisis" | "spike" | "drop" | "mention";
  title: string;
  message: string;
  severity: "high" | "medium" | "low";
  dirigente_id?: number;
  read: boolean;
  created_at: string;
}

export interface KpiOverview {
  total_dirigentes: number;
  avg_ipd_score: number;
  posts_monitored_24h: number;
  active_alerts: number;
  dirigentes_change: number;
  ipd_change: number;
  posts_change: number;
  alerts_change: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface DirigenteFilters {
  partido?: string;
  estado?: string;
  ipd_min?: number;
  ipd_max?: number;
  search?: string;
  page?: number;
  per_page?: number;
}

export interface SocialFilters {
  platform?: SocialPlatform;
  sentiment?: SentimentType;
  dirigente_id?: number;
  date_from?: string;
  date_to?: string;
  page?: number;
  per_page?: number;
}
