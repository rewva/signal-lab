import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { STANDARD } from "../theme";
import { FONT_FAMILY } from "../font";
import { PakkaSeal } from "../blocks/StaticBlocks";

// 4s logo sting (intro/outro). Pakka slides in -> GK chip stamps -> seal stamps -> tagline.
export const LogoSting: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sp = (delay: number, cfg = {}) =>
    spring({ frame: frame - delay, fps, config: { damping: 14, mass: 0.7, stiffness: 130, ...cfg }, durationInFrames: 22 });

  const bg = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const pakka = sp(8);
  const chip = sp(28, { damping: 9, stiffness: 170 });          // stamp w/ overshoot
  const seal = sp(50, { damping: 10, stiffness: 160 });
  const tag = interpolate(frame, [74, 92], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // white flashes at the two stamp impacts
  const flash = Math.max(
    interpolate(frame, [34, 40, 50], [0, 0.35, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
    interpolate(frame, [56, 62, 72], [0, 0.3, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
  );

  return (
    <AbsoluteFill style={{ background: STANDARD.bg, fontFamily: FONT_FAMILY, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill style={{ opacity: bg, background:
        `radial-gradient(circle at 50% 40%, rgba(${STANDARD.accentRgb},0.22), transparent 55%), ${STANDARD.bgDeep}` }} />

      <div style={{ zIndex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 54 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
          <span style={{ fontWeight: 800, fontSize: 168, color: STANDARD.text, letterSpacing: "-.02em",
                         opacity: pakka, transform: `translateX(${interpolate(pakka, [0, 1], [-70, 0])}px)` }}>Pakka</span>
          <span style={{ fontWeight: 800, fontSize: 150, color: STANDARD.bg, background: STANDARD.accent,
                         padding: "6px 40px", borderRadius: 28, boxShadow: "0 10px 0 rgba(0,0,0,0.22)",
                         opacity: interpolate(chip, [0, 0.2], [0, 1], { extrapolateRight: "clamp" }),
                         transform: `rotate(-3deg) scale(${interpolate(chip, [0, 1], [2.4, 1])})` }}>GK</span>
        </div>

        <div style={{ opacity: interpolate(seal, [0, 0.2], [0, 1], { extrapolateRight: "clamp" }),
                      transform: `scale(${interpolate(seal, [0, 1], [1.9, 1])})` }}>
          <PakkaSeal size={200} rotate={-9} />
        </div>

        <div style={{ fontWeight: 700, fontSize: 50, color: STANDARD.text, letterSpacing: ".02em",
                      opacity: tag, transform: `translateY(${interpolate(tag, [0, 1], [22, 0])}px)` }}>
          Verified GK. Every day.
        </div>
      </div>

      <AbsoluteFill style={{ background: "#ffffff", opacity: flash, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
