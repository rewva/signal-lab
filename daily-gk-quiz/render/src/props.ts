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
  fps: z.number().int().positive(),
});

export type QuizProps = z.infer<typeof quizSchema>;
