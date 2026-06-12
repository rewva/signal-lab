// Scene start times in seconds (baseline / no-voice timeline). With voice, the three
// narration spans (pre-countdown question+options, reveal, why) expand to fit their VO;
// the quiz-mechanic gaps (countdown, lock, ctaHold) stay fixed.
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

// Baseline gaps (seconds).
const OPTIONS_OFFSET = 0.8;       // options appear within the pre-countdown span
const PRECOUNTDOWN_MIN = 3.3;     // question+options shown before countdown
const COUNTDOWN_GAP = 5.3 - 3.3;  // fixed quiz mechanic
const LOCK_GAP = 6.1 - 5.3;       // fixed
const REVEAL_MIN = 9.0 - 6.1;     // expandable
const WHY_MIN = 11.5 - 9.0;       // expandable
const CTA_HOLD = END_SECONDS - 11.5; // fixed
const TAIL_DEFAULT = 0.45;

export type VoDurations = { question?: number; reveal?: number; why?: number };
export type SceneKey = (typeof SCENES)[number]["key"];
export type Timeline = Record<SceneKey, { from: number; durationInFrames: number }> & {
  totalFrames: number;
};

// Compute a span in frames: max(min, voSec+tail) rounded once. Working in integer frames
// avoids accumulated float drift when segments are summed.
const spanFrames = (minSec: number, fps: number, voSec: number | undefined, tail: number) =>
  voSec
    ? Math.max(Math.round(minSec * fps), Math.round((voSec + tail) * fps))
    : Math.round(minSec * fps);

export function buildTimeline(fps: number, vo?: VoDurations, tail = TAIL_DEFAULT): Timeline {
  // Compute each segment length in integer frames.
  const optionsOffsetF  = Math.round(OPTIONS_OFFSET * fps);
  const preF            = spanFrames(PRECOUNTDOWN_MIN, fps, vo?.question, tail);
  const countdownGapF   = Math.round(COUNTDOWN_GAP * fps);
  const lockGapF        = Math.round(LOCK_GAP * fps);
  const revealSpanF     = spanFrames(REVEAL_MIN, fps, vo?.reveal, tail);
  const whySpanF        = spanFrames(WHY_MIN, fps, vo?.why, tail);
  const ctaHoldF        = Math.round(CTA_HOLD * fps);

  // Build start frames by accumulating integer segments (zero drift).
  const questionFrom  = 0;
  const optionsFrom   = questionFrom  + optionsOffsetF;
  const countdownFrom = questionFrom  + preF;
  const lockFrom      = countdownFrom + countdownGapF;
  const revealFrom    = lockFrom      + lockGapF;
  const whyFrom       = revealFrom    + revealSpanF;
  const ctaFrom       = whyFrom       + whySpanF;
  const totalFrames   = ctaFrom       + ctaHoldF;

  const froms: Record<SceneKey, number> = {
    question: questionFrom,
    options:  optionsFrom,
    countdown: countdownFrom,
    lock:     lockFrom,
    reveal:   revealFrom,
    why:      whyFrom,
    ctaHold:  ctaFrom,
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
