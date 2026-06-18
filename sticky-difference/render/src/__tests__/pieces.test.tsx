import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrandHeaderView, ItemImageView } from "../blocks/Pieces";

describe("pieces", () => {
  it("brand header renders the masthead", () => {
    render(<BrandHeaderView />);
    expect(screen.getByText("CURIOUS")).toBeTruthy();
  });
  it("brand header shows the handle when present", () => {
    render(<BrandHeaderView brandHandle="@curious" />);
    expect(screen.getByText("@curious")).toBeTruthy();
  });
  it("item image renders an img with the resolved src + alt", () => {
    render(<ItemImageView src="comparisons/coffin.jpg" name="Coffin" />);
    const img = screen.getByAltText("Coffin") as HTMLImageElement;
    expect(img.getAttribute("src")).toBe("comparisons/coffin.jpg");
  });
});
