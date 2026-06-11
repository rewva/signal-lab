import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CountdownView, LockBeatView, WhyView, VerifiedBadgeView, SourceLineView, CtaView }
  from "../blocks/Pieces";

describe("piece views", () => {
  it("countdown shows the given number", () => {
    render(<CountdownView n={2} />); expect(screen.getByText("2")).toBeTruthy();
  });
  it("lock beat shows the lock text", () => {
    render(<LockBeatView />); expect(screen.getByText(/Lock your answer/i)).toBeTruthy();
  });
  it("why view shows the explanation", () => {
    render(<WhyView explanation="Article 21 protects life." />);
    expect(screen.getByText(/Article 21 protects life/)).toBeTruthy();
  });
  it("verified badge shows VERIFIED", () => {
    render(<VerifiedBadgeView />); expect(screen.getByText(/VERIFIED/i)).toBeTruthy();
  });
  it("source line shows the source, promoted when revealed", () => {
    render(<SourceLineView sourceLine="Constitution, Art. 21" promoted />);
    expect(screen.getByText(/Constitution, Art. 21/)).toBeTruthy();
  });
  it("cta shows the call to action", () => {
    render(<CtaView cta="Comment A or B" />); expect(screen.getByText(/Comment A or B/)).toBeTruthy();
  });
});

it("source line dark tone still shows text", () => {
  render(<SourceLineView sourceLine="X, Art. 21" promoted tone="dark" />);
  expect(screen.getByText(/X, Art. 21/)).toBeTruthy();
});
