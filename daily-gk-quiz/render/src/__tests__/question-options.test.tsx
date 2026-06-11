import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QuestionView, OptionsView } from "../blocks/QuestionOptions";

const opts = [
  { letter: "A" as const, text: "Article 19" }, { letter: "B" as const, text: "Article 21" },
  { letter: "C" as const, text: "Article 14" }, { letter: "D" as const, text: "Article 32" },
];

describe("question + options views", () => {
  it("question view shows the question text", () => {
    render(<QuestionView question="Right to Life?" />);
    expect(screen.getByText("Right to Life?")).toBeTruthy();
  });
  it("asked state marks no option correct", () => {
    render(<OptionsView options={opts} correctLetter="B" revealed={false} />);
    expect(screen.getByTestId("opt-B").getAttribute("data-correct")).toBe("false");
  });
  it("revealed state marks only the correct option", () => {
    render(<OptionsView options={opts} correctLetter="B" revealed={true} />);
    expect(screen.getByTestId("opt-B").getAttribute("data-correct")).toBe("true");
    expect(screen.getByTestId("opt-A").getAttribute("data-correct")).toBe("false");
  });
});
