# GK Render Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the render layer that turns one approved verified question into a branded 1080x1920 vertical MP4 — the selection-layer data additions it needs (Python) plus a self-contained Remotion video project (TypeScript/React).

**Architecture:** Part A extends the existing `daily-gk-quiz/selection` Python package with `is_trick`, answer-key balancing (`answer_position`), `template_for`, and a `trick_hook` rotation — the data contract the render consumes. Part B is a fresh Remotion project under `daily-gk-quiz/render/`: design tokens + pure logic (difficulty→colour, props schema, timeline math) are unit-tested with vitest; each visual block is split into a **pure `*View` component** (props-only, tested in jsdom with @testing-library/react) plus a thin **animated wrapper** (reads `useCurrentFrame`, verified by an actual render). Two templates (Standard, Trick) compose the blocks; a root `Quiz` composition sequences them on a ~12-14s timeline; a CLI renders to MP4.

**Tech Stack:** Part A — Python 3.12, pytest (existing package). Part B — Node 24, Remotion v4, React 18, TypeScript, zod (Remotion's prop schema), vitest + @testing-library/react + jsdom. Remotion bundles ffmpeg (no system ffmpeg needed).

**Spec:** `docs/specs/2026-06-10-gk-render-layer-design.md`
**Depends on:** `docs/specs/2026-06-10-gk-topic-selection-design.md` (the selection package already built)

**Prerequisite:** Node + npm present (verified: node v24, npm v11). All Part B commands run from `daily-gk-quiz/render/`.

---

## File Structure

| File | Responsibility |
|---|---|
| `daily-gk-quiz/selection/models.py` (modify) | add `Question.is_trick`, `HistoryRecord.answer_position` |
| `daily-gk-quiz/selection/selection.py` (modify) | add `balance_answer_position`, `template_for` |
| `daily-gk-quiz/selection/planner.py` (modify) | `DayPlan` gains `answer_position` + `trick_hook`; `plan_today` computes them |
| `daily-gk-quiz/data/prompts.json` (modify) | add `trick_hooks` pool |
| `daily-gk-quiz/render/package.json` etc. | Remotion project scaffold + vitest |
| `daily-gk-quiz/render/src/theme.ts` | design tokens (Standard + Trick) + `difficultyColor` |
| `daily-gk-quiz/render/src/props.ts` | zod `quizSchema` + `QuizProps` type |
| `daily-gk-quiz/render/src/timeline.ts` | scene timing -> frame ranges |
| `daily-gk-quiz/render/src/blocks/*.tsx` | one file per block: pure `*View` + animated wrapper |
| `daily-gk-quiz/render/src/templates/Standard.tsx`, `Trick.tsx` | compose blocks |
| `daily-gk-quiz/render/src/Quiz.tsx` | root composition body (timeline sequencing, template switch) |
| `daily-gk-quiz/render/src/Root.tsx`, `src/index.ts` | `registerRoot` + `<Composition>` (schema + defaults) |
| `daily-gk-quiz/render/render.mjs` | CLI: props JSON -> MP4 |
| `daily-gk-quiz/render/src/**/__tests__/*.test.ts(x)` | vitest tests |

**Data contract (locked, used across tasks):**

```
# Python Question gains: is_trick: bool = False
# Python HistoryRecord gains: answer_position: Optional[str] = None   # "A"|"B"|"C"|"D"
# DayPlan gains: answer_position: str ("A".."D"), trick_hook: str

# Remotion QuizProps (zod): {
#   dayNumber: number, category: string, difficulty: "basic"|"intermediate"|"advanced",
#   examPrefix: string,                      // e.g. "SSC"
#   template: "standard" | "trick",
#   question: string,
#   options: [{ letter: "A"|"B"|"C"|"D", text: string }]  // length 4, ordered
#   correctLetter: "A"|"B"|"C"|"D",
#   explanation: string,                     // 1-2 sentences
#   sourceLine: string,                      // "Constitution of India, Art. 21"
#   cta: string, trickHook: string, fps: number
# }
```

---

# PART A — Selection-layer data additions (Python)

All Part A commands run from `daily-gk-quiz/` using the existing venv:
`.venv\Scripts\python.exe -m pytest ...`

## Task A1: Model fields — is_trick + answer_position

**Files:**
- Modify: `daily-gk-quiz/selection/models.py`
- Test: `daily-gk-quiz/tests/test_models_render.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_models_render.py`:
```python
from selection.models import Question, HistoryRecord

def _q(**over):
    base = dict(domain="polity", difficulty="basic", fact_key="polity/art-21",
                entity="Article 21", question="Q?", answer="Article 21",
                distractors=["a", "b", "c"], exam_relevance=["SSC"],
                sources=["https://1", "https://2"], explanation="why")
    base.update(over)
    return Question(**base)

def test_question_defaults_is_trick_false():
    assert _q().is_trick is False

def test_question_is_trick_roundtrips():
    q = _q(is_trick=True)
    assert Question.from_dict(q.to_dict()).is_trick is True

def test_history_record_carries_answer_position():
    rec = HistoryRecord("2026-06-10", _q(), hook="h", cta="c", answer_position="B")
    d = rec.to_dict()
    assert d["answer_position"] == "B"
    assert HistoryRecord.from_dict(d).answer_position == "B"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_models_render.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'is_trick'`.

- [ ] **Step 3: Edit `selection/models.py`**

In `Question`, add after `mnemonic: Optional[str] = None`:
```python
    is_trick: bool = False
```
In `Question.from_dict`, add to the `cls(...)` call:
```python
            is_trick=d.get("is_trick", False),
```
In `HistoryRecord`, replace the class body with:
```python
@dataclass
class HistoryRecord:
    date: str
    question: Question
    hook: Optional[str] = None
    cta: Optional[str] = None
    answer_position: Optional[str] = None

    def to_dict(self) -> dict:
        return {"date": self.date, "hook": self.hook, "cta": self.cta,
                "answer_position": self.answer_position, **self.question.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryRecord":
        return cls(date=d["date"], question=Question.from_dict(d),
                   hook=d.get("hook"), cta=d.get("cta"),
                   answer_position=d.get("answer_position"))
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_models_render.py tests/test_models.py tests/test_store.py -v`
Expected: PASS (new 3 + existing model/store tests still green).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/models.py daily-gk-quiz/tests/test_models_render.py
git commit -m "feat: add is_trick + answer_position to render data model"
```

---

## Task A2: balance_answer_position + template_for

**Files:**
- Modify: `daily-gk-quiz/selection/selection.py`
- Test: `daily-gk-quiz/tests/test_answer_balance.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_answer_balance.py`:
```python
from datetime import date
from selection.models import Question, HistoryRecord
from selection.selection import balance_answer_position, template_for

def _rec(pos, d):
    q = Question("polity", "basic", f"polity/x-{d}", "X", "q?", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])
    return HistoryRecord(d, q, answer_position=pos)

