import React from "react";
import {
  Composition,
  Sequence,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
  AbsoluteFill,
} from "remotion";
import {
  MC_COLORS,
  TIMING,
  type DiagnosticoVideoProps,
} from "../types";
import { IPDScore } from "../components/IPDScore";
import { PlatformStats } from "../components/PlatformStats";
import { Recommendations } from "../components/Recommendations";

// ---------- Internal scene components ----------

const LogoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scaleIn = spring({
    frame,
    fps,
    config: { damping: 10, stiffness: 80 },
  });

  const fadeOut = interpolate(frame, [65, 85], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: MC_COLORS.negro,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: fadeOut,
      }}
    >
      <div
        style={{
          transform: `scale(${scaleIn})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
        }}
      >
        {/* MC Logo placeholder — orange circle with MC text */}
        <div
          style={{
            width: 160,
            height: 160,
            borderRadius: "50%",
            backgroundColor: MC_COLORS.naranja,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: `0 0 60px ${MC_COLORS.naranja}44`,
          }}
        >
          <div
            style={{
              fontSize: 64,
              fontWeight: 900,
              color: MC_COLORS.blanco,
              letterSpacing: "-0.04em",
            }}
          >
            MC
          </div>
        </div>
        <div
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: MC_COLORS.grisClaro,
            letterSpacing: "0.15em",
            textTransform: "uppercase",
          }}
        >
          Movimiento Ciudadano
        </div>
      </div>
    </AbsoluteFill>
  );
};

const NombreScene: React.FC<{ nombre: string; cargo: string }> = ({
  nombre,
  cargo,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const nameSlide = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 100 },
  });

  const cargoOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const lineWidth = interpolate(frame, [10, 50], [0, 200], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: MC_COLORS.negro,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 48px",
      }}
    >
      <div
        style={{
          fontSize: 56,
          fontWeight: 800,
          color: MC_COLORS.blanco,
          textAlign: "center",
          lineHeight: 1.2,
          transform: `translateY(${interpolate(nameSlide, [0, 1], [30, 0])}px)`,
          opacity: nameSlide,
          letterSpacing: "-0.02em",
        }}
      >
        {nombre}
      </div>

      {/* Accent line */}
      <div
        style={{
          width: lineWidth,
          height: 4,
          backgroundColor: MC_COLORS.naranja,
          borderRadius: 2,
          margin: "24px 0",
          boxShadow: `0 0 12px ${MC_COLORS.naranja}66`,
        }}
      />

      <div
        style={{
          fontSize: 30,
          fontWeight: 500,
          color: MC_COLORS.naranja,
          textAlign: "center",
          opacity: cargoOpacity,
        }}
      >
        {cargo}
      </div>
    </AbsoluteFill>
  );
};

const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scaleIn = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 90 },
  });

  const pulseScale =
    1 + 0.03 * Math.sin((frame / fps) * Math.PI * 2);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: MC_COLORS.negro,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 48px",
      }}
    >
      <div
        style={{
          transform: `scale(${scaleIn})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 32,
        }}
      >
        <div
          style={{
            fontSize: 44,
            fontWeight: 700,
            color: MC_COLORS.blanco,
            textAlign: "center",
            lineHeight: 1.3,
          }}
        >
          Transforma tu
          <br />
          presencia digital
        </div>

        <div
          style={{
            padding: "18px 48px",
            borderRadius: 16,
            backgroundColor: MC_COLORS.naranja,
            fontSize: 28,
            fontWeight: 700,
            color: MC_COLORS.blanco,
            transform: `scale(${pulseScale})`,
            boxShadow: `0 0 40px ${MC_COLORS.naranja}55`,
          }}
        >
          Conoce tu plan IA
        </div>

        <div
          style={{
            fontSize: 20,
            color: MC_COLORS.grisClaro,
            marginTop: 16,
          }}
        >
          Powered by CRECE v2.0
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- Main composition ----------

const DiagnosticoVideo: React.FC<DiagnosticoVideoProps> = ({
  nombre,
  cargo,
  ipd_score,
  platforms,
  recommendations,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: MC_COLORS.negro }}>
      {/* Scene 1: Logo MC — 0s to 3s */}
      <Sequence from={TIMING.LOGO_START} durationInFrames={TIMING.LOGO_DURATION}>
        <LogoScene />
      </Sequence>

      {/* Scene 2: Nombre y cargo — 3s to 7s */}
      <Sequence from={TIMING.NOMBRE_START} durationInFrames={TIMING.NOMBRE_DURATION}>
        <NombreScene nombre={nombre} cargo={cargo} />
      </Sequence>

      {/* Scene 3: IPD Score animado — 7s to 12s */}
      <Sequence from={TIMING.IPD_START} durationInFrames={TIMING.IPD_DURATION}>
        <IPDScore score={ipd_score} nombre={nombre} />
      </Sequence>

      {/* Scene 4: Platform stats — 12s to 22s */}
      <Sequence from={TIMING.PLATFORMS_START} durationInFrames={TIMING.PLATFORMS_DURATION}>
        <PlatformStats platforms={platforms} />
      </Sequence>

      {/* Scene 5: Recommendations — 22s to 27s */}
      <Sequence from={TIMING.RECS_START} durationInFrames={TIMING.RECS_DURATION}>
        <Recommendations recommendations={recommendations} />
      </Sequence>

      {/* Scene 6: CTA — 27s to 30s */}
      <Sequence from={TIMING.CTA_START} durationInFrames={TIMING.CTA_DURATION}>
        <CTAScene />
      </Sequence>
    </AbsoluteFill>
  );
};

// ---------- Remotion Root ----------

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="DiagnosticoVideo"
        component={DiagnosticoVideo}
        durationInFrames={TIMING.TOTAL_FRAMES}
        fps={TIMING.FPS}
        width={1080}
        height={1920}
        defaultProps={{
          nombre: "Alejandro Pina",
          cargo: "Dirigente MC — CDMX",
          ipd_score: 4.2,
          platforms: [
            {
              platform: "twitter",
              followers: 3100,
              engagement_rate: 1.8,
              score: 4.5,
            },
            {
              platform: "instagram",
              followers: 2200,
              engagement_rate: 3.2,
              score: 5.1,
            },
            {
              platform: "facebook",
              followers: 1800,
              engagement_rate: 0.9,
              score: 3.2,
            },
          ],
          recommendations: [
            {
              priority: 1,
              category: "contenido",
              text: "Crear serie semanal de video corto en TikTok e Instagram Reels",
            },
            {
              priority: 2,
              category: "engagement",
              text: "Implementar sesiones de Q&A en vivo cada 15 dias",
            },
            {
              priority: 3,
              category: "presencia",
              text: "Activar canal de YouTube con contenido de propuestas",
            },
          ],
        }}
      />
    </>
  );
};
