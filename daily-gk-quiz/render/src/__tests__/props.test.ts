import { describe, it, expect } from "vitest";
import { quizSchema } from "../props";

const valid = {
  dayNumber: 47, category: "Polity", difficulty: "basic", examPrefix: "SSC",
  template: "standard", question: "Which Article guarantees the Right to Life?",
  options: [
    { letter: "A", text: "Article 19" }, { letter: "B", text: "Article 21" },
    { letter: "C", text: "Article 14" }, { letter: "D", text: "Article 32" },
  ],
  correctLetter: "B", explanation: "Article 21 protects life and personal liberty.",
  sourceLine: "Constitution of India, Art. 21", cta: "Comment A or B",
  trickHook: "Common Exam Trap", fps: 30,
};

describe("quizSchema", () => {
  it("accepts a valid props object", () => {
    expect(quizSchema.parse(valid)).toMatchObject({ correctLetter: "B" });
  });
  it("rejects when options length != 4", () => {
    expect(() => quizSchema.parse({ ...valid, options: valid.options.slice(0, 3) })).toThrow();
  });
  it("rejects an unknown template", () => {
    expect(() => quizSchema.parse({ ...valid, template: "fancy" })).toThrow();
  });
});
