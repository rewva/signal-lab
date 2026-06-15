import { describe, it, expect } from "vitest";
import { standardState } from "../templates/Standard";
import { buildTimeline } from "../timeline";

const tl = buildTimeline(30);

describe("standardState (frame -> view state)", () => {
  it("scene A spans question..why (ask + in-place reveal live here)", () => {
    expect(standardState(0, tl).scene).toBe("A");
    expect(standardState(tl.reveal.from + 5, tl).scene).toBe("A");
    expect(standardState(tl.why.from - 1, tl).scene).toBe("A");
  });
  it("scene B is the answer/explanation page (why..ctaHold)", () => {
    expect(standardState(tl.why.from, tl).scene).toBe("B");
    expect(standardState(tl.ctaHold.from - 1, tl).scene).toBe("B");
  });
  it("scene C is the bonus/comment page (ctaHold..end)", () => {
    expect(standardState(tl.ctaHold.from, tl).scene).toBe("C");
    expect(standardState(tl.totalFrames - 1, tl).scene).toBe("C");
  });

  it("not revealed before the reveal beat, revealed after", () => {
    expect(standardState(tl.countdown.from + 1, tl).revealed).toBe(false);
    expect(standardState(tl.reveal.from + 5, tl).revealed).toBe(true);
  });

  it("the timer counts only between countdown.from and reveal.from", () => {
    expect(standardState(tl.countdown.from - 1, tl).counting).toBe(false);
    expect(standardState(tl.countdown.from + 1, tl).counting).toBe(true);
    expect(standardState(tl.reveal.from, tl).counting).toBe(false);
  });
});
