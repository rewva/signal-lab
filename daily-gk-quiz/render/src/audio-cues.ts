import type { QuizProps } from "./props";
import type { Timeline } from "./timeline";

export type AudioCue = { key: "question" | "reveal" | "why"; src: string; from: number };

// Map present audio lines to the frame their scene starts. Pure.
export function audioCues(props: QuizProps, tl: Timeline): AudioCue[] {
  const a = props.audio;
  if (!a) return [];
  const out: AudioCue[] = [];
  (["question", "reveal", "why"] as const).forEach((key) => {
    const src = a[key];
    if (src) out.push({ key, src, from: tl[key].from });
  });
  return out;
}
