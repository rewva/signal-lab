// Scene start times in seconds (baseline / no-voice, no-cta timeline). With voice, the
// narration spans (hook, itemX, itemY, difference, cta) expand to fit their VO. The cta beat
// only exists when props.cta is present (hasCta); otherwise it collapses to zero frames.
export const SCENES = [
  { key: "hook", start: 0.0 },
  { key: "itemX", start: 3.0 },
  { key: "itemY", start: 6.0 },
  { key: "difference", start: 9.0 },
  { key: "cta", start: 12.5 },
] as const;

const HOOK_MIN = 3.0;
const ITEM_MIN = 3.0;
const DIFF_MIN = 3.5;
const CTA_MIN = 2.0;
const TAIL_DEFAULT = 0.45;

export type VoDurations = {
  hook?: number; itemX?: number; itemY?: number; difference?: number; cta?: number;
};
export type SceneKey = (typeof SCENES)[number]["key"];
export type Timeline = Record<SceneKey, { from: number; durationInFrames: number }> & {
  totalFrames: number;
};

// max(min, voSec+tail) rounded once; integer frames avoid float drift when summed.
const spanFrames = (minSec: number, fps: number, voSec: number | undefined, tail: number) =>
  voSec
    ? Math.max(Math.round(minSec * fps), Math.round((voSec + tail) * fps))
    : Math.round(minSec * fps);

export function buildTimeline(
  fps: number,
  vo?: VoDurations,
  hasCta = false,
  tail = TAIL_DEFAULT,
): Timeline {
  const hookF = spanFrames(HOOK_MIN, fps, vo?.hook, tail);
  const itemXF = spanFrames(ITEM_MIN, fps, vo?.itemX, tail);
  const itemYF = spanFrames(ITEM_MIN, fps, vo?.itemY, tail);
  const diffF = spanFrames(DIFF_MIN, fps, vo?.difference, tail);
  const ctaF = hasCta ? spanFrames(CTA_MIN, fps, vo?.cta, tail) : 0;

  const hookFrom = 0;
  const itemXFrom = hookFrom + hookF;
  const itemYFrom = itemXFrom + itemXF;
  const differenceFrom = itemYFrom + itemYF;
  const ctaFrom = differenceFrom + diffF;
  const totalFrames = ctaFrom + ctaF;

  const froms: Record<SceneKey, number> = {
    hook: hookFrom, itemX: itemXFrom, itemY: itemYFrom, difference: differenceFrom, cta: ctaFrom,
  };
  const keys = SCENES.map((s) => s.key);
  const out = {} as Timeline;
  keys.forEach((k, i) => {
    const nextFrom = i + 1 < keys.length ? froms[keys[i + 1]] : totalFrames;
    out[k] = { from: froms[k], durationInFrames: nextFrom - froms[k] };
  });
  out.totalFrames = totalFrames;
  return out;
}
