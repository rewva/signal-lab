import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "../theme";
import { Mascot } from "../mascot/Mascot";
import type { DiffProps } from "../props";

export const Difference: React.FC<{ props: DiffProps; from: number }> = ({ props, from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - from, fps, config: { damping: 14, stiffness: 120, mass: 0.8 }, durationInFrames: 20 });
  const scale = interpolate(p, [0, 1], [0.85, 1]);
  const op = interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" });
  const bob = Math.sin(((frame - from) / fps) * 2.2) * 8;
  return (
    <AbsoluteFill style={{ fontFamily: "Arial, Helvetica, sans-serif", color: DIFF.ink }}>
      <div style={{ position: "absolute", top: 230, left: 70, right: 70, textAlign: "center", opacity: op, transform: `scale(${scale})` }}>
        <div style={{ fontSize: 34, fontWeight: 900, letterSpacing: ".2em", textTransform: "uppercase", color: DIFF.accent, marginBottom: 28 }}>
          The difference
        </div>
        <div style={{ fontSize: 66, fontWeight: 900, lineHeight: 1.18 }}>{props.difference}</div>
        {props.cta ? (
          <div style={{ marginTop: 50, display: "inline-block", fontSize: 46, fontWeight: 900, color: "#fff", background: DIFF.accent, borderRadius: 999, padding: "22px 46px" }}>
            {props.cta}
          </div>
        ) : null}
      </div>
      <div style={{ position: "absolute", bottom: 220, left: 0, right: 0, textAlign: "center", fontSize: 30, fontWeight: 700, color: DIFF.muted }}>
        Source: {props.sourceLine}
      </div>
      <div style={{ position: "absolute", bottom: 110, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `translateY(${bob}px)` }}>
        <Mascot pose="idea" />
      </div>
    </AbsoluteFill>
  );
};
