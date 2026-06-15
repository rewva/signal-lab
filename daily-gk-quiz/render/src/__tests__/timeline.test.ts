import { describe, it, expect } from "vitest";
import { buildTimeline, SCENES } from "../timeline";

describe("timeline (no voice -> current fixed timeline)", () => {
  it("reproduces the original frame ranges at 30fps", () => {
    const t = buildTimeline(30);
    expect(t.question.from).toBe(0);
    expect(t.options.from).toBe(Math.round(0.8 * 30));
    expect(t.countdown.from).toBe(Math.round(3.3 * 30));
    expect(t.lock.from).toBe(Math.round(5.3 * 30));
    expect(t.reveal.from).toBe(Math.round(6.1 * 30));
    expect(t.why.from).toBe(Math.round(9.0 * 30));
    expect(t.ctaHold.from).toBe(Math.round(11.5 * 30));
    expect(t.totalFrames).toBe(Math.round(13.0 * 30));
  });
  it("exposes the canonical scene list", () => {
    expect(SCENES.map((s) => s.key)).toEqual(
      ["question", "options", "countdown", "lock", "reveal", "why", "ctaHold"]);
  });
});

describe("timeline (voice-driven beats)", () => {
  const tail = 0.45;
  it("expands the pre-countdown span when the question VO is long", () => {
    const t = buildTimeline(30, { question: 5.0, reveal: 0, why: 0 }, tail);
    expect(t.countdown.from).toBe(Math.round(5.45 * 30));
    expect(t.lock.from).toBe(Math.round((5.45 + 2.0) * 30));
  });
  it("expands reveal and why spans to fit their VO", () => {
    const t = buildTimeline(30, { question: 0, reveal: 4.0, why: 4.0 }, tail);
    const revealDur = t.why.from - t.reveal.from;
    const whyDur = t.ctaHold.from - t.why.from;
    expect(revealDur).toBe(Math.round((4.0 + tail) * 30));
    expect(whyDur).toBe(Math.round((4.0 + tail) * 30));
  });
  it("a short VO never shrinks a beat below its visual minimum", () => {
    const t = buildTimeline(30, { question: 0.5, reveal: 0.5, why: 0.5 }, tail);
    expect(t.countdown.from).toBe(Math.round(3.3 * 30));
    expect(t.why.from - t.reveal.from).toBe(Math.round(2.9 * 30));
  });
  it("expands the ctaHold (bonus) span to fit the bonus nudge VO", () => {
    const t = buildTimeline(30, { question: 0, reveal: 0, why: 0, bonus: 4.0 }, tail);
    const ctaDur = t.totalFrames - t.ctaHold.from;
    expect(ctaDur).toBe(Math.round((4.0 + tail) * 30)); // max(1.5, 4.45) = 4.45
  });
});
