import React from "react";
import { Composition } from "remotion";
import { Quiz } from "./Quiz";
import { quizSchema, type QuizProps } from "./props";
import { buildTimeline } from "./timeline";

const FPS = 30;

const defaultProps: QuizProps = {
  dayNumber: 47, category: "Polity", difficulty: "basic", examPrefix: "SSC",
  template: "standard", question: "Which Article guarantees the Right to Life?",
  options: [
    { letter: "A", text: "Article 19" }, { letter: "B", text: "Article 21" },
    { letter: "C", text: "Article 14" }, { letter: "D", text: "Article 32" },
  ],
  correctLetter: "B", explanation: "Article 21 protects life and personal liberty.",
  sourceLine: "Constitution of India, Art. 21", cta: "Comment A or B",
  trickHook: "Common Exam Trap", fps: FPS,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Quiz"
    component={Quiz}
    schema={quizSchema}
    defaultProps={defaultProps}
    durationInFrames={buildTimeline(FPS).totalFrames}
    fps={FPS}
    width={1080}
    height={1920}
  />
);
