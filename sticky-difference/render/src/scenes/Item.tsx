import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "../theme";
import { Mascot } from "../mascot/Mascot";
import { ItemImageView } from "../blocks/Pieces";
import type { DiffProps } from "../props";

// Side-by-side item beat: the picture sits on one side and the cat on the other, pointing across
// AT it -- so the left/right gesture has a real target. side="left" => picture left, cat right
// pointing left (item X); side="right" mirrors it (item Y).
export const Item: React.FC<{ item: DiffProps["items"][number]; side: "left" | "right"; from: number }> = ({ item, side, from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - from, fps, config: { damping: 18, stiffness: 110, mass: 0.8 }, durationInFrames: 18 });
  const op = interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" });
  const bob = Math.sin(((frame - from) / fps) * 2.2) * 8;

  const picLeft = side === "left";
  const pose = picLeft ? "point-left" : "point-right";
  // picture slides in from its own edge; cat eases up from below
  const picSlide = interpolate(p, [0, 1], [picLeft ? -90 : 90, 0]);
  const catRise = interpolate(p, [0, 1], [60, 0]);

  return (
    <AbsoluteFill style={{ fontFamily: "Arial, Helvetica, sans-serif", color: DIFF.ink, opacity: op }}>
      <div style={{ position: "absolute", top: 250, left: 0, right: 0, textAlign: "center", fontSize: 100, fontWeight: 900, letterSpacing: "-.02em" }}>
        {item.name}
      </div>

      {/* picture on one side */}
      <div style={{ position: "absolute", top: 620, width: 480, [picLeft ? "left" : "right"]: 64, transform: `translateX(${picSlide}px)` }}>
        <ItemImageView src={staticFile(item.image)} name={item.name} height={540} />
      </div>

      {/* cat on the other side, pointing across at the picture */}
      <div style={{ position: "absolute", top: 660, [picLeft ? "right" : "left"]: 24, transform: `translateY(${bob + catRise}px)` }}>
        <Mascot pose={pose} size={460} />
      </div>

      <div style={{ position: "absolute", top: 1320, left: 80, right: 80, textAlign: "center", fontSize: 50, fontWeight: 700, lineHeight: 1.3 }}>
        {item.trait}
      </div>
    </AbsoluteFill>
  );
};