def test_empty_history_returns_A():
    assert balance_answer_position([], date(2026, 6, 10)) == "A"

def test_picks_least_used_position_over_last_30():
    # A used 3x, B 2x, C 2x, D 0x -> D is least used
    hist = ([_rec("A", f"2026-05-{d:02d}") for d in (1, 2, 3)]
            + [_rec("B", f"2026-05-{d:02d}") for d in (4, 5)]
            + [_rec("C", f"2026-05-{d:02d}") for d in (6, 7)])
    assert balance_answer_position(hist, date(2026, 6, 10)) == "D"

def test_only_counts_last_30_records():
    # 31 older "A" records then nothing else; window keeps 30 most recent (all A) -> A is max,
    # so the least-used among A/B/C/D is B (first non-A in tie order)
    hist = [_rec("A", f"2026-04-{(d % 28) + 1:02d}") for d in range(31)]
    assert balance_answer_position(hist, date(2026, 6, 10)) in ("B", "C", "D")

def test_template_for_maps_is_trick():
    assert template_for(True) == "trick"
    assert template_for(False) == "standard"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_answer_balance.py -v`
Expected: FAIL — `ImportError: cannot import name 'balance_answer_position'`.

- [ ] **Step 3: Append to `selection/selection.py`**

```python
POSITIONS = ("A", "B", "C", "D")

def balance_answer_position(history: list[HistoryRecord], today: date,
                            last_n: int = 30) -> str:
    """The A/B/C/D slot least used as the correct position over the last `last_n` posts.

    `today` is accepted for signature consistency with the other selectors (unused here:
    balancing is over the most recent posts, not a date window). Ties resolve A<B<C<D."""
    recent = [r.answer_position for r in history[-last_n:] if r.answer_position]
    counts = {p: recent.count(p) for p in POSITIONS}
    order = {p: i for i, p in enumerate(POSITIONS)}
    return min(POSITIONS, key=lambda p: (counts[p], order[p]))

def template_for(is_trick: bool) -> str:
    return "trick" if is_trick else "standard"
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_answer_balance.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/selection.py daily-gk-quiz/tests/test_answer_balance.py
git commit -m "feat: answer-key position balancing + template_for"
```

---

## Task A3: DayPlan gains answer_position + trick_hook; prompts.json trick_hooks

**Files:**
- Modify: `daily-gk-quiz/selection/planner.py`
- Modify: `daily-gk-quiz/data/prompts.json`
- Test: `daily-gk-quiz/tests/test_planner_render.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_planner_render.py`:
```python
from datetime import date
from selection.planner import plan_today, DayPlan

WEIGHTS = {"current-affairs": 30, "polity": 10}
MIX = {"basic": 0.5, "intermediate": 0.35, "advanced": 0.15}

def test_dayplan_has_answer_position_and_trick_hook():
    plan = plan_today(history=[], bank=[], weights=WEIGHTS, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"], trick_hooks=["Common Exam Trap"],
                      today=date(2026, 6, 10), window_days=120)
    assert isinstance(plan, DayPlan)
    assert plan.answer_position == "A"            # empty history -> first slot
    assert plan.trick_hook == "Common Exam Trap"  # rotated from the pool
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_planner_render.py -v`
Expected: FAIL — `TypeError: plan_today() got an unexpected keyword argument 'trick_hooks'`.

- [ ] **Step 3: Edit `selection/planner.py`**

Add `balance_answer_position` to the import from `selection.selection`:
```python
from selection.selection import (
    pick_domain, pick_difficulty, draw_from_bank, pick_rotation, _recent,
    balance_answer_position,
)
```
Add two fields to the `DayPlan` dataclass (after `cta: str`):
```python
    answer_position: str = "A"
    trick_hook: str = ""
```
Change the `plan_today` signature to accept `trick_hooks` (add it after `ctas`):
```python
def plan_today(*, history: list[HistoryRecord], bank: list[Question],
               weights: dict[str, float], target_mix: dict[str, float],
               hooks: list[str], ctas: list[str], trick_hooks: list[str],
               today: date, window_days: int = 120) -> DayPlan:
```
Before the `return`, compute the two values and pass them:
```python
    answer_position = balance_answer_position(history, today)
    recent_trick = [r.hook for r in recent_records if r.hook]  # reuse hook usage for variety
    trick_hook = pick_rotation(trick_hooks, recent_trick) if trick_hooks else ""
    return DayPlan(domain, difficulty, recent_fact_keys, bank_candidate, hook, cta,
                   answer_position=answer_position, trick_hook=trick_hook)
```
(`recent_records` already exists in `plan_today` from the hook/cta work.)

- [ ] **Step 4: Edit `daily-gk-quiz/data/prompts.json`**

Add a `trick_hooks` key (keep `hooks` and `ctas`):
```json
  "trick_hooks": [
    "Most Aspirants Miss This",
    "Common Exam Trap",
    "Easy But Confusing",
    "Don't Rush This One",
    "Looks Easy, Isn't",
    "SSC Favourite Trap",
    "UPSC Asked a Similar Concept",
    "90% Get This Wrong"
  ]
