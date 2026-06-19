import type { PoseKey } from "./poses";

// Mascot source toggle. The procedural SVG cat ("svg") is the default and always works.
// Flip to "image" once the AI-generated cat PNGs are dropped into public/mascot/
// (see public/mascot/README.md for the exact filenames + specs).
export const MASCOT_MODE: "svg" | "image" = "svg";

// Each beat pose maps to one image asset. point-right reuses the point-left art mirrored, so
// only THREE source images are needed: thinking.png, point-left.png, idea.png.
export type MascotAsset = { file: string; mirror: boolean };

export function mascotAsset(pose: PoseKey): MascotAsset {
  switch (pose) {
    case "thinking":    return { file: "mascot/thinking.png",   mirror: false };
    case "point-left":  return { file: "mascot/point-left.png", mirror: false };
    case "point-right": return { file: "mascot/point-left.png", mirror: true };
    case "idea":        return { file: "mascot/idea.png",       mirror: false };
  }
}
