# Quiz Voice-Over Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Indian-English neural narration (question / answer-reveal / explanation) to the quiz Short, with the visual beats timed to the voice, reusing edge-tts and leaving an ElevenLabs seam.

**Architecture:** All work in `daily-gk-quiz/render/`. Pure, unit-tested core: `voLines(props)` (script), parametric `buildTimeline(fps, vo?, tail?)` (voice-driven beat math), `audioCues(props, tl)` (where audio plays). Integration (manual-verified): Remotion `calculateMetadata` for dynamic duration, `<Audio>` in the templates, a pluggable `voiceover.mjs` TTS provider (edge-tts), and a VO pre-step in `render.mjs` (synthesize -> measure with `ffprobe-static` -> inject props -> render). `build.py` is unchanged.

**Tech Stack:** TypeScript, Remotion, zod, vitest (render tests); Node `render.mjs`; `python -m edge_tts` (subprocess); `ffprobe-static` (npm). 

**Working directory for ALL commands:** `D:\Rewva\signal-lab\daily-gk-quiz\render`. Commands: `npm test` (vitest), `npx tsc --noEmit` (typecheck), `node render.mjs <props.json> <out.mp4>` (render). ASCII quotes only.

**Spec:** `docs/specs/2026-06-12-gk-voiceover-design.md`.

**Existing code (read before editing):**
- `render/src/timeline.ts`: `SCENES` (start-seconds array: question 0, options 0.8, countdown 3.3, lock 5.3, reveal 6.1, why 9.0, ctaHold 11.5), `END_SECONDS=13.0`, `buildTimeline(fps)` -> `{[key]:{from,durationInFrames}, totalFrames}`.
- `render/src/props.ts`: `quizSchema` (zod) + `QuizProps`. Fields: dayNumber, category, difficulty, examPrefix, template, question, options[4]={letter,text}, correctLetter, explanation, sourceLine, cta, trickHook.
- `render/src/templates/Standard.tsx` + `Trick.tsx`: call `buildTimeline(fps)`, render one `AbsoluteFill` driven by a pure `standardState(frame, tl)` (frame comparisons; NO `<Sequence>` currently).
- `render/src/Root.tsx`: `<Composition id="Quiz" ... durationInFrames={buildTimeline(FPS).totalFrames} fps={30} width=1080 height=1920 />`.
- `render/render.mjs`: reads `props.json`, `bundle()`, `selectComposition`, `renderMedia`.
- Tests are pure-logic (vitest): `timeline.test.ts`, `standard.test.tsx` (tests `standardState`), `props.test.ts`. No Remotion component is rendered in tests.

---

### Task 1: Parametric `buildTimeline(fps, vo?, tail?)`

**Files:**
- Modify: `render/src/timeline.ts`
- Modify: `render/src/__tests__/timeline.test.ts`

- [ ] **Step 1: Write the failing tests**

Replace `render/src/__tests__/timeline.test.ts` with:

