/**
 * Mappers de tokens internos → lenguaje político accesible al dirigente.
 *
 * Sprint 4 · 2026-05-09 · cierre pre-reunión 2026-05-10
 *
 * Las descripciones, plataformas, métricas y responsables se generan en backend
 * con vocabulario técnico (ej: `CROSS`, `FODA[D]:`, `% posts tono=personal`,
 * `MD TI + equipo comunicación`). Estos mappers traducen al render para el VIEWER.
 *
 * No se modifica BD — la regeneración de planes vía LLM se difiere a Oleada 2
 * post-reunión (decisión Gemini cross-audit: evitar contenido absurdo sin
 * validación humana).
 */

export function mapPlataforma(p: string | null | undefined): string {
  if (!p) return "";
  const map: Record<string, string> = {
    CROSS: "Multiplataforma",
    INSTAGRAM: "Instagram",
    TWITTER: "Twitter / X",
    FACEBOOK: "Facebook",
    TIKTOK: "TikTok",
    YOUTUBE: "YouTube",
    LINKEDIN: "LinkedIn",
    THREADS: "Threads",
    TELEGRAM: "Telegram",
    BLUESKY: "Bluesky",
    WHATSAPP: "WhatsApp",
  };
  return map[p.toUpperCase()] ?? p;
}

export interface FodaTagInfo {
  tag: "D" | "O" | "F" | "A";
  label: string;
  icon: string;
  colorClass: string;
}

const FODA_INFO: Record<string, FodaTagInfo> = {
  D: { tag: "D", label: "Debilidad detectada", icon: "❗", colorClass: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200 border-red-200 dark:border-red-800" },
  O: { tag: "O", label: "Oportunidad", icon: "💡", colorClass: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800" },
  F: { tag: "F", label: "Fortaleza", icon: "💪", colorClass: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200 border-blue-200 dark:border-blue-800" },
  A: { tag: "A", label: "Amenaza", icon: "⚠️", colorClass: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200 border-amber-200 dark:border-amber-800" },
};

/**
 * Extrae prefijo `FODA[X]:` de una descripción y devuelve metadatos del chip
 * + el texto restante limpio. Si no hay prefijo, devuelve null + texto original.
 */
export function parseFodaTag(text: string | null | undefined): { foda: FodaTagInfo | null; descripcion: string } {
  if (!text) return { foda: null, descripcion: "" };
  const m = text.match(/^FODA\[([DOFA])\]:\s*/);
  if (!m) return { foda: null, descripcion: text };
  const tag = m[1] as "D" | "O" | "F" | "A";
  return { foda: FODA_INFO[tag], descripcion: text.slice(m[0].length) };
}

/**
 * Sustituye términos técnicos en una cadena de descripción por equivalentes
 * políticos. Aplicado tras parseFodaTag para limpiar texto residual.
 */
export function detechnicalize(text: string): string {
  if (!text) return "";
  type Replacer = string | ((substring: string, ...args: any[]) => string);
  const replacements: Array<[RegExp, Replacer]> = [
    [/\bscraper(s)?\b/gi, "datos de la plataforma"],
    [/engagement\s*=\s*0/gi, "audiencia que no interactúa"],
    [/\bengagement\b/gi, "interacción"],
    [/redesign editorial/gi, "ajustar la línea de contenido"],
    [/replantear estrategia/gi, "reformular la estrategia"],
    [/MD TI\s*\+\s*equipo comunicaci[oó]n/gi, "Equipo de la organización"],
    [/MD TI/gi, "Equipo de la organización"],
    [/tono\s*=\s*([a-z]+)/gi, (_m: string, t: string) => `tono ${t}`],
    [/% posts tono [a-z]+/gi, (m: string) => m.replace(/^%/, "Porcentaje de posts con")],
  ];
  let out = text;
  for (const [re, sub] of replacements) {
    out = typeof sub === "string" ? out.replace(re, sub) : out.replace(re, sub);
  }
  return out;
}

export function mapResponsable(r: string | null | undefined): string {
  if (!r) return "";
  return detechnicalize(r);
}

export function mapMetrica(m: string | null | undefined): string {
  if (!m) return "";
  // Casos comunes específicos
  const direct: Record<string, string> = {
    "% plataformas con engagement > 0": "Plataformas con audiencia activa",
    "% plataformas con engagement>0": "Plataformas con audiencia activa",
    "% posts tono=personal": "Porcentaje de posts con tono personal",
    "% posts tono=critico": "Porcentaje de posts con tono crítico",
    "publicaciones en CROSS": "Publicaciones multiplataforma",
    "contramedidas documentadas": "Contramedidas documentadas",
    "incremento output en canal ganador %": "Incremento de publicación en canal ganador",
  };
  if (direct[m]) return direct[m];
  return detechnicalize(m);
}

const TONO_LABEL: Record<string, string> = {
  critico: "Crítico",
  propositivo: "Propositivo",
  celebratorio: "Celebratorio",
  informativo: "Informativo",
  solidario: "Solidario",
  ataque: "Ataque",
  personal: "Personal",
};

export function mapTonoLabel(t: string | null | undefined): string {
  if (!t) return "—";
  return TONO_LABEL[t.toLowerCase()] ?? t;
}

const TARGET_LABEL: Record<string, string> = {
  gobierno: "Gobierno",
  oposicion: "Oposición",
  ciudadania: "Ciudadanía",
  medios: "Medios",
  autopromocion: "Autopromoción",
  tema_especifico: "Tema específico",
  dirigente: "Dirigente",
};

export function mapTargetLabel(t: string | null | undefined): string {
  if (!t) return "—";
  return TARGET_LABEL[t.toLowerCase()] ?? t;
}

const AMBITO_LABEL: Record<string, string> = {
  federal: "Federal",
  estatal: "Estatal",
  municipal: "Municipal",
};

export function mapAmbitoLabel(a: string | null | undefined): string {
  if (!a) return "";
  return AMBITO_LABEL[a.toLowerCase()] ?? a;
}
