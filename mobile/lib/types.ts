/**
 * TypeScript types matching the backend Pydantic schemas.
 */

import type {
  IntencionVotoType,
  NivelCertezaType,
  ResultadoVisitaType,
  EstadoRutaType,
} from "@/constants/enums";

// ── Auth ────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "field_operator" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ── Encuestas ───────────────────────────────────────────

export interface EncuestaCreate {
  ciudadano_id: number;
  seccion_id?: number | null;
  intencion_voto: IntencionVotoType;
  nivel_certeza?: NivelCertezaType;
  motivacion?: string | null;
  problematicas_detectadas?: Array<Record<string, unknown>> | null;
  latitud?: number | null;
  longitud?: number | null;
  fecha_encuesta: string; // YYYY-MM-DD
  duracion_minutos?: number | null;
  notas?: string | null;
}

export interface Encuesta {
  id: number;
  ciudadano_id: number;
  encuestador_id: number;
  org_id: number | null;
  seccion_id: number | null;
  intencion_voto: IntencionVotoType;
  nivel_certeza: NivelCertezaType;
  motivacion: string | null;
  problematicas_detectadas: Array<Record<string, unknown>> | null;
  fecha_encuesta: string;
  duracion_minutos: number | null;
  notas: string | null;
  created_at: string;
}

// ── Canvassing ──────────────────────────────────────────

export interface PuntoRuta {
  id: number;
  orden: number;
  ciudadano_id: number;
  ciudadano_nombre: string | null;
  visitado: boolean;
  visitado_at: string | null;
  resultado: ResultadoVisitaType | null;
  notas: string | null;
  lat: number | null;
  lon: number | null;
}

export interface RouteProgress {
  total: number;
  completados: number;
  porcentaje: number;
  distancia_restante_km: number | null;
}

export interface RutaCanvassing {
  id: number;
  org_id: number | null;
  encuestador_id: number;
  seccion_id: number | null;
  nombre: string;
  fecha_asignada: string;
  estado: EstadoRutaType;
  distancia_total_km: number | null;
  tiempo_estimado_min: number | null;
  puntos_total: number;
  puntos_completados: number;
  notas: string | null;
  created_at: string;
  updated_at: string;
  puntos: PuntoRuta[];
  progress: RouteProgress | null;
  geometry_geojson: Record<string, unknown> | null;
}

export interface NearbyCiudadano {
  id: number;
  nombre: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  direccion: string | null;
  lat: number | null;
  lon: number | null;
  distancia_km: number;
}

// ── Ciudadanos (search) ─────────────────────────────────

export interface Ciudadano {
  id: number;
  nombre: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  seccion_electoral: number | null;
  direccion: string | null;
}