```ts
import { describe, it, expect } from "vitest";
import { buildTimeline, SCENES } from "../timeline";

describe("timeline (no voice -> current fixed timeline)", () => {
  it("reproduces the original frame ranges at 30fps", () => {
    const t = buildTimeline(30);
    expect(t.question.from).toBe(0);
    expect(t.options.from).toBe(Math.round(0.8 * 30));
    expect(t.countdown.from).toBe(Math.round(3.3 * 30));
    expect(t.lock.from).toBe(Math.round(5.3 * 30));
    expect(t.reveal.from).toBe(Math.round(6.1 * 30));
    expect(t.why.from).toBe(Math.round(9.0 * 30));
    expect(t.ctaHold.from).toBe(Math.round(11.5 * 30));
    expect(t.totalFrames).toBe(Math.round(13.0 * 30));
  });
  it("exposes the canonical scene list", () => {
    expect(SCENES.map((s) => s.key)).toEqual(
      ["question", "options", "countdown", "lock", "reveal", "why", "ctaHold"]);
  });
});

describe("timeline (voice-driven beats)", () => {
  const tail = 0.45;
  it("expands the pre-countdown span when the question VO is long", () => {
    const t = buildTimeline(30, { question: 5.0, reveal: 0, why: 0 }, tail);
    // countdown now starts at max(3.3, 5.0+0.45)=5.45s, not 3.3s
    expect(t.countdown.from).toBe(Math.round(5.45 * 30));
    // structural countdown gap stays 2.0s -> lock at 7.45s
    expect(t.lock.from).toBe(Math.round((5.45 + 2.0) * 30));
  });
  it("expands reveal and why spans to fit their VO", () => {
    const t = buildTimeline(30, { question: 0, reveal: 4.0, why: 4.0 }, tail);
    const revealDur = t.why.from - t.reveal.from;
    const whyDur = t.ctaHold.from - t.why.from;
    expect(revealDur).toBe(Math.round((4.0 + tail) * 30)); // max(2.9, 4.45)=4.45
    expect(whyDur).toBe(Math.round((4.0 + tail) * 30));     // max(2.5, 4.45)=4.45
  });
  it("a short VO never shrinks a beat below its visual minimum", () => {
    const t = buildTimeline(30, { question: 0.5, reveal: 0.5, why: 0.5 }, tail);
    expect(t.countdown.from).toBe(Math.round(3.3 * 30));     // still the 3.3 minimum
    expect(t.why.from - t.reveal.from).toBe(Math.round(2.9 * 30)); // reveal min
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- timeline`
Expected: FAIL (buildTimeline ignores the 2nd/3rd args).

- [ ] **Step 3: Write the implementation**

Replace `render/src/timeline.ts` with:

```ts
// Scene start times in seconds (baseline / no-voice timeline). With voice, the three
// narration spans (pre-countdown question+options, reveal, why) expand to fit their VO;
// the quiz-mechanic gaps (countdown, lock, ctaHold) stay fixed.
export const SCENES = [
  { key: "question", start: 0.0 },
  { key: "options", start: 0.8 },
  { key: "countdown", start: 3.3 },
  { key: "lock", start: 5.3 },
  { key: "reveal", start: 6.1 },
  { key: "why", start: 9.0 },
  { key: "ctaHold", start: 11.5 },
] as const;

const END_SECONDS = 13.0;

// Baseline gaps derived from SCENES (single source of truth).
const OPTIONS_OFFSET = 0.8;       // options appear within the pre-countdown span
const PRECOUNTDOWN_MIN = 3.3;     // question+options shown before countdown
const COUNTDOWN_GAP = 5.3 - 3.3;  // fixed quiz mechanic
const LOCK_GAP = 6.1 - 5.3;       // fixed
const REVEAL_MIN = 9.0 - 6.1;     // expandable
const WHY_MIN = 11.5 - 9.0;       // expandable
const CTA_HOLD = END_SECONDS - 11.5; // fixed
const TAIL_DEFAULT = 0.45;

export type VoDurations = { question?: number; reveal?: number; why?: number };
export type SceneKey = (typeof SCENES)[number]["key"];
export type Timeline = Record<SceneKey, { from: number; durationInFrames: number }> & {
  totalFrames: number;
};

const span = (min: number, voSec: number | undefined, tail: number) =>
  Math.max(min, voSec ? voSec + tail : 0);

export function buildTimeline(fps: number, vo?: VoDurations, tail = TAIL_DEFAULT): Timeline {
  const pre = span(PRECOUNTDOWN_MIN, vo?.question, tail);
  const revealSpan = span(REVEAL_MIN, vo?.reveal, tail);
  const whySpan = span(WHY_MIN, vo?.why, tail);

  const starts: Record<SceneKey, number> = {
    question: 0,
    options: OPTIONS_OFFSET,
    countdown: pre,
    lock: pre + COUNTDOWN_GAP,
    reveal: pre + COUNTDOWN_GAP + LOCK_GAP,
    why: pre + COUNTDOWN_GAP + LOCK_GAP + revealSpan,
    ctaHold: pre + COUNTDOWN_GAP + LOCK_GAP + revealSpan + whySpan,
  };
  const end = starts.ctaHold + CTA_HOLD;

  const keys = SCENES.map((s) => s.key);
  const out = {} as Timeline;
  keys.forEach((k, i) => {
    const nextStart = i + 1 < keys.length ? starts[keys[i + 1]] : end;
    out[k] = {
      from: Math.round(starts[k] * fps),
      durationInFrames: Math.round((nextStart - starts[k]) * fps),
    };
  });
  out.totalFrames = Math.round(end * fps);
  return out;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- timeline` then `npm test` (the whole suite -- `standard.test.tsx` uses `buildTimeline(30)` and must still pass).
