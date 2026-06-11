import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TrickHookView } from "../templates/Trick";

describe("trick template", () => {
  it("renders the rotated trick hook (not hardcoded)", () => {
    render(<TrickHookView trickHook="Common Exam Trap" />);
    expect(screen.getByText("Common Exam Trap")).toBeTruthy();
  });
});
