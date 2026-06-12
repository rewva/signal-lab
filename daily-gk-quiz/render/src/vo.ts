import type { QuizProps } from "./props";

export type VoScript = { question: string; reveal: string; why: string };

// Derive the three narration lines from props. Pure -- no I/O.
export function voLines(props: QuizProps): VoScript {
  const correct = props.options.find((o) => o.letter === props.correctLetter);
  const answerText = correct ? correct.text : "";
  return {
    question: props.question,
    reveal: `The correct answer is ${props.correctLetter}. ${answerText}.`,
    why: props.explanation,
  };
}
