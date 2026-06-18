import { describe, it, expect } from "vitest";
import { buildTimeline, SCENES } from "../timeline";

describe("timeline (baseline, no voice, no cta)", () => {
  it("lays out the four beats at 30fps", () => {
    const t = buildTimeline(30);
    expect(t.hook.from).toBe(0);
    expect(t.itemX.from).toBe(Math.round(3.0 * 30));
    expect(t.itemY.from).toBe(Math.round(6.0 * 30));
    expect(t.difference.from).toBe(Math.round(9.0 * 30));
    expect(t.totalFrames).toBe(Math.round(12.5 * 30));
  });
  it("collapses the cta beat when there is no cta", () => {
    const t = buildTimeline(30);
    expect(t.cta.durationInFrames).toBe(0);
    expect(t.cta.from).toBe(t.totalFrames);
  });
  it("exposes the canonical scene list", () => {
    expect(SCENES.map((s) => s.key)).toEqual(["hook", "itemX", "itemY", "difference", "cta"]);
  });
});

describe("timeline (cta + voice)", () => {
  const tail = 0.45;
  it("adds a cta tail when hasCta", () => {
    const t = buildTimeline(30, undefined, true);
    expect(t.cta.durationInFrames).toBe(Math.round(2.0 * 30));
    expect(t.totalFrames).toBe(Math.round((12.5 + 2.0) * 30));
  });
  it("expands a beat to fit its VO, never below the visual minimum", () => {
    const long = buildTimeline(30, { hook: 5.0 }, false, tail);
    expect(long.itemX.from).toBe(Math.round((5.0 + tail) * 30));
    const short = buildTimeline(30, { hook: 0.5 }, false, tail);
    expect(short.itemX.from).toBe(Math.round(3.0 * 30));
  });
  it("expands the difference span for difference VO", () => {
    const t = buildTimeline(30, { difference: 5.0 }, false, tail);
    const diffDur = t.cta.from - t.difference.from;
    expect(diffDur).toBe(Math.round((5.0 + tail) * 30));
  });
});
