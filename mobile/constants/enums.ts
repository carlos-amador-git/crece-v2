/**
 * Enums mirroring the backend StrEnum values.
 * Keep in sync with backend/app/models/*.py
 */

export const IntencionVoto = {
  MC: "mc",
  MORENA: "morena",
  PAN: "pan",
  PRI: "pri",
  PVEM: "pvem",
  PT: "pt",
  OTRO: "otro",
  INDECISO: "indeciso",
} as const;

export type IntencionVotoType =
  (typeof IntencionVoto)[keyof typeof IntencionVoto];

export const IntencionVotoLabels: Record<IntencionVotoType, string> = {
  mc: "Movimiento Ciudadano",
  morena: "Morena",
  pan: "PAN",
  pri: "PRI",
  pvem: "PVEM",
  pt: "PT",
  otro: "Otro",
  indeciso: "Indeciso",
};

export const NivelCerteza = {
  ALTA: "alta",
  MEDIA: "media",
  BAJA: "baja",
} as const;

export type NivelCertezaType =
  (typeof NivelCerteza)[keyof typeof NivelCerteza];

export const NivelCertezaLabels: Record<NivelCertezaType, string> = {
  alta: "Alta",
  media: "Media",
  baja: "Baja",
};

export const ResultadoVisita = {
  ENCUESTA_COMPLETADA: "encuesta_completada",
  NO_EN_CASA: "no_en_casa",
  RECHAZO: "rechazo",
  REAGENDADO: "reagendado",
  DIRECCION_INCORRECTA: "direccion_incorrecta",
} as const;

export type ResultadoVisitaType =
  (typeof ResultadoVisita)[keyof typeof ResultadoVisita];

export const ResultadoVisitaLabels: Record<ResultadoVisitaType, string> = {
  encuesta_completada: "Encuesta completada",
  no_en_casa: "No en casa",
  rechazo: "Rechazo",
  reagendado: "Reagendado",
  direccion_incorrecta: "Direccion incorrecta",
};

export const EstadoRuta = {
  PENDIENTE: "pendiente",
  EN_PROGRESO: "en_progreso",
  COMPLETADA: "completada",
  CANCELADA: "cancelada",
} as const;

export type EstadoRutaType = (typeof EstadoRuta)[keyof typeof EstadoRuta];
