import React from "react";
import {
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";
import { MC_COLORS } from "../types";

interface IPDScoreProps {
  score: number;
  nombre: string;
}

export const IPDScore: React.FC<IPDScoreProps> = ({ score, nombre }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animated score counter: counts up from 0 to score
  const animatedScore = interpolate(frame, [15, 90], [0, score], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Scale-in spring for the score circle
  const scaleIn = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  // Progress ring: SVG arc from 0 to score/10
  const circumference = 2 * Math.PI * 140;
  const progress = interpolate(frame, [15, 100], [0, score / 10], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const strokeDashoffset = circumference * (1 - progress);

  // Label fade-in
  const labelOpacity = interpolate(frame, [60, 80], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Score color based on value
  const getScoreColor = (s: number): string => {
    if (s >= 7) return "#22C55E";
    if (s >= 4) return MC_COLORS.naranja;
    return "#EF4444";
  };

  const scoreColor = getScoreColor(score);

  // Score label
  const getScoreLabel = (s: number): string => {
    if (s >= 8) return "Excelente";
    if (s >= 6) return "Bueno";
    if (s >= 4) return "Regular";
    if (s >= 2) return "Bajo";
    return "Critico";
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        width: "100%",
        backgroundColor: MC_COLORS.negro,
        padding: "60px 40px",
      }}
    >
      {/* Title */}
      <div
        style={{
          fontSize: 42,
          fontWeight: 600,
          color: MC_COLORS.blanco,
          marginBottom: 12,
          opacity: interpolate(frame, [0, 20], [0, 1], {
            extrapolateRight: "clamp",
          }),
          letterSpacing: "-0.02em",
        }}
      >
        Indice de Penetracion Digital
      </div>

      <div
        style={{
          fontSize: 28,
          color: MC_COLORS.grisClaro,
          marginBottom: 80,
          opacity: interpolate(frame, [5, 25], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      >
        {nombre}
      </div>

      {/* Score circle */}
      <div
        style={{
          position: "relative",
          width: 340,
          height: 340,
          transform: `scale(${scaleIn})`,
        }}
      >
        <svg
          width={340}
          height={340}
          viewBox="0 0 340 340"
          style={{ position: "absolute", top: 0, left: 0 }}
        >
          {/* Background ring */}
          <circle
            cx={170}
            cy={170}
            r={140}
            fill="none"
            stroke={MC_COLORS.grisMedio}
            strokeWidth={16}
          />
          {/* Progress ring */}
          <circle
            cx={170}
            cy={170}
            r={140}
            fill="none"
            stroke={scoreColor}
            strokeWidth={16}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform="rotate(-90 170 170)"
            style={{
              filter: `drop-shadow(0 0 12px ${scoreColor}66)`,
            }}
          />
        </svg>

        {/* Score number */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              fontSize: 96,
              fontWeight: 800,
              color: scoreColor,
              lineHeight: 1,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {animatedScore.toFixed(1)}
          </div>
          <div
            style={{
              fontSize: 24,
              color: MC_COLORS.grisClaro,
              marginTop: 4,
            }}
          >
            / 10
          </div>
        </div>
      </div>

      {/* Score label */}
      <div
        style={{
          marginTop: 48,
          fontSize: 36,
          fontWeight: 700,
          color: scoreColor,
          opacity: labelOpacity,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}
      >
        {getScoreLabel(score)}
      </div>
    </div>
  );
};
