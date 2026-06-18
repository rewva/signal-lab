import { z } from "zod";

const item = z.object({
  name: z.string().min(1),
  image: z.string().min(1),   // filename under public/comparisons/
  trait: z.string().min(1),
});

export const diffSchema = z.object({
  topic: z.string().min(1),
  items: z.array(item).length(2),
  difference: z.string().min(1),
  cta: z.string().min(1).optional(),
  sourceLine: z.string().min(1),
  brandHandle: z.string().optional(),
  fps: z.number().int().positive().optional(),
  vo: z.object({
    hook: z.number().nonnegative(),
    itemX: z.number().nonnegative(),
    itemY: z.number().nonnegative(),
    difference: z.number().nonnegative(),
    cta: z.number().nonnegative(),
  }).partial().optional(),
  audio: z.object({
    hook: z.string(),
    itemX: z.string(),
    itemY: z.string(),
    difference: z.string(),
    cta: z.string(),
  }).partial().optional(),
});

export type DiffProps = z.infer<typeof diffSchema>;