```

- [ ] **Step 5: Run tests to verify pass**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest -v`
Expected: PASS — the new planner-render test plus all existing tests. The existing `test_planner.py` calls `plan_today` WITHOUT `trick_hooks`; update those three calls to pass `trick_hooks=[]` (a required kwarg now). Make that edit in `tests/test_planner.py` (add `trick_hooks=[]` to each `plan_today(...)` call), then re-run.

- [ ] **Step 6: Commit**

```bash
git add daily-gk-quiz/selection/planner.py daily-gk-quiz/data/prompts.json daily-gk-quiz/tests/test_planner_render.py daily-gk-quiz/tests/test_planner.py
git commit -m "feat: DayPlan emits balanced answer_position + rotated trick_hook"
```

---

# PART B — Remotion render project (TypeScript)

All Part B commands run from `daily-gk-quiz/render/`.

## Task B1: Scaffold the Remotion project

**Files:**
- Create: `daily-gk-quiz/render/package.json`, `tsconfig.json`, `vitest.config.ts`, `src/index.ts`, `src/Root.tsx`
- Test: `daily-gk-quiz/render/src/__tests__/smoke.test.ts`

- [ ] **Step 1: Create `daily-gk-quiz/render/package.json`**

```json
{
  "name": "daily-gk-quiz-render",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest run",
    "render": "node render.mjs",
    "studio": "remotion studio"
  },
  "dependencies": {
    "@remotion/cli": "4.0.290",
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

- [ ] **Step 2: Create `daily-gk-quiz/render/tsconfig.json`**

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

- [ ] **Step 3: Create `daily-gk-quiz/render/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: { globals: true, environment: "jsdom" },
});
```

- [ ] **Step 4: Write the failing smoke test** `daily-gk-quiz/render/src/__tests__/smoke.test.ts`

```ts
import { describe, it, expect } from "vitest";

