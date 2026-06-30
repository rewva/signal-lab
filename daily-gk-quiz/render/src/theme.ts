// Pakka brand palette (see docs/brand/pakka-identity.md).
// Brand accent (Stamp Vermilion) is intentionally separate from the semantic
// correct-answer green: the brand stamps; the content marks the right answer.
export const STANDARD = {
  bg: "#15233B",          // Exam Ink (primary ground)
  bgDeep: "#0E1828",      // gradient floor
  accent: "#FF5436",      // Stamp Vermilion (brand)
  accentRgb: "255,84,54",
  correct: "#36C26E",     // correct-answer semantic (content, not brand)
  correctRgb: "54,194,110",
  text: "#EEF1F4",        // Paper
  muted: "#9DB0C6",
  pillOutline: "#33425C",
} as const;

export const TRICK = {
  bg: "#fbe6c9",
  ink: "#171410",
  teal: "#16a085",
  red: "#e2402b",
  marigold: "#e9b949",
} as const;

export type Difficulty = "basic" | "intermediate" | "advanced";

const DIFFICULTY = {
  basic: { label: "Easy", color: "#3ddc84" },
  intermediate: { label: "Medium", color: "#f4c430" },
  advanced: { label: "Hard", color: "#ff5a5f" },
} as const;

export function difficultyColor(d: Difficulty) {
  return DIFFICULTY[d];
}
