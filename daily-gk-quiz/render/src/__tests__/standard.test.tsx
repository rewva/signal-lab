import { describe, it, expect } from "vitest";
import { standardState } from "../templates/Standard";
import { buildTimeline } from "../timeline";

const tl = buildTimeline(30);

describe("standardState (frame -> view state)", () => {
  it("before reveal: not revealed, countdown counts down", () => {
    const s = standardState(tl.countdown.from + 1, tl);
    expect(s.revealed).toBe(false);
    expect([3, 2, 1]).toContain(s.countdownN);
  });
  it("after reveal frame: revealed true", () => {
    const s = standardState(tl.reveal.from + 5, tl);
    expect(s.revealed).toBe(true);
  });
  it("lock window shows the lock beat", () => {
    const s = standardState(tl.lock.from + 1, tl);
    expect(s.showLock).toBe(true);
  });
});
