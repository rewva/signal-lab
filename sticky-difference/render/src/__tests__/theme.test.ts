import { describe, it, expect } from "vitest";
import { DIFF } from "../theme";

describe("DIFF theme", () => {
  it("locks the Curious palette tokens", () => {
    expect(DIFF.bg).toBe("#e6f6ef");
    expect(DIFF.accent).toBe("#ff6b6b");
    expect(DIFF.ink).toBe("#16241f");
  });
  it("exposes mascot colors", () => {
    expect(DIFF.fur).toBe("#9aa7b2");
    expect(DIFF.outline).toBe("#16241f");
  });
});
