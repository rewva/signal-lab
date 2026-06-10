# Design: GK render layer (daily-gk-quiz video)

**Date:** 2026-06-10
**Status:** Approved design (plan only -- no implementation in this phase)
**Owner:** sdevendran
**Relates to:** `docs/specs/2026-06-04-daily-gk-quiz-design.md` (parent), `docs/specs/2026-06-10-gk-topic-selection-design.md` (feeds it), `docs/engagement-antislop-research.md` (why differentiation = survival)

**Revision (2026-06-10, post-review):** faster ~12-14s timeline; added a "Lock your answer"
beat before reveal; added a visible **difficulty indicator** (Easy/Medium/Hard); added
**answer-key balancing** (even correct-position distribution over the last 30); trick hooks
**rotated from a pool, never hardcoded**; source line more prominent at reveal; WhyBlock allows
1-2 sentences.

---

## 1. What this is

The render layer turns one **approved, verified question** (from the topic-selection layer +
operator accuracy gate) into a finished **1080x1920 vertical MP4** ready for the `publisher` to
post. It is the differentiation surface: per verified research, a generic single-prompt A/B/C/D
card is a **channel-fatal** match for YouTube/Meta "inauthentic content" rules; the escape is
genuine per-video value + visibly varied substance + careful, branded production.

Built as a **fresh, self-contained Remotion project** inside `daily-gk-quiz/render/` -- the
proven design tokens and scene patterns from the operator's existing studio are **ported**, not
depended on (CLAUDE.md repo-boundary: signal-lab stays independent of the frozen finance repo).

Audience: SSC, UPSC, TNPSC, Railways, Banking, Police, State PSC aspirants. Non-negotiable
design goals: (1) stop the scroll in ~1s, (2) readable on a 6-inch phone, (3) credible (not
AI trivia), (4) build a recognizable brand over 365 days.

---

## 2. Visual system (locked)

Chosen from a 5-template exploration (newspaper, poster, chalkboard, notebook, duotone-zine).
Decision: **one primary brand template + one trick variant.**

### 2.1 Primary template -- "Standard" (80% of posts)

Dark duotone, modern, highest-contrast, readable at thumbnail size.

| Token | Value |
|---|---|
| Background | `#15123b` (deep indigo) + halftone dot texture (`#c6f24e` dots, ~10% opacity) |
| Accent / brand asset | `#c6f24e` (neon lime) -- the recurring brand signal |
| Text | `#f4f1ff` primary, `#c2bdec` muted |
| Option pill outline | `#4b4780` |
| Type | heavy grotesk (Arial/Helvetica bold; a licensed grotesk may replace later), tight tracking |

Anatomy (top -> bottom): brand header ("Daily GK" + Day N pill) -> big **Day-number** + category
band + **difficulty chip** -> **question** -> 4 **option pills** (A-D) -> **countdown ring** +
small VERIFIED-SOURCE badge -> CTA + **source line**. At reveal the **source line is promoted**
(larger/brighter) -- trust is the headline differentiator for aspirants.

