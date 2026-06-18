import React from "react";
import { Composition } from "remotion";
import { DifferenceVideo } from "./Video";
import { diffSchema, type DiffProps } from "./props";
import { buildTimeline } from "./timeline";

const FPS = 30;

const defaultProps: DiffProps = {
  topic: "Coffin vs Casket",
  items: [
    { name: "Coffin", image: "comparisons/coffin.jpg", trait: "Tapered to the body - six sides, wide at the shoulders." },
    { name: "Casket", image: "comparisons/casket.jpg", trait: "A rectangular box with four sides and a hinged lid." },
  ],
  difference: "A coffin is body-shaped (six-sided); a casket is a rectangular box.",
  cta: "Which did you think was which? Comment below",
  sourceLine: "Merriam-Webster; Britannica",
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Difference"
    component={DifferenceVideo}
    schema={diffSchema}
    defaultProps={defaultProps}
    fps={FPS}
    width={1080}
    height={1920}
    calculateMetadata={({ props }: { props: DiffProps }) => ({
      durationInFrames: buildTimeline(props.fps ?? FPS, props.vo, !!props.cta).totalFrames,
    })}
  />
);
