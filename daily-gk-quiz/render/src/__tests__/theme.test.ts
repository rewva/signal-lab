import { describe, it, expect } from "vitest";
import { STANDARD, TRICK, difficultyColor } from "../theme";

describe("theme", () => {
  it("standard palette is the locked duotone", () => {
    expect(STANDARD.bg).toBe("#15123b");
    expect(STANDARD.accent).toBe("#c6f24e");
  });
  it("maps difficulty to Easy/Medium/Hard colours", () => {
    expect(difficultyColor("basic")).toEqual({ label: "Easy", color: "#3ddc84" });
    expect(difficultyColor("intermediate")).toEqual({ label: "Medium", color: "#f4c430" });
    expect(difficultyColor("advanced")).toEqual({ label: "Hard", color: "#ff5a5f" });
  });
});
