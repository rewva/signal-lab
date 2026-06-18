import { describe, it, expect } from "vitest";
import { diffSchema } from "../props";

const valid = {
  topic: "Coffin vs Casket",
  items: [
    { name: "Coffin", image: "comparisons/coffin.jpg", trait: "Six-sided, body-shaped." },
    { name: "Casket", image: "comparisons/casket.jpg", trait: "Rectangular box." },
  ],
  difference: "A coffin is body-shaped; a casket is rectangular.",
  cta: "Comment below",
  sourceLine: "Merriam-Webster",
};

describe("diffSchema", () => {
  it("accepts valid props", () => {
    expect(diffSchema.parse(valid)).toMatchObject({ topic: "Coffin vs Casket" });
  });
  it("requires exactly two items", () => {
    expect(() => diffSchema.parse({ ...valid, items: valid.items.slice(0, 1) })).toThrow();
  });
  it("requires a source line", () => {
    const { sourceLine, ...rest } = valid;
    expect(() => diffSchema.parse(rest)).toThrow();
  });
  it("cta is optional", () => {
    const { cta, ...rest } = valid;
    expect(diffSchema.parse(rest).cta).toBeUndefined();
  });
  it("accepts optional vo + audio", () => {
    const parsed = diffSchema.parse({
      ...valid, vo: { hook: 2.0, difference: 3.0 }, audio: { hook: "vo/hook.mp3" },
    });
    expect(parsed.vo?.hook).toBe(2.0);
    expect(parsed.audio?.hook).toBe("vo/hook.mp3");
  });
});
