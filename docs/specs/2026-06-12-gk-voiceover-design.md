# Design: Quiz voice-over (edge-tts, voice-driven beats)

**Date:** 2026-06-12
**Status:** Approved design (plan next -- no implementation in this phase)
**Owner:** sdevendran
**Relates to:** `daily-gk-quiz/render/` (the Remotion render layer this extends),
`daily-gk-quiz/selection/build.py` (orchestrator -- unchanged by this), and the WhichWise
content-studio TTS approach reused as a *capability* (edge-tts), not its finance content/patterns.

**Context note:** the operator explicitly chose to keep building the pipeline as infrastructure
before posting any videos, with the market risk acknowledged (saturated niche, incumbents already do
verified content, distribution unbuilt). This spec is part of that infrastructure investment.

---

## 1. What this is

The quiz Short currently renders **silent** (visuals + no audio). This adds **Indian-English neural
narration** of the question, the answer reveal, and the explanation, with the visual beats **timed to
the voice** so nothing is rushed or clipped. It reuses WhichWise's free **edge-tts** mechanism
(`python -m edge_tts`, voice `en-IN-NeerjaNeural`) and leaves a pluggable seam for **ElevenLabs**
later. All work stays in the render layer; `build.py` is untouched.

**Out of scope (YAGNI / later):** the ElevenLabs implementation (seam only this round);
Hindi/bilingual narration (on-screen content is English -- bilingual is a separate content decision);
background music / sound design; per-word caption highlighting (the on-screen text already shows the
words); changing `build.py` or the publisher.

---

## 2. Where it lives -- render layer only

All voice work is inside `daily-gk-quiz/render/`, where Remotion and the npm media binaries live.
`build.py` keeps calling `node render.mjs <props.json> <out.mp4>` exactly as today; `render.mjs` does
the VO step internally. This mirrors WhichWise's `render-video.mjs` (Node orchestrates
`python -m edge_tts` as a subprocess) and keeps the Python/selection layer clean.

---

## 3. Flow inside `render.mjs` (new pre-render step)

1. **Derive the narration script** from the existing props -- a pure function
   `voLines(props) -> { question, reveal, why }`:
   - `question` = `props.question`
   - `reveal` = `"The correct answer is {correctLetter}. {answer text of the correct option}."`
   - `why` = `props.explanation`
   (Pure, no I/O -- the unit-tested core.)
2. **Synthesize** each line to an mp3 via the **TTS provider** (SS5) into
   `render/public/vo/<slug>-<line>.mp3` (under `public/` so Remotion `staticFile()` can serve them).
3. **Measure** each mp3 with `ffprobe-static` -> seconds.
4. **Compute the parametric timeline** (SS4) from those durations, pass the timeline + the three
   `staticFile`-relative audio paths into Remotion `inputProps`, and render.
5. **Clean up** the generated mp3s after the render (best-effort).

If a VO line is empty (e.g. no explanation), that beat falls back to its current fixed duration and
no `<Audio>` is placed.

---

## 4. Parametric timeline (`render/src/timeline.ts`)

`buildTimeline` changes from hardcoded scene starts to taking the three narration durations (seconds)
and a `tail` (breathing room, ~0.45s):

```
buildTimeline(fps, vo = { question, reveal, why }, tail = 0.45) -> Timeline
```

- **questionRead** (the pre-countdown span where the question + options are shown) =
  `max(currentFixedSpan, vo.question + tail)` -- the question is fully read before the countdown.
  Options still stagger within it.
- **countdown / lock / ctaHold** = **fixed** (the quiz mechanic -- unchanged from current SCENES).
- **reveal** = `max(currentFixed, vo.reveal + tail)` -- the answer is announced.
- **why** = `max(currentFixed, vo.why + tail)` -- the explanation is read.
- `totalFrames` = sum of all beats (the video length flexes per question).

Using `max(currentFixed, vo+tail)` means a short VO never makes a beat shorter than its current
visual minimum; a long VO expands it. Frame counts via `Math.round(seconds * fps)` (existing
convention). When `vo` is omitted, `buildTimeline(fps)` reproduces today's fixed timeline (back-compat
for existing tests / silent renders).

