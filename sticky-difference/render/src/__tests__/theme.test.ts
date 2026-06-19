import { describe, it, expect } from "vitest";
import { DIFF } from "../theme";

describe("DIFF theme", () => {
  it("locks the Curious palette tokens (soft-pastel)", () => {
    expect(DIFF.bg).toBe("#efeafd");
    expect(DIFF.accent).toBe("#7c5cf0");
    expect(DIFF.ink).toBe("#241f33");
  });
  it("exposes mascot colors", () => {
    expect(DIFF.fur).toBe("#b9b3d6");
    expect(DIFF.outline).toBe("#241f33");
  });
});
