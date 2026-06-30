import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrandHeaderView, DifficultyChipView, CategoryBandView, DayNumberView } from "../blocks/StaticBlocks";

describe("static block views", () => {
  it("brand header shows wordmark + day", () => {
    render(<BrandHeaderView dayNumber={47} />);
    expect(screen.getByText((_, el) => el?.textContent === "Pakka GK" && el?.tagName === "SPAN")).toBeTruthy();
    expect(screen.getByText("DAY 47")).toBeTruthy();
  });
  it("difficulty chip shows mapped label + exam prefix", () => {
    render(<DifficultyChipView difficulty="advanced" examPrefix="UPSC" />);
    expect(screen.getByText(/UPSC . Hard/)).toBeTruthy();
  });
  it("category band shows the category", () => {
    render(<CategoryBandView category="Polity" />);
    expect(screen.getByText("Polity")).toBeTruthy();
  });
  it("day number renders the number", () => {
    render(<DayNumberView dayNumber={47} />);
    expect(screen.getByText("47")).toBeTruthy();
  });
});
