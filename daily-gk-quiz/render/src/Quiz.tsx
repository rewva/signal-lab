import React from "react";
import type { QuizProps } from "./props";
import { Standard } from "./templates/Standard";
import { Trick } from "./templates/Trick";

export function pickTemplate(template: "standard" | "trick") {
  return template === "trick" ? Trick : Standard;
}

export const Quiz: React.FC<QuizProps> = (props) => {
  const Template = pickTemplate(props.template);
  return <Template {...props} />;
};
