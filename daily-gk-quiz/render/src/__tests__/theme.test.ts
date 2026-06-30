import { describe, it, expect } from "vitest";
import { STANDARD, TRICK, difficultyColor } from "../theme";

describe("theme", () => {
  it("standard palette is the Pakka Exam-Ink + Stamp-Vermilion brand", () => {
    expect(STANDARD.bg).toBe("#15233B");
    expect(STANDARD.accent).toBe("#FF5436");   // brand
    expect(STANDARD.correct).toBe("#36C26E");  // correct-answer semantic, split from brand
  });
  it("maps difficulty to Easy/Medium/Hard colours", () => {
    expect(difficultyColor("basic")).toEqual({ label: "Easy", color: "#3ddc84" });
    expect(difficultyColor("intermediate")).toEqual({ label: "Medium", color: "#f4c430" });
    expect(difficultyColor("advanced")).toEqual({ label: "Hard", color: "#ff5a5f" });
  });
});
