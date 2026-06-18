# Design: sticky-difference render template ("What's the Difference" Shorts)

**Date:** 2026-06-18
**Status:** Approved design (render template only -- no content-gen / publishing in this phase)
**Owner:** rewva
**Relates to:** `docs/specs/2026-06-10-gk-render-layer-design.md` (sibling render layer, patterns ported), `docs/idea-bank.md` (content-funnel channel class), `CLAUDE.md` (moat + anti-slop principles)

---

## 1. What this is

A second faceless-content channel render template: a **1080x1920 vertical MP4** that answers
**"X vs Y -- what's the difference?"** for one pair of commonly-confused things (Coffin vs Casket,
Jam vs Jelly, etc.). The format is a proven short-form education shape (used by many channels,
e.g. "Sticky Info") and is **not ownable**; what we build is an **original visual identity** on
top of it so the channel is distinct, not a clone -- per principle #6 (anti-slop = survival, we
win by being distinctive, not derivative).

Scope of THIS phase: **the render template only.** Props are fed by hand (a `props.json`). The
content-generation step (picking a verified pair + writing the verified difference) and the
publishing/review path are explicitly out of scope here and get their own spec -> plan cycle
later. The VO (voice-over) seam is included in the props shape so it stays compatible with the
existing edge-tts pipeline, but VO synthesis is not built here.

Built as a **fresh, self-contained Remotion project** in a new sibling channel folder
`sticky-difference/render/` -- the proven scene/timeline/test patterns from `daily-gk-quiz/render`
are **ported, not depended on** (repo-boundary: each channel stays independent).

Non-negotiable design goals (same as the GK render): (1) stop the scroll in ~1s, (2) readable on
a 6-inch phone, (3) credible / verified (a source line, never an unsourced claim), (4) a
recognizable brand built over many posts.

---

## 2. Visual system (locked)

Chosen from a 5-mascot exploration (owl, robot, fox, brain, cat). **Decision: the Cat mascot,
mint/coral light theme.** A custom original character is the identity moat -- recolorable,
animatable, ours, no licensing, and unmistakably not the reference channel.

### 2.1 Palette (the "Curious" theme)

| Token | Value |
|---|---|
| Background | `#e6f6ef` mint, with a soft white radial top-right glow |
| Ink (names, headline, "?") | `#16241f` near-black green |
| Accent | `#ff6b6b` coral (the recurring brand signal: "vs" badge, "difference?" word, frame outline) |
| Image frame | white card, coral outline, soft drop shadow |
| Placeholder text | `#9fb6ac` muted |
| Type | heavy grotesk (Arial/Helvetica bold), tight tracking |

### 2.2 The mascot -- procedural SVG cat

A `<Mascot pose="..." />` React component drawing the cat as SVG strokes/fills (gray body
`#9aa7b2`, white belly, coral nose, dark outline). Joint/feature positions live in `poses.ts` as
**pure data** (unit-testable); `Mascot.tsx` renders them and animates a blink + subtle idle bob
and per-beat gesture with Remotion springs. Recolorable via theme tokens.

Pose set (one per beat):

- `thinking` -- paw to chin, head slight tilt (Hook)
- `point-left` -- paw gestures toward item X (Item X beat)
- `point-right` -- paw gestures toward item Y (Item Y beat)
- `idea` -- alert/curious, ears up, small spark/`!` (Difference beat)

### 2.3 Brand name

On-screen masthead is a **placeholder ("CURIOUS")**. Final channel name is TBD and must be
**our own** (explicitly not "Sticky ..." -- avoid any echo of the reference). The cat + coral
accent + "what's the difference?" lockup are the constant brand assets. (Folder name
`sticky-difference` is an internal label only and does not appear on screen.)

---

## 3. Architecture

```
props.json  (one X-vs-Y pair, fed by hand this phase)
        |
        v
 sticky-difference/render/  (Remotion project, React -> video)
   src/
     props.ts        zod schema: topic, 2 items (name/image/trait), difference,
                     optional cta, sourceLine, brandHandle, fps, optional vo/audio
     theme.ts        DIFF design tokens (Curious palette)
     timeline.ts     buildTimeline(fps, vo): hook -> itemX -> itemY -> difference -> cta?
     mascot/
       poses.ts      pure pose data per pose key (unit-tested)
       Mascot.tsx    SVG cat; pose prop; blink/idle/gesture springs
     scenes/
       Hook.tsx        side-by-side images + names + "what's the difference?" + mascot:thinking
       Item.tsx        one item: image + name + 1-2 line trait + mascot:point-(left|right)
       Difference.tsx  the punchy distinction + optional CTA line + source; mascot:idea
     blocks/
       ItemImage.tsx   staticFile image in a rounded coral-outlined frame + entrance spring
       BrandHeader.tsx masthead (placeholder name) + optional handle
     Difference.tsx (root component) picks/sequences scenes on the timeline
     Root.tsx        Remotion <Composition id="Difference"> (1080x1920, calc duration from timeline)
   public/
     comparisons/    operator drops item images here (e.g. coffin.jpg, casket.jpg)
   render.mjs        CLI: props.json -> out/<slug>.mp4 (mirrors gk render.mjs)
   package.json, tsconfig.json, vitest.config.ts
        |
        v
   out/<slug>.mp4  (1080x1920, 30fps)  -- handed to content-gen / publisher later (out of scope)
```