describe("smoke", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 5: Install + run (verify pass)**

Run: `cd daily-gk-quiz/render && npm install && npm test`
Expected: install succeeds; vitest reports 1 passing test. (Remotion + ffmpeg download on install.)

- [ ] **Step 6: Create minimal `src/index.ts` and `src/Root.tsx` so the project is a valid Remotion root**

`src/Root.tsx`:
```tsx
import React from "react";

export const RemotionRoot: React.FC = () => {
  return null; // compositions registered in a later task
};
```
`src/index.ts`:
```ts
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);
```

- [ ] **Step 7: Commit**

```bash
git add daily-gk-quiz/render/package.json daily-gk-quiz/render/package-lock.json daily-gk-quiz/render/tsconfig.json daily-gk-quiz/render/vitest.config.ts daily-gk-quiz/render/src/index.ts daily-gk-quiz/render/src/Root.tsx daily-gk-quiz/render/src/__tests__/smoke.test.ts
git commit -m "chore: scaffold daily-gk-quiz Remotion render project"
```

Also create `daily-gk-quiz/render/.gitignore`:
```
node_modules/
out/
.remotion/
```
and `git add` + amend or a follow-up commit `chore: gitignore render artifacts`.

---

## Task B2: theme.ts + difficultyColor

**Files:**
- Create: `daily-gk-quiz/render/src/theme.ts`
- Test: `daily-gk-quiz/render/src/__tests__/theme.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { STANDARD, TRICK, difficultyColor } from "../theme";

describe("theme", () => {
  it("standard palette is the locked duotone", () => {
    expect(STANDARD.bg).toBe("#15123b");
    expect(STANDARD.accent).toBe("#c6f24e");
  });
  it("maps difficulty to Easy/Medium/Hard colours", () => {
    expect(difficultyColor("basic")).toEqual({ label: "Easy", color: "#3ddc84" });
    expect(difficultyColor("intermediate")).toEqual({ label: "Medium", color: "#f4c430" });
    expect(difficultyColor("advanced")).toEqual({ label: "Hard", color: "#ff5a5f" });
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- theme`
Expected: FAIL — cannot find module `../theme`.

- [ ] **Step 3: Create `src/theme.ts`**

```ts
export const STANDARD = {
  bg: "#15123b",
  accent: "#c6f24e",
  text: "#f4f1ff",
  muted: "#c2bdec",
  pillOutline: "#4b4780",
} as const;

export const TRICK = {
  bg: "#fbe6c9",
  ink: "#171410",
  teal: "#16a085",
  red: "#e2402b",
  marigold: "#e9b949",
} as const;

export type Difficulty = "basic" | "intermediate" | "advanced";

const DIFFICULTY = {
  basic: { label: "Easy", color: "#3ddc84" },
  intermediate: { label: "Medium", color: "#f4c430" },
  advanced: { label: "Hard", color: "#ff5a5f" },
} as const;

export function difficultyColor(d: Difficulty) {
  return DIFFICULTY[d];
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd daily-gk-quiz/render && npm test -- theme`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/theme.ts daily-gk-quiz/render/src/__tests__/theme.test.ts
git commit -m "feat: render theme tokens + difficulty colour mapping"
```

---

## Task B3: props.ts (zod schema)

**Files:**
- Create: `daily-gk-quiz/render/src/props.ts`
- Test: `daily-gk-quiz/render/src/__tests__/props.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { quizSchema } from "../props";

const valid = {
  dayNumber: 47, category: "Polity", difficulty: "basic", examPrefix: "SSC",
  template: "standard", question: "Which Article guarantees the Right to Life?",
  options: [
    { letter: "A", text: "Article 19" }, { letter: "B", text: "Article 21" },
    { letter: "C", text: "Article 14" }, { letter: "D", text: "Article 32" },
  ],
  correctLetter: "B", explanation: "Article 21 protects life and personal liberty.",
  sourceLine: "Constitution of India, Art. 21", cta: "Comment A or B",
  trickHook: "Common Exam Trap", fps: 30,
};

describe("quizSchema", () => {
  it("accepts a valid props object", () => {
    expect(quizSchema.parse(valid)).toMatchObject({ correctLetter: "B" });
  });
  it("rejects when options length != 4", () => {
    expect(() => quizSchema.parse({ ...valid, options: valid.options.slice(0, 3) })).toThrow();
  });
  it("rejects an unknown template", () => {
    expect(() => quizSchema.parse({ ...valid, template: "fancy" })).toThrow();
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- props`
Expected: FAIL — cannot find module `../props`.

- [ ] **Step 3: Create `src/props.ts`**

```ts
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
```

- [ ] **Step 4: Run to verify pass**

Run: `cd daily-gk-quiz/render && npm test -- props`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/props.ts daily-gk-quiz/render/src/__tests__/props.test.ts
git commit -m "feat: zod quiz props schema"
```

---

## Task B4: timeline.ts (scene frame ranges)

**Files:**
- Create: `daily-gk-quiz/render/src/timeline.ts`
- Test: `daily-gk-quiz/render/src/__tests__/timeline.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { buildTimeline, SCENES } from "../timeline";

describe("timeline", () => {
  it("converts the default scene seconds to frame ranges at 30fps", () => {
    const t = buildTimeline(30);
    expect(t.question.from).toBe(0);
    expect(t.options.from).toBe(Math.round(0.8 * 30));
    expect(t.lock.from).toBe(Math.round(5.3 * 30));
    expect(t.reveal.from).toBe(Math.round(6.1 * 30));
  });
  it("total duration is ~13s (<= 14s)", () => {
    const t = buildTimeline(30);
    expect(t.totalFrames).toBeLessThanOrEqual(14 * 30);
    expect(t.totalFrames).toBeGreaterThan(11 * 30);
  });
  it("exposes the canonical scene list", () => {
    expect(SCENES.map((s) => s.key)).toEqual(
      ["question", "options", "countdown", "lock", "reveal", "why", "ctaHold"]);
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- timeline`
Expected: FAIL — cannot find module `../timeline`.

- [ ] **Step 3: Create `src/timeline.ts`**

```ts
// Scene start times in seconds (post-review ~12-14s timeline).
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

export type SceneKey = (typeof SCENES)[number]["key"];
export type Timeline = Record<SceneKey, { from: number; durationInFrames: number }> & {
  totalFrames: number;
};

export function buildTimeline(fps: number): Timeline {
  const out = {} as Timeline;
  SCENES.forEach((scene, i) => {
    const nextStart = i + 1 < SCENES.length ? SCENES[i + 1].start : END_SECONDS;
    out[scene.key] = {
      from: Math.round(scene.start * fps),
      durationInFrames: Math.round((nextStart - scene.start) * fps),
    };
  });
  out.totalFrames = Math.round(END_SECONDS * fps);
  return out;
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd daily-gk-quiz/render && npm test -- timeline`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/timeline.ts daily-gk-quiz/render/src/__tests__/timeline.test.ts
git commit -m "feat: scene timeline -> frame ranges"
```

---

## Task B5: Static blocks — pure Views (BrandHeader, DifficultyChip, CategoryBand, DayNumber)

Pattern for all blocks: a pure `*View` (props only, no Remotion hooks — testable in jsdom) lives in the block file; the animated wrapper (added in templates) supplies frame-driven style. This task builds the **Views**.

**Files:**
- Create: `daily-gk-quiz/render/src/blocks/StaticBlocks.tsx`
- Test: `daily-gk-quiz/render/src/__tests__/static-blocks.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrandHeaderView, DifficultyChipView, CategoryBandView, DayNumberView } from "../blocks/StaticBlocks";

describe("static block views", () => {
  it("brand header shows wordmark + day", () => {
    render(<BrandHeaderView dayNumber={47} />);
    expect(screen.getByText("Daily GK")).toBeTruthy();
    expect(screen.getByText("DAY 47")).toBeTruthy();
  });
  it("difficulty chip shows mapped label + exam prefix", () => {
    render(<DifficultyChipView difficulty="advanced" examPrefix="UPSC" />);
    expect(screen.getByText(/UPSC . Hard/)).toBeTruthy();
  });
  it("category band shows the category", () => {
    render(<CategoryBandView category="Polity" />);
    expect(screen.getByText("Polity")).toBeTruthy();
  });
  it("day number renders the number", () => {
    render(<DayNumberView dayNumber={47} />);
    expect(screen.getByText("47")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- static-blocks`
Expected: FAIL — cannot find module `../blocks/StaticBlocks`.

- [ ] **Step 3: Create `src/blocks/StaticBlocks.tsx`**

```tsx
import React from "react";
import { STANDARD, difficultyColor, type Difficulty } from "../theme";

export const BrandHeaderView: React.FC<{ dayNumber: number }> = ({ dayNumber }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
    <span style={{ fontWeight: 900, fontSize: 34, color: STANDARD.text }}>
      Daily <span style={{ color: STANDARD.accent }}>GK</span>
    </span>
    <span style={{ fontWeight: 800, fontSize: 26, color: STANDARD.bg,
                   background: STANDARD.accent, padding: "8px 18px", borderRadius: 999 }}>
      DAY {dayNumber}
    </span>
  </div>
);

export const DifficultyChipView: React.FC<{ difficulty: Difficulty; examPrefix: string }> =
  ({ difficulty, examPrefix }) => {
    const { label, color } = difficultyColor(difficulty);
    const text = examPrefix ? `${examPrefix} . ${label}` : label;
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 12,
                     fontWeight: 800, fontSize: 26, color: STANDARD.text }}>
        <span style={{ width: 22, height: 22, borderRadius: 999, background: color }} />
        {text}
      </span>
    );
  };

export const CategoryBandView: React.FC<{ category: string }> = ({ category }) => (
  <span style={{ fontWeight: 800, fontSize: 28, letterSpacing: ".08em",
                 textTransform: "uppercase", color: STANDARD.bg, background: STANDARD.accent,
                 padding: "10px 20px", display: "inline-block" }}>
    {category}
  </span>
);

export const DayNumberView: React.FC<{ dayNumber: number }> = ({ dayNumber }) => (
  <span style={{ fontSize: 200, fontWeight: 900, lineHeight: 0.8, color: STANDARD.accent }}>
    {dayNumber}
  </span>
);
```
NOTE: the test matches `/UPSC . Hard/` where `.` is the regex any-char matching the middot rendered between prefix and label.

- [ ] **Step 4: Run to verify pass**

Run: `cd daily-gk-quiz/render && npm test -- static-blocks`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/blocks/StaticBlocks.tsx daily-gk-quiz/render/src/__tests__/static-blocks.test.tsx
git commit -m "feat: static block views (brand, difficulty, category, day number)"
```

---

## Task B6: QuestionView + OptionsView (asked / revealed states)

**Files:**
- Create: `daily-gk-quiz/render/src/blocks/QuestionOptions.tsx`
- Test: `daily-gk-quiz/render/src/__tests__/question-options.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QuestionView, OptionsView } from "../blocks/QuestionOptions";

const opts = [
  { letter: "A" as const, text: "Article 19" }, { letter: "B" as const, text: "Article 21" },
  { letter: "C" as const, text: "Article 14" }, { letter: "D" as const, text: "Article 32" },
];

describe("question + options views", () => {
  it("question view shows the question text", () => {
    render(<QuestionView question="Right to Life?" />);
    expect(screen.getByText("Right to Life?")).toBeTruthy();
  });
  it("asked state marks no option correct", () => {
    render(<OptionsView options={opts} correctLetter="B" revealed={false} />);
    expect(screen.getByTestId("opt-B").getAttribute("data-correct")).toBe("false");
  });
  it("revealed state marks only the correct option", () => {
    render(<OptionsView options={opts} correctLetter="B" revealed={true} />);
    expect(screen.getByTestId("opt-B").getAttribute("data-correct")).toBe("true");
    expect(screen.getByTestId("opt-A").getAttribute("data-correct")).toBe("false");
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- question-options`
Expected: FAIL — cannot find module.

- [ ] **Step 3: Create `src/blocks/QuestionOptions.tsx`**

```tsx
import React from "react";
import { STANDARD } from "../theme";

export type Option = { letter: "A" | "B" | "C" | "D"; text: string };

export const QuestionView: React.FC<{ question: string }> = ({ question }) => (
  <h1 style={{ fontSize: 74, fontWeight: 900, lineHeight: 1.08, letterSpacing: "-.02em",
               color: STANDARD.text, margin: 0 }}>
    {question}
  </h1>
);

export const OptionsView: React.FC<{ options: Option[]; correctLetter: string; revealed: boolean }> =
  ({ options, correctLetter, revealed }) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
      {options.map((o) => {
        const isCorrect = revealed && o.letter === correctLetter;
        const dim = revealed && o.letter !== correctLetter;
        return (
          <div key={o.letter} data-testid={`opt-${o.letter}`} data-correct={String(isCorrect)}
               style={{ display: "flex", alignItems: "center", gap: 26, padding: "28px 34px",
                        borderRadius: 999, fontSize: 48, fontWeight: 700, opacity: dim ? 0.45 : 1,
                        border: `3px solid ${isCorrect ? STANDARD.accent : STANDARD.pillOutline}`,
                        background: isCorrect ? "rgba(198,242,78,0.15)" : "transparent",
                        color: STANDARD.text }}>
            <span style={{ width: 70, height: 70, borderRadius: 999, fontSize: 38, fontWeight: 900,
                           display: "flex", alignItems: "center", justifyContent: "center",
                           background: isCorrect ? STANDARD.accent : STANDARD.pillOutline,
                           color: isCorrect ? STANDARD.bg : "#fff" }}>{o.letter}</span>
            {o.text}
          </div>
        );
      })}
    </div>
  );
```

- [ ] **Step 4: Run to verify pass**

Run: `cd daily-gk-quiz/render && npm test -- question-options`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/blocks/QuestionOptions.tsx daily-gk-quiz/render/src/__tests__/question-options.test.tsx
git commit -m "feat: question + options views with reveal state"
```

---

## Task B7: Remaining Views — Countdown, LockBeat, Reveal, Why, VerifiedBadge, SourceLine, CTA

**Files:**
- Create: `daily-gk-quiz/render/src/blocks/Pieces.tsx`
- Test: `daily-gk-quiz/render/src/__tests__/pieces.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CountdownView, LockBeatView, WhyView, VerifiedBadgeView, SourceLineView, CtaView }
  from "../blocks/Pieces";

describe("piece views", () => {
  it("countdown shows the given number", () => {
    render(<CountdownView n={2} />); expect(screen.getByText("2")).toBeTruthy();
  });
  it("lock beat shows the lock text", () => {
    render(<LockBeatView />); expect(screen.getByText(/Lock your answer/i)).toBeTruthy();
  });
  it("why view shows the explanation", () => {
    render(<WhyView explanation="Article 21 protects life." />);
    expect(screen.getByText(/Article 21 protects life/)).toBeTruthy();
  });
  it("verified badge shows VERIFIED", () => {
    render(<VerifiedBadgeView />); expect(screen.getByText(/VERIFIED/i)).toBeTruthy();
  });
  it("source line shows the source, promoted when revealed", () => {
    render(<SourceLineView sourceLine="Constitution, Art. 21" promoted />);
    expect(screen.getByText(/Constitution, Art. 21/)).toBeTruthy();
  });
  it("cta shows the call to action", () => {
    render(<CtaView cta="Comment A or B" />); expect(screen.getByText(/Comment A or B/)).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- pieces`
Expected: FAIL — cannot find module.

- [ ] **Step 3: Create `src/blocks/Pieces.tsx`**

```tsx
import React from "react";
import { STANDARD } from "../theme";

export const CountdownView: React.FC<{ n: number }> = ({ n }) => (
  <div style={{ width: 132, height: 132, borderRadius: 999, border: `7px solid ${STANDARD.accent}`,
                color: STANDARD.accent, fontSize: 70, fontWeight: 900, display: "flex",
                alignItems: "center", justifyContent: "center" }}>{n}</div>
);

export const LockBeatView: React.FC = () => (
  <div style={{ fontSize: 60, fontWeight: 900, color: STANDARD.accent, letterSpacing: "-.01em" }}>
    Lock your answer...
  </div>
);

export const WhyView: React.FC<{ explanation: string }> = ({ explanation }) => (
  <div style={{ borderLeft: `10px solid ${STANDARD.accent}`, paddingLeft: 28 }}>
    <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: ".14em", textTransform: "uppercase",
                  color: STANDARD.accent, marginBottom: 12 }}>Why it matters</div>
    <div style={{ fontSize: 38, fontWeight: 600, lineHeight: 1.32, color: STANDARD.text }}>
      {explanation}</div>
  </div>
);

export const VerifiedBadgeView: React.FC = () => (
  <span style={{ fontSize: 22, fontWeight: 800, color: STANDARD.accent,
                 border: `2px solid ${STANDARD.pillOutline}`, borderRadius: 999, padding: "10px 20px" }}>
    &#10003; VERIFIED SOURCE
  </span>
);

export const SourceLineView: React.FC<{ sourceLine: string; promoted?: boolean }> =
  ({ sourceLine, promoted }) => (
    <div style={{ fontSize: promoted ? 38 : 32, fontWeight: promoted ? 700 : 400,
                  color: promoted ? STANDARD.text : STANDARD.muted }}>
      Source: {sourceLine}
    </div>
  );

export const CtaView: React.FC<{ cta: string }> = ({ cta }) => (
  <div style={{ fontSize: 60, fontWeight: 900, color: STANDARD.text, letterSpacing: "-.01em" }}>
    {cta}
  </div>
);
```

- [ ] **Step 4: Run to verify pass**

Run: `cd daily-gk-quiz/render && npm test -- pieces`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/blocks/Pieces.tsx daily-gk-quiz/render/src/__tests__/pieces.test.tsx
git commit -m "feat: countdown, lock, why, verified, source, cta views"
```

---

## Task B8: Standard template + animated composition

**Files:**
- Create: `daily-gk-quiz/render/src/templates/Standard.tsx`
- Test: `daily-gk-quiz/render/src/__tests__/standard.test.tsx`

The animated wrapper uses Remotion hooks; to keep it testable, the test renders it inside Remotion's test surface by mounting the **pure composition function** `standardScene(frame, props, timeline)` that returns the current countdown number / revealed flag, plus a thin React tree. We unit-test `standardScene`.

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { standardState } from "../templates/Standard";
import { buildTimeline } from "../timeline";

const tl = buildTimeline(30);

describe("standardState (frame -> view state)", () => {
  it("before reveal: not revealed, countdown counts down", () => {
    const s = standardState(tl.countdown.from + 1, tl);
    expect(s.revealed).toBe(false);
    expect([3, 2, 1]).toContain(s.countdownN);
  });
  it("after reveal frame: revealed true", () => {
    const s = standardState(tl.reveal.from + 5, tl);
    expect(s.revealed).toBe(true);
  });
  it("lock window shows the lock beat", () => {
    const s = standardState(tl.lock.from + 1, tl);
    expect(s.showLock).toBe(true);
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- standard`
Expected: FAIL — cannot find module.

- [ ] **Step 3: Create `src/templates/Standard.tsx`**

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { STANDARD } from "../theme";
import { buildTimeline, type Timeline } from "../timeline";
import type { QuizProps } from "../props";
import { BrandHeaderView, DifficultyChipView, CategoryBandView, DayNumberView } from "../blocks/StaticBlocks";
import { QuestionView, OptionsView } from "../blocks/QuestionOptions";
import { CountdownView, LockBeatView, WhyView, VerifiedBadgeView, SourceLineView, CtaView } from "../blocks/Pieces";

// Pure frame -> view-state (unit-tested). No React, no Remotion hooks.
export function standardState(frame: number, tl: Timeline) {
  const revealed = frame >= tl.reveal.from;
  const showLock = frame >= tl.lock.from && frame < tl.reveal.from;
  const inCountdown = frame >= tl.countdown.from && frame < tl.lock.from;
  const cdWindow = tl.lock.from - tl.countdown.from; // split into thirds so 3-2-1 all show
  const elapsed = frame - tl.countdown.from;
  const countdownN = inCountdown
    ? Math.max(1, Math.min(3, 3 - Math.floor(elapsed / (cdWindow / 3))))
    : 0;
  const showWhy = frame >= tl.why.from;
  return { revealed, showLock, inCountdown, countdownN, showWhy };
}

export const Standard: React.FC<QuizProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tl = buildTimeline(fps);
  const s = standardState(frame, tl);
  return (
    <AbsoluteFill style={{ background: STANDARD.bg, padding: "64px 60px",
                           display: "flex", flexDirection: "column",
                           fontFamily: "Arial, Helvetica, sans-serif" }}>
      <BrandHeaderView dayNumber={props.dayNumber} />
      <div style={{ display: "flex", gap: 20, alignItems: "center", marginTop: 26 }}>
        <DayNumberView dayNumber={props.dayNumber} />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <CategoryBandView category={props.category} />
          <DifficultyChipView difficulty={props.difficulty} examPrefix={props.examPrefix} />
        </div>
      </div>
      <div style={{ marginTop: 34 }}><QuestionView question={props.question} /></div>
      <div style={{ marginTop: 40 }}>
        <OptionsView options={props.options} correctLetter={props.correctLetter} revealed={s.revealed} />
      </div>
      <div style={{ marginTop: 36, minHeight: 140, display: "flex", alignItems: "center", gap: 26 }}>
        {s.inCountdown && <CountdownView n={s.countdownN} />}
        {s.showLock && <LockBeatView />}
        {s.revealed && <VerifiedBadgeView />}
      </div>
      {s.showWhy && <div style={{ marginTop: 8 }}><WhyView explanation={props.explanation} /></div>}
      <div style={{ marginTop: "auto" }}>
        <CtaView cta={props.cta} />
        <div style={{ marginTop: 14 }}>
          <SourceLineView sourceLine={props.sourceLine} promoted={s.revealed} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 4: Run to verify pass**

Run: `cd daily-gk-quiz/render && npm test -- standard`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/templates/Standard.tsx daily-gk-quiz/render/src/__tests__/standard.test.tsx
git commit -m "feat: Standard template + frame->state logic"
```

---

## Task B9: Trick template

**Files:**
- Create: `daily-gk-quiz/render/src/templates/Trick.tsx`
- Test: `daily-gk-quiz/render/src/__tests__/trick.test.tsx`

The Trick template reuses the same `standardState` timing logic but renders the poster skin and a `trickHook` headline.

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TrickHookView } from "../templates/Trick";

describe("trick template", () => {
  it("renders the rotated trick hook (not hardcoded)", () => {
    render(<TrickHookView trickHook="Common Exam Trap" />);
    expect(screen.getByText("Common Exam Trap")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- trick`
Expected: FAIL — cannot find module.

- [ ] **Step 3: Create `src/templates/Trick.tsx`**

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { TRICK } from "../theme";
import { buildTimeline } from "../timeline";
import { standardState } from "./Standard";
import type { QuizProps } from "../props";
import { QuestionView, OptionsView } from "../blocks/QuestionOptions";
import { CountdownView, LockBeatView, WhyView, SourceLineView, CtaView } from "../blocks/Pieces";

export const TrickHookView: React.FC<{ trickHook: string }> = ({ trickHook }) => (
  <div style={{ fontSize: 110, fontWeight: 900, lineHeight: 0.9, textTransform: "uppercase",
                color: TRICK.ink, fontFamily: "Impact, 'Arial Narrow', sans-serif" }}>
    {trickHook}
  </div>
);

export const Trick: React.FC<QuizProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = standardState(frame, buildTimeline(fps));
  return (
    <AbsoluteFill style={{ background: TRICK.bg, padding: "64px 56px", display: "flex",
                           flexDirection: "column", fontFamily: "Arial, sans-serif", color: TRICK.ink }}>
      <TrickHookView trickHook={props.trickHook || "Common Exam Trap"} />
      <div style={{ marginTop: 30, border: `8px solid ${TRICK.ink}`, background: "#fff7e8",
                    boxShadow: `16px 16px 0 ${TRICK.ink}`, padding: "40px 36px" }}>
        <div style={{ marginBottom: 22 }}><QuestionView question={props.question} /></div>
        <OptionsView options={props.options} correctLetter={props.correctLetter} revealed={s.revealed} />
        <div style={{ marginTop: 28, display: "flex", gap: 26, alignItems: "center" }}>
          {s.inCountdown && <CountdownView n={s.countdownN} />}
          {s.showLock && <LockBeatView />}
        </div>
        {s.showWhy && <div style={{ marginTop: 24 }}><WhyView explanation={props.explanation} /></div>}
      </div>
      <div style={{ marginTop: "auto" }}>
        <CtaView cta={props.cta} />
        <SourceLineView sourceLine={props.sourceLine} promoted={s.revealed} />
      </div>
    </AbsoluteFill>
  );
};
```
NOTE: `QuestionView`/`WhyView`/`CtaView` use `STANDARD` text colours; on the light Trick bg the question/why still read because the panel is `#fff7e8`. If contrast review (QA) flags it, add a `tone` prop later — out of scope for this task.

- [ ] **Step 4: Run to verify pass**

Run: `cd daily-gk-quiz/render && npm test -- trick`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/render/src/templates/Trick.tsx daily-gk-quiz/render/src/__tests__/trick.test.tsx
git commit -m "feat: Trick template with rotated hook"
```

---

## Task B10: Quiz composition + Root registration

**Files:**
- Create: `daily-gk-quiz/render/src/Quiz.tsx`
- Modify: `daily-gk-quiz/render/src/Root.tsx`
- Test: `daily-gk-quiz/render/src/__tests__/quiz.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { pickTemplate } from "../Quiz";

describe("pickTemplate", () => {
  it("routes by props.template", () => {
    expect(pickTemplate("standard").name).toMatch(/Standard/);
    expect(pickTemplate("trick").name).toMatch(/Trick/);
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd daily-gk-quiz/render && npm test -- quiz`
Expected: FAIL — cannot find module.

- [ ] **Step 3: Create `src/Quiz.tsx`**

```tsx
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
```

- [ ] **Step 4: Update `src/Root.tsx` to register the composition**

```tsx
import React from "react";
import { Composition } from "remotion";
import { Quiz } from "./Quiz";
import { quizSchema } from "./props";
import { buildTimeline } from "./timeline";

const FPS = 30;

const defaultProps = {
  dayNumber: 47, category: "Polity", difficulty: "basic", examPrefix: "SSC",
  template: "standard", question: "Which Article guarantees the Right to Life?",
  options: [
    { letter: "A", text: "Article 19" }, { letter: "B", text: "Article 21" },
    { letter: "C", text: "Article 14" }, { letter: "D", text: "Article 32" },
  ],
  correctLetter: "B", explanation: "Article 21 protects life and personal liberty.",
  sourceLine: "Constitution of India, Art. 21", cta: "Comment A or B",
  trickHook: "Common Exam Trap", fps: FPS,
} as const;

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
```

- [ ] **Step 5: Run to verify pass + typecheck**

Run: `cd daily-gk-quiz/render && npm test -- quiz && npx tsc --noEmit`
Expected: vitest 1 test passes; `tsc --noEmit` reports no type errors.

- [ ] **Step 6: Commit**

```bash
git add daily-gk-quiz/render/src/Quiz.tsx daily-gk-quiz/render/src/Root.tsx daily-gk-quiz/render/src/__tests__/quiz.test.tsx
git commit -m "feat: Quiz composition + registered Remotion root"
```

---

## Task B11: Render CLI + sample MP4 (integration)

**Files:**
- Create: `daily-gk-quiz/render/render.mjs`
- Create: `daily-gk-quiz/render/sample-props.json`

This task has no unit test — it is the integration step that produces an actual MP4 and is verified by eye.

- [ ] **Step 1: Create `daily-gk-quiz/render/sample-props.json`**

```json
{
  "dayNumber": 47, "category": "Polity", "difficulty": "basic", "examPrefix": "SSC",
  "template": "standard", "question": "Which Article guarantees the Right to Life?",
  "options": [
    { "letter": "A", "text": "Article 19" }, { "letter": "B", "text": "Article 21" },
    { "letter": "C", "text": "Article 14" }, { "letter": "D", "text": "Article 32" }
  ],
  "correctLetter": "B", "explanation": "Article 21 protects life and personal liberty; the Supreme Court has read dignity, privacy and livelihood into it.",
  "sourceLine": "Constitution of India, Art. 21", "cta": "Comment A or B",
  "trickHook": "Common Exam Trap", "fps": 30
}
```

- [ ] **Step 2: Create `daily-gk-quiz/render/render.mjs`**

```js
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync } from "node:fs";
import path from "node:path";

const propsPath = process.argv[2] ?? "sample-props.json";
const outPath = process.argv[3] ?? "out/sample.mp4";
const inputProps = JSON.parse(readFileSync(propsPath, "utf-8"));

const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id: "Quiz", inputProps });
await renderMedia({ serveUrl, composition, codec: "h264", outputLocation: outPath, inputProps });
console.log("rendered", outPath);
```

- [ ] **Step 3: Render the sample**

Run: `cd daily-gk-quiz/render && node render.mjs sample-props.json out/sample.mp4`
Expected: completes without error; `out/sample.mp4` exists and is > 0 bytes (`ls -l out/sample.mp4`). First run downloads a Chromium for Remotion.

- [ ] **Step 4: Eyeball the output**

Open `out/sample.mp4` (or extract a frame) and confirm: brand header, Day 47, Polity + difficulty chip, question legible, 4 options, countdown, "Lock your answer", reveal with B in lime, why-it-matters, verified badge, promoted source, "Comment A or B". Report what you saw; if a block is missing/overflowing, fix the relevant View/template and re-render before committing.

- [ ] **Step 5: Commit (code only — not the MP4)**

```bash
git add daily-gk-quiz/render/render.mjs daily-gk-quiz/render/sample-props.json
git commit -m "feat: render CLI + sample props (out/ is gitignored)"
```

---

## Task B12: Full suite green + README

**Files:**
- Create: `daily-gk-quiz/render/README.md`

- [ ] **Step 1: Run both suites**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest -q` (Part A — expect all green)
Run: `cd daily-gk-quiz/render && npm test` (Part B — expect all green)
Report both totals.

- [ ] **Step 2: Write `daily-gk-quiz/render/README.md`**

```markdown
# daily-gk-quiz render

Remotion project: one approved question (JSON props) -> 1080x1920 MP4.

## Develop
npm install
npm test          # vitest (logic + view components)
npm run studio    # live preview (Remotion Studio)

## Render
node render.mjs <props.json> <out.mp4>   # e.g. node render.mjs sample-props.json out/sample.mp4

Props schema: src/props.ts. Templates: standard (80%) + trick (20%, set props.template).
Design tokens: src/theme.ts. Timeline: src/timeline.ts. Output handed to the publisher.
```

- [ ] **Step 3: Commit**

```bash
git add daily-gk-quiz/render/README.md
git commit -m "docs: render project README"
```

---

## Notes for the implementer

- **Two suites:** Part A is pytest in `daily-gk-quiz/`; Part B is vitest in `daily-gk-quiz/render/`. Keep them green independently.
- **View/wrapper split is the testability rule:** never put `useCurrentFrame`/`useVideoConfig` in a `*View`. Views are pure (jsdom-testable); only templates use Remotion hooks, and their timing is extracted into the pure `standardState` function (unit-tested).
- **Don't commit binaries:** `out/`, `node_modules/`, `.remotion/` are gitignored (Task B1).
- **Trick contrast:** the Trick template reuses Standard-coloured text views on a light panel; flagged in B9 — only revisit if the QA review (spec sec 7) fails contrast.
- **answer_position wiring:** Part A emits the balanced slot in `DayPlan`; the SKILL builds `options` ordered so the correct option sits in `answer_position` and sets `correctLetter` accordingly when it writes the render props. (That prop-assembly glue lives in the SKILL recipe, updated when the pipeline is wired end-to-end — out of scope for this plan, which builds the render + its data.)
- **QA rubric (spec sec 7) is applied manually for v1:** Task B11 step 4 eyeballs the sample render against the rubric dimensions (1s-stop, 6-inch readability, credibility, brand consistency, accuracy/metadata surface, answer-key balance, pacing). The automated "render stills -> Claude grades" tool described in the spec is deferred — not built in this plan.
