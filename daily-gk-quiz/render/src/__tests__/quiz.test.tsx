import { describe, it, expect } from "vitest";
import { pickTemplate } from "../Quiz";

describe("pickTemplate", () => {
  it("routes by props.template", () => {
    expect(pickTemplate("standard").name).toMatch(/Standard/);
    expect(pickTemplate("trick").name).toMatch(/Trick/);
  });
});