Pure functions (timeline math, pose data, prop mapping, per-scene view-state) are unit-tested;
the actual video encode (headless Chrome) is the one binary integration seam, same isolation as
the GK render.

---

## 4. Props schema (fed by hand this phase)

```ts
{
  topic: string,                 // "Coffin vs Casket" (used for slug / metadata)
  items: [                       // exactly 2
    { name: string, image: string, trait: string },  // image = filename in public/comparisons/
    { name: string, image: string, trait: string }
  ],
  difference: string,            // the one punchy key distinction (the payoff)
  cta?: string,                  // optional comment-bait; omit -> Difference beat shows no CTA line
  sourceLine: string,            // verified source (anti-slop trust gate; always shown)
  brandHandle?: string,          // e.g. "@yourhandle"
  fps?: number,                  // default 30
  vo?: { hook, itemX, itemY, difference, cta? },   // optional VO durations (seam; not synthesized here)
  audio?: { hook, itemX, itemY, difference, cta? } // optional VO file paths (staticFile)
}
```

`trait` is a short (1-2 line) characterizing fact per item; `difference` is the contrast payoff.
`sourceLine` is mandatory -- the credibility differentiator; the template always renders it.

---

## 5. Scene / animation timeline (no-VO baseline; VO expands narration spans)

Mirrors the GK `buildTimeline` approach: integer-frame segments accumulated with zero drift;
narration spans expand to fit VO when present, fixed beats stay fixed. Baseline (no VO),
30fps, total ~16-20s:

| Beat | Mascot pose | Content | Motion |
|---|---|---|---|
| Hook | thinking | both names + image frames side by side, "vs" badge, "what's the difference?" | names/frames stagger in; mascot idle bob; "?" pops over mascot |
| Item X | point-left | X image enlarged + name + trait | scene slides in; mascot points left; trait lines stagger |
| Item Y | point-right | Y image enlarged + name + trait | scene slides in; mascot points right |
| Difference | idea | the key distinction stated boldly; optional CTA line; source line | distinction scales in; mascot ears-up spark; CTA pill (if present) |

`cta` is optional: if omitted, the Difference beat ends on the distinction + source (no CTA line),
and the timeline's CTA tail collapses. VO durations (when supplied) expand the hook / item /
difference spans via the same `max(minSec, voSec+tail)` rule as the GK timeline.

---

## 6. Testing

Same vitest setup as `daily-gk-quiz/render`:

- `poses.test.ts` -- pose data shape + every pose key present, values in range
- `timeline.test.ts` -- segment math, no-VO baseline, VO expansion, optional-CTA collapse, zero drift
- `props.test.ts` -- zod schema accepts valid props, rejects (not exactly 2 items, missing source, etc.)
- per-scene render-smoke tests (Hook/Item/Difference mount without throwing for sample props)
- `mascot.test.tsx` -- Mascot renders for each pose key

---

## 7. Integration & boundaries

- **Input (this phase):** a hand-authored `props.json` + item images in `public/comparisons/`.
- **Output:** `out/<slug>.mp4` (1080x1920, 30fps).
- **Out of scope here:** content generation (verified pair selection + difference writing),
  review dashboard, publishing, VO synthesis, the brand-name decision -- each later.
- **Repo boundary:** patterns ported from `daily-gk-quiz/render`; NO runtime dependency on it,
  and none on the frozen finance repo.

---

## 8. Out of scope (YAGNI)

- More than the one Cat identity (the other 4 explored mascots are parked, not built).
- Attribute-table / multi-difference variants (start with the single-distinction payoff).
- Stock-image fetching pipeline (images dropped in by hand this phase).
- VO synthesis, captions burn-in (seam only; built later with the existing edge-tts path).
- Any in-template content generation or fact-checking (separate spec).

---

## 9. Open questions

- **Final brand name + masthead** (our own, not "Sticky ...") -- decide before launch.
- **Mascot render polish:** the explored cat is a draft; finalize proportions, the four poses,
  and blink/idle/gesture timing during implementation.
- **Item image handling:** fixed frame size with object-fit cover; confirm crop/letterbox rule
  for odd aspect ratios during implementation.
- **Typeface:** ship with system grotesk for v1; evaluate a licensed display face later.
- **"vs" / headline lockup:** keep constant as a brand asset; confirm exact placement vs mascot.