`Quiz.tsx` adds a Remotion `<Audio src={staticFile(props.audio.question)}>` (and reveal / why) inside
the matching `<Sequence>`. **Remotion muxes the audio during `renderMedia`** -- no separate ffmpeg
step; `ffprobe-static` is only for measuring VO length pre-render.

**Props augmentation:** `render.mjs` reads the `props.json` written by `build.py`, generates the VO,
then **injects** an optional `audio: { question, reveal, why }` (staticFile-relative paths) into the
`inputProps` it passes to `selectComposition`/`renderMedia`. The zod `quizSchema` gains an **optional**
`audio` field (and the timeline reads VO durations that `render.mjs` also injects), so `build.py`'s
existing `props.json` -- which has no audio -- stays valid (a silent render just omits `audio`, and
`buildTimeline(fps)` with no `vo` reproduces today's fixed timeline). `Quiz.tsx` renders `<Audio>`
only when the corresponding `audio.*` path is present.

---

## 5. Pluggable TTS provider (`render/src/voiceover.mjs` or `render/voiceover.mjs`)

A small module exposing `synthesize(text, outPath, opts) -> Promise<void>`:
- **edge-tts (default, implemented):** spawn `python -m edge_tts --voice en-IN-NeerjaNeural
  --rate +6% --text <text> --write-media <outPath>` (the WhichWise invocation).
- **elevenlabs (stub, NOT implemented this round):** selected when `process.env.TTS === "elevenlabs"`;
  throws "not implemented" for now. The seam means the later swap is one module with no pipeline
  change.

Voice id and rate are module constants (overridable via `props.voice` / env), defaulting to
`en-IN-NeerjaNeural` / `+6%`.

---

## 6. Dependencies & disclosure

- Add **`ffprobe-static`** to `render/package.json` (npm static binary -- **no system ffmpeg/ffprobe
  install**, which removes the known repo gotcha for the render+VO path; posting-time normalize is a
  separate publisher concern).
- **`edge-tts`** is a Python package: `pip install edge-tts` into `daily-gk-quiz/.venv` (documented in
  `render/README.md`). `render.mjs` invokes it as `python -m edge_tts` (system/venv python on PATH).
- **AI disclosure:** the videos now contain a synthetic voice, so `ai_disclosure=true` (already set by
  `build.py`) is now genuinely accurate -- no change needed, but noted for the record.

---

## 7. Testing (TDD)

- **`voLines(props)`** -- pure unit tests: question/reveal/why derivation; reveal string format
  (`"The correct answer is B. Article 21."`); empty-explanation -> empty `why`; works for both
  standard and trick templates (vitest).
- **`buildTimeline(fps, vo, tail)`** -- pure unit tests: narration beats = `max(fixed, vo+tail)`;
  structural beats unchanged; `totalFrames` = sum; `buildTimeline(fps)` with no `vo` reproduces the
  current fixed timeline (back-compat); fps rounding. Extends the existing `timeline.test.ts`.
- **`<Audio>` placement** -- a Quiz render test asserts an `<Audio>` is present for each non-empty
  narration line and absent when a line is empty (vitest + existing render test harness).
- **edge-tts synthesis + Remotion audio muxing** = subprocess/binary side-effects -> **one manual
  end-to-end verify**: render a real narrated MP4 and eyeball that the voice matches the on-screen
  beats and nothing is clipped (consistent with how the silent render is already verified;
  `ffprobe-static` provides durations, edge-tts requires network for the first synth).

---

## 8. Open questions / locked defaults

Locked: render-layer-only (build.py unchanged); voice-driven narration beats with fixed quiz-mechanic
beats; `en-IN-NeerjaNeural` English voice matching on-screen text; Remotion embeds audio (no separate
ffmpeg mux); edge-tts now / ElevenLabs seam only; `ffprobe-static` via npm. Tunable later: voice id,
`rate`, `tail` seconds; whether to also narrate the hook/CTA; Hindi/bilingual (needs bilingual
content first).
