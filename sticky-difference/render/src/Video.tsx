import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "./theme";
import { buildTimeline, type Timeline, type SceneKey } from "./timeline";
import { audioCues } from "./audio-cues";
import { Hook } from "./scenes/Hook";
import { Item } from "./scenes/Item";
import { Difference } from "./scenes/Difference";
import { BrandHeaderView } from "./blocks/Pieces";
import type { DiffProps } from "./props";

// Pure frame -> scene-key selector (unit-tested). The cta beat is only reachable when it has a
// non-zero span; otherwise the difference scene holds to the end.
export function activeScene(frame: number, tl: Timeline): SceneKey {
  if (frame >= tl.cta.from && tl.cta.durationInFrames > 0) return "cta";
  if (frame >= tl.difference.from) return "difference";
  if (frame >= tl.itemY.from) return "itemY";
  if (frame >= tl.itemX.from) return "itemX";
  return "hook";
}

export const DifferenceVideo: React.FC<DiffProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tl = buildTimeline(fps, props.vo, !!props.cta);
  const scene = activeScene(frame, tl);
  const [x, y] = props.items;

  // gentle moving highlight, shared across scenes for continuity
  const t = frame / fps;
  const gx = 78 + 8 * Math.sin(t * 0.4);
  const gy = 12 + 6 * Math.cos(t * 0.5);

  return (
    <AbsoluteFill style={{ background: DIFF.bg }}>
      <AbsoluteFill style={{ background: `radial-gradient(circle at ${gx}% ${gy}%, #ffffff, transparent 45%), ${DIFF.bg}` }} />

      {audioCues(props, tl).map((c) => (
        <Sequence key={c.key} from={c.from} name={`vo-${c.key}`}><Audio src={staticFile(c.src)} /></Sequence>
      ))}

      {scene === "hook" && <Hook props={props} from={tl.hook.from} />}
      {scene === "itemX" && <Item item={x} side="left" from={tl.itemX.from} />}
      {scene === "itemY" && <Item item={y} side="right" from={tl.itemY.from} />}
      {(scene === "difference" || scene === "cta") && <Difference props={props} from={tl.difference.from} />}

      {/* persistent masthead across all beats (brand identity, spec 2.3) */}
      <BrandHeaderView brandHandle={props.brandHandle} />
    </AbsoluteFill>
  );
};
