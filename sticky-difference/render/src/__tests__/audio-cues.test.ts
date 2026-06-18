import { describe, it, expect } from "vitest";
import { audioCues } from "../audio-cues";
import { buildTimeline } from "../timeline";
import type { DiffProps } from "../props";

const base: DiffProps = {
  topic: "X vs Y",
  items: [
    { name: "X", image: "a.jpg", trait: "t" },
    { name: "Y", image: "b.jpg", trait: "t" },
  ],
  difference: "d",
  sourceLine: "s",
};

describe("audioCues", () => {
  it("returns [] when there is no audio", () => {
    expect(audioCues(base, buildTimeline(30))).toEqual([]);
  });
  it("maps present audio keys to their scene start frames", () => {
    const tl = buildTimeline(30);
    const cues = audioCues({ ...base, audio: { hook: "vo/hook.mp3", difference: "vo/diff.mp3" } }, tl);
    expect(cues).toEqual([
      { key: "hook", src: "vo/hook.mp3", from: tl.hook.from },
      { key: "difference", src: "vo/diff.mp3", from: tl.difference.from },
    ]);
  });
});
