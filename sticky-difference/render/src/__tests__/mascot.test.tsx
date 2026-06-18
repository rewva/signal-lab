import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Mascot } from "../mascot/Mascot";
import { POSE_KEYS } from "../mascot/poses";

describe("Mascot", () => {
  it("renders an svg for every pose", () => {
    for (const pose of POSE_KEYS) {
      const { container, unmount } = render(<Mascot pose={pose} />);
      expect(container.querySelector("svg")).toBeTruthy();
      unmount();
    }
  });
  it("shows the idea spark (extra <line> marks) only for the idea pose", () => {
    const idea = render(<Mascot pose="idea" />);
    expect(idea.container.querySelectorAll("line").length).toBeGreaterThan(0);
    idea.unmount();
    const thinking = render(<Mascot pose="thinking" />);
    expect(thinking.container.querySelectorAll("line").length).toBe(0);
  });
});
