export const STANDARD = {
  bg: "#15123b",
  accent: "#c6f24e",
  text: "#f4f1ff",
  muted: "#c2bdec",
  pillOutline: "#4b4780",
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
