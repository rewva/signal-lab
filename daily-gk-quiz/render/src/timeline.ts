// Scene start times in seconds (post-review ~12-14s timeline).
export const SCENES = [
  { key: "question", start: 0.0 },
  { key: "options", start: 0.8 },
  { key: "countdown", start: 3.3 },
  { key: "lock", start: 5.3 },
  { key: "reveal", start: 6.1 },
  { key: "why", start: 9.0 },
  { key: "ctaHold", start: 11.5 },
] as const;

const END_SECONDS = 13.0;

export type SceneKey = (typeof SCENES)[number]["key"];
export type Timeline = Record<SceneKey, { from: number; durationInFrames: number }> & {
  totalFrames: number;
};

export function buildTimeline(fps: number): Timeline {
  const out = {} as Timeline;
  SCENES.forEach((scene, i) => {
    const nextStart = i + 1 < SCENES.length ? SCENES[i + 1].start : END_SECONDS;
    out[scene.key] = {
      from: Math.round(scene.start * fps),
      durationInFrames: Math.round((nextStart - scene.start) * fps),
    };
  });
  out.totalFrames = Math.round(END_SECONDS * fps);
  return out;
}
