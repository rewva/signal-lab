import type { DiffProps } from "./props";
import type { Timeline } from "./timeline";

export type AudioCue = {
  key: "hook" | "itemX" | "itemY" | "difference" | "cta";
  src: string;
  from: number;
};

// Map each present VO line to the frame its scene starts. Pure.
export function audioCues(props: DiffProps, tl: Timeline): AudioCue[] {
  const a = props.audio;
  if (!a) return [];
  const fromFor = {
    hook: tl.hook.from, itemX: tl.itemX.from, itemY: tl.itemY.from,
    difference: tl.difference.from, cta: tl.cta.from,
  };
  const out: AudioCue[] = [];
  (["hook", "itemX", "itemY", "difference", "cta"] as const).forEach((key) => {
    const src = a[key];
    if (src) out.push({ key, src, from: fromFor[key] });
  });
  return out;
}
