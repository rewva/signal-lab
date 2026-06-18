# Sticky-Difference Render Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained Remotion project that renders one "X vs Y -- what's the difference?" pair into a 1080x1920 MP4, with an original procedural Cat mascot.

**Architecture:** Fresh Remotion project in `sticky-difference/render/`, patterns ported from `daily-gk-quiz/render` (no runtime dependency). Pure functions (timeline math, pose data, prop schema, scene selection, audio mapping) are unit-tested; React scenes that use Remotion hooks are composed by a root component and exercised via the render CLI. Flow: Hook -> Item X -> Item Y -> Difference (+ optional CTA).

**Tech Stack:** Remotion 4.0.290, React 18.3.1, TypeScript 5.6.3, Zod 3.23.8, Vitest 2.1.8 (jsdom), @testing-library/react.

**Branch:** Work on `sticky-difference-template` (already created; the design doc is committed there).

**Spec:** `docs/specs/2026-06-18-sticky-difference-template-design.md`

---

## File structure

```
sticky-difference/render/
  package.json            scripts + pinned deps (Task 1)
  tsconfig.json           (Task 1)
  vitest.config.ts        (Task 1)
  .gitignore              node_modules, out, public/vo (Task 1)
  render.mjs              CLI: props.json -> out/<name>.mp4 (Task 11)
  sample-props.json       hand-authored example props (Task 11)
  public/comparisons/     operator drops item images here (Task 11)
  src/
    theme.ts              DIFF palette tokens (Task 2)
    timeline.ts           SCENES + buildTimeline (Task 3)
    props.ts              diffSchema + DiffProps (Task 4)
    audio-cues.ts         VO seam: audio keys -> scene start frames (Task 8)
    mascot/
      poses.ts            POSES pose data + PoseKey (Task 5)
      Mascot.tsx          pure SVG cat, pose-driven (Task 6)
    blocks/
      Pieces.tsx          BrandHeaderView, ItemImageView (Task 7)
    scenes/
      Hook.tsx            (Task 9)
      Item.tsx            (Task 9)
      Difference.tsx      (Task 9)
    Video.tsx             activeScene() + DifferenceVideo root component (Task 10)
    Root.tsx              Remotion <Composition id="Difference"> (Task 10)
    index.ts              registerRoot (Task 10)
    __tests__/
      theme.test.ts       (Task 2)
      timeline.test.ts    (Task 3)
      props.test.ts       (Task 4)
      poses.test.ts       (Task 5)
      mascot.test.tsx     (Task 6)
      pieces.test.tsx     (Task 7)
      audio-cues.test.ts  (Task 8)
      video.test.ts       (Task 10)
```

---

### Task 1: Scaffold the Remotion project

**Files:**
- Create: `sticky-difference/render/package.json`
- Create: `sticky-difference/render/tsconfig.json`
- Create: `sticky-difference/render/vitest.config.ts`
- Create: `sticky-difference/render/.gitignore`

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "sticky-difference-render",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest run",
    "render": "node render.mjs",
    "studio": "remotion studio"
  },
  "dependencies": {
    "@remotion/bundler": "4.0.290",
    "@remotion/cli": "4.0.290",
    "@remotion/renderer": "4.0.290",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "remotion": "4.0.290",
    "zod": "3.23.8"
  },
  "devDependencies": {
    "@testing-library/dom": "10.4.0",
    "@testing-library/react": "16.0.1",
    "@types/react": "18.3.12",
    "jsdom": "25.0.1",
    "typescript": "5.6.3",
    "vitest": "2.1.8"
  }
}
```

- [ ] **Step 2: Create `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "types": ["vitest/globals"]
  },
  "include": ["src", "render.mjs"]
}
```

- [ ] **Step 3: Create `vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: { globals: true, environment: "jsdom" },
});
```

- [ ] **Step 4: Create `.gitignore`**

```
node_modules
out
public/vo
```

- [ ] **Step 5: Install dependencies**

Run (from `sticky-difference/render/`): `npm install`
Expected: completes; `node_modules/` created. (First run downloads the Remotion Chromium headless shell -- may take a minute.)

- [ ] **Step 6: Verify the toolchain resolves**

Run: `npm ls remotion`
Expected: prints `remotion@4.0.290` (no "missing" / "UNMET DEPENDENCY").

- [ ] **Step 7: Commit**

```bash
git add sticky-difference/render/package.json sticky-difference/render/tsconfig.json sticky-difference/render/vitest.config.ts sticky-difference/render/.gitignore sticky-difference/render/package-lock.json
git commit -m "chore(sticky-difference): scaffold Remotion render project"
```

---

### Task 2: Theme tokens (TDD)

**Files:**
- Create: `sticky-difference/render/src/theme.ts`
- Test: `sticky-difference/render/src/__tests__/theme.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { DIFF } from "../theme";