Expected: all PASS.

- [ ] **Step 5: Typecheck + commit**

Run: `npx tsc --noEmit` (expect clean).

```bash
git add daily-gk-quiz/render/src/timeline.ts daily-gk-quiz/render/src/__tests__/timeline.test.ts
git commit -m "feat(gk-render): parametric voice-driven buildTimeline (narration beats expand, quiz beats fixed)"
```

---

### Task 2: `voLines(props)` narration script (pure)

**Files:**
- Create: `render/src/vo.ts`
- Test: `render/src/__tests__/vo.test.ts` (Create)

- [ ] **Step 1: Write the failing test**

Create `render/src/__tests__/vo.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { voLines } from "../vo";
import type { QuizProps } from "../props";

const base: QuizProps = {
  dayNumber: 47, category: "Polity", difficulty: "basic", examPrefix: "SSC",
  template: "standard", question: "Which Article guarantees the Right to Life?",
  options: [
    { letter: "A", text: "Article 19" }, { letter: "B", text: "Article 21" },
    { letter: "C", text: "Article 14" }, { letter: "D", text: "Article 32" },
  ],
  correctLetter: "B", explanation: "Article 21 protects life and personal liberty.",
  sourceLine: "Constitution of India, Art. 21", cta: "Comment A or B", trickHook: "",
};

describe("voLines", () => {
  it("question line is the question text", () => {
    expect(voLines(base).question).toBe("Which Article guarantees the Right to Life?");
  });
  it("reveal names the correct letter and its option text", () => {
    expect(voLines(base).reveal).toBe("The correct answer is B. Article 21.");
  });
  it("why line is the explanation", () => {
    expect(voLines(base).why).toBe("Article 21 protects life and personal liberty.");
  });
  it("empty explanation yields an empty why line", () => {
    expect(voLines({ ...base, explanation: "" }).why).toBe("");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- vo`
Expected: FAIL (no module `../vo`).

- [ ] **Step 3: Write the implementation**

Create `render/src/vo.ts`:

