/* ============================================
 * CRECE v2.0 — TypeScript interfaces
 * Maps to backend API schemas
 * ============================================ */

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "field_operator" | "viewer";
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
  full_name: string;
  cargo: string;
  partido: string;
  estado: string;
  municipio?: string;
  seccion_electoral?: string;
  social_profiles: SocialAccount[];
  avatar_url?: string;
  ipd_score?: number;
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
  avg_sentiment: number;
  post_count: number;
  positive: number;
  positive_pct: number;
  negative: number;
  negative_pct: number;
  neutral: number;
  neutral_pct: number;
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

/* ============================================
 * New entity types — Fase 2 endpoints
 * ============================================ */

export type IntencionVotoCiudadano =
  | "mc"
  | "morena"
  | "pan"
  | "pri"
  | "pvem"
  | "pt"
  | "otro"
  | "indeciso"
  | "no_vota";

export type Escolaridad =
  | "sin_estudios"
  | "primaria"
  | "secundaria"
  | "preparatoria"
  | "licenciatura"
  | "posgrado";

export type RangoEdad =
  | "18_24"
  | "25_34"
  | "35_44"
  | "45_54"
  | "55_64"
  | "65_plus";

export type Genero = "masculino" | "femenino" | "otro" | "no_especificado";

export type NivelInteres = "alto" | "medio" | "bajo" | "desconocido";

export interface Ciudadano {
  id: number;
  nombre: string;
  apellido_paterno: string;
  apellido_materno?: string;
  seccion_id: number;
  direccion?: string;
  telefono?: string;
  email?: string;
  edad_rango: RangoEdad;
  genero: Genero;
  nivel_interes: NivelInteres;
  es_simpatizante_mc: boolean;
  es_promotor: boolean;
  notas?: string;
  registrado_por_id: number;
  intencion_voto?: IntencionVotoCiudadano;
  programas_sociales?: Record<string, unknown>[];
  problematicas?: Record<string, unknown>[];
  colonia?: string;
  codigo_postal?: string;
  escolaridad?: Escolaridad;
  foto_ine_url?: string;
  org_id?: number;
  created_at: string;
  updated_at: string;
}

export interface CiudadanoFilters {
  intencion_voto?: IntencionVotoCiudadano;
  colonia?: string;
  codigo_postal?: string;
  escolaridad?: Escolaridad;
  org_id?: number;
  search?: string;
  page?: number;
  per_page?: number;
}

export type TipoEvento =
  | "reunion"
  | "mitin"
  | "capacitacion"
  | "brigada"
  | "visita"
  | "otro";

export type EstadoEvento =
  | "programado"
  | "en_curso"
  | "completado"
  | "cancelado";

export interface Evento {
  id: number;
  titulo: string;
  descripcion?: string;
  tipo: TipoEvento;
  fecha_inicio: string;
  fecha_fin?: string;
  lugar: string;
  seccion_id?: number;
  dirigente_id?: number;
  organizador_id: number;
  asistentes_esperados?: number;
  asistentes_reales?: number;
  estado: EstadoEvento;
  notas?: string;
  recursos?: Record<string, unknown>;
  nuevos_simpatizantes?: number;
  costo_total?: number;
  costo_por_adquisicion?: number;
  org_id?: number;
  created_at: string;
  updated_at: string;
}

export interface EventoFilters {
  estado?: EstadoEvento;
  tipo?: TipoEvento;
  org_id?: number;
  page?: number;
  per_page?: number;
}

export type NivelGobierno = "federal" | "estatal" | "municipal";

export interface ProgramaSocial {
  id: number;
  nombre: string;
  descripcion: string;
  dependencia: string;
  nivel_gobierno: NivelGobierno;
  presupuesto_anual?: number;
  created_at: string;
}

export interface Organizacion {
  id: number;
  nombre: string;
  tipo?: string;
  created_at: string;
}

export interface Encuesta {
  id: number;
  seccion_id: number;
  fecha: string;
  intencion_voto: IntencionVotoCiudadano;
  created_at: string;
}

export interface EncuestaResumen {
  seccion_id: number;
  total: number;
  mc: number;
  morena: number;
  pan: number;
  pri: number;
  otros: number;
  indeciso: number;
}

export interface MetricaSocial {
  id: number;
  profile_id: number;
  platform: SocialPlatform;
  followers: number;
  following?: number;
  posts_count?: number;
  engagement_rate?: number;
  snapshot_date: string;
}

export interface MetricaSocialTrend {
  date: string;
  followers: number;
  engagement_rate?: number;
}

export interface HealthCheck {
  status: string;
  version?: string;
  timestamp?: string;
}

export interface BenchmarkData {
  dirigente: Dirigente;
  competidores: Dirigente[];
  comparison: BenchmarkComparison[];
}

export interface CrisisAlert {
  id: number;
  active: boolean;
  message: string;
  dirigente_id?: number;
  dirigente_nombre?: string;
  severity: "high" | "medium" | "low";
  created_at: string;
}

export interface SystemStatus {
  last_sync: string;
  workers_active: number;
  workers_total: number;
  scrapers_running: number;
}
