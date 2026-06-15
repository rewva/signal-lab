import type { QuizProps } from "./props";

export type VoScript = { question: string; reveal: string; why: string; bonus: string };

// Generic spoken nudge for the comment-bait scene. It must NEVER answer the bonus question --
// it only tells the viewer to comment, so the comment bait stays intact.
export const BONUS_NUDGE = "But here is a bonus. Do you know this one? Drop your answer in the comments.";

// Derive the narration lines from props. Pure -- no I/O. `bonus` is the (answer-free) nudge,
// present only when the question carries a commentChallenge.
export function voLines(props: QuizProps): VoScript {
  const correct = props.options.find((o) => o.letter === props.correctLetter);
  const answerText = correct ? correct.text : "";
  return {
    question: props.question,
    reveal: `The correct answer is ${props.correctLetter}. ${answerText}.`,
    why: props.explanation,
    bonus: props.commentChallenge ? BONUS_NUDGE : "",
  };
}
