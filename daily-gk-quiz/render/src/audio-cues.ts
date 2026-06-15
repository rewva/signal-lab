import type { QuizProps } from "./props";
import type { Timeline } from "./timeline";

export type AudioCue = { key: "question" | "reveal" | "why" | "bonus"; src: string; from: number };

// Map present audio lines to the frame their scene starts. Pure. The bonus nudge plays at the
// start of the ctaHold scene (there is no separate "bonus" scene key in the timeline).
export function audioCues(props: QuizProps, tl: Timeline): AudioCue[] {
  const a = props.audio;
  if (!a) return [];
  const fromFor = { question: tl.question.from, reveal: tl.reveal.from, why: tl.why.from, bonus: tl.ctaHold.from };
  const out: AudioCue[] = [];
  (["question", "reveal", "why", "bonus"] as const).forEach((key) => {
    const src = a[key];
    if (src) out.push({ key, src, from: fromFor[key] });
  });
  return out;
}
