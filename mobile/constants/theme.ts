/**
 * CRECE Campo design tokens.
 * Primary navy, gold accent, emerald for success states.
 */

export const Colors = {
  primary: "#1e3a5f",
  primaryLight: "#2d5a8e",
  primaryDark: "#0f1f33",
  accent: "#d4a853",
  accentLight: "#e8c97a",
  emerald: "#10b981",
  emeraldLight: "#d1fae5",
  error: "#ef4444",
  errorLight: "#fef2f2",
  warning: "#f59e0b",
  warningLight: "#fef3c7",
  white: "#ffffff",
  gray50: "#f9fafb",
  gray100: "#f3f4f6",
  gray200: "#e5e7eb",
  gray300: "#d1d5db",
  gray400: "#9ca3af",
  gray500: "#6b7280",
  gray600: "#4b5563",
  gray700: "#374151",
  gray800: "#1f2937",
  gray900: "#111827",
} as const;

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const FontSize = {
  xs: 12,
  sm: 14,
  base: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  heading: 28,
} as const;

export const BorderRadius = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
} as const;
