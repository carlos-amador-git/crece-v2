/**
 * Types for CRECE v2 Remotion video compositions.
 * Mirrors backend schema: /api/v1/dirigentes/{id}/diagnostico
 */

export interface PlatformScore {
  platform: "twitter" | "instagram" | "facebook" | "tiktok" | "youtube";
  followers: number;
  engagement_rate: number;
  score: number;
}

export interface Recommendation {
  priority: number;
  category: string;
  text: string;
}

export interface DiagnosticoVideoProps {
  nombre: string;
  cargo: string;
  ipd_score: number;
  platforms: PlatformScore[];
  recommendations: Recommendation[];
}

/** Timing constants (in frames at 30fps) */
export const TIMING = {
  FPS: 30,
  TOTAL_FRAMES: 900, // 30 seconds

  // Sequence start frames
  LOGO_START: 0,
  LOGO_DURATION: 90, // 3s

  NOMBRE_START: 90,
  NOMBRE_DURATION: 120, // 4s

  IPD_START: 210,
  IPD_DURATION: 150, // 5s

  PLATFORMS_START: 360,
  PLATFORMS_DURATION: 300, // 10s

  RECS_START: 660,
  RECS_DURATION: 150, // 5s

  CTA_START: 810,
  CTA_DURATION: 90, // 3s
} as const;

/** Movimiento Ciudadano brand colors */
export const MC_COLORS = {
  naranja: "#FF6B00",
  naranjaLight: "#FF8F3F",
  naranjaDark: "#CC5600",
  blanco: "#FFFFFF",
  grisOscuro: "#1A1A2E",
  grisMedio: "#2D2D44",
  grisClaro: "#8E8EA0",
  negro: "#0F0F1A",
} as const;
