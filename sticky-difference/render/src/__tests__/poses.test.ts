import { describe, it, expect } from "vitest";
import { POSES, POSE_KEYS } from "../mascot/poses";

describe("poses", () => {
  it("defines the four beat poses", () => {
    expect([...POSE_KEYS].sort()).toEqual(["idea", "point-left", "point-right", "thinking"]);
  });
  it("only the idea pose sparks", () => {
    expect(POSES.idea.spark).toBe(true);
    expect(POSES.thinking.spark).toBe(false);
  });
  it("point poses gesture to opposite sides of center (x=270)", () => {
    expect(POSES["point-left"].paw.x).toBeLessThan(270);
    expect(POSES["point-right"].paw.x).toBeGreaterThan(270);
  });
});
