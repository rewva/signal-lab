import React from "react";
import { MASCOT_MODE } from "./asset";
import { MascotSvg } from "./MascotSvg";
import { MascotImage } from "./MascotImage";
import type { PoseKey } from "./poses";

// Single entry point for the mascot. Picks the SVG cat or the AI image cat based on MASCOT_MODE,
// keeping a stable {pose, size} API so the scenes never need to change between the two.
export const Mascot: React.FC<{ pose: PoseKey; size?: number }> = (props) =>
  MASCOT_MODE === "image" ? <MascotImage {...props} /> : <MascotSvg {...props} />;
