import React from "react";
import {
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";
import { MC_COLORS, type PlatformScore } from "../types";

interface PlatformStatsProps {
  platforms: PlatformScore[];
}

const PLATFORM_ICONS: Record<string, string> = {
  twitter: "X",
  instagram: "IG",
  facebook: "FB",
  tiktok: "TK",
  youtube: "YT",
};

const PLATFORM_COLORS: Record<string, string> = {
  twitter: "#1DA1F2",
  instagram: "#E4405F",
  facebook: "#1877F2",
  tiktok: "#00F2EA",
  youtube: "#FF0000",
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

interface PlatformRowProps {
  platform: PlatformScore;
  index: number;
}

const PlatformRow: React.FC<PlatformRowProps> = ({ platform, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Staggered entrance: each platform slides in 12 frames after the previous
  const delay = index * 12;

  const slideIn = spring({
    frame: frame - delay,
    fps,
    config: { damping: 14, stiffness: 120 },
  });

  const opacity = interpolate(frame - delay, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Animated follower count
  const animatedFollowers = interpolate(
    frame - delay,
    [10, 60],
    [0, platform.followers],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  // Engagement bar width
  const barWidth = interpolate(
    frame - delay,
    [20, 70],
    [0, Math.min(platform.engagement_rate * 20, 100)],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  const color = PLATFORM_COLORS[platform.platform] ?? MC_COLORS.naranja;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 24,
        padding: "20px 32px",
        borderRadius: 16,
        backgroundColor: `${MC_COLORS.grisMedio}99`,
        transform: `translateX(${interpolate(slideIn, [0, 1], [80, 0])}px)`,
        opacity,
        marginBottom: 16,
      }}
    >
      {/* Platform icon badge */}
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: 14,
          backgroundColor: `${color}22`,
          border: `2px solid ${color}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 24,
          fontWeight: 800,
          color,
          flexShrink: 0,
        }}
      >
        {PLATFORM_ICONS[platform.platform] ?? "?"}
      </div>

      {/* Stats */}
      <div style={{ flex: 1 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 10,
          }}
        >
          <div
            style={{
              fontSize: 26,
              fontWeight: 700,
              color: MC_COLORS.blanco,
              textTransform: "capitalize",
            }}
          >
            {platform.platform === "twitter" ? "X (Twitter)" : platform.platform}
          </div>
          <div
            style={{
              fontSize: 30,
              fontWeight: 800,
              color,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {formatNumber(Math.round(animatedFollowers))}
          </div>
        </div>

        {/* Engagement bar */}
        <div
          style={{
            height: 8,
            borderRadius: 4,
            backgroundColor: MC_COLORS.grisMedio,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${barWidth}%`,
              borderRadius: 4,
              backgroundColor: color,
              boxShadow: `0 0 8px ${color}66`,
            }}
          />
        </div>
        <div
          style={{
            fontSize: 16,
            color: MC_COLORS.grisClaro,
            marginTop: 6,
          }}
        >
          Engagement: {platform.engagement_rate.toFixed(2)}%
        </div>
      </div>
    </div>
  );
};

export const PlatformStats: React.FC<PlatformStatsProps> = ({ platforms }) => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Sort by followers descending
  const sorted = [...platforms].sort((a, b) => b.followers - a.followers);

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
          marginBottom: 40,
          opacity: titleOpacity,
          letterSpacing: "-0.02em",
        }}
      >
        Presencia Digital
      </div>

      {sorted.map((p, i) => (
        <PlatformRow key={p.platform} platform={p} index={i} />
      ))}
    </div>
  );
};
