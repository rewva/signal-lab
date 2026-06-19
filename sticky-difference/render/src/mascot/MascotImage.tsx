import React from "react";
import { Img, staticFile } from "remotion";
import { mascotAsset } from "./asset";
import type { PoseKey } from "./poses";

// Image-backed mascot (the AI-generated cat). Same {pose, size} API as the SVG cat so scenes
// don't change. point-right is the point-left art mirrored. `size` is the rendered width; height
// follows the source image's aspect ratio. Scene-level bob / slide / entrance still animate it.
export const MascotImage: React.FC<{ pose: PoseKey; size?: number }> = ({ pose, size = 520 }) => {
  const a = mascotAsset(pose);
  return (
    <Img
      src={staticFile(a.file)}
      style={{ width: size, height: "auto", display: "block", transform: a.mirror ? "scaleX(-1)" : undefined }}
    />
  );
};
