import { describe, it, expect } from "vitest";
import { mascotAsset } from "../mascot/asset";
import { POSE_KEYS } from "../mascot/poses";

describe("mascotAsset", () => {
  it("maps every pose to an image file", () => {
    for (const pose of POSE_KEYS) {
      expect(mascotAsset(pose).file).toMatch(/^mascot\/.+\.png$/);
    }
  });
  it("point-right is point-left mirrored (only 3 source images needed)", () => {
    expect(mascotAsset("point-right").file).toBe(mascotAsset("point-left").file);
    expect(mascotAsset("point-right").mirror).toBe(true);
    expect(mascotAsset("point-left").mirror).toBe(false);
  });
  it("non-point poses are not mirrored", () => {
    expect(mascotAsset("thinking").mirror).toBe(false);
    expect(mascotAsset("idea").mirror).toBe(false);
  });
});
