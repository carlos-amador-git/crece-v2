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
  dirigente_id?: number | null;
  org_id?: number | null;
  org_nombre?: string | null;
  org_slug?: string | null;
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
  // D-23-G' · 2026-04-24 · KPI hero reformulado · ver actividad-alineada-card.tsx
  // Backward compat: `actividad_alineada` = default (Phase A consumers).
  actividad_alineada?: ActividadAlineada;
  // D-23-H · Phase B · doble métrica + pesos editables
  actividad_alineada_default?: ActividadAlineada;
  actividad_alineada_ajustada?: ActividadAlineada;
  pesos_target_politico?: PesosTargetPolitico;
  pesos_last_modified_at?: string | null;
}

// D-23-G' · KPI Actividad Política Alineada
// Reemplaza el flip × -1 sobre sentiment_score por conteo de actividad por target_politico.
// Plan: .context/PLAN-D-23-G-actividad-alineada-2026-04-24.md
export interface ActividadAlineadaBreakdown {
  oficialismo: number;
  oposicion: number;
  propio: number;
  personal: number;
}

export interface ActividadAlineada {
  score: number | null;          // 0..1 · null si no hay datos clasificados
  score_pct: number | null;      // 0..100 (presentación) · null si sin datos
  breakdown: ActividadAlineadaBreakdown;
  total_classified: number;
  total_posts_window: number;
  rol_politico: "oficialismo" | "oposicion" | "independiente" | string;
  days: number;
  modo?: "default" | "ajustado";
  pesos?: PesosTargetPolitico;
  empty_state: "no_classified" | null;
}

// D-23-H · Phase B · pesos editables target_politico (Palanca 1)
// Cap [0.5, 1.5] enforced en CHECK BD + UI. 1.0 = neutro (sin ajuste).
export interface PesosTargetPolitico {
  oficialismo: number;
  oposicion: number;
  propio: number;
  personal: number;
}

export interface PesosUpdateResponse {
  pesos_target_politico: PesosTargetPolitico;
  pesos_last_modified_at: string;
  pesos_last_modified_by: number;
  actividad_alineada_default: ActividadAlineada;
  actividad_alineada_ajustada: ActividadAlineada;
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
  sentiment_label: string | null;
  sentiment_score: number | null;
  likes: number;
  comments: number;
  shares: number;
  views?: number;
  published_at: string;
  collected_at: string;
  media_urls?: string[] | null;
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
  /** P0 #2 (2026-05-19): posts con `sentiment_label IS NULL` cuentan aquí,
   *  no en `neutral`. Permite mostrar caveat real al usuario. */
  unclassified: number;
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
  tipo: string;
  contenido: string;
  modelo_ia: string;
  prompt_usado?: string;
  datos_entrada?: Record<string, unknown> | null;
  generado_por_id: number;
  aprobado: boolean;
  created_at: string;
  estructura_json?: DiagnosticoEstructura | Record<string, unknown> | null;
}

/** D-DIAGNOSTICO-V2-2026-05-21 · shape generado por regen_diagnostico_v2.py */
/** D-DIAGNOSTICO-ENRICHED-2026-05-21 · shape generado por
 *  regen_diagnostico_enriched_host.py · 4 cuadrantes FODA con implicación/táctica/riesgo/mitigación.
 *  Compat back: si plan viejo viene con `riesgos`, normalizar a `amenazas` en frontend. */
export interface DiagnosticoEstructura {
  ipd_score: number;
  ipd_bucket: "BAJO" | "MEDIO" | "ALTO" | "CRITICO" | "BUENO" | "EXCELENTE";
  delta_vs_anterior?: number | null;
  insight_bala: string;
  fortalezas: { titulo: string; evidencia: string; implicacion?: string; card?: string }[];
  oportunidades: { titulo: string; evidencia: string; tactica?: string; card?: string }[];
  debilidades: { titulo: string; evidencia: string; riesgo?: string; card?: string }[];
  amenazas: { titulo: string; evidencia: string; mitigacion?: string; card?: string }[];
  acciones_top3: {
    orden: number;
    texto: string;
    cta_label: string;
    cta_href: string;
    card_origen?: string;
  }[];
  plataforma_prioritaria?: string;
  /** @deprecated · compat con planes v2 antiguos (renombrado a amenazas) */
  riesgos?: { card?: string; titulo: string; evidencia: string }[];
}

/** D-CONSOLIDACION-V2-2026-05-21 · shape generado por regen_consolidacion_v2.py */
export interface ConsolidacionEstructura {
  resumen_ejecutivo: string;
  objetivo_90d: {
    narrativa: string;
    kpis_target: { metrica: string; valor_baseline: number; valor_target: number; unidad: string }[];
  };
  narrativa_central: string;
  pilares: { titulo: string; descripcion: string; tacticas: string[] }[];
  audiencias_prioritarias: { nombre: string; rationale: string; tactica_clave: string }[];
  mitigaciones_debilidades: { debilidad_origen: string; accion_mitigacion: string }[];
  roadmap_3_hitos: { mes: number; hito: string; kpi_control: string }[];
  riesgos: { tipo: string; descripcion: string; mitigacion: string }[];
}

/** D-CONTENIDO-V2-2026-05-21 · shape generado por regen_contenido_v2.py */
export interface ContenidoEstructura {
  ventana: { inicio: string; fin: string; semanas: number };
  cadencia_recomendada: Record<string, string>;
  pilares_editoriales: { titulo: string; descripcion: string; frecuencia_semanal_pct: number }[];
  posts_sugeridos: {
    fecha_sugerida: string;
    hora_optima: string;
    plataforma: string;
    tipo: string;
    pilar: string;
    copy: string;
    hashtags: string[];
    tono: string;
    rationale: string;
    cta_label: string;
  }[];
  veda_warnings: { fecha_inicio: string; fecha_fin: string; descripcion: string }[];
}

export type PlanType = "DIAGNOSTICO" | "CONSOLIDACION" | "CRISIS" | "CONTENIDO";
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
  dirigentes_change: number | null;
  ipd_change: number | null;
  posts_change: number;
  alerts_change: number;
  // political KPIs
  total_audiencia: number;
  audiencia_change: number | null;
  contactos_periodo: number;
  tema_urgente: string | null;
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