Difficulty chip colours (mapped from the data model's difficulty): `basic` -> green `#3ddc84`
(Easy), `intermediate` -> amber `#f4c430` (Medium), `advanced` -> red `#ff5a5f` (Hard). Rendered
as a coloured dot + label, optionally prefixed with the top exam ("SSC - Easy").

### 2.2 Trick variant -- "Poster" (20% of posts)

Reserved for misconception / current-affairs-trap / tricky questions only (so the hook keeps
its credibility). Cream `#fbe6c9`, charcoal `#171410`, condensed Impact headline, hard-shadow
panel, accents teal `#16a085` + red `#e2402b` + marigold `#e9b949`, slanted sticker badge.

**The hook is NOT hardcoded** -- it is drawn from a rotated pool (LRU, via the existing
`pick_rotation`) so it never wears out. Pool: "Most Aspirants Miss This", "Common Exam Trap",
"Easy But Confusing", "Don't Rush This One", "Looks Easy, Isn't", "SSC Favourite Trap",
"UPSC Asked a Similar Concept", "90% Get This Wrong". Lives in `data/prompts.json` under a
`trick_hooks` key.

### 2.3 Brand-name

Masthead reads **"Daily GK"** (placeholder). Final name TBD -- **explicitly not WhichWise**
(signal-lab is independent). The lime accent + Day-number + VERIFIED-SOURCE badge are the
365-day brand assets, kept constant.

### 2.4 Refinements already applied to the Standard template

Bigger question (fills frame, ~20% less dead space below the timer), smaller VERIFIED-SOURCE
badge, larger/brighter source line, CTA = "Comment A or B" (forced-choice -- the verified
comment-driver). Reference render: the brainstorm mockups.

---

## 3. Architecture

```
approved Question + DayPlan (JSON)
        |
        v
 render/  (Remotion project, React -> video)
   props.ts        typed input: question, options, answer, explanation,
                   source, exam_relevance, day_number, template, hooks/cta
   theme.ts        ported design tokens (Standard + Trick palettes)
   blocks/         composable scene blocks (see sec 4)
   templates/
     Standard.tsx  composes blocks in the primary layout
     Trick.tsx     composes blocks in the poster layout
   Quiz.tsx        root composition: picks template by props.template,
                   sequences scenes on a timeline (sec 5)
        |
        v
   render.mjs / CLI  ->  out/<fact_key>.mp4  (1080x1920, 30fps)
        |
        v
   handed to publisher (POST /api/jobs)   [separate subsystem]
```

The Remotion render is the one integration seam with a binary (the renderer/headless Chrome),
mirroring how the publisher isolates ffmpeg/network. Block components and the prop mapping are
pure/unit-testable; the actual video encode is an integration step.

---

## 4. Composable blocks (ported resolver pattern)

Each block is a focused React component with typed props; a template composes them. Blocks:

- `BrandHeader` -- "Daily GK" wordmark + Day-N pill (constant brand row)
- `DayNumber` -- the large day number (Standard) -- brand anchor
- `CategoryBand` -- category (e.g. "Polity")
- `DifficultyChip` -- coloured dot + Easy/Medium/Hard (mapped from difficulty), optional exam prefix
- `QuestionBlock` -- the question text (auto-fit sizing for length)
- `Options` -- A-D pills; render state = `asked` | `revealed` (correct highlighted, others dimmed)
- `Countdown` -- 3-2-1 ring (Standard) / circle (Trick)
- `LockBeat` -- a brief "Lock your answer..." card shown after the countdown, before reveal (builds anticipation, drives comments)
- `AnswerReveal` -- the correct option callout
- `WhyBlock` -- the "why it matters / exam relevance" explanation; supports **1-2 sentences** of real learning (the added-value pedagogy, the key differentiator)
- `VerifiedBadge` -- small "VERIFIED SOURCE" chip (trust signal; only shown when sourced)
- `SourceLine` -- the cited source text (e.g. "Source: Constitution of India, Art. 21"); **promoted (larger) during reveal**
- `CTA` -- rotating call-to-action ("Comment A or B", etc.)
- `Hook` -- the trick-variant headline (Trick template only; rotated, never hardcoded)

`VerifiedBadge`/`SourceLine` render only when the question is verified (trust-gate: never show
an unsourced claim) -- the field-trust principle ported from the operator's pipeline.

---

## 5. Scene / animation timeline (~12-14s, 30fps)

Faster than the first draft -- for daily Shorts/Reels in 2026, faster wins. Total ~12-14s.

| t (s) | Scene | Motion |
|---|---|---|
| 0.0-0.8 | Hook / question entrance | brand header + difficulty chip static; question words stagger in fast (the 1-second stop) |
| 0.8-3.3 | Options appear | A-D pills slide/fade in quickly; CTA "Comment A or B" visible |
| 3.3-5.3 | Countdown | ring counts 3-2-1 with a tick |
| 5.3-6.1 | **Lock your answer** | brief "Lock your answer..." card -- a ~0.8s anticipation beat |
| 6.1-10 | Answer reveal | correct pill turns lime + scales (a *ding*); others dim; **source line promoted** |
| 9-13 | Why it matters | WhyBlock fades in (1-2 sentences); VerifiedBadge + SourceLine settle |
| end | CTA hold | final CTA + source on screen ~1.5s |

Timings are defaults (tunable per the post-review table; faster preferred). Audio (Kokoro TTS
narration + captions) layers onto this timeline but is specced/built separately (parent design);
the render must leave room for burned-in captions and expose timing markers.

---

## 6. Selection rules (template + answer-key balancing)

### 6.1 Template -- the 80/20 rule

A question carries an **`is_trick`** boolean (set during selection: misconception, common
confusion, or current-affairs trap). The planner sets `DayPlan.template`:

- `is_trick == true` -> `"trick"` (Poster), with a trick-hook rotated from `trick_hooks`.
- otherwise -> `"standard"` (Design 1).

This wires into the existing `DayPlan` (add `template`; `hook`/`cta` already present). Target
mix is ~80/20; if trick questions are scarce, standard simply dominates (no forcing). `is_trick`
is added to the `Question` model + surfaced at the operator accuracy gate.

### 6.2 Answer-key balancing (even A/B/C/D over the last 30)

Aspirants pattern-detect: if the correct answer is "B" too often, the channel looks rigged and
guessable. So the **position of the correct option (A/B/C/D) is balanced**, not the answer text.

- History stores `answer_position` (the A/B/C/D slot the correct option occupied) per posted record.
- When assembling the 4 options for a video, place the correct option in the position whose
  count is **lowest over the last 30 posts** (ties -> stable order), then fill the other three
  slots with the distractors. Deterministic.
- Exposed to the operator at the accuracy gate (so they see the final A/B/C/D order).

This is a small extension to the **selection/planner layer** (it owns history): add
`answer_position` to the history record + a `balance_answer_position(history, today)` helper, and
have `plan_today` emit the chosen slot. The render just consumes the already-ordered options.
(Update `docs/specs/2026-06-10-gk-topic-selection-design.md` accordingly when planned.)

---

## 7. Video QA rubric (ported from the 14-dimension review)

A render is graded before it's accepted, mirroring the operator's Lane-Review machinery:
render frames in headless Chrome (Remotion `<Thumbnail>` / still export) -> screenshot key
frames (question, countdown, reveal) -> a Claude pass scores:

| Dimension | Bar |
|---|---|
| 1-second stop | Is the question legible + hook compelling in the first frame? |
| 6-inch readability | Question + options legible at phone-thumbnail scale? |
| Credibility | Looks like a verified educational brand, not AI trivia? VERIFIED badge + source present? |
| Brand consistency | Masthead, lime accent, Day-N, layout match the locked template? |
| Accuracy surface | Correct option highlighted matches the approved answer; source line correct? |
| Metadata surface | Difficulty chip present + correct colour; category + Day-N shown? |
| Answer-key balance | Correct position not clustering (checked against the last-30 distribution)? |
| Frame pacing | Does info land legibly at each scene (no overcrowding/overflow); total <= ~14s? |

Below-bar -> flag for fix. This is the render-side analogue of the topic-layer accuracy gate.

---

## 8. Integration & boundaries

- **Input:** the SKILL, after the operator approves a question, emits a JSON props file
  (question, options, answer, explanation, source, exam_relevance, day_number, template, hook,
  cta) and invokes the renderer.
- **Output:** `out/<fact_key>.mp4` (1080x1920). The SKILL hands this to the `publisher`
  (`POST /api/jobs`) for the second approval gate + posting.
- **Out of scope here:** TTS/captions audio (parent design), the publisher, live account setup.
- **Repo boundary:** tokens/patterns ported from the finance repo; NO runtime dependency on it.

---

## 9. Out of scope (YAGNI)

- Stock imagery / Pexels pipeline (text-first stays; the proven image-validation technique can
  layer in later if needed).
- More than two templates at launch (the other 3 explored designs are parked, not built).
- Interactive elements (video is playback).
- A visual theme editor / multiple brand skins beyond Standard + Trick.

---

## 10. Open questions

- **Typeface:** ship with system grotesk (Arial/Helvetica bold) for v1; evaluate a licensed
  display face later for stronger brand distinctiveness.
- **Trick-hook believability:** monitor that the 20% cap holds and hooks stay honest (the
  research flagged hook fatigue if overused).
- **Auto-fit question sizing:** long questions must not overflow; needs a fit-to-box rule in
  `QuestionBlock` (define exact min/max font sizes during implementation).
- **Final brand name + masthead** (not WhichWise) -- decide before launch.
