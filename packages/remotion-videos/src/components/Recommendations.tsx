import React from "react";
import {
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";
import { MC_COLORS, type Recommendation } from "../types";

interface RecommendationsProps {
  recommendations: Recommendation[];
}

const PRIORITY_BADGES: Record<number, { label: string; color: string }> = {
  1: { label: "ALTA", color: "#EF4444" },
  2: { label: "MEDIA", color: MC_COLORS.naranja },
  3: { label: "NORMAL", color: "#3B82F6" },
};

export const Recommendations: React.FC<RecommendationsProps> = ({
  recommendations,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Take top 3 by priority
  const top3 = [...recommendations]
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 3);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        height: "100%",
        width: "100%",
        backgroundColor: MC_COLORS.negro,
        padding: "60px 48px",
      }}
    >
      <div
        style={{
          fontSize: 42,
          fontWeight: 600,
          color: MC_COLORS.blanco,
          marginBottom: 48,
          opacity: titleOpacity,
          letterSpacing: "-0.02em",
        }}
      >
        Recomendaciones Clave
      </div>

      {top3.map((rec, i) => {
        const delay = i * 18;

        const slideUp = spring({
          frame: frame - delay - 10,
          fps,
          config: { damping: 14, stiffness: 100 },
        });

        const opacity = interpolate(frame - delay, [10, 30], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        const badge = PRIORITY_BADGES[rec.priority] ?? PRIORITY_BADGES[3];

        return (
          <div
            key={i}
            style={{
              display: "flex",
              gap: 20,
              padding: "28px 32px",
              borderRadius: 16,
              backgroundColor: `${MC_COLORS.grisMedio}99`,
              borderLeft: `4px solid ${badge.color}`,
              marginBottom: 20,
              opacity,
              transform: `translateY(${interpolate(slideUp, [0, 1], [40, 0])}px)`,
            }}
          >
            {/* Number */}
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: 12,
                backgroundColor: `${badge.color}22`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 26,
                fontWeight: 800,
                color: badge.color,
                flexShrink: 0,
              }}
            >
              {i + 1}
            </div>

            {/* Content */}
            <div style={{ flex: 1 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 8,
                }}
              >
                <span
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: badge.color,
                    padding: "2px 10px",
                    borderRadius: 6,
                    backgroundColor: `${badge.color}22`,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  {badge.label}
                </span>
                <span
                  style={{
                    fontSize: 18,
                    color: MC_COLORS.grisClaro,
                    textTransform: "capitalize",
                  }}
                >
                  {rec.category}
                </span>
              </div>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 500,
                  color: MC_COLORS.blanco,
                  lineHeight: 1.4,
                }}
              >
                {rec.text}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
