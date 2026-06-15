import { z } from "zod";

const letter = z.enum(["A", "B", "C", "D"]);

export const quizSchema = z.object({
  dayNumber: z.number().int().positive(),
  category: z.string().min(1),
  difficulty: z.enum(["basic", "intermediate", "advanced"]),
  examPrefix: z.string(),
  template: z.enum(["standard", "trick"]),
  question: z.string().min(1),
  options: z.array(z.object({ letter, text: z.string().min(1) })).length(4),
  correctLetter: letter,
  explanation: z.string().min(1),
  sourceLine: z.string().min(1),
  cta: z.string().min(1),
  trickHook: z.string(),
  vo: z.object({
    question: z.number().nonnegative(),
    reveal: z.number().nonnegative(),
    why: z.number().nonnegative(),
    bonus: z.number().nonnegative().optional(),
  }).optional(),
  audio: z.object({
    question: z.string(),
    reveal: z.string(),
    why: z.string(),
    bonus: z.string(),
  }).partial().optional(),
  commentChallenge: z.string().optional(),  // bonus question shown at the end to bait comments
});

export type QuizProps = z.infer<typeof quizSchema>;
