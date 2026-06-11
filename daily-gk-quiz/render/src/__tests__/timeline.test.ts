import { describe, it, expect } from "vitest";
import { buildTimeline, SCENES } from "../timeline";

describe("timeline", () => {
  it("converts the default scene seconds to frame ranges at 30fps", () => {
    const t = buildTimeline(30);
    expect(t.question.from).toBe(0);
    expect(t.options.from).toBe(Math.round(0.8 * 30));
    expect(t.lock.from).toBe(Math.round(5.3 * 30));
    expect(t.reveal.from).toBe(Math.round(6.1 * 30));
  });
  it("total duration is ~13s (<= 14s)", () => {
    const t = buildTimeline(30);
    expect(t.totalFrames).toBeLessThanOrEqual(14 * 30);
    expect(t.totalFrames).toBeGreaterThan(11 * 30);
  });
  it("exposes the canonical scene list", () => {
    expect(SCENES.map((s) => s.key)).toEqual(
      ["question", "options", "countdown", "lock", "reveal", "why", "ctaHold"]);
  });
});
