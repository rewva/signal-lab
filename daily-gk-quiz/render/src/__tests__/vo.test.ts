import { describe, it, expect } from "vitest";
import { voLines } from "../vo";
import type { QuizProps } from "../props";

const base: QuizProps = {
  dayNumber: 47, category: "Polity", difficulty: "basic", examPrefix: "SSC",
  template: "standard", question: "Which Article guarantees the Right to Life?",
  options: [
    { letter: "A", text: "Article 19" }, { letter: "B", text: "Article 21" },
    { letter: "C", text: "Article 14" }, { letter: "D", text: "Article 32" },
  ],
  correctLetter: "B", explanation: "Article 21 protects life and personal liberty.",
  sourceLine: "Constitution of India, Art. 21", cta: "Comment A or B", trickHook: "",
};

describe("voLines", () => {
  it("question line is the question text", () => {
    expect(voLines(base).question).toBe("Which Article guarantees the Right to Life?");
  });
  it("reveal names the correct letter and its option text", () => {
    expect(voLines(base).reveal).toBe("The correct answer is B. Article 21.");
  });
  it("why line is the explanation", () => {
    expect(voLines(base).why).toBe("Article 21 protects life and personal liberty.");
  });
  it("empty explanation yields an empty why line", () => {
    expect(voLines({ ...base, explanation: "" }).why).toBe("");
  });
});
