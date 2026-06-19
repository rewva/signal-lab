import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MascotSvg } from "../mascot/MascotSvg";
import { POSE_KEYS } from "../mascot/poses";

describe("MascotSvg", () => {
  it("renders an svg for every pose", () => {
    for (const pose of POSE_KEYS) {
      const { container, unmount } = render(<MascotSvg pose={pose} />);
      expect(container.querySelector("svg")).toBeTruthy();
      unmount();
    }
  });
  it("shows the idea spark (extra <line> marks) only for the idea pose", () => {
    const idea = render(<MascotSvg pose="idea" />);
    expect(idea.container.querySelectorAll("line").length).toBeGreaterThan(0);
    idea.unmount();
    const thinking = render(<MascotSvg pose="thinking" />);
    expect(thinking.container.querySelectorAll("line").length).toBe(0);
  });
});
