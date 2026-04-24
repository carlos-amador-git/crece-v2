/**
 * Mapeo partido → rol político federal (CDMX / nacional).
 *
 * Interim para disclaimer "Sentimiento sin afiliación" en Tema Urgente + Alertas
 * mientras el motor §9.8 (backend/app/services/political_framework.py conectado a
 * endpoints) se conecta al dashboard. Ver BLOCKERS.md B-23-03.
 *
 * NOTA: esta clasificación es federal. A nivel estatal puede variar (p.ej. Morena
 * es oficialismo federal pero puede ser oposición en un estado con gobierno PAN).
 * Cuando el framework político 3-capas se conecte, este helper desaparece y el
 * rol lo resuelve el backend con contexto de org/estado.
 */

export type RolPolitico = "oficialismo" | "oposicion" | "independiente";

const PARTIDO_A_ROL_FEDERAL: Record<string, RolPolitico> = {
  MORENA: "oficialismo",
  PT: "oficialismo",
  PVEM: "oficialismo",
  PAN: "oposicion",
  PRI: "oposicion",
  PRD: "oposicion",
  MC: "oposicion",
  INDEPENDIENTE: "independiente",
  SIN_PARTIDO: "independiente",
};

export function rolFromPartido(partido: string | null | undefined): RolPolitico {
  if (!partido) return "independiente";
  const key = partido.trim().toUpperCase();
  return PARTIDO_A_ROL_FEDERAL[key] ?? "independiente";
}

export function disclaimerSentimientoCrudo(rol: RolPolitico): string {
  if (rol === "oficialismo") {
    return "Sentimiento crudo — todavía no aplicamos filtro de afiliación. Tu rol es oficialismo; críticas al gobierno se muestran como negativas aunque para ti sean riesgo real.";
  }
  if (rol === "oposicion") {
    return "Sentimiento crudo — todavía no aplicamos filtro de afiliación. Tu rol es oposición; muchas críticas al gobierno aquí marcadas como negativas suelen ser positivas para tu narrativa.";
  }
  return "Sentimiento crudo — todavía no aplicamos filtro de afiliación. Tu rol es independiente; el signo refleja el tono literal del contenido, no alineación política.";
}