```ts
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- vo`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/vo.ts daily-gk-quiz/render/src/__tests__/vo.test.ts
git commit -m "feat(gk-render): voLines derives the narration script from props"
```

---

### Task 3: Optional `vo` + `audio` props on `quizSchema`

**Files:**
- Modify: `render/src/props.ts`
- Modify: `render/src/__tests__/props.test.ts`

- [ ] **Step 1: Write the failing tests**

Append to `render/src/__tests__/props.test.ts` (inside the `describe`):

```ts
  it("accepts optional vo + audio fields", () => {
    const parsed = quizSchema.parse({
      ...valid,
      vo: { question: 2.5, reveal: 1.8, why: 3.0 },
      audio: { question: "vo/q.mp3", reveal: "vo/r.mp3", why: "vo/w.mp3" },
    });
    expect(parsed.vo?.reveal).toBe(1.8);
    expect(parsed.audio?.why).toBe("vo/w.mp3");
  });
  it("is still valid with no vo/audio (silent render)", () => {
    expect(quizSchema.parse(valid).vo).toBeUndefined();
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- props`
Expected: FAIL (vo/audio stripped or rejected).

- [ ] **Step 3: Write the implementation**

In `render/src/props.ts`, add these optional fields inside `z.object({ ... })` (after `trickHook`):

```ts
  vo: z.object({
    question: z.number().nonnegative(),
    reveal: z.number().nonnegative(),
    why: z.number().nonnegative(),
  }).optional(),
  audio: z.object({
    question: z.string(),
    reveal: z.string(),
    why: z.string(),
  }).partial().optional(),
```

(`vo` carries measured VO seconds; `audio` carries staticFile-relative mp3 paths. Both optional so `build.py`'s existing `props.json` stays valid. `audio` is `.partial()` so a missing explanation line can omit `why`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- props` then `npx tsc --noEmit`.
Expected: PASS + clean typecheck.

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/props.ts daily-gk-quiz/render/src/__tests__/props.test.ts
git commit -m "feat(gk-render): optional vo+audio props (back-compat with silent render)"
```

---

### Task 4: `audioCues` + wire `<Audio>` into the templates

**Files:**
- Create: `render/src/audio-cues.ts`
- Test: `render/src/__tests__/audio-cues.test.ts` (Create)
- Modify: `render/src/templates/Standard.tsx`, `render/src/templates/Trick.tsx`

- [ ] **Step 1: Write the failing test**

Create `render/src/__tests__/audio-cues.test.ts`:

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- audio-cues`
Expected: FAIL (no module).

- [ ] **Step 3: Write `audio-cues.ts`**

Create `render/src/audio-cues.ts`:

```ts
import type { QuizProps } from "./props";
import type { Timeline } from "./timeline";

export type AudioCue = { key: "question" | "reveal" | "why"; src: string; from: number };

// Map present audio lines to the frame their scene starts. Pure.
export function audioCues(props: QuizProps, tl: Timeline): AudioCue[] {
  const a = props.audio;
  if (!a) return [];
  const out: AudioCue[] = [];
  (["question", "reveal", "why"] as const).forEach((key) => {
    const src = a[key];
    if (src) out.push({ key, src, from: tl[key].from });
  });
  return out;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- audio-cues`
Expected: PASS (3 tests).

- [ ] **Step 5: Wire `<Audio>` into the templates**

In BOTH `render/src/templates/Standard.tsx` and `render/src/templates/Trick.tsx`:

(a) Change the timeline call to use the VO durations: replace `const tl = buildTimeline(fps);` with `const tl = buildTimeline(fps, props.vo);`.

(b) Add imports: from `"remotion"` add `Audio, Sequence, staticFile`; add `import { audioCues } from "../audio-cues";` (adjust relative path: templates are in `src/templates/`, so `../audio-cues`).

(c) Inside the returned `<AbsoluteFill>...`, add the audio cues as the FIRST children (they render nothing visual):

```tsx
      {audioCues(props, tl).map((c) => (
        <Sequence key={c.key} from={c.from} name={`vo-${c.key}`}>
          <Audio src={staticFile(c.src)} />
        </Sequence>
      ))}
```

(Place this immediately after the opening `<AbsoluteFill ...>` tag, before `<BrandHeaderView .../>`.)

- [ ] **Step 6: Typecheck + full suite + commit**

Run: `npx tsc --noEmit` then `npm test`.
Expected: clean typecheck; all tests pass (templates still render; `standardState` tests unaffected).

```bash
git add daily-gk-quiz/render/src/audio-cues.ts daily-gk-quiz/render/src/__tests__/audio-cues.test.ts daily-gk-quiz/render/src/templates/Standard.tsx daily-gk-quiz/render/src/templates/Trick.tsx
git commit -m "feat(gk-render): play VO via <Audio> at each narration beat (audioCues)"
```

---

### Task 5: Dynamic composition duration (`calculateMetadata`)

**Files:**
- Modify: `render/src/Root.tsx`

- [ ] **Step 1: Update Root to compute duration from props**

In `render/src/Root.tsx`:

(a) Import the type: `import { quizSchema, type QuizProps } from "./props";` already exists; ensure `buildTimeline` is imported (it is).

(b) Replace the static `durationInFrames={buildTimeline(FPS).totalFrames}` with a `calculateMetadata` prop on the `<Composition>` that recomputes from `props.vo`:

```tsx
  <Composition
    id="Quiz"
    component={Quiz}
    schema={quizSchema}
    defaultProps={defaultProps}
    fps={FPS}
    width={1080}
    height={1920}
    calculateMetadata={({ props }) => ({
      durationInFrames: buildTimeline(FPS, props.vo).totalFrames,
    })}
  />
```

(Remove the `durationInFrames={...}` attribute -- `calculateMetadata` supplies it. Keep `fps`, `width`, `height`. With no `props.vo`, `buildTimeline(FPS)` gives the original 390 frames, so silent renders are unchanged.)

- [ ] **Step 2: Typecheck**

Run: `npx tsc --noEmit`
Expected: clean. (If TS complains the `props` arg is untyped, annotate: `calculateMetadata={({ props }: { props: QuizProps }) => (...)}`.)

- [ ] **Step 3: Verify the existing silent render still works (no VO yet)**

Run: `node render.mjs sample-props.json out/sample.mp4`
Expected: renders `out/sample.mp4` as before (duration ~13s; `sample-props.json` has no `vo`, so duration is unchanged). This confirms `calculateMetadata` did not break the silent path.

- [ ] **Step 4: Commit**

```bash
git add daily-gk-quiz/render/src/Root.tsx
git commit -m "feat(gk-render): composition duration computed from props.vo via calculateMetadata"
```

---

### Task 6: Pluggable TTS provider (`voiceover.mjs`)

**Files:**
- Create: `render/voiceover.mjs`

- [ ] **Step 1: Write the provider**

Create `render/voiceover.mjs`:

```js
// Pluggable TTS provider. Default: edge-tts (free, Microsoft Edge neural voice via `python -m edge_tts`).
// Later: ElevenLabs behind TTS=elevenlabs (stubbed). Mirrors the WhichWise content-studio approach.
import { spawnSync } from "node:child_process";

export const VOICE = process.env.TTS_VOICE || "en-IN-NeerjaNeural";
export const RATE = process.env.TTS_RATE || "+6%";

function edgeTts(text, outPath) {
  const r = spawnSync("python", ["-m", "edge_tts", "--voice", VOICE, "--rate", RATE,
                                 "--text", text, "--write-media", outPath], { encoding: "utf-8" });
  if (r.status !== 0) {
    throw new Error(`edge-tts failed (is it installed? pip install edge-tts):\n${r.stderr || r.stdout || r.error}`);
  }
}

// Synthesize `text` to an mp3 at `outPath`. Selected by env TTS (default edge-tts).
export function synthesize(text, outPath) {
  const provider = (process.env.TTS || "edge-tts").toLowerCase();
  if (provider === "elevenlabs") {
    throw new Error("ElevenLabs provider not implemented yet (seam only); unset TTS to use edge-tts");
  }
  edgeTts(text, outPath);
}
```

- [ ] **Step 2: Smoke-check it loads (no network call)**

Run: `node -e "import('./voiceover.mjs').then(m => console.log('ok', m.VOICE, typeof m.synthesize))"`
Expected: prints `ok en-IN-NeerjaNeural function`.

- [ ] **Step 3: Commit**

```bash
git add daily-gk-quiz/render/voiceover.mjs
git commit -m "feat(gk-render): pluggable TTS provider (edge-tts default, ElevenLabs seam)"
```

---

### Task 7: VO pre-step in `render.mjs` + `ffprobe-static` dep

**Files:**
- Modify: `render/render.mjs`
- Modify: `render/package.json` (add `ffprobe-static`)
- Modify: `render/README.md` (document `pip install edge-tts`)

- [ ] **Step 1: Add the dependency**

Run (from `render/`): `npm install --save ffprobe-static`
Confirm `render/package.json` now lists `ffprobe-static` under dependencies.

- [ ] **Step 2: Rewrite `render.mjs` to add the VO pre-step**

Replace `render/render.mjs` with:

```js
import { bundle } from "@remotion/bundler";
import { ensureBrowser, renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { createRequire } from "node:module";
import { synthesize } from "./voiceover.mjs";

const require = createRequire(import.meta.url);
const FFPROBE = require("ffprobe-static").path;

// Narration script (kept in sync with the unit-tested src/vo.ts; inlined here because this
// plain-Node ESM file cannot import the .ts module at runtime). Pure, ~6 lines.
function voLines(props) {
  const correct = (props.options || []).find((o) => o.letter === props.correctLetter);
  const answerText = correct ? correct.text : "";
  return {
    question: props.question,
    reveal: `The correct answer is ${props.correctLetter}. ${answerText}.`,
    why: props.explanation || "",
  };
}

const propsPath = process.argv[2] ?? "sample-props.json";
const outPath = process.argv[3] ?? "out/sample.mp4";
const noVoice = process.argv.includes("--no-voice"); // escape hatch: silent render
const inputProps = JSON.parse(readFileSync(propsPath, "utf-8"));

const probeDur = (f) => {
  const r = spawnSync(FFPROBE, ["-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", f], { encoding: "utf-8" });
  if (r.status !== 0) throw new Error(`ffprobe failed on ${f}: ${r.stderr || r.error}`);
  return parseFloat(r.stdout.trim());
};

// --- Voice-over pre-step: synthesize -> measure -> inject vo+audio into inputProps ----------
const PUBLIC_DIR = path.resolve("public", "vo");
if (!noVoice) {
  const lines = voLines(inputProps);                 // { question, reveal, why }
  mkdirSync(PUBLIC_DIR, { recursive: true });
  const vo = {}; const audio = {};
  for (const key of ["question", "reveal", "why"]) {
    const text = (lines[key] || "").trim();
    if (!text) { vo[key] = 0; continue; }
    const abs = path.join(PUBLIC_DIR, `${key}.mp3`);
    synthesize(text, abs);
    vo[key] = probeDur(abs);
    audio[key] = `vo/${key}.mp3`;                     // staticFile-relative (public/ root)
  }
  inputProps.vo = vo;
  inputProps.audio = audio;
}

// --- Render -------------------------------------------------------------------------------
await ensureBrowser();
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id: "Quiz", inputProps });
await renderMedia({ serveUrl, composition, codec: "h264", outputLocation: outPath, inputProps });
if (!noVoice && existsSync(PUBLIC_DIR)) rmSync(PUBLIC_DIR, { recursive: true, force: true });
console.log("rendered", outPath);
```

NOTE: `voLines` is inlined in `render.mjs` (above) rather than imported from `./src/vo.ts`, because this plain-Node ESM file cannot transpile/import a `.ts` module at runtime. The logic is identical to the unit-tested `src/vo.ts` (Task 2) -- keep the two in sync (both are ~6 trivial lines). The bundled Remotion code (`src/index.ts` -> templates) still uses the real `src/vo.ts`-free path; only `render.mjs` needs this inline copy to compute the script before bundling.

- [ ] **Step 3: Document the Python dep**

In `render/README.md`, add a short section:

```markdown
## Voice-over (edge-tts)
The renderer narrates the question, answer, and explanation using edge-tts (free Microsoft Edge
neural TTS). Install once: `pip install edge-tts` (into the daily-gk-quiz venv or system python on PATH).
ffprobe is bundled via the `ffprobe-static` npm package -- no system install. Render silently with
`node render.mjs <props.json> <out.mp4> --no-voice`. Voice/rate via env `TTS_VOICE` / `TTS_RATE`;
`TTS=elevenlabs` is reserved for a future provider.
```

- [ ] **Step 4: Verify the silent escape hatch still renders (no edge-tts needed)**

Run: `node render.mjs sample-props.json out/sample.mp4 --no-voice`
Expected: renders as before. (Confirms the render path is intact even without edge-tts installed. If the `./src/vo.ts` import errored, apply the inline-`voLines` fallback from Step 2's NOTE, then re-run.)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/render.mjs daily-gk-quiz/render/package.json daily-gk-quiz/render/package-lock.json daily-gk-quiz/render/README.md
git commit -m "feat(gk-render): render.mjs synthesizes + measures VO and injects vo/audio props"
```

---

### Task 8: End-to-end narrated render (manual verification)

**Files:** none (verification only).

- [ ] **Step 1: Ensure edge-tts is available**

Run: `python -m edge_tts --list-voices` (expect a voice list; if "No module named edge_tts", run `pip install edge-tts`). This needs network.

- [ ] **Step 2: Render a real narrated MP4**

Run: `node render.mjs sample-props.json out/narrated.mp4`
Expected: console shows the render completing; `out/narrated.mp4` exists.

- [ ] **Step 3: Verify A/V**

- Confirm the file has an audio track: `node -e "const {execFileSync}=require('node:child_process'); const p=require('ffprobe-static').path; console.log(execFileSync(p,['-v','error','-show_entries','stream=codec_type','-of','csv=p=0','out/narrated.mp4']).toString())"` -> expect both `video` and `audio`.
- Play it: the question is read before the countdown; the answer reveal and explanation are narrated and not clipped; total length flexes to the voice (longer than the silent 13s if the lines are long).

- [ ] **Step 4: Run the full render suite + typecheck once more**

Run: `npm test` and `npx tsc --noEmit`.
Expected: all green, clean.

- [ ] **Step 5: Note results**

Record in the commit/PR what was eyeballed (audio track present, narration synced to beats, nothing clipped). If edge-tts network was unavailable in this environment, state that the synthesis step is verified by the provider smoke-test (Task 6) + the `--no-voice` render path, and that a live narrated render needs network.

```bash
git add -A && git commit -m "test(gk-render): verify end-to-end narrated render" --allow-empty
```

---

## Self-Review notes (author)

- **Spec coverage:** SS3 voLines -> Task 2; SS4 parametric timeline -> Task 1; SS4 <Audio>/audioCues -> Task 4; SS4 calculateMetadata -> Task 5; SS5 provider -> Task 6; SS3/SS6 render.mjs pre-step + ffprobe-static -> Task 7; SS6 deps/README -> Task 7; SS7 testing -> each pure task's vitest + Task 8 manual e2e. All covered.
- **Back-compat:** `buildTimeline(fps)` no-arg reproduces the 390-frame timeline (Task 1 test); optional `vo`/`audio` keep `build.py`'s props valid (Task 3 test); `--no-voice` + `calculateMetadata` with no `vo` keep the silent render working (Tasks 5,7).
- **Type consistency:** `voLines(props) -> {question,reveal,why}` (Task 2) matches `render.mjs` usage (Task 7) and the `audio`/`vo` keys (Task 3 schema, Task 4 cues). `buildTimeline(fps, vo?, tail?)` signature identical in Tasks 1,4,5.
- **Honest risk:** Tasks 5-7 (Remotion calculateMetadata, `<Audio>`+staticFile, edge-tts subprocess, `.ts` import from `render.mjs`) are integration-verified, not unit-tested; Task 7 Step 2 calls out the `.ts`-import fallback (inline voLines) explicitly, and Task 8 is the real proof. The pure core (Tasks 1-4) is fully TDD'd.