describe("DIFF theme", () => {
  it("locks the Curious palette tokens", () => {
    expect(DIFF.bg).toBe("#e6f6ef");
    expect(DIFF.accent).toBe("#ff6b6b");
    expect(DIFF.ink).toBe("#16241f");
  });
  it("exposes mascot colors", () => {
    expect(DIFF.fur).toBe("#9aa7b2");
    expect(DIFF.outline).toBe("#16241f");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- theme`
Expected: FAIL ("Cannot find module '../theme'").

- [ ] **Step 3: Write the implementation**

```ts
export const DIFF = {
  bg: "#e6f6ef",
  ink: "#16241f",
  accent: "#ff6b6b",
  frame: "#ffffff",
  frameLine: "#ff6b6b",
  muted: "#9fb6ac",
  // mascot
  fur: "#9aa7b2",
  belly: "#ffffff",
  innerEar: "#ff9eb0",
  nose: "#ff6b6b",
  outline: "#16241f",
} as const;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- theme`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add sticky-difference/render/src/theme.ts sticky-difference/render/src/__tests__/theme.test.ts
git commit -m "feat(sticky-difference): DIFF theme tokens (Curious palette)"
```

---

### Task 3: Timeline (TDD)

**Files:**
- Create: `sticky-difference/render/src/timeline.ts`
- Test: `sticky-difference/render/src/__tests__/timeline.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { buildTimeline, SCENES } from "../timeline";

describe("timeline (baseline, no voice, no cta)", () => {
  it("lays out the four beats at 30fps", () => {
    const t = buildTimeline(30);
    expect(t.hook.from).toBe(0);
    expect(t.itemX.from).toBe(Math.round(3.0 * 30));
    expect(t.itemY.from).toBe(Math.round(6.0 * 30));
    expect(t.difference.from).toBe(Math.round(9.0 * 30));
    expect(t.totalFrames).toBe(Math.round(12.5 * 30));
  });
  it("collapses the cta beat when there is no cta", () => {
    const t = buildTimeline(30);
    expect(t.cta.durationInFrames).toBe(0);
    expect(t.cta.from).toBe(t.totalFrames);
  });
  it("exposes the canonical scene list", () => {
    expect(SCENES.map((s) => s.key)).toEqual(["hook", "itemX", "itemY", "difference", "cta"]);
  });
});

describe("timeline (cta + voice)", () => {
  const tail = 0.45;
  it("adds a cta tail when hasCta", () => {
    const t = buildTimeline(30, undefined, true);
    expect(t.cta.durationInFrames).toBe(Math.round(2.0 * 30));
    expect(t.totalFrames).toBe(Math.round((12.5 + 2.0) * 30));
  });
  it("expands a beat to fit its VO, never below the visual minimum", () => {
    const long = buildTimeline(30, { hook: 5.0 }, false, tail);
    expect(long.itemX.from).toBe(Math.round((5.0 + tail) * 30));
    const short = buildTimeline(30, { hook: 0.5 }, false, tail);
    expect(short.itemX.from).toBe(Math.round(3.0 * 30));
  });
  it("expands the difference span for difference VO", () => {
    const t = buildTimeline(30, { difference: 5.0 }, false, tail);
    const diffDur = t.cta.from - t.difference.from;
    expect(diffDur).toBe(Math.round((5.0 + tail) * 30));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- timeline`
Expected: FAIL ("Cannot find module '../timeline'").

- [ ] **Step 3: Write the implementation**

```ts
// Scene start times in seconds (baseline / no-voice, no-cta timeline). With voice, the
// narration spans (hook, itemX, itemY, difference, cta) expand to fit their VO. The cta beat
// only exists when props.cta is present (hasCta); otherwise it collapses to zero frames.
export const SCENES = [
  { key: "hook", start: 0.0 },
  { key: "itemX", start: 3.0 },
  { key: "itemY", start: 6.0 },
  { key: "difference", start: 9.0 },
  { key: "cta", start: 12.5 },
] as const;

const HOOK_MIN = 3.0;
const ITEM_MIN = 3.0;
const DIFF_MIN = 3.5;
const CTA_MIN = 2.0;
const TAIL_DEFAULT = 0.45;

export type VoDurations = {
  hook?: number; itemX?: number; itemY?: number; difference?: number; cta?: number;
};
export type SceneKey = (typeof SCENES)[number]["key"];
export type Timeline = Record<SceneKey, { from: number; durationInFrames: number }> & {
  totalFrames: number;
};

// max(min, voSec+tail) rounded once; integer frames avoid float drift when summed.
const spanFrames = (minSec: number, fps: number, voSec: number | undefined, tail: number) =>
  voSec
    ? Math.max(Math.round(minSec * fps), Math.round((voSec + tail) * fps))
    : Math.round(minSec * fps);

export function buildTimeline(
  fps: number,
  vo?: VoDurations,
  hasCta = false,
  tail = TAIL_DEFAULT,
): Timeline {
  const hookF = spanFrames(HOOK_MIN, fps, vo?.hook, tail);
  const itemXF = spanFrames(ITEM_MIN, fps, vo?.itemX, tail);
  const itemYF = spanFrames(ITEM_MIN, fps, vo?.itemY, tail);
  const diffF = spanFrames(DIFF_MIN, fps, vo?.difference, tail);
  const ctaF = hasCta ? spanFrames(CTA_MIN, fps, vo?.cta, tail) : 0;

  const hookFrom = 0;
  const itemXFrom = hookFrom + hookF;
  const itemYFrom = itemXFrom + itemXF;
  const differenceFrom = itemYFrom + itemYF;
  const ctaFrom = differenceFrom + diffF;
  const totalFrames = ctaFrom + ctaF;

  const froms: Record<SceneKey, number> = {
    hook: hookFrom, itemX: itemXFrom, itemY: itemYFrom, difference: differenceFrom, cta: ctaFrom,
  };
  const keys = SCENES.map((s) => s.key);
  const out = {} as Timeline;
  keys.forEach((k, i) => {
    const nextFrom = i + 1 < keys.length ? froms[keys[i + 1]] : totalFrames;
    out[k] = { from: froms[k], durationInFrames: nextFrom - froms[k] };
  });
  out.totalFrames = totalFrames;
  return out;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- timeline`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add sticky-difference/render/src/timeline.ts sticky-difference/render/src/__tests__/timeline.test.ts
git commit -m "feat(sticky-difference): scene timeline (hook->X->Y->difference+optional cta)"
```

---

### Task 4: Props schema (TDD)

**Files:**
- Create: `sticky-difference/render/src/props.ts`
- Test: `sticky-difference/render/src/__tests__/props.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { diffSchema } from "../props";

const valid = {
  topic: "Coffin vs Casket",
  items: [
    { name: "Coffin", image: "comparisons/coffin.jpg", trait: "Six-sided, body-shaped." },
    { name: "Casket", image: "comparisons/casket.jpg", trait: "Rectangular box." },
  ],
  difference: "A coffin is body-shaped; a casket is rectangular.",
  cta: "Comment below",
  sourceLine: "Merriam-Webster",
};

describe("diffSchema", () => {
  it("accepts valid props", () => {
    expect(diffSchema.parse(valid)).toMatchObject({ topic: "Coffin vs Casket" });
  });
  it("requires exactly two items", () => {
    expect(() => diffSchema.parse({ ...valid, items: valid.items.slice(0, 1) })).toThrow();
  });
  it("requires a source line", () => {
    const { sourceLine, ...rest } = valid;
    expect(() => diffSchema.parse(rest)).toThrow();
  });
  it("cta is optional", () => {
    const { cta, ...rest } = valid;
    expect(diffSchema.parse(rest).cta).toBeUndefined();
  });
  it("accepts optional vo + audio", () => {
    const parsed = diffSchema.parse({
      ...valid, vo: { hook: 2.0, difference: 3.0 }, audio: { hook: "vo/hook.mp3" },
    });
    expect(parsed.vo?.hook).toBe(2.0);
    expect(parsed.audio?.hook).toBe("vo/hook.mp3");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- props`
Expected: FAIL ("Cannot find module '../props'").

- [ ] **Step 3: Write the implementation**

```ts
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- props`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add sticky-difference/render/src/props.ts sticky-difference/render/src/__tests__/props.test.ts
git commit -m "feat(sticky-difference): zod props schema (X/Y pair, difference, optional cta + vo seam)"
```

---

### Task 5: Mascot poses (TDD)

**Files:**
- Create: `sticky-difference/render/src/mascot/poses.ts`
- Test: `sticky-difference/render/src/__tests__/poses.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { POSES, POSE_KEYS } from "../mascot/poses";

describe("poses", () => {
  it("defines the four beat poses", () => {
    expect([...POSE_KEYS].sort()).toEqual(["idea", "point-left", "point-right", "thinking"]);
  });
  it("only the idea pose sparks", () => {
    expect(POSES.idea.spark).toBe(true);
    expect(POSES.thinking.spark).toBe(false);
  });
  it("point poses gesture to opposite sides of center (x=270)", () => {
    expect(POSES["point-left"].paw.x).toBeLessThan(270);
    expect(POSES["point-right"].paw.x).toBeGreaterThan(270);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- poses`
Expected: FAIL ("Cannot find module '../mascot/poses'").

- [ ] **Step 3: Write the implementation**

```ts
export type PoseKey = "thinking" | "point-left" | "point-right" | "idea";

export type Pose = {
  paw: { x: number; y: number }; // gesture-paw tip in the 540x640 viewBox
  earTilt: number;               // degrees; ears perk for 'idea'
  spark: boolean;                // show the idea spark over the head
  mouth: "hmm" | "smile";
};

export const POSES: Record<PoseKey, Pose> = {
  thinking:      { paw: { x: 360, y: 318 }, earTilt: 0,  spark: false, mouth: "hmm" },
  "point-left":  { paw: { x: 120, y: 360 }, earTilt: 0,  spark: false, mouth: "smile" },
  "point-right": { paw: { x: 420, y: 360 }, earTilt: 0,  spark: false, mouth: "smile" },
  idea:          { paw: { x: 360, y: 300 }, earTilt: -8, spark: true,  mouth: "smile" },
};

export const POSE_KEYS = Object.keys(POSES) as PoseKey[];
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- poses`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add sticky-difference/render/src/mascot/poses.ts sticky-difference/render/src/__tests__/poses.test.ts
git commit -m "feat(sticky-difference): mascot pose data (thinking/point/idea)"
```

---

### Task 6: Mascot component (TDD)

**Files:**
- Create: `sticky-difference/render/src/mascot/Mascot.tsx`
- Test: `sticky-difference/render/src/__tests__/mascot.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Mascot } from "../mascot/Mascot";
import { POSE_KEYS } from "../mascot/poses";

describe("Mascot", () => {
  it("renders an svg for every pose", () => {
    for (const pose of POSE_KEYS) {
      const { container, unmount } = render(<Mascot pose={pose} />);
      expect(container.querySelector("svg")).toBeTruthy();
      unmount();
    }
  });
  it("shows the idea spark (extra <line> marks) only for the idea pose", () => {
    const idea = render(<Mascot pose="idea" />);
    expect(idea.container.querySelectorAll("line").length).toBeGreaterThan(0);
    idea.unmount();
    const thinking = render(<Mascot pose="thinking" />);
    expect(thinking.container.querySelectorAll("line").length).toBe(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- mascot`
Expected: FAIL ("Cannot find module '../mascot/Mascot'").

- [ ] **Step 3: Write the implementation**

```tsx
import React from "react";
import { DIFF } from "../theme";
import { POSES, type PoseKey } from "./poses";

// Pure presentational SVG cat. Geometry is constant except the gesture paw, ear tilt, mouth,
// and the optional idea spark, which come from POSES[pose]. Idle bob / blink are applied by the
// parent scene via a wrapping transform, so this stays hook-free and unit-testable.
export const Mascot: React.FC<{ pose: PoseKey; size?: number }> = ({ pose, size = 520 }) => {
  const p = POSES[pose];
  const mouth = p.mouth === "smile" ? "M232 262 q18 14 36 0" : "M236 264 q16 8 28 0";
  const out = DIFF.outline;
  return (
    <svg width={size} height={size * (640 / 540)} viewBox="0 0 540 640" role="img" aria-label={`cat ${pose}`}>
      {/* tail */}
      <path d="M392 470 q120 20 70 -120 q-30 70 -86 84 q-28 14 16 36 z" fill={DIFF.fur} stroke={out} strokeWidth={12} />
      {/* body + belly */}
      <ellipse cx={250} cy={410} rx={140} ry={150} fill={DIFF.fur} stroke={out} strokeWidth={12} />
      <ellipse cx={250} cy={450} rx={80} ry={100} fill={DIFF.belly} stroke={out} strokeWidth={10} />
      {/* ears (tilt for idea) */}
      <g transform={`rotate(${p.earTilt} 250 120)`}>
        <path d="M150 170 l-6 -96 l84 56 z" fill={DIFF.fur} stroke={out} strokeWidth={12} />
        <path d="M350 170 l6 -96 l-84 56 z" fill={DIFF.fur} stroke={out} strokeWidth={12} />
        <path d="M165 150 l-2 -54 l50 34 z" fill={DIFF.innerEar} />
        <path d="M335 150 l2 -54 l-50 34 z" fill={DIFF.innerEar} />
      </g>
      {/* head */}
      <circle cx={250} cy={215} r={128} fill={DIFF.fur} stroke={out} strokeWidth={12} />
      {/* eyes */}
      <circle cx={205} cy={205} r={16} fill={out} />
      <circle cx={295} cy={205} r={16} fill={out} />
      <circle cx={211} cy={199} r={5} fill="#fff" />
      <circle cx={301} cy={199} r={5} fill="#fff" />
      {/* nose + mouth */}
      <path d="M250 248 l-16 -14 l32 0 z" fill={DIFF.nose} stroke={out} strokeWidth={5} />
      <path d={mouth} fill="none" stroke={out} strokeWidth={6} strokeLinecap="round" />
      {/* whiskers (paths, never lines) */}
      <path d="M196 250 L110 236" stroke={out} strokeWidth={6} strokeLinecap="round" />
      <path d="M196 264 L112 272" stroke={out} strokeWidth={6} strokeLinecap="round" />
      <path d="M304 250 L390 236" stroke={out} strokeWidth={6} strokeLinecap="round" />
      <path d="M304 264 L388 272" stroke={out} strokeWidth={6} strokeLinecap="round" />
      {/* feet */}
      <ellipse cx={208} cy={548} rx={40} ry={24} fill={DIFF.fur} stroke={out} strokeWidth={8} />
      <ellipse cx={300} cy={548} rx={40} ry={24} fill={DIFF.fur} stroke={out} strokeWidth={8} />
      {/* gesture paw (pose-driven) */}
      <ellipse cx={p.paw.x} cy={p.paw.y} rx={32} ry={26} fill={DIFF.fur} stroke={out} strokeWidth={8} />
      {/* idea spark (the only <line> elements) */}
      {p.spark && (
        <g stroke={DIFF.accent} strokeWidth={10} strokeLinecap="round">
          <line x1={250} y1={40} x2={250} y2={10} />
          <line x1={300} y1={55} x2={322} y2={33} />
          <line x1={200} y1={55} x2={178} y2={33} />
        </g>
      )}
    </svg>
  );
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- mascot`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add sticky-difference/render/src/mascot/Mascot.tsx sticky-difference/render/src/__tests__/mascot.test.tsx
git commit -m "feat(sticky-difference): procedural SVG cat mascot (pose-driven)"
```

---

### Task 7: Static view blocks (TDD)

**Files:**
- Create: `sticky-difference/render/src/blocks/Pieces.tsx`
- Test: `sticky-difference/render/src/__tests__/pieces.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrandHeaderView, ItemImageView } from "../blocks/Pieces";

describe("pieces", () => {
  it("brand header renders the masthead", () => {
    render(<BrandHeaderView />);
    expect(screen.getByText("CURIOUS")).toBeTruthy();
  });
  it("brand header shows the handle when present", () => {
    render(<BrandHeaderView brandHandle="@curious" />);
    expect(screen.getByText("@curious")).toBeTruthy();
  });
  it("item image renders an img with the resolved src + alt", () => {
    render(<ItemImageView src="comparisons/coffin.jpg" name="Coffin" />);
    const img = screen.getByAltText("Coffin") as HTMLImageElement;
    expect(img.getAttribute("src")).toBe("comparisons/coffin.jpg");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- pieces`
Expected: FAIL ("Cannot find module '../blocks/Pieces'").

- [ ] **Step 3: Write the implementation**

```tsx
import React from "react";
import { DIFF } from "../theme";

// Masthead. Brand name is a v1 placeholder ("CURIOUS") -- final name TBD per the spec.
export const BrandHeaderView: React.FC<{ brandHandle?: string }> = ({ brandHandle }) => (
  <div style={{ position: "absolute", top: 60, left: 0, right: 0, textAlign: "center" }}>
    <span style={{ fontSize: 32, fontWeight: 900, letterSpacing: ".30em", color: DIFF.accent }}>CURIOUS</span>
    {brandHandle ? (
      <span style={{ marginLeft: 18, fontSize: 26, fontWeight: 700, color: DIFF.muted }}>{brandHandle}</span>
    ) : null}
  </div>
);

// Rounded, coral-outlined image card. `src` is already resolved (the scene calls staticFile),
// keeping this component pure and testable outside the Remotion bundler.
export const ItemImageView: React.FC<{ src: string; name: string; height?: number }> = ({ src, name, height = 430 }) => (
  <div style={{
    width: "100%", height, borderRadius: 30, background: DIFF.frame,
    border: `4px solid ${DIFF.frameLine}`, boxShadow: "0 24px 60px rgba(0,0,0,.18)",
    overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center",
  }}>
    <img src={src} alt={name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
  </div>
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- pieces`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add sticky-difference/render/src/blocks/Pieces.tsx sticky-difference/render/src/__tests__/pieces.test.tsx
git commit -m "feat(sticky-difference): brand header + item image view blocks"
```

---

### Task 8: Audio cues / VO seam (TDD)

**Files:**
- Create: `sticky-difference/render/src/audio-cues.ts`
- Test: `sticky-difference/render/src/__tests__/audio-cues.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- audio-cues`
Expected: FAIL ("Cannot find module '../audio-cues'").

- [ ] **Step 3: Write the implementation**

```ts
import type { DiffProps } from "./props";
import type { Timeline } from "./timeline";

export type AudioCue = {
  key: "hook" | "itemX" | "itemY" | "difference" | "cta";
  src: string;
  from: number;
};

// Map each present VO line to the frame its scene starts. Pure.
export function audioCues(props: DiffProps, tl: Timeline): AudioCue[] {
  const a = props.audio;
  if (!a) return [];
  const fromFor = {
    hook: tl.hook.from, itemX: tl.itemX.from, itemY: tl.itemY.from,
    difference: tl.difference.from, cta: tl.cta.from,
  };
  const out: AudioCue[] = [];
  (["hook", "itemX", "itemY", "difference", "cta"] as const).forEach((key) => {
    const src = a[key];
    if (src) out.push({ key, src, from: fromFor[key] });
  });
  return out;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- audio-cues`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add sticky-difference/render/src/audio-cues.ts sticky-difference/render/src/__tests__/audio-cues.test.ts
git commit -m "feat(sticky-difference): VO audio-cue seam (audio keys -> scene frames)"
```

---

### Task 9: Scene components (Hook / Item / Difference)

These compose the views above and use Remotion hooks for entrance animation. They are exercised
by the render CLI in Task 11 (not render-tested, matching the GK render pattern). Write all three,
then verify they typecheck.

**Files:**
- Create: `sticky-difference/render/src/scenes/Hook.tsx`
- Create: `sticky-difference/render/src/scenes/Item.tsx`
- Create: `sticky-difference/render/src/scenes/Difference.tsx`

- [ ] **Step 1: Create `scenes/Hook.tsx`**

```tsx
import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "../theme";
import { Mascot } from "../mascot/Mascot";
import { ItemImageView } from "../blocks/Pieces";
import type { DiffProps } from "../props";

export const Hook: React.FC<{ props: DiffProps; from: number }> = ({ props, from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = (i: number) => {
    const p = spring({ frame: frame - from - i * 4, fps, config: { damping: 16, mass: 0.8 }, durationInFrames: 16 });
    return {
      opacity: interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" }),
      transform: `translateY(${interpolate(p, [0, 1], [40, 0])}px)`,
    };
  };
  const bob = Math.sin(((frame - from) / fps) * 2.2) * 8;
  const [x, y] = props.items;
  return (
    <AbsoluteFill style={{ fontFamily: "Arial, Helvetica, sans-serif", color: DIFF.ink }}>
      <div style={{ position: "absolute", top: 220, left: 60, right: 60, display: "flex", gap: 40 }}>
        {[x, y].map((it, i) => (
          <div key={it.name} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 26, ...enter(i) }}>
            <div style={{ fontSize: 80, fontWeight: 900, letterSpacing: "-.02em" }}>{it.name}</div>
            <ItemImageView src={staticFile(it.image)} name={it.name} />
          </div>
        ))}
      </div>
      <div style={{
        position: "absolute", top: 435, left: "50%", transform: "translate(-50%,-50%)",
        width: 120, height: 120, borderRadius: "50%", background: DIFF.accent, color: "#fff",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 52, fontWeight: 900, fontStyle: "italic", boxShadow: `0 0 50px ${DIFF.accent}66`,
      }}>vs</div>
      <div style={{ position: "absolute", top: 850, left: 0, right: 0, textAlign: "center", fontSize: 82, fontWeight: 900 }}>
        what&#39;s the <span style={{ color: DIFF.accent }}>difference?</span>
      </div>
      <div style={{ position: "absolute", bottom: 120, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `translateY(${bob}px)` }}>
        <Mascot pose="thinking" />
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Create `scenes/Item.tsx`**

```tsx
import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "../theme";
import { Mascot } from "../mascot/Mascot";
import { ItemImageView } from "../blocks/Pieces";
import type { DiffProps } from "../props";

export const Item: React.FC<{ item: DiffProps["items"][number]; side: "left" | "right"; from: number }> = ({ item, side, from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - from, fps, config: { damping: 18, stiffness: 110, mass: 0.8 }, durationInFrames: 18 });
  const slide = interpolate(p, [0, 1], [80, 0]);
  const op = interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" });
  const bob = Math.sin(((frame - from) / fps) * 2.2) * 8;
  return (
    <AbsoluteFill style={{ fontFamily: "Arial, Helvetica, sans-serif", color: DIFF.ink, opacity: op, transform: `translateX(${slide}px)` }}>
      <div style={{ position: "absolute", top: 200, left: 80, right: 80, display: "flex", flexDirection: "column", alignItems: "center", gap: 34 }}>
        <div style={{ fontSize: 92, fontWeight: 900, letterSpacing: "-.02em" }}>{item.name}</div>
        <div style={{ width: "70%" }}>
          <ItemImageView src={staticFile(item.image)} name={item.name} height={520} />
        </div>
        <div style={{ fontSize: 46, fontWeight: 700, lineHeight: 1.3, textAlign: "center", maxWidth: 760 }}>{item.trait}</div>
      </div>
      <div style={{ position: "absolute", bottom: 110, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `translateY(${bob}px)` }}>
        <Mascot pose={side === "left" ? "point-left" : "point-right"} />
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: Create `scenes/Difference.tsx`**

```tsx
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "../theme";
import { Mascot } from "../mascot/Mascot";
import type { DiffProps } from "../props";

export const Difference: React.FC<{ props: DiffProps; from: number }> = ({ props, from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - from, fps, config: { damping: 14, stiffness: 120, mass: 0.8 }, durationInFrames: 20 });
  const scale = interpolate(p, [0, 1], [0.85, 1]);
  const op = interpolate(p, [0, 1], [0, 1], { extrapolateRight: "clamp" });
  const bob = Math.sin(((frame - from) / fps) * 2.2) * 8;
  return (
    <AbsoluteFill style={{ fontFamily: "Arial, Helvetica, sans-serif", color: DIFF.ink }}>
      <div style={{ position: "absolute", top: 230, left: 70, right: 70, textAlign: "center", opacity: op, transform: `scale(${scale})` }}>
        <div style={{ fontSize: 34, fontWeight: 900, letterSpacing: ".2em", textTransform: "uppercase", color: DIFF.accent, marginBottom: 28 }}>
          The difference
        </div>
        <div style={{ fontSize: 66, fontWeight: 900, lineHeight: 1.18 }}>{props.difference}</div>
        {props.cta ? (
          <div style={{ marginTop: 50, display: "inline-block", fontSize: 46, fontWeight: 900, color: "#fff", background: DIFF.accent, borderRadius: 999, padding: "22px 46px" }}>
            {props.cta}
          </div>
        ) : null}
      </div>
      <div style={{ position: "absolute", bottom: 220, left: 0, right: 0, textAlign: "center", fontSize: 30, fontWeight: 700, color: DIFF.muted }}>
        Source: {props.sourceLine}
      </div>
      <div style={{ position: "absolute", bottom: 110, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `translateY(${bob}px)` }}>
        <Mascot pose="idea" />
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 4: Verify the scenes typecheck**

Run: `npx tsc --noEmit`
Expected: no errors. (Tests still pass: `npm test` -> all green.)

- [ ] **Step 5: Commit**

```bash
git add sticky-difference/render/src/scenes/
git commit -m "feat(sticky-difference): hook, item, and difference scene components"
```

---

### Task 10: Root composition + scene selection (TDD for activeScene)

**Files:**
- Create: `sticky-difference/render/src/Video.tsx`
- Create: `sticky-difference/render/src/Root.tsx`
- Create: `sticky-difference/render/src/index.ts`
- Test: `sticky-difference/render/src/__tests__/video.test.ts`

- [ ] **Step 1: Write the failing test (for the pure `activeScene`)**

```ts
import { describe, it, expect } from "vitest";
import { activeScene } from "../Video";
import { buildTimeline } from "../timeline";

describe("activeScene", () => {
  it("walks hook -> itemX -> itemY -> difference (no cta)", () => {
    const tl = buildTimeline(30);
    expect(activeScene(0, tl)).toBe("hook");
    expect(activeScene(tl.itemX.from, tl)).toBe("itemX");
    expect(activeScene(tl.itemY.from, tl)).toBe("itemY");
    expect(activeScene(tl.difference.from, tl)).toBe("difference");
    expect(activeScene(tl.totalFrames - 1, tl)).toBe("difference");
  });
  it("enters the cta beat only when a cta span exists", () => {
    const tl = buildTimeline(30, undefined, true);
    expect(activeScene(tl.cta.from, tl)).toBe("cta");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- video`
Expected: FAIL ("Cannot find module '../Video'").

- [ ] **Step 3: Write `Video.tsx`**

```tsx
import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DIFF } from "./theme";
import { buildTimeline, type Timeline, type SceneKey } from "./timeline";
import { audioCues } from "./audio-cues";
import { Hook } from "./scenes/Hook";
import { Item } from "./scenes/Item";
import { Difference } from "./scenes/Difference";
import type { DiffProps } from "./props";

// Pure frame -> scene-key selector (unit-tested). The cta beat is only reachable when it has a
// non-zero span; otherwise the difference scene holds to the end.
export function activeScene(frame: number, tl: Timeline): SceneKey {
  if (frame >= tl.cta.from && tl.cta.durationInFrames > 0) return "cta";
  if (frame >= tl.difference.from) return "difference";
  if (frame >= tl.itemY.from) return "itemY";
  if (frame >= tl.itemX.from) return "itemX";
  return "hook";
}

export const DifferenceVideo: React.FC<DiffProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tl = buildTimeline(fps, props.vo, !!props.cta);
  const scene = activeScene(frame, tl);
  const [x, y] = props.items;

  // gentle moving highlight, shared across scenes for continuity
  const t = frame / fps;
  const gx = 78 + 8 * Math.sin(t * 0.4);
  const gy = 12 + 6 * Math.cos(t * 0.5);

  return (
    <AbsoluteFill style={{ background: DIFF.bg }}>
      <AbsoluteFill style={{ background: `radial-gradient(circle at ${gx}% ${gy}%, #ffffff, transparent 45%), ${DIFF.bg}` }} />

      {audioCues(props, tl).map((c) => (
        <Sequence key={c.key} from={c.from} name={`vo-${c.key}`}><Audio src={staticFile(c.src)} /></Sequence>
      ))}

      {scene === "hook" && <Hook props={props} from={tl.hook.from} />}
      {scene === "itemX" && <Item item={x} side="left" from={tl.itemX.from} />}
      {scene === "itemY" && <Item item={y} side="right" from={tl.itemY.from} />}
      {(scene === "difference" || scene === "cta") && <Difference props={props} from={tl.difference.from} />}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- video`
Expected: PASS (2 tests).

- [ ] **Step 5: Write `Root.tsx`**

```tsx
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
```

- [ ] **Step 6: Write `index.ts`**

```ts
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);
```

- [ ] **Step 7: Verify the whole project typechecks and tests pass**

Run: `npx tsc --noEmit && npm test`
Expected: no type errors; all test files green.

- [ ] **Step 8: Commit**

```bash
git add sticky-difference/render/src/Video.tsx sticky-difference/render/src/Root.tsx sticky-difference/render/src/index.ts sticky-difference/render/src/__tests__/video.test.ts
git commit -m "feat(sticky-difference): root composition + frame->scene selector"
```

---

### Task 11: Render CLI + sample props + manual render verification

**Files:**
- Create: `sticky-difference/render/render.mjs`
- Create: `sticky-difference/render/sample-props.json`
- Create: `sticky-difference/render/public/comparisons/.gitkeep`

- [ ] **Step 1: Write `render.mjs`**

```js
import { bundle } from "@remotion/bundler";
import { ensureBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync, mkdirSync } from "node:fs";
import path from "node:path";

const propsPath = process.argv[2] ?? "sample-props.json";
const outPath = process.argv[3] ?? "out/sample.mp4";
const inputProps = JSON.parse(readFileSync(propsPath, "utf-8"));

await ensureBrowser();
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id: "Difference", inputProps });
mkdirSync(path.dirname(outPath), { recursive: true });
await renderMedia({ serveUrl, composition, codec: "h264", outputLocation: outPath, inputProps });
console.log("rendered", outPath);
```

- [ ] **Step 2: Write `sample-props.json`**

```json
{
  "topic": "Coffin vs Casket",
  "items": [
    { "name": "Coffin", "image": "comparisons/coffin.jpg", "trait": "Tapered to the body - six sides, wide at the shoulders." },
    { "name": "Casket", "image": "comparisons/casket.jpg", "trait": "A rectangular box with four sides and a hinged lid." }
  ],
  "difference": "A coffin is body-shaped (six-sided); a casket is a rectangular box.",
  "cta": "Which did you think was which? Comment below",
  "sourceLine": "Merriam-Webster; Britannica"
}
```

- [ ] **Step 3: Create the public assets folder**

Create an empty file `sticky-difference/render/public/comparisons/.gitkeep` so the folder is tracked.

- [ ] **Step 4: Add two test images for the render**

Place any two JPGs named `coffin.jpg` and `casket.jpg` into `sticky-difference/render/public/comparisons/`. (These are local test assets, not committed -- `public/` item images are operator-supplied. If you have none handy, copy any two images and rename them.)

- [ ] **Step 5: Run the render**

Run (from `sticky-difference/render/`): `npm run render`
Expected: console prints `rendered out/sample.mp4`; the file `out/sample.mp4` exists and is ~15s, 1080x1920. Open it and confirm: Hook (two images + "vs" + "what's the difference?" + thinking cat) -> Coffin (point-left cat) -> Casket (point-right cat) -> Difference (idea cat + CTA pill + source line).

- [ ] **Step 6: Commit**

```bash
git add sticky-difference/render/render.mjs sticky-difference/render/sample-props.json sticky-difference/render/public/comparisons/.gitkeep
git commit -m "feat(sticky-difference): render CLI + sample props"
```

---

## Self-review notes (author checklist, completed)

- **Spec coverage:** palette/theme (Task 2), 4-beat timeline + optional CTA collapse (Task 3), props incl. mandatory sourceLine + VO seam (Task 4), Cat mascot with 4 poses (Tasks 5-6), side-by-side hook + per-item + difference scenes (Task 9), VO audio seam (Task 8), 1080x1920 composition + duration-from-timeline (Task 10), hand-fed render CLI + public/comparisons (Task 11). Out-of-scope items (content-gen, publishing, VO synthesis, brand name) are correctly absent.
- **Placeholder scan:** none -- every step has real code/commands/expected output. The only intentional "placeholder" is the on-screen brand text "CURIOUS", which the spec designates as a v1 placeholder.
- **Type consistency:** `DiffProps`/`diffSchema`, `buildTimeline(fps, vo?, hasCta?, tail?)`, `Timeline`/`SceneKey`/`SCENES`, `DIFF`, `POSES`/`POSE_KEYS`/`PoseKey`, `Mascot`, `BrandHeaderView`/`ItemImageView`, `audioCues`/`AudioCue`, `Hook`/`Item`/`Difference`, `activeScene`/`DifferenceVideo` are defined once and referenced consistently across tasks.
