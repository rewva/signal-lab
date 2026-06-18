import { describe, it, expect } from "vitest";
import { activeScene } from "../Video";
import { buildTimeline } from "../timeline";

describe("activeScene", () => {
  it("walks hook -> itemX -> itemY -> difference (no cta)", () => {
    const tl = buildTimeline(30);
    expect(activeScene(0, tl)).toBe("hook");
    expect(activeScene(tl.itemX.from, tl)).toBe("itemX");
    expect(activeScene(tl.itemY.from, tl)).toBe("itemY");
    expect(activeScene(tl.difference.from, tl)).toBe("difference");
    expect(activeScene(tl.totalFrames - 1, tl)).toBe("difference");
  });
  it("enters the cta beat only when a cta span exists", () => {
    const tl = buildTimeline(30, undefined, true);
    expect(activeScene(tl.cta.from, tl)).toBe("cta");
  });
});
