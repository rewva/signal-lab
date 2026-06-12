import { describe, it, expect } from "vitest";
import { audioCues } from "../audio-cues";
import { buildTimeline } from "../timeline";
import type { QuizProps } from "../props";

const tl = buildTimeline(30);
const base = { question: "q", reveal: "r", why: "w" };

function props(audio?: Record<string, string>): QuizProps {
  return {
    dayNumber: 1, category: "Polity", difficulty: "basic", examPrefix: "SSC",
    template: "standard", question: "Q?", options: [
      { letter: "A", text: "a" }, { letter: "B", text: "b" },
      { letter: "C", text: "c" }, { letter: "D", text: "d" }],
    correctLetter: "B", explanation: "e", sourceLine: "s", cta: "c", trickHook: "",
    audio,
  } as QuizProps;
}

describe("audioCues", () => {
  it("returns no cues when there is no audio", () => {
    expect(audioCues(props(undefined), tl)).toEqual([]);
  });
  it("maps each present audio line to its scene start frame", () => {
    const cues = audioCues(props(base), tl);
    expect(cues).toEqual([
      { key: "question", src: "q", from: tl.question.from },
      { key: "reveal", src: "r", from: tl.reveal.from },
      { key: "why", src: "w", from: tl.why.from },
    ]);
  });
  it("omits a missing line", () => {
    const cues = audioCues(props({ question: "q" }), tl);
    expect(cues.map((c) => c.key)).toEqual(["question"]);
  });
});
