import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "../theme";
import { Mascot } from "../mascot/Mascot";
import { ItemImageView } from "../blocks/Pieces";
import type { DiffProps } from "../props";

export const Hook: React.FC<{ props: DiffProps; from: number }> = ({ props, from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = (i: number) => {
    const p = spring({ frame: frame - from - i * 4, fps, config: { damping: 16, mass: 0.8 }, durationInFrames: 16 });
    return {
      opacity: interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" }),
      transform: `translateY(${interpolate(p, [0, 1], [40, 0])}px)`,
    };
  };
  const bob = Math.sin(((frame - from) / fps) * 2.2) * 8;
  const [x, y] = props.items;
  return (
    <AbsoluteFill style={{ fontFamily: "Arial, Helvetica, sans-serif", color: DIFF.ink }}>
      <div style={{ position: "absolute", top: 220, left: 60, right: 60, display: "flex", gap: 40 }}>
        {[x, y].map((it, i) => (
          <div key={it.name} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 26, ...enter(i) }}>
            <div style={{ fontSize: 80, fontWeight: 900, letterSpacing: "-.02em" }}>{it.name}</div>
            <ItemImageView src={staticFile(it.image)} name={it.name} />
          </div>
        ))}
      </div>
      <div style={{
        position: "absolute", top: 435, left: "50%", transform: "translate(-50%,-50%)",
        width: 120, height: 120, borderRadius: "50%", background: DIFF.accent, color: "#fff",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 52, fontWeight: 900, fontStyle: "italic", boxShadow: `0 0 50px ${DIFF.accent}66`,
      }}>vs</div>
      <div style={{ position: "absolute", top: 850, left: 0, right: 0, textAlign: "center", fontSize: 82, fontWeight: 900 }}>
        what&#39;s the <span style={{ color: DIFF.accent }}>difference?</span>
      </div>
      <div style={{ position: "absolute", bottom: 120, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `translateY(${bob}px)` }}>
        <Mascot pose="thinking" />
      </div>
    </AbsoluteFill>
  );
};
