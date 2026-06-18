import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "../theme";
import { Mascot } from "../mascot/Mascot";
import { ItemImageView } from "../blocks/Pieces";
import type { DiffProps } from "../props";

export const Item: React.FC<{ item: DiffProps["items"][number]; side: "left" | "right"; from: number }> = ({ item, side, from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - from, fps, config: { damping: 18, stiffness: 110, mass: 0.8 }, durationInFrames: 18 });
  const slide = interpolate(p, [0, 1], [80, 0]);
  const op = interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" });
  const bob = Math.sin(((frame - from) / fps) * 2.2) * 8;
  return (
    <AbsoluteFill style={{ fontFamily: "Arial, Helvetica, sans-serif", color: DIFF.ink, opacity: op, transform: `translateX(${slide}px)` }}>
      <div style={{ position: "absolute", top: 200, left: 80, right: 80, display: "flex", flexDirection: "column", alignItems: "center", gap: 34 }}>
        <div style={{ fontSize: 92, fontWeight: 900, letterSpacing: "-.02em" }}>{item.name}</div>
        <div style={{ width: "70%" }}>
          <ItemImageView src={staticFile(item.image)} name={item.name} height={520} />
        </div>
        <div style={{ fontSize: 46, fontWeight: 700, lineHeight: 1.3, textAlign: "center", maxWidth: 760 }}>{item.trait}</div>
      </div>
      <div style={{ position: "absolute", bottom: 110, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `translateY(${bob}px)` }}>
        <Mascot pose={side === "left" ? "point-left" : "point-right"} />
      </div>
    </AbsoluteFill>
  );
};
